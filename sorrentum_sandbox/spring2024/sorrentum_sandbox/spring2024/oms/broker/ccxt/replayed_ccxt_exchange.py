"""
Import as:

import oms.broker.ccxt.replayed_ccxt_exchange as obcrccex
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

import helpers.hdbg as hdbg
import oms.broker.ccxt.mock_ccxt_exchange as obcmccex

_LOG = logging.getLogger(__name__)


class ReplayedCcxtExchange(obcmccex.MockCcxtExchange):
    """
    Replay the behavior of an actual CCXT Exchange.

    - This class allows advanced testing of broker behavior by replaying logs that
    took place during a particular experiment in the exact same sequential order.
    - Instead of interacting with real CCXT Exchange this class is injected in CcxtBroker
    which will use the data(ccxt_orders, ccxt_fills, ccxt_trades) from the log files and
    replay the entire simulation in the same sequential order.

    Invariants in v0.1:
    - ccxt_orders list is provided in sorted sequential order using timestamps.
    - TODO(Sameep): Because of CmampTask5796 we are not mocking the wallclock yet,
      thus we are currently using real-time market data, which means that the
      timestamps on our orders are synchronized with the actual time on the clock.
      As a result, there are variations in the start and end timestamps for new
      orders created during the 'ReplayedCcxtExchange' compared to those in the
      original experiment.
    """

    def __init__(
        self,
        ccxt_orders: List[obcmccex.CcxtOrderStructure],
        ccxt_fill_list: List[obcmccex.CcxtOrderStructure],
        ccxt_trades_list: List[obcmccex.CcxtOrderStructure],
        exchange_markets: List[Dict[str, Any]],
        leverage_info: List[Dict[str, Any]],
        reduce_only_ccxt_orders: List[obcmccex.CcxtOrderStructure],
        positions: List[Dict[str, Any]],
        balances: List[Dict[str, Any]],
        # Params from `MockCcxtExchange`.
        *args: Any,
        **kwargs: Any,
    ):
        """
        Constructor.

        :param ccxt_orders: CCXT orders from the logs.
        :param ccxt_fills: CCXT fill order from the logs.
        :param ccxt_trades: CCXT trade orders from the logs.
        """
        # TODO(Sameep): To add assertions which check if the invariants.
        # specified in the constructors are met.
        super().__init__(*args, **kwargs)
        self._orders = self._get_dictionary_from_list(ccxt_orders)
        self._ccxt_fills = self._get_dictionary_from_list(ccxt_fill_list)
        self._ccxt_trades = self._get_dictionary_from_list(ccxt_trades_list)
        self._exchange_markets = exchange_markets
        self._leverage_info = leverage_info
        self._ccxt_filled = {}
        self.has = {"fetchBalance": True}
        self._balances = balances
        self._reduce_only_ccxt_orders = self._get_dictionary_from_list(
            reduce_only_ccxt_orders
        )
        self._positions = positions

    async def create_order(
        self,
        symbol: str,
        type: str,
        amount: float,
        price: float,
        side: str,
        *,
        params: Optional[obcmccex.ParamsDict] = None,
    ) -> obcmccex.CcxtOrderStructure:
        """
        Function to replicate behavior of CCXT response to creating orders.
        """
        await asyncio.sleep(self._delay_in_secs)
        # Check if the order list is not empty and get the first order.
        hdbg.dassert_ne(len(self._orders), 0, "Log order data is empty")
        if symbol not in self._orders:
            raise AssertionError(f"symbol: {symbol} not present in log data")
        elif len(self._orders[symbol]) == 0:
            raise AssertionError(
                f"symbol: {symbol} has no more log entries present"
            )
        order = self._orders[symbol].pop(0)
        if order.get("empty") == True:
            return {}
        params_list = {
            "type": type,
            "amount": amount,
            "price": price,
            "side": side,
        }
        diff_params = []
        for param, value in params_list.items():
            if order[param] != value:
                diff_params.append(param)
        if diff_params:
            raise AssertionError(
                f"The following arguments do not match with log data: {diff_params}"
            )
        return order

    async def createReduceOnlyOrder(
        self,
        symbol: str,
        type: str,
        amount: float,
        price: float,
        side: str,
        *,
        params: Optional[obcmccex.ParamsDict] = None,
    ) -> obcmccex.CcxtOrderStructure:
        # Reduce only orders are called to flatten CCXT account due to which
        # there is only 1 order per symbol.
        # The positions are closed via reduce-only orders of the opposite
        # side of the current position, with larger order amount.
        # E.g. for a position of `"BTC/USDT": -0.1`, a reduce-only order of "BTC/USDT": 0.1" is placed.
        order = self._reduce_only_ccxt_orders[symbol].pop(0)
        return order

    def load_markets(self) -> obcmccex.CcxtOrderStructure:
        """
        Load information about exchange markets at the time of experiment.
        """
        return self._exchange_markets[0]

    def fetch_leverage_tiers(
        self, symbols: List[str]
    ) -> obcmccex.CcxtOrderStructure:
        """
        Load exchange leverage information at the time of experiment.
        """
        return self._leverage_info[0]

    async def cancel_all_orders(self, pair: str) -> None:
        """
        Dummy function to cancel all orders of the provided pairs.
        """

    async def fetch_order(
        self,
        id: str,
        symbol: str,
    ) -> obcmccex.CcxtOrderStructure:
        """
        Fetch the last fill order with the given id from logs.
        """
        requested_order = None
        orders = self._ccxt_fills[symbol]
        for order in orders:
            if order["id"] == id:
                requested_order = order
                if requested_order["info"]["status"] == "FILLED":
                    quantity = float(requested_order["info"]["executedQty"])
                    quantity = -quantity if order["info"]["side"] == "SELL" else quantity
                    self._update_position(symbol, quantity)
                if symbol in self._ccxt_filled:
                    self._ccxt_filled[symbol].append(requested_order)
                else:
                    self._ccxt_filled[symbol] = [requested_order]
        return requested_order

    async def fetch_orders(
        self,
        symbol: str,
        *,
        limit: Optional[int] = None,
    ) -> List[obcmccex.CcxtOrderStructure]:
        """
        Fetch all filled orders of the requested symbol from logs.

        :param limit: maximum number of orders requested.
        """
        orders = self._ccxt_filled[symbol][:limit]
        return orders

    async def fetchMyTrades(
        self,
        symbol: str,
        limit: float,
    ) -> List[obcmccex.CcxtOrderStructure]:
        """
        Fetch trades from logs.
        """
        # The method generates trade information that offers a glimpse into the
        # future, but the broker's algorithm ensures that only the desired
        # trades with correct CCXT id are selected. Duplicating this selection
        # logic here would be redundant because it's already embedded within the
        # broker.
        trades = self._ccxt_trades[symbol]
        return trades

    def fetchBalance(self) -> Dict[str, Any]:
        """
        Fetch the current balance of the account.
        """
        # TODO(Sameep): Update it to choose using the earliest timestamp.
        # Update after CmTask5711 starts working.
        balance = self._balances.pop(0)
        return balance

    @staticmethod
    def _get_dictionary_from_list(
        input_list_dict: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Map list of dicts to a dict of key value pairs, where key is a symbol
        and value is a list of input dicts where "symbol" equals the dict key.

        This helper method avoids passing through the entire input list upon
        each call to `create_order` and other related methods.

        :param input_list_dict: List of dicts that need to be processed.
        :return: Processed dict.
        """
        result_dict = {}
        for item in input_list_dict:
            symbol = item["symbol"]
            if symbol in result_dict:
                result_dict[symbol].append(item)
            else:
                result_dict[symbol] = [item]
        return result_dict
