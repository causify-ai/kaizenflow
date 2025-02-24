#!/bin/bash -xe

dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
    --old "_Cx_ProdSystem(?=\()" \
    --new "_Cx_ProdSystemMixin" \
    --exclude_dirs "$dir_names" 

replace_text.py \
    --old "(?<=\s|.)Cx_ProdSystem(?=\()" \
    --new "Cx_ProdSystem_v1_20220727" \
    --exclude_dirs "$dir_names"
