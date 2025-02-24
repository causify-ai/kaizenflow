#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
   --old "_to_multi_line_cmd" \
   --new "to_multi_line_cmd" \
   --exclude_dirs "$dir_names"
