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
# This notebook contains examples of the API endpoints for Coingecko.com.
#
# The API is accessed through an API wrapper `pycoingecko` (https://github.com/man-c/pycoingecko).

# %% [markdown]
# # Imports

# %% [markdown]
# ## Installing pycoingecko

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade pip)"
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install -U pycoingecko)"

# %%
import requests
from pycoingecko import CoinGeckoAPI

# %% [markdown]
# # Examples of the free API endpoints

# %% [markdown]
# API reference: https://www.coingecko.com/en/api/documentation
#
# `pycoingecko` documentation: https://github.com/man-c/pycoingecko#api-documentation

# %%
cg = CoinGeckoAPI()

# %% [markdown]
# ## Getting a list of IDs

# %% [markdown]
# ### Coins

# %%
# Get IDs of supported coins.
all_coins = cg.get_coins_list()
print(len(all_coins))
bitcoin = [c for c in all_coins if c["name"].lower() == "bitcoin"][0]
print(bitcoin)
bitcoin_id = bitcoin["id"]

# %% [markdown]
# ### Exchanges

# %%
# Get IDs of supported exchanges.
all_exchanges = cg.get_exchanges_list()
print(len(all_exchanges))
print(all_exchanges[:3])
binance_id = cg.get_exchanges_by_id("binance")

# %% [markdown]
# ## /simple

# %%
supported_vs_currencies = cg.get_supported_vs_currencies()


# %%
usd_id = "usd"

# %%
# Get full latest price data for BTC/USD.
kwargs = {
    "include_market_cap": True,
    "include_24hr_vol": True,
    "include_24hr_change": True,
    "include_last_updated_at": True,
}
cg.get_price(bitcoin_id, usd_id, **kwargs)

# %%
# Get ETH price given a contract address.
eth_id = "ethereum"
contract_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
cg.get_token_price(eth_id, contract_address, usd_id, **kwargs)

# %% [markdown]
# ## /coins

# %%
kwargs = {
    "ids": f"{bitcoin_id},{eth_id}",
    "per_page": 10,
    "sparkline": True,
    "price_change_percentage": "1h,24h",
}
cg.get_coins_markets(usd_id, **kwargs)

# %%
# Get metadata and market data for BTC.
kwargs = {"sparkline": True}
coin_by_id = cg.get_coin_by_id(bitcoin_id, **kwargs)
coin_by_id.keys()

# %% run_control={"marked": true}
# Get ticker for BTC.
tickers = cg.get_coin_ticker_by_id(bitcoin_id)
print(tickers.keys())
tickers["tickers"][:2]

# %%
# Get metadata and historical data for BTC/USD on 01-01-2021.
kwargs = {"localization": False}
date = "01-01-2021"
cg.get_coin_history_by_id(bitcoin_id, date, **kwargs)

# %%
# Get BTC/USD market chart for a single day.
days = 1
cg.get_coin_market_chart_by_id(bitcoin_id, usd_id, days)

# %%
# Get BTC/USD market_chart since 01-22-2020 to 01-27-2020.
from_timestamp = 1579726800
to_timestamp = 1580158800
cg.get_coin_market_chart_range_by_id(
    bitcoin_id, usd_id, from_timestamp, to_timestamp
)

# %%
# Get OHLC for BTC/USD for 1 day.
days = 1
cg.get_coin_ohlc_by_id(bitcoin_id, usd_id, days)

# %% [markdown]
# ### Commentary

# %% [markdown]
# - CoinGecko provides quasi-real-time data which is updated online; the concrete way the resampling for prices works is unclear, however, we know that `volume` the cumulative. The delay between data updates is still to be determined.
# - It is possible to get many kinds of historic data, but granularity becomes larger and larger the farther in the past the requested dates are. It is unclear whether this can be fixed by purchasing a Pro account, but the probability is low.
# - For further endpoints, there will be only 1 represented for each category. The structure is almost the same throughout:
#    - endpoints for quasi-real-time data by ID (see `get_price`)
#    - endpoints for historical data (see `get_coin_history_by_id`)
#    - endpoints for lists of IDs (see `get_exchanges_list`)
#    - The data that can be received are prices, market charts and various metadata on coins and exchanges.
# - The user may consult the extensive documentation by both CoinGecko and the `pycoingecko` library.

# %% [markdown]
# ## /contract

# %% run_control={"marked": true}
# Get market chart for 1 day, ETH/USD, based on contract address.
contract_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
days = 1
market_chart = cg.get_coin_market_chart_from_contract_address_by_id(
    eth_id, "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", usd_id, days
)
print(market_chart.keys())
print(market_chart["prices"][:2])
print(market_chart["market_caps"][:2])
print(market_chart["total_volumes"][:2])

# %% [markdown]
# ## /asset_platforms

# %%
# Get list of supported Blockchain networks.
cg.get_asset_platforms()[:3]

# %% [markdown]
# ## /categories

# %%
# Get all supported categories of coins with market information.
cg.get_coins_categories()[:2]

# %% [markdown]
# ## /exchanges

# %%
# Get 100 tickers from Binance exchange.
#  Note: does not work due to 414 error below, looks like a failure of the python lib.
#  This holds for all endpoints in `exchanges` category.
kwargs = {"coin_ids": f"{bitcoin_id},{eth_id}", "page": 1}
cg.get_exchanges_tickers_by_id(binance_id, **kwargs)

# %% run_control={"marked": true}
# Trying access via `requests`.
endpoint_url = "http://api.coingecko.com/api/v3/exchanges/binance/tickers/"
response = requests.get(endpoint_url)
data = response.json()
print(data.keys())
data["tickers"][:3]

# %% [markdown]
# ## /indexes

# %% run_control={"marked": true}
# Get a list of indexes.
cg.get_indexes()[10:15]


# %% run_control={"marked": true}
# Also returns a `414` error.
# cg.get_indexes_by_market_id_and_index_id(binance_id, "ADA")

# %%
# Get price info on MOB index for FTX Derivatives.
endpoint_url = "http://api.coingecko.com/api/v3/indexes/ftx/MOB/"
response = requests.get(endpoint_url)
print(response)
data = response.json()
data

# %% [markdown]
# ## /derivatives

# %%
# Get a list of derivatives with price and other data.
cg.get_derivatives()[:3]


# %%
kwargs = {"include_tickers": "all"}

derivatives = cg.get_derivatives_exchanges_by_id("bitmex", **kwargs)
print(derivatives.keys())
derivatives["tickers"][:3]


# %% [markdown]
# ## /trending

# %%
# Get 7 most searched coins in the last 24 hours.
cg.get_search_trending()


# %% [markdown]
# ## /global

# %%
# Get Top 100 Cryptocurrency Global Eecentralized Finance(defi) data.
cg.get_global_decentralized_finance_defi()

# %% [markdown]
# ## /companies

# %% run_control={"marked": true}
# Get Bitcoin holdings by companies.
public_treasury = cg.get_companies_public_treasury_by_coin_id(bitcoin_id)
print(public_treasury.keys())
public_treasury["companies"][:3]
