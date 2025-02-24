"""
Import as:

import oms.broker.ib_api as obribapi
"""

import logging
from typing import Dict, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)

# TODO(gp): @nina -> ib_api.py


class Contract:
    """
    Represent a financial instrument.

    Modelled after:
    https://ib-insync.readthedocs.io/api.html#module-ib_insync.contract

    IB Documentation:
    https://interactivebrokers.github.io/tws-api/classIBApi_1_1Contract.html
    """

    def __init__(
        self,
        symbol: str,
        sec_type: str,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
    ):
        self.symbol = symbol
        hdbg.dassert_in(sec_type, ("STK", "FUT"))
        self.sec_type = sec_type
        hdbg.dassert_in(currency, ("USD", None))
        self.exchange = exchange
        self.currency = currency

    def __repr__(self):
        return "Contract: symbol=%s, sec_type=%s, currency=%s, exchange=%s" % (
            self.symbol,
            self.sec_type,
            self.exchange,
            self.currency,
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Contract):
            return self.__key() == other.__key()
        return NotImplementedError

    def __key(self):
        return self.symbol, self.sec_type, self.exchange, self.currency


class ContinuousFutures(Contract):
    pass


class Futures(Contract):
    pass


class Stock(Contract):
    pass


# #############################################################################


class Order:
    """
    Order for trading contracts.

    Modelled after:
    https://ib-insync.readthedocs.io/api.html#ib_insync.order.Order

    IB Documentation:
    https://interactivebrokers.github.io/tws-api/classIBApi_1_1Order.html
    """

    def __init__(
        self,
        order_id: int,
        action: str,
        total_quantity: float,
        order_type: str,
        timestamp: Optional[pd.Timestamp] = None,
    ):
        """
        Create an order.

        :param order_id: The API client's order id.
        :param action: Identifies the side. Generally available values are BUY, SELL...
        :param total_quantity: The number of positions being bought/sold.
        :param order_type: The order's type.
        :param timestamp:
        """
        self.order_id = order_id
        hdbg.dassert_in(action, ("BUY", "SELL"))
        self.action = action
        hdbg.dassert_lt(0.0, total_quantity)
        self.total_quantity = total_quantity
        hdbg.dassert_in(order_type, ("MKT", "LIM"))
        self.order_type = order_type
        #
        self.timestamp = timestamp

    def __repr__(self):
        return (
            "Order: order_id=%s, action=%s, total_quantity=%s, order_type=%s timestamp=%s"
            % (
                self.order_id,
                self.action,
                self.total_quantity,
                self.order_type,
                self.timestamp,
            )
        )


class MarketOrder(Order):
    pass


class LimitOrder(Order):
    def __init__(self, limit_price: float):
        self.limit_price = limit_price


# #############################################################################


class Position:
    """
    Modelled after:

    https://ib-insync.readthedocs.io/api.html#ib_insync.objects.Position
    """

    def __init__(self, contract: Contract, position: float):
        self.contract = contract
        # We don't allow a position with no shares.
        hdbg.dassert_ne(0, position)
        self.position = position

    def __repr__(self):
        ret = []
        ret.append("contract=%s" % self.contract)
        ret.append("position=%s" % self.position)
        ret = "\n".join(ret)
        num_spaces = 2
        ret = "Position:\n" + hprint.indent(ret, num_spaces=num_spaces)
        return ret

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Position):
            return self.__key() == other.__key()
        return NotImplemented

    @staticmethod
    def update(lhs: "Position", rhs: "Position") -> Optional["Position"]:
        """
        Update the position `lhs` using another position `rhs`.
        """
        hdbg.dassert_eq(lhs.contract, rhs.contract)
        position = lhs.position + rhs.position
        if position == 0:
            return None
        return Position(lhs.contract, position)

    def __key(self):
        return self.contract, self.position


# #############################################################################


class OrderStatus:
    """
    Status of order.

    IB Documentation:
    https://interactivebrokers.github.io/tws-api/interfaceIBApi_1_1EWrapper.html#a17f2a02d6449710b6394d0266a353313
    """

    def __init__(
        self,
        order_id: int,
        status: str,
        filled: float,
        remaining: float,
        avg_fill_price: float,
    ) -> None:
        # Pointer to the corresponding Order.
        hdbg.dassert_lte(0, order_id)
        self.order_id = order_id
        self.status = status
        # How many shares are filled.
        hdbg.dassert_lte(0, filled)
        self.filled = filled
        # How many shares were not filled.
        hdbg.dassert_lte(0, remaining)
        self.remaining = remaining
        hdbg.dassert_lte(0, avg_fill_price)
        self.avg_fill_price = avg_fill_price

    def __repr__(self):
        return (
            "OrderStatus: order_id=%s, status=%s, filled=%s, remaining=%s avg_fill_price=%s"
            % (
                self.order_id,
                self.status,
                self.filled,
                self.remaining,
                self.avg_fill_price,
            )
        )


class Trade:
    """
    Keep track of an order, its status, and its fills.

    Modelled after:
    https://ib-insync.readthedocs.io/api.html#ib_insync.order.Trade
    """

    def __init__(
        self,
        contract: Contract,
        order: Order,
        order_status: OrderStatus,
        timestamp: Optional[pd.Timestamp] = None,
    ) -> None:
        self.contract = contract
        self.order = order
        hdbg.dassert_lte(
            order_status.filled,
            order.total_quantity,
            msg="Can't fill more than what was requested",
        )
        hdbg.dassert_eq(
            order.total_quantity,
            order_status.filled + order_status.remaining,
            msg="The filled and remaining shares must be the same as the total quantity",
        )
        self.order_status = order_status
        self.timestamp = timestamp  # TODO(gp): Implement fills.

    def __repr__(self):
        ret = []
        ret.append("contract=%s" % self.contract)
        ret.append("order=%s" % self.order)
        ret.append("order_status=%s" % self.order_status)
        ret.append("timestamp=%s" % self.timestamp)
        ret = "\n".join(ret)
        num_spaces = 2
        ret = "Trade:\n" + hprint.indent(ret, num_spaces=num_spaces)
        return ret

    def to_position(self) -> Position:
        return Position(self.contract, self.order_status.filled)


# #############################################################################


# TODO(gp): Consider extending to support more accounts.
class OMS:
    """
    Order management system.

    It is a singleton.

    Modelled after:
    https://ib-insync.readthedocs.io/api.html#module-ib_insync.ib
    """

    def __init__(self) -> None:
        self._trades = []
        self._orders = []
        #
        self._current_positions: Dict[Contract, Position] = {}

    def __repr__(self):
        def _to_string(prefix, objs) -> str:
            ret = "%s=%d" % (prefix, len(objs))
            if objs:
                ret += "\n" + hprint.indent("\n".join(map(str, objs)), 2)
            return ret

        ret = []
        ret.append(_to_string("trades", self._trades))
        ret.append(_to_string("orders", self._orders))
        ret.append(_to_string("positions", sorted(self._current_positions)))
        #
        ret = "\n".join(ret)
        ret = "OMS:\n" + hprint.indent(ret, 2)
        return ret

    def get_current_positions(self) -> Dict[Contract, Position]:
        return self._current_positions.copy()

    # TODO(gp): To be implemented.
    def pnl(self):
        pass

    def place_order(
        self,
        contract: Contract,
        order: Order,
        timestamp: Optional[pd.Timestamp] = None,
    ) -> Trade:
        """
        Place an order, record trade, and update current position.

        https://ib-insync.readthedocs.io/_modules/ib_insync/client.html#Client.placeOrder

        :param contract:
        :param order:
        :param timestamp:
        :return:
        """
        self._orders.append(order)
        # Assume that everything is filled.
        # TODO(gp): Here we can implement market impact and incomplete fills.
        status = "filled"
        filled = order.total_quantity
        remaining = 0.0
        # TODO(gp): Implement this by talking to IM.
        avg_fill_price = 1000.0
        order_status = OrderStatus(
            order.order_id, status, filled, remaining, avg_fill_price
        )
        trade = Trade(contract, order, order_status, timestamp=timestamp)
        self._trades.append(trade)
        #
        self._update_positions(trade)
        return trade

    def _update_positions(self, trade: Trade) -> None:
        """
        Update the current position given the executed trade.
        """
        hdbg.dassert_eq(
            len(set(self._current_positions)),
            len(self._current_positions),
            msg="All positions should be about different Contracts",
        )
        # Look for the contract corresponding to `trade` among the current positions.
        contract = trade.contract
        current_position = self._current_positions.get(contract, None)
        if current_position is None:
            _LOG.debug("Adding new contract: %s", contract)
            position = Position(contract, trade.order.total_quantity)
        else:
            # Update the current position for `contract`.
            position = Position.update(current_position, trade.to_position())
        _LOG.debug("position=%s", position)
        # Update the contract.
        if position is None:
            if contract in self._current_positions:
                _LOG.debug(
                    "Removing %s from %s", contract, self._current_positions
                )
                del self._current_positions[contract]
        else:
            _LOG.debug("Updating %s to %s", current_position, position)
            self._current_positions[contract] = position
