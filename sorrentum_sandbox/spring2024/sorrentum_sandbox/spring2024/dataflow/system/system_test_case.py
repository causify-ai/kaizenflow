"""
Import as:

import dataflow.system.system_test_case as dtfssyteca
"""

import abc
import asyncio
import datetime
import logging
import os
from typing import Any, Coroutine, List, Optional, Tuple

import pandas as pd
import pytest

import dataflow.core as dtfcore
import dataflow.system.system as dtfsyssyst
import dataflow.system.system_builder_utils as dtfssybuut
import dataflow.system.system_signature as dtfsysysig
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import market_data as mdata
import oms as oms
import oms.test.oms_db_helper as otodh

_LOG = logging.getLogger(__name__)


# #############################################################################
# Utils
# #############################################################################


def run_NonTime_ForecastSystem_from_backtest_config(
    self: Any,
    system: dtfsyssyst.System,
    method: str,
    config_tag: str,
    use_unit_test_log_dir: bool,
) -> dtfcore.ResultBundle:
    """
    Run `NonTime_ForecastSystem` DAG with the specified fit / predict method
    and using the backtest parameters from `SystemConfig`.

    :param system: system object to extract `DagRunner` from
    :param method: "fit" or "predict"
    :param config_tag: tag used to freeze the system config by `check_SystemConfig()`
    :param use_unit_test_log_dir: whether to use unit test log dir or not
    :return: result bundle
    """
    hdbg.dassert_in(method, ["fit", "predict"])
    if use_unit_test_log_dir:
        dtfssybuut.apply_unit_test_log_dir(self, system)
    else:
        hdbg.dassert_in("system_log_dir", system.config)
    # Build `DagRunner`.
    dag_runner = system.dag_runner
    hdbg.dassert_isinstance(dag_runner, dtfcore.DagRunner)
    # Check the system config against the frozen value.
    dtfsysysig.check_SystemConfig(self, system, config_tag)
    # Set the time boundaries.
    start_datetime = system.config[
        "backtest_config", "start_timestamp_with_lookback"
    ]
    end_datetime = system.config["backtest_config", "end_timestamp"]
    # Run.
    if method == "fit":
        dag_runner.set_fit_intervals(
            [(start_datetime, end_datetime)],
        )
        result_bundle = dag_runner.fit()
    elif method == "predict":
        dag_runner.set_predict_intervals(
            [(start_datetime, end_datetime)],
        )
        result_bundle = dag_runner.predict()
    else:
        raise ValueError("Invalid method='%s'" % method)
    return result_bundle


def run_Time_ForecastSystem(
    self: Any,
    system: dtfsyssyst.System,
    config_tag: str,
    use_unit_test_log_dir: bool,
    *,
    check_config: bool = True,
) -> List[dtfcore.ResultBundle]:
    """
    Run `Time_ForecastSystem` with predict method.

    :param system: `Time_ForecastSystem` object
    :param config_tag: tag used to freeze the system config by `check_SystemConfig()`
    :param use_unit_test_log_dir: whether to use unit test log dir or not
    :param check_config: whether to check the config against the frozen value
    :return: `DagRunner` result bundles
    """
    if use_unit_test_log_dir:
        dtfssybuut.apply_unit_test_log_dir(self, system)
    else:
        hdbg.dassert_in("system_log_dir", system.config)
    with hasynci.solipsism_context() as event_loop:
        coroutines = []
        # Complete the system config.
        system.config["event_loop_object"] = event_loop
        # Create a `DagRunner`.
        dag_runner = system.dag_runner
        _LOG.info(
            "\n"
            + hprint.frame("Final system config")
            + "\n"
            + hprint.indent(str(system.config))
            + "\n"
            + hprint.frame("End config")
        )
        if check_config:
            # Check the system config against the frozen value.
            dtfsysysig.check_SystemConfig(self, system, config_tag)
        coroutines.append(dag_runner.predict())
        #
        if "order_processor_config" in system.config:
            # Get the `OrderProcessor` coroutine.
            order_processor_coroutine = system.order_processor_coroutine
            hdbg.dassert_isinstance(order_processor_coroutine, Coroutine)
            coroutines.append(order_processor_coroutine)
        #
        results = hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)
        # Extract the result bundles from the `DagRunner`.
        result_bundles = results[0]
    return result_bundles


def get_test_file_path(self_: Any) -> str:
    """
    Get path to a file with market data; use in unit tests.
    """
    use_only_test_class = True
    dst_dir = self_.get_s3_input_dir(use_only_test_class=use_only_test_class)
    # TODO(Grisha): consider exposing if needed.
    file_name = "test_data.csv.gz"
    file_path = os.path.join(dst_dir, file_name)
    return file_path


def save_Ccxt_MarketData(
    file_path: str,
    full_symbols: Optional[List[ivcu.FullSymbol]],
    im_client_params: Any,
    wall_clock_time: pd.Timestamp,
    *,
    period: pd.Timedelta = pd.Timedelta("15D"),
) -> None:
    # pylint: disable=line-too-long
    """
    Dump data from a CCXT `MarketData` for the last `period` and ending to the
    current wall clock so that it can be used as `ReplayedMarketData`.

    :param full_symbols: full symbols to load data for
        If `None`, all the symbols from the universe are taken
    :param im_client_params: params to initialize `ImClient`
    :param wall_clock_time: wall clock time
    :param period: how much of data is needed

    ```
      index                    end_ts   asset_id       full_symbol      open       high        low     close   volume              knowledge_timestamp                  start_ts
    0     0 2021-12-19 19:00:00-05:00 1182743717 binance::BTC_BUSD 46681.500 46687.4000 46620.0000 46678.400   47.621 2022-07-09 16:21:44.328375+00:00 2021-12-19 18:59:00-05:00
    1     1 2021-12-19 19:00:00-05:00 1464553467 binance::ETH_USDT  3922.510  3927.4500  3920.1900  3927.060 1473.723 2022-06-24 11:10:10.287766+00:00 2021-12-19 18:59:00-05:00
    2     2 2021-12-19 19:00:00-05:00 1467591036 binance::BTC_USDT 46668.650 46677.2200 46575.0000 46670.340  620.659 2022-07-09 12:07:51.240219+00:00 2021-12-19 18:59:00-05:00
    ```
    """
    # pylint: disable=line-too-long
    im_client = icdcl.get_CcxtHistoricalPqByTileClient_example1(
        **im_client_params
    )
    if full_symbols is None:
        # Get all full symbols in the universe.
        full_symbols = im_client.get_universe()
    asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)
    columns = None
    columns_remap = None
    market_data_client = mdata.get_HistoricalImClientMarketData_example1(
        im_client,
        asset_ids,
        columns,
        columns_remap,
        wall_clock_time=wall_clock_time,
    )
    # We should have data available for the period [`wall_clock_time` - `period`, `wall_clock_time`).
    mdata.save_market_data(market_data_client, file_path, period)
    _LOG.warning("Updated file '%s'", file_path)


# #############################################################################
# System_CheckConfig_TestCase1
# #############################################################################


class System_CheckConfig_TestCase1(hunitest.TestCase):
    """
    Check the config.
    """

    def _test_freeze_config1(self, system: dtfsyssyst.System) -> None:
        """
        Freeze config.
        """
        hdbg.dassert_isinstance(system, dtfsyssyst.System)
        dtfssybuut.apply_unit_test_log_dir(self, system)
        # Build `DagRunner`.
        _ = system.dag_runner
        # TODO(gp): Use check_SystemConfig.
        txt = []
        txt.append(hprint.frame("system_config"))
        txt.append(str(system.config))
        # Check.
        txt = "\n".join(txt)
        txt = hunitest.filter_text("trade_date:", txt)
        txt = hunitest.filter_text("log_dir:", txt)
        self.check_string(txt, purify_text=True, fuzzy_match=True)


# #############################################################################
# NonTime_ForecastSystem1_FitPredict_TestCase1
# #############################################################################


class NonTime_ForecastSystem_FitPredict_TestCase1(hunitest.TestCase):
    """
    Test fit() and predict() methods on a System.
    """

    def _test_fit_over_backtest_period1(
        self,
        system: dtfsyssyst.System,
        output_col_name: str,
    ) -> None:
        """
        - Fit a System over the backtest_config period
        - Save the signature of the system
        """
        method = "fit"
        # TODO(Grisha): @Dan Rename to "forecast_system" in CmTask2739 "Introduce `NonTime_ForecastSystem`."
        config_tag = "forecast_system"
        use_unit_test_log_dir = True
        result_bundle = run_NonTime_ForecastSystem_from_backtest_config(
            self, system, method, config_tag, use_unit_test_log_dir
        )
        # Check outcome.
        actual = dtfsysysig.get_signature(
            system.config, result_bundle, output_col_name
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)

    def _test_fit_over_period1(
        self,
        system: dtfsyssyst.System,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        *,
        output_col_name: str = "prediction",
    ) -> None:
        """
        - Fit a System over the given period
        - Save the signature of the system
        """
        dtfssybuut.apply_unit_test_log_dir(self, system)
        # Build `DagRunner`.
        dag_runner = system.dag_runner
        # Set the time boundaries.
        dag_runner.set_fit_intervals(
            [(start_timestamp, end_timestamp)],
        )
        # Run.
        result_bundle = dag_runner.fit()
        # Check outcome.
        actual = dtfsysysig.get_signature(
            system.config, result_bundle, output_col_name
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)

    def _test_fit_vs_predict1(
        self,
        system: dtfsyssyst.System,
        *,
        n_last_rows_to_burn: Optional[int] = None,
    ) -> None:
        """
        Check that `predict()` matches `fit()` on the same data, when the model
        is frozen.

        :param n_last_rows_to_burn: the number of rows to remove from
            the fit and predict results. When a model is fitting it
            cannot compute a N-steps-ahead target but when a model has
            been already fit it can compute it
        """
        use_unit_test_log_dir = True
        # Fit.
        method = "fit"
        config_tag = "forecast_system"
        fit_result_bundle = run_NonTime_ForecastSystem_from_backtest_config(
            self, system, method, config_tag, use_unit_test_log_dir
        )
        fit_df = fit_result_bundle.result_df
        # Predict.
        method = "predict"
        config_tag = "forecast_system"
        predict_result_bundle = run_NonTime_ForecastSystem_from_backtest_config(
            self, system, method, config_tag, use_unit_test_log_dir
        )
        predict_df = predict_result_bundle.result_df
        if n_last_rows_to_burn is not None:
            hdbg.dassert_isinstance(n_last_rows_to_burn, int)
            hpandas.dassert_strictly_increasing_index(fit_df)
            hpandas.dassert_strictly_increasing_index(predict_df)
            fit_df = fit_df.head(-n_last_rows_to_burn)
            predict_df = predict_df.head(-n_last_rows_to_burn)
        # Check.
        self.assert_dfs_close(fit_df, predict_df)


# #############################################################################
# NonTime_ForecastSystem_FitInvariance_TestCase1
# #############################################################################


class NonTime_ForecastSystem_FitInvariance_TestCase1(hunitest.TestCase):
    """
    Check the behavior of a System for different amount of passed data history.
    """

    def _test_invariance1(
        self,
        system: dtfsyssyst.System,
        start_timestamp1: pd.Timestamp,
        start_timestamp2: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        compare_start_timestamp: pd.Timestamp,
    ) -> None:
        """
        Test output invariance over different history lengths.
        """
        dtfssybuut.apply_unit_test_log_dir(self, system)
        # Run dag_runner1.
        dag_runner1 = system.dag_runner
        dag_runner1.set_fit_intervals(
            [(start_timestamp1, end_timestamp)],
        )
        result_bundle1 = dag_runner1.fit()
        result_df1 = result_bundle1.result_df
        # Run dag_runner2.
        dag_runner2 = system.dag_runner
        dag_runner2.set_fit_intervals(
            [(start_timestamp2, end_timestamp)],
        )
        result_bundle2 = dag_runner2.fit()
        result_df2 = result_bundle2.result_df
        # Compare.
        result_df1 = result_df1[compare_start_timestamp:]
        result_df2 = result_df2[compare_start_timestamp:]
        self.assert_equal(str(result_df1), str(result_df2), fuzzy_match=True)


# #############################################################################
# NonTime_ForecastSystem_CheckPnl_TestCase1
# #############################################################################


class NonTime_ForecastSystem_CheckPnl_TestCase1(hunitest.TestCase):
    def _test_fit_run1(
        self,
        system: dtfsyssyst.System,
    ) -> None:
        method = "fit"
        config_tag = "forecast_system"
        use_unit_test_log_dir = True
        result_bundle = run_NonTime_ForecastSystem_from_backtest_config(
            self, system, method, config_tag, use_unit_test_log_dir
        )
        # Check the pnl.
        forecast_evaluator_from_prices_dict = system.config[
            "research_forecast_evaluator_from_prices"
        ].to_dict()
        signature, _ = dtfsysysig.get_research_pnl_signature(
            result_bundle, forecast_evaluator_from_prices_dict
        )
        self.check_string(signature, fuzzy_match=True, purify_text=True)


# #############################################################################
# Test_Time_ForecastSystem_TestCase1
# #############################################################################


class Test_Time_ForecastSystem_TestCase1(hunitest.TestCase):
    """
    Test a System composed of:

    - a `ReplayedMarketData` (providing fake data and features)
    - a time DAG
    """

    def _test1(
        self,
        system: dtfsyssyst.System,
        *,
        output_col_name: str = "prediction",
    ) -> None:
        # Run the system.
        config_tag = "forecast_system"
        use_unit_test_log_dir = True
        result_bundles = run_Time_ForecastSystem(
            self, system, config_tag, use_unit_test_log_dir
        )
        # Check the run signature.
        result_bundle = result_bundles[-1]
        actual = dtfsysysig.get_signature(
            system.config, result_bundle, output_col_name
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)


# #############################################################################
# Time_ForecastSystem_with_DataFramePortfolio_TestCase1
# #############################################################################


class Time_ForecastSystem_with_DataFramePortfolio_TestCase1(hunitest.TestCase):
    """
    Run for an extended period of time a system containing:

    - a timed DAG
    - ReplayedMarketData
    - DataFrame portfolio
    - DataFrame Broker

    Freeze the config and the output of the system.
    """

    # TODO(Grisha): there is some code that is common for
    #  `Time_ForecastSystem_with_DataFramePortfolio_TestCase1`
    #  and
    #  `Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1`
    #  that we should factor out.
    def _test_dataframe_portfolio_helper(
        self,
        system: dtfsyssyst.System,
        *,
        trading_end_time: Optional[datetime.time] = None,
        liquidate_at_trading_end_time: bool = False,
        add_system_config: bool = True,
        add_run_signature: bool = True,
    ) -> str:
        """
        Run a System with a DataframePortfolio.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "trading_end_time liquidate_at_trading_end_time "
                    "add_system_config add_run_signature"
                )
            )
        # Set `trading_end_time`.
        if trading_end_time is not None:
            system.config[
                "process_forecasts_node_dict",
                "process_forecasts_dict",
                "trading_end_time",
            ] = trading_end_time
        # Set `liquidate_at_trading_end_time`.
        system.config[
            "process_forecasts_node_dict",
            "process_forecasts_dict",
            "liquidate_at_trading_end_time",
        ] = liquidate_at_trading_end_time
        # 1) Run the system.
        config_tag = "dataframe_portfolio"
        use_unit_test_log_dir = True
        result_bundles = run_Time_ForecastSystem(
            self, system, config_tag, use_unit_test_log_dir
        )
        # 2) Check the run signature.
        # In a dataframe-based system, there is not order processor.
        add_order_processor_signature = False
        actual = dtfsysysig.get_signature_from_result_bundle(
            system,
            result_bundles,
            add_system_config,
            add_run_signature,
            add_order_processor_signature,
        )
        # 3) Check the state of the Portfolio after forced liquidation.
        if liquidate_at_trading_end_time:
            # The Portfolio should have no holdings after the end of trading.
            portfolio = system.portfolio
            has_no_holdings = portfolio.has_no_holdings()
            last_portfolio_timestamp = portfolio.get_last_timestamp()
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    hprint.to_str("last_portfolio_timestamp has_no_holdings")
                )
            self.assertLess(trading_end_time, last_portfolio_timestamp.time())
            self.assertTrue(has_no_holdings)
        return actual

    def _test1(self, system: dtfsyssyst.System) -> None:
        """
        - Run a system:
            - Using a DataFramePortfolio
            - Freezing the output
        """
        liquidate_at_trading_end_time = False
        actual = self._test_dataframe_portfolio_helper(
            system,
            liquidate_at_trading_end_time=liquidate_at_trading_end_time,
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)

    def _test_with_liquidate_at_end_of_day1(
        self, system: dtfsyssyst.System
    ) -> None:
        """
        - Run a system:
            - Using a DataFramePortfolio
            - Liquidating at 10am
            - Freezing the output

        Like `_test1` but liquidating at 10am.
        """
        # Liquidate at 10am.
        trading_end_time = datetime.time(10, 0)
        liquidate_at_trading_end_time = True
        actual = self._test_dataframe_portfolio_helper(
            system,
            trading_end_time=trading_end_time,
            liquidate_at_trading_end_time=liquidate_at_trading_end_time,
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)


# #############################################################################
# Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1
# #############################################################################


class Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1(
    otodh.TestOmsDbHelper,
):
    """
    Test end-to-end system with:

    - `RealTimeDagRunner`
    - `ReplayedMarketData`
    - `DatabasePortfolio` and `OrderProcessor`
    """

    @staticmethod
    def reset() -> None:
        oms.Fill._fill_id = 0
        oms.Order._order_id = 0

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        self.reset()

    def tear_down_test(self) -> None:
        self.reset()

    # TODO(gp): -> run_system
    def _test_database_portfolio_helper(
        self,
        system: dtfsyssyst.System,
        *,
        add_system_config: bool = True,
        add_run_signature: bool = True,
        add_order_processor_signature: bool = True,
    ) -> str:
        """
        Run a System with a DatabasePortfolio.
        """
        # Add the DB connection.
        asset_id_name = system.config["market_data_config", "asset_id_col_name"]
        incremental = False
        oms.create_oms_tables(self.connection, incremental, asset_id_name)
        system.config["db_connection_object"] = self.connection
        # Run the system.
        config_tag = "database_portfolio"
        use_unit_test_log_dir = True
        result_bundles = run_Time_ForecastSystem(
            self, system, config_tag, use_unit_test_log_dir
        )
        # Check the run signature.
        actual = dtfsysysig.get_signature_from_result_bundle(
            system,
            result_bundles,
            add_system_config,
            add_run_signature,
            add_order_processor_signature,
        )
        return actual

    def _test1(self, system: dtfsyssyst.System) -> None:
        """
        Run a system using the desired DB portfolio and freeze the output.
        """
        actual = self._test_database_portfolio_helper(system)
        self.check_string(actual, fuzzy_match=True, purify_text=True)


# #############################################################################
# NonTime_ForecastSystem_vs_Time_ForecastSystem_TestCase1
# #############################################################################


class NonTime_ForecastSystem_vs_Time_ForecastSystem_TestCase1(hunitest.TestCase):
    """
    Reconcile `NonTime_ForecastSystem` and `Time_ForecastSystem`.

    Make sure that `NonTime_ForecastSystem` and `Time_ForecastSystem`
    produce the same predictions.
    """

    @staticmethod
    def reset() -> None:
        oms.Fill._fill_id = 0
        oms.Order._order_id = 0

    @staticmethod
    def postprocess_result_bundle(
        result_bundle: dtfcore.ResultBundle,
    ) -> dtfcore.ResultBundle:
        """
        Postprocess result bundle to unify system output format for comparison.

        - Clear index column name since it may differ for systems,
          e.g. "start_ts" and "start_datetime"
        """
        result_bundle_df = result_bundle.result_df
        result_bundle_df.index.name = None
        result_bundle.result_df = result_bundle_df
        return result_bundle

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        self.reset()

    def tear_down_test(self) -> None:
        self.reset()

    @abc.abstractmethod
    def get_NonTime_ForecastSystem(self) -> dtfsyssyst.System:
        """
        Get the `NonTime_ForecastSystem` to be compared to the
        `Time_ForecastSystem`.
        """

    @abc.abstractmethod
    def get_Time_ForecastSystem(self) -> dtfsyssyst.System:
        """
        Get the `Time_ForecastSystem` to be compared to the
        `NonTime_ForecastSystem`.
        """

    # TODO(Grisha): Consolidate with `dtfsysysig.get_signature()`.
    def get_signature(self, result_bundle: dtfcore.ResultBundle, col: str) -> str:
        txt: List[str] = []
        #
        txt.append(hprint.frame(col))
        result_df = result_bundle.result_df
        data = result_df[col].dropna(how="all").round(3)
        data_str = hpandas.df_to_str(data, num_rows=None, precision=3)
        txt.append(data_str)
        #
        res = "\n".join(txt)
        return res

    def get_NonTime_ForecastSystem_signature(
        self, non_time_system: dtfsyssyst.System, output_col_name: str
    ) -> str:
        """
        Get `NonTime_ForecastSystem` outcome signature.
        """
        # Run the system.
        method = "predict"
        config_tag = "non_time_system"
        use_unit_test_log_dir = True
        non_time_system_result_bundle = (
            run_NonTime_ForecastSystem_from_backtest_config(
                self, non_time_system, method, config_tag, use_unit_test_log_dir
            )
        )
        non_time_system_result_bundle = self.postprocess_result_bundle(
            non_time_system_result_bundle
        )
        non_time_system_signature = self.get_signature(
            non_time_system_result_bundle, output_col_name
        )
        return non_time_system_signature

    # TODO(Grisha): @Dan factor out the code, given `system_test_case.py`.
    def get_Time_ForecastSystem_signature(
        self, time_system: dtfsyssyst.System, output_col_name: str
    ) -> str:
        """
        Get `Time_ForecastSystem` outcome signature.
        """
        # Run the system.
        config_tag = "time_system"
        use_unit_test_log_dir = True
        time_system_result_bundles = run_Time_ForecastSystem(
            self, time_system, config_tag, use_unit_test_log_dir
        )
        # Get the last result bundle data for comparison.
        time_system_result_bundle = time_system_result_bundles[-1]
        time_system_result_bundle = self.postprocess_result_bundle(
            time_system_result_bundle
        )
        time_system_signature = self.get_signature(
            time_system_result_bundle, output_col_name
        )
        return time_system_signature

    @staticmethod
    def _update_NonTime_ForecastSystem_config(
        non_time_system: dtfsyssyst.NonTime_ForecastSystem,
        time_system: dtfsyssyst.Time_ForecastSystem,
    ) -> dtfsyssyst.System:
        """
        Update `NonTimeForecastSystem.config` using values from
        `TimeForecastSystem.config`.

        The problem is that run time period is set differently for the Systems:
            - `NonTime_ForecastSystem`: using backtest_config,
                e.g., `ccxt_v7-all.5T.2022-01-01_2022-02-01`
            - `Time_ForecastSystem`: using `rt_timeout_in_secs_or_time`,
                e.g., run start time is `19:00` and `rt_timeout_in_secs_or_time`
                (for how long to run the System) is 900 seconds (15 minutes) ->
                run stop time is `19:15`

        For the reconciliation tests the System run period must be the same for
        both Systems. Given 2 ways of specifying the run period it is easy to
        get Systems out of sync. The function ensures that both Systems run for
        the same time period. E.g., from `19:00` to `19:15`.
        """
        # Time when a `Time_ForecastSystem` starts running.
        start_timestamp = time_system.config[
            "market_data_config", "replayed_delay_in_mins_or_timestamp"
        ]
        # This is needed to know for how long a System runs.
        rt_timeout_in_secs_or_time = time_system.config[
            "dag_runner_config", "rt_timeout_in_secs_or_time"
        ]
        # TODO(Grisha): Won't work if `rt_timeout_in_secs_or_time` is not in seconds.
        hdbg.dassert_isinstance(rt_timeout_in_secs_or_time, int)
        end_timestamp = start_timestamp + pd.Timedelta(
            rt_timeout_in_secs_or_time, "seconds"
        )
        # Align on a bar. E.g., if `end_ts` is `19:14` -> the last bar computed
        # will be `19:10` assuming that the bar duration is 5 minutes.
        bar_duration_in_secs = time_system.config[
            "dag_runner_config", "bar_duration_in_secs"
        ]
        last_bar_timestamp = hdateti.find_bar_timestamp(
            end_timestamp, bar_duration_in_secs, mode="floor"
        )
        # Account for market delay. E.g., when computing a bar 19:10 the Time System starts
        # reading data at 19:10:10 (market delay is 10 seconds). In this case end_timestamp
        # is 2021-12-26 19:10:10 (last bar + market delay) and start_timestamp is
        # 2021-12-22 19:10:10, i.e. data at 2021-12-22 19:10:00 should be not be available
        # for the NonTime System to mimic the Time System.
        delay_in_secs = time_system.config["market_data_config"]["delay_in_secs"]
        hdbg.dassert_isinstance(delay_in_secs, int)
        last_bar_timestamp_with_delay = last_bar_timestamp + pd.Timedelta(
            seconds=delay_in_secs
        )
        # Get the amount of history required before a System starts.
        history_lookback = time_system.config[
            "market_data_config", "history_lookback"
        ]
        hdbg.dassert_isinstance(history_lookback, pd.Timedelta)
        # Use the last bar computed by the Time System to get the start timestamp for the
        # NonTime System because when comparing the Systems we use only the results that
        # correspond to the last bar computed by the Time System.
        start_timestamp_with_lookback = (
            last_bar_timestamp_with_delay - history_lookback
        )
        # Update the `NonTimeForecastSystem.config`.
        non_time_system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ] = start_timestamp_with_lookback
        non_time_system.config[
            "backtest_config", "end_timestamp"
        ] = last_bar_timestamp_with_delay
        return non_time_system

    def _test1(self, output_col_name: str) -> None:
        # Run the Time System.
        time_system = self.get_Time_ForecastSystem()
        time_system_signature = self.get_Time_ForecastSystem_signature(
            time_system, output_col_name
        )
        # Build the Non-Time System.
        non_time_system = self.get_NonTime_ForecastSystem()
        # Overwrite Non-Time System's config values using Time System's config values
        # to guarantee that both System are in sync.
        non_time_system = self._update_NonTime_ForecastSystem_config(
            non_time_system, time_system
        )
        # Run the Non-Time System.
        non_time_system_signature = self.get_NonTime_ForecastSystem_signature(
            non_time_system, output_col_name
        )
        # Compare system results.
        self.assert_equal(
            time_system_signature,
            non_time_system_signature,
            fuzzy_match=True,
            purify_text=True,
            purify_expected_text=True,
        )


# #############################################################################
# Test_Time_ForecastSystem_vs_Time_ForecastSystem_with_DataFramePortfolio_TestCase1
# #############################################################################


# TODO(Grisha): Use for the Mock1 pipeline.
class Test_Time_ForecastSystem_vs_Time_ForecastSystem_with_DataFramePortfolio_TestCase1(
    hunitest.TestCase
):
    """
    Reconcile `Time_ForecastSystem` and
    `Time_ForecastSystem_with_DataFramePortfolio`.

    It is expected that research PnL is strongly correlated with the PnL from Portfolio.
    2 versions of PnL may differ by a constant so we use correlation to compare them
    instead of comparing the values directly.

    Add `ForecastEvaluatorFromPrices` to `Time_ForecastSystem` to compute research PnL.
    """

    @abc.abstractmethod
    def get_Time_ForecastSystem(self) -> dtfsyssyst.System:
        """
        Get `Time_ForecastSystem` and fill the `system.config`.
        """

    def run_Time_ForecastSystem(self) -> Tuple[str, pd.Series]:
        """
        Run `Time_ForecastSystem` and compute research PnL.
        """
        time_system = self.get_Time_ForecastSystem()
        # Run the system and check the config against the frozen value.
        config_tag = "time_system"
        use_unit_test_log_dir = True
        time_system_result_bundles = run_Time_ForecastSystem(
            self, time_system, config_tag, use_unit_test_log_dir
        )
        # Get the last result bundle data for comparison.
        result_bundle = time_system_result_bundles[-1]
        forecast_evaluator_from_prices_dict = time_system.config[
            "research_forecast_evaluator_from_prices"
        ].to_dict()
        signature, research_pnl = dtfsysysig.get_research_pnl_signature(
            result_bundle, forecast_evaluator_from_prices_dict
        )
        return signature, research_pnl

    @abc.abstractmethod
    def get_Time_ForecastSystem_with_DataFramePortfolio(
        self,
    ) -> dtfsyssyst.System:
        """
        Get `Time_ForecastSystem_with_DataFramePortfolio` and fill the
        `system.config`.
        """

    def run_Time_ForecastSystem_with_DataFramePortfolio(
        self,
    ) -> Tuple[str, pd.Series]:
        """
        Run `Time_ForecastSystem_with_DataFramePortfolio` and compute Portfolio
        PnL.
        """
        time_system = self.get_Time_ForecastSystem_with_DataFramePortfolio()
        # Run the system and check the config against the frozen value.
        config_tag = "dataframe_portfolio"
        use_unit_test_log_dir = True
        _ = run_Time_ForecastSystem(
            self, time_system, config_tag, use_unit_test_log_dir
        )
        # Compute Portfolio PnL. Get the number of data points
        # that is sufficient for a reconciliation.
        num_periods = 20
        signature, pnl = dtfsysysig.get_portfolio_signature(
            time_system.portfolio, num_periods=num_periods
        )
        return signature, pnl

    def _test1(self) -> None:
        actual = []
        # Compute research PnL and check in the signature.
        research_signature, research_pnl = self.run_Time_ForecastSystem()
        actual.append(research_signature)
        # Compute Portfolio PnL and check in the signature.
        (
            portfolio_signature,
            pnl,
        ) = self.run_Time_ForecastSystem_with_DataFramePortfolio()
        actual.append(portfolio_signature)
        # Compute correlation for research PnL vs Portfolio PnL.
        # TODO(Grisha): copy-pasted from `system_test_case.py`, try to share code.
        if min(pnl.count(), research_pnl.count()) > 1:
            # Drop leading NaNs and burn the first PnL entry.
            research_pnl = research_pnl.dropna().iloc[1:]
            tail = research_pnl.size
            # We create new series because the portfolio times may be
            # disaligned from the research bar times.
            pnl1 = pd.Series(pnl.tail(tail).values)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("portfolio pnl=\n%s", pnl1)
            corr_samples = min(tail, pnl1.size)
            pnl2 = pd.Series(research_pnl.tail(corr_samples).values)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("research pnl=\n%s", pnl2)
            correlation = pnl1.corr(pnl2)
            actual.append("\n# pnl agreement with research pnl\n")
            actual.append(f"corr = {correlation:.3f}")
            actual.append(f"corr_samples = {corr_samples}")
        # Check in the output.
        actual = "\n".join(map(str, actual))
        self.check_string(actual, fuzzy_match=True, purify_text=True)


# #############################################################################
# Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_vs_DataFramePortfolio_TestCase1
# #############################################################################


class Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_vs_DataFramePortfolio_TestCase1(
    Time_ForecastSystem_with_DataFramePortfolio_TestCase1,
    Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1,
):
    def _test1(
        self,
        system_with_dataframe_portfolio: dtfsyssyst.System,
        system_with_database_portfolio: dtfsyssyst.System,
    ) -> None:
        """
        Test that the outcome is the same when running a System with a
        DataFramePortfolio vs running one with a DatabasePortfolio.
        """
        # The config signature is different (since the systems are different) so
        # we only compare the result of the run.
        add_system_config = False
        add_run_signature = True
        # Only the system with DatabasePortfolio but not a DataFramePortfolio
        # has the OrderProcessor so we don't print it.
        add_order_processor_signature = False
        actual = self._test_dataframe_portfolio_helper(
            system_with_dataframe_portfolio,
            add_system_config=add_system_config,
            add_run_signature=add_run_signature,
        )
        # Make sure there is something in the actual outcome.
        hdbg.dassert_lte(10, len(actual.split("\n")))
        expected = self._test_database_portfolio_helper(
            system_with_database_portfolio,
            add_system_config=add_system_config,
            add_run_signature=add_run_signature,
            add_order_processor_signature=add_order_processor_signature,
        )
        #
        hdbg.dassert_lte(10, len(expected.split("\n")))
        # Remove `DataFrame*` and `Database*` to avoid mismatches from the fact
        # that the systems are different.
        regex = (
            "DataFramePortfolio|DatabasePortfolio|DataFrameBroker|DatabaseBroker"
        )
        actual = hunitest.filter_text(regex, actual)
        expected = hunitest.filter_text(regex, expected)
        self.assert_equal(
            actual,
            expected,
            fuzzy_match=True,
            purify_text=True,
            purify_expected_text=True,
        )
