#!/bin/bash -xe

# CmTask5743 - Replace the aliases of builtin types like np.int
#              to the Python native data types
dir_names="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts"

replace_text.py \
    --old "((?:np)|(?:numpy))\.(?=((?:int)|(?:float)|(?:bool)|(?:complex)|(?:object)|(?:str)|(?:long)|(?:unicode))([^0-9_]|$))" \
    --new "" \
    --ext "py,numba" \
    --exclude_dirs "$dir_names"
