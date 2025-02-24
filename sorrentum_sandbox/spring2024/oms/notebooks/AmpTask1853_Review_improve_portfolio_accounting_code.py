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

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
# hdbg.init_logger(verbosity=logging.INFO)
import market_data as mdata
import oms.portfolio.portfolio_example as opopoexa

hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

# _LOG.info("%s", env.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Section 1

# %%
event_loop = None
market_data = mdata.get_ReplayedTimeMarketData_example3(event_loop)

# %%
initial_timestamp = pd.Timestamp("2000-01-01 09:35:00-05:00")
portfolio = opopoexa.get_simulated_portfolio_example1(
    market_data, initial_timestamp
)

# %%
str(portfolio)

# %%
portfolio.holdings

# %%
portfolio.get_holdings(initial_timestamp, asset_id=-1, exclude_cash=True)

# %%
portfolio.get_holdings_as_scalar(pd.Timestamp("2000-01-01 09:35:00-05:00"), 0)

# %%
srs = portfolio.get_characteristics(initial_timestamp)
display(srs)

# %%
portfolio.orders

# %%
portfolio.get_net_wealth(initial_timestamp)

# %%
