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

# %% [markdown] heading_collapsed=true
# # Imports

# %% hidden=true
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

# %load_ext autoreload
# %autoreload 2


# %% hidden=true
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown] heading_collapsed=true
# # Get coinmarketcap top 200

# %% hidden=true
# To download top 100 from https://coinmarketcap.com/ we will use it's API. 
# Simple registration give us personal API KEY

CMC_PRO_API_KEY = "31eb170c-a347-4c3e-824a-76c5aaa8b22d"
LIMIT = "200"
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

# %% hidden=true
result = requests.get(
    latest_url,
    params=parameters,
    headers=headers
)

# %% hidden=true
data = result.json()["data"]

# %% hidden=true
coinmarketcap_symbols = [e["symbol"] for e in data]

# %% hidden=true
coinmarketcap_symbols = pd.Series(coinmarketcap_symbols)

# %% [markdown] heading_collapsed=true
# # Get available binance futures currency pairs

# %% [markdown] heading_collapsed=true hidden=true
# ## CCXT

# %% hidden=true
binance_ccxt = ccxt.binance({'options': {'defaultType': 'future'}, })

# %% hidden=true
markets = binance_ccxt.loadMarkets()

# %% hidden=true
markets_futures = {pair: data for pair, data in markets.items() if data["future"]}

# %% hidden=true
market_futures_currencies = [data["base"] for pair, data in markets_futures.items()]

# %% hidden=true
ccxt_market_futures_currencies = pd.Series(list(set(market_futures_currencies)))

# %% [markdown] hidden=true
# ## Binance API

# %% hidden=true
url = "https://fapi.binance.com/fapi/v1/exchangeInfo"

payload = {}
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("GET", url, headers=headers, data=payload)

# %% hidden=true
symbols = [symbol for symbol in response.json()["symbols"] if symbol["status"] == "TRADING"]

# %% hidden=true
binance_api_symbols = set([s["baseAsset"] for s in symbols])

# %% hidden=true
binnace_api_symbols = pd.Series(list(binance_api_symbols))

# %% [markdown] heading_collapsed=true
# # Find intersections

# %% hidden=true
len(coinmarketcap_symbols[coinmarketcap_symbols.isin(binnace_api_symbols)])

# %% hidden=true
len(coinmarketcap_symbols[coinmarketcap_symbols.isin(ccxt_market_futures_currencies)])

# %% hidden=true
symbols_intersection = list(coinmarketcap_symbols[coinmarketcap_symbols.isin(binnace_api_symbols)])

# %% hidden=true
top_100_symbols_intersections = symbols_intersection[:100]

# %% hidden=true
new_universe = [f"{symbol}_USDT" for symbol in top_100_symbols_intersections]

# %% hidden=true
old_universe = [
        "ETH_USDT",
        "BTC_USDT",
        "SAND_USDT",
        "STORJ_USDT",
        "GMT_USDT",
        "AVAX_USDT",
        "BNB_USDT",
        "APE_USDT",
        "MATIC_USDT",
        "DYDX_USDT",
        "DOT_USDT",
        "UNFI_USDT",
        "LINK_USDT",
        "XRP_USDT",
        "CRV_USDT",
        "RUNE_USDT",
        "BAKE_USDT",
        "NEAR_USDT",
        "FTM_USDT",
        "WAVES_USDT",
        "AXS_USDT",
        "OGN_USDT",
        "DOGE_USDT",
        "SOL_USDT",
        "CTK_USDT"
   ]

# %% hidden=true
new_mixed_universe = list(set(new_universe + old_universe))

# %% hidden=true
len(new_mixed_universe)

# %% [markdown]
# # Read and check downloaded data

# %%
signature = "bulk.airflow.downloaded_1min.parquet.ohlcv.futures.v7_5.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-02-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-06-01T00:00:00+00:00")
binance_ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %%
binance_ohlcv_data.head()

# %%
downloaded_currency_pairs = pd.Series(binance_ohlcv_data.currency_pair.unique())

# %%
downloaded_currency_pairs.shape
