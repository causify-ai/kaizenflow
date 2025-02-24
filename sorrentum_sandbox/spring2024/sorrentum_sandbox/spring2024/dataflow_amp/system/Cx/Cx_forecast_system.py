"""
Import as:

import dataflow_amp.system.Cx.Cx_forecast_system as dtfasccfosy
"""

import logging
from typing import Any, Coroutine

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import market_data as mdata
import oms

_LOG = logging.getLogger(__name__)


# #############################################################################
# Cx_NonTime_ForecastSystem
# #############################################################################


class Cx_NonTime_ForecastSystem(dtfsys.ForecastSystem):
    """
    Create a System with:

    - a `HistoricalMarketData`
    - a non-timed Cx DAG
    - a `FitPredictDagRunner`

    This is used to run a historical simulation for a Cx system.
    """

    def __init__(
        self,
        # TODO(Grisha): consider passing an already built `DagBuilder` object.
        dag_builder_ctor_as_str: str,
        *dag_builder_args: Any,
        # TODO(gp): Why is this not before dag_builder_args?
        train_test_mode: str,
        **dag_builder_kwargs: Any,
    ) -> None:
        """
        Build the object.

        :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
            e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
        :param dag_builder_args: positional args for a `DagBuilder` ctor
        :param train_test_mode: how to perform the prediction
            - "ins": fit and predict using the same data
            - "ins_oos": fit using a train dataset and predict using a test
              dataset
            - "rolling": see `RollingFitPredictDagRunner` for description
        :param dag_builder_kwargs: keyword args for a `DagBuilder` ctor
        """
        self._dag_builder = dtfcore.get_DagBuilder_from_string(
            dag_builder_ctor_as_str, *dag_builder_args, **dag_builder_kwargs
        )
        # This needs to be initialized before the constructor of the parent
        # class.
        self.train_test_mode = train_test_mode
        super().__init__()

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            self._dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ImClientMarketData:
        market_data = dtfasccxbu.get_Cx_HistoricalMarketData_example1(self)
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasccxbu.get_Cx_HistoricalDag_example1(self)
        return dag

    # TODO(Grisha): @Dan Factor out in in abstract class so it can be reused
    # by all `ForecastSystem`s.
    def _get_dag_runner(self) -> dtfcore.DagRunner:
        if self.train_test_mode in ["ins", "ins_oos"]:
            dag_runner = dtfcore.FitPredictDagRunner(self.dag)
        elif self.train_test_mode == "rolling":
            dag_runner = dtfsys.get_RollingFitPredictDagRunner_from_System(self)
        else:
            raise ValueError(
                f"Unsupported train_test_mode={self.train_test_mode}"
            )
        return dag_runner


# #############################################################################
# Cx_Time_ForecastSystem
# #############################################################################


class Cx_Time_ForecastSystem(dtfsys.Time_ForecastSystem):
    """
    Create a System with:

    - ReplayedMarketData from a dataframe
    - timed Cx DAG
    - RealTimeDagRunner

    This is used for a bar-by-bar simulation.
    """

    def __init__(
        self,
        dag_builder_ctor_as_str: str,
        *dag_builder_args: Any,
        **dag_builder_kwargs: Any,
    ) -> None:
        """
        Ctor.

        :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
        """
        # This needs to be initialized before the other constructor.
        self._dag_builder = dtfcore.get_DagBuilder_from_string(
            dag_builder_ctor_as_str, *dag_builder_args, **dag_builder_kwargs
        )
        super().__init__()

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            self._dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        # TODO(Grisha): pass via system.config.
        column_remap = {
            "start_ts": "start_datetime",
            "end_ts": "end_datetime",
        }
        market_data = dtfsys.get_ReplayedMarketData_from_file_from_System(
            self, column_remap
        )
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasccxbu.get_Cx_RealTimeDag_example1(self)
        return dag

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner


# #############################################################################
# Cx_Time_ForecastSystem_with_DataFramePortfolio
# #############################################################################


class Cx_Time_ForecastSystem_with_DataFramePortfolio(
    dtfsys.Time_ForecastSystem_with_DataFramePortfolio
):
    """
    Build a System with:

    - RealTimeMarketData
    - timed Cx DAG
    - DataFramePortfolio

    This is used to simulate a System creating and executing orders.
    """

    def __init__(
        self,
        dag_builder_ctor_as_str: str,
        *dag_builder_args: Any,
        **dag_builder_kwargs: Any,
    ) -> None:
        """
        Build the object.

        :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
        """
        # This needs to be initialized before the other constructor.
        self._dag_builder = dtfcore.get_DagBuilder_from_string(
            dag_builder_ctor_as_str, *dag_builder_args, **dag_builder_kwargs
        )
        super().__init__()

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            self._dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        # TODO(Grisha): pass via system.config.
        column_remap = {
            "start_ts": "start_datetime",
            "end_ts": "end_datetime",
        }
        market_data = dtfsys.get_ReplayedMarketData_from_file_from_System(
            self, column_remap
        )
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasccxbu.get_Cx_RealTimeDag_example2(self)
        return dag

    def _get_portfolio(self) -> oms.Portfolio:
        portfolio = dtfsys.get_DataFramePortfolio_from_System(self)
        return portfolio

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner


# #############################################################################
# Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
# #############################################################################


class Cx_Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor(
    dtfsys.Time_ForecastSystem_with_DatabasePortfolio_and_OrderProcessor
):
    """
    Build a system with:

    - a RealTimeMarketData
    - a timed Cx DAG
    - a `DatabasePortfolio` (which includes a `DatabaseBroker`)
    - an `OrderProcessor`
    """

    def __init__(
        self,
        dag_builder_ctor_as_str: str,
        *dag_builder_args: Any,
        **dag_builder_kwargs: Any,
    ) -> None:
        """
        Build the object.

        :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_args: same as in `Cx_NonTime_ForecastSystem`
        :param dag_builder_kwargs: same as in `Cx_NonTime_ForecastSystem`
        """
        # This needs to be initialized before the other constructor.
        self._dag_builder = dtfcore.get_DagBuilder_from_string(
            dag_builder_ctor_as_str, *dag_builder_args, **dag_builder_kwargs
        )
        super().__init__()

    def _get_system_config_template(self) -> cconfig.Config:
        _ = self
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            self._dag_builder
        )
        return system_config

    def _get_market_data(self) -> mdata.ReplayedMarketData:
        # TODO(Grisha): pass via system.config.
        column_remap = {
            "start_ts": "start_datetime",
            "end_ts": "end_datetime",
        }
        market_data = dtfsys.get_ReplayedMarketData_from_file_from_System(
            self, column_remap
        )
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        dag = dtfasccxbu.get_Cx_RealTimeDag_example2(self)
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
