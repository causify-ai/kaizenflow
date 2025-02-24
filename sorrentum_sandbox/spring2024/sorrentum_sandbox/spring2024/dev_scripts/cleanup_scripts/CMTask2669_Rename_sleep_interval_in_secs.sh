#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "sleep_interval_in_secs: float" \
  --new "bar_duration_in_secs: int" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "sleep_interval_in_secs" \
  --new "bar_duration_in_secs" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "grid_time_in_secs: float" \
  --new "bar_duration_in_secs: int" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "grid_time_in_secs" \
  --new "bar_duration_in_secs" \
  --exclude_dirs "$dir_names"
