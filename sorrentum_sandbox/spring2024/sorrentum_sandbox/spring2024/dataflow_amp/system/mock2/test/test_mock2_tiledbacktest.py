import pytest

import dataflow.backtest as dtfmrpmofl
import dataflow_amp.system.mock2.mock2_forecast_system_example as dtasmmfsex

class Test_Mock2_NonTime_ForecastSystem_TiledBacktest(
    dtfmrpmofl.TiledBacktest_TestCase
):
    """
    Run end-to-end backtest for a Mock2 pipeline:

    - run model
    - run the analysis flow to make sure that it works
    """

    @pytest.mark.superslow
    def test1(self) -> None:
        """
        Run on a couple of asset ids for a single month.

        The output is a single tile with both asset_ids.
        """
        backtest_config = "bloomberg_v1-top1.5T.2023-08-10_2023-08-31"
        config_builder = (
            "dataflow_amp.system.mock2.mock2_tile_config_builders."
            + f'build_Mock2_tile_config_list_for_unit_test("{backtest_config}")'
        )
        experiment_builder = (
            "dataflow.backtest.master_backtest.run_in_sample_tiled_backtest"
        )
        # We abort on error since we don't expect failures.
        run_model_extra_opts = ""
        #
        self._test(config_builder, experiment_builder, run_model_extra_opts)
    
    @pytest.mark.slow("~6 seconds.")
    def test_mock2_backtest(self) -> None:
        """
        Smoke test mock2 model backtest run.
        """
        # Set model params.
        backtest_config = "bloomberg_v1-top1.5T.2023-08-10_2023-08-31"
        # Create model.
        system = (
            dtasmmfsex.get_Mock2_NonTime_ForecastSystem_example2(
                backtest_config=backtest_config
            )
        )
        # Run.
        self._run_backtest(system)
