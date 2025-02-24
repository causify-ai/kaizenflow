# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2


import pandas as pd

import helpers.hpandas as hpandas
import helpers.hs3 as hs3

# %%
AM_AWS_PROFILE = "am"
S3_BUCKET = hs3.get_s3_bucket_path(AM_AWS_PROFILE, add_s3_prefix=False)
file_name = f"s3://{S3_BUCKET}/data/kibot/sp_500_1min/AAPL.csv.gz"

s3fs = hs3.get_s3fs("am")
# This call was broken during a refactoring and this fix is not
# guaranteed to work.
try:
    df = hpandas.read_csv_to_df(file_name)
except Exception:  # pylint: disable=broad-except
    df = hpandas.read_csv_to_df(s3fs)
df.head(5)

# %%
file_name = f"s3://{S3_BUCKET}/data/kibot/pq/sp_500_1min/AAPL.pq"
pd.read_parquet(file_name)
