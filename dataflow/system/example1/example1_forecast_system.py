"""
Import as:

import dataflow.system.example1.example1_forecast_system as dtfseefosy
"""

import logging

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.model.experiment_config as dtfmoexcon
import dataflow.pipelines.example1.example1_pipeline as dtfpexexpi
import dataflow.system.example1.example1_builders as dtfsexexbu
import dataflow.system.real_time_dag_runner as dtfsrtdaru
import dataflow.system.system as dtfsyssyst
import dataflow.system.system_builder_utils as dtfssybuut
import dataflow.universe as dtfuniver
import helpers.hdbg as hdbg
import im_v2.common.data.client as icdc
import market_data as mdata
import oms

_LOG = logging.getLogger(__name__)


# #############################################################################
# Example1_ForecastSystem
# #############################################################################


class Example1_ForecastSystem(dtfsyssyst.ForecastSystem):
    """
    Create a System with:

    - a ReplayedMarketData
    - an non-timed Example1 DAG

    This is used to run an historical simulation of an Example1 system.
    """

    def get_dag_runner(self) -> dtfcore.DagRunner:
        dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        return dag_runner

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfpexexpi.Example1_DagBuilder()
        system_config = dtfssybuut.get_system_config_template_from_dag_builder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        market_data = dtfsexexbu.get_Example1_MarketData_example2(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsexexbu.get_Example1_dag_example1(self)
        return dag


# TODO(Grisha): "Factor out `build_ForecastSystem`" CmTask #2282.
def get_Example1_ForecastSystem_example1(
    backtest_config: str,
) -> dtfsyssyst.ForecastSystem:
    """
    Get Example1_ForecastSystem object for backtesting.
    """
    # Parse the backtest experiment.
    (
        universe_str,
        trading_period_str,
        time_interval_str,
    ) = dtfmoexcon.parse_experiment_config(backtest_config)
    #
    system = Example1_ForecastSystem()
    # Set the trading period.
    hdbg.dassert_in(trading_period_str, ("1T", "5T", "15T"))
    # TODO(gp): Use a setter.
    system.config[
        "dag_config_config", "resample", "transformer_kwargs", "rule"
    ] = trading_period_str
    # TODO(gp): We pass dag_runner through the config since somebody
    #  outside needs this function to run. In reality we should build the
    #  object and not pass a builder.
    system.config["dag_runner_object"] = system.get_dag_runner
    # TODO(gp):
    system.config["backtest_config", "universe_str"] = universe_str
    system.config["backtest_config", "trading_period_str"] = trading_period_str
    system.config["backtest_config", "time_interval_str"] = time_interval_str
    #
    system.config["backtest_config", "freq_as_pd_str"] = "M"
    system.config["backtest_config", "lookback_as_pd_str"] = "10D"
    # Use `ImClient` to get asset ids universe.
    im_client = icdc.get_DataFrameImClient_example1()
    full_symbols = dtfuniver.get_universe(universe_str)
    asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)
    system.config["market_data_config", "im_client"] = im_client
    system.config["market_data_config", "asset_ids"] = asset_ids
    # TODO(gp): Find a better place in the config, maybe "save_results"?
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    return system


# #############################################################################
# Example1_Time_ForecastSystem
# #############################################################################


class Example1_Time_ForecastSystem(dtfsyssyst.Time_ForecastSystem):
    """
    Create a System with:

    - a ReplayedMarketData
    - an Example1 DAG
    - a RealTimeDagRunner
    """

    def get_dag_runner(self) -> dtfsrtdaru.RealTimeDagRunner:
        dag_runner = dtfssybuut.get_realtime_DagRunner_from_system(self)
        return dag_runner

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfpexexpi.Example1_DagBuilder()
        system_config = dtfssybuut.get_system_config_template_from_dag_builder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        market_data = dtfssybuut.get_event_loop_MarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsexexbu.get_Example1_realtime_dag_example1(self)
        return dag


# #############################################################################
# Example1_Time_ForecastSystem_with_DataFramePortfolio
# #############################################################################


class Example1_Time_ForecastSystem_with_DataFramePortfolio(
    dtfsyssyst.Time_ForecastSystem_with_DataFramePortfolio
):
    """
    Build a system with:

    - a ReplayedTimeMarketData
    - a time Example1 DAG
    - a DataFramePortfolio
    """

    def get_dag_runner(self) -> dtfsrtdaru.RealTimeDagRunner:
        dag_runner = dtfssybuut.get_realtime_DagRunner_from_system(self)
        return dag_runner

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfpexexpi.Example1_DagBuilder()
        system_config = dtfssybuut.get_system_config_template_from_dag_builder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        market_data = dtfssybuut.get_event_loop_MarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsexexbu.get_Example1_dag_example3(self)
        return dag

    # TODO(gp): Extract this code in Example1_builders.py
    def _get_portfolio(self) -> oms.Portfolio:
        event_loop = self.config["event_loop_object"]
        market_data = self.market_data
        asset_ids = self.config["market_data_config", "asset_ids"]
        portfolio = oms.get_DataFramePortfolio_example1(
            event_loop,
            market_data=market_data,
            # TODO(gp): These should go in the config.
            mark_to_market_col="close",
            pricing_method="twap.5T",
            asset_ids=asset_ids,
        )
        # TODO(gp): These should go in the config?
        portfolio.broker._column_remap = {
            "bid": "bid",
            "ask": "ask",
            "midpoint": "midpoint",
            "price": "close",
        }
        return portfolio


# #############################################################################
# Example1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
# #############################################################################


class Example1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor(
    dtfsyssyst.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
):
    """
    A System with:

    - a `ReplayedMarketData`
    - an `Example1` DAG
    - a `DatabasePortfolio` (which includes a `DatabaseBroker`)
    - an `OrderProcessor`
    """

    def get_dag_runner(self) -> dtfsrtdaru.RealTimeDagRunner:
        dag_runner = dtfssybuut.get_realtime_DagRunner_from_system(self)
        return dag_runner

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfpexexpi.Example1_DagBuilder()
        system_config = dtfssybuut.get_system_config_template_from_dag_builder(
            dag_builder
        )
        return system_config

    def _get_market_data(
        self,
    ):
        market_data = dtfssybuut.get_event_loop_MarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsexexbu.get_Example1_dag_example3(self)
        return dag

    # TODO(gp): Extract this code in Example1_builders.py
    def _get_portfolio(
        self,
    ) -> oms.Portfolio:
        event_loop = self.config["event_loop_object"]
        db_connection = self.config["db_connection_object"]
        market_data = self.market_data
        table_name = oms.CURRENT_POSITIONS_TABLE_NAME
        asset_ids = self.config["market_data_config", "asset_ids"]
        portfolio = oms.get_DatabasePortfolio_example1(
            event_loop,
            db_connection,
            table_name,
            market_data=market_data,
            mark_to_market_col="close",
            pricing_method="twap.5T",
            asset_ids=asset_ids,
        )
        portfolio.broker._column_remap = {
            "bid": "bid",
            "ask": "ask",
            "midpoint": "midpoint",
            "price": "close",
        }
        return portfolio
