import pandas as pd
import pytest

import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_forecast_system_example as dtfasccfsex
import im_v2.ccxt.data.client as icdcl


def _get_test_NonTime_ForecastSystem() -> dtfsys.System:
    """
    Get a mock `NonTime_ForecastSystem` for unit testing.
    """
    dag_builder_ctor_as_str = "dataflow_amp.pipelines.mock_bid_ask.mock_bid_ask_pipeline.MockBidAsk_DagBuilder"
    # In this system the time periods are set manually, so the value of
    # `time_interval_str` doesn't affect tests.
    backtest_config = "ccxt_v7_4-top2.5T.2024-01-01_2024-01-31"
    # Build `ImClient` config.
    im_client_config = (
        icdcl.get_CcxtBidAskHistoricalPqByTileClient_config_example1()
    )
    train_test_mode = "ins"
    # Even though this is called `Cx_NonTime_ForecastSystem`, this is already
    # general enough to work with `MockBidAsk` pipeline. In other words, there
    # is no need to create a separate System for the `MockBidAsk` pipeline.
    system = dtfasccfsex.get_Cx_NonTime_ForecastSystem_example(
        dag_builder_ctor_as_str,
        train_test_mode=train_test_mode,
        backtest_config=backtest_config,
        im_client_config=im_client_config,
    )
    return system


# #############################################################################
# Test_MockBidAsk_System_CheckConfig
# #############################################################################


class Test_MockBidAsk_System_CheckConfig(dtfsys.System_CheckConfig_TestCase1):
    def test_freeze_config1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        self._test_freeze_config1(system)


# #############################################################################
# Test_MockBidAsk_NonTime_ForecastSystem_FitPredict
# #############################################################################


class Test_MockBidAsk_NonTime_ForecastSystem_FitPredict(
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
        ] = pd.Timestamp("2024-01-01 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2024-01-31 00:00:00+0000", tz="UTC"
        )
        return system

    @pytest.mark.requires_ck_infra
    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_fit_over_backtest_period1(self) -> None:
        system = self.get_system()
        output_col_name = "level_1.bid_ask_midpoint.close.ret_0.vol_adj"
        self._test_fit_over_backtest_period1(system, output_col_name)

    @pytest.mark.requires_ck_infra
    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_fit_over_period1(self) -> None:
        system = self.get_system()
        start_timestamp = pd.Timestamp("2024-01-01 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2024-01-10 00:00:00+0000", tz="UTC")
        output_col_name = "level_1.bid_ask_midpoint.close.ret_0.vol_adj"
        self._test_fit_over_period1(
            system,
            start_timestamp,
            end_timestamp,
            output_col_name=output_col_name,
        )

    @pytest.mark.requires_ck_infra
    @pytest.mark.slow("Slow via GH, fast on server.")
    def test_fit_vs_predict1(self) -> None:
        system = self.get_system()
        self._test_fit_vs_predict1(system)


# #############################################################################
# Test_MockBidAsk_NonTime_ForecastSystem_FitInvariance
# #############################################################################


@pytest.mark.slow("Slow via GH, fast on server.")
class Test_MockBidAsk_NonTime_ForecastSystem_FitInvariance(
    dtfsys.NonTime_ForecastSystem_FitInvariance_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_invariance1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        start_timestamp1 = pd.Timestamp("2024-01-01 00:00:00+0000", tz="UTC")
        start_timestamp2 = pd.Timestamp("2024-01-10 00:00:00+0000", tz="UTC")
        end_timestamp = pd.Timestamp("2024-01-31 00:00:00+0000", tz="UTC")
        compare_start_timestamp = pd.Timestamp(
            "2024-01-20 00:00:00+0000", tz="UTC"
        )
        self._test_invariance1(
            system,
            start_timestamp1,
            start_timestamp2,
            end_timestamp,
            compare_start_timestamp,
        )


# #############################################################################
# Test_MockBidAsk_NonTime_ForecastSystem_CheckPnl
# #############################################################################


@pytest.mark.slow("Slow via GH, fast on server.")
class Test_MockBidAsk_NonTime_ForecastSystem_CheckPnl(
    dtfsys.NonTime_ForecastSystem_CheckPnl_TestCase1
):
    @pytest.mark.requires_ck_infra
    def test_fit_run1(self) -> None:
        system = _get_test_NonTime_ForecastSystem()
        system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ] = pd.Timestamp("2024-01-01 00:00:00+0000", tz="UTC")
        system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
            "2024-01-31 00:00:00+0000", tz="UTC"
        )
        # Add research Portfolio configuration.
        system = dtfsys.apply_ForecastEvaluatorFromPrices_config(system)
        self._test_fit_run1(system)
