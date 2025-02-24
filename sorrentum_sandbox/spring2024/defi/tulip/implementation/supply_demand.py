"""
Import as:

import defi.tulip.implementation.supply_demand as dtimsude
"""

import logging
import random
from typing import List

import matplotlib.pyplot as plt
import pandas as pd

import defi.tulip.implementation.order as dtuimord
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Discrete supply/demand curves.
# #############################################################################


def convert_discrete_curve_to_limit_orders(
    discrete_curve: pd.Series,
    *,
    quantity_scale: float = 1.0,
    quantity_const: float = 0.0,
    limit_price_scale: float = 1.0,
    limit_price_const: float = 0.0,
    seed: int = 42,
) -> List[dtuimord.Order]:
    """
    Get a list of orders that represent supply or demand.

    :param discrete_curve: series of discrete curve dots coordinates
    :param quantity_scale: coef to multiply quantities
    :param quantity_const: const to change quantities
    :param limit_price_scale: coef to multiply limit prices
    :param limit_price_const: const to change limit prices
    :param seed: seed for random sampling
    :return: orders that represent demand or supply curve
    """
    random.seed(seed)
    timestamp = None
    # TODO(Dan): Add asserts for the passed discrete curve `pd.Series`.
    # Get base token and order action from the passed curve name.
    base_token, type_ = discrete_curve.name.split(".")
    hdbg.dassert_in(type_, ["supply", "demand"])
    if type_ == "supply":
        action = "sell"
        ascending = True
    else:
        action = "buy"
        ascending = False
    # Get quote token from the passed curve index name.
    quote_token = discrete_curve.index.name
    # Invert coordinates, so prices are indices and quantities are values.
    # Sort by prices with respect to the curve type.
    inverted_srs = pd.Series(
        index=discrete_curve.values,
        data=discrete_curve.index,
    ).sort_index(ascending=ascending)
    # Order quantities are distances between the curve quantities.
    # Order limit prices correspond to the curve limit prices.
    order_data = inverted_srs.diff().fillna(inverted_srs)
    # Generate orders.
    orders = []
    for p, q in order_data.items():
        # Adjust quantities and prices by the passed params.
        q = q * quantity_scale + quantity_const
        p = p * limit_price_scale + limit_price_const
        # Generate random addresses.
        deposit_address = random.randint(1, 10)
        wallet_address = deposit_address
        # Build orders.
        order = dtuimord.Order(
            timestamp,
            action,
            q,
            base_token,
            p,
            quote_token,
            deposit_address,
            wallet_address,
        )
        orders.append(order)
    return orders


def get_supply_demand_discrete_curve(
    type_: str,
    orders_df: pd.DataFrame,
) -> pd.Series:
    """
    Get a series of discrete curve dots coordinates from orders data.

    :param type_: curve type
    :param orders_df: orders data
    :return: series of dots coordinates that belong to the curve
    """
    # TODO(Dan): Allow to parse equivalent orders?
    # Get base and quote tokens and check that they are equal for all orders.
    base_tokens = orders_df["base_token"].unique()
    quote_tokens = orders_df["quote_token"].unique()
    hdbg.dassert_eq(1, len(base_tokens))
    hdbg.dassert_eq(1, len(quote_tokens))
    base_token = base_tokens[0]
    quote_token = quote_tokens[0]
    # Filter orders based on the specified curve type.
    if type_ == "supply":
        orders_df = orders_df[orders_df["action"] == "sell"]
        ascending = True
    elif type_ == "demand":
        orders_df = orders_df[orders_df["action"] == "buy"]
        ascending = False
    else:
        raise ValueError("Invalid type_='%s'" % type_)
    # Get only necessary columns.
    orders_df = orders_df[["limit_price", "quantity"]]
    # Sort orders by limit price with respect to the curve type.
    # Supply curve is increasing, orders are in ascending order.
    # Demand curve is decreasing, orders are in descending order.
    orders_df = orders_df.sort_values(by="limit_price", ascending=ascending)
    # Get curve values for quantities and limit prices.
    curve_quantities = orders_df["quantity"].cumsum()
    curve_limit_prices = orders_df["limit_price"]
    # Set curve name using base token and curve type.
    curve_name = ".".join([base_token, type_])
    # Build a series from curve coordinates.
    curve_srs = pd.Series(
        data=curve_limit_prices.values,
        index=curve_quantities.values,
        name=curve_name,
    )
    # Set curve index name using quote token.
    curve_srs.index.name = quote_token
    return curve_srs


def plot_discrete_curve(
    curve_srs: pd.Series,
    *,
    display_plot: bool = False,
) -> None:
    """
    Plot a discrete supply or demand curve.
    """
    quantities = curve_srs.index
    limit_prices = curve_srs.values
    # Get tokens and curve type from the series.
    quote_token = curve_srs.index.name
    base_token, type_ = curve_srs.name.split(".")
    # Set params dependent on the curve type.
    if type_ == "demand":
        color = "b"
        vertical_line_ymin = 0
        vertical_line_ymax = limit_prices[-1]
    elif type_ == "supply":
        color = "r"
        vertical_line_ymin = limit_prices[-1]
        # Supply curve limit price is extending to infinity at max quantity.
        vertical_line_ymax = limit_prices[-1] * 1.25
    else:
        raise ValueError("Invalid type_='%s'" % type_)
    # Plot the curve.
    plt.step(quantities, limit_prices, color=color)
    # Add lines to complete the step plots and capture available trading dots.
    plt.vlines(
        x=quantities[-1],
        ymin=vertical_line_ymin,
        ymax=vertical_line_ymax,
        color=color,
    )
    plt.hlines(
        xmin=0,
        xmax=quantities[0],
        y=limit_prices[0],
        color=color,
    )
    # Add title and lables.
    title = f"{base_token}/{quote_token}"
    plt.title(title)
    plt.xlabel("Quantity")
    plt.ylabel("Limit price")
    if display_plot:
        plt.show()


# #############################################################################
# Aggregated supply/demand curves.
# #############################################################################


def get_supply_demand_aggregated_curve(
    type_: str,
    alpha: float,
    beta: float,
    n_orders: int,
    *,
    base_token: str = "BTC",
    quote_token: str = "ETH",
    max_quantity: float = 100.0,
    seed: int = 42,
) -> pd.Series:
    """
    Get a series of aggregated curve dots from the linear function formula.

    Formula: limit_price = alpha * quantity + beta

    :param type_: curve type
    :param alpha: slope
    :param beta: intercept
    :param n_orders: number of orders to generate
    :param max_quantity: max quantity that a seller can provide
    :param seed: seed for random sampling
    :return: series of aggregated curve coordinates
    """
    random.seed(seed)
    if type_ == "supply":
        hdbg.dassert_lt(0.0, alpha)
        # Get supply min quantity to set it as a limit.
        min_quantity = -beta / alpha
        # Supply quantity cannot be negative.
        min_quantity = max(0.0, min_quantity)
    elif type_ == "demand":
        hdbg.dassert_lt(alpha, 0.0)
        hdbg.dassert_lt(0.0, beta)
        # A buyer can order any non-negative quantity.
        min_quantity = 0.0
        # Get demand max quantity to set it as a limit.
        max_quantity = -beta / alpha
    else:
        raise ValueError("Invalid type_='%s'" % type_)
    # Generate curve dots.
    quantities = []
    limit_prices = []
    for _ in range(n_orders):
        # Generate random quantity in specified interval.
        q = random.uniform(min_quantity, max_quantity)
        quantities.append(q)
        # Get the corresponging limit price using linear function formula.
        p = alpha * q + beta
        limit_prices.append(p)
    # Sort quantities in ascending order to represent a curve.
    quantities = sorted(quantities)
    # Sort limit prices with respect to the curve type.
    # Supply curve is increasing, limit prices are in ascending order.
    # Demand curve is decreasing, limit prices are in descending order.
    reverse = type_ == "demand"
    limit_prices = sorted(limit_prices, reverse=reverse)
    # Set curve name using base token and curve type.
    curve_name = ".".join([base_token, type_])
    # Put aggregated curve coodinates in a series.
    agg_curve = pd.Series(data=limit_prices, index=quantities, name=curve_name)
    # Set curve index name using quote token.
    agg_curve.index.name = quote_token
    return agg_curve


def convert_aggregated_curve_to_limit_orders(
    agg_curve: pd.Series,
    *,
    seed: int = 42,
) -> List[dtuimord.Order]:
    """
    Get orders from a series of aggregated curve dots coordinates.

    :param agg_curve: series of aggregated curve coordinates
    :param seed: seed for random sampling
    :return: orders that represent demand or supply curve
    """
    random.seed(seed)
    timestamp = None
    # TODO(Dan): Add asserts for the passed agg curve `pd.Series`.
    # Get base token and order action from the passed curve name.
    base_token, type_ = agg_curve.name.split(".")
    hdbg.dassert_in(type_, ["supply", "demand"])
    if type_ == "supply":
        action = "sell"
    else:
        action = "buy"
    # Get quote token from the passed curve index name.
    quote_token = agg_curve.index.name
    # Set amount of quantity that has already entered the market.
    quantity_on_market = 0.0
    orders = []
    for q, p in agg_curve.items():
        # Order quantity is a distance between the dot with this order
        # and quantity on market before it.
        order_q = q - quantity_on_market
        # Generate random addresses.
        deposit_address = random.randint(1, 10)
        wallet_address = deposit_address
        # Generate orders.
        order = dtuimord.Order(
            timestamp=timestamp,
            action=action,
            quantity=order_q,
            base_token=base_token,
            limit_price=p,
            quote_token=quote_token,
            deposit_address=deposit_address,
            wallet_address=wallet_address,
        )
        orders.append(order)
        # Update quantity on market.
        quantity_on_market = q
    return orders
