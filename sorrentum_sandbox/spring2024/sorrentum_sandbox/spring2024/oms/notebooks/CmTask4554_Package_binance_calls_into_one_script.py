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
import json


import ccxt
import requests


import logging

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe as imvcounun

# # %load_ext autoreload
# # %autoreload 2


# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Get last prices from coinmarketcap.com

# %%
CMC_PRO_API_KEY = "31eb170c-a347-4c3e-824a-76c5aaa8b22d"
LIMIT = "1000"
latest_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
parameters = {
  'start':'1',
  'limit': LIMIT,
  'convert':'USD'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': CMC_PRO_API_KEY,
}

# %%
result = requests.get(
    latest_url,
    params=parameters,
    headers=headers
)

# %%
mode = "trade"
vendor = "ccxt"
version = "v7.1"
universe = ivcu.get_vendor_universe(
    vendor, mode, version=version
)


# %%
market_data = pd.DataFrame(result.json()["data"])

# %%
market_data = market_data.groupby('symbol').apply(lambda x: x[x['id'] == x['id'].min()])

# %%
market_data

# %%
market_prices = market_data[["symbol", "quote"]]

# %%
market_prices["price"] = market_prices["quote"].apply(lambda x: x["USD"]["price"])

# %%
market_prices.drop(columns=["quote"], inplace=True)

# %%
market_prices

# %%
universe_symbols = pd.Series([
    symbol.split("_")[0]
    for symbol in universe["binance"]
])

# %%
universe_symbols[~universe_symbols.isin(market_prices.symbol)]

# %%
market_prices = market_prices[market_prices.symbol.isin(universe_symbols)]

# %%
market_prices = market_prices.set_index("symbol")

# %%
prices = market_prices.to_dict(orient="index")

# %%
prices = {
    key: prices[key]["price"]
    for key in prices
}

# %%
prices
