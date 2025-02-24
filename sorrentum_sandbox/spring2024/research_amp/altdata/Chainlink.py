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
# This notebook demonstrates the access to Chainlink price feeds.
#
# The notebook follows the example from the documentation:
# - https://docs.chain.link/data-feeds/price-feeds
# - API reference: https://docs.chain.link/data-feeds/price-feeds/api-reference

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade pip)"
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install web3)"

# %% [markdown]
# # Imports

# %%
import numpy as np
from web3 import Web3

# %% [markdown]
# # Access to price feeds

# %% [markdown]
# ## Latest data

# %% [markdown]
# ## Example from the docs

# %% [markdown]
# Copy of the example from the documentation: https://docs.chain.link/data-feeds/price-feeds/#python

# %%
# Change this to use your own RPC URL
web3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth_goerli"))
# AggregatorV3Interface ABI
abi = '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
# Price Feed address
addr = "0xA39434A63A52E749F02807ae27335515BA4b07F7"

# Set up contract instance
contract = web3.eth.contract(address=addr, abi=abi)
# Make call to latestRoundData()
latestData = contract.functions.latestRoundData().call()
print(latestData)

# %% [markdown]
# From the API reference, the fields are as follows:
#
# - roundId: The round ID.
# - answer: The price.
# - startedAt: Timestamp of when the round started.
# - updatedAt: Timestamp of when the round was updated.
# - answeredInRound: The round ID of the round in which the answer was computed.

# %%
decimals = contract.functions.decimals().call()
print(decimals)

# %%
description = contract.functions.description().call()
print(description)

# %%
round_data = contract.functions.getRoundData(18446744073709558875).call()
print(round_data)

# %% [markdown]
# ## Historical data

# %% [markdown]
# ### Example from the docs

# %%
#  Valid roundId must be known. They are NOT incremental.
# invalidRoundId = 18446744073709562300
validRoundId = 18446744073709554177

historicalData = contract.functions.getRoundData(validRoundId).call()
print(historicalData)

# %% [markdown]
# Historical data is being given on a by-round basis.
#
# In order to get data on all valid Round IDs:
#
# -

# %% [markdown]
# ## Getting the same data from ETH mainnet

# %% [markdown]
# - Accessing the same data from mainnet for ADA/USD currency pair
# - List of mainnet price feeds: https://docs.chain.link/data-feeds/price-feeds/addresses#Ethereum%20Mainnet
# - RPC of ethereum mainnet: https://rpc.ankr.com/eth

# %%
web3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth"))
addr = "0xAE48c91dF1fE419994FFDa27da09D5aC69c30f55"  # Corresponds to https://app.ens.domains/name/ada-usd.data.eth

# %%
# Set up contract instance
contract = web3.eth.contract(address=addr, abi=abi)
# Make call to latestRoundData().
# Output:
# roundId: The round ID.
# answer: The price.
# startedAt: Timestamp of when the round started.
# updatedAt: Timestamp of when the round was updated.
# answeredInRound: The round ID of the round in which the answer was computed.
latestData = contract.functions.latestRoundData().call()
print(latestData)

# %% [markdown]
# This corresponds with the price provided here: https://data.chain.link/ethereum/mainnet/crypto-usd/ada-usd.
#
# With price at $0.33110628, it seems like the response in that field is the number of lowest decimals, i.e. if the price goes to the 8th decimal, everything with less than 8 digits represents value below 1.
#
# The number of decimals can be found at the `decimals` API endpoint.

# %%
decimals = contract.functions.decimals().call()
print(f"decimals={decimals}")
description = contract.functions.description().call()
print(f"descrition={description}")
round_data = contract.functions.getRoundData(55340232221128666997).call()
print(round_data)

# %% [markdown]
# Accessing other round IDs incrementally by reducing the latest round ID by one:

# %%
round_data = contract.functions.getRoundData(55340232221128666996).call()
print(round_data)

# %%
round_data = contract.functions.getRoundData(55340232221128666995).call()
print(round_data)

# %% [markdown]
# The round ID is not originally incremental, but this link in the API describes how to get to the end of the round history:
#
# https://docs.chain.link/data-feeds/price-feeds/historical-data
#
# The proxy that is being used by the `web3` lib takes care of this problem and the roundID is provided with an incremental increase of 1.
#

# %% [markdown]
# ## Summary

# %% [markdown]
# - Chainlink provides a comprehensive data feed for Crypto prices on multiple mainnet networks
# - All historical data can be accessed by iterating over incremental roundIDs
# - The timestamps at the data are not incremental since the network state change is triggered rather than updated regularly

# %%
