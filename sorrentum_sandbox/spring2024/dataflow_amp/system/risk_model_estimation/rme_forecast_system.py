"""
Import as:

import dataflow_amp.system.risk_model_estimation.rme_forecast_system as dtfasrmerfs
"""

import logging

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.risk_model_estimation as dtfaprme

_LOG = logging.getLogger(__name__)


# #############################################################################
# RME_NonTime_Df_ForecastSystem
# #############################################################################


class RME_NonTime_Df_ForecastSystem(dtfsys.NonTime_Df_ForecastSystem):
    """
    Create a System with:

    - an input data represented by a df
    - a non-timed DAG
    - a FitPredictDagRunner

    This is used to run a risk model estimation for a System.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
        # TODO(Grisha): consider exposing to the interface.
        self.train_test_mode = "ins"

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        dag_builder = dtfaprme.SimpleRiskModel_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_df(self) -> pd.DataFrame:
        return self._df

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsys.build_Dag_with_DfDataSource_from_System(self)
        return dag

    def _get_dag_runner(self) -> dtfcore.DagRunner:
        dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        return dag_runner
