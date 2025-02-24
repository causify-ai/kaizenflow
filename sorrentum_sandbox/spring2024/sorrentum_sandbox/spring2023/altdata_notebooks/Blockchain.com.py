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
# This notebook contains the examples of the outputs for relevant endpoints of the [blockchain.com](blockchain.com) API.

# %%
import logging

import requests

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Blockchain Data API (REST)

# %% [markdown]
# https://www.blockchain.com/explorer/api/blockchain_api

# %% [markdown]
# ## Unconfirmed Transactions

# %% [markdown]
# A list of all current unconfirmed transactions.

# %%
api_url = "https://blockchain.info/unconfirmed-transactions?format=json"

# %%
response = requests.get(api_url)
data = response.json()
display(data.keys())

# %%
data = data["txs"]
display(len(data))
display(data[:3])

# %%
display(data[0])

# %% [markdown]
# ### Comment

# %% [markdown]
# - It seems like only the latest 100 transactions is returned through REST
# - The time of the transaction is not recorded
# - `value` can be stored in satoshi or this is not related to monetary value.
# - There is no API endpoint for ETH, but it can be scraped from their website:
# https://www.blockchain.com/eth/unconfirmed-transactions
# - In general, it seems like this data is meant to be received from websocket API

# %% [markdown]
# ## Chart data

# %% [markdown]
# Data from charts found in https://www.blockchain.com/explorer/charts
#
# An example is given for Estimated Transaction Value on BTC blockchain:
# https://www.blockchain.com/explorer/charts/estimated-transaction-volume-usd

# %%
api_url = (
    "https://blockchain.info/charts/$estimated-transaction-volume-usd?format=json"
)
response = requests.get(api_url)
response.text[:300]

# %%
api_url = "https://blockchain.info/charts/$market-price?format=json"
response = requests.get(api_url)
response.text[:300]

# %% [markdown]
# ### Comment

# %% [markdown]
# - The API instructions are not clear - the requests return only the HTML page of the chart in question, although the page itself has a JSON download. Probably a different API should be used.

# %% [markdown]
# # Query API

# %% [markdown]
# https://www.blockchain.com/explorer/api/q

# %% [markdown]
# Not described here due to limitations:
# - Too few endpoints of which all are plaintext;
# - A limit to 1 request per 10 seconds

# %% [markdown]
# # Blockchain.com Explorer API (Websocket)

# %% [markdown]
# https://www.blockchain.com/explorer/api/api_websocket

# %% [markdown]
# Not described here due to issues with running websocket/asyncio in jupyter notebook environment.
#
# TODO(Danya): Should we update the `websockets` library?

# %%
# api_endpoint = "wss://ws.blockchain.info/inv"
# # ws = websocket.WebSocket()
# # ws.connect(api_endpoint)
# with contextlib.closing(websocket.create_connection("wss://ws.blockchain.info/inv")) as conn:
#     print(conn.recv_data())

# %% [markdown]
# # Exchange Rates API

# %% [markdown]
# https://www.blockchain.com/explorer/api/exchange_rates_api

# %%
api_url = "https://blockchain.info/ticker"
response = requests.get(api_url)
data = response.json()

# %%
display(len(data.keys()))

# %%
display(data)

# %%
api_url = "https://blockchain.info/tobtc?currency=RUB&value=10000"
response = requests.get(api_url)
data = response.json()
display(data)

# %% [markdown]
# ### Comment

# %% [markdown]
# - A simple mechanism for exchanging BTC to fiat
# - Data goes back only 15m
# - In general, very limited

# %% [markdown]
# # Blockchain Charts & Statistics API

# %% [markdown]
# https://www.blockchain.com/explorer/api/charts_api

# %% [markdown]
# ## Charts data

# %% [markdown]
# Data on charts found at https://www.blockchain.com/explorer/charts
#
# The example used is [Estimated Transaction Value (USD)](https://www.blockchain.com/explorer/charts/estimated-transaction-volume-usd)

# %% [markdown]
# ### Data with default parameters

# %%
api_url = "https://api.blockchain.info/charts/estimated-transaction-volume-usd"
response = requests.get(api_url)
data = response.json()
display(len(data.keys()))
display(data.keys())

# %%
data

# %% [markdown]
# ### Providing a specific timeframe (to catch all available historical data)

# %%
api_url = "https://api.blockchain.info/charts/estimated-transaction-volume-usd?start=2011-01-01?sampled=False"
response = requests.get(api_url)
data = response.json()
display(len(data.keys()))
display(data.keys())

# %%
len(data["values"])

# %% [markdown]
# ### Comment

# %% [markdown]
# - Data on this chart goes at least as far back as 2010
# - The `timespan` parameter does not work (at least with this particular chart), but by default the API returns daily data for the entire year
# - The data is only for BTC, but contains loads of historical data

# %% [markdown]
# ## Stats data

# %% [markdown]
# Current statistics for BTC. No parameters.

# %%
api_url = "https://api.blockchain.info/stats"
response = requests.get(api_url)
data = response.json()
display(len(data.keys()))
display(data.keys())

# %%
display(data)

# %% [markdown]
# ### Comment

# %% [markdown]
# - Data is rounded up to minutes, so it is probably updated every minute
# - No endpoint for historical data provided
