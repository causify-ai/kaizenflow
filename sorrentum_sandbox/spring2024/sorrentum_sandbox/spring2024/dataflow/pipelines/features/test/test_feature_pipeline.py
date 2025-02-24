import logging

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.pipelines.features.pipeline as dtfpifepip
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestFeaturePipeline(hunitest.TestCase):
    """
    Test the feature pipeline end-to-end.
    """

    def test1(self) -> None:
        dag_builder = dtfpifepip.FeaturePipeline()
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
                "source_node_name": "arma",
                "source_node_kwargs": {
                    "frequency": "T",
                    "start_date": "2010-01-04 09:30:00",
                    "end_date": "2010-01-04 16:05:00",
                    "ar_coeffs": [0],
                    "ma_coeffs": [0],
                    "scale": 0.1,
                    "burnin": 0,
                    "seed": 0,
                },
            }
        )
        config[
            "perform_col_arithmetic", "func_kwargs"
        ] = cconfig.Config.from_dict({"col_groups": []})
        config["zscore", "transformer_kwargs", "dyadic_tau"] = 5
        config["compress_tails", "transformer_kwargs", "scale"] = 6
        config["cross_feature_pairs", "func_kwargs"] = cconfig.Config.from_dict(
            {
                "feature_groups": [
                    (
                        "bid_size",
                        "ask_size",
                        [
                            "difference",
                            "normalized_difference",
                            "compressed_difference",
                        ],
                        "basize",
                    )
                ],
                "join_output_with_input": False,
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
