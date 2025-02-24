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
# This notebook researches how BitQuery GraphQL API interacts with Uniswap data.

# %% [markdown]
# # Imports

# %%
import os
from typing import Any, Dict, List

import pandas as pd
import requests

# %% [markdown]
# # Functions

# %%
def run_query(query: str):
    headers = {"X-API-KEY": os.environ["API_KEY"]}
    request = requests.post(
        "https://graphql.bitquery.io/", json={"query": query}, headers=headers
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(
            "Query failed and return code is {}.      {}".format(
                request.status_code, query
            )
        )


# %% run_control={"marked": false}
def json_to_df(data: List[Dict[Any, Any]]) -> pd.DataFrame:
    """
    Transform the data to Dataframe and set the time index.
    """
    df = pd.json_normalize(data, sep="_")
    df = df.set_index("timeInterval_minute")
    return df


# %% [markdown]
# # Get data

# %% [markdown]
# **1 min data example for WETH/USDT pair**

# %%
query = """
query{
  ethereum(network: ethereum) {
    dexTrades(
      options: {limit: 20000, asc: "timeInterval.minute"}
      date: {since: "2023-01-01", till: "2023-01-10"}
      baseCurrency: {is: "0xdac17f958d2ee523a2206206994597c13d831ec7"}
      quoteCurrency: {is: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"}
      exchangeName: {is: "Uniswap"}
     )
     {
      timeInterval {
      minute(count: 1)
      }
    baseCurrency {
      symbol
      address
    }
    baseAmount(in: USD)
    quoteCurrency {
      symbol
      address
    }
    quoteAmount(in: USD)
    trades: count
    quotePrice
    maximum_price: quotePrice(calculate: maximum)
    minimum_price: quotePrice(calculate: minimum)
    open_price: minimum(of: block, get: quote_price)
    close_price: maximum(of: block, get: quote_price)
    }
  }
}
"""
# Get the data
result = run_query(query)

# %%
df = json_to_df(result["data"]["ethereum"]["dexTrades"])
df

# %% [markdown]
# The query was made at 2023-01-10 10:33:00, so real-time delay is ~3-4 minutes.

# %% [markdown]
# **Get historical data Uniswap from november 2018 with no token pairs filter**

# %%
query = """
query{
  ethereum(network: ethereum) {
    dexTrades(
      options: {limit: 20000, asc: "timeInterval.minute"}
      date: {since: "2018-11-01", till: "2018-12-01"}
      exchangeName: {is: "Uniswap"}
     )
     {
      timeInterval {
      minute(count: 1)
      }
    baseCurrency {
      symbol
      address
    }
    baseAmount(in: USD)
    quoteCurrency {
      symbol
      address
    }
    quoteAmount(in: USD)
    trades: count
    quotePrice
    maximum_price: quotePrice(calculate: maximum)
    minimum_price: quotePrice(calculate: minimum)
    open_price: minimum(of: block, get: quote_price)
    close_price: maximum(of: block, get: quote_price)
    }
  }
}
"""
# Get the data
result = run_query(query)

# %%
df = json_to_df(result["data"]["ethereum"]["dexTrades"])
df

# %% [markdown]
# **Get bigger: download all swap data for today (2023-01-10)**

# %%
query = """
query{
  ethereum(network: ethereum) {
    dexTrades(
      options: {limit: 100000, asc: "timeInterval.minute"}
      date: {since: "2023-01-10"}
      exchangeName: {is: "Uniswap"}
     )
     {
      timeInterval {
      minute(count: 1)
      }
    baseCurrency {
      symbol
      address
    }
    baseAmount(in: USD)
    quoteCurrency {
      symbol
      address
    }
    quoteAmount(in: USD)
    trades: count
    quotePrice
    maximum_price: quotePrice(calculate: maximum)
    minimum_price: quotePrice(calculate: minimum)
    open_price: minimum(of: block, get: quote_price)
    close_price: maximum(of: block, get: quote_price)
    }
  }
}
"""
# Get the data
result = run_query(query)

# %%
result

# %% [markdown]
# It seems like we have a limitation for number of rows by one query, let's try to write the loop and export every 25k rows.

# %%
# Use limit and offset parameters.
query = """query{
  ethereum(network: ethereum) {
    dexTrades(
      options: {limit: 25000, offset: %d, asc: "timeInterval.minute"}
      date: {since: "2023-01-10"}
      exchangeName: {is: "Uniswap"}
     )
     {
      timeInterval {
      minute(count: 1)
      }
    baseCurrency {
      symbol
      address
    }
    baseAmount(in: USD)
    quoteCurrency {
      symbol
      address
    }
    quoteAmount(in: USD)
    trades: count
    quotePrice
    maximum_price: quotePrice(calculate: maximum)
    minimum_price: quotePrice(calculate: minimum)
    open_price: minimum(of: block, get: quote_price)
    close_price: maximum(of: block, get: quote_price)
    }
  }
}
"""

limit = 25000
offset = 0
data_dfs = []

for i in range(3):
    # Error message above says there are 61k rows, so 3 iterations by 25k would be enough.
    formatted_query = query % offset
    result = run_query(formatted_query)
    df = json_to_df(result["data"]["ethereum"]["dexTrades"])
    data_dfs.append(df)
    offset += 25000

full_data = pd.concat(data_dfs)

# %%
full_data

# %% [markdown]
# The query was made at 2023-01-10 10:42:00, so real-time delay is 5 min.

# %%
