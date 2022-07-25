"""
Import as:

import dataflow.system.test.system_test_case as dtfsytsytc
"""

import asyncio
import logging
import os
from typing import Callable, List, Tuple, Union

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import dataflow.system.system as dtfsyssyst
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import market_data as mdata
import oms as oms
import oms.test.oms_db_helper as otodh

_LOG = logging.getLogger(__name__)

# TODO(gp): -> system_test_case.py


# #############################################################################
# Utils
# #############################################################################


def get_signature(
    system_config: cconfig.Config, result_bundle: dtfcore.ResultBundle, col: str
) -> str:
    txt: List[str] = []
    #
    txt.append(hprint.frame("system_config"))
    txt.append(str(system_config))
    #
    txt.append(hprint.frame(col))
    result_df = result_bundle.result_df
    data = result_df[col].dropna(how="all").round(3)
    data_str = hunitest.convert_df_to_string(data, index=True, decimals=3)
    txt.append(data_str)
    #
    res = "\n".join(txt)
    return res


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
        # Force building the DAG runner.
        _ = system.dag_runner
        #
        txt = []
        txt.append(hprint.frame("system_config"))
        txt.append(str(system.config))
        # Check.
        txt = "\n".join(txt)
        txt = hunitest.filter_text("trade_date:", txt)
        txt = hunitest.filter_text("log_dir:", txt)
        self.check_string(txt, purify_text=True)


# #############################################################################
# ForecastSystem1_FitPredict_TestCase1
# #############################################################################


class ForecastSystem_FitPredict_TestCase1(hunitest.TestCase):
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
        # Force building the DAG runner.
        dag_runner = system.dag_runner
        hdbg.dassert_isinstance(dag_runner, dtfcore.DagRunner)
        # Set the time boundaries.
        start_datetime = system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ]
        end_datetime = system.config["backtest_config", "end_timestamp"]
        dag_runner.set_fit_intervals(
            [(start_datetime, end_datetime)],
        )
        # Run.
        result_bundle = dag_runner.fit()
        # Check outcome.
        actual = get_signature(system.config, result_bundle, output_col_name)
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
        # Force building the DAG runner.
        dag_runner = system.dag_runner
        # Set the time boundaries.
        dag_runner.set_fit_intervals(
            [(start_timestamp, end_timestamp)],
        )
        # Run.
        result_bundle = dag_runner.fit()
        # Check outcome.
        actual = get_signature(system.config, result_bundle, output_col_name)
        self.check_string(actual, fuzzy_match=True, purify_text=True)

    def _test_fit_vs_predict1(
        self,
        system: dtfsyssyst.System,
    ) -> None:
        """
        Check that `predict()` matches `fit()` on the same data, when the model
        is frozen.
        """
        # Force building the DAG runner.
        dag_runner = system.dag_runner
        # Get the time boundaries.
        start_datetime = system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ]
        end_datetime = system.config["backtest_config", "end_timestamp"]
        # Fit.
        dag_runner.set_fit_intervals(
            [(start_datetime, end_datetime)],
        )
        fit_result_bundle = dag_runner.fit()
        fit_df = fit_result_bundle.result_df
        # Predict.
        dag_runner.set_predict_intervals(
            [(start_datetime, end_datetime)],
        )
        predict_result_bundle = dag_runner.predict()
        predict_df = predict_result_bundle.result_df
        # Check.
        self.assert_dfs_close(fit_df, predict_df)


# #############################################################################
# ForecastSystem_FitInvariance_TestCase1
# #############################################################################


class ForecastSystem_FitInvariance_TestCase1(hunitest.TestCase):
    """
    Check the behavior of a System for different amount of passed data history.
    """

    def _test_invariance1(
        self,
        system_builder: Callable,
        start_timestamp1: pd.Timestamp,
        start_timestamp2: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        compare_start_timestamp: pd.Timestamp,
    ) -> None:
        """
        Test output invariance over different history lengths.
        """
        # Run dag_runner1.
        system = system_builder()
        dag_runner1 = system.dag_runner
        dag_runner1.set_fit_intervals(
            [(start_timestamp1, end_timestamp)],
        )
        result_bundle1 = dag_runner1.fit()
        result_df1 = result_bundle1.result_df
        # Run dag_runner2.
        system = system_builder()
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
# ForecastSystem_CheckPnl_TestCase1
# #############################################################################


class ForecastSystem_CheckPnl_TestCase1(hunitest.TestCase):
    def _test_fit_run1(
        self,
        system: dtfsyssyst.System,
    ) -> None:
        dag_runner = system.dag_runner
        # Set the time boundaries.
        start_datetime = system.config[
            "backtest_config", "start_timestamp_with_lookback"
        ]
        end_datetime = system.config["backtest_config", "end_timestamp"]
        dag_runner.set_fit_intervals(
            [(start_datetime, end_datetime)],
        )
        # Run.
        result_bundle = dag_runner.fit()
        # Check.
        system_tester = SystemTester()
        # TODO(gp): Factor out these params somehow.
        price_col = system.config["research_pnl", "price_col"]
        volatility_col = system.config["research_pnl", "volatility_col"]
        prediction_col = system.config["research_pnl", "prediction_col"]
        signature, _ = system_tester.get_research_pnl_signature(
            result_bundle,
            price_col=price_col,
            volatility_col=volatility_col,
            prediction_col=prediction_col,
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

    def _test_save_data(
        self,
        market_data: mdata.MarketData,
        period: pd.Timedelta,
        file_path: str,
    ) -> None:
        """
        Generate test data and store it.
        """
        limit = None
        mdata.save_market_data(market_data, file_path, period, limit)
        _LOG.warning("Updated file '%s'", file_path)

    def _test1(
        self,
        system: dtfsyssyst.System,
        *,
        output_col_name: str = "prediction",
    ) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Complete system config.
            system.config["event_loop_object"] = event_loop
            # Create DAG runner.
            dag_runner = system.dag_runner
            # Run.
            coroutines = [dag_runner.predict()]
            result_bundles = hasynci.run(
                asyncio.gather(*coroutines), event_loop=event_loop
            )
            result_bundle = result_bundles[0][-1]
            actual = get_signature(system.config, result_bundle, output_col_name)
            self.check_string(actual, fuzzy_match=True, purify_text=True)


# #############################################################################
# Time_ForecastSystem_with_DataFramePortfolio_TestCase1
# #############################################################################


class Time_ForecastSystem_with_DataFramePortfolio_TestCase1(hunitest.TestCase):
    """
    Run for an extended period of time a system containing:

    - a time DAG
    - ReplayedMarketData
    - DataFrame portfolio
    - Simulated broker
    """

    def _test1(
        self,
        system: dtfsyssyst.System,
        # TODO(Grisha): @Dan pass all params via `system.config`.
        asset_ids: List[int],
        sleep_interval_in_secs: int,
        real_time_loop_time_out_in_secs: int,
    ) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Complete system config.
            system.config["market_data_config", "asset_ids"] = asset_ids
            system.config[
                "dag_runner_config", "sleep_interval_in_secs"
            ] = sleep_interval_in_secs
            system.config[
                "dag_runner_config", "real_time_loop_time_out_in_secs"
            ] = real_time_loop_time_out_in_secs
            #
            system.config["event_loop_object"] = event_loop
            portfolio = system.portfolio
            dag_runner = system.dag_runner
            # Run.
            coroutines = [dag_runner.predict()]
            result_bundles = hasynci.run(
                asyncio.gather(*coroutines), event_loop=event_loop
            )
            result_bundles = result_bundles[0]
            result_bundle = result_bundles[-1]
            system_tester = SystemTester()
            # Check output.
            portfolio = system.portfolio
            price_col = system.config["research_pnl", "price_col"]
            volatility_col = system.config["research_pnl", "volatility_col"]
            prediction_col = system.config["research_pnl", "prediction_col"]
            actual = system_tester.compute_run_signature(
                dag_runner,
                portfolio,
                result_bundle,
                price_col=price_col,
                volatility_col=volatility_col,
                prediction_col=prediction_col,
            )
            self.check_string(actual)


# #############################################################################
# Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1
# #############################################################################


class Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor_TestCase1(
    otodh.TestOmsDbHelper,
):
    """
    Test end-to-end system with:

    - `ReplayedMarketData` using synthetic bar data
    - `DatabasePortfolio` and `OrderProcessor`
    - a single asset
    - an entire trading day
    """

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def get_file_name(self) -> str:
        dir_name = self.get_input_dir(use_only_test_class=True)
        hio.create_dir(dir_name, incremental=True)
        file_name = os.path.join(dir_name, "real_time_bar_data.csv")
        _LOG.debug("file_name=%s", file_name)
        return file_name

    def _test_save_data(
        self, market_data: mdata.MarketData, period: pd.Timedelta, file_name: str
    ) -> None:
        """
        Generate data used in this test.

        end_time,start_time,asset_id,close,volume,good_bid,good_ask,sided_bid_count,sided_ask_count,day_spread,day_num_spread
        2022-01-10 09:01:00-05:00,2022-01-10 14:00:00+00:00,10971.0,,0.0,463.0,463.01,0.0,0.0,1.32,59.0
        2022-01-10 09:01:00-05:00,2022-01-10 14:00:00+00:00,13684.0,,0.0,998.14,999.4,0.0,0.0,100.03,59.0
        2022-01-10 09:01:00-05:00,2022-01-10 14:00:00+00:00,17085.0,,0.0,169.27,169.3,0.0,0.0,1.81,59.0
        2022-01-10 09:02:00-05:00,2022-01-10 14:01:00+00:00,10971.0,,0.0,463.03,463.04,0.0,0.0,2.71,119.0
        """
        # period = "last_day"
        # period = pd.Timedelta("15D")
        limit = None
        mdata.save_market_data(market_data, file_name, period, limit)
        _LOG.warning("Updated file '%s'", file_name)
        # aws s3 cp dataflow_lime/system/test/TestReplayedE8dWithMockedOms1/input/real_time_bar_data.csv s3://eglp-spm-sasm/data/market_data.20220118.csv

    # ////////////////////////////////////////////////////////////////////////////

    def _test1(self, system: dtfsyssyst.System) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Complete system config.
            system.config["event_loop_object"] = event_loop
            system.config["db_connection_object"] = self.connection
            # Build the System.
            dag_runner = system.dag_runner
            # Create the OrderProcessor.
            portfolio = system.portfolio
            # Clean the DB tables.
            asset_id_name = system.market_data.asset_id_col
            # TODO(gp): Should this be system.get_order_processor_coroutine()?
            incremental = False
            oms.create_oms_tables(self.connection, incremental, asset_id_name)
            # TODO(gp): sleep_interval_in_secs -> grid_time_in_secs
            max_wait_time_for_order_in_secs = system.config[
                "dag_runner_config", "sleep_interval_in_secs"
            ]
            order_processor = oms.get_order_processor_example1(
                self.connection,
                portfolio,
                asset_id_name,
                max_wait_time_for_order_in_secs,
            )
            real_time_loop_time_out_in_secs = system.config[
                "dag_runner_config", "real_time_loop_time_out_in_secs"
            ]
            _LOG.debug(hprint.to_str("real_time_loop_time_out_in_secs"))
            order_processor_coroutine = (
                oms.get_order_processor_coroutine_example1(
                    order_processor, portfolio, real_time_loop_time_out_in_secs
                )
            )
            # Run.
            coroutines = [dag_runner.predict(), order_processor_coroutine]
            result_bundles = hasynci.run(
                asyncio.gather(*coroutines), event_loop=event_loop
            )
            # Compute signature.
            txt = []
            txt.append(hprint.frame("system_config"))
            txt.append(str(system.config))
            # TODO(gp): This should be factored out.
            txt.append(hprint.frame("compute_run_signature"))
            result_bundles = result_bundles[0]
            result_bundle = result_bundles[-1]
            result_bundle.result_df = result_bundle.result_df.tail(40)
            system_tester = dtfsyssyst.SystemTester()
            # Check output.
            price_col = system.config[
                "process_forecasts_config",
                "forecast_evaluator_from_prices_dict",
                "init",
                "price_col",
            ]
            prediction_col = system.config[
                "process_forecasts_config", "prediction_col"
            ]
            volatility_col = system.config[
                "process_forecasts_config", "volatility_col"
            ]
            txt_tmp = system_tester.compute_run_signature(
                dag_runner,
                portfolio,
                result_bundle,
                price_col=price_col,
                volatility_col=volatility_col,
                prediction_col=prediction_col,
            )
            txt.append(txt_tmp)
            #
            actual = "\n".join(txt)
            # Remove the following line:
            # ```
            # db_connection_object: <connection object; dsn: 'user=aljsdalsd
            #   password=xxx dbname=oms_postgres_db_local
            #   host=cf-spm-dev4 port=12056', closed: 0>
            # ```
            actual = hunitest.filter_text("db_connection_object", actual)
            actual = hunitest.filter_text("log_dir:", actual)
            actual = hunitest.filter_text("trade_date:", actual)
            self.check_string(actual, purify_text=True)


# TODO(gp): Add a longer test with more assets once things are working.

# #############################################################################
# SystemTester
# #############################################################################


# TODO(gp): These functions should be free-standing.
class SystemTester:
    """
    Test a System.
    """

    def get_events_signature(self, events) -> str:
        # TODO(gp): Use events.to_str()
        actual = ["# event signature=\n"]
        events_as_str = "\n".join(
            [
                event.to_str(
                    include_tenths_of_secs=False,
                    include_wall_clock_time=False,
                )
                for event in events
            ]
        )
        actual.append("events_as_str=\n%s" % events_as_str)
        actual = "\n".join(actual)
        return actual

    def get_portfolio_signature(self, portfolio) -> Tuple[str, pd.Series]:
        actual = ["\n# portfolio signature=\n"]
        actual.append(str(portfolio))
        actual = "\n".join(actual)
        statistics = portfolio.get_historical_statistics()
        pnl = statistics["pnl"]
        _LOG.debug("pnl=\n%s", pnl)
        return actual, pnl

    # TODO(gp): @paul pass dictionaries instead of the values to mimic the
    #  interface of `ProcessForecasts`.
    def compute_run_signature(
        self,
        dag_runner,
        portfolio,
        result_bundle,
        *,
        price_col: str,
        volatility_col: str,
        prediction_col: str,
    ) -> str:
        # Check output.
        actual = []
        #
        events = dag_runner.events
        actual.append(self.get_events_signature(events))
        signature, pnl = self.get_portfolio_signature(portfolio)
        actual.append(signature)
        signature, research_pnl = self.get_research_pnl_signature(
            result_bundle,
            price_col=price_col,
            volatility_col=volatility_col,
            prediction_col=prediction_col,
        )
        actual.append(signature)
        if min(pnl.count(), research_pnl.count()) > 1:
            # Drop leading NaNs and burn the first PnL entry.
            research_pnl = research_pnl.dropna().iloc[1:]
            tail = research_pnl.size
            # We create new series because the portfolio times may be
            # disaligned from the research bar times.
            pnl1 = pd.Series(pnl.tail(tail).values)
            _LOG.debug("portfolio pnl=\n%s", pnl1)
            corr_samples = min(tail, pnl1.size)
            pnl2 = pd.Series(research_pnl.tail(corr_samples).values)
            _LOG.debug("research pnl=\n%s", pnl2)
            correlation = pnl1.corr(pnl2)
            actual.append("\n# pnl agreement with research pnl\n")
            actual.append(f"corr = {correlation:.3f}")
            actual.append(f"corr_samples = {corr_samples}")
        actual = "\n".join(map(str, actual))
        return actual

    # TODO(gp): @paul pass dictionaries instead of the values to mimic the
    #  interface of `ProcessForecasts`.
    def get_research_pnl_signature(
        self,
        result_bundle,
        *,
        price_col: str,
        volatility_col: str,
        prediction_col: str,
        bulk_frac_to_remove: float = 0.0,
        bulk_fill_method: str = "zero",
        target_gmv: float = 1e5,
        liquidate_at_end_of_day: bool = False,
    ) -> Tuple[str, pd.Series]:
        # TODO(gp): @all use actual.append(hprint.frame("system_config"))
        #  to separate the sections of the output.
        actual = ["\n# forecast_evaluator_from_prices signature=\n"]
        forecast_evaluator = dtfmod.ForecastEvaluatorFromPrices(
            price_col=price_col,
            volatility_col=volatility_col,
            prediction_col=prediction_col,
        )
        result_df = result_bundle.result_df
        _LOG.debug("result_df=\n%s", hpandas.df_to_str(result_df))
        #
        signature = forecast_evaluator.to_str(
            result_df,
            bulk_frac_to_remove=bulk_frac_to_remove,
            bulk_fill_method=bulk_fill_method,
            liquidate_at_end_of_day=liquidate_at_end_of_day,
            target_gmv=target_gmv,
        )
        _LOG.debug("signature=\n%s", signature)
        actual.append(signature)
        #
        _, _, _, _, stats = forecast_evaluator.compute_portfolio(
            result_df,
            bulk_frac_to_remove=bulk_frac_to_remove,
            bulk_fill_method=bulk_fill_method,
            target_gmv=target_gmv,
            liquidate_at_end_of_day=liquidate_at_end_of_day,
            reindex_like_input=True,
            burn_in_bars=0,
        )
        research_pnl = stats["pnl"]
        actual = "\n".join(map(str, actual))
        return actual, research_pnl

    @staticmethod
    def _append(
        list_: List[str], label: str, data: Union[pd.Series, pd.DataFrame]
    ) -> None:
        data_str = hpandas.df_to_str(data, index=True, num_rows=None, decimals=3)
        list_.append(f"{label}=\n{data_str}")
