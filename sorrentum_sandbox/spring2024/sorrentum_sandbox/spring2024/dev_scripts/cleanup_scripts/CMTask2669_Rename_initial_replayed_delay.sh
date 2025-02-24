#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "initial_replayed_delay: int" \
  --new "replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp]" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "initial_replayed_delay" \
  --new "replayed_delay_in_mins_or_timestamp" \
  --exclude_dirs "$dir_names"
