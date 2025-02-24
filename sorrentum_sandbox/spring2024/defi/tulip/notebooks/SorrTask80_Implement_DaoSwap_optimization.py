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
# The notebook demonstrates how open-source solvers solve the DaoSwap problem.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

import defi.dao_cross.optimize as ddacropt
import defi.dao_cross.order as ddacrord
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
try:
    import pulp
except ImportError:
    # !sudo /bin/bash -c "(source /venv/bin/activate; pip install pulp)"
    import pulp

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Test orders

# %%
def _generate_test_orders(
    actions: List[str],
    quantities: List[float],
    base_tokens: List[str],
    limit_prices: List[float],
    quote_tokens: List[str],
) -> List[ddacrord.Order]:
    """
    Create N `Order` instances using the inputs.

    See `Order` for params description.
    """
    # Use dummy values as the params are not relevant for the
    # optimization problem.
    timestamp = np.nan
    deposit_address = 1
    wallet_address = 1
    orders: List[ddacrord.Order] = []
    # TODO(Grisha): check that all lists are of the same length.
    for i in range(len(base_tokens)):
        order_i = ddacrord.Order(
            timestamp,
            actions[i],
            quantities[i],
            base_tokens[i],
            limit_prices[i],
            quote_tokens[i],
            deposit_address,
            wallet_address,
        )
        orders.append(order_i)
    return orders


# %%
_actions = ["buy", "buy", "sell", "sell", "buy", "buy", "sell", "sell"]
_quantities = [4, 2, 5, 3, 6, 2, 9, 1]
_base_tokens = ["BTC", "BTC", "BTC", "BTC", "ETH", "ETH", "ETH", "ETH"]
_quote_tokens = ["ETH", "ETH", "ETH", "ETH", "BTC", "BTC", "BTC", "BTC"]
_limit_prices = [3, 3.5, 1.5, 1.9, 0.6, 2, 0.1, 0.25]


def test1() -> None:
    """
    The limit price condition is True for all orders.
    """
    # Get inputs.
    prices = {"BTC": 3, "ETH": 6}
    limit_prices = [3, 3.5, 1.5, 1.9, 0.6, 2, 0.1, 0.25]
    test_orders = _generate_test_orders(
        _actions,
        _quantities,
        _base_tokens,
        _limit_prices,
        _quote_tokens,
    )
    return test_orders


# %%
prices = {"BTC": 3, "ETH": 6}

# %%
orders = test1()

# %%
ddacrord.convert_orders_to_dataframe(orders)

# %% [markdown]
# ## Run DaoCross

# %%
daocross_results = ddacropt.run_daocross_solver(orders, prices)
display(daocross_results)

# %% [markdown]
# ## Run DaoSwap

# %%
daoswap_results = ddacropt.run_daoswap_solver(orders)
display(daoswap_results)

# %%
