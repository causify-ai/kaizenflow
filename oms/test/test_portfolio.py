import asyncio
import io
import logging

import numpy as np
import pandas as pd

import core.real_time as creatime
import helpers.hasyncio as hasynci
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.broker_example as obroexam
import oms.oms_db as oomsdb
import oms.portfolio as omportfo
import oms.portfolio_example as oporexam
import oms.test.oms_db_helper as omtodh

_LOG = logging.getLogger(__name__)

_5mins = pd.DateOffset(minutes=5)


# #############################################################################
# TestDataFramePortfolio1
# #############################################################################


class TestDataFramePortfolio1(hunitest.TestCase):
    @staticmethod
    def get_portfolio1() -> omportfo.Portfolio:
        """
        Return a freshly minted Portfolio with only cash.
        """
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            # Build a Portfolio.
            portfolio = oporexam.get_DataFramePortfolio_example1(
                event_loop,
                market_data=market_data,
            )
            _ = portfolio.mark_to_market()
        return portfolio

    # @pytest.mark.skip("This is flaky because of the clock jitter")
    def test_state(self) -> None:
        """
        Check non-cash holdings for a Portfolio with only cash.
        """
        expected = r"""
                                   asset_id  curr_num_shares  price    value  \
        2000-01-01 09:35:00-05:00        -1          1000000      1  1000000

                                       wall_clock_timestamp
        2000-01-01 09:35:00-05:00 2000-01-01 09:35:00-05:00  """
        portfolio = self.get_portfolio1()
        actual = portfolio.get_cached_mark_to_market()
        self.assert_equal(str(actual), expected, fuzzy_match=True)


# #############################################################################
# TestDataFramePortfolio2
# #############################################################################


class TestDataFramePortfolio2(hunitest.TestCase):
    def test_initialization_with_cash1(self) -> None:
        """
        Initialize a Portfolio with cash.
        """
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            # Build Portfolio.
            portfolio = oporexam.get_DataFramePortfolio_example1(
                event_loop,
                market_data=market_data,
            )
            _ = portfolio.mark_to_market()
            # Check.
            expected = pd.DataFrame(
                index=[
                    pd.Timestamp(
                        "2000-01-01 09:35:00-05:00", tz="America/New_York"
                    )
                ],
            )
            self.assert_dfs_close(
                portfolio.get_historical_holdings_shares(), expected
            )

    def test_initialization_with_holdings1(self) -> None:
        """
        Initialize a Portfolio with holdings.
        """
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                get_wall_clock_time,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            # Build Broker.
            broker = obroexam.get_DataFrameBroker_example1(
                event_loop, market_data=market_data
            )
            # Build Portfolio.
            mark_to_market_col = "price"
            pricing_method = "last"
            holdings_dict = {101: 727.5, 202: 1040.3, -1: 10000}
            portfolio = omportfo.DataFramePortfolio.from_dict(
                broker,
                mark_to_market_col,
                pricing_method,
                holdings_shares_dict=holdings_dict,
            )
            _ = portfolio.mark_to_market()
            # Check.
            expected_shares = pd.DataFrame(
                {101: 727.5, 202: 1040.3},
                [
                    pd.Timestamp(
                        "2000-01-01 09:35:00-05:00", tz="America/New_York"
                    )
                ],
            )
            self.assert_dfs_close(
                portfolio.get_historical_holdings_shares(), expected_shares
            )

    def test_get_historical_statistics1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            #
            portfolio = oporexam.get_DataFramePortfolio_example1(
                event_loop,
                market_data=market_data,
            )
            _ = portfolio.mark_to_market()
            # Check.
            expected = r"""
                          2000-01-01 09:35:00-05:00
            pnl                                 NaN
            gross_volume                        0.0
            net_volume                          0.0
            gmv                                 0.0
            nmv                                 0.0
            cash                          1000000.0
            net_wealth                    1000000.0
            leverage                            0.0"""
            actual = portfolio.get_historical_statistics().transpose()
            self.assert_equal(str(actual), expected, fuzzy_match=True)

    def test_get_historical_statistics2(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                get_wall_clock_time,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            # Build Broker.
            broker = obroexam.get_DataFrameBroker_example1(
                event_loop, market_data=market_data
            )
            # Build Portfolio.
            mark_to_market_col = "price"
            pricing_method = "last"
            holdings_dict = {101: 727.5, 202: 1040.3, -1: 10000}
            portfolio = omportfo.DataFramePortfolio.from_dict(
                broker,
                mark_to_market_col,
                pricing_method,
                holdings_shares_dict=holdings_dict,
            )
            _ = portfolio.mark_to_market()
            expected = r"""
                          2000-01-01 09:35:00-05:00
            pnl                                 NaN
            gross_volume               0.000000e+00
            net_volume                 0.000000e+00
            gmv                        1.768351e+06
            nmv                        1.768351e+06
            cash                       1.000000e+04
            net_wealth                 1.778351e+06
            leverage                   9.943768e-01"""
            actual = portfolio.get_historical_statistics().transpose()
            self.assert_equal(str(actual), expected, fuzzy_match=True)

    def test_get_historical_statistics3(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            tz = "ET"
            initial_replayed_timestamp = pd.Timestamp(
                "2000-01-01 09:35:00-05:00", tz="America/New_York"
            )
            get_wall_clock_time = creatime.get_replayed_wall_clock_time(
                tz,
                initial_replayed_timestamp,
                event_loop=event_loop,
            )
            price_txt = r"""
            start_datetime,end_datetime,asset_id,price
            2000-01-01 09:30:00-05:00,2000-01-01 09:35:00-05:00,100,100.34
            """
            price_df = pd.read_csv(
                io.StringIO(hprint.dedent(price_txt)),
                parse_dates=["start_datetime", "end_datetime"],
            )
            start_time_col_name = "start_datetime"
            end_time_col_name = "end_datetime"
            knowledge_datetime_col_name = "end_datetime"
            delay_in_secs = 0
            asset_id_col = "asset_id"
            asset_ids = None
            columns = []
            market_data = mdata.ReplayedMarketData(
                price_df,
                knowledge_datetime_col_name,
                delay_in_secs,
                asset_id_col,
                asset_ids,
                start_time_col_name,
                end_time_col_name,
                columns,
                get_wall_clock_time,
            )
            portfolio = oporexam.get_DataFramePortfolio_example1(
                event_loop,
                market_data=market_data,
            )
            _ = portfolio.mark_to_market()
            # Check.
            expected = r"""
                          2000-01-01 09:35:00-05:00
            pnl                                 NaN
            gross_volume                        0.0
            net_volume                          0.0
            gmv                                 0.0
            nmv                                 0.0
            cash                          1000000.0
            net_wealth                    1000000.0
            leverage                            0.0"""
            actual = portfolio.get_historical_statistics().transpose()
            self.assert_equal(str(actual), expected, fuzzy_match=True)


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

    async def coroutine1(self, portfolio: omportfo.Portfolio) -> None:
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        # Check.
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.DatabasePortfolio at 0x>
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
  2000-01-01 09:40:00-05:00 -0.0
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
            table_name = oomsdb.CURRENT_POSITIONS_TABLE_NAME
            oomsdb.create_current_positions_table(
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
            portfolio = oporexam.get_DatabasePortfolio_example1(
                event_loop,
                self.connection,
                table_name,
                asset_ids=[101],
            )
            coroutines = [self.coroutine1(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)

    # //////////////////////////////////////////////////////////////////////////////

    async def coroutine2(self, portfolio: omportfo.Portfolio):
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        # Check.
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.DatabasePortfolio at 0x>
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
            table_name = oomsdb.CURRENT_POSITIONS_TABLE_NAME
            oomsdb.create_current_positions_table(
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
            portfolio = oporexam.get_DatabasePortfolio_example1(
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

    async def coroutine1(self, portfolio: omportfo.Portfolio) -> None:
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
        portfolio_df_str = hpandas.df_to_str(portfolio_df, precision=precision)
        expected_portfolio_df_str = r"""
                          holdings_shares holdings_notional  executed_trades_shares executed_trades_notional   pnl
                                      101               101                     101                      101   101
2000-01-01 09:40:00-05:00            20.0          20004.03                    20.0                     -0.0   NaN
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
            table_name = oomsdb.CURRENT_POSITIONS_TABLE_NAME
            oomsdb.create_current_positions_table(
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
            portfolio = oporexam.get_DatabasePortfolio_example1(
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

    async def coroutine1(self, portfolio: omportfo.Portfolio) -> None:
        portfolio.mark_to_market()
        await asyncio.sleep(60 * 5)
        portfolio.mark_to_market()
        #
        actual = str(portfolio)
        expected = r"""
<oms.portfolio.DatabasePortfolio at 0x>
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
  2000-01-01 09:40:00-05:00 -0.0
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
            table_name = oomsdb.CURRENT_POSITIONS_TABLE_NAME
            oomsdb.create_current_positions_table(
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
            portfolio = oporexam.get_DatabasePortfolio_example2(
                event_loop,
                self.connection,
                table_name,
                universe=[101, -1],
            )
            coroutines = [self.coroutine1(portfolio)]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)
