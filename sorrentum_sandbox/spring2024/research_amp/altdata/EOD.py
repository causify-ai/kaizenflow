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
# This notebook researches `eodhistoricaldata.com` news API.

# %% [markdown]
# # Imports

# %%
import os

import requests

# %% [markdown] run_control={"marked": false}
# Free API key is valid for 20 API requests per day.

# %%
api_token = os.environ["EOD"]

# %% [markdown]
# List of allowed token pairs can be found here https://eodhistoricaldata.com/financial-apis/list-supported-crypto-currencies/

# %% [markdown]
# # Query the API

# %%
eod_base = (
    "https://eodhistoricaldata.com/api/news?api_token=%s&s=%s&offset=%s&limit=%s"
)

# %% [markdown]
# **BTC**

# %% run_control={"marked": true}
token = "BTC"
offset = "0"
limit = "10"

query = eod_base % (api_token, token, offset, limit)
response = requests.get(query).json()

# %%
response[0]

# %% [markdown]
# We can see here that `sentiment` field stores the sentiment evaluation of a text, with looks very useful for crypto analysis.

# %% [markdown]
# **ETH-USD**

# %%
token = "ETH-USD.CC"
offset = "0"
limit = "10"

query = eod_base % (api_token, token, offset, limit)
response = requests.get(query).json()

# %% [markdown]
# Let's evaluate the quality of sentiment analysis.

# %% [markdown]
# **1**

# %%
response[0]

# %% [markdown]
# In my opinion the text `Top Ethereum (ETH) Gas Spenders Are Scammers. According to the latest findings by blockchain security firm PeckShield, the top two gas spenders on the Ethereum network are zero transfer scammers.` has more negative sentiment than positive.

# %% [markdown]
# **2**

# %%
response[1]

# %% [markdown]
# This sentiment percentage seems fair to me.

# %% [markdown]
# **Let's look for a negative sentiment in out response list**

# %%
for resp in response:
    neg = resp["sentiment"]["neg"]
    if neg > 0.2:
        print(resp)

# %% [markdown]
# It seems like negative sentiment is less common than positive sentiment.

# %% [markdown]
# **Extract the symbols related to `ETH-USD` symbol.**

# %%
symbols = []
for r in response:
    symbols.extend(r["symbols"])
print(set(symbols))

# %% [markdown]
# # Other relevant EOD API URLs

# %% [markdown]
# **[Fundamental Data for Cryptocurrencies](https://eodhistoricaldata.com/financial-apis/fundamental-data-for-cryptocurrencies/)**, URL example: https://eodhistoricaldata.com/api/fundamentals/BTC-USD.CC?api_token={token}
# - Market Capitalization
# - Market Capitalization Diluted
# - Circulating Supply
# - Total Supply
# - Max Supply
# - Market Capitalization Dominance
# - Technical Documentation LInk
# - Explorer
# - Source Code
# - Message Board
# - Low All Time
# - High All Time
#

# %% [markdown]
# **[End-Of-Day Historical Stock Market Data API](https://eodhistoricaldata.com/financial-apis/api-for-historical-data-and-volumes/)**,
# URL example: https://eodhistoricaldata.com/api/eod/BTC.CC?api_token={token}
#
# - Date
# - Open
# - High
# - Close
# - Adjusted_close
# - Volume

# %% [markdown]
# **[Intraday Historical Data API](https://eodhistoricaldata.com/financial-apis/intraday-historical-data-api/)**
#
# Cryptocurrencies (CC) have 1-minute intervals of trading data from 2009, more than 12 years of data. 5-minute and 1-hour intervals are available from October 2020.
# URL example: https://eodhistoricaldata.com/api/intraday/BTC.CC?api_token={}

# %% [markdown]
# **[Live (Delayed) Stock Prices API](https://eodhistoricaldata.com/financial-apis/live-realtime-stocks-api/)**
#
# With this API endpoint, you are able to get delayed (15-20 minutes) information about almost all stocks on the market.
# URL example: https://eodhistoricaldata.com/api/real-time/BTC.CC?fmt=json&api_token={token}
#

# %% [markdown]
# **[Real-Time Data API (WebSockets)](https://eodhistoricaldata.com/financial-apis/new-real-time-data-api-websockets/)**
# Real-time data with a delay of less than 50ms.
#
# Websocket URL: wss://ws.eodhistoricaldata.com/ws/crypto?api_token={token}

# %% [markdown]
# **[Sentiment Data Financial API for News and Tweets](https://eodhistoricaldata.com/financial-apis/sentimental-data-financial-api/)**
#
# The Financial News aggregated sentiment data collected from the financial news for stocks, ETFs, Forex, and cryptocurrencies data. The data is aggregated by day.
# URL example: https://eodhistoricaldata.com/api/sentiments?s=btc-usd.cc,aapl&from=2022-01-01&to=2022-04-22&api_token={token}
#
#

# %%
