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
    -v DEBUG \
    2>&1 | tee encrypt_model.log

#amp/dev_scripts/encrypt_models/encrypt_model.py \
#    --input_dir $MODEL_DIR/system \
#    --output_dir $MODEL_DIR/encrypted_system \
#    --release_dir $DST_DIR/$MODEL_DIR/system \
#    -v DEBUG \
#    2>&1 | tee encrypt_model.log
