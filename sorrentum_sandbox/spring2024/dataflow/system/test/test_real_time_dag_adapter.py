import logging
import os

import pandas as pd

import dataflow.core as dtfcobuexa
import dataflow.system.real_time_dag_adapter as dtfsrtdaad
import dataflow.system.sink_nodes as dtfsysinod
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import oms

_LOG = logging.getLogger(__name__)


class Test_adapt_dag_to_real_time1(hunitest.TestCase):
    # TODO(gp): Add a test for Mock1 and factor out the code below.

    def testMvnReturnsBuilder1(self) -> None:
        """
        Build a realtime DAG from `MvnReturnsBuilder()`.
        """
        txt = []
        # Build a DagBuilder.
        # TODO(Paul): Replace this with `MvnReturnsBuilder()`.
        dag_builder = dtfcobuexa.Returns_DagBuilder()
        txt.append(hprint.frame("dag_builder"))
        txt.append(hprint.indent(str(dag_builder)))
        # Build initial DAG.
        config = dag_builder.get_config_template()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("config=\n%s", config)
        dag = dag_builder.get_dag(config)
        # Print the initial DAG.
        file_name = os.path.join(self.get_scratch_space(), "initial_dag.png")
        dtfcobuexa.draw_to_file(dag, file_name)
        #
        txt.append(hprint.frame("initial dag"))
        txt.append(hprint.indent(str(dag)))
        # Build a MarketData.
        # TODO(Paul): Use a nontrivial event loop.
        event_loop = None
        portfolio = oms.get_DataFramePortfolio_example1(event_loop)
        market_data = portfolio.market_data
        market_data_history_lookback = pd.Timedelta("5T")
        # Get params for ProcessForecastsNode.
        prediction_col = "close"
        volatility_col = "close"
        spread_col = None
        order_config = {
            "order_type": "price@twap",
            "passivity_factor": None,
            "order_duration_in_mins": 5,
        }
        compute_target_positions_kwargs = {
            "bulk_frac_to_remove": 0.0,
            "target_gmv": 1e5,
        }
        optimizer_config = {
            "backend": "pomo",
            "asset_class": "equities",
            "apply_cc_limits": None,
            "params": {
                "style": "cross_sectional",
                "kwargs": compute_target_positions_kwargs,
            },
        }
        #
        root_log_dir = None
        process_forecasts_node_dict = (
            dtfsysinod.get_ProcessForecastsNode_dict_example1(
                portfolio,
                volatility_col,
                prediction_col,
                spread_col,
                order_config,
                optimizer_config,
                root_log_dir,
            )
        )
        ts_col_name = "end_datetime"
        # Adapt DAG to real-time.
        dag = dtfsrtdaad.adapt_dag_to_real_time(
            dag,
            market_data,
            market_data_history_lookback,
            process_forecasts_node_dict,
            ts_col_name,
        )
        # Print the final DAG.
        file_name = os.path.join(self.get_scratch_space(), "final_dag.png")
        dtfcobuexa.draw_to_file(dag, file_name)
        #
        txt.append(hprint.frame("final dag"))
        txt.append(str(dag))
        # Check.
        txt = "\n".join(txt)
        self.check_string(txt, purify_text=True)
