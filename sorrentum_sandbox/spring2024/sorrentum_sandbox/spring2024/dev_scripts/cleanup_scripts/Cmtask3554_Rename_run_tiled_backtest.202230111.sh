#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
    --old "run_tiled_backtest" \
    --new "run_in_sample_tiled_backtest" \
    --exclude_dirs "$dir_names"
