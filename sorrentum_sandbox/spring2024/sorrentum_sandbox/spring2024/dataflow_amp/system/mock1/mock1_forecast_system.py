"""
Import as:

import dataflow_amp.system.mock1.mock1_forecast_system as dtfasmmfosy
"""

import logging
from typing import Coroutine

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.mock1 as dtfapmo
import dataflow_amp.system.mock1.mock1_builders as dtfasmmobu
import market_data as mdata
import oms

_LOG = logging.getLogger(__name__)


# #############################################################################
# Mock1_NonTime_ForecastSystem
# #############################################################################


class Mock1_NonTime_ForecastSystem(dtfsys.NonTime_ForecastSystem):
    """
    Create a System with:

    - a ReplayedMarketData
    - a non-timed Mock1 DAG

    This is used to run an historical simulation of a Mock1 system.
    """

    def __init__(self):
        super().__init__()
        # TODO(Grisha): consider exposing to the interface.
        self.train_test_mode = "ins"

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfapmo.Mock1_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        market_data = dtfasmmobu.get_Mock1_MarketData_example2(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        # TODO(Grisha): pass via `System.config` instead.
        timestamp_column_name = "end_datetime"
        dag = dtfasmmobu.get_Mock1_HistoricalDag_example1(
            self, timestamp_column_name
        )
        return dag

    def _get_dag_runner(self) -> dtfcore.DagRunner:
        dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        return dag_runner


# #############################################################################
# Mock1_Time_ForecastSystem
# #############################################################################


class Mock1_Time_ForecastSystem(dtfsys.Time_ForecastSystem):
    """
    Create a System with:

    - a ReplayedMarketData
    - a timed Mock1 DAG
    - a RealTimeDagRunner
    """

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfapmo.Mock1_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        market_data = dtfsys.get_ReplayedMarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasmmobu.get_Mock1_RealtimeDag_example2(self)
        return dag

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner


# #############################################################################
# Mock1_Time_ForecastSystem_with_DataFramePortfolio
# #############################################################################


class Mock1_Time_ForecastSystem_with_DataFramePortfolio(
    dtfsys.Time_ForecastSystem_with_DataFramePortfolio
):
    """
    Build a system with:

    - a ReplayedTimeMarketData
    - a timed Mock1 DAG
    - a DataFramePortfolio
    """

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfapmo.Mock1_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        market_data = dtfsys.get_ReplayedMarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasmmobu.get_Mock1_RealtimeDag_example3(self)
        return dag

    def _get_portfolio(self) -> oms.Portfolio:
        portfolio = dtfsys.get_DataFramePortfolio_from_System(self)
        return portfolio

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner


# #############################################################################
# Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
# #############################################################################


class Mock1_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor(
    dtfsys.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
):
    """
    A System with:

    - a `ReplayedMarketData`
    - a timed `Mock1` DAG
    - a `DatabasePortfolio` (which includes a `DatabaseBroker`)
    - an `OrderProcessor`
    """

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfapmo.Mock1_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        market_data = dtfsys.get_ReplayedMarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasmmobu.get_Mock1_RealtimeDag_example3(self)
        return dag

    def _get_portfolio(self) -> oms.Portfolio:
        portfolio = dtfsys.get_DatabasePortfolio_from_System(self)
        return portfolio

    def _get_order_processor(self) -> oms.OrderProcessor:
        order_processor = dtfsys.get_OrderProcessor_from_System(self)
        return order_processor

    def _get_order_processor_coroutine(self) -> Coroutine:
        order_processor = self.order_processor
        order_processor_coroutine: Coroutine = (
            dtfsys.get_OrderProcessorCoroutine_from_System(self, order_processor)
        )
        return order_processor_coroutine

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner
