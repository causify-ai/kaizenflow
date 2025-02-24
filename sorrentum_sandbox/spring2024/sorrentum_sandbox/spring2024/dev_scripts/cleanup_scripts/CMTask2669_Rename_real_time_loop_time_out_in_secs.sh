#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "real_time_loop_time_out_in_secs: Optional[int]" \
  --new "rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]]" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "real_time_loop_time_out_in_secs" \
  --new "rt_timeout_in_secs_or_time" \
  --exclude_dirs "$dir_names"

if [[ 0 == 1 ]]; then
replace_text.py \
  --old "time_out_in_secs: int" \
  --new "rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time]]" \
  --only_dirs "core dataflow helpers dataflow_amp" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "time_out_in_secs" \
  --new "rt_timeout_in_secs_or_time" \
  --only_dirs "core dataflow helpers dataflow_amp" \
  --exclude_dirs "$dir_names"
fi;
