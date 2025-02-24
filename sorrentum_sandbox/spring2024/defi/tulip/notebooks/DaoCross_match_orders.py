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

import defi.dao_cross.dao_cross as ddcrdacr
import defi.dao_cross.order as ddacrord
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.DEBUG)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %%
buy_order1 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "buy",
    5,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=1,
    wallet_address=1,
)
buy_order2 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "buy",
    2.5,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=2,
    wallet_address=2,
)
buy_order3 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "buy",
    4,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=3,
    wallet_address=3,
)

# %%
buy_orders = [buy_order1, buy_order2, buy_order3]
display(buy_orders)


# %%
sell_order1 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "sell",
    2,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=-1,
    wallet_address=-1,
)
sell_order2 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "sell",
    5,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=-2,
    wallet_address=-2,
)
sell_order3 = ddacrord.Order(
    "BaseToken",
    "ETH",
    "sell",
    3,
    100000000000000 / 10**18,
    timestamp=None,
    deposit_address=-3,
    wallet_address=-3,
)
sell_orders = [sell_order1, sell_order2, sell_order3]
display(sell_orders)

# %%
ddacrord.get_random_order()

# %% [markdown]
# # Order matching

# %% [markdown]
# ## Example 1

# %%
clearing_price = 100000000000000 / 10**18
transfers_df = ddcrdacr.match_orders(buy_orders + sell_orders, clearing_price)

# %%
transfers_df

# %%
eth_transfers = transfers_df[transfers_df["token"] == "ETH"]
display(eth_transfers)

# %%
# Transferred ETH (in ETH).
eth_transfers["amount"].sum()

# %%
btc_transfers = transfers_df[transfers_df["token"] == "BTC"]
display(btc_transfers)

# %%
# Transferred BTC (in BTC).
btc_transfers["amount"].sum()

# %%
# BTC transferred divided by the ETH/BTC price (quoted in BTC per ETH)
# returns amount of transferred ETH.
btc_transfers["amount"].sum() / clearing_price

# %% [markdown]
# ## Example 2

# %%
orders = []
for idx in range(0, 10):
    order = ddacrord.get_random_order(idx)
    orders.append(order)

# %%
orders

# %%
transfers_df_2 = ddcrdacr.match_orders(orders, 0.1)
display(transfers_df_2)

# %%
