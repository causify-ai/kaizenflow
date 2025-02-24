"""
Import as:

import dataflow_amp.system.mock3.mock3_forecast_system as dtfasmmfosy
"""

import logging

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.mock3.mock3_pipeline as dtfapmmopi
import dataflow_amp.system.mock1.mock1_builders as dtfasmmobu
import market_data as mdata

_LOG = logging.getLogger(__name__)


# #############################################################################
# Mock3_NonTime_ForecastSystem
# #############################################################################


class Mock3_NonTime_ForecastSystem(dtfsys.NonTime_ForecastSystem):
    """
    Create a System with:

    - a StitchedMarketData
    - a non-timed Mock3 DAG

    This is used to run batch simulations.
    """

    def __init__(self):
        super().__init__()
        # TODO(Grisha): consider exposing to the interface.
        self.train_test_mode = "ins"

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfapmmopi.Mock3_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        market_data = dtfsys.get_StitchedMarketData_from_System(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        # The column name does not affect anything, as the work is delegated to `ImClient`
        # that filters by index.
        timestamp_column_name = "end_datetime"
        # TODO(Grisha): use `build_HistoricalDag_from_System()` instead.
        dag = dtfasmmobu.get_Mock1_HistoricalDag_example1(
            self, timestamp_column_name
        )
        return dag

    def _get_dag_runner(self) -> dtfcore.DagRunner:
        dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        return dag_runner
