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

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hprint.config_notebook()

# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.test_logger()
_LOG = logging.getLogger(__name__)

# %% [markdown]
# # Load data

# %% [markdown]
# ## Use ImClient

# %%
# TODO(max): Add ImClient (ok to use CCXT)

# %% [markdown]
# ## Read from file

# %%
# TODO(max): read cryptochassis
df = pd.read_csv("/app/vendors_lime/taq_bars/notebooks/data.csv", index_col=0)
df.head()

# %%
hpandas.df_to_str(df, print_shape_info=True)

# %% [markdown]
# # Analyze

# %%
# The format is like:

#     asset_id name    start_time    end_time    volume    close    ask    bid    sided_ask_count    sided_bid_count
# 0    1455235    WINM21    1622496660    1622496720    10374    126140.0    126150.0    126140.0    0    1347
# 1    1455235    WINM21    1622496720    1622496780    0    NaN    126150.0    126140.0    0    0

# %%
import vendors_lime.taq_bars.futures_utils as tu

import core.finance.tradability as cfintrad

# TODO(max): Use the right functions (calculate_twap)

df2 = tu.normalize_data(df)
hpandas.df_to_str(df2, print_shape_info=True)

# %%
df2.groupby("ric")["volume"].sum()

# %%
futs = [
    "WINM21",
    "NIFM1",
    "NBNM1",
    "WDON21",
    "SRBV1",
    "SIRTSM1",
    "NIRM1",
    "BRRTSN1",
    "CTAU1",
    "CMAU1",
    "SHHCV1",
    "ESM1",
    "TYU1",
    "SFUU1",
    "DSMU1",
    "DIJN21",
    "DCPU1",
    "DBYU1",
    "SAGZ1",
    "CFGU1",
]

# %% [markdown]
# ## Deep dive on one contract

# %%
# fut = "WINM21"
# fut = "ESM1"
fut = futs[3]
print(fut)
df_tmp = tu.filter_by_ric(df2, fut)["volume"]

pct_nans = df["close"].isnull().mean()
print("pct nans=", pct_nans)

pct_volume_0 = (df["volume"] == 0).mean()
print("pct_volume_0=", pct_volume_0)

df_tmp = df_tmp.dropna()
# print(df_tmp)

df_tmp.plot()

# %%
# Process data and print stats.

# fut = "WINM21"
# fut = "ESM1"
fut = futs[0]
print(fut)

df_tmp = tu.filter_by_ric(df2, fut)
# display(df_tmp.head(3))
hpandas.df_to_str(df_tmp, print_nan_info=True)
df_tmp = cfintrad.process_df(df_tmp, 5)

# print("trad.median=", df_tmp["trad"].median())
print(cfintrad.compute_stats(df_tmp))
df_tmp["trad"].hist(bins=101)

# %%
# Tradability over time.
df_tmp["time"] = df_tmp.index.time
display(df_tmp.head(3))
df_tmp.groupby("time")["trad"].mean().plot()

# %%
# Std dev over time.
df_tmp.groupby("time")["ret_0"].std().plot()

# %%
# Volume over time.

df_tmp.groupby("time")["volume"].sum().plot()
# df_tmp.groupby("time")["spread_bps"].std().plot()

# %%
df_tmp2 = df_tmp[["time", "ret_0"]]
# _ = df_tmp2.groupby("time").boxplot()#subplots=False)
# for time, df_0 in df_tmp2.groupby("time"):
#    print(df_0)

# %%
df_tmp2

df_tmp3 = []
for time, df_0 in df_tmp2.groupby("time"):
    # print(time, df_0["ret_0"])
    srs = pd.Series(df_0["ret_0"].values)
    srs.name = time
    df_tmp3.append(srs)
df_tmp3 = pd.concat(df_tmp3, axis=1)
df_tmp3.head()

df_tmp3.boxplot(rot=90)

# %%
df3 = df2.groupby("ric").apply(lambda df_tmp: cfintrad.process_df(df_tmp, 5))
df3.head(3)

# %%
# Compute stats for all futures.
gb = df3.reset_index(drop=True).groupby("ric").apply(cfintrad.compute_stats)

# gb.first()
gb.sort_values("trad")
