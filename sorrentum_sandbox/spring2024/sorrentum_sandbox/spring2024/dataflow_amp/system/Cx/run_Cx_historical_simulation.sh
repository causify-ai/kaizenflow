#!/bin/bash -xe
# TODO(Grisha): kill once CmTask5854 "Resolve backtest memory leakage" is resolved.
# OPTS="$OPTS --clean_dst_dir --no_confirm"
OPTS="$OPTS --num_threads serial"
# OPTS="$OPTS --skip_on_error"
# OPTS="$OPTS --dry_run"
OPTS="$OPTS $*"

# Train test modes.
export TRAIN_TEST_MODE="ins"
# export TRAIN_TEST_MODE="ins_oos"
# export TRAIN_TEST_MODE="rolling"

# Experement builders.
export EXPERIMENT_BUILDER="amp.dataflow.backtest.master_backtest.run_in_sample_tiled_backtest"
# export EXPERIMENT_BUILDER="amp.dataflow.backtest.master_backtest.run_ins_oos_tiled_backtest"
# export EXPERIMENT_BUILDER="amp.dataflow.backtest.master_backtest.run_rolling_tiled_backtest"

export DAG_BUILDER_NAME="C3a"
export DAG_BUILDER_CTOR_AS_STR="dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
export BACKTEST_CONFIG="ccxt_v7_4-all.5T.2022-06-01_2022-06-02"
export TAG="run0"
# Sometimes we want to set `DST_DIR` outside the current script, e.g., for the corresponding unit test.
# Uncomment when running a simulation.
# export DST_DIR="build_tile_configs.$DAG_BUILDER_NAME.$BACKTEST_CONFIG.$TRAIN_TEST_MODE.$TAG"

# Set `ImClient` config values.
export UNIVERSE_VERSION="v7.4"
export ROOT_DIR="s3://cryptokaizen-unit-test/v3"
export PARTITION_MODE="by_year_month"
export DATASET="ohlcv"
export CONTRACT_TYPE="futures"
export DATA_SNAPSHOT=""
export AWS_PROFILE="ck"
export RESAMPLE_1MIN=False
export VERSION="v1_0_0"
export DOWNLOAD_UNIVERSE_VERSION="v7_3"
export TAG="downloaded_1min"

# Specific of models that requires learning.
export FIT_AT_BEGINNING=None

# Specific of out-of-sample prediction.
# export OOS_START_DATE_AS_STR="2022-09-01"

export CONFIG_BUILDER="amp.dataflow_amp.system.Cx.Cx_tile_config_builders.get_Cx_config_builder_for_historical_simulations(\"$DAG_BUILDER_CTOR_AS_STR\",$FIT_AT_BEGINNING,train_test_mode=\"$TRAIN_TEST_MODE\",backtest_config=\"$BACKTEST_CONFIG\",universe_version=\"$UNIVERSE_VERSION\",root_dir=\"$ROOT_DIR\",partition_mode=\"$PARTITION_MODE\",dataset=\"$DATASET\",contract_type=\"$CONTRACT_TYPE\",data_snapshot=\"$DATA_SNAPSHOT\",aws_profile=\"$AWS_PROFILE\",resample_1min=$RESAMPLE_1MIN,version=\"$VERSION\",download_universe_version=\"$DOWNLOAD_UNIVERSE_VERSION\",tag=\"$TAG\")"
# export CONFIG_BUILDER="amp.dataflow_amp.system.Cx.Cx_tile_config_builders.get_Cx_config_builder_for_historical_simulations(\"$DAG_BUILDER_CTOR_AS_STR\",$FIT_AT_BEGINNING,train_test_mode=\"$TRAIN_TEST_MODE\",backtest_config=\"$BACKTEST_CONFIG\",oos_start_date_as_str=\"$OOS_START_DATE_AS_STR\")"

# Run.
/app/amp/dataflow/backtest/run_config_list.py \
    --experiment_builder $EXPERIMENT_BUILDER \
    --dst_dir $DST_DIR \
    --config_builder $CONFIG_BUILDER \
    $OPTS 2>&1

# Command line to run the pipeline for a single config. Used only for debugging.
# /app/amp/dataflow/backtest/run_config_stub.py --experiment_builder $EXPERIMENT_BUILDER --config_builder $CONFIG_BUILDER --config_idx 0 --dst_dir $DST_DIR | tee tmp.log.run_config_stub.txt
