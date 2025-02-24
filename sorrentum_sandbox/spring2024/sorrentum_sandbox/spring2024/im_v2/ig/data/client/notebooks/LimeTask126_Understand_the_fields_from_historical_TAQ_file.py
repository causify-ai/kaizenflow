# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.ig.data.client.historical_bars as imvidchiba

# %%
hprint.config_notebook()

# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.test_logger()
_LOG = logging.getLogger(__name__)

# %% [markdown]
# ## Data

# %%
ig_date = "20190701"
df = imvidchiba.get_raw_historical_data(ig_date)

# %%
print(df.shape)

# %%
df.iloc[0]

# %%
df["start_time"].apply(lambda x: pd.Timestamp.utcfromtimestamp(x, utc=True))

# %%
dtf_df = imvidchiba.normalize_bar_data(df, drop_ts_epoch=True, inplace=False)

# %%
dtf_df2 = imvidchiba.normalize_bar_data(df, drop_ts_epoch=True, inplace=False)

# %%
dtf_df.equals(dtf_df2)

# %%
dtf_df.head(5)

# %%
print("\n".join(map(str, dtf_df.dropna().iloc[0].values)))

# %%
igid

# %%
igid = 13684
mask = dtf_df["igid"] == igid
dtf_df[mask]["open close low high".split()].dropna().tail(100).plot()
