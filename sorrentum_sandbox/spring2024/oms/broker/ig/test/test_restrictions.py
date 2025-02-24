import logging

import pandas as pd

import helpers.hpandas as hpandas
import helpers.hsql as hsql
import oms.broker.ig.restrictions_example as obigreex
import oms.db.oms_db as odbomdb
import oms.test.oms_db_helper as omtodh

_LOG = logging.getLogger(__name__)


# #############################################################################


class TestRestrictions1(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test1(self) -> None:
        table_name = odbomdb.RESTRICTIONS_TABLE_NAME
        asset_id_name = "asset_id"
        incremental = False
        odbomdb.create_restrictions_table(
            self.connection, incremental, asset_id_name, table_name
        )
        # Populate the Restrictions table with an example row.
        row = _get_row1()
        hsql.execute_insert_query(self.connection, row, table_name)
        if False:
            # Print the DB status.
            query = """SELECT * FROM restrictions"""
            df = hsql.execute_query_to_df(self.connection, query)
            print(hpandas.df_to_str(df))
            assert 0
        #
        # Create Restrictions object.
        restrictions = obigreex.get_Restrictions_example1(
            self.connection,
        )
        trading_restrictions = restrictions.get_trading_restrictions()
        # Check.
        actual = hpandas.df_to_str(trading_restrictions)
        expected = r"""
            strategyid account  id   tradedate               timestamp_db  asset_id  is_restricted  is_buy_restricted  is_buy_cover_restricted  is_sell_short_restricted  is_sell_long_restricted
    0       SAU1   paper   0  2000-01-01 2000-01-01 21:38:39.419536       101           True               True                     True                      True                     True"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        table_name = odbomdb.RESTRICTIONS_TABLE_NAME
        asset_id_name = "asset_id"
        incremental = False
        odbomdb.create_restrictions_table(
            self.connection, incremental, asset_id_name, table_name
        )
        # Populate the Restrictions table with an example row.
        rows = [_get_row1(), _get_row2(), _get_row3()]
        for row in rows:
            hsql.execute_insert_query(self.connection, row, table_name)
        if False:
            # Print the DB status.
            query = """SELECT * FROM restrictions"""
            df = hsql.execute_query_to_df(self.connection, query)
            print(hpandas.df_to_str(df))
            assert 0
        #
        # Create Restrictions object.
        restrictions = obigreex.get_Restrictions_example1(
            self.connection,
        )
        trading_restrictions = restrictions.get_trading_restrictions()
        # Check.
        actual = hpandas.df_to_str(trading_restrictions)
        expected = r"""
        strategyid account  id   tradedate               timestamp_db  asset_id  is_restricted  is_buy_restricted  is_buy_cover_restricted  is_sell_short_restricted  is_sell_long_restricted
0       SAU1   paper   0  2000-01-01 2000-01-01 21:38:39.419536       101           True               True                     True                      True                     True
1       SAU1   paper   0  2000-01-01 2000-01-01 21:38:38.419536       201           True              False                    False                     False                    False"""
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


def _get_row1() -> pd.Series:
    row = """
    strategyid,SAU1
    account,paper
    id,0
    tradedate,2000-01-01
    timestamp_db,2000-01-01 21:38:39.419536
    asset_id,101
    is_restricted,TRUE
    is_buy_restricted,TRUE
    is_buy_cover_restricted,TRUE
    is_sell_short_restricted,TRUE
    is_sell_long_restricted,TRUE
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs


def _get_row2() -> pd.Series:
    row = """
    strategyid,SAU1
    account,paper
    id,0
    tradedate,2000-01-01
    timestamp_db,2000-01-01 21:38:38.419536
    asset_id,201
    is_restricted,TRUE
    is_buy_restricted,FALSE
    is_buy_cover_restricted,FALSE
    is_sell_short_restricted,FALSE
    is_sell_long_restricted,FALSE
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs


def _get_row3() -> pd.Series:
    row = """
    strategyid,SAU1
    account,paper
    id,0
    tradedate,1999-12-31
    timestamp_db,1999-12-31 21:38:56.12345
    asset_id,101
    is_restricted,TRUE
    is_buy_restricted,TRUE
    is_buy_cover_restricted,TRUE
    is_sell_short_restricted,TRUE
    is_sell_long_restricted,TRUE
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs
