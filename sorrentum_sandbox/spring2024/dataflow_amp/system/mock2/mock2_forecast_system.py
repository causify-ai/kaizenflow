"""
Import as:

import dataflow_amp.system.mock2.mock2_forecast_system as dtfasmmfosy
"""

import os

import pandas as pd

import core.config as cconfig
import core.finance.market_data_example as cfmadaex
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.mock2.mock2_pipeline as dtapmmopi
import dataflow_amp.system.mock1.mock1_builders as dtfasmmobu
import market_data as mdata
import oms

# #############################################################################
# Mock2_NonTime_ForecastSystem
# #############################################################################


class Mock2_NonTime_ForecastSystem(dtfsys.NonTime_ForecastSystem):
    """
    Create a System with:

    - a HistoricalMarketData
    - a non-timed DAG

    This is used to run a backtest for a Mock2 pipeline.
    """

    def __init__(self):
        super().__init__()
        # TODO(Grisha): consider exposing to the interface.
        self.train_test_mode = "ins"

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtapmmopi.Mock2_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        # TODO(Grisha): we should not use Mock1 builders here, better to
        # factor out common code, put it under a common dir and re-use here.
        market_data = dtfasmmobu.get_Mock1_MarketData_example2(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        # TODO(Grisha): pass via `System.config` instead.
        timestamp_column_name = "end_ts"
        # TODO(Grisha): we should not use Mock1 builders here, better to factor
        # out common code, put it under a common dir and re-use here.
        dag = dtfasmmobu.get_Mock1_HistoricalDag_example1(
            self, timestamp_column_name
        )
        return dag

    def _get_dag_runner(self) -> dtfcore.DagRunner:
        dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        return dag_runner


# #############################################################################
# Mock2_Time_ForecastSystem_with_DataFramePortfolio
# #############################################################################


class Mock2_Time_ForecastSystem_with_DataFramePortfolio(
    dtfsys.Time_ForecastSystem_with_DataFramePortfolio
):
    """
    Build a System with:

    - `ReplayedMarketData`
    - a timed DAG
    - `DataFramePortfolio`
    """

    def _get_system_config_template(self) -> cconfig.Config:
        dag_builder = dtapmmopi.Mock2_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        # Generate random OHLCV bars.
        start_datetime = pd.Timestamp(
            "2023-08-01 10:00:00", tz="America/New_York"
        )
        end_datetime = pd.Timestamp("2023-08-31 10:00:00", tz="America/New_York")
        n_assets = self.config["market_data_config", "number_of_assets"]
        asset_ids = [i for i in range(n_assets)]
        bar_duration_in_seconds = self.config["bar_duration_in_seconds"]
        bar_duration = f"{int(bar_duration_in_seconds/60)}T"
        df = cfmadaex.generate_random_ohlcv_bars(
            start_datetime, end_datetime, asset_ids, bar_duration=bar_duration
        )
        # Specify parameters for `ReplayedMarketData_from_df`.
        self.config[
            "market_data_config", "replayed_delay_in_mins_or_timestamp"
        ] = pd.Timestamp("2023-08-15 10:30:00", tz="America/New_York")
        self.config["market_data_config", "data"] = df
        # We wait 10 seconds in any case, because we add 10 seconds to
        # `timestamp_db` column in `generate_random_ohlcv_bars()`.
        self.config["market_data_config", "delay_in_secs"] = 0
        # This is needed to construct the Portfolio.
        self.config["market_data_config", "asset_ids"] = asset_ids
        # Build `MarketData`.
        market_data = dtfsys.get_ReplayedMarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        # Add `RealTimeDataSource`.
        bar_duration_in_minutes = int(self.config["bar_duration_in_seconds"] / 60)
        # TODO(Grisha): we should remove the resampling piece for this pipeline
        # or create another Mock3 pipeline.
        self.config[
            "dag_config", "resample", "transformer_kwargs", "rule"
        ] = f"{bar_duration_in_minutes}T"
        dag = dtfsys.add_real_time_data_source(self)
        # Configure a `ProcessForecastNode`.
        log_dir = os.path.join(self.config["system_log_dir"], "process_forecasts")
        # Here we configure only `compute_target_positions_kwargs` from the outside.
        compute_target_positions_kwargs = self.config[
            "process_forecasts_node_dict",
            "process_forecasts_dict",
            "optimizer_config",
            "params",
            "kwargs",
        ]
        process_forecasts_dict = {
            # Params for `process_forecasts()`.
            "order_config": {
                "order_type": "price@twap",
                "passivity_factor": None,
                "order_duration_in_mins": bar_duration_in_minutes,
            },
            "optimizer_config": {
                "backend": "pomo",
                "params": {
                    "style": "cross_sectional",
                    "kwargs": compute_target_positions_kwargs,
                },
            },
            "execution_mode": "real_time",
            "log_dir": log_dir,
        }
        # Params for `ProcessForecastsNode`.
        dag_builder = self.config["dag_builder_object"]
        volatility_col = dag_builder.get_column_name("volatility")
        prediction_col = dag_builder.get_column_name("prediction")
        process_forecasts_node_dict = {
            "prediction_col": prediction_col,
            "volatility_col": volatility_col,
            "spread_col": None,
            "portfolio": self.portfolio,
            # This configures `process_forecasts()`.
            "process_forecasts_dict": process_forecasts_dict,
        }
        process_forecasts_node_config = cconfig.Config.from_dict(
            process_forecasts_node_dict
        )
        self.config["process_forecasts_node_dict"] = process_forecasts_node_config
        self = dtfsys.apply_ProcessForecastsNode_config_for_equities(self)
        # Append the `ProcessForecastNode` to the `Dag`.
        dag = dtfsys.add_ProcessForecastsNode(self, dag)
        return dag

    def _get_portfolio(self) -> oms.Portfolio:
        # Portfolio config.
        bar_duration_in_seconds = self.config["bar_duration_in_seconds"]
        self.config["portfolio_config", "mark_to_market_col"] = "close"
        self.config[
            "portfolio_config", "pricing_method"
        ] = f"twap.{int(bar_duration_in_seconds/60)}T"
        column_remap = {
            "bid": "bid",
            "ask": "ask",
            "midpoint": "midpoint",
            "price": "close",
        }
        self.config[
            "portfolio_config", "column_remap"
        ] = cconfig.Config.from_dict(column_remap)
        # Build `Portfolio`.
        portfolio = dtfsys.get_DataFramePortfolio_from_System(self)
        return portfolio

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner
