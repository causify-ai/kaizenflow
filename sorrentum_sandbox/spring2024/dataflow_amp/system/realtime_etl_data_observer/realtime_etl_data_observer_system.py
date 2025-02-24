"""
Import as:

import dataflow_amp.system.realtime_etl_data_observer.realtime_etl_data_observer_system as dtfasredoredos
"""


import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.realtime_etl_data_observer.realtime_etl_data_observer_pipeline as dtfapredoredop
import market_data as mdata


class RealTime_etl_DataObserver_System(dtfsys.Time_ForecastSystem):
    def _get_system_config_template(
        self,
    ) -> cconfig.Config:
        _ = self
        dag_builder = dtfapredoredop.Realtime_etl_DataObserver_DagBuilder()
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.MarketData:
        market_data = dtfsys.get_ReplayedMarketData_from_df(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfsys.add_real_time_data_source(self)
        return dag

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner
