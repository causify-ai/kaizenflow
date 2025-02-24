#!/bin/bash -x

if [[ 0 == 1 ]]; then
im/kibot/data/extract/download.py \
    --dataset 'sp_500_1min' \
    -u abc@xyz.com -p s33f3c3c3 \
    --no_incremental
fi;

if [[ 1 == 1 ]]; then
im/kibot/data/transform/convert_csv_to_pq.py --dataset all_forex_pairs_1min -v DEBUG
fi;

./dev_scripts/tg.py

#    --serial
#    --dry_run \

# DONE: sp_500_tickbidask
# sp_500_unadjusted_tickbidask
# DONE: sp_500_1min
# DONE: sp_500_unadjusted_1min
# DONE: sp_500_daily
# DONE: sp_500_unadjusted_daily
