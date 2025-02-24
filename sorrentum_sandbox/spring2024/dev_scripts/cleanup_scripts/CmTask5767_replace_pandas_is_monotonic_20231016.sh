#!/bin/bash -xe

# CmTask5767 - Replace deprecated `is_monotonic` to `is_monotonic_increasing`
dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
    --old "is_monotonic(?!(_| is deprecated))" \
    --new "is_monotonic_increasing" \
    --ext "py,numba" \
    --exclude_dirs "$dir_names"