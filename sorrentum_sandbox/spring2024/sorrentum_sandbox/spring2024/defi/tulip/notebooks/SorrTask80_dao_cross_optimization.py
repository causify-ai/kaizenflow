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
# The notebook demonstrates how open-source solvers solve the DaoCross problem.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
from typing import Tuple

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
# # Functions

# %%
# TODO(Grisha): consider extending for n orders.
# TODO(Grisha): move to a lib, add unit tests.
def optimize_for_volume(
    order_1: ddacrord.Order,
    order_2: ddacrord.Order,
    exchange_rate: float,
) -> None:
    """
    Find the maximum transacted volume given the orders and the constraints.

    :param order_1: input buy order
    :param order_2: input sell order
    :param exchange_rate: price of base token / price of quote token
    :return: solver's output in a human readable format
    """
    # Assume the fixed directions.
    hdbg.dassert_eq(order_1.action, "buy")
    hdbg.dassert_eq(order_2.action, "sell")
    #
    hdbg.dassert_lt(0, exchange_rate)
    # Initialize the model.
    problem = pulp.LpProblem("The DaoCross problem", pulp.LpMaximize)
    # Specify the vars. By setting the lower bound to zero it is safe
    # to omit the >= 0 constraint on the executed quantity.
    q_base_asterisk_1 = pulp.LpVariable("q_base_asterisk_1", lowBound=0)
    q_base_asterisk_2 = pulp.LpVariable("q_base_asterisk_2", lowBound=0)
    # Objective function.
    # TODO(Grisha): since the base token is the same, i.e. BTC it's
    # ok to use quantity, however the objective function should be
    # modified to account for different base tokens.
    problem += q_base_asterisk_1 + q_base_asterisk_2
    # Constraints.
    # Random number that is big enough to use the
    # "Big M" method.
    M = 1e6
    # TODO(Grisha): this should be a function of action.
    limit_price_cond_1 = int(exchange_rate <= order_1.limit_price)
    _LOG.info("limit_price_cond_1 is %s", limit_price_cond_1)
    limit_price_cond_2 = int(exchange_rate >= order_2.limit_price)
    _LOG.info("limit_price_cond_2 is %s", limit_price_cond_2)
    # Executed quantity is not greater than the requested quantity
    # given that the limit price condition is satisfied.
    problem += q_base_asterisk_1 <= order_1.quantity + M * (
        1 - limit_price_cond_1
    )
    problem += q_base_asterisk_2 <= order_2.quantity + M * (
        1 - limit_price_cond_2
    )
    # Executed quantity is zero if the limit price condition is not met.
    problem += q_base_asterisk_1 <= M * limit_price_cond_1
    problem += q_base_asterisk_1 >= -M * limit_price_cond_1
    #
    problem += q_base_asterisk_2 <= M * limit_price_cond_2
    problem += q_base_asterisk_2 >= -M * limit_price_cond_2
    # The number of sold tokens must match the number of bought tokens.
    problem += q_base_asterisk_1 == q_base_asterisk_2
    # Use the default solver and suppress the solver's log.
    solver = pulp.getSolver("PULP_CBC_CMD", msg=0)
    problem.solve(solver)
    # Display the results.
    # TODO(Grisha): probably package the output in a dict.
    _LOG.info(
        "The status is: %s"
        "\nThe total volume (in BTC) exchanged is: %s"
        "\nThe value of exchanged base token from order 1: %s"
        "\nThe value of exchanged base token from order 2: %s"
        "\nThe solution time (in seconds) is: %s",
        pulp.LpStatus[problem.status],
        pulp.value(problem.objective),
        q_base_asterisk_1.varValue,
        q_base_asterisk_2.varValue,
        # TODO(Grisha): double-check that time is in seconds.
        round(problem.solutionTime, 2),
    )


def get_test_orders(
    limit_price_1: float, limit_price_2: float
) -> Tuple[ddacrord.Order, ddacrord.Order]:
    """
    Get toy orders to demonstrate how the solver works.

    :param limit_price_1: limit price for the buy order
    :param limit_price_2: limit price for the sell order
    :return: buy and sell orders
    """
    # Set dummy variables.
    base_token = "BTC"
    quote_token = "ETH"
    deposit_address = 1
    wallet_address = 1
    # Genereate buy order.
    action = "buy"
    quantity = 5
    order_1 = ddacrord.Order(
        base_token,
        quote_token,
        action,
        quantity,
        limit_price_1,
        deposit_address,
        wallet_address,
    )
    _LOG.info("Buy order: %s", str(order_1))
    # Generate sell order.
    action = "sell"
    quantity = 6
    order_2 = ddacrord.Order(
        base_token,
        quote_token,
        action,
        quantity,
        limit_price_2,
        deposit_address,
        wallet_address,
    )
    _LOG.info("Sell order: %s", str(order_2))
    return order_1, order_2


# %% [markdown]
# # Solve the optimization problem

# %% [markdown]
# Any simulation for which the limit price constraint is not satisfied for at least one order ends with no trades being executed.
# While if the limit price constraint is satisfied for all orders the trade is executed using the maximum quantity of the base token taking into account the constraint saying that quantity of sold token = quantity of bought token.

# %%
exchange_rate = 4
_LOG.info("Exchange rate=%s", exchange_rate)

# %% [markdown]
# ## Limit price condition is met for both orders

# %%
limit_price_1 = 5
limit_price_2 = 3
test_orders_1 = get_test_orders(limit_price_1, limit_price_2)
optimize_for_volume(test_orders_1[0], test_orders_1[1], exchange_rate)

# %% [markdown]
# ## Limit price condition is met only for 1 order

# %%
limit_price_1 = 5
limit_price_2 = 5
test_orders_1 = get_test_orders(limit_price_1, limit_price_2)
optimize_for_volume(test_orders_1[0], test_orders_1[1], exchange_rate)

# %%
limit_price_1 = 3
limit_price_2 = 3
test_orders_1 = get_test_orders(limit_price_1, limit_price_2)
optimize_for_volume(test_orders_1[0], test_orders_1[1], exchange_rate)

# %% [markdown]
# ## Limit price condition is not met for both orders

# %%
limit_price_1 = 3
limit_price_2 = 5
test_orders_1 = get_test_orders(limit_price_1, limit_price_2)
optimize_for_volume(test_orders_1[0], test_orders_1[1], exchange_rate)

# %%
