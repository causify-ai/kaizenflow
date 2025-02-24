"""
Import as:

import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
"""

import abc
import logging
import os
from typing import Any, List, Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hsql as hsql
import im_v2.common.data.client as icdc
import im_v2.common.data_snapshot as icdds
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# #############################################################################
# CcxtImClient
# #############################################################################


class CcxtImClient(icdc.ImClient):
    """
    Implement behaviors specific of CCXT.
    """

    def _read_data(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        *,
        full_symbol_col_name: Optional[str] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Override the implementation by taking care of special timing semantic
        of the data (e.g., for Binance).
        """
        exchange_to_full_symbols_unique = self._split_full_symbols_by_exchanges(
            full_symbols
        )
        _LOG.debug(hprint.to_str("exchange_to_full_symbols_unique"))
        # Collect exchange-specific dataframes.
        exchange_dfs = []
        for exchange, full_symbols in exchange_to_full_symbols_unique.items():
            binance_cond = exchange == "binance"
            # For Parquet readers use `_dataset` attribute to get dataset type.
            ohlcv_pq_cond = getattr(self, "_dataset", "") == "ohlcv"
            # For DB readers use table name to get dataset type, e.g., `ccxt_ohlcv_futures`.
            ohlcv_db_cond = "ohlcv" in getattr(self, "_table_name", "")
            # The assumption is that the reader is either Parquet or DB one.
            ohlcv_cond = ohlcv_pq_cond or ohlcv_db_cond
            if binance_cond and ohlcv_cond:
                # Account for the fact that for CCXT OHLCV Binance `timestamp` is the start of the
                # sampling interval. E.g., to get data for [17:00, 17:02] (end of sampling
                # interval) one needs to query for [16:59, 17:01] (start of sampling interval).
                # TODO(Grisha): the assumption is that data resolution is 1 minute, is it
                # always true?
                _LOG.debug(
                    "Adjusting Binance timestamps to the DataFlow time semantic..."
                )
                if start_ts is not None:
                    start_ts = start_ts - pd.Timedelta(minutes=1)
                if end_ts is not None:
                    end_ts = end_ts - pd.Timedelta(minutes=1)
                _LOG.debug(hprint.to_str("start_ts end_ts"))
                df = super()._read_data(
                    full_symbols,
                    start_ts,
                    end_ts,
                    columns,
                    full_symbol_col_name=full_symbol_col_name,
                    **kwargs,
                )
                # TODO(Grisha): is `timestamp` always an index?
                # Add 1 minute back to convert `timestamp` to the end of sampling interval.
                df.index = df.index + pd.Timedelta(minutes=1)
                exchange_dfs.append(df)
            else:
                df = super()._read_data(
                    full_symbols,
                    start_ts,
                    end_ts,
                    columns,
                    full_symbol_col_name=full_symbol_col_name,
                    **kwargs,
                )
                exchange_dfs.append(df)
        # Combine exchange specific dfs.
        df = pd.concat(exchange_dfs)
        return df


# #############################################################################
# CcxtCddClient
# #############################################################################


# TODO(gp): It would be better to plug the functions directly in the classes,
#  rather than complicating the class hierarchy. Also it seems that there is
#  a single derived class.
class CcxtCddClient(icdc.ImClient, abc.ABC):
    """
    Contain common code for all the `CCXT` and `CDD` clients.

    E.g.,
    - getting `CCXT` and `CDD` universe
    - applying common transformation for all the data from `CCXT` and `CDD`
        - E.g., `_apply_olhlcv_transformations()`,
          `_apply_vendor_normalization()`
    """

    def __init__(
        self, vendor: str, universe_version: str, *, resample_1min: bool = False
    ) -> None:
        """
        Constructor.
        """
        super().__init__(vendor, universe_version, resample_1min=resample_1min)
        _vendors = ["CCXT", "CDD"]
        hdbg.dassert_in(self._vendor, _vendors)

    @staticmethod
    def _apply_ohlcv_transformations(data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations for OHLCV data.
        """
        ohlcv_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        # Verify that dataframe contains OHLCV columns.
        hdbg.dassert_is_subset(ohlcv_columns, data.columns)
        # Rearrange the columns.
        data = data[ohlcv_columns]
        return data

    def _apply_vendor_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Input data is indexed with numbers and looks like:
        ```
             timestamp      open        close    volume
        0    1631145600000  3499.01 ... 3496.36  346.4812
        1    1631145660000  3496.36     3501.59  401.9576
        2    1631145720000  3501.59     3513.09  579.5656
        ```
        Output data is indexed by timestamp and looks like:
        ```
                                   open        close    volume
        2021-09-08 20:00:00-04:00  3499.01 ... 3496.36  346.4812
        2021-09-08 20:01:00-04:00  3496.36     3501.59  401.9576
        2021-09-08 20:02:00-04:00  3501.59     3513.09  579.5656
        ```
        """
        # Apply vendor-specific transformations.
        data = self._apply_ccxt_cdd_normalization(data)
        # Apply transformations specific of the type of data.
        data = self._apply_ohlcv_transformations(data)
        return data

    def _apply_ccxt_cdd_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations common to `CCXT` and `CDD` data.
        """
        if self._vendor == "CDD":
            # Rename columns for consistency with other crypto vendors.
            # Column name for `volume` depends on the `currency_pair`, e.g.,
            # there are 2 columns `Volume BTC` and `Volume USDT` for `currency
            # pair `BTC_USDT. And there is no easy way to select the right
            # `Volume` column without passing `currency_pair` that will
            # complicate the interface. To get rid of this dependency the
            # column's index is used.
            data.columns.values[7] = "volume"
            data = data.rename({"unix": "timestamp"}, axis=1)
        # Verify that the timestamp data is provided in ms.
        hdbg.dassert_container_type(
            data["timestamp"], container_type=None, elem_type=int
        )
        # Transform Unix epoch into UTC timestamp.
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
        # Set timestamp as index.
        data = data.set_index("timestamp")
        # Round up float values in case values in raw data are rounded up
        # incorrectly when being read from a file.
        data = data.round(8)
        return data


# #############################################################################
# CcxtSqlRealTimeImClient
# #############################################################################


class CcxtSqlRealTimeImClient(CcxtImClient, icdc.SqlRealTimeImClient):
    def __init__(
        self,
        universe_version: str,
        db_connection: hsql.DbConnection,
        table_name: str,
        *,
        resample_1min: bool = False,
    ) -> None:
        vendor = "ccxt"
        super().__init__(
            vendor,
            universe_version,
            db_connection,
            table_name,
            resample_1min=resample_1min,
        )

    @staticmethod
    def should_be_online() -> bool:  # pylint: disable=arguments-differ'
        """
        The real-time system for CCXT should always be online.
        """
        return True


# #############################################################################
# CcxtCddCsvParquetByAssetClient
# #############################################################################


class CcxtCddCsvParquetByAssetClient(
    CcxtCddClient, icdc.ImClientReadingOneSymbol
):
    """
    Read data from a CSV or Parquet file storing data for a single `CCXT` or
    `CDD` asset.

    It can read data from local or S3 filesystem as backend.

    Using our naming convention this class implements the two classes:
    - CcxtCddCsvClient
    - CcxtCddPqByAssetClient
    """

    def __init__(
        self,
        vendor: str,
        universe_version: str,
        root_dir: str,
        # TODO(gp): -> file_extension
        extension: str,
        data_snapshot: str,
        *,
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Load `CCXT` data from local or S3 filesystem.

        :param vendor: price data provider, i.e. `CCXT` or `CDD`
        :param root_dir: either a local root path (e.g., `/app/im`) or
            an S3 root path (e.g., `s3://<ck-data>/reorg/historical.manual.pq`) to `CCXT` data
        :param extension: file extension, e.g., `csv.gz` or `parquet`
        :param aws_profile: AWS profile, e.g., `am`
        :param data_snapshot: same format used in `get_data_snapshot()`
        """
        super().__init__(vendor, universe_version, resample_1min=resample_1min)
        self._root_dir = root_dir
        # Verify that extension does not start with "." and set parameter.
        hdbg.dassert(
            not extension.startswith("."),
            "The extension %s should not start with '.'",
            extension,
        )
        self._extension = extension
        data_snapshot = icdds.get_data_snapshot(
            root_dir, data_snapshot, aws_profile
        )
        self._data_snapshot = data_snapshot
        # Set s3fs parameter value if aws profile parameter is specified.
        if aws_profile:
            self._s3fs = hs3.get_s3fs(aws_profile)
        # TODO(Sonya): Consider moving it to the base class as the `dataset` param.
        self._dataset = "ohlcv"

    def get_metadata(self) -> pd.DataFrame:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def _read_data_for_one_symbol(
        self,
        full_symbol: ivcu.FullSymbol,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        See description in the parent class.
        """
        # Split full symbol into exchange and currency pair.
        exchange_id, currency_pair = ivcu.parse_full_symbol(full_symbol)
        # Get absolute file path for a file with crypto price data.
        file_path = self._get_file_path(
            self._data_snapshot, exchange_id, currency_pair
        )
        # Read raw crypto price data.
        _LOG.info(
            "Reading data for vendor=`%s`, exchange id='%s', currencies='%s' from file='%s'...",
            self._vendor,
            exchange_id,
            currency_pair,
            file_path,
        )
        if hs3.is_s3_path(file_path):
            # Add s3fs argument to kwargs.
            kwargs["s3fs"] = self._s3fs
        if self._vendor == "CDD":
            # For `CDD` column names are in the 1st row.
            kwargs["skiprows"] = 1
        # TODO(Nikola): parquet?
        if self._extension == "pq":
            # Initialize list of filters.
            filters = []
            if start_ts:
                # Add filtering by start timestamp if specified.
                start_ts = hdateti.convert_timestamp_to_unix_epoch(start_ts)
                filters.append(("timestamp", ">=", start_ts))
            if end_ts:
                # Add filtering by end timestamp if specified.
                end_ts = hdateti.convert_timestamp_to_unix_epoch(end_ts)
                filters.append(("timestamp", "<=", end_ts))
            if filters:
                # Add filters to kwargs if any were set.
                kwargs["filters"] = filters
            # Load data.
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_parquet_to_df(stream, **kwargs)
        elif self._extension in ["csv", "csv.gz"]:
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_csv_to_df(stream, **kwargs)
            # Filter by dates if specified.
            if start_ts:
                start_ts = hdateti.convert_timestamp_to_unix_epoch(start_ts)
                data = data[data["timestamp"] >= start_ts]
            if end_ts:
                end_ts = hdateti.convert_timestamp_to_unix_epoch(end_ts)
                data = data[data["timestamp"] <= end_ts]
        else:
            raise ValueError(
                f"Unsupported extension {self._extension}. "
                f"Supported extensions are: `pq`, `csv`, `csv.gz`"
            )
        # Normalize data according to the vendor.
        data = self._apply_vendor_normalization(data)
        return data

    def _get_file_path(
        self,
        data_snapshot: str,
        exchange_id: str,
        currency_pair: str,
    ) -> str:
        """
        Get the absolute path to a file with `CCXT` or `CDD` price data.

        The file path is constructed in the following way:
        `<root_dir>/<data_snapshot>/<dataset>/<vendor>/<exchange_id>/<currency_pair>.<extension>`.

        E.g., `s3://.../20210924/ohlcv/ccxt/binance/BTC_USDT.csv.gz`.

        :param data_snapshot: same format used in `get_data_snapshot()`
        :param exchange_id: exchange id, e.g. "binance"
        :param currency_pair: currency pair `<currency1>_<currency2>`,
            e.g. "BTC_USDT"
        :return: absolute path to a file with `CCXT` or `CDD` price data
        """
        # Get absolute file path.
        file_name = ".".join([currency_pair, self._extension])
        file_path = os.path.join(
            self._root_dir,
            data_snapshot,
            self._dataset,
            self._vendor.lower(),
            exchange_id,
            file_name,
        )
        return file_path


# #############################################################################
# CcxtHistoricalPqByTileClient
# #############################################################################


class CcxtHistoricalPqByTileClient(
    CcxtImClient, icdc.HistoricalPqByCurrencyPairTileClient
):
    """
    Read historical data for `CCXT` assets stored as Parquet dataset.

    It can read data from local or S3 filesystem as backend.
    """

    # TODO(Grisha): use `*args` and `**kwargs` in order not to repeat the base class params.
    def __init__(
        self,
        universe_version: str,
        root_dir: str,
        partition_mode: str,
        dataset: str,
        contract_type: str,
        data_snapshot: str,
        *,
        version: str = "",
        download_universe_version: str = "",
        tag: str = "",
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        See the parent class for parameters description.
        """
        vendor = "CCXT"
        super().__init__(
            vendor,
            universe_version,
            root_dir,
            partition_mode,
            dataset,
            contract_type,
            data_snapshot,
            version=version,
            download_universe_version=download_universe_version,
            tag=tag,
            aws_profile=aws_profile,
            resample_1min=resample_1min,
        )
