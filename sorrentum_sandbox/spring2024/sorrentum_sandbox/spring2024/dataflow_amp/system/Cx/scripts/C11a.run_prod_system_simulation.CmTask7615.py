#!/usr/bin/env python
"""
The script runs a simulation equivalent to the production run.
"""
import logging
import os

import pandas as pd

import dataflow.system as dtfsys
import dataflow_amp.system.common.system_simulation_utils as dtfascssiut
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import dataflow_amp.system.Cx.Cx_prod_system as dtfasccprsy
import helpers.hdbg as hdbg
import reconciliation as reconcil

if __name__ == "__main__":
    # Set logger.
    hdbg.init_logger(
        verbosity=logging.INFO,
        use_exec_path=True,
        report_memory_usage=True,
    )
    # Build the prod system.
    dag_builder_ctor_as_str = (
        "dataflow_lemonade.pipelines.C11.C11a_pipeline.C11a_DagBuilder"
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
    system.config["market_data_config", "days"] = pd.Timedelta("6T")
    system.config["market_data_config", "universe_version"] = "v8.1"
    system.config[
        "market_data_config", "im_client_config", "table_name"
    ] = "ccxt_ohlcv_futures"
    # Simulation saves dag outputs. To disable, add
    # `("dag_property_config","debug_mode_config","save_node_io"),(str(""))` to
    # overrides.
    set_config_values = '("dag_property_config","debug_mode_config","profile_execution"),(bool(False));("dag_property_config","debug_mode_config","save_node_df_out_stats"),(bool(False));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","backend"),(str("batch_optimizer"));("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params"),({"dollar_neutrality_penalty": float(0.0), "constant_correlation": float(0.5), "constant_correlation_penalty": float(1.0), "relative_holding_penalty": float(0.0), "relative_holding_max_frac_of_gmv": float(0.1), "target_gmv": float(1000.0), "target_gmv_upper_bound_penalty": float(0.0), "target_gmv_hard_upper_bound_multiple": float(1.05), "transaction_cost_penalty": float(0.5), "solver": str("ECOS")});("dag_config", "resample", "transformer_kwargs", "rule"),(str("5T"));("trading_period"),(str("5T"));("market_data_config","universe_version"),(str("v8.1"));("dag_property_config","force_free_nodes"),(bool(False));("dag_property_config","debug_mode_config","profile_execution"),(bool(True));("process_forecasts_node_dict","process_forecasts_dict","order_config","order_duration_in_mins"),(int(5));("process_forecasts_node_dict","process_forecasts_dict","order_config","order_type"),(str("price@start"));("portfolio_config", "pricing_method"),(str("last"))'
    # Define params.
    start_timestamp_as_str = "20240314_000000"
    end_timestamp_as_str = "20240321_235900"
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
