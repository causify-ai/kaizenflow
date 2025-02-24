#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
  --old "load_ccxt_child_order_responses" \
  --new "load_ccxt_order_response_df" \
  --exclude_dirs "$dir_names"

replace_text.py \
  --old "load_child_orders" \
  --new "load_child_order_df" \
  --exclude_dirs "$dir_names"  

replace_text.py \
  --old "load_child_order_fills" \
  --new "load_ccxt_fills_df" \
  --exclude_dirs "$dir_names"

  replace_text.py \
  --old "align_child_orders_and_fills" \
  --new "align_ccxt_orders_and_fills" \
  --exclude_dirs "$dir_names" 
