#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "get_market_data_df" \
  --new "get_MarketData_df" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "get_im_client_market_data_df1" \
  --new "get_MarketData_df6" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "apply_market_data_config" \
  --new "apply_MarketData_config" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "save_ccxt_market_data" \
  --new "save_Ccxt_MarketData" \
  --exclude_dirs "$dir_names"
#
replace_text.py \
  --old "build_im_client_from_config" \
  --new "build_ImClient_from_System" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "get_EventLoop_MarketData_from_df" \
  --new "get_ReplayedMarketData_from_df" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "adapt_dag_to_real_time_from_config" \
  --new "get_RealTimeDag_from_System" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "get_HistoricalDag_from_system" \
  --new "build_HistoricalDag_from_System" \
  --exclude_dirs "$dir_names"
#
replace_text.py \
  --old "_apply_dag_runner_config" \
  --new "_apply_DagRunner_config" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "apply_dag_runner_config_for" \
  --new "apply_DagRunner_config_for" \
  --exclude_dirs "$dir_names"
#
replace_text.py \
  --old "add_process_forecasts_node" \
  --new "add_ProcessForecastsNode" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "check_system_config" \
  --new "check_SystemConfig" \
  --exclude_dirs "$dir_names"
