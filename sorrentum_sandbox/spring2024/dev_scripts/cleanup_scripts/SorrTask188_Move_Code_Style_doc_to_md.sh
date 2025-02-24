#!/bin/bash -xe

replace_text.py \
  --action "replace" \
  --old "<a name=".+"><\/a>" \
  --new "" \
  --ext "_all_" \
  --only_files "docs/Coding_Style_Guide.md" \
