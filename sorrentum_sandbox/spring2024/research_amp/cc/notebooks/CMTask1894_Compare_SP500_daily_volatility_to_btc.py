# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
# To install Yahoo API run:
# #!sudo /bin/bash -c "(source /venv/bin/activate; pip install yfinance)"
import logging

import pandas as pd
import yfinance as yf

import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Load the data

# %%
sp500_data = yf.download("^GSPC", start="2019-01-01", end="2022-05-07")
btc_data = yf.download("BTC-USD", start="2019-01-01", end="2022-05-07")
display(sp500_data.head(3))
display(btc_data.head(3))

# %% [markdown]
# # Compute and plot returns' volatility

# %%
cplpluti.configure_notebook_for_presentation()


# %%
def get_rolling_vix_for_rets(df, price_col, lookback_in_samples):
    srs = df[price_col].pct_change().rolling(lookback_in_samples).std()
    return srs


# %%
sp500_vix = get_rolling_vix_for_rets(sp500_data, "Adj Close", 21).rename(
    "SP500_Volatility"
)
btc_vix = get_rolling_vix_for_rets(btc_data, "Adj Close", 21).rename(
    "BTC_Volatility"
)
df = pd.concat([sp500_vix, btc_vix], axis=1)
df = hpandas.dropna(df, report_stats=True)
display(df.head(3))
df.plot(figsize=(20, 5))

# %%
# General mean value of volatility for a given period.
general_vix = pd.DataFrame()
general_vix.loc[
    "S&P 500", "Returns Volatility for given period"
] = sp500_vix.mean()
general_vix.loc["BTC", "Returns Volatility for given period"] = btc_vix.mean()
display(general_vix)
cplpluti.plot_barplot(
    general_vix["Returns Volatility for given period"], title="Returns Volatility"
)
