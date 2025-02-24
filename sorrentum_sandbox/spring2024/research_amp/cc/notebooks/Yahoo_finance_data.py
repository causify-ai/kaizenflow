# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import logging
import sys

import numpy as np
import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import core.plotting as coplotti
import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Package `pandas-datareader`

# %%
# !sudo {sys.executable} -m pip install --upgrade pandas_datareader

# %%
import pandas_datareader as pdr

# %%
pdr.__version__

# %%
pdr.get_quote_yahoo("MSFT")

# %%
# https://saturncloud.io/blog/how-to-use-python-pandas-datareader-with-yahoo-finances-changed-url/
# Define the data source
data_source = 'yahoo'

# Define the stock symbol and the date range
ticker = 'AAPL'
start_date = '2022-01-01'
end_date = '2022-01-10'

# Define the new URL
url = 'https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events=history'.format(ticker, start_date, end_date)

# Use Python Pandas Datareader to retrieve data from the new URL
df = pdr.DataReader(
    ticker,
    data_source, 
    start_date,
    end_date,
    access_key=url,
)

# %% [markdown]
# # Package `yahoo_fin`

# %%
# https://theautomatic.net/2018/01/25/coding-yahoo_fin-package/
# !sudo {sys.executable} -m pip install --upgrade yahoo_fin

# %%
import yahoo_fin as yfin

# %%
import yahoo_fin.stock_info as si

# %%
amzn = si.get_data("amzn", start_date = "01/01/2017", end_date = "01/31/2017")

# %%
amzn

# %% [markdown]
# # Package `yfinance`

# %%
# !sudo {sys.executable} -m pip install yfinance

# %%
import yfinance as yf

# %%
aapl = yf.Ticker("aapl")

# %%
aapl_historical = aapl.history(start="2020-06-02", end="2020-06-07", interval="1d")
aapl_historical

# %% [markdown]
# # Alternatives

# %%
# https://robotwealth.com/yahoo-prices-r-easy/

# %%
