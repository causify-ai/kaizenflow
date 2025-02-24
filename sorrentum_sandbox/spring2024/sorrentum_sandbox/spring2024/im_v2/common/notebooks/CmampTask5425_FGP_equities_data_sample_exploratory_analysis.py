# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Process input file

# %% [markdown]
# In this notebook we will load sample trades data (https://drive.google.com/file/d/1up5otVlfw-RX1S6K8o4d2nNRPP-lKran/view), resample them and store on S3 in a parquet tiled format

# %% [markdown]
# Assuming the tar archive is in the root of the repository

# %%
# ! mkdir data && tar xf /app/msfttaqcsv202308.tar -C ./data

# %%
# !ls ./data

# %% [markdown]
# ## Imports

# %%
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hparquet as hparque
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)
log_level = logging.INFO

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# ## Load data

# %%
data = pd.read_csv("data/uT1dPod8mR2s_MSFT US Equity_trades_1_1.csv.gz")

# %%
data.head()

# %% [markdown]
# Drop columns with all NaNs

# %%
data = data.dropna(axis=1, how="all")

# %%
data.head()

# %%
data["SECURITY"].value_counts()

# %%
null_size = data[data["EVT_TRADE_SIZE"] == 0]

# %%
null_size.shape

# %% [markdown]
# Some trades have 0 size

# %%
null_size.head()

# %%
data.dtypes

# %% [markdown]
# Set datetime index

# %%
data["timestamp"] = pd.to_datetime(data["TRADE_REPORTED_TIME"])
data = data.set_index("timestamp", drop=True)

# %% [markdown]
# Prepare relevant columns and set index

# %%
data = data[["EVT_TRADE_PRICE", "EVT_TRADE_SIZE"]]

# %% [markdown]
# ## Compute OHLCV
#
# Our time interval labelling convention is that time interval [a, b) is labelled as b.
#
# E.g. for interval [06:40:00, 06:41:00) the timestamp is
# 06:41:00

# %%
data_ohlcv = (
    data["EVT_TRADE_PRICE"].resample("1T", closed="left", label="right").ohlc()
)

# %%
data_volume = (
    data["EVT_TRADE_SIZE"].resample("1T", closed="left", label="right").sum()
)
data_volume.name = "volume"

# %%
data = pd.concat([data_ohlcv, data_volume], axis=1)

# %%
data.head()

# %%
data["currency_pair"] = "MSFT"
data["knowledge_timestamp"] = pd.Timestamp.utcnow()

# %%
data.head()

# %% [markdown]
# ## Save as parquet

# %%
partition_mode = "by_year_month"
# TODO(Juraj): FGP doesn't have access to this bucket
s3_path = "s3://cryptokaizen-data-test/v3/bulk/manual/resampled_1min/parquet/ohlcv/spot/v1/bloomberg/us_market/v1_0_0/"
aws_profile = "ck"

# %%
data, partition_cols = hparque.add_date_partition_columns(data, partition_mode)
hparque.to_partitioned_parquet(
    data,
    ["currency_pair"] + partition_cols,
    s3_path,
    aws_profile=aws_profile,
)

# %% [markdown]
# ## Load back from parquet

# %%
ohlcv_data = hparque.from_parquet(s3_path, aws_profile=aws_profile)

# %%
ohlcv_data.head()

# %%
ohlcv_data.index.min()

# %%
ohlcv_data.index.max()

# %%
