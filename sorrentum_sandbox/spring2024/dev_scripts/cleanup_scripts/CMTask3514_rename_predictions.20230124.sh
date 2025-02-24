#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
    --old "(?<=ret_0_vol)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=ret_0_zscored)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=vol_sq)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=ret_0)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<![a-z])y_(?=\d)" \
    --new "y.shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<![a-z])y_hat_(?=\d)" \
    --new "y_hat.shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=10_vol)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=\svol)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "(?<=cumret)_(?=\d)" \
    --new ".shift_-" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old ",vol_2_hat" \
    --new ",vol.shift_-2_hat" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "vwap.ret_0.vol_adj_2" \
    --new "vwap.ret_0.vol_adj.shift_-2" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "vwap.ret_0.vol_adj_2_hat" \
    --new "vwap.ret_0.vol_adj.shift_-2_hat" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "ret_0_2_vol_2_hat" \
    --new "ret_0.shift_-2.vol.shift_-2_hat" \
    --exclude_dirs "$dir_names"

replace_text.py \
    --old "ret_0_2_vol_2" \
    --new "ret_0.shift_-2.vol.shift_-2" \
    --exclude_dirs "$dir_names"
