import logging
from typing import List

import core.config as cconfig
import dataflow.backtest.dataflow_backtest_utils as dtfbdtfbaut
import dataflow.core as dtfcore
import dataflow_amp.pipelines.mock1 as dtfapmo
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# This mimics the code in example1_configs.py
# TODO(gp): Consider calling that code directly if it doesn't violate the
#  dependencies.

# TODO(gp): @all Port to new System style (see E8_config.py).


def _build_base_config() -> cconfig.Config:
    wrapper = cconfig.Config()
    #
    dag_builder = dtfapmo.Mock1_DagBuilder()
    dag_config = dag_builder.get_config_template()
    wrapper["dag_config"] = dag_config
    wrapper["dag_builder_object"] = dag_builder
    # wrapper["tags"] = []
    return wrapper


def _get_universe_tiny() -> List[int]:
    """
    Return a toy universe of liquid equities.
    """
    asset_ids = [
        13684,
        10971,
    ]
    return asset_ids


def get_dag_runner(config: cconfig.Config) -> dtfcore.DAG:
    """
    Build a DAG runner from a config.
    """
    # Build the DAG.
    dag_builder = config["dag_builder_object"]
    dag = dag_builder.get_dag(config["dag_config"])
    # Build the DagRunner.
    dag_runner = dtfcore.FitPredictDagRunner(dag)
    return dag_runner


def build_tile_config_list(
    backtest_config: str,
) -> cconfig.ConfigList:
    (
        _,
        _,
        time_interval_str,
    ) = cconfig.parse_backtest_config(backtest_config)
    #
    config = _build_base_config()
    # Name of the asset_ids to save.
    config["market_data_config", "asset_id_name"] = "asset_id"
    config_list = cconfig.ConfigList([config])
    # Apply the cross-product by the universe tiles.
    asset_ids = _get_universe_tiny()
    func = lambda cfg: cconfig.build_config_list_with_tiled_universe(
        cfg, asset_ids
    )
    config_list = cconfig.apply_build_config_list(func, config_list)
    _LOG.info(
        "After applying universe tiles: num_config_list=%s", len(config_list)
    )
    # Apply the cross-product by the time tiles.
    start_timestamp, end_timestamp = cconfig.get_period(time_interval_str)
    freq_as_pd_str = "M"
    lookback_as_pd_str = "10D"
    func = lambda cfg: cconfig.build_config_list_varying_tiled_periods(
        cfg, start_timestamp, end_timestamp, freq_as_pd_str, lookback_as_pd_str
    )
    config_list = cconfig.apply_build_config_list(func, config_list)
    _LOG.info("After applying time tiles: num_config_list=%s", len(config_list))
    return config_list


# TODO(gp): -> ..._get_config_list_
class Test_get_configs_from_command_line_Amp1(hunitest.TestCase):
    """
    Test building (but not running) the configs for backtest.
    """

    def test1(self) -> None:
        # Prepare inputs.
        class Args:
            experiment_list_config = "universe_v2_0-top2.5T.2020-01-01_2020-03-01"
            config_builder = (
                "dataflow.backtest.test.test_dataflow_backtest_utils.build_tile_config_list"
                + f'("{experiment_list_config}")'
            )
            dst_dir = "./dst_dir"
            experiment_builder = (
                "dataflow.backtest.master_backtest.run_in_sample_tiled_backtest"
            )
            index = 0
            start_from_index = 0
            no_incremental = True

        args = Args()
        # Run.
        config_list = dtfbdtfbaut.get_config_list_from_command_line(args)
        # Check.
        txt = str(config_list)
        self.check_string(txt, purify_text=True)
