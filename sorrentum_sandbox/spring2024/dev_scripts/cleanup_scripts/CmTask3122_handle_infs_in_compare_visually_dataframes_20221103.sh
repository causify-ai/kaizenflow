#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "compare_visually_dataframes" \
  --new "compare_dfs" \
  --exclude_dirs "$dir_names"
