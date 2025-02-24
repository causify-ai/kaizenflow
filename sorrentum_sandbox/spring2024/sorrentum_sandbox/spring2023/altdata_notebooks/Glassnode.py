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
# This notebook examines free endpoints in Glassnode Studio.
# - Website: https://studio.glassnode.com/
# - API docs: https://docs.glassnode.com/basic-api/endpoints

# %% [markdown]
# # Imports

# %%
import requests
import os
import json

# %% [markdown]
# How to get the API keys:
#
# https://docs.glassnode.com/basic-api/api-key

# %%
api_key = ""

# %% [markdown]
# # Endpoints
# - Due to abundance of endpoints, only several will be provided for each category.
# - API endpoints available for the free tier can be found under Tier 1 Metrics at this address: https://studio.glassnode.com/catalog
# - For the free tier, the only time resolution available for bar data is 24 hours

# %% [markdown]
# ## Addresses
# https://docs.glassnode.com/basic-api/endpoints/addresses

# %% run_control={"marked": true}
# Active addresses.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/addresses/active_count",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])
display(res.json()[:10])

# %%
# Sending addresses.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/addresses/sending_count",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Blockchain
# https://docs.glassnode.com/basic-api/endpoints/blockchain

# %%
# Blocks mined.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/blockchain/block_count",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Block size (Mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/blockchain/block_size_mean",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Block interval (Mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/blockchain/block_interval_mean",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# UTXO Value Created (Total).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/blockchain/utxo_created_value_sum",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Distribution
# https://docs.glassnode.com/basic-api/endpoints/distribution

# %%
# Proof of reserve (current).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/distribution/proof_of_reserves_all_latest",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json())

# %%
# Proof of reserve.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/distribution/proof_of_reserves",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## ETH 2.0
# https://docs.glassnode.com/basic-api/endpoints/eth2

# %%
# ETH 2.0 total number of deposits.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/eth2/staking_total_deposits_count",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# ETH 2.0 total value staked.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/eth2/staking_total_volume_sum",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Fees
# https://docs.glassnode.com/basic-api/endpoints/fees

# %%
# Fees (total).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/fees/volume_sum",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Gas price (mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/fees/gas_price_mean",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Gas used (mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/fees/gas_used_mean",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Indicators
# https://docs.glassnode.com/basic-api/endpoints/indicators

# %%
# SOPR.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/indicators/sopr",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Difficulty ribbon.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/indicators/difficulty_ribbon",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Institutions
# https://docs.glassnode.com/basic-api/endpoints/institutions

# %%
# Purpose Bitcoin ETF holdings.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/institutions/purpose_etf_holdings_sum",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Market
# https://docs.glassnode.com/basic-api/endpoints/market

# %%
# Market cap.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/market/marketcap_usd",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Price OHLC.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/market/price_usd_ohlc",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Mining
# https://docs.glassnode.com/basic-api/endpoints/mining

# %%
# Difficulty.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/mining/difficulty_latest",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Hash Rate.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/mining/hash_rate_mean",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Protocols
# https://docs.glassnode.com/basic-api/endpoints/protocols

# %%
# Uniswap liqudity.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/protocols/uniswap_liquidity_latest",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Supply
# https://docs.glassnode.com/basic-api/endpoints/supply

# %%
# Circulating supply.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/supply/current",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %% [markdown]
# ## Transactions
# https://docs.glassnode.com/basic-api/endpoints/transactions

# %%
# Transaction counts.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/transactions/count",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Transfer counts.
res = requests.get(
    "https://api.glassnode.com/v1/metrics/transactions/transfers_count",
    params={"a": "ETH", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Transaction size (mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/transactions/size_mean",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])

# %%
# Transfer size (mean).
res = requests.get(
    "https://api.glassnode.com/v1/metrics/transactions/transfers_volume_mean",
    params={"a": "BTC", "api_key": api_key, "timestamp_format": "humanized"},
)
display(res.json()[-10:])
