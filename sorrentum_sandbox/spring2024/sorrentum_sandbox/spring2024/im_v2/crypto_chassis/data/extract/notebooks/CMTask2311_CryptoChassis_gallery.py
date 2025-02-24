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
# ## Description

# %% [markdown]
# This notebook contains reference of the main API endpoints and data examples for CryptoChassis.
#
# CryptoChassis API docs: https://github.com/crypto-chassis/cryptochassis-data-api-docs

# %%
import pandas as pd
import requests

import im_v2.common.universe.universe as imvcounun
import im_v2.crypto_chassis.data.extract.extractor as imvccdexex

# %% [markdown]
# ## General endpoints and Extractor methods

# %% [markdown]
# ### General endpoints

# %%
# Base url for all requests to append to.
base_url = "https://api.cryptochassis.com/v1"
response = requests.get(base_url)
response.json()

# %% [markdown]
# ### Information
# https://github.com/crypto-chassis/cryptochassis-data-api-docs#information

# %%
example_url = "https://api.cryptochassis.com/v1/information?dataType=market-depth&exchange=coinbase"
response = requests.get(example_url)
response.json()

# %% [markdown]
# ### Types of extractor

# %%
extractor_spot = imvccdexex.CryptoChassisExtractor("spot")

# %%
# Only binance futures are supported.
extractor_futures = imvccdexex.CryptoChassisExtractor("futures")

# %% [markdown]
# ### Methods for building an URL

# %% [markdown]
# #### Building an URL

# %%
base_url = extractor_spot._build_base_url("ohlc", "binance", "btc-usdt")
base_url

# %%
response = requests.get(base_url)
response.json()

# %% [markdown]
# #### Specifying a query

# %% run_control={"marked": false}
startTime = "2019-12-26T00:00:00.000Z"
endTime = "2019-12-27T00:00:00.000Z"
interval = "1m"
query_url = extractor_spot._build_query_url(
    base_url, startTime=startTime, endTime=endTime, interval=interval
)
query_url

# %%
response = requests.get(query_url)
response.json()

# %% [markdown]
# ### Available data types

# %%
url = "https://api.cryptochassis.com/v1/information"
response = requests.get(url)
response.json()

# %%
data_types = ["market-depth", "ohlc", "trade"]
for data_type in data_types:
    url = f"https://api.cryptochassis.com/v1/information?dataType={data_type}"
    print(url)
    print(requests.get(url).json())

# %% [markdown]
# ### Available instruments

# %% [markdown]
# Only for those included in universe v5.

# %%
universe = imvcounun.get_vendor_universe("crypto_chassis", "download")
supported_exchanges = list(universe.keys())

# %%
supported_exchanges

# %% [markdown]
# ## OHLCV

# %% [markdown]
# ### Spot

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/ohlc/ftx/btc-usdt?startTime=1657778400&endTime=1657789200"
response = requests.get(url)
print(url)
print(response.json())

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-06-14T10:00:00", tz="UTC")
end_timestamp = pd.Timestamp("2022-06-14T12:59:00", tz="UTC")
extractor_spot._download_ohlcv(
    "ftx",
    "btc-usdt",
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %% [markdown]
# ### Futures

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/ohlc/binance-usds-futures/btcusdt?startTime=1654718400&endTime=1654740000"
response = requests.get(url)
print(url)
# The raw data is in the value of the `urls.url` field zipped into the csv.gz archive,
# which contains dataframe which is unpacked by the extractor.
print(response.json())

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-06-09T00:00:00", tz="UTC")
end_timestamp = pd.Timestamp("2022-06-10T00:00:00", tz="UTC")
extractor_futures._download_ohlcv(
    "binance",
    "btc/usdt",
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %% [markdown]
# ## Bid/ask

# %% [markdown]
# ### Spot

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/market-depth/ftx/btc-usdt?startTime=1655204609&endTime=1655206609"
response = requests.get(url)
# The raw data is in the value of the `urls.url` field zipped into the csv.gz archive,
# which contains dataframe which is unpacked by the extractor.
response.json()

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-06-14T10:00:00", tz="UTC")
end_timestamp = pd.Timestamp("2022-06-14T12:59:00", tz="UTC")
extractor_spot._download_bid_ask(
    "ftx",
    "btc-usdt",
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %% [markdown]
# ### Futures

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/market-depth/binance-usds-futures/btcusdt?startTime=1654718400&endTime=1654740000"
response = requests.get(url)
print(url)
# The raw data is in the value of the `urls.url` field zipped into the csv.gz archive,
# which contains dataframe which is unpacked by the extractor.
print(response.json())

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-06-09T00:00:00", tz="UTC")
end_timestamp = pd.Timestamp("2022-06-09T07:00:00", tz="UTC")
extractor_futures._download_bid_ask(
    "binance",
    "btc/usdt",
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %% [markdown]
# ## Trade

# %% [markdown]
# ### Spot

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/trade/ftx/btc-usdt?startTime=1655204609"
response = requests.get(url)
# The raw data is in the value of the `urls.url` field zipped into the csv.gz archive,
# which contains dataframe which is unpacked by the extractor.
response.json()

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-07-10T10:00:00", tz="UTC")
extractor_spot._download_trades(
    "ftx", "btc-usdt", start_timestamp=start_timestamp
)

# %% [markdown]
# ### Futures

# %% [markdown]
# #### Raw data example (using `requests`)

# %%
url = f"https://api.cryptochassis.com/v1/trade/binance-usds-futures/btcusdt?startTime=1654718400"
response = requests.get(url)
print(url)
# The raw data is in the value of the `urls.url` field zipped into the csv.gz archive,
# which contains dataframe which is unpacked by the extractor.
print(response.json())

# %% [markdown]
# #### DataFrame example using Extractor class

# %%
start_timestamp = pd.Timestamp("2022-07-15T14:00:00", tz="UTC")
extractor_futures._download_trades(
    "binance", "btc/usdt", start_timestamp=start_timestamp
)

# %%
