# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# The goal of this notebook is to show how synthetic market data is generated using the following methods:
# - `generate_random_price_data` (for one and multiple assets)
# - `generate_random_bars`
# - `get_gaussian_walk`

# %% [markdown]
# ## Imports

# %%
import logging

import matplotlib.pyplot as plt
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.finance as cofinanc
import core.finance.market_data_example as cfmadaex
import dataflow.core as dtfcore
import dataflow.core.utils as dtfcorutil
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Generate the data

# %% [markdown]
# ## Using `generate_random_price_data` for multiple assets

# %% [markdown]
# Problems:
# - Generated prices are the same for all assets
# - Distribution of returns is not normal

# %%
# Generate the initial price data.
start_datetime = pd.Timestamp("2021-01-01")
end_datetime = pd.Timestamp("2021-01-31")
columns = ["close"]
asset_ids = list(range(2))
freq = "1T"
initial_price = 29000
seed = (100,)

df = cfmadaex.generate_random_price_data(
    start_datetime,
    end_datetime,
    columns,
    asset_ids,
    freq=freq,
    initial_price=initial_price,
    seed=seed,
)

df = df.set_index("timestamp_db").drop(columns=["start_datetime", "end_datetime"])
df = dtfcorutils.convert_to_multiindex(df, "asset_id")

# %%
# Calculate returns.
node_returns_config = {
    "in_col_groups": [
        ("close",),
    ],
    "out_col_group": (),
    "transformer_kwargs": {
        "mode": "pct_change",
    },
    "col_mapping": {
        "close": "close.ret_0",
    },
}
# Create the node that computes ret_0.
nid = "ret0"
node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=cofinanc.compute_ret_0,
    **node_returns_config,
)
# Compute the node on the data.
rets = node.fit(df)

# %%
# Show DataFrame with prices and returns for multiple assets.
df = rets["df_out"]
df.head(5)

# %%
# Plot the prices.
df[["close"]].plot(figsize=(15, 7))

# %%
# Plot returns.
df[["close.ret_0"]].plot(figsize=(15, 7))

# %% [markdown]
# ## Using `generate_random_price_data` for one asset
#

# %% [markdown]
# Problems:
# - Distribution of returns is not normal

# %%
start_datetime = pd.Timestamp("2021-01-01")
end_datetime = pd.Timestamp("2021-01-31")
columns = ["close"]
asset_ids = [1]
freq = "1T"
initial_price = 29000
seed = (100,)

df = cfmadaex.generate_random_price_data(
    start_datetime,
    end_datetime,
    columns,
    asset_ids,
    freq=freq,
    initial_price=initial_price,
    seed=seed,
)

df = df.set_index("timestamp_db").drop(
    columns=["start_datetime", "end_datetime", "asset_id"]
)
df["rets"] = cofinanc.compute_ret_0(df[["close"]], "pct_change")
df.head(3)

# %%
df[["close"]].plot(figsize=(15, 7))
df[["rets"]].plot(figsize=(15, 7))

# %%
fig = plt.figure(figsize=(15, 7))
ax1 = fig.add_subplot(1, 1, 1)
df["rets"].hist(bins=50, ax=ax1)
ax1.set_xlabel("Return")
ax1.set_ylabel("Sample")
ax1.set_title("Return distribution")
plt.show()

# %% [markdown]
# ## Using `generate_random_bars`
#

# %% [markdown] run_control={"marked": true}
# Problems:
# - Strange outcomes

# %%
# Generate the data.
start_datetime = pd.Timestamp("2021-01-01")
end_datetime = pd.Timestamp("2021-01-31")

df = cfmadaex.generate_random_bars(
    start_datetime,
    end_datetime,
    asset_ids=[1, 2],
)

df = df.set_index("timestamp_db").drop(columns=["start_datetime", "end_datetime"])
df = dtfcorutil.convert_to_multiindex(df, "asset_id")

# %%
# Show prices.
df["close"].plot(figsize=(15, 7))

# %%
# Calculate returns.
node_returns_config = {
    "in_col_groups": [
        ("close",),
    ],
    "out_col_group": (),
    "transformer_kwargs": {
        "mode": "pct_change",
    },
    "col_mapping": {
        "close": "close.ret_0",
    },
}
# Create the node that computes ret_0.
nid = "ret0"
node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=cofinanc.compute_ret_0,
    **node_returns_config,
)
# Compute the node on the data.
rets = node.fit(df)
rets["df_out"].head(3)

# %%
# Show returns.
rets["df_out"]["close.ret_0"].plot(figsize=(15, 7))

# %% [markdown]
# ## Using returns directly (`get_gaussian_walk`)

# %%
drift = 0
vol = 0.2
size = 252
seed = 10
rets = carsigen.get_gaussian_walk(drift, vol, size, seed=seed).diff()

# %%
rets.plot()

# %%
fig = plt.figure(figsize=(15, 7))
ax1 = fig.add_subplot(1, 1, 1)
rets.hist(bins=50, ax=ax1)
ax1.set_xlabel("Return")
ax1.set_ylabel("Sample")
ax1.set_title("Returns distribution")
plt.show()
