"""
An abstract base class CCXT broker.

Import as:

import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
"""

import abc
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import ccxt
import ccxt.pro as ccxtpro
import nest_asyncio
import numpy as np
import pandas as pd

import dev_scripts.git.git_hooks.utils as dsgghout
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hretry as hretry
import im_v2.ccxt.utils as imv2ccuti
import im_v2.common.data.client as icdc
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe as ivcu
import oms.broker.broker as obrobrok
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.fill as omfill
import oms.hsecrets as omssec
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)

# Max number of order submission retries.
_MAX_EXCHANGE_REQUEST_RETRIES = 1

# Sleep time in sec between request retries.
_REQUEST_RETRY_SLEEP_TIME_IN_SEC = 0.5

CcxtData = Dict[str, Any]

# Added because of "RuntimeError: This event loop is already running"
# https://stackoverflow.com/questions/46827007/runtimeerror-this-event-loop-is-already-running-in-python
# TODO(gp): Investigate if it's a limitation of `asyncio` or a "design error" on our
# side.
nest_asyncio.apply()


# #############################################################################
# AbstractCcxtBroker
# #############################################################################


class AbstractCcxtBroker(obrobrok.Broker):
    def __init__(
        self,
        *args: Any,
        exchange_id: str,
        account_type: str,
        portfolio_id: str,
        contract_type: str,
        secret_identifier: omssec.SecretIdentifier,
        logger: obcccclo.CcxtLogger,
        sync_exchange: ccxt.Exchange,
        async_exchange: ccxtpro.Exchange,
        # TODO(Grisha): consider passing StichedMarketData with OHLCV and bid /
        #  ask data instead of passing `market_data` and `bid_ask_im_client`
        #  separately.
        bid_ask_im_client: Optional[icdc.ImClient] = None,
        max_order_submit_retries: Optional[int] = _MAX_EXCHANGE_REQUEST_RETRIES,
        bid_ask_raw_data_reader: Optional[imvcdcimrdc.RawDataReader] = None,
        bid_ask_lookback: str = "60S",
        sanity_check_cached_open_positions: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Constructor.

        :param exchange_id: name of the exchange to initialize the broker for
            (e.g., Binance)
        :param account_type:
            - "trading" launches the broker in trading environment
            - "sandbox" launches the broker in sandbox environment (not supported
               for every exchange)
        :param contract_type: "spot" or "futures"
        :param secret_identifier: a SecretIdentifier holding a full name of secret
            to look for in AWS SecretsManager
        :param logger: CcxtLogger object
        :param bid_ask_im_client: ImClient that reads bid / ask data
            (required to calculate price for limit orders)
        :param max_order_submit_retries: maximum number of attempts to submit
            an order if the first try is unsuccessful
        :param bid_ask_lookback: lookback period in pd.Timedelta-compatible string format, e.g. '10S'
        :param sanity_check_cached_open_positions: compare cached open
            positions to the current value and raise if there is a mismatch
        :param *args: `obrobrok.Broker` positional arguments
        :param **kwargs: `obrobrok.Broker` keyword arguments
        """
        super().__init__(*args, **kwargs)
        if not self._log_dir:
            _LOG.warning(
                "No logging directory is provided, so not saving orders or fills."
            )
        # TODO(Juraj): This is a nasty hack, address properlly in #CmTask7688
        global _MAX_EXCHANGE_REQUEST_RETRIES
        _MAX_EXCHANGE_REQUEST_RETRIES = max_order_submit_retries
        self._max_exchange_request_retries = max_order_submit_retries
        self._exchange_id = exchange_id
        #
        hdbg.dassert_in(account_type, ["trading", "sandbox"])
        self._account_type = account_type
        #
        self._secret_identifier = secret_identifier
        _LOG.warning("Using secret_identifier=%s", secret_identifier)
        self._portfolio_id = portfolio_id
        #
        hdbg.dassert_in(contract_type, ["spot", "futures", "swap"])
        self._contract_type = contract_type
        # Map from asset ids to CCXT symbols and vice versa (e.g., when placing
        # orders).
        self.asset_id_to_ccxt_symbol_mapping = (
            self._build_asset_id_to_ccxt_symbol_mapping()
        )
        self.ccxt_symbol_to_asset_id_mapping = {
            symbol: asset
            for asset, symbol in self.asset_id_to_ccxt_symbol_mapping.items()
        }
        self._sync_exchange = sync_exchange
        self._async_exchange = async_exchange
        # TODO(Sameep): disabled as part of CMTask5310.
        # self.fees = self._get_trading_fee_info()
        self.fees = {}
        # Positions on the exchange currently opened by the broker instance.
        # See docstring for `get_open_positions()`.
        # This variable is:
        # - is a cached version of the positions tracked by the exchange
        # - is set to `None` and invalidated, when orders are submitted, since we have to query the exchange
        # - should not be accessed directly, but only through `get_open_positions()`
        # - is updated by `get_open_positions()` which queries the exchange
        self._cached_open_positions: Optional[Dict[str, float]] = None
        # If this parameter is enabled, the cached value is compared to the
        # live value. Enabling this will lead to slower performance due to
        # additional exchange requests.
        self._sanity_check_cached_open_positions = (
            sanity_check_cached_open_positions
        )
        # Store the timestamp and parent orders in the previous execution.
        # Initially the orders are empty.
        self.previous_parent_orders_timestamp: Optional[pd.Timestamp] = None
        self._previous_parent_orders: Optional[List[oordorde.Order]] = None
        # Initialize the logger.
        self._logger = logger
        # Get info about the market.
        self.market_info = self._get_market_info()
        # Initialize ImClient with bid / ask data if it is provided.
        self._bid_ask_im_client = bid_ask_im_client
        # TODO(Sameep): CMTask5014.
        # if self._bid_ask_im_client is not None:
        # Initialize MarketData with bid / ask data to calculate limit price.
        # TODO(Sameep): disabled as part of CMTask5310.
        # self._bid_ask_market_data = self._get_bid_ask_real_time_market_data()
        self._bid_ask_raw_data_reader = bid_ask_raw_data_reader
        if self._bid_ask_raw_data_reader is None:
            _LOG.info(
                "This broker instance does not connect to IM database, \
                only basic exchange calls (i.e. get_total_balance) \
                    are supported."
            )
        self.bid_ask_lookback = bid_ask_lookback
        leverage = 1
        self._set_leverage_for_all_symbols(leverage)

    # ////////////////////////////////////////////////////////////////////////

    # TODO(Danya): The name of the method indicates string return value,
    # while actually it's a dict. The reason is CMTask6283. Once the task is
    # finished, the method will be separated into a string representation
    # for printing and a JSON representation for logging, for now this includes
    # only the Logger representation.
    def get_broker_config(self) -> Dict[str, Any]:
        """
        Return a representation of Broker config attributes.

        Config includes attributes relevant for execution analysis.

        Example of the output:
        ```
        {
        'universe_version': 'v7.4',
        'stage': 'prod',
        'log_dir': '/app/system_log_dir',
        'secret_identifier': 'binance.prod.trading.4',
        'bid_ask_lookback': '60S',
        'limit_price_computer': {'object_type': 'LimitPriceComputerUsingVolatility',
        '_volatility_multiple': [0.75, 0.7, 0.6, 0.8, 1.0]},
        'child_order_quantity_computer': {'object_type': 'DynamicSchedulingChildOrderQuantityComputer'},
        'raw_data_reader': 'RawDataReader'
        }
        ```
        """
        broker_config = {}
        # Get single string/int attributes.
        #
        # Get `oms.Broker` attributes.
        broker_config["universe_version"] = self._universe_version
        broker_config["stage"] = self.stage
        broker_config["log_dir"] = self._log_dir
        # Get `AbstractCcxtBroker` attributes.
        broker_config["secret_identifier"] = str(self._secret_identifier)
        broker_config["bid_ask_lookback"] = self.bid_ask_lookback
        #
        # Get complex object attributes.
        #
        # Get `oms.Broker` attributes.
        if self._limit_price_computer is not None:
            broker_config[
                "limit_price_computer"
            ] = self._limit_price_computer.to_dict()
        #
        if self._child_order_quantity_computer is not None:
            broker_config[
                "child_order_quantity_computer"
            ] = self._child_order_quantity_computer.to_dict()
        # Get `AbstractCcxttBroker` attributes.
        if self._bid_ask_raw_data_reader is not None:
            broker_config[
                "raw_data_reader"
            ] = self._bid_ask_raw_data_reader.__class__.__name__
        return broker_config

    # ////////////////////////////////////////////////////////////////////////

    def get_bid_ask_data_for_last_period(self) -> pd.DataFrame:
        """
        Get raw bid/ask data for the given last period.

        :return: bid/ask data for given period.
            Example of the output DataFrame (levels 3-10 omitted for readability):

            ```
                                             currency_pair exchange_id           end_download_timestamp              knowledge_timestamp  bid_size_l1  bid_size_l2  ... bid_price_l1  bid_price_l2   ...  ask_size_l1  ask_size_l2  ...  ask_price_l1  ask_price_l2 ...   ccxt_symbols    asset_id
            timestamp
            2023-08-11 12:49:52.835000+00:00      GMT_USDT     binance 2023-08-11 12:49:52.975836+00:00 2023-08-11 12:49:53.205151+00:00      38688.0     279499.0  ...        0.2033        0.2032  ...     232214.0     244995.0  ...       0.2034        0.2035  ...  GMT/USDT:USDT  1030828978
            2023-08-11 12:49:52.835000+00:00      GMT_USDT     binance 2023-08-11 12:49:53.482785+00:00 2023-08-11 12:49:55.324804+00:00      38688.0     279499.0  ...        0.2033        0.2032  ...     232214.0     244995.0  ...       0.2034        0.2035  ...  GMT/USDT:USDT  1030828978
            2023-08-11 12:49:52.845000+00:00      SOL_USDT     binance 2023-08-11 12:49:52.979713+00:00 2023-08-11 12:49:53.205151+00:00        258.0        467.0  ...       24.4110       24.4100  ...        629.0        151.0  ...       24.4120       24.4130 ...  SOL/USDT:USDT  2237530510
            ```
        """
        # Get the first and last timestamp of the period.
        end_timestamp = pd.Timestamp.utcnow()
        start_timestamp = end_timestamp - pd.Timedelta(self.bid_ask_lookback)
        # Load raw data.
        bid_ask_data = self._bid_ask_raw_data_reader.load_db_table(
            start_timestamp,
            end_timestamp,
            bid_ask_levels=[1],
            # At this point we drop fully duplicated data entries.
            deduplicate=True,
            subset=[
                "timestamp",
                "currency_pair",
                "bid_price",
                "bid_size",
                "ask_price",
                "ask_size",
                "level",
            ],
        )
        self._logger.log_bid_ask_data(self._get_wall_clock_time, bid_ask_data)
        # Drop duplicates from the bid/ask data.
        # TODO(Grisha): pass `max_num_dups` via SystemConfig["broker_config"].
        bid_ask_data, _ = obccccut.drop_bid_ask_duplicates(bid_ask_data, max_num_dups=10)
        # Filter loaded data to only the broker's universe symbols.
        # Convert currency pairs to full CCXT symbol format, e.g. 'BTC_USDT' ->
        # 'BTC/USDT:USDT'
        bid_ask_data["ccxt_symbols"] = bid_ask_data["currency_pair"].apply(
            imv2ccuti.convert_currency_pair_to_ccxt_format,
            args=(self._exchange_id, self._contract_type),
        )
        # Map CCXT symbols to asset IDs.
        bid_ask_data = bid_ask_data.loc[
            bid_ask_data["ccxt_symbols"].isin(
                self.ccxt_symbol_to_asset_id_mapping
            )
        ]
        bid_ask_data["asset_id"] = bid_ask_data["ccxt_symbols"].apply(
            lambda x: self.ccxt_symbol_to_asset_id_mapping[x]
        )
        # When creating a set from a dictionary, only the keys are included
        # in the set by default.
        hdbg.dassert_set_eq(
            self.ccxt_symbol_to_asset_id_mapping,
            bid_ask_data["ccxt_symbols"],
            "Bid/Ask data is missing symbols",
        )
        # Convert original index from unix epoch to Timestamp, e.g.
        # 1691758182667 ->
        #   pd.Timestamp('2023-08-11 12:50:01.987000+0000', tz='UTC')
        bid_ask_data.index = bid_ask_data.index.to_series().apply(
            lambda x: hdateti.convert_unix_epoch_to_timestamp(x)
        )
        bid_ask_data = bid_ask_data.sort_index()
        return bid_ask_data

    # ////////////////////////////////////////////////////////////////////////

    # TODO(gp): Can it be private?
    @hretry.async_retry(
        # We cannot use `self` in the decorator and thus we use constants.
        num_attempts=_MAX_EXCHANGE_REQUEST_RETRIES,
        exceptions=(ccxt.NetworkError, ccxt.RequestTimeout),
        retry_delay_in_sec=_REQUEST_RETRY_SLEEP_TIME_IN_SEC,
    )
    async def get_fills_for_order(self, order: oordorde.Order) -> omfill.Fill:
        """
        Return fill for a parent order.

        :param order: parent order to fetch fills for.
        """
        _LOG.debug("Getting fills for order=%s", str(order))
        asset_id = order.asset_id
        order_id = order.order_id
        symbol = self.asset_id_to_ccxt_symbol_mapping[asset_id]
        # Get CCXT ID of the children orders corresponding to the parent
        # order.
        child_order_ccxt_ids = order.extra_params.get("ccxt_id", [])
        _LOG.info(hprint.to_str("child_order_ccxt_ids"))
        hdbg.dassert_isinstance(child_order_ccxt_ids, list)
        if not child_order_ccxt_ids:
            # If no child orders were accepted, consider `Fill` to be empty.
            _LOG.info(
                "No child orders found for parent order_id=%s",
                order_id,
            )
            return
        # The CCXT method `fetch_orders()` can filter by time range and order ID,
        # however:
        # - OMS `get_fills()` method currently does not take a time range
        # - only one order ID is accepted by CCXT and querying for all the order
        #   IDs takes too long
        # Our current solution is to fetch the latest 500 orders for the single
        # parent order symbol using CCXT `fetch_orders()`.
        # TODO(Danya): There is a problem if we submit more than 500 child
        #  orders in a single interval. Think about how to remove this limitation.
        child_orders = await self._async_exchange.fetch_orders(
            symbol=symbol, limit=500
        )
        # Filter child orders corresponding to this parent order.
        child_orders = [
            child_order
            for child_order in child_orders
            if int(child_order["id"]) in child_order_ccxt_ids
        ]
        _LOG.debug(hprint.to_str("child_orders"))
        # Calculate fill amount based on child orders.
        (
            order_fill_signed_num_shares,
            order_price,
        ) = obccccut.roll_up_child_order_fills_into_parent(order, child_orders)
        # Skip the parent order if it has not been filled at all.
        if order_fill_signed_num_shares == 0:
            _LOG.info(
                "Empty fill for parent order: %s",
                hprint.to_str("order child_orders"),
            )
            return
        # Compute the timestamp for the `oms.Fill` as the latest child order
        # update time.
        # `updateTime` in CCXT data structure is the time of the latest trade
        # for the given order, or the datetime of order submission if no
        # trades were conducted.
        fill_timestamp = max(
            int(child_order["info"]["updateTime"]) for child_order in child_orders
        )
        fill_timestamp = hdateti.convert_unix_epoch_to_timestamp(fill_timestamp)
        # Create a `oms.Fill` object.
        hdateti.dassert_has_UTC_tz(fill_timestamp)
        fill = omfill.Fill(
            order,
            fill_timestamp,
            order_fill_signed_num_shares,
            order_price,
        )
        _LOG.info("fill=%s", str(fill))
        return fill

    # ////////////////////////////////////////////////////////////////////////

    # TODO(Sonaal): Temporary fix for converting all the sync calls of 'get_fills'
    # to async. This is the sync method for `get_fills`, check Cmamp5842,
    # Cmamp5583.
    async def get_fills_async(self) -> List[omfill.Fill]:
        """
        Same interface as get_fills() but uses async semantic instead of sync
        one.
        """
        fills: List[omfill.Fill] = []
        # Get all parent orders sent to the `oms.Broker` in the previous
        # execution: each order passed to the Broker is considered a parent order.
        # Each parent order may correspond to 1 or more CCXT orders, and each
        # CCXT order is assigned an ID by the exchange if the submission was
        # successful.
        # - In case of market orders, one parent order corresponds to one
        #   "child" order
        # - In case of TWAP orders, one parent order corresponds to multiple child
        #   orders with separate CCXT IDs
        submitted_parent_orders = self._previous_parent_orders
        if submitted_parent_orders is None:
            _LOG.info(
                "No parent orders sent in the previous execution: "
                "returning no fills"
            )
            return fills
        if self.previous_parent_orders_timestamp is None:
            # If there was no parent order in previous execution, then there is
            # no fill.
            _LOG.info("No last order execution timestamp: returning no fills")
            return fills
        # Get asset ids for the (parent) orders sent in previous execution.
        asset_ids = [oms_order.asset_id for oms_order in submitted_parent_orders]
        _LOG.info(hprint.to_str("asset_ids"))
        hdbg.dassert_lt(0, len(asset_ids))
        get_fills_tasks = [
            self.get_fills_for_order(parent_order)
            for parent_order in submitted_parent_orders
        ]
        fills = await asyncio.gather(*get_fills_tasks)
        fills = [fill for fill in fills if fill is not None]
        return fills

    def get_fills(self) -> List[omfill.Fill]:
        """
        Return list of fills from the previous order execution.

        This is used by Portfolio to update its state given the fills.

        In case of child-less parent orders (e.g., market orders) we
        should return fills corresponding to the parent orders directly.
        In case of child orders (e.g., TWAP order) we need to roll up
        the fills for the children orders into corresponding fills for
        the parent orders.

        :return: list of OMS fills
        """
        fills = asyncio.get_running_loop().run_until_complete(
            self.get_fills_async()
        )
        return fills

    # ////////////////////////////////////////////////////////////////////////

    async def get_ccxt_trades(
        self,
        ccxt_orders: List[CcxtData],
    ) -> List[CcxtData]:
        """
        Get CCXT trades corresponding to passed CCXT orders.

        Each CCXT order can be associated with 0, 1 or more trades/fills.

        The binance endpoint used is:
        https://binance-docs.github.io/apidocs/futures/en/#position-information-v2-user_data

        :param ccxt_orders: CCXT orders to load trades for
        :return: list of dicts with trades in the format described in
            https://docs.ccxt.com/#/?id=trade-structure
        """
        # Map currency symbols to the passed CCXT orders.
        symbol_to_order_mapping: Dict[str, List[CcxtData]] = {}
        for order in ccxt_orders:
            symbol = order["symbol"]
            if symbol in symbol_to_order_mapping:
                symbol_to_order_mapping[symbol].append(order)
            else:
                symbol_to_order_mapping[symbol] = [order]
        # Get trades for each symbol provided in the list of orders.
        # The trades are loaded for each symbol separately and then filtered
        # to leave only those corresponding to provided CCXT orders.
        tasks = [
            self._get_ccxt_trades_for_one_symbol(orders)
            for _, orders in symbol_to_order_mapping.items()
        ]
        trades = await asyncio.gather(*tasks)
        # Each task returns a list of trades, flatten it via list comprehension.
        trades = [trade for symbol_trades in trades for trade in symbol_trades]
        _LOG.info(
            "CCXT trades loaded timestamp=%s",
            self.market_data.get_wall_clock_time(),
        )
        return trades

    @hretry.sync_retry(
        num_attempts=_MAX_EXCHANGE_REQUEST_RETRIES,
        exceptions=(ccxt.NetworkError, ccxt.RequestTimeout),
        retry_delay_in_sec=_REQUEST_RETRY_SLEEP_TIME_IN_SEC,
    )
    def get_open_positions(self) -> Dict[str, float]:
        """
        Load all the open positions (with non-zero amount) from the exchange.

        If the open positions have already been loaded, returns the cached value
        of `self._cached_open_positions`.

        :return: open positions in the format like:
            ```
            {
                "BTC/USDT": 0.001,
                "ETH/USDT": 10
            }
            ```
        """
        if self._cached_open_positions is None:
            # If there are no cached positions, load them from the exchange.
            # We avoid doing this operation often, as it is time-expensive.
            open_positions = self._get_open_positions_from_exchange()
            self._cached_open_positions = open_positions
        else:
            if self._sanity_check_cached_open_positions:
                # Compare cached value to the live value.
                _LOG.warning(
                    "sanity_check_cached_open_positions enabled: checking cache vs actual value"
                )
                exchange_open_positions = self._get_open_positions_from_exchange()
                hdbg.dassert_eq(open_positions, exchange_open_positions)
            # Return cached value.
            open_positions = self._cached_open_positions
        _LOG.info(hprint.to_str("open_positions"))
        return open_positions

    @hretry.async_retry(
        num_attempts=_MAX_EXCHANGE_REQUEST_RETRIES,
        exceptions=(ccxt.NetworkError, ccxt.RequestTimeout),
        retry_delay_in_sec=_REQUEST_RETRY_SLEEP_TIME_IN_SEC,
    )
    async def cancel_open_orders_for_symbols(
        self, currency_pairs: List[str]
    ) -> None:
        """
        Cancel all open orders for a given list of symbols.

        :param: currency_pairs: pairs to cancer all orders for
        """
        # Binance does not allow cancelling open orders for all symbols in one API call.
        tasks = [
            self._async_exchange.cancel_all_orders(pair)
            for pair in currency_pairs
        ]
        await asyncio.gather(*tasks)

    def cancel_open_orders(self, currency_pair: str) -> None:
        """
        Cancel all the open orders for the given currency pair.
        """
        self._sync_exchange.cancel_all_orders(currency_pair)

    def get_total_balance(self) -> Dict[str, float]:
        """
        Fetch total available balance from the exchange through CCXT.

        :return: total balance, e.g., ``` { 'BNB': 0.0, 'USDT':
            5026.22494667, 'BUSD': 1000.10001 } ```
        """
        # Fetch the balance data.
        hdbg.dassert(self._sync_exchange.has["fetchBalance"])
        balance = self._sync_exchange.fetchBalance()
        # Log the current balance.
        self._logger.log_balance(self._get_wall_clock_time, balance)
        # Select total balance.
        total_balance = balance["total"]
        # Verify the type of the return value is valid.
        hdbg.dassert_type_is(total_balance, dict)
        for k, v in total_balance.items():
            hdbg.dassert_type_is(k, str)
            hdbg.dassert_type_is(v, float)
        return total_balance

    # TODO(gp): -> _calculate_limit_price since loading data is just a side
    #  effect and it's used only here.
    def load_bid_ask_and_calculate_limit_price(
        self,
        asset_id: int,
        side: str,
    ) -> float:
        """
        Calculate limit price for an order for `asset_id` and `side`.
        """
        # Get bid/ask data.
        bid_ask_data = self.get_bid_ask_data_for_last_period()
        # Filter data on asset_id.
        bid_ask_data = bid_ask_data[bid_ask_data["asset_id"] == asset_id]
        # Calculate limit price.
        # Note: since this method is used for market order price calculation,
        # which does not have the execution frequency, we use the default
        # value identical to bid/ask lookback.
        # This is a temporary measure until the execution frequency
        # is passed as an order attribute.
        execution_freq = self.bid_ask_lookback
        price_dict = self._get_limit_price_dict(
            bid_ask_data,
            side,
            self.market_info[asset_id]["price_precision"],
            execution_freq,
        )
        limit_price = price_dict["limit_price"]
        return limit_price

    # ////////////////////////////////////////////////////////////////////////////

    # TODO(gp): Consider moving all this chunk of code in utils since it has a
    #  consistent interface.
    @staticmethod
    def _get_ccxt_id_from_child_order(order: oordorde.Order) -> int:
        """
        Get `ccxt_id` from an `Order` object.

        CCXT ID is assigned by the exchange in case of successful order
        submission, or assigned a default value of `-1` if the exchange
        could not accept the order for some reason. CCXT ID is not
        present if and only if the order submission was not attempted
        yet.

        :param order: order to retrieve CCXT ID from
        :return: CCXT ID value
        """
        # The ID is stored as a list since by default one parent order can
        # correspond to multiple CCXT child orders (e.g., in a TWAP execution).
        hdbg.dassert_in("ccxt_id", order.extra_params)
        hdbg.dassert_isinstance(order.extra_params["ccxt_id"], list)
        hdbg.dassert_eq(len(order.extra_params["ccxt_id"]), 1)
        ccxt_id = order.extra_params["ccxt_id"][0]
        hdbg.dassert_isinstance(ccxt_id, int)
        if ccxt_id == -1:
            # `ccxt_id` equal to -1 is possible if the order submission has been
            # tried, but was not accepted by the exchange. In this case, a
            # corresponding error should be logged in order extra params.
            hdbg.dassert_in("error_msg", order.extra_params)
        return ccxt_id

    # TODO(gp): Why is ccxt int or str and not one type?
    @staticmethod
    def _set_ccxt_id_to_child_order(
        order: oordorde.Order, ccxt_id: Union[int, str]
    ) -> oordorde.Order:
        """
        Set the `ccxt_id` order for an Order.
        """
        # By default, in a TWAP execution context a single OMS parent order may
        # correspond to multiple CCXT order IDs.
        if isinstance(ccxt_id, str):
            # Check whether the ID is a numerical string.
            try:
                ccxt_id = [int(ccxt_id)]
            except ValueError:
                raise ValueError(f"Can't convert CCXT ID `{ccxt_id}` to integer")
        elif isinstance(ccxt_id, int):
            ccxt_id = [ccxt_id]
        else:
            raise ValueError(
                f"Invalid type for CCXT ID: `{type(ccxt_id)}` (must be int or str)"
            )
        order.extra_params["ccxt_id"] = ccxt_id
        return order

    # ////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _update_stats_for_order(
        order: oordorde.Order,
        tag: str,
        value: Any,
        *,
        prefix: Optional[str] = None,
    ) -> None:
        """
        Helper to update the stats on an Order execution in the extra params.

        :param order: Order object to update
        :param tag: tag representing the specific stat to update (e.g., start)
        :param value: value to update the stat with
        :param prefix: a prefix to add to the tag (e.g., "submit_twap_orders")
            - If not provided, the name of the calling function is used
        """
        if prefix is None:
            # Get the name of the calling function if no prefix was suggested.
            prefix = dsgghout.get_function_name(count=1)
        # Construct the full tag, e.g., "start" -> "submit_twap_orders::start".
        tag = f"{prefix}::{tag}"
        _LOG.debug("order=%s tag=%s value=%s", str(order), tag, value)
        # Assign the value.
        if "stats" not in order.extra_params:
            order.extra_params["stats"] = {}
        order_stats = order.extra_params["stats"]
        hdbg.dassert_not_in(tag, order_stats)
        order_stats[tag] = value

    # TODO(gp): Inline this!
    @staticmethod
    def _is_child_order_shares_correct(
        child_order_diff_num_shares: float,
    ) -> bool:
        """
        Verify that the child order amount is correct.

        :param child_order_diff_num_shares: `diff_num_shares`
          value of the child order.
        """
        # TODO(Danya): Add a check for meeting the notional limit.
        is_correct = child_order_diff_num_shares == 0
        return is_correct

    def _get_open_positions_from_exchange(self):
        """
        Load open positions from the exchange and return as dict.

        Implementation of `get_open_positions`.
        """
        positions = []
        # Fetch all the open positions. The response from the exchange looks like:
        # ```
        # [{'info': {'symbol': 'BTCUSDT',
        #            'positionAmt': '-0.200',
        #            'entryPrice': '23590.549',
        #            'markPrice': '23988.40000000',
        #            'unRealizedProfit': '-79.57020000',
        #            'liquidationPrice': '68370.47429432',
        #            'leverage': '20',
        #            'maxNotionalValue': '250000',
        #            'marginType': 'cross',
        #            'isolatedMargin': '0.00000000',
        #            'isAutoAddMargin': 'false',
        #            'positionSide': 'BOTH',
        #            'notional': '-4797.68000000',
        #            'isolatedWallet': '0',
        #            'updateTime': '1659028521933'},
        #   'symbol': 'BTC/USDT',
        #   'contracts': 0.2,
        #   'contractSize': 1.0,
        #   'unrealizedPnl': -79.5702,
        #   'leverage': 20.0,
        #   'liquidationPrice': 68370.47429432,
        #   'collateral': 9092.72600745,
        #   'notional': 4797.68,
        #   'markPrice': 23988.4,
        #   'entryPrice': 23590.549,
        #   'timestamp': 1659028521933,
        #   'initialMargin': 239.884,
        #   'initialMarginPercentage': 0.05,
        #   'maintenanceMargin': 47.9768,
        #   'maintenanceMarginPercentage': 0.01,
        #   'marginRatio': 0.0053,
        #   'datetime': '2022-07-28T17:15:21.933Z',
        #   'marginType': 'cross',
        #   'side': 'short',
        #   'hedged': False,
        #   'percentage': -33.17}]
        _LOG.info("No cached value for open positions: accessing exchange")
        positions = self._sync_exchange.fetch_positions()
        self._logger.log_positions(self._get_wall_clock_time, positions)
        # Map from symbol to the amount currently owned if different than zero,
        # e.g. `{'BTC/USDT': 0.01}`.
        open_positions: Dict[str, float] = {}
        for position in positions:
            # Get the quantity of assets on short/long positions.
            position_amount = float(position["info"]["positionAmt"])
            position_symbol = position["symbol"]
            if position_amount != 0:
                open_positions[position_symbol] = position_amount
        return open_positions

    # ////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    async def _submit_twap_orders(
        self,
        parent_orders: List[oordorde.Order],
        passivity_factor: float,
        *,
        execution_freq: Optional[str] = "1T",
    ) -> List[pd.DataFrame]:
        """
        Execute orders using the TWAP strategy.
        """
        ...

    # ////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # ////////////////////////////////////////////////////////////////////////////

    def _build_asset_id_to_ccxt_symbol_mapping(
        self,
    ) -> Dict[int, str]:
        """
        Build asset id to CCXT symbol mapping.

        This is an helper for the constructor.

        :return: mapping like:
            ```
            {
                1528092593: 'BAKE/USDT',
                8968126878: 'BNB/USDT',
                1182743717: 'BTC/BUSD',
            }
            ```
        """
        # Get full symbol universe.
        vendor = "CCXT"
        mode = "trade"
        full_symbol_universe = ivcu.get_vendor_universe(
            vendor, mode, version=self._universe_version, as_full_symbol=True
        )
        # Filter symbols of the exchange corresponding to this instance.
        exchange_symbol_universe = [
            s for s in full_symbol_universe if s.startswith(self._exchange_id)
        ]
        # Build asset_id -> symbol mapping.
        asset_id_to_full_symbol_mapping = (
            ivcu.build_numerical_to_string_id_mapping(exchange_symbol_universe)
        )
        asset_id_to_symbol_mapping: Dict[int, str] = {}
        for asset_id, symbol in asset_id_to_full_symbol_mapping.items():
            # Select currency pair.
            currency_pair = ivcu.parse_full_symbol(symbol)[1]
            # Transform to CCXT format, e.g. 'BTC_USDT' -> 'BTC/USDT'.
            ccxt_symbol = imv2ccuti.convert_currency_pair_to_ccxt_format(
                currency_pair, self._exchange_id, self._contract_type
            )
            asset_id_to_symbol_mapping[asset_id] = ccxt_symbol
        return asset_id_to_symbol_mapping

    def _get_market_info(self) -> Dict[int, Any]:
        """
        Load market information from the given exchange and map to asset ids.

        The following data is saved:
        - minimal order limits (notional and quantity)
        - asset quantity precision (for rounding of orders)
        - maximum allowed leverage for tier 0

        The numbers are determined by loading the market metadata from CCXT.
        """
        minimal_order_limits: Dict[int, Any] = {}
        symbols = list(self.ccxt_symbol_to_asset_id_mapping.keys())
        # Load market information from CCXT.
        exchange_markets = self._sync_exchange.load_markets()
        # Download leverage information. See more about the output format:
        # https://docs.ccxt.com/#/README?id=leverage-tiers-structure.
        leverage_info = self._sync_exchange.fetch_leverage_tiers(symbols)
        self._logger.log_exchange_markets(
            self._get_wall_clock_time, exchange_markets, leverage_info
        )
        _LOG.info(hprint.to_str("leverage_info"))
        for asset_id, symbol in self.asset_id_to_ccxt_symbol_mapping.items():
            minimal_order_limits[asset_id] = {}
            currency_market = exchange_markets[symbol]
            # Example:
            # {'active': True,
            # 'base': 'ADA',
            # 'baseId': 'ADA',
            # 'contract': True,
            # 'contractSize': 1.0,
            # 'delivery': False,
            # 'expiry': None,
            # 'expiryDatetime': None,
            # 'feeSide': 'get',
            # 'future': True,
            # 'id': 'ADAUSDT',
            # 'info': {'baseAsset': 'ADA',
            #         'baseAssetPrecision': '8',
            #         'contractType': 'PERPETUAL',
            #         'deliveryDate': '4133404800000',
            #         'filters': [{'filterType': 'PRICE_FILTER',
            #                     'maxPrice': '25.56420',
            #                     'minPrice': '0.01530',
            #                     'tickSize': '0.00010'},
            #                     {'filterType': 'LOT_SIZE',
            #                     'maxQty': '10000000',
            #                     'minQty': '1',
            #                     'stepSize': '1'},
            #                     {'filterType': 'MARKET_LOT_SIZE',
            #                     'maxQty': '10000000',
            #                     'minQty': '1',
            #                     'stepSize': '1'},
            #                     {'filterType': 'MAX_NUM_ORDERS', 'limit': '200'},
            #                     {'filterType': 'MAX_NUM_ALGO_ORDERS', 'limit': '10'},
            #                     {'filterType': 'MIN_NOTIONAL', 'notional': '10'},
            #                     {'filterType': 'PERCENT_PRICE',
            #                     'multiplierDecimal': '4',
            #                     'multiplierDown': '0.9000',
            #                     'multiplierUp': '1.1000'}],
            #         'liquidationFee': '0.020000',
            #         'maintMarginPercent': '2.5000',
            #         'marginAsset': 'USDT',
            #         'marketTakeBound': '0.10',
            #         'onboardDate': '1569398400000',
            #         'orderTypes': ['LIMIT',
            #                         'MARKET',
            #                         'STOP',
            #                         'STOP_MARKET',
            #                         'TAKE_PROFIT',
            #                         'TAKE_PROFIT_MARKET',
            #                         'TRAILING_STOP_MARKET'],
            #         'pair': 'ADAUSDT',
            #         'pricePrecision': '5',
            #         'quantityPrecision': '0',
            #         'quoteAsset': 'USDT',
            #         'quotePrecision': '8',
            #         'requiredMarginPercent': '5.0000',
            #         'settlePlan': '0',
            #         'status': 'TRADING',
            #         'symbol': 'ADAUSDT',
            #         'timeInForce': ['GTC', 'IOC', 'FOK', 'GTX'],
            #         'triggerProtect': '0.0500',
            #         'underlyingSubType': ['HOT'],
            #         'underlyingType': 'COIN'},
            # 'inverse': False,
            # 'limits': {'amount': {'max': 10000000.0, 'min': 1.0},
            #             'cost': {'max': None, 'min': 10.0},
            #             'leverage': {'max': None, 'min': None},
            #             'market': {'max': 10000000.0, 'min': 1.0},
            #             'price': {'max': 25.5642, 'min': 0.0153}},
            # 'linear': True,
            # 'lowercaseId': 'adausdt',
            # 'maker': 0.0002,
            # 'margin': False,
            # 'option': False,
            # 'optionType': None,
            # 'percentage': True,
            # 'precision': {'amount': 0, 'base': 8, 'price': 4, 'quote': 8},
            # 'quote': 'USDT',
            # 'quoteId': 'USDT',
            # 'settle': 'USDT',
            # 'settleId': 'USDT',
            # 'spot': False,
            # 'strike': None,
            # 'swap': True,
            # 'symbol': 'ADA/USDT',
            # 'taker': 0.0004,
            # 'tierBased': False,
            # 'type': 'future'}
            limits = currency_market["limits"]
            # Get the minimal amount of asset in the order.
            amount_limit = limits["amount"]["min"]
            minimal_order_limits[asset_id]["min_amount"] = amount_limit
            # Set the minimal cost of asset in the order.
            # The notional limit can differ between symbols and subject to
            # fluctuations, so it is set manually to 10.
            notional_limit = 10.0
            minimal_order_limits[asset_id]["min_cost"] = notional_limit
            # Set the rounding precision for amount of the asset.
            amount_precision = currency_market["precision"]["amount"]
            minimal_order_limits[asset_id]["amount_precision"] = amount_precision
            # Set the rounding precision for price of the asset.
            price_precision = currency_market["precision"]["price"]
            minimal_order_limits[asset_id]["price_precision"] = price_precision
            # Assume that all the positions belong to the lowest tier.
            tier_0_leverage_info = leverage_info[symbol][0]
            max_leverage_float = tier_0_leverage_info["maxLeverage"]
            try:
                # Convert max leverage to int, raw value is a float.
                max_leverage = int(max_leverage_float)
            except ValueError as e:
                _LOG.warning(
                    "Max leverage=%s should be of int type", max_leverage_float
                )
                raise e
            minimal_order_limits[asset_id]["max_leverage"] = max_leverage
        return minimal_order_limits

    # TODO(gp): Make static and move.
    def _is_submitted_order(self, order: oordorde.Order) -> bool:
        """
        Check if an order is submitted to CCXT.

        A submitted order has a valid `ccxt_id` and is not empty.
        """
        if order is None:
            # An empty order was not submitted.
            return False
        if "ccxt_id" not in order.extra_params:
            # Submitted order contains CCXT response in the form of `ccxt_id`.
            return False
        ccxt_id = self._get_ccxt_id_from_child_order(order)
        ret = True
        if not isinstance(ccxt_id, int):
            # ID must be an int.
            ret = False
        if ccxt_id < 0:
            # ID cannot be negative.
            ret = False
        return ret

    def _handle_exchange_exception(
        self, e: Exception, order: oordorde.Order
    ) -> oordorde.Order:
        """
        Handle the exception reported by the exchange during the order
        submission.

        The expected CCXT exceptions are:
        - `NetworkError` for problems with connectivity
        - `ExchangeError` for violating rules of the exchange, like going below
          the notional limit
        - `ExchangeNotAvailable` for problems on the exchange side

        All exceptions are handled the same way:
        - the order submission is skipped
        - the order is assigned a `ccxt_id` == -1 to indicate that the submission
          was attempted, but unsuccessful.
        - the error message is logged in the `order.extra_params` for later
          accounting

        :param e: exception reported by the exchange during the submission
        :param order: order that needed to be submitted
        :return: Order object with `ccxt_id` == -1 and appended error message
        """
        # Report a warning.
        error_msg = str(e)
        _LOG.warning(
            "Order: %s\nOrder submission failed due to: %s", str(order), error_msg
        )
        # Set the CCXT ID to -1 to indicate that the order submission was not
        # successful.
        self._set_ccxt_id_to_child_order(order, -1)
        order.extra_params["error_msg"] = error_msg
        return order

    # TODO(gp): This is used only in ccxt_broker, so it should be moved there,
    # but merging AbstractCcxtBroker and CcxtBroker will address this.
    def _skip_child_order_if_needed(
        self,
        parent_order: oordorde.Order,
        child_order_diff_signed_num_shares: Dict[int, float],
    ) -> bool:
        """
        Check whether a child order should be skipped if its amount is equal to
        0.

        :param parent_order: parent order on which the child is based
        :param child_order_diff_signed_num_shares: size of the child order
            corresponding to the parent
        :return: boolean value of the check
        """
        # Skip the child order if it is empty after rounding down.
        if self._is_child_order_shares_correct(
            child_order_diff_signed_num_shares
        ):
            _LOG.info(
                "Parent order ID: %s",
                parent_order.order_id,
            )
            _LOG.debug(
                "Child order for parent_order=%s not sent, %s",
                str(parent_order),
                hprint.to_str("child_order_diff_signed_num_shares"),
            )
            return True

    @abc.abstractmethod
    def _submit_twap_child_orders(
        self,
        parent_orders: List[oordorde.Order],
        parent_order_ids_to_child_order_shares: Dict[int, float],
        order_dfs: List[pd.DataFrame],
        execution_freq: pd.Timedelta,
        passivity_factor: float,
    ) -> List[pd.DataFrame]:
        """
        Given a set of parent orders, create and submit TWAP child orders.
        """
        ...

    async def _wait_for_accepted_orders(
        self,
        order_receipt: str,
    ) -> None:
        # Calls to CCXT to submit orders are blocking, so there is no need to wait
        # for order being accepted.
        _ = order_receipt

    # ////////////////////////////////////////////////////////////////////////////

    @hretry.async_retry(
        num_attempts=_MAX_EXCHANGE_REQUEST_RETRIES,
        exceptions=(ccxt.NetworkError, ccxt.RequestTimeout),
        retry_delay_in_sec=_REQUEST_RETRY_SLEEP_TIME_IN_SEC,
    )
    async def _get_ccxt_trades_for_one_symbol(
        self, ccxt_orders: List[CcxtData]
    ) -> List[CcxtData]:
        """
        Get CCXT trades for orders that share the same symbol.

        This is a helper handling loading of trades from CCXT for a
        batch of orders via a single API call.

        :param ccxt_orders: list of dicts of CCXT order with the same
            symbol, e.g. 'BTC/USDT'
        :return: list of dicts of trades for provided orders
        """
        # Get the symbol of the provided orders.
        symbol = list(set([ccxt_order["symbol"] for ccxt_order in ccxt_orders]))
        # Verify that it is the same for all provided orders.
        hdbg.dassert_eq(len(symbol), 1)
        symbol = symbol[0]
        # Get conducted trades for that symbol.
        #
        # Example of output of `fetchMyTrades()`
        # ```
        # {'info': {'symbol': 'ETHUSDT',
        #           'id': '2271885264',
        #           'orderId': '8389765544333791328',
        #           'side': 'SELL',
        #           'price': '1263.68',
        #           'qty': '0.016',
        #           'realizedPnl': '-3.52385454',
        #           'marginAsset': 'USDT',
        #           'quoteQty': '20.21888',
        #           'commission': '0.00808755',
        #           'commissionAsset': 'USDT',
        #           'time': '1663859837554',
        #           'positionSide': 'BOTH',
        #           'buyer': False,
        #           'maker': False},
        #  'timestamp': 1663859837554,
        #  'datetime': '2022-09-22T15:17:17.554Z',
        #  'symbol': 'ETH/USDT',
        #  'id': '2271885264',
        #  'order': '8389765544333791328',
        #  'type': None,
        #  'side': 'sell',
        #  'takerOrMaker': 'taker',
        #  'price': 1263.68,
        #  'amount': 0.016,
        #  'cost': 20.21888,
        #  'fee': {'cost': 0.00808755, 'currency': 'USDT'},
        #  'fees': [{'currency': 'USDT', 'cost': 0.00808755}]}
        # ```
        symbol_trades = {}
        symbol_trades = await self._async_exchange.fetchMyTrades(
            symbol, limit=1000
        )
        # Map from symbol t
        # Filter the trades based on CCXT order IDs.
        #
        # Select CCXT IDs and filter orders by them.
        # By default, the trades for symbol are loaded for the past 7 days.
        # To get trades corresponding to a Broker session, the trades are
        # filtered out by order ID. It is assumed that the input CCXT orders
        # are already closed orders for the given Broker iteration.
        ccxt_order_ids = set([ccxt_order["id"] for ccxt_order in ccxt_orders])
        symbol_trades = filter(
            lambda trade: trade["info"]["orderId"] in ccxt_order_ids,
            symbol_trades,
        )
        # Add the asset ids to each fill.
        asset_id = self.ccxt_symbol_to_asset_id_mapping[symbol]
        symbol_trades_with_asset_ids = []
        for symbol_fill in symbol_trades:
            _LOG.info(hprint.to_str("symbol_fill"))
            # Get the position of the full symbol field
            # to paste the asset id after it.
            hdbg.dassert_in("symbol", symbol_fill.keys())
            idx = list(symbol_fill.keys()).index("symbol") + 1
            # Add asset id.
            symbol_fill = list(symbol_fill.items())
            symbol_fill.insert(idx, ("asset_id", asset_id))
            _LOG.info(hprint.to_str("symbol_fill"))
            symbol_trades_with_asset_ids.append(dict(symbol_fill))

        return symbol_trades_with_asset_ids

    def _get_ccxt_trades_for_time_period(
        self,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        *,
        symbols: Optional[List[str]] = None,
    ) -> List[CcxtData]:
        """
        Get a list of CCXT trades for a given time period [a, b] in JSON
        format.

        This is used by objects other than oms.Portfolio (e.g., scripts)
        to retrieve all the CCXT trades corresponding to a period of
        time.

        Note that in case of long time periods (>24h) the pagination is
        done by day, which can lead to more data being downloaded than
        expected.

        :return: list of dictionary, each containing trade information
        """
        hdbg.dassert_isinstance(start_timestamp, pd.Timestamp)
        hdbg.dassert_isinstance(end_timestamp, pd.Timestamp)
        hdbg.dassert_lte(start_timestamp, end_timestamp)
        #
        start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
        end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp)
        # Get CCXT trades symbol by symbol.
        trades = []
        symbols = symbols or list(self.ccxt_symbol_to_asset_id_mapping.keys())
        day_in_millisecs = 24 * 60 * 60 * 1000
        for symbol in symbols:
            if end_timestamp - start_timestamp <= day_in_millisecs:
                # Download all trades if period is less than 24 hours.
                _LOG.info(
                    "Downloading period=%s, %s", start_timestamp, end_timestamp
                )
                symbol_trades = self._sync_exchange.fetchMyTrades(
                    symbol=symbol,
                    since=start_timestamp,
                    params={"endTime": end_timestamp},
                )
            else:
                # Download day-by-day for longer time periods.
                symbol_trades = []
                for timestamp in range(
                    start_timestamp, end_timestamp + 1, day_in_millisecs
                ):
                    _LOG.info(
                        "Downloading period=%s, %s", timestamp, day_in_millisecs
                    )
                    day_trades = self._sync_exchange.fetchMyTrades(
                        symbol=symbol,
                        since=timestamp,
                        params={"endTime": timestamp + day_in_millisecs},
                    )
                    symbol_trades.extend(day_trades)
            # Example of output of `fetchMyTrades()`
            # ```
            # {'info': {'symbol': 'ETHUSDT',
            #           'id': '2271885264',
            #           'orderId': '8389765544333791328',
            #           'side': 'SELL',
            #           'price': '1263.68',
            #           'qty': '0.016',
            #           'realizedPnl': '-3.52385454',
            #           'marginAsset': 'USDT',
            #           'quoteQty': '20.21888',
            #           'commission': '0.00808755',
            #           'commissionAsset': 'USDT',
            #           'time': '1663859837554',
            #           'positionSide': 'BOTH',
            #           'buyer': False,
            #           'maker': False},
            #  'timestamp': 1663859837554,
            #  'datetime': '2022-09-22T15:17:17.554Z',
            #  'symbol': 'ETH/USDT',
            #  'id': '2271885264',
            #  'order': '8389765544333791328',
            #  'type': None,
            #  'side': 'sell',
            #  'takerOrMaker': 'taker',
            #  'price': 1263.68,
            #  'amount': 0.016,
            #  'cost': 20.21888,
            #  'fee': {'cost': 0.00808755, 'currency': 'USDT'},
            #  'fees': [{'currency': 'USDT', 'cost': 0.00808755}]}
            # ```
            # Add the asset ids to each trade.
            asset_id = self.ccxt_symbol_to_asset_id_mapping[symbol]
            trades_with_asset_ids = []
            for symbol_trade in symbol_trades:
                _LOG.info("symbol_trade=%s", symbol_trade)
                # Get the position of the full symbol field to paste the asset id
                # after it.
                hdbg.dassert_in("symbol", symbol_trade.keys())
                idx = list(symbol_trade.keys()).index("symbol") + 1
                # Add asset id.
                symbol_trade = list(symbol_trade.items())
                symbol_trade.insert(idx, ("asset_id", asset_id))
                _LOG.info("after transformation: symbol_trade=%s", symbol_trade)
                # Accumulate.
                trades_with_asset_ids.append(dict(symbol_trade))
            # Accumulate.
            trades.extend(trades_with_asset_ids)
        return trades

    def _set_leverage_for_all_symbols(self, leverage: int) -> None:
        """
        Set leverage for all symbols.

        :param leverage: leverage to set
        """
        # TODO(Juraj): Should we check if the change was successful?
        # TODO(Juraj): Temporary hack to assist with random order generation.
        for symbol in self.ccxt_symbol_to_asset_id_mapping.keys():
            self._sync_exchange.setLeverage(leverage, symbol)

    async def _submit_single_order_to_ccxt_with_exception(
        self,
        submitted_order: oordorde.Order,
        *,
        symbol: str,
        position_size: float,
        side: str,
        order_type: str,
        limit_price: Optional[float],
    ) -> Tuple[
        oordorde.Order,
        CcxtData,
        Optional[
            Union[ccxt.BaseError, ccxt.ExchangeNotAvailable, ccxt.NetworkError]
        ],
        bool,
    ]:
        """
        Submit a single order to CCXT.

        Errors processing scenario:
          - `ccxt.ExchangeNotAvailable`, `ccxt.NetworkError`: log the error and retry
          - `ccxt.BaseError`: log the error and not retry

        Raises:
          - Exception: any other errors not specified above
        """
        # Define the error None by default.
        error = None
        # Set up empty response in case the order is not submitted.
        ccxt_order_response: CcxtData = {}
        params = {
            "portfolio_id": self._portfolio_id,
            "client_oid": submitted_order.order_id,
        }
        try:
            # Create a reduce-only order.
            # Such an order can only reduce the current open position
            # and will never go over the current position size.
            if submitted_order.extra_params.get("reduce_only", False):
                # Reduce-only order can be placed as a market order,
                # but since we only use it for quick liquidation,
                # keeping this assertion here.
                hdbg.dassert_eq(order_type, "market")
                _LOG.info("Creating reduceOnly order: %s", str(submitted_order))
                # TODO(Danya): Not sure if async-supported, but probably irrelevant,
                # since it is only used to flatten accounts.
                ccxt_order_response = (
                    await self._async_exchange.createReduceOnlyOrder(
                        symbol=symbol,
                        type=order_type,
                        side=side,
                        amount=position_size,
                        params=params,
                        price=0,
                    )
                )
            elif order_type == "market":
                # Simple market order.
                ccxt_order_response = await self._async_exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=position_size,
                    params=params,
                )
            elif order_type == "limit":
                # Limit order.
                hdbg.dassert_isinstance(limit_price, float)
                ccxt_order_response = await self._async_exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=position_size,
                    price=limit_price,
                    params=params,
                )
            else:
                raise ValueError(f"Invalid order_type='{order_type}'")
            _LOG.info(hprint.to_str("ccxt_order_response"))
            # Assign parent order CCXT ID.
            if not ccxt_order_response:
                submitted_order = self._handle_exchange_exception(
                    "Empty response", submitted_order
                )
            else:
                submitted_order = self._set_ccxt_id_to_child_order(
                    submitted_order, ccxt_order_response["id"]
                )
            to_retry = False
        except Exception as e:
            error = e
            submitted_order = self._handle_exchange_exception(
                error, submitted_order
            )
            # Check the Binance API error.
            if isinstance(error, (ccxt.ExchangeNotAvailable, ccxt.NetworkError)):
                # If there is a temporary server error, wait a bit and retry.
                to_retry = True
                _LOG.warning(
                    "Connectivity error:\n%s\nRetrying ...",
                    error,
                )
            elif isinstance(error, ccxt.BaseError):
                # Don't raise the error if it is connected to the CCXT.
                # This logs the error in the Order object.
                to_retry = False
            else:
                raise error
        return submitted_order, ccxt_order_response, error, to_retry

    async def _submit_single_order_to_ccxt(
        self,
        order: oordorde.Order,
        *,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        wait_time_in_secs: int = 0.5,
    ) -> Tuple[oordorde.Order, CcxtData]:
        """
        Submit a single order to CCXT using a retry mechanism.

        This function tries several times to submit the order, and if it fails it
        raises. For each attempt, the
        `_submit_single_order_to_ccxt_with_exception()` method is used, which also
        handles any exceptions that occur.

        :param order: order to be submitted
        :param order_type: 'market' or 'limit'
        :param limit_price: limit order price if order_type = 'limit'
        :param wait_time_in_secs: how long to wait between resubmissions

        :return: if order submission is successful, a tuple with 2 elements:
         - order updated with CCXT order id if the submission was successful
         - CCXT order structure: https://docs.ccxt.com/en/latest/manual.html#order-structure
        """
        hdbg.dassert_in(order_type, ["market", "limit"])
        _LOG.info("Submitting order=%s", order)
        # Extract the info from the order.
        symbol = self.asset_id_to_ccxt_symbol_mapping[order.asset_id]
        side = "buy" if order.diff_num_shares > 0 else "sell"
        hdbg.dassert_ne(order.diff_num_shares, 0)
        position_size = abs(order.diff_num_shares)
        submitted_order = order
        # TODO(Juraj): Log the actual leverage used in the order,
        # not only the maximum possible.
        self._update_stats_for_order(
            submitted_order,
            f"start.timestamp",
            self.market_data.get_wall_clock_time(),
        )
        for attempt_num in range(1, self._max_exchange_request_retries + 1):
            _LOG.info(
                "Order submission attempt: %s / %s",
                attempt_num,
                self._max_exchange_request_retries,
            )
            # Submit an order and handle the possible exception.
            (
                submitted_order,
                ccxt_order_response,
                e,
                to_retry,
            ) = await self._submit_single_order_to_ccxt_with_exception(
                submitted_order,
                symbol=symbol,
                position_size=position_size,
                side=side,
                order_type=order_type,
                limit_price=limit_price,
            )
            # If the submission was successful and resulted in a successfully
            #  formed response, stop submission attempts.
            if not to_retry:
                # The submission attempt was successful, so any cached value
                # of `_open_positions` is obsolete.
                self._cached_open_positions = None
                break
            # Log the exception that necessitated a retry.
            self._update_stats_for_order(
                submitted_order, f"exception_on_retry.{attempt_num}", str(e)
            )
            _LOG.info("Sleeping for %s secs: start", wait_time_in_secs)
            await asyncio.sleep(wait_time_in_secs)
            _LOG.info("Sleeping for %s secs: done", wait_time_in_secs)
        # Log order stats.
        self._update_stats_for_order(
            submitted_order,
            f"attempt_num",
            attempt_num,
        )
        self._update_stats_for_order(
            submitted_order,
            f"all_attempts_end.timestamp",
            self.market_data.get_wall_clock_time(),
        )
        return submitted_order, ccxt_order_response

    # ///////////////////////////////////////////////////////////////////////////

    async def _align_with_parent_order_start_timestamp(
        self, parent_order_start_time: pd.Timestamp
    ) -> None:
        """
        Wait until it's time to start executing the parent order.
        """
        # Get the actual start time for TWAP execution.
        current_timestamp = self.market_data.get_wall_clock_time()
        if current_timestamp < parent_order_start_time:
            _LOG.info("Aligning time with parent order start time")
            await hasynci.async_wait_until(
                parent_order_start_time, self._get_wall_clock_time
            )

    # ///////////////////////////////////////////////////////////////////////////

    def _calculate_num_twap_child_order_waves(
        self,
        parent_order_execution_end_timestamp: pd.Timestamp,
        execution_freq: pd.Timedelta,
    ) -> int:
        """
        Calculate number of child waves to run based on the current time and
        execution end timestamp of the parent order, given an execution
        frequency:

        :param parent_order_execution_end_timestamp
        :execution_freq: frequency of order submission
        :return: number of child order waves
        """
        num_waves = int(
            np.ceil(
                (
                    parent_order_execution_end_timestamp
                    - self._get_wall_clock_time()
                )
                / execution_freq
            )
        )
        return num_waves

    async def _submit_market_orders(
        self,
        orders: List[oordorde.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool = False,
    ) -> Tuple[str, List[oordorde.Order]]:
        """
        Submit orders to the actual OMS and wait for the orders to be accepted.
        """
        # self.previous_parent_orders_timestamp = self.market_data.get_wall_clock_time()
        self.previous_parent_orders_timestamp = wall_clock_timestamp
        # Submit the orders to CCXT one by one.
        sent_orders: List[oordorde.Order] = []
        for order in orders:
            if order.type_ == "limit":
                side = "buy" if order.diff_num_shares > 0 else "sell"
                limit_price = self.load_bid_ask_and_calculate_limit_price(
                    order.asset_id, side
                )
            else:
                limit_price = None
            # Submit the order to CCXT.
            (
                sent_order,
                ccxt_order_response,
            ) = await self._submit_single_order_to_ccxt(
                order,
                order_type=order.type_,
                limit_price=limit_price,
            )
            # Logging CCXT response.
            self._logger.log_child_order(
                self._get_wall_clock_time,
                sent_order,
                ccxt_order_response,
                {"limit_price": limit_price},
            )
            # If order was submitted successfully append it to the list of sent
            # orders.
            if self._is_submitted_order(sent_order):
                sent_orders.append(sent_order)
        # Save sent CCXT orders to class state.
        self._previous_parent_orders = sent_orders
        # The receipt is not really needed since the order is accepted right away,
        # and we don't need to wait for the order being accepted.
        submitted_order_id = self._get_next_submitted_order_id()
        receipt = f"order_{submitted_order_id}"
        _LOG.info("orders=%s", oordorde.orders_to_string(orders))
        return receipt, sent_orders
