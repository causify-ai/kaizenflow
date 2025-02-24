# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd
import vendors_lime.datastream_liquidity.universe_utils as vldlunut

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsql as hsql

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

# _LOG.info("%s", env.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load liquidity files

# %%
connection = hsql.get_connection(
    "dp-research.redshift"
    "refdata",
    5439,
)

# %%
date = "2022-03-01"

# apply_categorical_filters = False
apply_categorical_filters = True
add_rankings = False
df = vldlunut.generate_liquidity_df(
    date,
    connection,
    apply_categorical_filters=apply_categorical_filters,
    add_rankings=add_rankings,
)

print("df=", df.shape)
display(df.head(3))

# %%
df.head()

# %%
print("region=", df["region"].unique())

print("trade_date=", df["trade_date"].unique())

print("num(asset_ids)=", df["asset_id"].nunique())

print("num(infocode)=", df["infocode"].nunique())

print("country=\n%s" % df["country"].value_counts())

print("is_major_sec=\n%s" % df["is_major_sec"].value_counts())

print("is_prim_qt=\n%s" % df["is_prim_qt"].value_counts())

print("sectype=\n%s" % df["sectype"].value_counts())

# %%
# mask = df["sectype"] == "NA:P "
# mask = df["sectype"] == "NA:F "
mask = df["is_prim_qt"] == False
df[mask]
print(df[mask]["ticker"])

# %%
mask = df["ticker"] == "SPY"
# mask = (df["ticker"] == "AAPL")
display(df[mask])
display(df[mask]["sectype"])

# %%
df.iloc[0]

# %%
df.columns.to_list()

# %%
df["spread_usd_21d"].hist(bins=101)

# %%
# col = "spread_bps_21d"
col = "spread_usd_21d"
df_val = df[df[col] <= 0.1]

# print(df_val)

df_val[col].hist(bins=101)

print(df_val[col].sum())

# df["spread_bps_21d"].hist(bins=101)

# %%

# %% [markdown]
# df["spread_bps_21d"].hist(bins=101)
# # Generate liquidity plots

# %%
df[df["spread_bps_63d"] < 200]["spread_bps_63d"].hist(log=False, bins=101)

# %%
df[df["spread_usd_63d"] < 0.2]["spread_usd_63d"].hist(log=False, bins=101)

# %%
df["mkt_cap_usd_avg_90d"].hist(log=True, bins=100)

# %% [markdown]
# # Apply filters

# %%
filtered_df = vldlunut.apply_threshold_filters(df)

# %%
filtered_df.describe()

# %%
filtered_df[filtered_df["ticker"].isna()]

# %%
tickers = filtered_df["ticker"].dropna().to_list()

# %%
assert 0

# %% [markdown]
# # Get universe dataframe at datetime

# %%
universe = vldlunut.get_filtered_universe_dfs([date], connection)[0]

# %%
dates = pd.date_range(
    start="2017-01-01", end="2022-03-01", freq=pd.offsets.BMonthBegin()
)

# %%
universe_dfs = vldlunut.get_filtered_universe_dfs(dates, connection)

# %%
df = universe_dfs[10]

# %%
df.head()

# %%
df = vldlunut.combine_universe_dfs(universe_dfs)

# %%
df.iloc[0:10, 0:10]

# %%
asset_ids = df.columns.to_list()

# %%
len(asset_ids)

# %%
(df.sum(axis=0) / df.shape[0]).hist(bins=20)

# %%
df.sum(axis=1).plot(ylim=(0, None), title="Universe size count")

# %% [markdown]
# # Save universe

# %%
# Write union of EGIDs to a csv
assert 0
pd.Series(data=df.columns).to_csv("universe_20210810.csv", index=False)

# %% [markdown]
# # Read universe

# %%
import pandas as pd

# %%
universe = pd.read_csv("s3://data/universe_20210810.csv")

# %%
universe

# %%
universe["asset_id"].tolist()
