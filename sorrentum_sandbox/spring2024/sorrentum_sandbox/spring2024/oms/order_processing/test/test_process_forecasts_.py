import asyncio
import datetime
import logging
from typing import Any, Dict, List, Tuple, Union

import pandas as pd
import pytest

import core.finance as cofinanc
import core.finance_data_example as cfidaexa
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.db.oms_db as odbomdb
import oms.order_processing.order_processor as ooprorpr
import oms.order_processing.process_forecasts_ as oopprfo
import oms.portfolio.database_portfolio as opdapor
import oms.portfolio.dataframe_portfolio as opodapor
import oms.portfolio.portfolio as oporport
import oms.portfolio.portfolio_example as opopoexa
import oms.test.oms_db_helper as omtodh

# TODO(gp): Why does this file ends with _.py?


_LOG = logging.getLogger(__name__)


# #############################################################################
# TestSimulatedProcessForecasts1
# #############################################################################


class TestSimulatedProcessForecasts1(hunitest.TestCase):
    @staticmethod
    def get_portfolio(
        event_loop: asyncio.AbstractEventLoop, asset_ids: List[int]
    ) -> opodapor.DataFramePortfolio:
        (
            market_data,
            get_wall_clock_time,
        ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
        portfolio = opopoexa.get_DataFramePortfolio_example1(
            event_loop, market_data=market_data, asset_ids=asset_ids
        )
        return portfolio

    def test_initialization1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            hasynci.run(
                self._test_simulated_system1(event_loop), event_loop=event_loop
            )

    # TODO(gp): -> run_simulated_system1
    async def _test_simulated_system1(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Run `process_forecasts()` logic with a given prediction df to update a
        Portfolio.
        """
        asset_ids = [101, 202]
        # Build predictions.
        index = [
            pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:40:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:45:00-05:00", tz="America/New_York"),
        ]
        prediction_data = [
            [0.1, 0.2],
            [-0.1, 0.3],
            [-0.3, 0.0],
        ]
        predictions = pd.DataFrame(prediction_data, index, asset_ids)
        volatility_data = [
            [1, 1],
            [1, 1],
            [1, 1],
        ]
        volatility = pd.DataFrame(volatility_data, index, asset_ids)
        # Build a Portfolio.
        portfolio = self.get_portfolio(event_loop, asset_ids)
        # Get process forecasts config.
        order_type = "price@twap"
        dict_ = _get_process_forecasts_dict(order_type)
        spread_df = None
        restrictions_df = None
        # Run.
        await oopprfo.process_forecasts(
            predictions,
            volatility,
            portfolio,
            dict_,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        actual = str(portfolio)
        expected = r"""
        <oms.portfolio.dataframe_portfolio.DataFramePortfolio at 0x>
        # holdings_shares=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00   0.00   0.00
        2000-01-01 09:40:00.100000-05:00 -49.98  49.98
        2000-01-01 09:45:00.100000-05:00 -49.99  49.99
        # holdings_notional=
        asset_id                               101       202
        2000-01-01 09:35:00.100000-05:00      0.00      0.00
        2000-01-01 09:40:00.100000-05:00 -49994.47  49994.47
        2000-01-01 09:45:00.100000-05:00 -49985.86  49985.86
        # executed_trades_shares=
        asset_id                               101       202
        2000-01-01 09:35:00.100000-05:00  0.00e+00  0.00e+00
        2000-01-01 09:40:00.100000-05:00 -5.00e+01  5.00e+01
        2000-01-01 09:45:00.100000-05:00 -5.53e-03  5.53e-03
        # executed_trades_notional=
        asset_id                               101       202
        2000-01-01 09:40:00.100000-05:00 -49980.22  49980.22
        2000-01-01 09:45:00.100000-05:00     -5.53      5.53
        # pnl=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00    NaN    NaN
        2000-01-01 09:40:00.100000-05:00 -14.26  14.26
        2000-01-01 09:45:00.100000-05:00  14.14 -14.14
        # statistics=
                                            pnl  gross_volume  net_volume       gmv  nmv       cash  net_wealth  leverage
        2000-01-01 09:35:00.100000-05:00  NaN          0.00         0.0      0.00  0.0  1000000.0   1000000.0       0.0
        2000-01-01 09:40:00.100000-05:00  0.0      99960.44         0.0  99988.95  0.0  1000000.0   1000000.0       0.1
        2000-01-01 09:45:00.100000-05:00  0.0         11.05         0.0  99971.72  0.0  1000000.0   1000000.0       0.1
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)


# #############################################################################
# TestSimulatedProcessForecasts2
# #############################################################################


class TestSimulatedProcessForecasts2(hunitest.TestCase):
    @staticmethod
    def get_portfolio(
        event_loop: asyncio.AbstractEventLoop,
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
        asset_ids: List[int],
    ) -> opodapor.DataFramePortfolio:
        replayed_delay_in_mins_or_timestamp = 5
        delay_in_secs = 0
        columns = ["price"]
        sleep_in_secs = 30
        time_out_in_secs = 60 * 5
        (
            market_data,
            get_wall_clock_time,
        ) = mdata.get_ReplayedTimeMarketData_example2(
            event_loop,
            start_datetime,
            end_datetime,
            replayed_delay_in_mins_or_timestamp,
            asset_ids,
            delay_in_secs=delay_in_secs,
            columns=columns,
            sleep_in_secs=sleep_in_secs,
            time_out_in_secs=time_out_in_secs,
        )
        portfolio = opopoexa.get_DataFramePortfolio_example1(
            event_loop,
            market_data=market_data,
            asset_ids=asset_ids,
        )
        return portfolio

    @pytest.mark.slow("~8 seconds")
    def test_initialization1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            hasynci.run(
                self._test_simulated_system1(event_loop), event_loop=event_loop
            )

    # TODO(gp): -> run_simulated_system1
    async def _test_simulated_system1(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Run `process_forecasts()` logic with a given prediction df to update a
        Portfolio.
        """
        start_datetime = pd.Timestamp(
            "2000-01-01 15:00:00-05:00", tz="America/New_York"
        )
        end_datetime = pd.Timestamp(
            "2000-01-02 10:30:00-05:00", tz="America/New_York"
        )
        asset_ids = [100, 200]
        # Generate returns predictions and volatility forecasts.
        forecasts = cfidaexa.get_forecast_dataframe(
            start_datetime + pd.Timedelta("5T"),
            end_datetime,
            asset_ids,
        )
        predictions = forecasts["prediction"]
        volatility = forecasts["volatility"]
        # Get portfolio.
        portfolio = self.get_portfolio(
            event_loop, start_datetime, end_datetime, asset_ids
        )
        order_type = "price@twap"
        dict_ = _get_process_forecasts_dict(order_type)
        spread_df = None
        restrictions_df = None
        # Run.
        await oopprfo.process_forecasts(
            predictions,
            volatility,
            portfolio,
            dict_,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        # Check.
        actual = str(portfolio)
        # TODO(gp): Check some invariant and check_string rather than freezing the
        #  output here.
        self.check_string(actual, purify_text=True, fuzzy_match=True)


# #############################################################################
# TestSimulatedProcessForecasts3
# #############################################################################


class TestSimulatedProcessForecasts3(hunitest.TestCase):
    @staticmethod
    def get_portfolio(
        event_loop: asyncio.AbstractEventLoop, asset_ids: List[int]
    ) -> opodapor.DataFramePortfolio:
        start_datetime = pd.Timestamp(
            "2000-01-01 09:30:00-05:00", tz="America/New_York"
        )
        end_datetime = pd.Timestamp(
            "2000-01-01 09:50:00-05:00", tz="America/New_York"
        )
        market_data, _ = mdata.get_ReplayedTimeMarketData_example5(
            event_loop,
            start_datetime,
            end_datetime,
            asset_ids,
        )
        mark_to_market_col = "midpoint"
        portfolio = opopoexa.get_DataFramePortfolio_example1(
            event_loop,
            market_data=market_data,
            mark_to_market_col=mark_to_market_col,
            asset_ids=asset_ids,
        )
        return portfolio

    def test_initialization1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            hasynci.run(
                self._test_simulated_system1(event_loop), event_loop=event_loop
            )

    async def _test_simulated_system1(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Run `process_forecasts()` logic with a given prediction df to update a
        Portfolio.
        """
        asset_ids = [101, 202]
        # Build predictions.
        index = [
            pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:40:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:45:00-05:00", tz="America/New_York"),
        ]
        prediction_data = [
            [0.1, 0.2],
            [-0.1, 0.3],
            [-0.3, 0.0],
        ]
        predictions = pd.DataFrame(prediction_data, index, asset_ids)
        volatility_data = [
            [1, 1],
            [1, 1],
            [1, 1],
        ]
        volatility = pd.DataFrame(volatility_data, index, asset_ids)
        # Build a Portfolio.
        portfolio = self.get_portfolio(event_loop, asset_ids)
        # Get process forecasts config.
        order_type = "partial_spread_0.25@twap"
        dict_ = _get_process_forecasts_dict(order_type)
        spread_df = None
        restrictions_df = None
        # Run.
        await oopprfo.process_forecasts(
            predictions,
            volatility,
            portfolio,
            dict_,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        actual = str(portfolio)
        expected = r"""
        <oms.portfolio.dataframe_portfolio.DataFramePortfolio at 0x>
        # holdings_shares=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00   0.00   0.00
        2000-01-01 09:40:00.100000-05:00 -50.12  49.89
        2000-01-01 09:45:00.100000-05:00 -50.01  49.87
        # holdings_notional=
        asset_id                               101       202
        2000-01-01 09:35:00.100000-05:00      0.00      0.00
        2000-01-01 09:40:00.100000-05:00 -50103.24  50020.21
        2000-01-01 09:45:00.100000-05:00 -49878.97  50008.48
        # executed_trades_shares=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00   0.00   0.00
        2000-01-01 09:40:00.100000-05:00 -50.12  49.89
        2000-01-01 09:45:00.100000-05:00   0.10  -0.02
        # executed_trades_notional=
        asset_id                               101       202
        2000-01-01 09:40:00.100000-05:00 -50053.97  49986.47
        2000-01-01 09:45:00.100000-05:00    103.03    -20.21
        # pnl=
        asset_id                             101    202
        2000-01-01 09:35:00.100000-05:00     NaN    NaN
        2000-01-01 09:40:00.100000-05:00  -49.27  33.74
        2000-01-01 09:45:00.100000-05:00  121.24   8.48
        # statistics=
                                            pnl  gross_volume  net_volume        gmv     nmv      cash  net_wealth  leverage
        2000-01-01 09:35:00.100000-05:00     NaN          0.00        0.00       0.00    0.00  1.00e+06    1.00e+06       0.0
        2000-01-01 09:40:00.100000-05:00  -15.53     100040.44      -67.50  100123.45  -83.03  1.00e+06    1.00e+06       0.1
        2000-01-01 09:45:00.100000-05:00  129.72        123.24       82.83   99887.45  129.51  1.00e+06    1.00e+06       0.1
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)


# #############################################################################
# TestMockedProcessForecasts1
# #############################################################################


class TestMockedProcessForecasts1(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test_mocked_system1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Build a Portfolio.
            db_connection = self.connection
            asset_id_name = "asset_id"
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            incremental = False
            #
            odbomdb.create_oms_tables(self.connection, incremental, asset_id_name)
            #
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                db_connection,
                table_name,
                asset_ids=[101, 202],
            )
            # Build OrderProcessor.
            bar_duration_in_secs = 300
            termination_condition = 3
            delay_to_accept_in_secs = 3
            delay_to_fill_in_secs = 10
            max_wait_time_for_order_in_secs = 10
            broker = portfolio.broker
            asset_id_name = "asset_id"
            order_processor = ooprorpr.OrderProcessor(
                db_connection,
                bar_duration_in_secs,
                termination_condition,
                max_wait_time_for_order_in_secs,
                delay_to_accept_in_secs,
                delay_to_fill_in_secs,
                broker,
                asset_id_name,
            )
            order_processor_coroutine = order_processor.run_loop()
            # Run.
            coroutines = [
                self._test_mocked_system1(portfolio),
                order_processor_coroutine,
            ]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)

    async def _test_mocked_system1(
        self,
        portfolio: oporport.Portfolio,
    ) -> None:
        """
        Run process_forecasts() logic with a given prediction df to update a
        Portfolio.
        """
        # Build predictions.
        index = [
            pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:40:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:45:00-05:00", tz="America/New_York"),
        ]
        columns = [101, 202]
        prediction_data = [
            [0.1, 0.2],
            [-0.1, 0.3],
            [-0.3, 0.0],
        ]
        predictions = pd.DataFrame(prediction_data, index, columns)
        volatility_data = [
            [1, 1],
            [1, 1],
            [1, 1],
        ]
        volatility = pd.DataFrame(volatility_data, index, columns)
        # TODO(gp): Factor this out.
        dict_ = {
            "order_config": {
                "order_type": "price@twap",
                "order_duration_in_mins": 5,
                "execution_frequency": "1T",
            },
            "optimizer_config": {
                "backend": "pomo",
                "asset_class": "equities",
                "apply_cc_limits": None,
                "params": {
                    "style": "cross_sectional",
                    "kwargs": {
                        "bulk_frac_to_remove": 0.0,
                        "bulk_fill_method": "zero",
                        "target_gmv": 1e5,
                    },
                },
            },
            "execution_mode": "batch",
            # TODO(gp): Use the `apply_ProcessForecastsNode_config_for_equities`.
            "ath_start_time": datetime.time(9, 30),
            "trading_start_time": datetime.time(9, 35),
            "ath_end_time": datetime.time(16, 00),
            "trading_end_time": datetime.time(15, 55),
            "liquidate_at_trading_end_time": False,
            "share_quantization": 30,
        }
        spread_df = None
        restrictions_df = None
        # Run.
        await oopprfo.process_forecasts(
            predictions,
            volatility,
            portfolio,
            dict_,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        # TODO(Paul): Factor out a test that compares simulation and mock.
        actual = str(portfolio)
        expected = r"""
        <oms.portfolio.database_portfolio.DatabasePortfolio at 0x>
        # holdings_shares=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00   0.00   0.00
        2000-01-01 09:40:00.100000-05:00 -49.98  49.98
        2000-01-01 09:45:00.100000-05:00 -49.99  49.99
        # holdings_notional=
        asset_id                               101       202
        2000-01-01 09:35:00.100000-05:00      0.00      0.00
        2000-01-01 09:40:00.100000-05:00 -49994.47  49994.47
        2000-01-01 09:45:00.100000-05:00 -49985.86  49985.86
        # executed_trades_shares=
        asset_id                               101       202
        2000-01-01 09:35:00.100000-05:00  0.00e+00  0.00e+00
        2000-01-01 09:40:00.100000-05:00 -5.00e+01  5.00e+01
        2000-01-01 09:45:00.100000-05:00 -5.53e-03  5.53e-03
        # executed_trades_notional=
        asset_id                               101       202
        2000-01-01 09:40:00.100000-05:00 -49980.22  49980.22
        2000-01-01 09:45:00.100000-05:00     -5.53      5.53
        # pnl=
        asset_id                            101    202
        2000-01-01 09:35:00.100000-05:00    NaN    NaN
        2000-01-01 09:40:00.100000-05:00 -14.26  14.26
        2000-01-01 09:45:00.100000-05:00  14.14 -14.14
        # statistics=
                                            pnl  gross_volume  net_volume       gmv  nmv       cash  net_wealth  leverage
        2000-01-01 09:35:00.100000-05:00  NaN          0.00         0.0      0.00  0.0  1000000.0   1000000.0       0.0
        2000-01-01 09:40:00.100000-05:00  0.0      99960.44         0.0  99988.95  0.0  1000000.0   1000000.0       0.1
        2000-01-01 09:45:00.100000-05:00  0.0         11.05         0.0  99971.72  0.0  1000000.0   1000000.0       0.1
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)


# #############################################################################
# TestMockedProcessForecasts2
# #############################################################################


class TestMockedProcessForecasts2(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test_mocked_system1(self) -> None:
        data = self._get_MarketData_df1()
        predictions, volatility = self._get_predictions_and_volatility1(data)
        self._run_coroutines(data, predictions, volatility)

    def test_mocked_system2(self) -> None:
        data = self._get_MarketData_df2()
        predictions, volatility = self._get_predictions_and_volatility1(data)
        self._run_coroutines(data, predictions, volatility)

    def test_mocked_system3(self) -> None:
        data = self._get_MarketData_df1()
        predictions, volatility = self._get_predictions_and_volatility2(data)
        self._run_coroutines(data, predictions, volatility)

    @pytest.mark.skip(
        "This test times out because nothing interesting happens after the first set of orders."
    )
    def test_mocked_system4(self) -> None:
        data = self._get_MarketData_df2()
        predictions, volatility = self._get_predictions_and_volatility2(data)
        self._run_coroutines(data, predictions, volatility)

    # TODO(gp): Move to core/finance/market_data_example.py or reuse some of those
    #  functions.
    @staticmethod
    def _get_MarketData_df1() -> pd.DataFrame:
        """
        Generate price series that alternates every 5 minutes.
        """
        idx = pd.date_range(
            start=pd.Timestamp(
                "2000-01-01 09:31:00-05:00", tz="America/New_York"
            ),
            end=pd.Timestamp("2000-01-01 09:55:00-05:00", tz="America/New_York"),
            freq="T",
        )
        bar_duration = "1T"
        bar_delay = "0T"
        data = cofinanc.build_timestamp_df(idx, bar_duration, bar_delay)
        price_pattern = [101.0] * 5 + [100.0] * 5
        price = price_pattern * 2 + [101.0] * 5
        data["price"] = price
        data["asset_id"] = 101
        return data

    # TODO(gp): Move to core/finance/market_data_example.py or reuse some of
    #  those functions.
    @staticmethod
    def _get_MarketData_df2() -> pd.DataFrame:
        idx = pd.date_range(
            start=pd.Timestamp(
                "2000-01-01 09:31:00-05:00", tz="America/New_York"
            ),
            end=pd.Timestamp("2000-01-01 09:55:00-05:00", tz="America/New_York"),
            freq="T",
        )
        bar_duration = "1T"
        bar_delay = "0T"
        data = cofinanc.build_timestamp_df(idx, bar_duration, bar_delay)
        data["price"] = 100
        data["asset_id"] = 101
        return data

    @staticmethod
    def _get_predictions_and_volatility1(
        market_data_df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate a signal that alternates every 5 minutes.
        """
        # Build predictions.
        asset_id = market_data_df["asset_id"][0]
        index = [
            pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:40:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:45:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:50:00-05:00", tz="America/New_York"),
        ]
        # Sanity check the index (e.g., in case we update the test).
        hdbg.dassert_is_subset(index, market_data_df["end_datetime"].to_list())
        columns = [asset_id]
        prediction_data = [
            [1],
            [-1],
            [1],
            [-1],
        ]
        predictions = pd.DataFrame(prediction_data, index, columns)
        volatility_data = [
            [1],
            [1],
            [1],
            [1],
        ]
        volatility = pd.DataFrame(volatility_data, index, columns)
        return predictions, volatility

    @staticmethod
    def _get_predictions_and_volatility2(
        market_data_df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate a signal that is only long.
        """
        # Build predictions.
        asset_id = market_data_df["asset_id"][0]
        index = [
            pd.Timestamp("2000-01-01 09:35:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:40:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:45:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:50:00-05:00", tz="America/New_York"),
        ]
        # Sanity check the index (e.g., in case we update the test).
        hdbg.dassert_is_subset(index, market_data_df["end_datetime"].to_list())
        columns = [asset_id]
        prediction_data = [
            [1],
            [1],
            [1],
            [1],
        ]
        predictions = pd.DataFrame(prediction_data, index, columns)
        volatility_data = [
            [1],
            [1],
            [1],
            [1],
        ]
        volatility = pd.DataFrame(volatility_data, index, columns)
        return predictions, volatility

    @staticmethod
    def _append(
        list_: List[str], label: str, data: Union[pd.Series, pd.DataFrame]
    ) -> None:
        data_str = hpandas.df_to_str(
            data, handle_signed_zeros=True, num_rows=None, precision=3
        )
        list_.append(f"{label}=\n{data_str}")

    def _run_coroutines(
        self,
        data: pd.DataFrame,
        predictions: pd.DataFrame,
        volatility: pd.DataFrame,
    ) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Build MarketData.
            replayed_delay_in_mins_or_timestamp = 5
            asset_id_name = "asset_id"
            asset_id = [data[asset_id_name][0]]
            market_data, _ = mdata.get_ReplayedTimeMarketData_from_df(
                event_loop,
                replayed_delay_in_mins_or_timestamp,
                data,
                asset_id_col_name=asset_id_name,
            )
            # Create a portfolio with one asset (and cash).
            db_connection = self.connection
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            incremental = False
            odbomdb.create_oms_tables(self.connection, incremental, asset_id_name)
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                db_connection,
                table_name,
                market_data=market_data,
                asset_ids=asset_id,
            )
            # Build OrderProcessor.
            bar_duration_in_secs = 300
            termination_condition = 4
            max_wait_time_for_order_in_secs = 10
            delay_to_accept_in_secs = 3
            delay_to_fill_in_secs = 10
            broker = portfolio.broker
            order_processor = ooprorpr.OrderProcessor(
                db_connection,
                bar_duration_in_secs,
                termination_condition,
                max_wait_time_for_order_in_secs,
                delay_to_accept_in_secs,
                delay_to_fill_in_secs,
                broker,
                asset_id_name,
            )
            # Build order process coroutine.
            order_processor_coroutine = order_processor.run_loop()
            coroutines = [
                self._test_mocked_system1(predictions, volatility, portfolio),
                order_processor_coroutine,
            ]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)

    async def _test_mocked_system1(
        self,
        predictions: pd.DataFrame,
        volatility: pd.DataFrame,
        portfolio: opdapor.DatabasePortfolio,
    ) -> None:
        """
        Run process_forecasts() logic with a given prediction df to update a
        Portfolio.
        """
        # TODO(gp): Factor this out.
        process_forecasts_dict = {
            "order_config": {
                "order_type": "price@twap",
                "order_duration_in_mins": 5,
                "execution_frequency": "1T",
            },
            "optimizer_config": {
                "backend": "pomo",
                "asset_class": "equities",
                "apply_cc_limits": None,
                "params": {
                    "style": "cross_sectional",
                    "kwargs": {
                        "bulk_frac_to_remove": 0.0,
                        "bulk_fill_method": "zero",
                        "target_gmv": 1e5,
                    },
                },
            },
            "execution_mode": "batch",
            "ath_start_time": datetime.time(9, 30),
            "trading_start_time": datetime.time(9, 35),
            "ath_end_time": datetime.time(16, 00),
            "trading_end_time": datetime.time(15, 55),
            "liquidate_at_trading_end_time": False,
            "share_quantization": 30,
        }
        spread_df = None
        restrictions_df = None
        # Run.
        await oopprfo.process_forecasts(
            predictions,
            volatility,
            portfolio,
            process_forecasts_dict,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        #
        asset_ids = portfolio.universe
        hdbg.dassert_eq(len(asset_ids), 1)
        asset_id = asset_ids[0]
        price = portfolio.market_data.get_data_for_interval(
            pd.Timestamp("2000-01-01 09:30:00-05:00", tz="America/New_York"),
            pd.Timestamp("2000-01-01 09:50:00-05:00", tz="America/New_York"),
            ts_col_name="timestamp_db",
            asset_ids=asset_ids,
            left_close=True,
            right_close=True,
        )["price"]
        #
        twap = cofinanc.resample(price, rule="5T").mean().rename("twap")
        rets = twap.pct_change().rename("rets")
        predictions_srs = predictions[asset_id].rename("prediction")
        research_pnl = (
            predictions_srs.shift(2).multiply(rets).rename("research_pnl")
        )
        #
        actual: List[str] = []
        self._append(actual, "TWAP", twap)
        self._append(actual, "rets", rets)
        self._append(actual, "prediction", predictions_srs)
        self._append(actual, "research_pnl", research_pnl)
        actual.append(portfolio)
        actual = "\n".join(map(str, actual))
        self.check_string(actual, purify_text=True)


def _get_process_forecasts_dict(order_type: str) -> Dict[str, Any]:
    """
    Build process forecasts config.

    :param order_type: The type of order. E.g., `price@twap`.
    """
    dict_ = {
        "order_config": {
            "order_type": order_type,
            "order_duration_in_mins": 5,
            "execution_frequency": "1T",
        },
        "optimizer_config": {
            "backend": "pomo",
            "asset_class": "equities",
            "apply_cc_limits": None,
            "params": {
                "style": "cross_sectional",
                "kwargs": {
                    "bulk_frac_to_remove": 0.0,
                    "bulk_fill_method": "zero",
                    "target_gmv": 1e5,
                },
            },
        },
        "execution_mode": "batch",
        "ath_start_time": datetime.time(9, 30),
        "trading_start_time": datetime.time(9, 35),
        "ath_end_time": datetime.time(16, 00),
        "trading_end_time": datetime.time(15, 55),
        "liquidate_at_trading_end_time": False,
        "share_quantization": 30,
    }
    return dict_
