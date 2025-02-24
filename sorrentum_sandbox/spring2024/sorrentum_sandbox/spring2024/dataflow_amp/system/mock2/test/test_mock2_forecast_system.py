import pandas as pd
import pytest

import dataflow.system as dtfsys
import dataflow_amp.system.mock2.mock2_forecast_system_example as dtasmmfsex


def _get_test_NonTime_ForecastSystem() -> dtfsys.System:
    """
    Get a mock `NonTime_ForecastSystem` for unit testing.
    """
    # In this system the time periods are set manually, so the value of
    # `time_interval_str` doesn't affect tests.
    backtest_config = "bloomberg_v1-top1.5T.2023-08-10_2023-08-31"
    system = dtasmmfsex.get_Mock2_NonTime_ForecastSystem_example2(backtest_config)
    return system


# #############################################################################
# Test_Mock2_System_CheckConfig
# #############################################################################


class Test_Mock2_System_CheckConfig(dtfsys.System_CheckConfig_TestCase1):
    def test_freeze_config1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        self._test_freeze_config1(system)


# #############################################################################
# Test_Mock2_NonTime_ForecastSystem_FitPredict
# #############################################################################


@pytest.mark.slow("Slow via GH, fast on server.")
class Test_Mock2_NonTime_ForecastSystem_FitPredict(
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
        ] = pd.Timestamp("2023-08-09 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2023-08-31 00:00:00+0000", tz="UTC"
        )
        return system

    @pytest.mark.requires_ck_infra
    def test_fit_over_backtest_period1(self) -> None:
        system = self.get_system()
        output_col_name = "vwap.ret_0.vol_adj.c"
        self._test_fit_over_backtest_period1(system, output_col_name)

    @pytest.mark.requires_ck_infra
    def test_fit_over_period1(self) -> None:
        system = self.get_system()
        start_timestamp = pd.Timestamp("2023-08-10 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2023-08-31 00:00:00+0000", tz="UTC")
        output_col_name = "vwap.ret_0.vol_adj.c"
        self._test_fit_over_period1(
            system,
            start_timestamp,
            end_timestamp,
            output_col_name=output_col_name,
        )

    @pytest.mark.requires_ck_infra
    def test_fit_vs_predict1(self) -> None:
        system = self.get_system()
        self._test_fit_vs_predict1(system)


# #############################################################################
# Test_Mock2_NonTime_ForecastSystem_FitInvariance
# #############################################################################


@pytest.mark.slow("Slow via GH, fast on server.")
class Test_Mock2_NonTime_ForecastSystem_FitInvariance(
    dtfsys.NonTime_ForecastSystem_FitInvariance_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_invariance1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        start_timestamp1 = pd.Timestamp("2023-08-10 00:00:00+0000", tz="UTC")
        start_timestamp2 = pd.Timestamp("2023-08-10 00:40:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2023-08-31 00:00:00+0000", tz="UTC")
        compare_start_timestamp = pd.Timestamp(
            "2023-08-10 00:50:00+0000", tz="UTC"
        )
        self._test_invariance1(
            system,
            start_timestamp1,
            start_timestamp2,
            end_timestamp,
            compare_start_timestamp,
        )


# #############################################################################
# Test_Mock2_NonTime_ForecastSystem_CheckPnl
# #############################################################################


@pytest.mark.slow("Slow via GH, fast on server.")
class Test_Mock2_NonTime_ForecastSystem_CheckPnl(
    dtfsys.NonTime_ForecastSystem_CheckPnl_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_fit_run1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ] = pd.Timestamp("2023-08-09 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2023-08-31 00:00:00+0000", tz="UTC"
        )
        self._test_fit_run1(system)
