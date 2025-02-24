import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.pipelines.execution.execution_pipeline as dtfpexexpi
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def get_test_data() -> pd.DataFrame:
    start_timestamp = pd.Timestamp("2022-01-10 09:30", tz="America/New_York")
    end_timestamp = pd.Timestamp("2022-01-10 09:45", tz="America/New_York")
    asset_ids = [101, 201]
    data = cofinanc.generate_random_top_of_book_bars(
        start_timestamp,
        end_timestamp,
        asset_ids,
        bar_duration="1s",
    )
    data = data.set_index("end_datetime")
    data = data.pivot(columns="asset_id")[["bid", "ask"]]
    data = data.rename(columns={"bid": "bid_price", "ask": "ask_price"})
    return data


class TestExecutionPipeline(hunitest.TestCase):
    """
    Test the execution pipeline end-to-end.
    """

    def test1(self) -> None:
        dag_builder = dtfpexexpi.ExecutionPipeline()
        #
        config = dag_builder.get_config_template()
        # Set up `overwrite` mode to allow reassignment of values.
        # Note: by default the `update_mode` does not allow overwrites,
        # but they are required by the FeaturePipeline.
        config.update_mode = "overwrite"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("config from dag_builder=%s", config)
        # Initialize config.
        config["load_data"] = cconfig.Config.from_dict(
            {
                "source_node_name": "FunctionDataSource",
                "source_node_kwargs": {
                    "func": get_test_data,
                },
            }
        )
        #
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("config after patching=%s", config)
        dag = dag_builder.get_dag(config)
        # Initialize DAG runner.
        dag_runner = dtfcore.FitPredictDagRunner(dag)
        result_bundle = dag_runner.fit()
        df_out = result_bundle.result_df
        df_str = hpandas.df_to_str(
            df_out.round(3).dropna(), num_rows=None, precision=3
        )
        self.check_string(df_str)
