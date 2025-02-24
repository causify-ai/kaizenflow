import asyncio
import logging

import numpy as np
import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hpandas as hpandas
import helpers.hsql as hsql
import oms.db.oms_db as odbomdb
import oms.portfolio.database_portfolio as opodapor
import oms.portfolio.portfolio_example as opopoexa
import oms.test.oms_db_helper as omtodh

_LOG = logging.getLogger(__name__)

_5mins = pd.DateOffset(minutes=5)


# #############################################################################
# TestDatabasePortfolio1
# #############################################################################


def _get_row1() -> pd.Series:
    row = """
    strategyid,SAU1
    account,candidate
    id,0
    tradedate,2000-01-01
    timestamp_db,2000-01-01 21:38:39.419536
    asset_id,101
    target_position,10
    current_position,20.0
    open_quantity,0
    net_cost,0
    bod_position,0
    bod_price,0
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs


def _get_row2() -> pd.Series:
    row = """
    strategyid,SAU1
    account,candidate
    id,0
    tradedate,2000-01-01
    timestamp_db,2000-01-01 21:38:39.419536
    asset_id,101
    target_position,10
    current_position,20.0
    open_quantity,0
    net_cost,1903.1217
    bod_position,0
    bod_price,0
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs


def _get_row3() -> pd.Series:
    row = """
    strategyid,SAU1
    account,candidate
    id,0
    tradedate,2000-01-01
    timestamp_db,2000-01-01 09:10:39.419536
    asset_id,101
    target_position,20.0
    current_position,20.0
    open_quantity,0
    net_cost,0
    bod_position,20.0
    bod_price,1000.00
    """
    srs = hsql.csv_to_series(row, sep=",")
    return srs


class TestDatabasePortfolio1(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    async def coroutine1(self, portfolio: opodapor.DatabasePortfolio) -> None:
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        # Check.
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.database_portfolio.DatabasePortfolio at 0x>
  # holdings_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00   0.0
  2000-01-01 09:40:00-05:00  20.0
  # holdings_notional=
  asset_id                        101
  2000-01-01 09:35:00-05:00      0.00
  2000-01-01 09:40:00-05:00  20004.03
  # executed_trades_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00   0.0
  2000-01-01 09:40:00-05:00  20.0
  # executed_trades_notional=
  asset_id                   101
  2000-01-01 09:40:00-05:00  0.0
  # pnl=
  asset_id                        101
  2000-01-01 09:35:00-05:00       NaN
  2000-01-01 09:40:00-05:00  20004.03
  # statistics=
                                  pnl  gross_volume  net_volume       gmv       nmv       cash  net_wealth  leverage
  2000-01-01 09:35:00-05:00       NaN           0.0         0.0      0.00      0.00  1000000.0    1.00e+06      0.00
  2000-01-01 09:40:00-05:00  20004.03           0.0         0.0  20004.03  20004.03  1000000.0    1.02e+06      0.02
"""
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test that the update of Portfolio works.
        """
        with hasynci.solipsism_context() as event_loop:
            # Create current positions in the table.
            row = _get_row1()
            asset_id_name = "asset_id"
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            odbomdb.create_current_positions_table(
                self.connection, False, asset_id_name, table_name
            )
            hsql.execute_insert_query(self.connection, row, table_name)
            if False:
                # Print the DB status.
                query = """SELECT * FROM current_positions"""
                df = hsql.execute_query_to_df(self.connection, query)
                print(hpandas.df_to_str(df))
                assert 0
            # Create DatabasePortfolio with some initial cash.
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                self.connection,
                table_name,
                asset_ids=[101],
            )
            coroutines = [self.coroutine1(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)

    # //////////////////////////////////////////////////////////////////////////////

    async def coroutine2(self, portfolio: opodapor.DatabasePortfolio):
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        # Check.
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.database_portfolio.DatabasePortfolio at 0x>
  # holdings_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00   0.0
  2000-01-01 09:40:00-05:00  20.0
  # holdings_notional=
  asset_id                        101
  2000-01-01 09:35:00-05:00      0.00
  2000-01-01 09:40:00-05:00  20004.03
  # executed_trades_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00   0.0
  2000-01-01 09:40:00-05:00  20.0
  # executed_trades_notional=
  asset_id                       101
  2000-01-01 09:40:00-05:00 -1903.12
  # pnl=
  asset_id                        101
  2000-01-01 09:35:00-05:00       NaN
  2000-01-01 09:40:00-05:00  21907.15
  # statistics=
                                  pnl  gross_volume  net_volume       gmv       nmv      cash  net_wealth  leverage
  2000-01-01 09:35:00-05:00       NaN          0.00        0.00      0.00      0.00  1.00e+06    1.00e+06      0.00
  2000-01-01 09:40:00-05:00  21907.15       1903.12    -1903.12  20004.03  20004.03  1.00e+06    1.02e+06      0.02
"""
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test that the update of Portfolio works when accounting for costs.
        """
        with hasynci.solipsism_context() as event_loop:
            # Create current positions in the table.
            row = _get_row2()
            asset_id_name = "asset_id"
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            odbomdb.create_current_positions_table(
                self.connection, False, asset_id_name, table_name
            )
            hsql.execute_insert_query(self.connection, row, table_name)
            if False:
                # Print the DB status.
                query = """SELECT * FROM current_positions"""
                df = hsql.execute_query_to_df(self.connection, query)
                print(hpandas.df_to_str(df))
                assert 0
            # Create DatabasePortfolio with some initial cash.
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                self.connection,
                table_name,
                asset_ids=[101],
            )
            coroutines = [self.coroutine2(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)


# #############################################################################
# TestDatabasePortfolio2
# #############################################################################


class TestDatabasePortfolio2(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    async def coroutine1(self, portfolio: opodapor.DatabasePortfolio) -> None:
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        log_dir = self.get_scratch_space()
        _ = portfolio.log_state(log_dir)
        #
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        _ = portfolio.log_state(log_dir)
        #
        portfolio_df, stats_df = portfolio.read_state(log_dir)
        # Ensure that the `int` asset id type is recovered.
        asset_id_idx = portfolio_df.columns.levels[1]
        self.assertEqual(asset_id_idx.dtype.type, np.int64)
        #
        precision = 2
        #
        portfolio_df_str = hpandas.df_to_str(
            portfolio_df, handle_signed_zeros=True, precision=precision
        )
        expected_portfolio_df_str = r"""
                          holdings_shares holdings_notional  executed_trades_shares executed_trades_notional   pnl
                                      101               101                     101                      101   101
2000-01-01 09:40:00-05:00            20.0          20004.03                    20.0                      0.0   NaN
2000-01-01 09:45:00-05:00            20.0          19998.37                     0.0                      0.0 -5.66
"""
        self.assert_equal(
            portfolio_df_str, expected_portfolio_df_str, fuzzy_match=True
        )
        #
        stats_df_str = hpandas.df_to_str(stats_df, precision=precision)
        expected_stats_df_str = r"""
                                        pnl  gross_volume  net_volume       gmv       nmv       cash  net_wealth  leverage
        2000-01-01 09:40:00-05:00  20004.03           0.0         0.0  20004.03  20004.03  1000000.0    1.02e+06      0.02
        2000-01-01 09:45:00-05:00     -5.66           0.0         0.0  19998.37  19998.37  1000000.0    1.02e+06      0.02"""
        self.assert_equal(
            stats_df_str,
            expected_stats_df_str,
            purify_text=True,
            fuzzy_match=True,
        )

    def test1(self) -> None:
        """
        Test the `log_state()`/`read_state()` round trip.
        """
        with hasynci.solipsism_context() as event_loop:
            # Create current positions in the table.
            row = _get_row1()
            asset_id_name = "asset_id"
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            odbomdb.create_current_positions_table(
                self.connection, False, asset_id_name, table_name
            )
            hsql.execute_insert_query(self.connection, row, table_name)
            if False:
                # Print the DB status.
                query = """SELECT * FROM current_positions"""
                df = hsql.execute_query_to_df(self.connection, query)
                print(hpandas.df_to_str(df))
                assert 0
            # Create DatabasePortfolio with some initial cash.
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                self.connection,
                table_name,
                asset_ids=[101],
            )
            coroutines = [self.coroutine1(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)


# #############################################################################
# TestDatabasePortfolio3
# #############################################################################


class TestDatabasePortfolio3(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    async def coroutine1(self, portfolio: opodapor.DatabasePortfolio) -> None:
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        #
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.database_portfolio.DatabasePortfolio at 0x>
  # holdings_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00  20.0
  2000-01-01 09:40:00-05:00  20.0
  # holdings_notional=
  asset_id                        101
  2000-01-01 09:35:00-05:00  20006.24
  2000-01-01 09:40:00-05:00  20004.03
  # executed_trades_shares=
  asset_id                    101
  2000-01-01 09:35:00-05:00  20.0
  2000-01-01 09:40:00-05:00   0.0
  # executed_trades_notional=
  asset_id                   101
  2000-01-01 09:40:00-05:00  0.0
  # pnl=
  asset_id                    101
  2000-01-01 09:35:00-05:00   NaN
  2000-01-01 09:40:00-05:00 -2.21
  # statistics=
                              pnl  gross_volume  net_volume       gmv       nmv  cash  net_wealth  leverage
  2000-01-01 09:35:00-05:00   NaN           0.0         0.0  20006.24  20006.24   0.0    20006.24       1.0
  2000-01-01 09:40:00-05:00 -2.21           0.0         0.0  20004.03  20004.03   0.0    20004.03       1.0
"""
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test initialization from db.
        """
        with hasynci.solipsism_context() as event_loop:
            # Create current positions in the table.
            row = _get_row3()
            asset_id_name = "asset_id"
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            odbomdb.create_current_positions_table(
                self.connection, False, asset_id_name, table_name
            )
            hsql.execute_insert_query(self.connection, row, table_name)
            if False:
                # Print the DB status.
                query = """SELECT * FROM current_positions"""
                df = hsql.execute_query_to_df(self.connection, query)
                print(hpandas.df_to_str(df))
                assert 0
            # Create DatabasePortfolio from the DB.
            portfolio = opopoexa.get_DatabasePortfolio_example2(
                event_loop,
                self.connection,
                table_name,
                universe=[101, -1],
            )
            coroutines = [self.coroutine1(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)
