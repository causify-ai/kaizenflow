#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "_convert_to_multiindex" \
  --new "convert_to_multiindex" \
  --exclude_dirs "$dir_names" \
  --ext "py,ipynb"
