"""
Import as:

import oms.broker.ig.restrictions as obrigres
"""
import logging
from typing import Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hsql as hsql

_LOG = logging.getLogger(__name__)


class Restrictions:
    def __init__(
        self,
        strategy_id: str,
        account: Optional[str],
        asset_id_col: str,
        date_col: str,
        db_connection: hsql.DbConnection,
        table_name: str,
        get_wall_clock_time: hdateti.GetWallClockTime,
    ) -> None:
        """
        Constructor.

        :param strategy_id: identifier of the strategy (e.g., "SAU1")
        :param account: used to create SQL queries, if not `None`
        """
        self._strategy_id = self._check_nonempty_str(strategy_id)
        self._account = account
        self._asset_id_col = self._check_nonempty_str(asset_id_col)
        self._date_col = self._check_nonempty_str(date_col)
        self._db_connection = db_connection
        self._table_name = self._check_nonempty_str(table_name)
        self._get_wall_clock_time = get_wall_clock_time
        #
        self._restrictions = None

    def get_trading_restrictions(
        self,
        *,
        read_cached: bool = True,
    ) -> pd.DataFrame:
        if self._restrictions is not None and read_cached:
            return self._restrictions
        restrictions = self._get_trading_restrictions()
        self._restrictions = restrictions
        return restrictions

    @staticmethod
    def _check_nonempty_str(string: str) -> str:
        hdbg.dassert_isinstance(string, str)
        hdbg.dassert(string, "String must be nonempty.")
        return string

    def _get_trading_restrictions(self) -> pd.DataFrame:
        query = []
        query.append(f"SELECT * FROM {self._table_name}")
        #
        wall_clock_timestamp = self._get_wall_clock_time()
        _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        trade_date = wall_clock_timestamp.date()
        where_clause = f"WHERE tradedate='{trade_date}'"
        if self._account:
            where_clause += f" AND account='{self._account}'"
        query.append(where_clause)
        #
        query.append(f"ORDER BY {self._asset_id_col}")
        query = "\n".join(query)
        _LOG.debug("query=%s", query)
        # Retrieve the data from the DB.
        restrictions_df = hsql.execute_query_to_df(self._db_connection, query)
        restrictions_df.rename(
            columns={self._asset_id_col: "asset_id"}, inplace=True
        )
        _LOG.debug(
            "restrictions_df=\n%s",
            hpandas.df_to_str(restrictions_df, num_rows=None, precision=2),
        )
        if not restrictions_df.empty:
            hdbg.dassert_no_duplicates(
                restrictions_df["asset_id"],
                "Each asset_id should be unique in a restrictions_df",
            )
        return restrictions_df
