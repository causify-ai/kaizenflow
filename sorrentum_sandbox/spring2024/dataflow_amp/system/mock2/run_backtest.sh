#!/bin/bash -xe
clear

OPTS="$OPTS --clean_dst_dir --no_confirm"
OPTS="$OPTS --num_threads serial"
OPTS="$OPTS $*"

tag="mock2"
backtest_config="bloomberg_v1-top1.5T.2023-08-01_2023-08-31"
config_builder="dataflow_amp.system.mock2.mock2_tile_config_builders.build_Mock2_tile_config_list(\"${backtest_config}\")"

dst_dir="build_Mock2_tile_config_list.${tag}.${backtest_config}.run1"

./dataflow/backtest/run_config_list.py \
    --experiment_builder "dataflow.backtest.master_backtest.run_in_sample_tiled_backtest" \
    --config_builder $config_builder \
    --dst_dir $dst_dir \
    $OPTS 2>&1 | tee run_config_list.txt
