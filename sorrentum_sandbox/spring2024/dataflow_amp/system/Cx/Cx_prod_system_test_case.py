"""
Import as:

import dataflow_amp.system.Cx.Cx_prod_system_test_case as dtfasccpstc
"""

import datetime
import os

import dataflow.core as dtfcore
import helpers.hgit as hgit
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest


class Test_Cx_ProdSystem_TestCase(hunitest.TestCase):
    """
    Run prod system test for a Cx pipeline:

    - run prod model
    - run flow for multiple bars to make sure that it works
    """

    def run_test_helper(self, dag_builder_ctor_as_str: str) -> None:
        amp_path = hgit.get_amp_abs_path()
        script_name = os.path.join(
            amp_path,
            "dataflow_amp",
            "system",
            "Cx",
            "scripts",
            "run_Cx_prod_system.py",
        )
        run_mode = "paper_trading"
        dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
            dag_builder_ctor_as_str
        )
        trade_date = datetime.date.today().strftime("%Y%m%d")
        dst_dir = self.get_input_dir(use_only_test_class=True)
        exchange = "binance"
        stage = "preprod"
        account_type = "trading"
        secret_id = 3
        run_duration = 300
        log_file_name = "system_log.txt"
        opts = [
            f"--dag_builder_ctor_as_str {dag_builder_ctor_as_str}",
            f"--run_mode {run_mode}",
            f"--strategy {dag_builder_name}",
            f"--trade_date {trade_date}",
            f"--dst_dir {dst_dir}",
            f"--exchange {exchange}",
            f"--stage {stage}",
            f"--account_type {account_type}",
            f"--secret_id {secret_id}",
            f"--run_duration {run_duration}",
            f"--log_file_name {log_file_name}",
        ]
        opts = " ".join(opts)
        opts += " -v DEBUG 2>&1"
        cmd = f"{script_name} {opts}"
        hsystem.system(cmd, suppress_output=False)
