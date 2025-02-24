"""
Import as:

import im_v2.kibot.data.client.kibot_clients as imvkdckicl
"""

import logging
import os
from typing import Any, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# #############################################################################
# KibotClient
# #############################################################################


class KibotClient(icdc.ImClient):
    """
    Contain common code for all the `Kibot` clients, e.g.,

    - getting `Kibot` universe
    - applying common transformation for all the data from `Kibot`
        - E.g., `_apply_kibot_csv_normalization()`, `_apply_kibot_parquet_normalization()`

    `Kibot` does not provide any information about the exchange so we
    use `kibot` as exchange for parallelism with other vendors so that
    we do not forget about it.
    """

    def __init__(
        self, universe_version: str, *, resample_1min: bool = False
    ) -> None:
        """
        Constructor.
        """
        vendor = "kibot"
        super().__init__(vendor, universe_version, resample_1min=resample_1min)

    def get_universe(self) -> List[ivcu.FullSymbol]:
        """
        See description in the parent class.
        """
        # TODO(Dan): CmTask1246.
        return []

    @staticmethod
    def _apply_kibot_csv_normalization(data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations to `Kibot` data in CSV format.

        CSV data is normalized to fit parent class output format:
            - full timestamp information is extracted from calendar date and
            clock time columns and set as index
            - calendar date and clock time columns are dropped

        Input data:
        ```
        0    09/29/2015  08:24  102.99 ... 102.99  112
        1    09/29/2015  08:27  102.99 ... 102.99  112
        2    09/29/2015  09:04  103.18 ... 103.18  781
        ```
        Output data:
        ```
                                   open       close   volume
        2015-09-29 08:24:00+00:00  102.99 ... 102.99  112
        2015-09-29 08:27:00+00:00  102.99     102.99  112
        2015-09-29 09:24:00+00:00  103.18     103.18  781
        ```
        """
        timestamp_column = pd.to_datetime(
            data["date"] + " " + data["time"], utc=True
        )
        data = data.set_index(timestamp_column)
        data = data.drop(["time", "date"], axis=1)
        return data

    @staticmethod
    def _apply_kibot_parquet_normalization(data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations to `Kibot` data in Parquet by asset format.

        Parquet by asset data is normalized to fit parent class output format:
            - UTC timezone is added to the index
            - index name is dropped
            - columns are named accordingly

        Input data:
        ```
                               open      close  vol
        datetime
        2015-09-29 08:24:00  102.99 ... 102.99  112
        2015-09-29 08:27:00  102.99     102.99  112
        2015-09-29 09:24:00  103.18     103.18  781
        ```
        Output data:
        ```
                                   open       close   volume
        2015-09-29 08:24:00+00:00  102.99 ... 102.99  112
        2015-09-29 08:27:00+00:00  102.99     102.99  112
        2015-09-29 09:24:00+00:00  103.18     103.18  781
        ```
        """
        data.index.name = None
        data.index = data.index.tz_localize("utc")
        data = data.rename(columns={"vol": "volume"})
        return data


# #############################################################################
# KibotEquitiesCsvParquetByAssetClient
# #############################################################################


class KibotEquitiesCsvParquetByAssetClient(
    KibotClient, icdc.ImClientReadingOneSymbol
):
    """
    Read a CSV or Parquet by asset file storing data for a single `Kibot`
    equity asset.

    It can read data from local or S3 filesystem as backend.
    """

    def __init__(
        self,
        universe_version: str,
        root_dir: str,
        extension: str,
        asset_class: str,
        unadjusted: Optional[bool],
        *,
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        :param root_dir: either a local root path (e.g., "/app/im") or an S3
            root path (e.g., "s3://alphamatic-data/data") to `Kibot` equity data
        :param extension: file extension, e.g., `csv`, `csv.gz` or `parquet`
        :param asset_class: asset class, e.g "stocks", "etfs", "forex" or "sp_500"
        :param unadjusted: whether asset class prices are unadjusted,
            required for all asset classes except for "forex"
        :param aws_profile: AWS profile name (e.g., `am`)
        """
        super().__init__(universe_version, resample_1min=resample_1min)
        self._root_dir = root_dir
        # Verify that extension does not start with "." and set parameter.
        hdbg.dassert(
            not extension.startswith("."),
            "The extension %s should not start with '.'",
            extension,
        )
        self._extension = extension
        #
        self._asset_class = asset_class
        _asset_classes = ["etfs", "stocks", "forex", "sp_500"]
        hdbg.dassert_in(self._asset_class, _asset_classes)
        #
        if unadjusted is None:
            hdbg.dassert_not_in(
                self._asset_class,
                ["stocks", "etfs", "sp_500"],
                msg="`unadjusted` is a required arg for asset "
                "classes: 'stocks' & 'etfs' & 'sp_500'",
            )
            self._unadjusted = False
        else:
            self._unadjusted = unadjusted
        # Set s3fs parameter value if aws profile parameter is specified.
        if aws_profile:
            self._s3fs = hs3.get_s3fs(aws_profile)

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
        # Split full symbol into exchange and trade symbol.
        exchange_id, trade_symbol = ivcu.parse_full_symbol(full_symbol)
        hdbg.dassert_eq(exchange_id, "kibot")
        # Get absolute file path for a file with equity data.
        file_path = self._get_file_path(trade_symbol)
        _LOG.info(
            "Reading data for `Kibot`, asset class='%s', trade symbol='%s'"
            "unadjusted='%s' from file='%s'...",
            self._asset_class,
            trade_symbol,
            self._unadjusted,
            file_path,
        )
        if hs3.is_s3_path(file_path):
            # Add s3fs argument to kwargs.
            kwargs["s3fs"] = self._s3fs
        # Read data.
        # TODO(Nikola): parquet?
        if self._extension == "pq":
            # Initialize list of filters.
            filters = []
            # Add filtering by start and/or end timestamp if specified.
            # Timezone info is dropped since input data does not have it.
            if start_ts:
                filters.append(("datetime", ">=", start_ts.tz_localize(None)))
            if end_ts:
                filters.append(("datetime", "<=", end_ts.tz_localize(None)))
            if filters:
                # Add filters to kwargs if any were set.
                kwargs["filters"] = filters
            # Add columns to read to kwargs.
            kwargs["columns"] = ["open", "high", "low", "close", "vol"]
            # Load and normalize data.
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_parquet_to_df(stream, **kwargs)
            data = self._apply_kibot_parquet_normalization(data)
        elif self._extension in ["csv", "csv.gz"]:
            # Avoid using the 1st data row as columns and set column names.
            kwargs["header"] = None
            kwargs["names"] = [
                "date",
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
            # Load and normalize data.
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_csv_to_df(stream, **kwargs)
            data = self._apply_kibot_csv_normalization(data)
            # Filter by dates if specified.
            if start_ts:
                data = data[data.index >= start_ts]
            if end_ts:
                data = data[data.index <= end_ts]
        else:
            raise ValueError(
                f"Unsupported extension {self._extension}. "
                f"Supported extensions are: `pq`, `csv`, `csv.gz`"
            )
        return data

    def _get_file_path(
        self,
        trade_symbol: str,
    ) -> str:
        """
        Get the absolute path to a file with `Kibot` equity data.

        The file path is constructed in the following way:
        `<root_dir>/kibot/<pq_subdir>/<subdir>/<trade_symbol>.<extension>`

        E.g., "s3://alphamatic-data/data/kibot/all_stocks_1min/HD.csv.gz"
        """
        # Get absolute file path.
        file_name = ".".join([trade_symbol, self._extension])
        subdir = self._get_subdir_name()
        pq_subdir = ""
        # TODO(Nikola): parquet?
        if self._extension == "pq":
            pq_subdir = "pq"
        file_path = os.path.join(
            self._root_dir,
            self._vendor,
            pq_subdir,
            subdir,
            file_name,
        )
        return file_path

    def _get_subdir_name(self) -> str:
        """
        Get subdir name where `Kibot` data is stored.

        E.g., "all_stocks_unadjusted_1min"
        """
        _asset_class_prefix_mapping = {
            "etfs": "all_etfs",
            "stocks": "all_stocks",
            "forex": "all_forex_pairs",
            "sp_500": "sp_500",
        }
        subdir_name = _asset_class_prefix_mapping[self._asset_class]
        if self._unadjusted:
            subdir_name = "_".join([subdir_name, "unadjusted"])
        subdir_name = "_".join([subdir_name, "1min"])
        return subdir_name


# #############################################################################
# KibotFuturesCsvParquetByAssetClient
# #############################################################################


class KibotFuturesCsvParquetByAssetClient(
    KibotClient, icdc.ImClientReadingOneSymbol
):
    """
    Read a CSV or Parquet file storing data for a single `Kibot` futures asset.

    It can read data from local or S3 filesystem as backend.
    """

    def __init__(
        self,
        universe_version: str,
        root_dir: str,
        extension: str,
        contract_type: str,
        *,
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        :param root_dir: either a local root path (e.g., "/app/im") or an S3
            root path (e.g., "s3://alphamatic-data/data") to `Kibot` futures data
        :param extension: file extension, e.g., `csv`, `csv.gz` or `parquet`
        :param contract_type: futures contract type (e.g., "continuous", "expiry")
        :param aws_profile: AWS profile name (e.g., `am`)
        """
        super().__init__(universe_version, resample_1min=resample_1min)
        self._root_dir = root_dir
        # Verify that extension does not start with "." and set parameter.
        hdbg.dassert(
            not extension.startswith("."),
            "The extension %s should not start with '.'",
            extension,
        )
        self._extension = extension
        #
        self._contract_type = contract_type
        _contract_types = ["continuous", "expiry"]
        hdbg.dassert_in(self._contract_type, _contract_types)
        #
        # Set s3fs parameter value if aws profile parameter is specified.
        if aws_profile:
            self._s3fs = hs3.get_s3fs(aws_profile)

    # TODO(Grisha): @Dan move to a separate class under `metadata` dir.
    def get_metadata(self, **read_csv_kwargs: Any) -> pd.DataFrame:
        # pylint: disable=line-too-long
        """
        See description in the parent class.

        Metadata snippet:

        ```
               Symbol                                            Link                       Description
        0          JY  http://api.kibot.com/?action=download&link=...  CONTINUOUS JAPANESE YEN CONTRACT
        1       JYF18  http://api.kibot.com/?action=download&link=...         JAPANESE YEN JANUARY 2018
        2       JYF19  http://api.kibot.com/?action=download&link=...         JAPANESE YEN JANUARY 2019
        ```
        """
        # pylint: disable=line-too-long
        # Set metadata file path and columns to load.
        metadata_dir = "kibot/metadata"
        file_name = "All_Futures_Contracts_1min.csv.gz"
        file_path = os.path.join(self._root_dir, metadata_dir, file_name)
        columns = ["Symbol", "Link", "Description"]
        # Add arguments to kwargs.
        read_csv_kwargs["usecols"] = columns
        if hs3.is_s3_path(file_path):
            read_csv_kwargs["s3fs"] = self._s3fs
        # Read metadata.
        stream, kwargs = hs3.get_local_or_s3_stream(file_path, **read_csv_kwargs)
        df = hpandas.read_csv_to_df(stream, **kwargs)
        return df

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
        # Split full symbol into exchange and trade symbol.
        exchange_id, trade_symbol = ivcu.parse_full_symbol(full_symbol)
        hdbg.dassert_eq(exchange_id, "kibot")
        # Get absolute file path for a file with futures data.
        file_path = self._get_file_path(trade_symbol)
        _LOG.info(
            "Reading data for `Kibot` futures, trade symbol='%s', "
            "contract type='%s' from file='%s'...",
            trade_symbol,
            self._contract_type,
            file_path,
        )
        if hs3.is_s3_path(file_path):
            # Add s3fs argument to kwargs.
            kwargs["s3fs"] = self._s3fs
        # Read data.
        # TODO(Nikola): parquet?
        if self._extension == "pq":
            # Initialize list of filters.
            filters = []
            # Add filtering by start and/or end timestamp if specified.
            # Timezone info is dropped since input data does not have it.
            if start_ts:
                filters.append(("datetime", ">=", start_ts.tz_localize(None)))
            if end_ts:
                filters.append(("datetime", "<=", end_ts.tz_localize(None)))
            if filters:
                # Add filters to kwargs if any were set.
                kwargs["filters"] = filters
            # Add columns to read to kwargs.
            kwargs["columns"] = ["open", "high", "low", "close", "vol"]
            # Load and normalize data.
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_parquet_to_df(stream, **kwargs)
            data = self._apply_kibot_parquet_normalization(data)
        elif self._extension in ["csv", "csv.gz"]:
            # Avoid using the 1st data row as columns and set column names.
            kwargs["header"] = None
            kwargs["names"] = [
                "date",
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
            # Load and normalize data.
            stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
            data = hpandas.read_csv_to_df(stream, **kwargs)
            data = self._apply_kibot_csv_normalization(data)
            # Filter by dates if specified.
            if start_ts:
                data = data[data.index >= start_ts]
            if end_ts:
                data = data[data.index <= end_ts]
        else:
            raise ValueError(
                f"Unsupported extension {self._extension}. "
                f"Supported extensions are: `pq`, `csv`, `csv.gz`"
            )
        return data

    def _get_file_path(self, trade_symbol: str) -> str:
        """
        Get the absolute path to a file with `Kibot` futures data.

        The file path is constructed in the following way:
        `<root_dir>/kibot/<pq_subdir>/<subdir>/<trade_symbol>.<extension>`

        E.g., "s3://alphamatic-data/data/kibot/pq/All_Futures_Contracts_1min/ZI.pq"
        """
        # Get absolute file path.
        file_name = ".".join([trade_symbol, self._extension])
        subdir = self._get_subdir_name()
        pq_subdir = ""
        # TODO(Nikola): parquet?
        if self._extension == "pq":
            pq_subdir = "pq"
            # Capitalize parts of subdir name for Parquet files for futures.
            subdir = "_".join([e.capitalize() for e in subdir.split("_")])
        file_path = os.path.join(
            self._root_dir,
            self._vendor,
            pq_subdir,
            subdir,
            file_name,
        )
        return file_path

    def _get_subdir_name(self) -> str:
        """
        Get subdir name where `Kibot` data is stored.

        E.g., "all_futures_continuous_contracts_1min"
        """
        subdir_name = "all_futures"
        if self._contract_type == "continuous":
            subdir_name = "_".join([subdir_name, "continuous"])
        subdir_name = "_".join([subdir_name, "contracts", "1min"])
        return subdir_name
