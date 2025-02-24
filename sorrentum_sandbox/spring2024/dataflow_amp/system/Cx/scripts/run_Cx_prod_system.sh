#!/bin/bash -xe
OPTS="$OPTS -v DEBUG"
OPTS="$OPTS $*"

# Run date.
export RUN_DATE=$(date +'%Y%m%d')

# DagBuilder.
export DAG_BUILDER_CTOR_AS_STR="dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
export DAG_BUILDER_NAME="C3a"

# Run mode.
export RUN_MODE="prod"

/app/amp/dataflow_amp/system/Cx/scripts/run_Cx_prod_system.py \
    --dag_builder_ctor_as_str $DAG_BUILDER_CTOR_AS_STR \
    --run_mode $RUN_MODE \
    --trade_date ${RUN_DATE} \
    --strategy $DAG_BUILDER_NAME \
    --liveness CANDIDATE \
    --exchange 'binance' \
    --instance_type PROD \
    --stage 'preprod' \
    --account_type 'trading' \
    --secret_id 3 \
    --run_duration 600 \
    --dst_dir ./system_log_dir_${RUN_DATE}_15minutes \
    --log_file_name ./log_${RUN_DATE}_15minutes.txt \
    # --set_config_value '("process_forecasts_node_dict","process_forecasts_dict","order_config","order_type"),(str("price@custom_twap"))' \
    # --set_config_value '("process_forecasts_node_dict","process_forecasts_dict","order_config","passivity_factor"),(float(0.55))' \
    # --set_config_value '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal"))' \
    # --set_config_value '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(1.0)})' \
    $OPTS 2>&1

# --print_config \
