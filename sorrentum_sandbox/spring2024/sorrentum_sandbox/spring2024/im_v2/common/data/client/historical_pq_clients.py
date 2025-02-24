"""
Import as:

import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
"""

import abc
import collections
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.common.data.client.abstract_im_clients as imvcdcaimcl
import im_v2.common.data_snapshot as icdds
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# #############################################################################
# HistoricalPqByTileClient
# #############################################################################


# TODO(Dan): Consolidate HistoricalPqByTileClients CmTask #1961.
class HistoricalPqByTileClient(
    imvcdcaimcl.ImClientReadingMultipleSymbols, abc.ABC
):
    """
    Read historical data stored as Parquet by-tile.

    For base implementation Parquet dataset should be partitioned by
    full symbol.
    """

    def __init__(
        self,
        # TODO(gp): We could use *args, **kwargs as params for ImClient,
        # same for the child classes.
        vendor: str,
        # The version is not strictly needed for this class, but it is used by
        # the child classes, e.g., by `CcxtHistoricalPqByTileClient`.
        universe_version: str,
        root_dir: str,
        partition_mode: str,
        infer_exchange_id: bool,
        *,
        aws_profile: Optional[str] = None,
        full_symbol_col_name: Optional[str] = None,
        resample_1min: bool = False,
    ):
        """
        Constructor.

        See the parent class for parameters description.

        :param root_dir: root path to the tiled Parquet data
            - either local, e.g., "/app/im"
            - or on S3, e.g., "s3://<ck-data>/reorg/historical.manual.pq"
        :param partition_mode: how the data is partitioned, e.g.,
            "by_year_month"
        :param infer_exchange_id: use the last part of a dir to indicate
            the exchange originating the data. This allows to merging
            multiple Parquet files on exchange. See CmTask #1533 "Add
            exchange to the ParquetDataset partition".
        :param aws_profile: AWS profile, e.g., "ck"
        """
        super().__init__(
            vendor,
            universe_version,
            full_symbol_col_name=full_symbol_col_name,
            resample_1min=resample_1min,
        )
        hdbg.dassert_isinstance(root_dir, str)
        self._root_dir = root_dir
        self._infer_exchange_id = infer_exchange_id
        self._partition_mode = partition_mode
        self._aws_profile = aws_profile

    @staticmethod
    def get_metadata() -> pd.DataFrame:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    # TODO(Grisha): factor out the column names in the child classes, see `CCXT`.
    @staticmethod
    def _get_columns_for_query(
        full_symbol_col_name: str, columns: Optional[List[str]]
    ) -> Optional[List[str]]:
        """
        Get columns for Parquet data query.

        For base implementation the queries columns are equal to the
        passed ones.
        """
        if (columns is not None) and (full_symbol_col_name not in columns):
            # In order not to modify the input.
            query_columns = columns.copy()
            # Data is partitioned by full symbols so the column is mandatory.
            query_columns.append(full_symbol_col_name)
        else:
            query_columns = columns
        return query_columns

    # TODO(Grisha): factor out the common code in the child classes, see CmTask #1696
    # "Refactor HistoricalPqByTileClient and its child classes".
    @staticmethod
    def _apply_transformations(
        df: pd.DataFrame,
        full_symbol_col_name: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Apply transformations to loaded data.
        """
        # The asset data can come back from Parquet as:
        # ```
        # Categories(540, int64): [10025, 10036, 10040, 10045, ..., 82711, 82939,
        #                         83317, 89970]
        # ```
        # which confuses `df.groupby()`, so we force that column to str.
        df[full_symbol_col_name] = df[full_symbol_col_name].astype(str)
        return df

    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        full_symbol_col_name: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        See description in the parent class.
        """
        hdbg.dassert_container_type(full_symbols, list, str)
        # Implement logging and add it to kwargs.
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts columns full_symbol_col_name"
            )
        )
        kwargs["log_level"] = logging.INFO
        # Get columns for query and add them to kwargs.
        kwargs["columns"] = self._get_columns_for_query(
            full_symbol_col_name, columns
        )
        # Add AWS profile to kwargs.
        kwargs["aws_profile"] = self._aws_profile
        # Build root dirs to the data and Parquet filtering condition.
        root_dir_symbol_filter_dict = self._get_root_dirs_symbol_filters(
            full_symbols, full_symbol_col_name
        )
        #
        res_df_list = []
        for root_dir, symbol_filter in root_dir_symbol_filter_dict.items():
            # Build list of filters for a query and add them to kwargs.
            filters = hparque.get_parquet_filters_from_timestamp_interval(
                self._partition_mode,
                start_ts,
                end_ts,
                additional_filters=[symbol_filter],
            )
            kwargs["filters"] = filters
            # Read Parquet data from a root dir.
            root_dir_df = hparque.from_parquet(root_dir, **kwargs)
            # TODO(Grisha): "Handle missing tiles" CmTask #1775.
            # hdbg.dassert_lte(
            #     1,
            #     root_dir_df.shape[0],
            #     "Can't find data for root_dir='%s' and symbol_filter='%s'",
            #     root_dir,
            #     symbol_filter,
            # )
            # Convert index to datetime.
            root_dir_df.index = pd.to_datetime(root_dir_df.index)
            # TODO(gp): IgHistoricalPqByTileTaqBarClient used a ctor param to rename a column.
            #  Not sure if this is still needed.
            #        # Rename column storing `full_symbols`, if needed.
            #        hdbg.dassert_in(self._full_symbol_col_name, df.columns)
            #        if full_symbol_col_name != self._full_symbol_col_name:
            #            hdbg.dassert_not_in(full_symbol_col_name, df.columns)
            #            df.rename(
            #                columns={self._full_symbol_col_name: full_symbol_col_name},
            #                inplace=True,
            #            )
            transformation_kwargs: Dict = {}
            if self._infer_exchange_id:
                # Infer `exchange_id` position in a file path.
                s3_bucket_path = hs3.get_s3_bucket_path(self._aws_profile)
                reorg_root_dir = os.path.join(s3_bucket_path, "reorg")
                daily_staged_reorg_dir = os.path.join(
                    reorg_root_dir, "daily_staged.airflow.pq"
                )
                if root_dir == daily_staged_reorg_dir:
                    # E.g. "binance" from
                    # "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask-futures/crypto_chassis.downloaded_1min/binance/".
                    exchange_loc = -1
                else:
                    # E.g. "binance" from
                    # "s3://cryptokaizen-data/v3/periodic_daily/airflow/downloaded_1min/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0/".
                    exchange_loc = -2
                # Infer `exchange_id` from a file path if it is not present in data.
                # E.g., `s3://.../latest/ohlcv/ccxt/binance` -> `binance`.
                transformation_kwargs["exchange_id"] = root_dir.split("/")[
                    exchange_loc
                ]
            # Transform data.
            root_dir_df = self._apply_transformations(
                root_dir_df, full_symbol_col_name, **transformation_kwargs
            )
            # The columns are used just to partition the data but these columns
            # are not included in the `ImClient` output.
            current_columns = root_dir_df.columns.to_list()
            month_column = "month"
            if month_column in current_columns:
                root_dir_df = root_dir_df.drop(month_column, axis=1)
            year_column = "year"
            if year_column in current_columns:
                root_dir_df = root_dir_df.drop(year_column, axis=1)
            # Column with name "timestamp" that stores epochs remains in most
            # vendors data if no column filtering was done. Drop it since it
            # replicates data from index and has the same name as index column
            # which causes a break when we try to reset it.
            timestamp_column = "timestamp"
            if timestamp_column in current_columns:
                root_dir_df = root_dir_df.drop(timestamp_column, axis=1)
            #
            res_df_list.append(root_dir_df)
        # Combine data from all root dirs into a single DataFrame.
        res_df = pd.concat(res_df_list, axis=0)
        return res_df

    # TODO(Grisha): try to unify child classes with the base class, see CmTask #1696
    # "Refactor HistoricalPqByTileClient and its child classes".
    # TODO(Grisha): remove the hack that allows to read data for multiple exchanges in
    # the child classes, see CmTask #1533 "Add exchange to the ParquetDataset partition".
    # TODO(Grisha): param `full_symbol_col_name` is not used in the child classes,
    # see CmTask #1696 "Refactor HistoricalPqByTileClient and its child classes".
    def _get_root_dirs_symbol_filters(
        self, full_symbols: List[ivcu.FullSymbol], full_symbol_col_name: str
    ) -> Dict[str, hparque.ParquetFilter]:
        """
        Get dict with root dir to data as keys and corresponding symbol filters
        as values.

        Since in the base class filtering is done by full symbols, the root dir
        will be common for all of them so the output has only one key-value pair.

        E.g.,
        ```
        {
            "s3://.../20210924/ohlcv/ccxt/binance": (
                "full_symbol", "in", ["binance::ADA_USDT", "ftx::BTC_USDT"]
            )
        }
        ```
        """
        # The root dir of the data is the one passed from the constructor.
        root_dir = self._root_dir
        # Add a filter on full symbols.
        symbol_filter = (full_symbol_col_name, "in", full_symbols)
        # Build a dict.
        res_dict = {root_dir: symbol_filter}
        return res_dict


# #############################################################################
# HistoricalPqByCurrencyPairTileClient
# #############################################################################


# TODO(gp): CurrencyPair -> Asset
class HistoricalPqByCurrencyPairTileClient(HistoricalPqByTileClient):
    """
    Read historical data for vendor specific assets stored as Parquet dataset.

    Parquet dataset should be partitioned by currency pair.
    """

    # TODO(Grisha): make data_version-specific parameters optional,
    # e.g., `data_snapshot` is applicable only for `v2`, `download_mode`,
    # `downloading_entity` are applicable only for `v3`.
    def __init__(
        self,
        vendor: str,
        universe_version: str,
        root_dir: str,
        partition_mode: str,
        # TODO(Sonya): Consider moving the `dataset` param to the base class.
        dataset: str,
        contract_type: str,
        data_snapshot: str,
        *,
        download_mode: str = "periodic_daily",
        downloading_entity: str = "airflow",
        # TODO(Grisha): -> `data_version`.
        version: str = "",
        # TODO(Dan): Use `None` default value instead of an empty string.
        download_universe_version: str = "",
        tag: str = "",
        aws_profile: Optional[str] = None,
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        See the parent class for parameters description.

        :param dataset: the dataset type, e.g. "ohlcv", "bid_ask"
        :param data_snapshot: same format used in `get_data_snapshot()`
        :param download_mode: data download mode
        :param downloading_entity: entity used to download data
        :param version: data version
        :param download_universe_version: version of download universe
            file
        :param tag: resample type, e.g., "resampled_1min",
            "downloaded_1sec"
        """
        infer_exchange_id = True
        super().__init__(
            vendor,
            universe_version,
            root_dir,
            partition_mode,
            infer_exchange_id,
            aws_profile=aws_profile,
            resample_1min=resample_1min,
        )
        hdbg.dassert_in(
            dataset, ["bid_ask", "ohlcv"], f"Invalid dataset type='{dataset}'"
        )
        # TODO(Grisha): @Dan `dataset` -> `data_type`.
        self._dataset = dataset
        hdbg.dassert_in(
            contract_type,
            ["spot", "futures"],
            f"Invalid dataset type='{contract_type}'",
        )
        # TODO(Grisha): @Dan `contract_type` -> `asset_type`.
        self._contract_type = contract_type
        data_snapshot = icdds.get_data_snapshot(
            root_dir, data_snapshot, aws_profile
        )
        self._data_snapshot = data_snapshot
        hdbg.dassert_in(
            tag, ["", "downloaded_1min", "resampled_1min", "downloaded_1sec"]
        )
        self._download_mode = download_mode
        self._downloading_entity = downloading_entity
        self._version = version
        self._download_universe_version = download_universe_version
        # TODO(Grisha): @Dan `tag` -> `action_tag`.
        self._tag = tag
        self._data_format = "parquet"

    @staticmethod
    def get_metadata() -> pd.DataFrame:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _get_columns_for_query(
        full_symbol_col_name: str, columns: Optional[List[str]]
    ) -> Optional[List[str]]:
        """
        See description in the parent class.
        """
        if columns is not None:
            # In order not to modify the input.
            query_columns = columns.copy()
            # Data is partitioned by currency pairs so the column is mandatory.
            query_columns.append("currency_pair")
            # Full symbol column is added after we read data, so skipping here.
            if full_symbol_col_name in query_columns:
                query_columns.remove(full_symbol_col_name)
        else:
            query_columns = columns
        return query_columns

    @staticmethod
    def _apply_transformations(
        df: pd.DataFrame, full_symbol_col_name: str, **kwargs: Any
    ) -> pd.DataFrame:
        """
        See description in the parent class.
        """
        if "exchange_id" in kwargs:
            df["exchange_id"] = kwargs["exchange_id"]
        # Convert to string, see the parent class for details.
        df["exchange_id"] = df["exchange_id"].astype(str)
        df["currency_pair"] = df["currency_pair"].astype(str)
        # Add full symbol column at first position in data.
        full_symbol_col = ivcu.build_full_symbol(
            df["exchange_id"], df["currency_pair"]
        )
        if df.columns[0] != full_symbol_col_name:
            # Insert if it doesn't already exist.
            df.insert(0, full_symbol_col_name, full_symbol_col)
        else:
            # Replace the values to ensure the correct data.
            df[full_symbol_col_name] = full_symbol_col.values
        # The columns are used just to partition the data but these columns
        # are not included in the `ImClient` output.
        df = df.drop(["exchange_id", "currency_pair"], axis=1)
        # Round up float values in case values in raw data are rounded up incorrectly
        # when being read from a file.
        df = df.round(8)
        return df

    def _get_root_dirs_symbol_filters(
        self, full_symbols: List[ivcu.FullSymbol], full_symbol_col_name: str
    ) -> Dict[str, hparque.ParquetFilter]:
        """
        Build a dict with exchange root dirs of the vendor data as keys and
        filtering conditions on corresponding currency pairs as values.

        E.g.,
        ```
        {
            "s3://.../20210924/ohlcv/ccxt/binance": (
                "currency_pair", "in", ["ADA_USDT", "BTC_USDT"]
            ),
            "s3://.../20210924/ohlcv/ccxt/coinbase": (
                "currency_pair", "in", ["BTC_USDT", "ETH_USDT"]
            ),
        }
        ```
        """
        filter_root_dir = self._get_filter_root_dir()
        # Split full symbols into exchange id and currency pair tuples, e.g.,
        # [('binance', 'ADA_USDT'),
        # ('coinbase', 'BTC_USDT')].
        full_symbol_tuples = [
            ivcu.parse_full_symbol(full_symbol) for full_symbol in full_symbols
        ]
        # Store full symbols as a dictionary, e.g.,
        # `{exchange_id1: [currency_pair1, currency_pair2]}`.
        # `Defaultdict` provides a default value for the key that does not
        # exists that prevents from getting `KeyError`.
        symbol_dict = collections.defaultdict(list)
        for exchange_id, *currency_pair in full_symbol_tuples:
            symbol_dict[exchange_id].extend(currency_pair)
        # Build a dict with exchange root dirs as keys and Parquet filters by
        # the corresponding currency pairs as values.
        root_dir_symbol_filter_dict = {
            os.path.join(filter_root_dir, exchange_id, self._version): (
                "currency_pair",
                "in",
                currency_pairs,
            )
            for exchange_id, currency_pairs in symbol_dict.items()
        }
        return root_dir_symbol_filter_dict

    def _get_filter_root_dir(self) -> str:
        """
        Build a root dir to files to filter.

        Examples:
        - reorg dir: 's3://cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask-futures/crypto_chassis.downloaded_1min/binance/'
        - v3 dir: 's3://cryptokaizen-data/v3/periodic_daily/airflow/downloaded_1min/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0/'
        """
        # Set condition for reorg and unit test subdirs approach.
        s3_bucket_path = hs3.get_s3_bucket_path(self._aws_profile)
        s3_unit_test_bucket_path = henv.execute_repo_config_code(
            "get_unit_test_bucket_path()"
        )
        reorg_root_dir = os.path.join(s3_bucket_path, "reorg")
        # We check `s3://cryptokaizen-unit-test/outcomes/` because most of the tests
        # use reorg dir pattern path `s3://cryptokaizen-data/reorg`,
        # while `Mock2` tests use v3 dir pattern `s3://cryptokaizen-unit-test/v3/bulk`.
        unit_test_s3_dir = os.path.join(s3_unit_test_bucket_path, "outcomes")
        is_reorg_dir = self._root_dir.startswith(reorg_root_dir)
        is_unit_test_s3_dir = self._root_dir.startswith(unit_test_s3_dir)
        if is_reorg_dir or is_unit_test_s3_dir:
            filter_root_dir = self._get_filter_root_dir_reorg()
        else:
            filter_root_dir = self._get_filter_root_dir_v3()
        return filter_root_dir

    def _get_filter_root_dir_reorg(self) -> str:
        """
        Build a reorg filter root dir.
        """
        vendor = self._vendor.lower()
        contract_type_separator = "-"
        contract_type = self._contract_type
        if contract_type == "spot":
            # E.g., `s3://.../20210924/ohlcv/ccxt/coinbase`.
            contract_type_separator = ""
            contract_type = ""
        # E.g., `ohlcv-futures` for futures.
        dataset = "".join([self._dataset, contract_type_separator, contract_type])
        # E.g., `crypto_chassis.resampled_1min` for resampled data.
        if self._tag:
            vendor = ".".join([vendor, self._tag])
        filter_root_dir = os.path.join(
            self._root_dir,
            self._data_snapshot,
            dataset,
            vendor,
        )
        return filter_root_dir

    def _get_filter_root_dir_v3(self) -> str:
        """
        Build a v3 filter root dir.
        """
        hdbg.dassert_is_not(self._download_universe_version, "")
        filter_root_dir = os.path.join(
            self._root_dir,
            self._download_mode,
            self._downloading_entity,
            self._tag,
            self._data_format,
            self._dataset,
            self._contract_type,
            self._download_universe_version,
            self._vendor.lower(),
        )
        return filter_root_dir


# #############################################################################
# HistoricalPqByDateClient
# #############################################################################


# TODO(gp): This is very similar to HistoricalPqByTile. Can we unify?
class HistoricalPqByDateClient(
    imvcdcaimcl.ImClientReadingMultipleSymbols, abc.ABC
):
    """
    Read historical data stored as Parquet by-date.
    """

    # TODO(gp): Do not pass a read_func but use an abstract method.
    def __init__(
        self,
        vendor: str,
        read_func,
        *,
        full_symbol_col_name: Optional[str] = None,
        resample_1min: bool = False,
    ):
        universe_version = None
        super().__init__(
            vendor,
            universe_version,
            full_symbol_col_name=full_symbol_col_name,
            resample_1min=resample_1min,
        )
        self._read_func = read_func

    # ///////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ///////////////////////////////////////////////////////////////////////////

    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        full_symbol_col_name: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Same as abstract method.
        """
        # The data is stored by date so we need to convert the timestamps into
        # dates and then trim the excess.
        # Compute the start_date.
        if start_ts is not None:
            start_date = start_ts.date()
        else:
            start_date = None
        # Compute the end_date.
        if end_ts is not None:
            end_date = end_ts.date()
        else:
            end_date = None
        # Get the data for [start_date, end_date].
        # TODO(gp): Use an abstract_method.
        # TODO(gp): This should not be hardwired but passed.
        asset_id_name = self._full_symbol_col_name
        hdbg.dassert_is_not(asset_id_name, None)
        normalize = True
        tz_zone = "UTC"
        df = self._read_func(
            # TODO(gp): These are int.
            full_symbols,
            asset_id_name,
            start_date,
            end_date,
            columns,
            normalize,
            tz_zone,
            kwargs["root_data_dir"],
            kwargs["aws_profile"],
        )
        # Convert to datetime.
        df.index = pd.to_datetime(df.index)
        # Rename column storing the asset ids.
        hdbg.dassert_in(self._full_symbol_col_name, df.columns)
        df[self._full_symbol_col_name] = df[self._full_symbol_col_name].astype(
            str
        )
        if full_symbol_col_name != self._full_symbol_col_name:
            hdbg.dassert_not_in(full_symbol_col_name, df.columns)
            df.rename(
                columns={self._full_symbol_col_name: full_symbol_col_name},
                inplace=True,
            )
        # Since we have normalized the data, the index is a timestamp and we can
        # trim the data with index in [start_ts, end_ts] to remove the excess
        # from filtering in terms of days.
        ts_col_name = None
        left_close = True
        right_close = True
        df = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        return df
