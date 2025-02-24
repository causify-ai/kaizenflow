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
# This notebook contains examples of the API endpoints for finance.yahoo.com.
#
# The API is accessed through an API wrapper `yfinance` (https://github.com/ranaroussi/yfinance).

# %% [markdown]
# # Imports

# %% [markdown]
# ## Installing yfinance

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade pip)"
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install -U yfinance --upgrade --no-cache-dir)"

# %%
import requests
import yfinance as yf

# %% [markdown]
# # Examples of the free API endpoints

# %% [markdown]
# Yahoo finance API was shutdown in 2017. But there is an available API which is returning historical stock data. From https://news.ycombinator.com/item?id=15617278
#
#
# There is a lib `yfinance` that has access to this API and its code can be used to extract some crypto data. Documentation: https://github.com/ranaroussi/yfinance

# %% [markdown]
# ## Load data

# %% [markdown]
# `yfinance` is a very limited lib, I could not find a way to get available tickers universe.
# There are many tickers that data is being retrieved for.

# %%
universe = [
    "ETH-USD",
    "BTC-USD",
    "SAND-USD",
    "STORJ-USD",
    "AVAX-USD",
    "BNB-USD",
    "APE-USD",
    "MATIC-USD",
    "DOT-USD",
    "UNFI-USD",
    "LINK-USD",
    "XRP-USD",
    "RUNE-USD",
    "NEAR-USD",
    "FTM-USD",
    "AXS-USD",
    "OGN-USD",
    "DOGE-USD",
    "SOL-USD",
]

# %% [markdown]
# `.download()` loads data for the specified tickers.
# One of the prerequisites is that `period` and `interval` should be in the following ranges, otherwise output is empty:
# - 1m data is available only for the last 7 days max
# - 2m/5m/15m/30m data is available only for the last 60 days max
# - 1h data is available for 730 days max
# - 1d data is available for the whole period

# %%
period = "7d"
interval = "1m"
#
df_all = yf.download(
    tickers=universe,
    period=period,
    interval=interval,
    ignore_tz=True,
    prepost=False,
)
df_all.tail()

# %% [markdown]
# The latest data point is 3 min away from the actual run time so data is being updated in real time.

# %%
df_all.isna().sum()["Adj Close"]

# %% [markdown]
# Not all the retrieved tickers have data for 1 minute bar interval, but we have at least 13 full symbols that we can track from Yahoo in real-time.

# %% [markdown]
# ## Other lib methods

# %% [markdown]
# Apart from it `yfinance` can be used to extract ticker metadata and its stats on the ongoing trade parameters in real time.

# %%
ticker = yf.Ticker("BTC-USD")

# %%
ticker.info

# %%
ticker.fast_info

# %%
ticker.fast_info.last_volume

# %%
hist = ticker.history(period="7d")
display(hist)

# %%
ticker.history_metadata

# %%
