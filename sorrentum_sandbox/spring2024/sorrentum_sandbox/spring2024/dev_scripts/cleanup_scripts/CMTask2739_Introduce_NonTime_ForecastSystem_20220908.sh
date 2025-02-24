#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts"

replace_text.py \
  --old "(?<!Time_)ForecastSystem" \
  --new "NonTime_ForecastSystem" \
  --exclude_dirs "$dir_names" 
