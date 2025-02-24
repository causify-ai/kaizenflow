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
import market_data.abstract_market_data as mdabmada
import market_data.im_client_market_data as mdimcmada

_LOG = logging.getLogger(__name__)


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
        ignore_delay: bool,
    ) -> pd.DataFrame:
        # This is used only in ReplayedMarketData.
        _ = ignore_delay
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


# TODO(Dan): decide whether we need a separate class, maybe use `ImClientMarketData` for both
# historical and real-time runs.
class RealTimeMarketData2(mdimcmada.ImClientMarketData):
    """
    Interface for real-time market data accessed through a realtime SQL client.
    """

    def __init__(
        self, im_client: icdc.SqlRealTimeImClient, *args, **kwargs
    ) -> None:
        super().__init__(*args, im_client=im_client, **kwargs)
