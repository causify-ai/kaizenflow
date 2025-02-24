"""
Import as:

import defi.tulip.implementation.order_matching as dtimorma
"""

import copy
import heapq
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import defi.tulip.implementation.order as dtuimord
import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


def _get_transfer_df(transfers: Optional[List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Get a table of all the token transfers.

    :param transfers: list of transfers, where each transfer is a dict with the
        following format:
        ```
        {
            "token": name of a token to transfer,
            "amount": transferred quantity,
            "from": wallet address to send transfer from,
            "to": deposit to send transfer to,
        }
        ```
    :return: table of transfers as df
    """
    if transfers:
        transfer_df = pd.DataFrame(transfers)
    else:
        transfer_df = pd.DataFrame(columns=["token", "amount", "from", "to"])
    return transfer_df


# TODO(Dan): "Adjust `match_orders()` returns to Tulip contract format" SorrTask #296.
def match_orders(
    orders: List[dtuimord.Order],
    clearing_price: float,
    base_token: str,
    quote_token: str,
) -> pd.DataFrame:
    """
    Implement orders matching for token swaps given a clearing price.

    All orders are assumed to be compatible.

    :param orders: orders to match
    :param clearing_price: clearing price
    :param base_token: name of the base token for swaps, which determines
        the quantity
    :param quote_token: name of the quote token for swaps, which determines
        the price
    :return: transfers implemented to match orders
    """
    _LOG.debug(hprint.to_str("orders"))
    _LOG.debug(hprint.to_str("clearing_price"))
    hdbg.dassert_lt(0, len(orders))
    hdbg.dassert_container_type(orders, list, dtuimord.Order)
    hdbg.dassert_lt(0, clearing_price)
    # Build buy and sell heaps.
    buy_heap = []
    sell_heap = []
    for order in orders:
        # Check that only base and quote tokens are used in the passed orders.
        hdbg.dassert_eq(
            sorted([order.base_token, order.quote_token]),
            sorted([base_token, quote_token]),
        )
        # Adjust all orders to the same base and quote tokens using order
        # equivalence.
        if order.base_token == quote_token:
            order = get_equivalent_order(order, clearing_price)
        # Distribute equalized orders on buy and sell heaps.
        if order.action == "buy":
            if order.limit_price >= clearing_price:
                heapq.heappush(buy_heap, order)
            else:
                _LOG.debug("Order not eligible for matching due to limit")
        elif order.action == "sell":
            if order.limit_price <= clearing_price:
                heapq.heappush(sell_heap, order)
            else:
                _LOG.debug("Order not eligible for matching due to limit")
        else:
            raise ValueError("Invalid action='%s'" % order.action)
    # Check that we have orders of both types so matching is possible.
    hdbg.dassert_lt(0, len(buy_heap))
    hdbg.dassert_lt(0, len(sell_heap))
    _LOG.debug("buy_heap=%s", buy_heap)
    _LOG.debug("sell_heap=%s", sell_heap)
    # Set a list to store transfers that perform matching.
    transfers = []
    # Pick first in priority buy and sell orders for matching.
    # Make a copy so that the func does not alter state (and is idempotent).
    buy_order = copy.copy(buy_heap.pop())
    sell_order = copy.copy(sell_heap.pop())
    # Successively compare `buy_heap` top with `sell_heap` top, matching
    # quantity until zero or queues empty.
    while (buy_heap or buy_order.is_active) and (
        sell_heap or sell_order.is_active
    ):
        # If an order is not active anymore, pop the next order
        # from the corresponding heaps for matching.
        if not buy_order.is_active:
            buy_order = copy.copy(buy_heap.pop())
        if not sell_order.is_active:
            sell_order = copy.copy(sell_heap.pop())
        # Transfer quantity is equal to the min quantity among the matching
        # buy and sell orders.
        quantity = min(buy_order.quantity, sell_order.quantity)
        # Get base token transfer dict and add it to the transfers list.
        base_transfer = {
            "token": buy_order.base_token,
            "amount": quantity,
            "from": sell_order.wallet_address,
            "to": buy_order.deposit_address,
        }
        transfers.append(base_transfer)
        # Get quote token transfer dict and add it to the transfers list.
        quote_transfer = {
            "token": buy_order.quote_token,
            "amount": quantity * clearing_price,
            "from": buy_order.wallet_address,
            "to": sell_order.deposit_address,
        }
        transfers.append(quote_transfer)
        # Change orders quantities with respect to the implemented transfers.
        buy_order.quantity -= quantity
        sell_order.quantity -= quantity
    # Get DataFrame with the transfers implemented to match the passed orders.
    transfer_df = _get_transfer_df(transfers)
    # Check if there are any remaining orders.
    if buy_heap:
        _LOG.warning("Buy orders remain unmatched: %s", buy_heap)
    if sell_heap:
        _LOG.warning("Sell orders remain unmatched: %s", sell_heap)
    return transfer_df


def get_equivalent_order(
    order: dtuimord.Order,
    clearing_price: float,
) -> dtuimord.Order:
    """
    Get equivalent DaoCross order.

    E.g., if `clearing_price` is 0.5 BTC for 1 ETH:
    input order: (1678660406, sell, 3.2, ETH, 0.25, BTC, 0xdeadc0de, 0xabcd0000)
    output order: (1678660406, buy, 1.6, BTC, 4.0, ETH, 0xdeadc0de, 0xabcd0000)

    :param order: input order
    :param clearing_price: clearing price
    :return: order equivalent to the input one
    """
    hdbg.dassert_isinstance(order, dtuimord.Order)
    # Set action opposite to the input's one.
    if order.action == "buy":
        action = "sell"
    elif order.action == "sell":
        action = "buy"
    else:
        raise ValueError("Invalid action='%s'" % order.action)
    # Convert quantity of base token to quantity of quote token.
    quantity = order.quantity * clearing_price
    # Swap base and quote token values.
    base_token = order.quote_token
    quote_token = order.base_token
    # Convert limit price of base token to limit price of quote token.
    limit_price = 1 / order.limit_price
    # Build equivalent order.
    order = dtuimord.Order(
        order.timestamp,
        action,
        quantity,
        base_token,
        limit_price,
        quote_token,
        order.deposit_address,
        order.wallet_address,
    )
    return order
