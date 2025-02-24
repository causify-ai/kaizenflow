"""
Import as:

import oms.broker.ccxt.mock_ccxt_exchange as obcmccex
"""

import asyncio
import copy
import itertools
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import ccxt

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg

_EXCEPTIONS = [
    ccxt.ExchangeNotAvailable,
    ccxt.OnMaintenance,
]
_LOG = logging.getLogger(__name__)

# Represent a deterministic delay or a delay randomly distributed in an interval.
DelayType = Union[float, Tuple[float, float]]

ParamsDict = Dict[str, Union[str, int]]
# For simplicity, say values can be of Any type.
CcxtOrderStructure = Dict[str, Any]

_DUMMY_MARKET_INFO = {
    1464553467: {"amount_precision": 3, "price_precision": 3, "max_leverage": 1},
    1467591036: {"amount_precision": 3, "price_precision": 3, "max_leverage": 1},
    6051632686: {"amount_precision": 3, "price_precision": 3, "max_leverage": 1},
    4516629366: {"amount_precision": 3, "price_precision": 3, "max_leverage": 1},
}


class MockCcxtExchange:
    """
    Class to mock behavior of a CCXT Exchange.

    - This class allows advanced testing of broker behavior.
    - Instead of interacting with real Binance API, the behavior is simulated.

    Invariants in v0.1:
    - Server response delay is simulated as a constant time interval.
    - Orders are filled immediately according to fill_percent.
    """

    # TODO(Juraj): Make the delay argument more advanced, specify per order etc.).
    def __init__(
        self,
        delay_in_secs: DelayType,
        event_loop: asyncio.AbstractEventLoop,
        get_wall_clock_time: hdateti.GetWallClockTime,
        fill_percents: Union[float, List[float]],
        *,
        num_trades_per_order: int = 1,
    ):
        """
        Initialize MockCcxtExchange.

        :param delay_in_secs: default delay in responding
        :param fill_percents:
          - if list: how much % of the child order is filled in each wave,
            each element of the list is used for single wave
          - if float: how much % of the child order is filled, the same for all waves
        :param num_trades_per_order: number of trades to be simulated
            for child order
        """
        # Needed for assigning correct timestamp while inside solipsism context manager.
        # This is a callable.
        self._get_wall_clock_time = get_wall_clock_time
        self._delay_in_secs = delay_in_secs
        # The following attributes represent a state of the binance account, they act as stubs
        # for data that would otherwise be fetched via Binance API calls
        # TODO(Juraj): It might be beneficial to wrap these into a separate class
        # to encapsulate a state of a binance account, decide based on observed complexity.
        self._total_balance = {}
        # Represent exchange positions, example:
        # [
        #    {"info": {"positionAmt": 2500}, "symbol": "ETH/USDT"},
        #    {"info": {"positionAmt": 1000}, "symbol": "BTC/USDT"},
        # ]
        self._positions = []
        # Store all orders as a list of CCXT order structures.
        # CCXT order structure is the cornerstone of most order related methods/operations.
        # https:docs.ccxt.com/#/README?id=order-structure
        # The implementation of methods consists of manipulating this structure +
        # adding artificial waiting times to simulate interaction with a 3rd
        # party server.
        self._orders = []
        # Set-up trivial order ID assigner.
        self._id_counter = None
        # Set event loop in order to simulate passage of time.
        self._event_loop = event_loop
        self._fill_percents = fill_percents
        self._num_trades_per_order = num_trades_per_order
        if isinstance(fill_percents, float):
            # Convert to a list for uniform processing.
            fill_percents = [fill_percents]
        # Set how much of the order (expressed as % float number) is filled.
        for fill_percent in fill_percents:
            hdbg.dassert_is_proportion(fill_percent)
        # Set how many trades will be there for an order to get fill.
        if num_trades_per_order == 0:
            # If there are no trades then fill percentages should also be 0.
            for fill_percent in fill_percents:
                hdbg.dassert_eq(fill_percent, 0)
        if all(fill_percent == 0 for fill_percent in fill_percents):
            # If there are no fills then number of trades should also be 0.
            hdbg.dassert_eq(num_trades_per_order, 0)
        self._trades = {}

    async def fetchMyTrades(
        self, symbol: str, *, limit: Optional[int] = None
    ) -> List[CcxtOrderStructure]:
        """
        Fetch trades from exchange.

        :param limit: return of to the last limit orders, if None return
            all
        """
        trades = self._trades[symbol]
        if limit:
            # In the simulated logic trades are appended one after another,
            # meaning the newest trade is the last in the list.
            adjusted_limit = min(len(trades), limit)
            trades = trades[-adjusted_limit:]
        return trades

    async def fetch_orders(
        self, symbol: str, *, limit: Optional[int] = None
    ) -> List[CcxtOrderStructure]:
        """
        Fetch orders from exchange account.

        :param limit: return of to the last limit orders, if None return
            all
        """
        # It is safer to deepcopy to avoid weird behavior.
        orders = copy.deepcopy(self._orders)
        orders = [o for o in orders if o["symbol"] == symbol]
        if limit:
            # In the simulated logic orders are appended one after another,
            # meaning the newest order is the last in the list.
            adjusted_limit = min(len(orders), limit)
            orders = orders[-adjusted_limit:]
        return orders

    async def fetch_order(self, id: str, symbol: str) -> List[CcxtOrderStructure]:
        """
        Fetch single order for ccxt id and symbol from exchange.
        """
        orders = copy.deepcopy(self._orders)
        orders = [o for o in orders if o["symbol"] == symbol and o["id"] == id]
        return orders[0]

    def fetchPositions(
        self, *, symbols: Optional[List[str]] = None
    ) -> Dict[str, Union[str, float]]:
        """
        Fetch positions from exchange account.

        CCXT returns the position structure
        https://docs.ccxt.com/#/README?id=position-structure
         We return only a subset of fields of interest to us.

        :param symbols: specify list of symbols to return positions of,
            if None then all symbols returned
        """
        positions = copy.deepcopy(self._positions)
        if symbols:
            positions = [
                p
                for p in positions
                if p["symbol"] in symbols and p["info"]["positionAmt"] != 0
            ]
        return positions

    def fetch_positions(
        self, *, symbols: Optional[List[str]] = None
    ) -> Dict[str, Union[str, float]]:
        """
        Fetch positions from exchange account.

        Proxy for fetchPositions (same functionality under different
        name).
        """
        return self.fetchPositions(symbols=symbols)

    def setLeverage(self, leverage: int, symbol: str) -> None:
        """
        Set leverage for a symbol.

        Currently this behavior does not alter outputs of the mock
        exchange, meaning implementation is empty.
        """

    def cancelAllOrders(self, symbol: str) -> List[CcxtOrderStructure]:
        # self._simulate_waiting_for_response()
        cancelled_orders = []
        for order in self._orders:
            if order["status"] == "opened":
                order["status"] = "canceled"
                cancelled_orders.append(order)
        return cancelled_orders

    async def cancel_all_orders(self, symbol: str) -> List[CcxtOrderStructure]:
        """
        Cancel all orders for given symbol.
        """
        return self.cancelAllOrders(symbol)

    def createLimitBuyOrder(
        self,
        symbol: str,
        amount: float,
        price: float,
        *,
        params: Optional[ParamsDict] = None,
    ) -> CcxtOrderStructure:
        """
        Simulate sending a limit buy order:
        """
        return self.create_order(symbol, amount, price, "buy", params=params)

    def createLimitSellOrder(
        self, symbol: str, amount: float, price: float, params: ParamsDict
    ) -> CcxtOrderStructure:
        """
        Simulate sending a limit sell order:
        """
        return self.create_order(symbol, amount, price, "sell", params=params)

    async def create_order(
        self,
        symbol: str,
        amount: float,
        price: float,
        side: str,
        *,
        type: str = "limit",
        params: Optional[ParamsDict] = None,
    ) -> CcxtOrderStructure:
        """
        Helper function for creating an order.
        """
        await self._simulate_waiting_for_response()
        # TODO(Juraj): implement usage of params.
        amount = amount if side == "buy" else -amount
        if isinstance(self._fill_percents, float):
            fill_percent = self._fill_percents
        else:
            fill_percent = self._fill_percents.pop(0)
        filled = abs(amount) * fill_percent
        remaining = abs(amount) - filled
        order = {
            "id": self._generate_ccxt_order_id(),  # string
            # Currently we simulate order being filled immediately meaning its closed.
            "status": "closed",
            "symbol": symbol,
            # TODO(Juraj): Only "limit" is supported for now.
            "type": "limit",
            "side": side,
            "price": price,
            "amount": amount,
            # Assume order is filled immediately in full.
            "filled": filled,
            "remaining": remaining,
            # Needed when broker calls get_fills().
            "cost": price * filled,
            "info": {
                "updateTime": hdateti.convert_timestamp_to_unix_epoch(
                    self._get_wall_clock_time()
                )
            },
        }
        # Update the position with the amount filled.
        filled_amount = filled if side == "buy" else -filled
        self._update_position(symbol, filled_amount)
        self._generate_trades(order)
        self._orders.append(order)
        return order

    def _generate_trades(self, order: CcxtOrderStructure) -> None:
        """
        Generate dummy trades for a given order.

        This method creates multiple trade records for a single order,
        evenly dividing the filled amount.

        :param order: the order for which dummy trades are generated.
        """
        if self._num_trades_per_order > 0:
            amount_per_trade = order["filled"] / self._num_trades_per_order
            amount_per_trade = (
                amount_per_trade if order["side"] == "buy" else -amount_per_trade
            )
            trades = [
                {
                    "info": {
                        "orderId": order["id"],
                    },
                    "symbol": order["symbol"],
                    # Some random trade id.
                    "id": str(int(order["id"]) * 100 + i + 1),
                    "order": order["id"],
                    "type": order["type"],
                    "side": order["side"],
                    "price": order["price"],
                    "amount": amount_per_trade,
                    "cost": amount_per_trade * order["price"],
                }
                for i in range(self._num_trades_per_order)
            ]
        else:
            trades = []
        if order["symbol"] not in self._trades:
            self._trades[order["symbol"]] = trades
        else:
            self._trades[order["symbol"]].extend(trades)

    def _update_position(self, symbol: str, amount: float) -> None:
        for position in self._positions:
            if position["symbol"] == symbol:
                position["info"]["positionAmt"] += amount

    # TODO(Juraj): we might even create a decorator.
    async def _simulate_waiting_for_response(self) -> None:
        """
        Sleep for a defined time interval to simulate waiting for server
        response.
        """
        await asyncio.sleep(self._delay_in_secs)

    def _generate_ccxt_order_id(self) -> str:
        """
        Dummy order ID generator.

        The function simply increases internally stored counter by one
        and returns the value.
        """
        if self._id_counter is not None:
            self._id_counter += 1
        else:
            self._id_counter = 0
        # CCXT returns string id, stick to the interface.
        return str(self._id_counter)


class MockCcxtExchange_withErrors(MockCcxtExchange):
    """
    Invariants in this child class:

    - Calling method which creates order results in raising an exception.
    - The number of consecutive exceptions raised when repeating the method call is
    determined by the parameter set in constructor.
    """

    def __init__(self, num_exceptions: int, *args, **kwargs):
        """
        Initialize MockCcxtExchange_withErrors.

        :param num_exceptions: number of consecutive exceptions to raise
            when repeating a call to any of the order creating methods
        """
        super().__init__(*args, **kwargs)
        self._num_exceptions = num_exceptions
        self._num_exceptions_raised = 0
        self.exceptions_cycler = itertools.cycle(_EXCEPTIONS)

    async def create_order(self, *args, **kwargs) -> CcxtOrderStructure:
        if self._num_exceptions_raised < self._num_exceptions:
            # Simulate waiting response time from server.
            await self._simulate_waiting_for_response()
            self._num_exceptions_raised += 1
            exception_to_raise = next(self.exceptions_cycler)
            raise exception_to_raise("Some error message")
        order = await super().create_order(*args, **kwargs)
        return order
