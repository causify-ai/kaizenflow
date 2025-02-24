#!/usr/bin/env python
"""
The script runs a simulation equivalent to the production run.
"""
import logging
import os

import dataflow.system as dtfsys
import dataflow_amp.system.common.system_simulation_utils as dtfascssiut
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import dataflow_amp.system.Cx.Cx_prod_system as dtfasccprsy
import helpers.hdbg as hdbg
import reconciliation as reconcil

if __name__ == "__main__":
    # Set logger.
    hdbg.init_logger(
        verbosity=logging.DEBUG,
        use_exec_path=True,
        report_memory_usage=True,
    )
    # Build the prod system.
    dag_builder_ctor_as_str = (
        "dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder"
    )
    system = dtfasccprsy.Cx_ProdSystem_v1_20220727(
        dag_builder_ctor_as_str, run_mode="simulation"
    )
    # Fill the system.
    system = dtfsys.apply_Portfolio_config(system)
    order_config = dtfasccxbu.get_Cx_order_config_instance1()
    optimizer_config = dtfasccxbu.get_Cx_optimizer_config_instance1()
    log_dir = reconcil.get_process_forecasts_dir(system.config["system_log_dir"])
    system = dtfasccxbu.apply_ProcessForecastsNode_config(
        system, order_config, optimizer_config, log_dir
    )
    system.config["trading_period"] = "5T"
    system.config["market_data_config", "days"] = None
    system.config["market_data_config", "universe_version"] = "v7.4"
    system.config[
        "market_data_config", "im_client_config", "table_name"
    ] = "ccxt_ohlcv_futures"
    set_config_values = '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(1.0)})'
    # Define params.
    start_timestamp_as_str = "20230906_101000"
    end_timestamp_as_str = "20230906_103000"
    market_data_dst_dir = "./tmp"
    market_data_file_path = os.path.join(
        market_data_dst_dir, "market_data.csv.gz"
    )
    dst_dir = "/app/system_log_dir"
    db_stage = "preprod"
    config_tag = "prod_system"
    # Run simulation.
    _ = dtfascssiut.run_simulation(
        system,
        start_timestamp_as_str,
        end_timestamp_as_str,
        market_data_file_path,
        dst_dir,
        set_config_values=set_config_values,
        db_stage=db_stage,
        config_tag=config_tag,
    )
