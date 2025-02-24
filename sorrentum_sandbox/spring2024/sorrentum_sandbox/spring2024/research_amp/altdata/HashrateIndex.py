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
# # Imports

# %%
import os

import requests

# %% [markdown]
# This repository is not python module, we can't install it, so let's download the code.

# %% run_control={"marked": false}
def download_file(link: str):
    code = requests.get(link).text
    name = link.split("/")[-1]
    with open(name, "w") as f:
        f.write(code)


hashrateindex = "https://raw.githubusercontent.com/LuxorLabs/hashrateindex-api-python-client/master/hashrateindex.py"
resolver = "https://raw.githubusercontent.com/LuxorLabs/hashrateindex-api-python-client/master/resolvers.py"

download_file(resolver)
download_file(hashrateindex)

# %% run_control={"marked": false}
from hashrateindex import API
from resolvers import RESOLVERS

# %% [markdown]
# # Set-up

# %%
key1 = os.environ["HASHRATE_KEY"]

# %%
API = API(host="https://api.hashrateindex.com/graphql", method="POST", key=key)
RESOLVERS = RESOLVERS(df=True)

# %% [markdown]
# # Research

# %% [markdown]
# `get_hashprice` and `get_asic_price_index` functions take interval and currency as an input in `"_1_YEAR,BTC"` string format. The rest of the functions uses only interval parameter. Options of intervals: `_1_DAY`, `_7_DAYS`, `_1_MONTH`, `_3_MONTHS`, `_1_YEAR` and `ALL`

# %% [markdown]
# ## Get hashprice

# %% [markdown]
# Get hashprice for BTC at 7 day intervals.

# %%
function = "get_hashprice"
params = "ALL,BTC"

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_hashprice(hashprice)

# %% [markdown]
# ## Get bitcoin overview

# %%
function = "get_bitcoin_overview"
params = ""

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_bitcoin_overview(hashprice)

# %% [markdown]
# ## Get network hashrate

# %%
function = "get_network_hashrate"
params = "ALL"

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_network_hashrate(hashprice)

# %% [markdown]
# ## Get network difficulty

# %%
function = "get_network_difficulty"
params = "ALL"

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_network_difficulty(hashprice)

# %% [markdown]
# ## Get OHLC prices

# %%
function = "get_ohlc_prices"
params = "ALL"

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_ohlc_prices(hashprice)

# %% [markdown]
# ## Get asic price index

# %%
function = "get_asic_price_index"
params = "ALL,BTC"

hashprice = API.exec(function, params)

RESOLVERS.resolve_get_asic_price_index(hashprice)

# %% [markdown]
# # Remove scripts

# %%
os.remove("hashrateindex.py")
os.remove("resolvers.py")
