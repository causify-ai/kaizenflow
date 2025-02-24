#!/bin/bash -xe

replace_text.py \
    --old "save_node_stats" \
    --new "save_node_df_out_stats" \
    --ext "py,txt"
