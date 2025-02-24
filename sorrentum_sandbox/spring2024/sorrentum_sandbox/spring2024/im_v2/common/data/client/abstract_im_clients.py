"""
Import as:

import im_v2.common.data.client.abstract_im_clients as imvcdcaimcl
"""

import abc
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import core.finance.bid_ask as cfibiask
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)

# #############################################################################
# ImClient
# #############################################################################

# TODO(gp): @Grisha the output of ImClient should be in the form of
#  `start_timestamp`, `end_timestamp`, and `knowledge_timestamp` since these
#  depend on the specific data source.


class ImClient(abc.ABC, hobject.PrintableMixin):
    """
    Retrieve market data for different vendors and backends.

    The data in output of a class derived from `ImClient` is normalized so that:
    - the index:
      - is the end of the sampling interval
      - is called `timestamp`
      - is a tz-aware timestamp in UTC
    - the data:
      - is resampled on a one-minute grid and filled with NaN values
      - is sorted by index and `full_symbol`
      - is guaranteed to have no duplicates
      - belongs to intervals like [a, b]
      - has a `full_symbol` column with a string representing the canonical name
        of the instrument

    E.g.,
    ```
                                    full_symbol     close     volume
                    timestamp
    2021-07-26 13:42:00+00:00  binance:BTC_USDT  47063.51  29.403690
    2021-07-26 13:43:00+00:00  binance:BTC_USDT  46946.30  58.246946
    2021-07-26 13:44:00+00:00  binance:BTC_USDT  46895.39  81.264098
    ```
    """

    # TODO(Grisha): use `*args` and `**kwargs` in the child classes to specify the
    # base class's params.
    def __init__(
        self,
        vendor: str,
        universe_version: Optional[str],
        *,
        full_symbol_col_name: Optional[str] = None,
        timestamp_col_name: str = "timestamp",
        resample_1min: bool = False,
    ) -> None:
        """
        Constructor.

        :param vendor: data provider
        :param universe_version: version of universe file
        :param resample_1min: whether to resample data to 1 minute or
            not
        :param full_symbol_col_name: the name of the column storing the
            symbol name. It can be overridden by other methods
        :param timestamp_col_name: the name of the column storing
            timestamp
        """
        _LOG.debug(
            hprint.to_str(
                "vendor universe_version resample_1min full_symbol_col_name "
                "timestamp_col_name"
            )
        )
        hdbg.dassert_isinstance(vendor, str)
        self._vendor = vendor
        #
        if universe_version is not None:
            hdbg.dassert_isinstance(universe_version, str)
        self._universe_version = universe_version
        #
        hdbg.dassert_isinstance(resample_1min, bool)
        self._resample_1min = resample_1min
        #
        hdbg.dassert_isinstance(timestamp_col_name, str)
        self._timestamp_col_name = timestamp_col_name
        # TODO(gp): This is the name of the column of the asset_id in the data
        #  as it is read by the derived classes (e.g., `igid`, `asset_id`).
        #  We should rename this as "full_symbol" so that all the code downstream
        #  knows how to call it and / or we can add a column_remap.
        if full_symbol_col_name is not None:
            hdbg.dassert_isinstance(full_symbol_col_name, str)
        self._full_symbol_col_name = full_symbol_col_name
        #
        self._asset_id_to_full_symbol_mapping = (
            self._build_asset_id_to_full_symbol_mapping()
        )

    @staticmethod
    @abc.abstractmethod
    def get_metadata() -> pd.DataFrame:
        """
        Return metadata.
        """

    @staticmethod
    def get_asset_ids_from_full_symbols(
        full_symbols: List[ivcu.FullSymbol],
    ) -> List[int]:
        """
        Convert full symbols into asset ids.

        :param full_symbols: assets as full symbols
        :return: assets as numerical ids
        """
        hdbg.dassert_container_type(full_symbols, list, ivcu.FullSymbol)
        numerical_asset_id = [
            ivcu.string_to_numerical_id(full_symbol)
            for full_symbol in full_symbols
        ]
        return numerical_asset_id

    # TODO(gp): Each derived class should call the proper function instead of
    #  delegating to the same function but using vendor to distinguish, since this
    #  couples the code. Replace if-then-else approach with polymorphism.
    def get_universe(self) -> List[ivcu.FullSymbol]:
        """
        Return the entire universe of valid full symbols.
        """
        # For now, we use the `trade` universe for `ImClient` instead of the
        # entire downloadable universe.
        universe_mode = "trade"
        universe = ivcu.get_vendor_universe(
            self._vendor,
            universe_mode,
            version=self._universe_version,
            as_full_symbol=True,
        )
        return universe  # type: ignore[no-any-return]

    def read_data(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        filter_data_mode: str,
        *,
        full_symbol_col_name: Optional[str] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Read data in `[start_ts, end_ts)` for `ivcu.FullSymbol` symbols.

        :param full_symbols: list of full symbols, e.g.
            `['binance::BTC_USDT', 'kucoin::ETH_USDT']`
        :param start_ts: the earliest date timestamp to load data for
            - `None` means start from the beginning of the available data
        :param end_ts: the latest date timestamp to load data for
            - `None` means return data until the end of the available data
        :param columns: columns to return, skipping reading columns that are not
            requested
            - `None` means return all available columns
        :param filter_data_mode: control class behavior with respect to extra
            or missing columns, like in
            `hpandas.check_and_filter_matching_columns()`
        :param full_symbol_col_name: name of the column storing the full
            symbols (e.g., `asset_id`)
        :return: combined data for all the requested symbols
        """
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts columns full_symbol_col_name kwargs"
            )
        )
        # Verify the requested parameters.
        ivcu.dassert_valid_full_symbols(full_symbols)
        # Check the date range.
        left_close = True
        right_close = True
        hdateti.dassert_is_valid_interval(
            start_ts, end_ts, left_close, right_close
        )
        # Delegate to the derived classes to retrieve the data.
        full_symbol_col_name = self._get_full_symbol_col_name(
            full_symbol_col_name
        )
        if columns is not None:
            # Check before reading the data.
            hdbg.dassert_container_type(columns, list, str)
            hdbg.dassert_lte(1, len(columns))
        # Read data through the derived class.
        df = self._read_data(
            full_symbols,
            start_ts,
            end_ts,
            columns,
            full_symbol_col_name=full_symbol_col_name,
            **kwargs,
        )
        _LOG.debug(
            hpandas.df_to_str(df, print_shape_info=True, tag="after _read_data")
        )
        # hpandas.dassert_increasing_index(df)
        if "level" in df.columns:
            _LOG.debug(
                "Detected level column and calling transform_bid_ask_long_data_to_wide"
            )
            # Transform bid ask data with multiple order book levels.
            timestamp_col = self._timestamp_col_name
            # The following transformations are needed to unify df format
            # when loading RDS vs. S3 Parquet.
            # E.g. apply "bid_price_close" (RDS) -> "bid_price.close" (S3 parquet)
            # for bid_*, ask_* and log_*, half_* columns.
            rename_value_col = (
                lambda col: ".".join(col.rsplit("_", 1))
                if col.startswith(("bid", "ask", "log", "half"))
                else col
            )
            df = df.rename(columns=rename_value_col)
            # TODO(gp): There should not be reference to bid_ask since this is a
            #  general transformation.
            df = cfibiask.transform_bid_ask_long_data_to_wide(
                df, timestamp_col, final_col_format="level_{0[1]}.{0[0]}"
            )
        # Check that we got what we asked for.
        hdbg.dassert_in(full_symbol_col_name, df.columns)
        loaded_full_symbols = df[full_symbol_col_name].unique().tolist()
        ivcu.dassert_valid_full_symbols(loaded_full_symbols)
        hdbg.dassert_set_eq(
            full_symbols,
            loaded_full_symbols,
            msg="Not all the requested symbols were retrieved",
            # TODO(Grisha): add param `assert_on_missing_asset_ids` that
            # allows to either assert or issues a warning.
            only_warning=True,
        )
        # Rename index.
        df.index.name = self._timestamp_col_name
        # Normalize data for each symbol.
        _LOG.debug("full_symbols=%s", df[full_symbol_col_name].unique())
        dfs = []
        for full_symbol, df_tmp in df.groupby(full_symbol_col_name):
            _LOG.debug("apply_im_normalization: full_symbol=%s", full_symbol)
            df_tmp = self._apply_im_normalizations(
                df_tmp,
                full_symbol_col_name,
                self._resample_1min,
                start_ts,
                end_ts,
            )
            if not df_tmp.empty:
                # Validate data that remained after normalization and append it
                # to the result.
                # TODO(gp): Difference between amp and cmamp.
                self._dassert_output_data_is_valid(
                    df_tmp,
                    full_symbol_col_name,
                    self._resample_1min,
                    start_ts,
                    end_ts,
                    self._timestamp_col_name,
                )
                dfs.append(df_tmp)
            else:
                _LOG.debug("Df for full_symbol=%s is empty", full_symbol)
        hdbg.dassert_lt(0, df.shape[0], "Empty df=\n%s", df)
        df = pd.concat(dfs, axis=0)
        _LOG.debug("After im_normalization: df=\n%s", hpandas.df_to_str(df))
        # Sort by index and `full_symbol_col_name`.
        # There is not a simple way to sort by index and columns in Pandas,
        # so we convert the index into a column, sort, and convert back.
        df = df.reset_index()
        df = df.sort_values(by=[self._timestamp_col_name, full_symbol_col_name])
        df = df.set_index(self._timestamp_col_name, drop=True)
        # The full_symbol should be a string.
        hdbg.dassert_isinstance(df[full_symbol_col_name].values[0], str)
        _LOG.debug("After sorting: df=\n%s", hpandas.df_to_str(df))
        # Check that columns are the required ones.
        # TODO(gp): Difference between amp and cmamp.
        # TODO(gp): This makes a test in E8 fail.
        if False and columns is not None:
            df = hpandas.check_and_filter_matching_columns(
                df, columns, filter_data_mode
            )
        return df

    # /////////////////////////////////////////////////////////////////////////

    def get_start_ts_for_symbol(
        self, full_symbol: ivcu.FullSymbol
    ) -> pd.Timestamp:
        """
        Return the earliest timestamp available for a given `full_symbol`.

        This implementation relies on reading all the data and then
        finding the min. Derived classes can override this method if
        there is a more efficient way to get this information.
        """
        mode = "start"
        return self._get_start_end_ts_for_symbol(full_symbol, mode)

    def get_end_ts_for_symbol(self, full_symbol: ivcu.FullSymbol) -> pd.Timestamp:
        """
        Same as `get_start_ts_for_symbol()`.
        """
        mode = "end"
        return self._get_start_end_ts_for_symbol(full_symbol, mode)

    def get_full_symbols_from_asset_ids(
        self, asset_ids: List[int]
    ) -> List[ivcu.FullSymbol]:
        """
        Convert asset ids into full symbols.

        :param asset_ids: assets ids
        :return: assets as full symbols
        """
        # Check that provided ids are part of the universe.
        hdbg.dassert_is_subset(asset_ids, self._asset_id_to_full_symbol_mapping)
        # Convert ids to full symbols.
        full_symbols = [
            self._asset_id_to_full_symbol_mapping[asset_id]
            for asset_id in asset_ids
        ]
        return full_symbols

    # /////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _apply_im_normalizations(
        df: pd.DataFrame,
        full_symbol_col_name: str,
        resample_1min: bool,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
    ) -> pd.DataFrame:
        """
        Apply normalizations to IM data.
        """
        _LOG.debug(hprint.to_str("full_symbol_col_name start_ts end_ts"))
        # 1) Drop duplicated timestamps.
        use_index = True
        df = hpandas.drop_duplicates(df, use_index)
        # TODO(Grisha): Consider adding "knowledge_timestamp" to every dataset
        # and removing the condition, otherwise some tests fail, see CmTask3630.
        if "knowledge_timestamp" in df.columns:
            duplicate_columns = [full_symbol_col_name]
            # Sort values by "knowledge_timestamp" to keep the latest ones while
            # removing duplicates.
            df = df.sort_values("knowledge_timestamp", ascending=True)
            use_index = True
            df = hpandas.drop_duplicates(
                df,
                use_index,
                column_subset=duplicate_columns,
                keep="last",
            ).sort_index()
        # 2) Trim the data keeping only the data with index in [start_ts, end_ts].
        # Trimming of the data is done because:
        # - some data sources can be only queried at day resolution, so we get
        #   a date range, and then we trim the excess data
        # - we want to guarantee that no derived class returns data outside the
        #   requested interval
        ts_col_name = None
        left_close = True
        right_close = True
        df = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        # 3) Resample index to 1 min frequency if specified.
        if resample_1min:
            df = hpandas.resample_df(df, "T")
            # Fill NaN values appeared after resampling in full symbol column.
            # Combination of full symbol and timestamp is a unique identifier,
            # so full symbol cannot be NaN.
            df[full_symbol_col_name] = df[full_symbol_col_name].bfill()
        # 4) Convert to UTC.
        df.index = df.index.tz_convert("UTC")
        return df

    @staticmethod
    def _dassert_output_data_is_valid(
        df: pd.DataFrame,
        full_symbol_col_name: str,
        resample_1min: bool,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        timestamp_col_name: str,
    ) -> None:
        """
        Verify that the normalized data is valid.
        """
        # TODO(Grisha): consider using `hpandas.dassert_time_indexed_df()`.
        # Check that data is not empty.
        hdbg.dassert_lt(0, df.shape[0])
        # Check that index is `pd.DatetimeIndex`.
        hpandas.dassert_index_is_datetime(df)
        if resample_1min:
            # Check that index is monotonic increasing.
            hpandas.dassert_strictly_increasing_index(df)
            # Verify that index frequency is 1 minute.
            hdbg.dassert_eq(df.index.freq, "T")
        # Check that timezone info is correct.
        expected_tz = ["UTC"]
        # Assume that the first value of an index is representative.
        hdateti.dassert_has_specified_tz(
            df.index[0],
            expected_tz,
        )
        # Check that full symbol column has no NaNs.
        hdbg.dassert(df[full_symbol_col_name].notna().all())
        # Check that there are no duplicates in data by index and full symbol.
        n_duplicated_rows = (
            df.reset_index()
            .duplicated(subset=[timestamp_col_name, full_symbol_col_name])
            .sum()
        )
        hdbg.dassert_eq(
            n_duplicated_rows, 0, msg="There are duplicated rows in the data"
        )
        # Ensure that all the data is in [start_ts, end_ts].
        hdateti.dassert_timestamp_lte(start_ts, df.index.min())
        hdateti.dassert_timestamp_lte(df.index.max(), end_ts)
        if "knowledge_timestamp" in df.columns:
            # Assert that both timestamps have timezone info.
            hdateti.dassert_tz_compatible(
                df["knowledge_timestamp"].iloc[0], df.index[0]
            )
            # Check if data is downloaded after a bar ends. E.g., a bar starts at
            # 20:00:00 (timestamp) and ends at 20:01:00 while knowledge_timestamp
            # is 20:00:40. That means that the data was downloaded before the bar
            # ends, i.e. incomplete data is received.
            mask = df["knowledge_timestamp"] <= (df.index)
            early_data = df.loc[mask]
            if not early_data.empty:
                _LOG.warning(
                    "Data that is downloaded before a bar ends accounts for=%s",
                    hprint.perc(early_data.shape[0], df.shape[0]),
                )

    @staticmethod
    def _split_full_symbols_by_exchanges(
        full_symbols: List[ivcu.FullSymbol],
    ) -> Dict[str, List[ivcu.FullSymbol]]:
        """
        Split full symbols by exchanges.

        :param full_symbols: full symbols, e.g.,
            `[binance::BTC_USDT, kraken::BTC_USDT]`
        :return: full symbols batches split by exchanges, e.g.,
            ```
            {
                "binance": [binance::BTC_USDT],
                "kraken": [kraken::BTC_USDT]
            }```
        """
        # TODO(Grisha): can it be simplified?
        exchange_to_full_symbols = []
        for symbol in full_symbols:
            exchange, _ = ivcu.parse_full_symbol(symbol)
            exchange_to_full_symbols.append((exchange, symbol))
        #
        exchange_to_full_symbols_unique = {}
        for exchange, full_symbol in exchange_to_full_symbols:
            exchange_to_full_symbols_unique.setdefault(exchange, []).append(
                full_symbol
            )
        return exchange_to_full_symbols_unique

    # //////////////////////////////////////////////////////////////////////////

    def _get_full_symbol_col_name(
        self, full_symbol_col_name: Optional[str]
    ) -> str:
        """
        Resolve the name of the `full_symbol_col_name` using the value in the
        ctor and the one passed to the function.
        """
        ret = self._full_symbol_col_name
        if full_symbol_col_name is not None:
            # The function has specified it, so this value overwrites the
            # constructor value.
            hdbg.dassert_isinstance(full_symbol_col_name, str)
            ret = full_symbol_col_name
        else:
            if self._full_symbol_col_name is None:
                # Both constructor and method have not specified the value, so
                # use the default value.
                ret = "full_symbol"
        hdbg.dassert_is_not(
            ret,
            None,
            "No value for 'full_symbol_col_name' was specified: ctor value='%s', method value='%s'",
            self._full_symbol_col_name,
            full_symbol_col_name,
        )
        return ret

    @abc.abstractmethod
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
        ...

    def _build_asset_id_to_full_symbol_mapping(self) -> Dict[int, str]:
        """
        Build asset id to full symbol mapping.
        """
        # Get full symbol universe.
        full_symbol_universe = self.get_universe()
        # Build the mapping.
        asset_id_to_full_symbol_mapping = (
            ivcu.build_numerical_to_string_id_mapping(full_symbol_universe)
        )
        return asset_id_to_full_symbol_mapping  # type: ignore[no-any-return]

    def _get_start_end_ts_for_symbol(
        self, full_symbol: ivcu.FullSymbol, mode: str
    ) -> pd.Timestamp:
        _LOG.debug(hprint.to_str("full_symbol"))
        # Read data for the entire period of time available.
        start_timestamp = None
        end_timestamp = None
        # Use only `self._full_symbol_col_name` after CmTask1588 is fixed.
        columns = None
        filter_data_mode = "assert"
        data = self.read_data(
            [full_symbol],
            start_timestamp,
            end_timestamp,
            columns,
            filter_data_mode,
        )
        # Assume that the timestamp is always stored as index.
        if mode == "start":
            timestamp = data.index.min()
        elif mode == "end":
            timestamp = data.index.max()
        else:
            raise ValueError("Invalid mode='%s'" % mode)
        #
        hdbg.dassert_isinstance(timestamp, pd.Timestamp)
        hdateti.dassert_has_specified_tz(timestamp, ["UTC"])
        return timestamp


# #############################################################################
# ImClientReadingOneSymbol
# #############################################################################


# TODO(Dan): Implement usage of `columns` parameter in descendant classes.
class ImClientReadingOneSymbol(ImClient, abc.ABC):
    """
    IM client for a backend that can only read one symbol at a time.

    E.g., CSV with data organized by-asset.
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
        Same as the method in the parent class.
        """
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts columns full_symbol_col_name kwargs"
            )
        )
        hdbg.dassert_container_type(full_symbols, list, str)
        # Check timestamp interval.
        left_close = True
        right_close = True
        hdateti.dassert_is_valid_interval(
            start_ts,
            end_ts,
            left_close=left_close,
            right_close=right_close,
        )
        # Load the data for each symbol.
        full_symbol_col_name = self._get_full_symbol_col_name(
            full_symbol_col_name
        )
        full_symbol_to_df = {}
        for full_symbol in sorted(full_symbols):
            df = self._read_data_for_one_symbol(
                full_symbol,
                start_ts,
                end_ts,
                **kwargs,
            )
            # Insert column with full symbol into the result dataframe.
            hdbg.dassert_is_not(full_symbol_col_name, df.columns)
            df.insert(0, full_symbol_col_name, full_symbol)
            # Add data to the result dict.
            full_symbol_to_df[full_symbol] = df
        # Combine results dict in a dataframe.
        df = pd.concat(full_symbol_to_df.values())
        # We rely on the parent class to sort.
        return df

    @abc.abstractmethod
    def _read_data_for_one_symbol(
        self,
        full_symbol: ivcu.FullSymbol,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Read data for a single symbol in [start_ts, end_ts].

        Parameters have the same meaning as in `read_data()`.
        """
        ...


# #############################################################################
# ImClientReadingMultipleSymbols
# #############################################################################


class ImClientReadingMultipleSymbols(ImClient, abc.ABC):
    """
    IM client for backend that can read multiple symbols at the same time.

    E.g., Parquet by-date or by-asset files allow to read data for
    multiple assets stored in the same file.
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
        Same as the parent class.
        """
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts columns full_symbol_col_name kwargs"
            )
        )
        full_symbol_col_name = self._get_full_symbol_col_name(
            full_symbol_col_name
        )
        df = self._read_data_for_multiple_symbols(
            full_symbols,
            start_ts,
            end_ts,
            columns,
            full_symbol_col_name,
            **kwargs,
        )
        return df

    @abc.abstractmethod
    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        full_symbol_col_name: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        ...
