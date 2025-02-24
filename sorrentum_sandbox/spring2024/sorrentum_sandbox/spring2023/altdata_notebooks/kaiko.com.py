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
# # Description

# %% [markdown]
# This notebook contains description of the (public) endpoints of [kaiko.com](kaiko.com) digital asset data aggregator
#
# API documentation: https://docs.kaiko.com/

# %%
import requests

# %% [markdown]
# ## Reference API

# %% [markdown]
# https://docs.kaiko.com/#reference-data-api
#
# Check public endpoints.

# %%
api_url = "https://reference-data-api.kaiko.io/"

# %%
# Assets.
assets_url = api_url + "v1/assets/"
response = requests.get(assets_url)
data = response.json()
data.keys()

# %%
# Get size of the entire asset universe.
len(data["data"])

# %%
# Get examples of asset metadata.
data["data"][410:415]

# %%
# Exchanges.
exchanges_url = api_url + "v1/exchanges/"
response = requests.get(exchanges_url)
data = response.json()
data.keys()

# %%
len(data["data"])

# %%
data["data"][30:40]

# %%
# Instruments.
# https://docs.kaiko.com/#instruments
instr_url = api_url + "v1/instruments/"
response = requests.get(instr_url)
data = response.json()
data.keys()

# %%
# Total number of retrieved instruments, same as `len(data["data"])`.
data["count"]

# %%
data["data"][100:105]

# %%
# Pools.
pools_url = api_url + "v1/pools/"
response = requests.get(pools_url)
data = response.json()
data.keys()

# %%
# Total number of pools, same as `len(data["data"])`.
data["count"]

# %%
data["data"][110:115]

# %% [markdown]
# ## Commentary

# %% [markdown]
# The public reference API gives only the information on the universe, i.e. the assets, exchanges, instruments and pools.
# Actual examples of data can be obtained by applying for a demo and having a trial subscription.
