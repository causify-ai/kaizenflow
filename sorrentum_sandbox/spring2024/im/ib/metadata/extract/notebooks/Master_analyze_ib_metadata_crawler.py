# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.0
#   kernelspec:
#     display_name: Python [conda env:venv] *
#     language: python
#     name: conda-env-venv-py
# ---

# %%
import glob
import os

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3

# %%
# !ls ..

# %% [markdown]
# ## Symbols

# %%
if False:
    dir_name = ".."
    files = glob.glob(os.path.join(dir_name, "symbols*.csv"))
    hdbg.dassert(len(files), 1)
    file_name = files[0]

AM_AWS_PROFILE = "am"
S3_BUCKET = hs3.get_s3_bucket_path(AM_AWS_PROFILE, add_s3_prefix=False)
file_name = (
    f"s3://{S3_BUCKET}/data/ib/metadata/symbols-2021-04-01-143112738505.csv"
)
s3fs = hs3.get_s3fs("am")
print("file_name=%s" % file_name)
stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
symbols = hpandas.read_csv_to_df(stream, sep="\t", **kwargs)

print(len(symbols))

symbols.head(3)

# %%
symbols.groupby("product").count()

# %% [markdown]
# ## Exchanges

# %%
if False:
    files = glob.glob(os.path.join(dir_name, "exchanges*.csv"))
    hdbg.dassert(len(files), 1)
    file_name = files[0]
file_name = (
    f"s3://{S3_BUCKET}/data/ib/metadata/exchanges-2021-04-01-143112738505.csv"
)

print("file_name=%s" % file_name)
exchanges = pd.read_csv(file_name, aws_profile=aws_profile, sep="\t")

print(len(exchanges))

exchanges.head(3)

# %% [markdown]
# ## Products

# %%
print(symbols["product"].unique())

# %% [markdown]
# ## Markets

# %%
markets = sorted(symbols["market"].unique())
print("\n".join(markets))

# %%
grouped = symbols.groupby("market")

count = grouped[["product"]].count()
count = count.sort_values(by="product", ascending=False)

count.plot()

print(count.head(10))

# %%
idx = 0
market = count.index[idx]
print("market=", market)
mask = symbols["market"] == market
symbols_tmp = symbols[mask]

grouped = symbols_tmp.groupby("product")

grouped[["product"]].count()

# %%
pd.set_option("display.max_colwidth", 100)

# %%
symbols_tmp[["product", "url"]]

# %%
symbols_tmp["url"].values

# %%
