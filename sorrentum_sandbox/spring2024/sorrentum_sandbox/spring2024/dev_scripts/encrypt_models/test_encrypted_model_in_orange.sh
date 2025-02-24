#!/bin/bash -xe
export MODEL_DIR=dataflow_lemonade
amp/dev_scripts/encrypt_models/encrypt_model.py \
    --input_dir $MODEL_DIR/pipelines \
    --test \
    --model_dag_builder "C1a_DagBuilder" \
    --model_dag_builder_file C1/C1a_pipeline.py \
    -v DEBUG \
    2>&1 | tee encrypt_model.log
