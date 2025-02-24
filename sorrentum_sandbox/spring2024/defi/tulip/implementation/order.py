"""
Import as:

import defi.tulip.implementation.order as dtuimord
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# TODO(gp): Maybe LimitOrder or DaoLimitOrder?
class Order:
    """
    Limit order to be used in DaoCross or DaoSwap.
    """

    def __init__(
        self,
        timestamp: Union[float, pd.Timestamp],
        action: str,
        quantity: float,
        base_token: str,
        limit_price: float,
        quote_token: str,
        # TODO(gp): -> dst_address?
        deposit_address: Union[int, str],
        # TODO(gp): -> src_address?
        wallet_address: Union[int, str],
    ) -> None:
        """
        Constructor.

        According to the white paper, an order like:

        ```(1678660406, buy, 3.2, ETH, 4.0, wBTC, 0xdeadc0de, 0xabcd0000)```

        corresponds to the natural language description:
        “At timestamp Mon Mar 13 2023 02:33:25 GMT+0000, the user commits
        to buy up to 3.2 units of ETH in exchange for wBTC up to a limit price
        of 4.0 wBTC per ETH with proceeds deposited at 0xdeadc0de and with
        token provided to the swap from wallet address 0xabcd0000”

        :param timestamp: time of order execution (e.g., "Mon Mar 13 2023
            02:33:25 GMT+0000")
            - `None` means the current wall clock time
        :param action: order action type
            - "buy": purchase the base token and pay with the quote token
            - "sell": sell the base token and receive the quote token
        :param quantity: maximum quantity in terms of the base token (e.g., 3.2)
        :param base_token: token to express order quantity with (e.g., ETH)
        :param limit_price: limit price in terms of the quote token (e.g.,
            4.0 BTC per ETH). The limit price is interpreted as non-strict
            inequality, e.g., if `limit_price=4`, the order can be executed
            with a price of 4.0 quote / base token
        :param quote_token: token to express order price with (e.g., BTC)
        :param deposit_address: deposit address to transfer the result of the swap
            (e.g., 0xdeadc0de)
        :param wallet_address: wallet address with the token to provide to the
            swap (e.g., 0xabcd0000)
        """
        hdbg.dassert_isinstance(base_token, str)
        hdbg.dassert_isinstance(quote_token, str)
        hdbg.dassert_lte(0, quantity)
        hdbg.dassert_in(action, ["buy", "sell"])
        if pd.isna(timestamp):
            # Use current time of execution if timestamp is not specified.
            self.timestamp = hdateti.get_current_time(tz="UTC")
        else:
            hdbg.dassert_isinstance(timestamp, pd.Timestamp)
            self.timestamp = timestamp
        self.action = action
        self.quantity = quantity
        self.base_token = base_token
        # Replace NaN with signed `np.inf` depending upon `action`.
        # This helps with `Order` comparisons (`lt` and `gt`).
        if pd.isna(limit_price):
            if self.action == "buy":
                self.limit_price = np.inf
            elif self.action == "sell":
                self.limit_price = -np.inf
            else:
                raise ValueError("Invalid action='%s'" % self.action)
        else:
            self.limit_price = limit_price
        self.quote_token = quote_token
        self.deposit_address = deposit_address
        self.wallet_address = wallet_address

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        ret = (
            "timestamp=%s action=%s quantity=%s base_token=%s limit_price=%s quote_token=%s deposit_address=%s wallet_address=%s"
            % (
                self.timestamp,
                self.action,
                self.quantity,
                self.base_token,
                self.limit_price,
                self.quote_token,
                self.deposit_address,
                self.wallet_address,
            )
        )
        return ret

    def __lt__(self, other: "Order") -> bool:
        """
        Compare if order is lower in priority than the passed one.

        Because we use a min-heap, taking precedence in the order queue
        is given "lower priority" in the internal heap.
        """
        return self._takes_precedence(other)

    def __gt__(self, other: "Order") -> bool:
        """
        Compare if order is greater in priority than the passed one.
        """
        return not self._takes_precedence(other)

    @property
    def is_active(self) -> bool:
        """
        `Order` is active if its quantity is above 0.
        """
        if self.quantity > 0:
            return True
        else:
            return False

    @property
    def action_as_int(self) -> int:
        """
        Translate `Order` action to an int representation of a direction with
        the usual conventions of buy / sell.
        """
        if self.action == "buy":
            return 1
        else:
            return -1

    # TODO(Dan): Add `to_dataframe()` func.
    def to_dict(self) -> Dict[str, Any]:
        dict_: Dict[str, Any] = collections.OrderedDict()
        dict_["timestamp"] = self.timestamp
        dict_["action"] = self.action
        dict_["quantity"] = self.quantity
        dict_["base_token"] = self.base_token
        dict_["limit_price"] = self.limit_price
        dict_["quote_token"] = self.quote_token
        dict_["deposit_address"] = self.deposit_address
        return dict_

    def _takes_precedence(self, other: "Order") -> bool:
        """
        Compare order to another one according to quantity, price and
        timestamp.

        Prioritize orders according to:

            1. Quantity - higher quantity comes first in priority
            2. Price - higher limit price breaks quantity ties
            3. Timestamp - earlier timestamp breaks ties in quantity and price
        :param other: order to compare the actual order with
        :return: "True" if this order preceeds the other one, "False" otherwise
        """
        takes_precedence = False
        if self.quantity > other.quantity:
            takes_precedence = True
        elif self.limit_price > other.limit_price:
            takes_precedence = True
        elif self.timestamp > other.timestamp:
            takes_precedence = True
        return takes_precedence


def get_random_order(seed: Optional[int] = None) -> Order:
    """
    Get an order for ETH/BTC with randomized valid parameters.
    """
    if seed is not None:
        np.random.seed(seed)
    # Do not impose a timestamp.
    timestamp = np.nan
    # Generate random buy/sells.
    action = "buy" if np.random.random() < 0.5 else "sell"
    # Generate random quantities.
    quantity = np.random.randint(1, 10)
    # Set token names.
    base_token = "ETH"
    quote_token = "BTC"
    # Do not impose a limit price.
    limit_price = np.nan
    # Create a random wallet address.
    deposit_address = np.random.randint(-3, 3)
    # Prevent self-crossing (in a crude way).
    if action == "buy":
        deposit_address = abs(deposit_address)
    elif action == "sell":
        deposit_address = -abs(deposit_address)
    # Make wallet address and deposit address the same.
    wallet_address = deposit_address
    # Build the order.
    order = Order(
        timestamp,
        action,
        quantity,
        base_token,
        limit_price,
        quote_token,
        deposit_address,
        wallet_address,
    )
    return order


def convert_orders_to_dataframe(orders: List[Order]) -> pd.DataFrame:
    """
    Convert a list of orders to a dataframe.

    :param orders: list of `Order`
    :return: dataframe with one order per row and attributes as cols
    """
    hdbg.dassert_container_type(orders, list, Order)
    df = pd.concat([pd.Series(order.to_dict()) for order in orders], axis=1).T
    df = df.convert_dtypes()
    return df


def execute_order(order: Order, price: float) -> List[Tuple[float, str]]:
    """
    Execute order at specified price.

    :param order: `Order` to be executed
    :param price: price that user pays in quote token in exchange to get base token
    :return: info about executed changes in base and quote token amounts
    """
    given_action = order.action
    if given_action == "buy":
        if price <= order.limit_price:
            exec_info = [
                (-order.quantity * price, order.quote_token),
                (order.quantity, order.base_token),
            ]
        else:
            _LOG.info(
                "The order cannot be executed for given action='%s' as the given \
                    price='%f' is greater than limit_price='%f'",
                given_action,
                price,
                order.limit_price,
            )
            exec_info = None
    elif given_action == "sell":
        if price >= order.limit_price:
            exec_info = [
                (order.quantity * price, order.quote_token),
                (order.quantity, order.base_token),
            ]
        else:
            _LOG.info(
                "The order cannot be executed for given action='%s' as the given \
                    price='%f' is less than limit_price='%f'",
                given_action,
                price,
                order.limit_price,
            )
            exec_info = None
    else:
        raise ValueError("Invalid order action='%s'" % given_action)
    return exec_info
