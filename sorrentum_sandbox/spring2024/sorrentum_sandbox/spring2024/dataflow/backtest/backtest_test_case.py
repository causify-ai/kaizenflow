"""
Code to run a backtest for a Dag and checks its result.

Import as:

import dataflow.backtest.backtest_test_case as dtfbbateca
"""

import abc
import logging
import os
from typing import Any

import core.config as cconfig
import dataflow.backtest.backtest_api as dtfbabaapi
import dataflow.model as dtfmod
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# Backtest_TestCase
# #############################################################################


class Backtest_TestCase(abc.ABC, hunitest.TestCase):
    """
    Run a backtest for a Dag and checks its result.
    """

    @staticmethod
    def get_config_list_signature(config_builder: str) -> str:
        """
        Compute a test signature from a `config_builder`.
        """
        # Create the configs.
        config_list = cconfig.get_config_list_from_builder(config_builder)
        # Create a signature.
        return str(config_list)

    @staticmethod
    def get_dir_signature(dir_name: str) -> str:
        include_file_content = False
        remove_dir_name = True
        txt: str = hunitest.get_dir_signature(
            dir_name, include_file_content, remove_dir_name=remove_dir_name
        )
        return txt

    # TODO(gp): -> run_dag_config
    @staticmethod
    def _run_model(
        config_builder: str,
        experiment_builder: str,
        extra_opts: str,
        dst_dir: str,
    ) -> None:
        """
        Invoke `run_config_list.py` on a config.

        We cannot pass function pointers to the builders or the result
        of the building to an executable
        `amp/core/dataflow/backtest/run_config_list.py`, so we only can
        accept strings representing static functions in the code.
        """
        # Execute a command line like:
        # ```
        # > /app/amp/core/dataflow/backtest/run_config_list.py \
        #       --experiment_builder \
        #           amp.dataflow.backtest.master_backtest.run_ins_oos_backtest \
        #       --config_builder \
        #           'dataflow....build_model_config_list("kibot_v1-top1.5T")' \
        #       --dst_dir .../run_model/oos_experiment.RH1E.kibot_v1-top1.5T \
        #       --clean_dst_dir \
        #       --no_confirm \
        #       --num_threads serial
        # ```
        if os.path.exists(dst_dir):
            # TODO(gp): Maybe assert.
            _LOG.warning("Dir with experiment already exists: skipping...")
            return
        #
        opts = []
        opts.append("--clean_dst_dir --no_confirm")
        opts.append("--num_threads serial")
        opts.append(extra_opts)
        opts = " ".join(opts)
        #
        amp_dir = hgit.get_amp_abs_path()
        exec_filename = os.path.join(
            amp_dir, "dataflow/backtest/run_config_list.py"
        )
        hdbg.dassert_path_exists(exec_filename)
        #
        cmd = []
        cmd.append(exec_filename)
        # Experiment builder.
        # E.g., "amp.dataflow.backtest.master_backtest.run_ins_oos_backtest"
        cmd.append(f"--experiment_builder {experiment_builder}")
        # Config builder.
        # E.g.,
        # builder = f'build_model_config_list("{backtest_config}", 1)'
        # config_builder = f'dataflow_lemonade.RH1E.RH1E_config_list.{builder}'
        cmd.append(f"--config_builder '{config_builder}'")
        #
        cmd.append(f"--dst_dir {dst_dir}")
        cmd.append("--aws_profile am")
        if _LOG.getEffectiveLevel() >= logging.DEBUG:
            cmd.append("-v DEBUG")
        cmd.append(opts)
        # Assemble the command line and run.
        cmd = " ".join(cmd)
        _LOG.info("cmd=%s", cmd)
        hsystem.system(cmd)

    @abc.abstractmethod
    def _test(self, *args: Any, **kwargs: Any) -> None:
        """
        Run the entire flow.
        """


# #############################################################################
# TiledBacktest_TestCase
# #############################################################################


class TiledBacktest_TestCase(Backtest_TestCase):
    """
    Run an end-to-end backtest for a model by:

    - Checking the configs against frozen representation
    - Running model using tiled backtest
    - Checking the dir signature against frozen representation
    - Checking that the output is a valid tiled results
    """

    def compute_tile_output_signature(self, file_name: str) -> str:
        """
        Create a test signature from a backtesting (Parquet) output.

        E.g.,
        ```
        # compute_metadata_stats_by_asset_id
                    n_years  n_unique_months  n_files
        asset_id
        1467591036        1                1        1
        3303714233        1                1        1
        # compute_universe_size_by_time
                    n_asset_ids
        year month
        2000 1                2
        ```

        :param file_name: name of a file with Parquet metadata
        :return: config signature
        """
        parquet_tile_analyzer = dtfmod.ParquetTileAnalyzer()
        parquet_tile_metadata = (
            parquet_tile_analyzer.collate_parquet_tile_metadata(file_name)
        )
        signature = []
        # Compute metadata stats by asset id.
        df = parquet_tile_analyzer.compute_metadata_stats_by_asset_id(
            parquet_tile_metadata
        )
        df_as_str = hpandas.df_to_str(df.drop("size", axis="columns"))
        signature.append("# compute_metadata_stats_by_asset_id")
        signature.append(df_as_str)
        # Compute metadata stats by time.
        df = parquet_tile_analyzer.compute_universe_size_by_time(
            parquet_tile_metadata
        )
        signature.append("# compute_universe_size_by_time")
        df_as_str = hpandas.df_to_str(df.drop("size", axis="columns"))
        signature.append(df_as_str)
        #
        signature = "\n".join(signature)
        return signature

    def _test(
        self,
        config_builder: str,
        experiment_builder: str,
        run_model_extra_opts: str,
    ) -> None:
        """
        Run the entire backtest flow.

        See the explanation of why we need string pointers in
        `_run_model()`.

        :param config_builder: string pointer to the function used to
            build configs
        :param experiment_builder: string pointer to the function used
            to build an experiment
        :param run_model_extra_opts: extra options passed to a model run
            command
        """
        scratch_dir = self.get_scratch_space()
        # 1) Check the configs against frozen representation.
        configs_signature = self.get_config_list_signature(config_builder)
        tag = "configs_signature"
        self.check_string(
            configs_signature, fuzzy_match=True, purify_text=True, tag=tag
        )
        # 2) Run the model using tiled backtest.
        run_model_dir = os.path.join(scratch_dir, "run_model")
        if hunitest.get_incremental_tests() and os.path.exists(run_model_dir):
            _LOG.warning(
                "Skipping running _run_model since '%s' already exists",
                run_model_dir,
            )
        else:
            self._run_model(
                config_builder,
                experiment_builder,
                run_model_extra_opts,
                run_model_dir,
            )
        # 3) Check the dir signature against frozen representation.
        tag = "output_signature"
        output_signature = self.get_dir_signature(run_model_dir)
        # Remove lines like 'log.20220304-200306.txt'.
        output_signature = hprint.filter_text(r"log\..*\.txt", output_signature)
        self.check_string(
            output_signature, fuzzy_match=True, purify_text=True, tag=tag
        )
        # 4) Check that the output is a valid tiled results.
        tile_output_dir = os.path.join(run_model_dir, "tiled_results")
        tile_output_signature = self.compute_tile_output_signature(
            tile_output_dir
        )
        tag = "tile_output_signature"
        self.check_string(
            tile_output_signature, fuzzy_match=True, purify_text=True, tag=tag
        )

    def _run_backtest(self, system: dtfsys.System) -> None:
        """
        Run backtest for a given system.

        :param system: the system to run backtest on
        """
        # Set dir params.
        dst_dir = self.get_scratch_space()
        dst_dir_tag = "run0"
        clean_dst_dir = True
        no_confirm = True
        # Set config params.
        index = None
        start_from_index = None
        config_update = None
        # Set execution params.
        abort_on_error = True
        num_threads = "serial"
        num_attempts = 1
        dry_run = False
        backend = "asyncio_threading"
        # Set logger.
        log_level = logging.DEBUG
        hdbg.init_logger(
            verbosity=log_level,
            use_exec_path=True,
            # report_memory_usage=True,
        )
        # Run backtest.
        dtfbabaapi.run_backtest(
            # Model params.
            system,
            config_update,
            # Dir params.
            dst_dir,
            dst_dir_tag,
            clean_dst_dir,
            no_confirm,
            # Config params.
            index,
            start_from_index,
            # Execution params.
            abort_on_error,
            num_threads,
            num_attempts,
            dry_run,
            backend,
        )
