#!/bin/bash

#exts="_all_"
#exts="py,ipynb,txt,sh"
exts="py"

#OPTS="--preview"
OPTS="$OPTS $*"

script_name="amp/dev_scripts_lime/cleanup_scripts/rename_backtest_config.sh"

#
#action="replace_rename"
action="replace"
replace_text.py \
    --old bm_config \
    --new backtest_config \
    --action $action \
    --exclude_files $script_name \
    --ext $exts \
    $OPTS

##
#action="rename"
#replace_text.py \
#    --old RH8E \
#    --new E8 \
#    --action $action \
#    --exclude_files $script_name \
#    --ext $exts \
#    $OPTS
