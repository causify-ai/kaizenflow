# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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
# # Description

# %% [markdown]
# This notebook is used to find currencies that are exactly the same in our universe.

# %% [markdown]
# # Imports

# %%
import logging
import os

import seaborn as sns

import core.config.config_ as cconconf
import core.plotting as coplotti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.common.universe as ivcu
import research_amp.cc.statistics as ramccsta

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Config

# %%
def get_config() -> cconconf.Config:
    """
    Get config that controls parameters.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = AM_AWS_PROFILE
    config["load"]["data_dir"] = os.path.join(
        hs3.get_s3_bucket_path(AM_AWS_PROFILE), "data"
    )
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["universe_version"] = "v03"
    config["data"]["data_type"] = "OHLCV"
    config["data"]["vendor"] = "CCXT"
    config["data"]["price_column"] = "close"
    return config


config = get_config()
print(config)

# %% [markdown]
# # Get price data for a given universe

# %%
vendor_universe = ivcu.get_vendor_universe(
    config["data"]["vendor"],
    version=config["data"]["universe_version"],
    as_full_symbol=True,
)
vendor_universe

# %%
df_price = ramccsta.get_universe_price_data(vendor_universe, config)
df_price.head(3)

# %%
df_price.describe().round(2)

# %%
df_price.head()

# %% [markdown]
# # Find same currencies

# %%
df_returns = df_price.pct_change()
df_returns.head(3)

# %%
corr_matrix = df_returns.corr()
_ = coplotti.plot_heatmap(corr_matrix)

# %% [markdown]
# `cluster_and_select()` distinguishes clusters but some very highly correlated stable coins are clustered together so it seems like that we cannot rely on dendrodram and clustering alone.

# %%
_ = coplotti.cluster_and_select(df_returns, 11)

# %% run_control={"marked": false}
_ = sns.clustermap(corr_matrix, figsize=(20, 20))

# %% run_control={"marked": false}
# Display top 10 most correlated series for each currency pair.
for colname in corr_matrix.columns:
    corr_srs = corr_matrix[colname]
    corr_srs_sorted = corr_srs.sort_values(ascending=False)
    display(corr_srs_sorted.head(10))

# %% [markdown]
# # Calculations on data resampled to 1 day

# %%
df_price_1day = df_price.resample("D", closed="right", label="right").mean()
df_price_1day.head(3)

# %%
df_returns_1day = df_price_1day.pct_change()
df_returns_1day.head(3)

# %%
corr_matrix_1day = df_returns_1day.corr()
_ = coplotti.plot_heatmap(corr_matrix_1day)

# %% [markdown]
# Resampling to 1 day makes clusters much more visible. <br>
# If we take a look at correlation numbers, we can see that equal currencies on different exchanges have a correlation above ~0.94 while different currencies correlate at much less rate.
#
# Therefore, it seems that for detecting similar currencies we'd better use 1 day frequency.

# %%
_ = coplotti.cluster_and_select(df_returns_1day, 11)

# %%
_ = sns.clustermap(corr_matrix_1day, figsize=(20, 20))

# %%
# Display top 10 most correlated series for each currency pair.
for colname in corr_matrix_1day.columns:
    corr_srs = corr_matrix_1day[colname]
    corr_srs_sorted = corr_srs.sort_values(ascending=False)
    display(corr_srs_sorted.head(10))
