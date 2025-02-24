import datetime
import logging
from typing import Optional, Tuple, Union

import pandas as pd
import pytest

import core.finance as cofinanc
import dataflow.system as dtfsys
import dataflow_amp.system.mock1.mock1_forecast_system as dtasmmfosy
import dataflow_amp.system.mock1.mock1_forecast_system_example as dtasmmfsex
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


def _get_test_NonTime_ForecastSystem() -> dtfsys.System:
    """
    Get a mock `NonTime_ForecastSystem` for unit testing.
    """
    # In this system the time periods are set manually, so the value of
    # `time_interval_str` doesn't affect tests.
    backtest_config = "mock1_v1-top2.5T.Jan2000"
    system = dtasmmfsex.get_Mock1_NonTime_ForecastSystem_for_simulation_example1(
        backtest_config
    )
    return system


# #############################################################################
# Test_Mock1_System_CheckConfig
# #############################################################################


class Test_Mock1_System_CheckConfig(dtfsys.System_CheckConfig_TestCase1):
    def test_freeze_config1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        self._test_freeze_config1(system)


# #############################################################################
# Test_Mock1_NonTime_ForecastSystem_FitPredict
# #############################################################################


class Test_Mock1_NonTime_ForecastSystem_FitPredict(
    dtfsys.NonTime_ForecastSystem_FitPredict_TestCase1
):
    @staticmethod
    def get_system() -> dtfsys.System:
        """
        Get `NonTime_ForecastSystem` and fill the `system.config`.
        """
        system = _get_test_NonTime_ForecastSystem()
        system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ] = pd.Timestamp("2000-01-01 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2000-01-31 00:00:00+0000", tz="UTC"
        )
        return system

    @pytest.mark.requires_ck_infra
    def test_fit_over_backtest_period1(self) -> None:
        system = self.get_system()
        output_col_name = "prediction"
        self._test_fit_over_backtest_period1(system, output_col_name)

    @pytest.mark.requires_ck_infra
    def test_fit_over_period1(self) -> None:
        system = self.get_system()
        start_timestamp = pd.Timestamp("2000-01-01 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2000-01-31 00:00:00+0000", tz="UTC")
        output_col_name = "prediction"
        self._test_fit_over_period1(
            system,
            start_timestamp,
            end_timestamp,
            output_col_name=output_col_name,
        )

    @pytest.mark.requires_ck_infra
    def test_fit_vs_predict1(self) -> None:
        system = self.get_system()
        # The target variable is 2 steps ahead.
        n_last_rows_to_burn = 2
        self._test_fit_vs_predict1(
            system, n_last_rows_to_burn=n_last_rows_to_burn
        )


# #############################################################################
# Test_Mock1_NonTime_ForecastSystem_FitInvariance
# #############################################################################


class Test_Mock1_NonTime_ForecastSystem_FitInvariance(
    dtfsys.NonTime_ForecastSystem_FitInvariance_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_invariance1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        start_timestamp1 = pd.Timestamp("2000-01-01 00:00:00+0000", tz="UTC")
        start_timestamp2 = pd.Timestamp("2000-01-01 09:40:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2000-01-31 00:00:00+0000", tz="UTC")
        compare_start_timestamp = pd.Timestamp(
            "2000-01-01 09:50:00+0000", tz="UTC"
        )
        self._test_invariance1(
            system,
            start_timestamp1,
            start_timestamp2,
            end_timestamp,
            compare_start_timestamp,
        )


# #############################################################################
# Test_Mock1_NonTime_ForecastSystem_CheckPnl
# #############################################################################


class Test_Mock1_NonTime_ForecastSystem_CheckPnl(
    dtfsys.NonTime_ForecastSystem_CheckPnl_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_fit_run1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ] = pd.Timestamp("2000-01-01 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2000-01-31 00:00:00+0000", tz="UTC"
        )
        self._test_fit_run1(system)


# #############################################################################
# Test_Mock1_Time_ForecastSystem1
# #############################################################################


class Test_Mock1_Time_ForecastSystem1(dtfsys.Test_Time_ForecastSystem_TestCase1):
    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        """
        Verify the contents of DAG prediction.
        """
        system = dtasmmfosy.Mock1_Time_ForecastSystem()
        (
            market_data,
            rt_timeout_in_secs_or_time,
        ) = cofinanc.get_MarketData_df4()
        # Since we are reading from a df there is no delay.
        system.config["market_data_config", "delay_in_secs"] = 0
        system.config["market_data_config", "data"] = market_data
        # We need at least 7 bars to compute volatility.
        system.config[
            "market_data_config", "replayed_delay_in_mins_or_timestamp"
        ] = pd.Timestamp("2000-01-01 10:05:00-05:00", tz="America/New_York")
        system.config["market_data_config", "days"] = 1
        # Exercise the system for multiple 5 minute intervals.
        system.config[
            "dag_runner_config", "rt_timeout_in_secs_or_time"
        ] = rt_timeout_in_secs_or_time
        system.config["dag_runner_config", "bar_duration_in_secs"] = 60 * 5
        #
        output_col_name = "prediction"
        self._test1(
            system,
            output_col_name=output_col_name,
        )


# #############################################################################
# Test_Mock1_Time_ForecastSystem_with_DataFramePortfolio1
# #############################################################################


class Test_Mock1_Time_ForecastSystem_with_DataFramePortfolio1(
    dtfsys.Time_ForecastSystem_with_DataFramePortfolio_TestCase1
):
    """
    See description in the parent class.
    """

    # These 3 tests correspond to the same tests for:
    # - DataFramePortfolio
    # - DatabasePortfolio
    # - DataFrame vs Database

    @pytest.mark.slow("~7 seconds.")
    def test1(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df1()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 10:05:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)

    @pytest.mark.slow("~7 seconds.")
    def test2(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df2()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 10:05:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)

    @pytest.mark.superslow("~32 seconds.")
    def test3(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df3()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 11:25:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)


# #############################################################################
# Test_Mock1_Time_ForecastSystem_with_DataFramePortfolio2
# #############################################################################


class Test_Mock1_Time_ForecastSystem_with_DataFramePortfolio2(
    dtfsys.Time_ForecastSystem_with_DataFramePortfolio_TestCase1
):
    """
    Test liquidating the portfolio at the end of the day.
    """

    @pytest.mark.slow("~7 seconds.")
    def test_with_liquidate_at_end_of_day1(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df1()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test_with_liquidate_at_end_of_day1(system)


# #############################################################################
# Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor1
# #############################################################################


class Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor1(
    dtfsys.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1
):
    """
    Test a Mock1 system with DatabasePortfolio.

    See description in the parent class.
    """

    # These 3 tests correspond to the same tests for:
    # - DataFramePortfolio
    # - DatabasePortfolio
    # - DataFrame vs Database

    @pytest.mark.slow("~6 seconds.")
    def test1(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df1()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 10:05:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)

    @pytest.mark.slow("~6 seconds.")
    def test2(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df2()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 10:05:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)

    # TODO(Grisha): Format golden to be indented for better readability.
    @pytest.mark.superslow("~30 seconds.")
    def test3(self) -> None:
        # Build the system.
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df3()
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Check some high level property of the Portfolio.
        expected_last_timestamp = pd.Timestamp("2000-01-01 11:25:05.100000-05:00")
        dtfsys.check_portfolio_state(self, system, expected_last_timestamp)


# #############################################################################
# Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor2
# #############################################################################


class Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor2(
    dtfsys.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1
):
    """
    Test a Mock1 system with DatabasePortfolio to verify the stopping
    condition.
    """

    @pytest.mark.slow("~6 seconds.")
    def test1(self) -> None:
        # Build the system.
        data, _ = cofinanc.get_MarketData_df1()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("data=\n%s", hpandas.df_to_str(data))
        self.assert_equal(str(data.index.min()), "2000-01-01 09:31:00-05:00")
        self.assert_equal(str(data.index.max()), "2000-01-01 10:10:00-05:00")
        # One bar is 5 mins and we want to run for 5 bars.
        rt_timeout_in_secs_or_time = 300 * 5
        system = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(system)
        # Test some properties of the system.
        order_processor = system.order_processor
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("order_processor.get_execution_signature()"))
        self.assert_equal(
            str(order_processor.start_timestamp), "2000-01-01 09:35:00-05:00"
        )
        self.assert_equal(
            str(order_processor.end_timestamp), "2000-01-01 10:00:00-05:00"
        )
        self.assertEqual(order_processor.num_filled_orders, 5)


# #############################################################################
# Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_vs_DataFramePortfolio1
# #############################################################################


class Test_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_vs_DataFramePortfolio1(
    dtfsys.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_vs_DataFramePortfolio_TestCase1
):
    """
    Run a Mock1 system with DatabasePortfolio and DataFramePortfolio and verify
    that the output is the same.

    See description in the parent class.
    """

    def run_test(
        self,
        data: pd.DataFrame,
        rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]],
    ) -> Tuple[dtfsys.System, dtfsys.System]:
        """
        Run two systems with DataFrame and Database portfolios and compare.
        """
        # Build the systems to compare.
        system_with_dataframe_portfolio = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DataFramePortfolio_example1(
            data, rt_timeout_in_secs_or_time
        )
        system_with_database_portfolio = dtasmmfsex.get_Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_example1(
            data, rt_timeout_in_secs_or_time
        )
        # Run.
        self._test1(
            system_with_dataframe_portfolio, system_with_database_portfolio
        )
        return system_with_dataframe_portfolio, system_with_database_portfolio

    # These 3 tests correspond to the same tests for:
    # - DataFramePortfolio
    # - DatabasePortfolio,
    # - DataFrame vs Database

    @pytest.mark.slow("~10 seconds.")
    def test1(self) -> None:
        """
        Run with a `cofinanc.get_MarketData_df1()`.
        """
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df1()
        self.run_test(data, rt_timeout_in_secs_or_time)

    @pytest.mark.slow("~10 seconds.")
    def test2(self) -> None:
        """
        Run with a `cofinanc.get_MarketData_df2()`.
        """
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df2()
        self.run_test(data, rt_timeout_in_secs_or_time)

    @pytest.mark.superslow("~30 seconds.")
    def test3(self) -> None:
        """
        Run with a `cofinanc.get_MarketData_df3()`.
        """
        data, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df3()
        self.run_test(data, rt_timeout_in_secs_or_time)


# #############################################################################
# Test_Mock1_NonTime_ForecastSystem_vs_Time_ForecastSystem1
# #############################################################################


class Test_Mock1_NonTime_ForecastSystem_vs_Time_ForecastSystem1(
    dtfsys.NonTime_ForecastSystem_vs_Time_ForecastSystem_TestCase1
):
    """
    See the parent class for description.
    """

    def get_NonTime_ForecastSystem(self) -> dtfsys.System:
        """
        Get `NonTime_ForecastSystem` for unit testing.
        """
        # TODO(Grisha): @Dan Write a function that extracts the latest available universe.
        universe_version = "v1"
        # In the current system, the time periods are set manually,
        # so the value of `time_interval_str` (e.g., "2022-01-01_2022-02-01")
        # doesn't affect tests.
        backtest_config = f"mock1_{universe_version}-all.5T.Jan2000"
        non_time_system = dtasmmfsex.get_Mock1_NonTime_ForecastSystem_example1(
            backtest_config
        )
        return non_time_system

    def get_Time_ForecastSystem(self) -> dtfsys.System:
        """
        See description in the parent test case class.
        """
        # Load market data for replaying.
        market_data_df, rt_timeout_in_secs_or_time = cofinanc.get_MarketData_df5()
        time_system = dtasmmfsex.get_Mock1_Time_ForecastSystem_example1()
        # TODO(Grisha): @Dan Pass "rt_timeout_in_secs_or_time" through kwargs.
        # Make system to run for 3 5-minute intervals.
        time_system.config[
            "dag_runner_config", "rt_timeout_in_secs_or_time"
        ] = rt_timeout_in_secs_or_time
        time_system.config["market_data_config", "data"] = market_data_df
        return time_system

    @pytest.mark.slow("~8 seconds.")
    def test1(self) -> None:
        output_col_name = "prediction"
        self._test1(output_col_name)
