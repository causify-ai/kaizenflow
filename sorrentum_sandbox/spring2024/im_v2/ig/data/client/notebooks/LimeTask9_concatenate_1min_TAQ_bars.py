# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import pandas as pd

import im_v2.ig.data.client.historical_bars as imvidchiba
import im_v2.ig.universe.ticker_igid_mapping as imviutigma

# %% [markdown]
# # Get IGID <-> Ticker mapping

# %%
mapping = imviutigma.get_id_mapping("20210614")

# %%
mapping

# %% run_control={"marked": true}
mapping = mapping.sort_values("volume", ascending=False).reset_index(drop=True)

# %%
mask = mapping["ticker"] == "AAPL"
mapping[mask]

# %%
mapping.head(30)

# %% [markdown]
# # Data loading helpers

# %%
date_srs = imvidchiba.get_dates()

# %%
date_srs

# %% [markdown]
# # Demo for Apple

# %%
df = imvidchiba.get_bars(17085, date_srs.loc["2014-12-02":"2014-12-05"])

# %%
df.info()

# %%
display(df.head(3))
display(df.tail(3))

# %%
df["close"].plot()

# %% [markdown]
# # Read data

# %% run_control={"marked": true}
assert 0
df = get_data(17085, date_srs.loc["2016-01-01":"2016-12-31"])

# %%
df.info()

# %%
assert 0
df.to_csv("AAPL_2016.csv")

# %%
df_2015 = imvidchiba.read_csv("/app/data/AAPL_2015.csv")

# %%
df_2015.head(3)

# %%
df_2016 = imvidchiba.read_csv("/app/data/AAPL_2016.csv")

# %%
df_2016.head(3)

# %%
df = pd.concat([df_2015, df_2016], axis=0)

# %%
df.info()

# %%
