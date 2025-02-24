#!/bin/bash -xe
export SRC_DIR=$HOME/src_vc/lemonade1
export MODEL_DIR=dataflow_lemonade
export DST_DIR=$HOME/src/orange1
export MODEL_NAME=C12
cd $SRC_DIR
amp/dev_scripts/encrypt_models/encrypt_model.py \
    --input_dir $MODEL_DIR/pipelines \
    --output_dir $MODEL_DIR/encrypted_pipelines \
    --release_dir $DST_DIR/$MODEL_DIR/pipelines \
    --model_dag_builder "${MODEL_NAME}a_DagBuilder" \
    --model_dag_builder_file ${MODEL_NAME}/${MODEL_NAME}a_pipeline.py \
    --test \
    -v DEBUG \
    2>&1 | tee encrypt_model.log

