#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "initial_replayed_dt" \
  --new "initial_replayed_timestamp" \
  --exclude_dirs "$dir_names"
