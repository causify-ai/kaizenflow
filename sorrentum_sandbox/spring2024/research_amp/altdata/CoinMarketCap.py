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
# Review of the Coin Market Cap API endpoints availiable on `basic` plan:
#
# * v1/cryptocurrency/categories
# * v1/cryptocurrency/category
# * v1/cryptocurrency/map
# * v2/cryptocurrency/info
# * v1/cryptocurrency/listings/latest
# * v2/cryptocurrency/quotes/latest
# * v1/fiat/map
# * v1/exchange/assets
# * v1/global-metrics/quotes/latest

# %% [markdown]
# # Imports

# %%
import json
import os
from typing import Dict

from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects

# %% [markdown]
# # Set-up

# %%
key = "6714e467-49e5-49bc-9484-30a6331d6fb3"
api_url = "https://sandbox-api.coinmarketcap.com"

# %%
headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": key,
}

session = Session()
session.headers.update(headers)


# %%
def get_data(session: Session, url: str, params: Dict[str, str]):
    """
    Make query to API endpoint.
    """
    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        return data
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        return e


# %% [markdown]
# # Cryptocurrency API access

# %% [markdown]
# **/categories**

# %% [markdown]
# Returns information about all coin categories available on CoinMarketCap. Includes a paginated list of cryptocurrency quotes and metadata from each category.

# %%
url = os.path.join(api_url, "v1/cryptocurrency/categories")
parameters = {"start": "1", "limit": "5000", "symbol": "ETH,BTC"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# **/category**

# %% [markdown]
# Returns information about a single coin category available on CoinMarketCap. Includes a paginated list of the cryptocurrency quotes and metadata for the category.

# %%
url = os.path.join(api_url, "v1/cryptocurrency/category")
parameters = {"id": "qisclrimb", "start": "1", "limit": "100"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# **/map**

# %% [markdown]
# Returns a mapping of all cryptocurrencies to unique CoinMarketCap ids. By default this endpoint returns cryptocurrencies that have actively tracked markets on supported exchanges.

# %%
url = os.path.join(api_url, "v1/cryptocurrency/map")
parameters = {"start": "1", "limit": "5000", "sort": "id", "symbol": "ETH,BTC"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# It looks like `name`, `symbol`, `slug` and other string typed values are encrypted, I'll figure out what it is.

# %% [markdown]
# **/info**

# %% [markdown]
# Returns all static metadata available for one or more cryptocurrencies. This information includes details like logo, description, official website URL, social links, and links to a cryptocurrency's technical documentation.

# %%
url = os.path.join(api_url, "v2/cryptocurrency/info")
parameters = {"symbol": "ETH,BTC"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# **/listings/latest**

# %% [markdown]
# Returns a paginated list of all active cryptocurrencies with latest market data. The default "market_cap" sort returns cryptocurrency in order of CoinMarketCap's market cap rank (as outlined in our methodology) but it may be configured  to order by another market ranking field. "convert" option is used to return market values in multiple fiat and cryptocurrency conversions in the same call.

# %%
url = os.path.join(api_url, "v1/cryptocurrency/listings/latest")
parameters = {
    "start": "1",
    "limit": "5000",
    "convert": "USD",
    "market_cap_min": 10000000000000,
    "market_cap_max": 9000000000000000,
}

data = get_data(session, url, parameters)
data


# %% [markdown]
# **/quotes/latest**

# %% [markdown]
# Returns the latest market quote for 1 or more cryptocurrencies. "convert" is used option to return market values in multiple fiat and cryptocurrency conversions in the same call.

# %%
url = os.path.join(api_url, "v2/cryptocurrency/quotes/latest")
parameters = {"convert": "USD", "symbol": "ETH,BTC"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# # Fiat API access

# %% [markdown]
# Returns a mapping of all supported fiat currencies to unique CoinMarketCap ids.

# %%
url = os.path.join(api_url, "v1/fiat/map")
parameters = {"start": "1", "limit": "5000"}

data = get_data(session, url, parameters)
data

# %% [markdown]
# # Exchange API access

# %% [markdown]
# Returns the exchange assets in the form of token holdings. This information includes details like wallet address, cryptocurrency, blockchain platform, balance, and etc.

# %%
url = os.path.join(api_url, "v1/exchange/assets")
parameters = {"id": "270"}  # CoinMarketCap exchange ID for binance

data = get_data(session, url, parameters)
data

# %% [markdown]
# # Global Market API access

# %% [markdown]
# Returns the latest global cryptocurrency market metrics. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

# %%
url = os.path.join(api_url, "v1/global-metrics/quotes/latest")
parameters = {"convert": "USD"}

data = get_data(session, url, parameters)
data

# %%
