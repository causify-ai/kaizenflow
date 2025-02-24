#!/bin/bash -xe

python dev_scripts/replace_text.py \
  --old "(pd\.Series\(\))|pd\.Series\(\[\]\)" \
  --new 'pd.Series(dtype="float64")' \
  --ext "ipynb,py"
