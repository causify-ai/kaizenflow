#!/usr/bin/env python

import logging
import os

import core.config as cconfig
import dataflow.backtest as dtfbcktst
import dataflow_amp.system.Cx.Cx_forecast_system_example as dtfasccfsex
import helpers.hdbg as hdbg
import helpers.hs3 as hs3

if __name__ == "__main__":
    # Set model params.
    dag_builder_ctor_as_str = (
        "dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
    )
    fit_at_beginning = False
    train_test_mode = "ins"
    backtest_config = "ccxt_v7-all.5T.2022-09-01_2022-11-30"
    # Set source dir params.
    aws_profile = "ck"
    root_dir = hs3.get_s3_bucket_path(aws_profile)
    # Append stage postfix to s3 bucket name if needed.
    stage = "preprod"
    if stage:
        root_dir = ".".join([root_dir, stage])
    root_dir = os.path.join(root_dir, "v3")
    # Set destination dir params.
    dst_dir = None
    dst_dir_tag = "run0"
    clean_dst_dir = True
    no_confirm = True
    # Set config params.
    index = None
    start_from_index = None
    # Introduce a switch instead of commenting out, otherwise the Linter
    # removes the `cconfig` import.
    update_config_switch = False
    if update_config_switch:
        # Below there is just an example.
        config_update = cconfig.Config.from_dict(
            {
                "dag_builder_class": "C1b_DagBuilder",
                "dag_config": {
                    "resample": {
                        "transformer_kwargs": {
                            "rule": "1T",
                        },
                    },
                },
            },
        )
    else:
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
    # Create system.
    system = dtfasccfsex.get_Cx_NonTime_ForecastSystem_example(
        dag_builder_ctor_as_str,
        fit_at_beginning,
        train_test_mode=train_test_mode,
        backtest_config=backtest_config,
        root_dir=root_dir,
    )
    # Run.
    dtfbcktst.run_backtest(
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
