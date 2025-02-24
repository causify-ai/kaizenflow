#!/usr/bin/env python

import logging

import dataflow.backtest as dtfbcktst
import dataflow_amp.system.mock3.mock3_forecast_system_example as dtfasmmfsex
import helpers.hdbg as hdbg

if __name__ == "__main__":
    # Set model params.
    backtest_config = "ccxt_v7_4-all.5T.2023-09-11_2023-09-12"
    # Set dir params.
    dst_dir = None
    dst_dir_tag = "run0"
    clean_dst_dir = True
    no_confirm = True
    # Set config params.
    index = None
    start_from_index = None
    config_update = None
    # config_update = cconfig.Config.from_dict(
    #     {
    #         "dag_builder_class": "C1b_DagBuilder",
    #         "dag_config": {
    #             "resample": {
    #                 "transformer_kwargs": {
    #                     "rule": "1T",
    #                 },
    #             },
    #         },
    #     },
    # )
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
    system = dtfasmmfsex.get_Mock3_NonTime_ForecastSystem_example1(
        backtest_config
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
