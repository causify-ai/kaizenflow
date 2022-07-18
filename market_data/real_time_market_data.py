"""
Import as:

import market_data.real_time_market_data as mdrtmada
"""

import logging
from typing import Any, List, Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu
import market_data.abstract_market_data as mdabmada

_LOG = logging.getLogger(__name__)


_LOG.verb_debug = hprint.install_log_verb_debug(_LOG, verbose=False)


# #############################################################################
# RealTimeMarketData
# #############################################################################

# TODO(gp): This should be pushed to the IM
class RealTimeMarketData(mdabmada.MarketData):
    """
    Implement an interface to a real-time SQL database with 1-minute bar data.
    """

    def __init__(
        self,
        db_connection,
        table_name: str,
        where_clause: Optional[str],
        valid_id: Any,
        # Params from abstract `MarketData`.
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Constructor.

        :param table_name: the table to use to get the data
        :param where_clause: an SQL where clause
            - E.g., `WHERE ...=... AND ...=...`
        """
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.connection = db_connection
        self._table_name = table_name
        self._where_clause = where_clause
        self._valid_id = valid_id

    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        return True

    @staticmethod
    def _to_sql_datetime_string(dt: pd.Timestamp) -> str:
        """
        Convert a timestamp into an SQL string to query the DB.
        """
        hdateti.dassert_has_tz(dt)
        # Convert to UTC, if needed.
        if dt.tzinfo != hdateti.get_UTC_tz().zone:
            dt = dt.tz_convert(hdateti.get_UTC_tz())
        ret: str = dt.strftime("%Y-%m-%d %H:%M:%S")
        return ret

    def _convert_data_for_normalization(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert data to format required by normalization in parent class.
        """
        # Add new TZ-localized datetime columns for research and readability.
        for col_name in [self._start_time_col_name, self._end_time_col_name]:
            if col_name in df.columns:
                srs = df[col_name]
                # _LOG.debug("srs=\n%s", str(srs.head(3)))
                if not srs.empty:
                    srs = srs.apply(pd.to_datetime)
                    srs = srs.dt.tz_localize("UTC")
                    srs = srs.dt.tz_convert("America/New_York")
                    df[col_name] = srs
        return df

    def _get_data(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        left_close: bool,
        right_close: bool,
        limit: Optional[int],
    ) -> pd.DataFrame:
        sort_time = True
        query = self._get_sql_query(
            self._columns,
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            left_close,
            right_close,
            sort_time,
            limit,
        )
        _LOG.debug("query=%s", query)
        df = hsql.execute_query_to_df(self.connection, query)
        # Prepare data for normalization by the parent class.
        df = self._convert_data_for_normalization(df)
        return df

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        """
        Return the last `end_time` available in the DB.
        """
        # We assume that all the bars are inserted together in a single
        # transaction, so we can check for the max timestamp.
        # Get the latest `start_time` (which is an index) with a query like:
        #   ```
        #   SELECT MAX(start_time)
        #     FROM bars_qa
        #     WHERE interval=60 AND region='AM' AND asset_id = '17085'
        #   ```
        query = []
        query.append(f"SELECT MAX({self._start_time_col_name})")
        query.append(f"FROM {self._table_name}")
        query.append("WHERE")
        if self._where_clause:
            query.append(f"{self._where_clause} AND")
        query.append(f"{self._asset_id_col} = '{self._valid_id}'")
        query = " ".join(query)
        # _LOG.debug("query=%s", query)
        df = hsql.execute_query_to_df(self.connection, query)
        # Check that the `start_time` is a single value.
        hdbg.dassert_eq(df.shape, (1, 1))
        start_time = df.iloc[0, 0]
        # _LOG.debug("start_time from DB=%s", start_time)
        # Get the `end_time` that corresponds to the last `start_time` with a
        # query like:
        #   ```
        #   SELECT end_time
        #     FROM bars_qa
        #     WHERE interval=60 AND
        #         region='AM' AND
        #         start_time = '2021-10-07 15:50:00' AND
        #         asset_id = '17085'
        #   ```
        query = []
        query.append(f"SELECT {self._end_time_col_name}")
        query.append(f"FROM {self._table_name}")
        query.append("WHERE")
        if self._where_clause:
            query.append(f"{self._where_clause} AND")
        query.append(
            f"{self._start_time_col_name} = '{start_time}' AND "
            + f"{self._asset_id_col} = '{self._valid_id}'"
        )
        query = " ".join(query)
        # _LOG.debug("query=%s", query)
        df = hsql.execute_query_to_df(self.connection, query)
        # Check that the `end_time` is a single value.
        hdbg.dassert_eq(df.shape, (1, 1))
        end_time = df.iloc[0, 0]
        # _LOG.debug("end_time from DB=%s", end_time)
        # We know that it should be `end_time = start_time + 1 minute`.
        start_time = pd.Timestamp(start_time, tz="UTC")
        end_time = pd.Timestamp(end_time, tz="UTC")
        hdbg.dassert_eq(end_time, start_time + pd.Timedelta(minutes=1))
        return end_time

    def _get_sql_query(
        self,
        columns: Optional[List[str]],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        ts_col_name: str,
        asset_ids: List[Any],
        # TODO(gp): Move these close to start_ts.
        left_close: bool,
        right_close: bool,
        sort_time: bool,
        limit: Optional[int],
    ) -> str:
        """
        Build a query for the RT DB.

        SELECT * \
            FROM bars \
            WHERE ... AND id in (...) \
            ORDER BY end_time DESC \
            LIMIT ...

        :param columns: columns to select from `table_name`
            - `None` means all columns.
        :param asset_ids: asset ids to select
        :param sort_time: whether to sort by end_time
        :param limit: how many rows to return
        """
        query = []
        # Handle `columns`.
        if columns is None:
            columns_as_str = "*"
        else:
            columns_as_str = ",".join(columns)
        query.append(f"SELECT {columns_as_str} FROM {self._table_name}")
        # Handle `where` clause.
        if self._where_clause is not None:
            # E.g., "WHERE interval=60 AND region='AM'")
            query.append(f"WHERE {self._where_clause}")
        # Handle `asset_ids`.
        hdbg.dassert_isinstance(asset_ids, list)
        if len(asset_ids) == 1:
            ids_as_str = f"{self._asset_id_col}={asset_ids[0]}"
        else:
            ids_as_str = ",".join(map(str, asset_ids))
            ids_as_str = f"{self._asset_id_col} in ({ids_as_str})"
        query.append("AND " + ids_as_str)
        # Handle `start_ts`.
        if start_ts is not None:
            if left_close:
                operator = ">="
            else:
                operator = ">"
            query.append(
                f"AND {ts_col_name} {operator} "
                + "'%s'" % self._to_sql_datetime_string(start_ts)
            )
        # Handle `end_ts`.
        if end_ts is not None:
            if right_close:
                operator = "<="
            else:
                operator = "<"
            query.append(
                f"AND {ts_col_name} {operator} "
                + "'%s'" % self._to_sql_datetime_string(end_ts)
            )
        # Handle `sort_time`.
        if sort_time:
            query.append("ORDER BY end_time DESC")
        # Handle `limit`.
        if limit is not None:
            query.append(f"LIMIT {limit}")
        query = " ".join(query)
        return query


# TODO(Grisha): "Factor out common code for RealTimeMarketData2 and ImClientMarketData`" CmTask #2382.
class RealTimeMarketData2(mdabmada.MarketData):
    """
    Interface for real-time market data accessed through a realtime SQL client.
    """

    def __init__(self, client: icdc.SqlRealTimeImClient, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._im_client = client

    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        return self._im_client.should_be_online()

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        # Note: Getting the end time for one symbol as a placeholder.
        # TODO(Danya): CMTask1622: "Return `last_end_time` for all symbols".
        return self._im_client.get_end_ts_for_symbol("binance::BTC_USDT")

    def _get_data(
        self,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        left_close: bool,
        right_close: bool,
        limit: Optional[int],
        *,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Build a query and load SQL data in MarketData format.
        """
        if not left_close:
            if start_ts is not None:
                # Add one millisecond to not include the left boundary.
                start_ts += pd.Timedelta(1, "ms")
        if not right_close:
            if end_ts is not None:
                # Subtract one millisecond not to include the right boundary.
                end_ts -= pd.Timedelta(1, "ms")
        if asset_ids is None:
            # If asset ids are not provided, get universe as full symbols.
            full_symbols = self._im_client.get_universe()
        else:
            # Convert asset ids to full symbols to read `im` data.
            full_symbols = self._im_client.get_full_symbols_from_asset_ids(
                asset_ids
            )
        # Load the data using `im_client`.
        ivcu.dassert_valid_full_symbols(full_symbols)
        # TODO(gp): im_client should always return the name of the column storing
        #  the asset_id as "full_symbol" instead we access the class to see what
        #  is the name of that column.
        full_symbol_col_name = self._im_client._get_full_symbol_col_name(None)
        if self._columns is not None:
            # Exlcude columns specific of `MarketData` when querying `ImClient`.
            columns_to_exclude_in_im = [
                self._asset_id_col,
                self._start_time_col_name,
                self._end_time_col_name,
            ]
            query_columns = [
                col
                for col in self._columns
                if col not in columns_to_exclude_in_im
            ]
            if full_symbol_col_name not in query_columns:
                # Add full symbol column to the query if its name wasn't passed
                # since it is necessary for asset id column generation.
                query_columns.insert(0, full_symbol_col_name)
        else:
            query_columns = self._columns
        # Read data.
        market_data = self._im_client.read_data(
            full_symbols,
            start_ts,
            end_ts,
            columns,
            self._filter_data_mode,
            ts_col_name=ts_col_name,
        )
        # Add `asset_id` column.
        _LOG.debug("asset_id_col=%s", self._asset_id_col)
        _LOG.debug("full_symbol_col_name=%s", full_symbol_col_name)
        _LOG.debug("market_data.columns=%s", sorted(list(market_data.columns)))
        hdbg.dassert_in(full_symbol_col_name, market_data.columns)
        transformed_asset_ids = self._im_client.get_asset_ids_from_full_symbols(
            market_data[full_symbol_col_name].tolist()
        )
        if self._asset_id_col in market_data.columns:
            _LOG.debug(
                "Overwriting column '%s' with asset_ids", self._asset_id_col
            )
            market_data[self._asset_id_col] = transformed_asset_ids
        else:
            market_data.insert(
                0,
                self._asset_id_col,
                transformed_asset_ids,
            )
        if self._columns is not None:
            # Drop full symbol column if it was not in the sepcified columns.
            if full_symbol_col_name not in self._columns:
                market_data = market_data.drop(full_symbol_col_name, axis=1)
        hdbg.dassert_in(self._asset_id_col, market_data.columns)
        # TODO(Dan): Propagate `limit` parameter to SQL query.
        if limit:
            # Keep only top N records.
            hdbg.dassert_lte(1, limit)
            market_data = market_data.head(limit)
        # Prepare data for normalization by the parent class.
        market_data = self._convert_data_for_normalization(market_data)
        return market_data

    def _convert_data_for_normalization(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert data to format required by normalization in parent class.

        :param df: IM data to transform
        ```
                                  full_symbol     close     volume
                      index
        2021-07-26 13:42:00  binance:BTC_USDT  47063.51  29.403690
        2021-07-26 13:43:00  binance:BTC_USDT  46946.30  58.246946
        2021-07-26 13:44:00  binance:BTC_USDT  46895.39  81.264098
        ```
        :return: transformed data
        ```
                        end_ts       full_symbol     close     volume             start_ts
        idx
        0  2021-07-26 13:42:00  binance:BTC_USDT  47063.51  29.403690  2021-07-26 13:41:00
        1  2021-07-26 13:43:00  binance:BTC_USDT  46946.30  58.246946  2021-07-26 13:42:00
        2  2021-07-26 13:44:00  binance:BTC_USDT  46895.39  81.264098  2021-07-26 13:43:00
        ```
        """
        # Move the index to the end ts column.
        df.index.name = "index"
        df = df.reset_index()
        hdbg.dassert_not_in(self._end_time_col_name, df.columns)
        df = df.rename(columns={"index": self._end_time_col_name})
        # `IM` data is assumed to have 1 minute frequency.
        hdbg.dassert_not_in(self._start_time_col_name, df.columns)
        # hdbg.dassert_eq(df.index.freq, "1T")
        df[self._start_time_col_name] = df[
            self._end_time_col_name
        ] - pd.Timedelta(minutes=1)
        return df
