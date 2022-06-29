"""
An implementation of broker class for CCXT.

Import as:

import oms.ccxt_broker as occxbrok
"""

import logging
from typing import Any, Dict, List, Optional

import ccxt
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hsecrets as hsecret
import im_v2.common.universe.full_symbol as imvcufusy
import im_v2.common.universe.universe as imvcounun
import im_v2.common.universe.universe_utils as imvcuunut
import oms.broker as ombroker
import oms.order as omorder

_LOG = logging.getLogger(__name__)


class CcxtBroker(ombroker.Broker):
    def __init__(
        self,
        exchange_id: str,
        universe_version: str,
        mode: str,
        portfolio_id: str,
        contract_type: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        """
        Constructor.

        :param exchange: name of the exchange to initialize the broker for
        :param universe_version: version of the universe to use
        :param mode: supported values: "test", "prod", if "test", launches the broker
         in sandbox environment (not supported for every exchange),
         if "prod" launches with production API.
        :param contract_type: "spot" or "futures"
        """
        hdbg.dassert_in(mode, ["prod", "test"])
        hdbg.dassert_in(contract_type, ["spot", "futures"])
        self._mode = mode
        self._exchange_id = exchange_id
        self._contract_type = contract_type
        self._exchange = self._log_into_exchange()
        self._assert_order_methods_presence()
        # Enable mapping back from asset ids when placing orders.
        self._asset_id_to_symbol_mapping = self._build_asset_id_to_symbol_mapping(
            universe_version
        )
        # Will be used to determine timestamp since when to fetch orders.
        self.last_order_execution_ts: Optional[pd.Timestamp] = None
        # TODO(Juraj): not sure how to generalize this coinbasepro-specific parameter.
        self._portfolio_id = portfolio_id

    def get_fills(
        self, sent_orders: List[omorder.Order] = None
    ) -> List[ombroker.Fill]:
        """
        Return list of fills from the last order execution.

        :param sent_orders: a list of orders submitted by Broker
        :return: a list of filled orders
        """
        fills: List[ombroker.Fill] = []
        order_symbols = set(
            [
                self._asset_id_to_symbol_mapping[order.asset_id]
                for order in sent_orders
            ]
        )
        if self.last_order_execution_ts:
            # Load orders for each given symbol.
            for symbol in order_symbols:
                _LOG.info("Inside get_fills")
                orders = self._exchange.fetch_orders(
                    since=hdateti.convert_timestamp_to_unix_epoch(
                        self.last_order_execution_ts,
                    ),
                    symbol=symbol,
                )
                # Select closed orders.
                for order in orders:
                    if order["status"] == "closed":
                        # Select order matching to CCXT exchange id.
                        filled_order = [
                            order
                            for sent_order in sent_orders
                            if sent_order.ccxt_id == order["id"]
                        ][0]
                        # Create a Fill object.
                        fill = ombroker.Fill(
                            filled_order,
                            hdateti.convert_unix_epoch_to_timestamp(
                                order["timestamp"]
                            ),
                            num_shares=order["amount"],
                            price=order["price"],
                        )
                        fills.append(fill)
        return fills

    def _assert_order_methods_presence(self) -> None:
        """
        Assert that the requested exchange supports all methods necessary to
        make placing/fetching orders possible.
        """
        methods = ["createOrder", "fetchClosedOrders"]
        abort = False
        for method in methods:
            if not self._exchange.has[method]:
                _LOG.error(
                    "Method %s is unsupported for %s.", method, self._exchange_id
                )
                abort = True
        if abort:
            raise ValueError(
                f"The {self._exchange_id} exchange is not fully supported for placing orders."
            )

    async def _submit_orders(
        self,
        orders: List[omorder.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool,
    ) -> List[omorder.Order]:
        """
        Submit orders.
        """
        self.last_order_execution_ts = pd.Timestamp.now()
        sent_orders: List[str] = []
        for order in orders:
            # TODO(Juraj): perform bunch of assertions for order attributes.
            symbol = self._asset_id_to_symbol_mapping[order.asset_id]
            side = "buy" if order.diff_num_shares > 0 else "sell"
            order_resp = self._exchange.createOrder(
                symbol=symbol,
                type=order.type_,
                side=side,
                amount=abs(order.diff_num_shares),
                # id = order.order_id,
                # id=order.order_id,
                # TODO(Juraj): maybe it is possible to somehow abstract this to a general behavior
                # but most likely the method will need to be overriden per each exchange
                # to accomodate endpoint specific behavior.
                params={
                    "portfolio_id": self._portfolio_id,
                    "client_oid": order.order_id,
                },
            )
            order.ccxt_id = order_resp["id"]
            sent_orders.append(order)
            _LOG.info(order_resp)
        return sent_orders

    def _build_asset_id_to_symbol_mapping(
        self, universe_version: str
    ) -> Dict[int, str]:
        """
        Build asset id to full symbol mapping.
        """
        # Get full symbol universe.
        # TODO(Danya): Change mode to "trade".
        full_symbol_universe = imvcounun.get_vendor_universe(
            "CCXT", "trade", version=universe_version, as_full_symbol=True
        )
        # Filter symbols of the exchange corresponding to this instance.
        full_symbol_universe = list(
            filter(
                lambda s: s.startswith(self._exchange_id), full_symbol_universe
            )
        )
        # Build mapping.
        asset_id_to_full_symbol_mapping = (
            imvcuunut.build_numerical_to_string_id_mapping(full_symbol_universe)
        )
        # Change mapped values to be symbol only (more convevient when placing orders)
        asset_id_to_symbol_mapping = {
            id_: imvcufusy.parse_full_symbol(fs)[1].replace("_", "/")
            for id_, fs in asset_id_to_full_symbol_mapping.items()
        }
        return asset_id_to_symbol_mapping

    async def _wait_for_accepted_orders(
        self,
        file_name: str,
    ) -> None:
        _ = file_name

    def _log_into_exchange(self) -> ccxt.Exchange:
        """
        Log into coinbasepro and return the corresponding `ccxt.Exchange`
        object.
        """
        # Select credentials for provided exchange.
        if self._mode == "test":
            secrets_id = self._exchange_id + "_sandbox"
        else:
            secrets_id = self._exchange_id
        exchange_params = hsecret.get_secret(secrets_id)
        # Enable rate limit.
        exchange_params["rateLimit"] = True
        # Log into futures/spot market.
        if self._contract_type == "futures":
            exchange_params["options"] = {"defaultType": "future"}
        # Create a CCXT Exchange class object.
        ccxt_exchange = getattr(ccxt, self._exchange_id)
        exchange = ccxt_exchange(exchange_params)
        if self._mode == "test":
            exchange.set_sandbox_mode(True)
            _LOG.warning("Running in sandbox mode")
        hdbg.dassert(
            exchange.checkRequiredCredentials(),
            msg="Required credentials not passed",
        )
        return exchange
