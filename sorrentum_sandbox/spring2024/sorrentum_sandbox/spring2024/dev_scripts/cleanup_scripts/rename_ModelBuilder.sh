#!/bin/bash

action="rename"
script_name="amp/dev_scripts/cleanup_scripts/rename_ModelBuilder.sh"

exts="_all_"

# --exclude_files $script_name \

replace_text.py \
    --old ModelBuilder \
    --new DagBuilder \
    --ext $exts \
    --action $action \
    --exclude_files $script_name \
    -v DEBUG \
    $*
