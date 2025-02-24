import logging

import pytest

import dataflow.backtest as dtfmrpmofl
import dataflow_amp.system.mock1.mock1_forecast_system_example as dtfasmmfsex

_LOG = logging.getLogger(__name__)

# TODO(gp): -> test_mock1_tiled_backtest.py


class Test_Mock1_NonTime_ForecastSystem_TiledBacktest(
    dtfmrpmofl.TiledBacktest_TestCase
):
    """
    Run end-to-end backtest for a Mock1 pipeline:

    - run model
    - run the analysis flow to make sure that it works
    """

    @pytest.mark.superslow
    def test1(self) -> None:
        """
        Run on a couple of asset ids for a single month.

        The output is a single tile with both asset_ids.
        """
        backtest_config = "mock1_v1-top2.5T.2000-01-01_2000-02-01"
        config_builder = (
            "dataflow_amp.system.mock1.mock1_tile_config_builders."
            + f'build_Mock1_tile_config_list("{backtest_config}")'
        )
        experiment_builder = (
            "dataflow.backtest.master_backtest.run_in_sample_tiled_backtest"
        )
        # We abort on error since we don't expect failures.
        run_model_extra_opts = ""
        #
        self._test(config_builder, experiment_builder, run_model_extra_opts)

    @pytest.mark.slow("~6 seconds.")
    def test_mock1_backtest(self) -> None:
        """
        Smoke test mock1 model backtest run.
        """
        # Set model params.
        backtest_config = "mock1_v1-top2.5T.2000-01-01_2000-02-01"
        # Create model.
        system = (
            dtfasmmfsex.get_Mock1_NonTime_ForecastSystem_for_simulation_example1(
                backtest_config=backtest_config
            )
        )
        # Run.
        self._run_backtest(system)
