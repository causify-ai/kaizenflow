#!/bin/bash -xe

# CmTask531 - Move golden outcomes from `test` dirs to `test/outcomes` dirs.
replace_text.py \
  --action "rename" \
  --filter_by "/test/Test.+/" \
  --filter_on "dirname" \
  --old "/test/" \
  --new "/test/outcomes/" \
  --replace_in "dirname" \
  --ext "_all_" \
