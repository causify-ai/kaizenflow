import io
import logging

import pandas as pd

import core.real_time as creatime
import helpers.hasyncio as hasynci
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.broker.broker_example as obrbrexa
import oms.portfolio.dataframe_portfolio as opodapor
import oms.portfolio.portfolio_example as opopoexa

_LOG = logging.getLogger(__name__)

_5mins = pd.DateOffset(minutes=5)


# #############################################################################
# TestDataFramePortfolio1
# #############################################################################


class TestDataFramePortfolio1(hunitest.TestCase):
    @staticmethod
    def get_portfolio1() -> opodapor.DataFramePortfolio:
        """
        Return a freshly minted Portfolio with only cash.
        """
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            # Build a Portfolio.
            portfolio = opopoexa.get_DataFramePortfolio_example1(
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
            portfolio = opopoexa.get_DataFramePortfolio_example1(
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
            broker = obrbrexa.get_DataFrameBroker_example1(
                event_loop, market_data=market_data
            )
            # Build Portfolio.
            mark_to_market_col = "price"
            pricing_method = "last"
            holdings_dict = {101: 727.5, 202: 1040.3, -1: 10000}
            portfolio = opodapor.DataFramePortfolio.from_dict(
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
            portfolio = opopoexa.get_DataFramePortfolio_example1(
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
            broker = obrbrexa.get_DataFrameBroker_example1(
                event_loop, market_data=market_data
            )
            # Build Portfolio.
            mark_to_market_col = "price"
            pricing_method = "last"
            holdings_dict = {101: 727.5, 202: 1040.3, -1: 10000}
            portfolio = opodapor.DataFramePortfolio.from_dict(
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
            portfolio = opopoexa.get_DataFramePortfolio_example1(
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
