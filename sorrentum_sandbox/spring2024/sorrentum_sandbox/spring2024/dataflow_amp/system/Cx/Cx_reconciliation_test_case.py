"""
Import as:

import dataflow_amp.system.Cx.Cx_reconciliation_test_case as dtfasccrtca
"""
import logging
import os
from typing import Dict, Optional

import pandas as pd

import dataflow.core as dtfcore
import dataflow.model as dtfmod
import dataflow_amp.system.Cx.utils as dtfasycxut
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import im_v2.common.universe as ivcu
import reconciliation as reconcil

_LOG = logging.getLogger(__name__)


class Test_Cx_ProdReconciliation_TestCase(hunitest.TestCase):
    """
    Run the reconciliation flow using the pre-computed inputs and freeze the
    results.

    The inputs are:
        - market data (price data)
        - prod system output
    """

    def _run_reconciliation(
        self,
        dag_builder_ctor_as_str: str,
        start_timestamp_as_str: str,
        end_timestamp_as_str: str,
        *,
        tag: str = "",
        set_config_values: Optional[str] = None,
    ) -> None:
        """
        Run the reconciliation.

        :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
            e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
        :param start_timestamp_as_str: system start timestamp as str, e.g., "20220101_130500"
        :param end_timestamp_as_str: system end timestamp as str, e.g., "20220101_130500"
        :param tag: config tag, e.g., "config1"
        :param set_config_values: string representations of config values used
            to override simulation params and update research portoflio config when
            running the system reconciliation notebook. Config values are separated
            with ';' in order to be processed by invoke. E.g.,
            '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal")); \n
            ("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(0.1), "prediction_abs_threshold": float(0.35)})'
        """
        run_mode = "paper_trading"
        mode = "scheduled"
        stage = "preprod"
        # TODO(Grisha): save the output on S3?
        dst_root_dir = self.get_scratch_space()
        aws_profile = "ck"
        s3_prod_data_source_dir = self.get_s3_input_dir()
        # Copy market data file to the target dir.
        file_name = "test_data.csv.gz"
        market_data_file_path = os.path.join(s3_prod_data_source_dir, file_name)
        hs3.dassert_path_exists(market_data_file_path, aws_profile)
        cmd = f"aws s3 cp {market_data_file_path} {dst_root_dir} --profile {aws_profile}"
        hsystem.system(cmd, suppress_output=False)
        # TODO(Grisha): maybe enable running the notebook.
        # The overwriting is not prevented because scratch dir must be removed
        # after the run is finished.
        opts = [
            f"--dag-builder-ctor-as-str {dag_builder_ctor_as_str}",
            f"--run-mode {run_mode}",
            f"--start-timestamp-as-str {start_timestamp_as_str}",
            f"--end-timestamp-as-str {end_timestamp_as_str}",
            f"--dst-root-dir {dst_root_dir}",
            f"--prod-data-source-dir {s3_prod_data_source_dir}",
            f"--market-data-source-dir {dst_root_dir}",
            f"--mode {mode}",
            f"--stage {stage}",
            f"--tag '{tag}'",
            "--no-prevent-overwriting",
            "--allow-update",
            "--incremental",
            f"--aws-profile {aws_profile}",
        ]
        if set_config_values:
            opts.append(f"--set-config-values '{set_config_values}'")
        opts = " ".join(opts)
        docker_cmd = f"invoke reconcile_run_all {opts}"
        hsystem.system(docker_cmd, suppress_output=False)
        #
        dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
            dag_builder_ctor_as_str
        )
        target_dir = reconcil.get_target_dir(
            dst_root_dir,
            dag_builder_name,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            tag=tag,
        )
        system_log_dir_paths = reconcil.get_system_log_dir_paths(target_dir, mode)
        # Check configs. Since we don't have access to the System directly as it
        # is built deeply inside `reconcile_run_all`, we cannot use `check_SystemConfig()`.
        self._check_config(system_log_dir_paths)
        # Get portfolio stats.
        self._get_portfolio_stats(system_log_dir_paths)

    def _check_config(self, system_log_dir_paths: Dict[str, str]) -> None:
        """
        Freeze the output config.

        :param system_log_dir_paths: paths to system log dirs
        """
        sim_dir = system_log_dir_paths["sim"]
        config_file_name = "system_config.output.txt"
        tag = "after"
        # Check config.
        config_file_path = os.path.join(sim_dir, config_file_name)
        config = hio.from_file(config_file_path)
        txt = []
        tag = f"system_config.{tag}"
        txt.append(hprint.frame(tag))
        txt.append(config)
        txt = "\n".join(txt)
        txt = hunitest.purify_line_number(txt)
        self.check_string(txt, tag=tag, purify_text=True, fuzzy_match=True)

    def _get_portfolio_stats(self, system_log_dir_paths: Dict[str, str]) -> None:
        """
        Get portfolio stats and check the output.

        :param system_log_dir_paths: paths to system log dirs
        """
        data_type = "portfolio"
        portfolio_path_dict = reconcil.get_system_log_paths(
            system_log_dir_paths, data_type
        )
        #
        freq = "5T"
        _, portfolio_stats_dfs = reconcil.load_portfolio_dfs(
            portfolio_path_dict, freq
        )
        prod_pnl = portfolio_stats_dfs["prod"]["pnl"]
        prod_pnl.name = "prod_pnl"
        sim_pnl = portfolio_stats_dfs["sim"]["pnl"]
        sim_pnl.name = "sim_pnl"
        prod_sim_pnl = pd.concat([prod_pnl, sim_pnl], axis=1)
        # Compute correlations.
        prod_sim_pnl_corr = dtfmod.compute_correlations(
            portfolio_stats_dfs["prod"],
            portfolio_stats_dfs["sim"],
        )
        # Check output.
        num_chars = 40
        corr_header = hprint.frame(
            "Portfolio stats correlations", num_chars=num_chars
        )
        pnl_corr_str = hpandas.df_to_str(
            prod_sim_pnl_corr,
            num_rows=None,
        )
        prod_sim_pnl_header = hprint.frame(
            "Prod and simulation PnL", num_chars=num_chars
        )
        prod_sim_pnl_str = hpandas.df_to_str(
            prod_sim_pnl,
            num_rows=None,
        )
        signature = [
            corr_header,
            pnl_corr_str,
            prod_sim_pnl_header,
            prod_sim_pnl_str,
        ]
        signature = "\n\n".join(signature)
        self.check_string(signature)

    def _save_data_for_reconciliation_test(
        self,
        start_timestamp_as_str: str,
        end_timestamp_as_str: str,
    ) -> None:
        """
        Save market data for reconciliation tests.

        :param start_timestamp_as_str: system start timestamp as str,
            e.g., "20220101_130500"
        :param end_timestamp_as_str: system end timestamp as str, e.g.,
            "20220101_130500"
        """
        dst_root_dir = self.get_s3_input_dir()
        # TODO(Grisha): rename `test_data.csv.gz` -> `market_data.csv.gz`.
        market_data_file_path = os.path.join(dst_root_dir, "test_data.csv.gz")
        db_stage = "preprod"
        universe_version = ivcu.get_latest_universe_version()
        # TODO(Grisha): this is overfit for OHLCV models, expose to the interface.
        table_name = "ccxt_ohlcv_futures"
        # Save market data to the dir with the inputs.
        dtfasycxut.dump_market_data_from_db(
            market_data_file_path,
            start_timestamp_as_str,
            end_timestamp_as_str,
            db_stage,
            table_name,
            universe_version,
        )
