#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "(?<!def\s)(?<!\.)(\btimestamp_as_str_to_timestamp\b)" \
  --new "hdateti.str_to_timestamp" \
  --exclude_dirs "$dir_names" \
  --ext "py,ipynb"

replace_text.py \
  --old "omreconc.timestamp_as_str_to_timestamp" \
  --new "hdateti.str_to_timestamp" \
  --exclude_dirs "$dir_names" \
  --ext "py,ipynb"

replace_text.py \
  --old "oms.timestamp_as_str_to_timestamp" \
  --new "hdateti.str_to_timestamp" \
  --exclude_dirs "$dir_names" \
  --ext "py,ipynb"
