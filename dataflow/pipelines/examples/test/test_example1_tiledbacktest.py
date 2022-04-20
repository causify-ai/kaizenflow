import logging

import pytest

import dataflow.model.run_prod_model_flow as dtfmrpmofl

_LOG = logging.getLogger(__name__)


class Test_Example1_TiledBacktest(dtfmrpmofl.TiledBacktest_TestCase):
    """
    Run end-to-end experiment for an Example1 pipeline:

    - run model
    - run the analysis flow to make sure that it works
    """

    @pytest.mark.superslow
    def test1(self) -> None:
        """
        Run on a single name for a few months.
        """
        backtest_config = "example1_v1-top2.1T.Jan2000"
        config_builder = (
            "dataflow.pipelines.examples.example1_configs."
            + f'build_tile_configs("{backtest_config}")'
        )
        experiment_builder = (
            # "amp.dataflow.model.master_experiment.run_tiled_experiment"
            "dataflow.model.master_experiment.run_tiled_experiment"
        )
        # We abort on error since we don't expect failures.
        run_model_extra_opts = ""
        #
        self._test(config_builder, experiment_builder, run_model_extra_opts)
