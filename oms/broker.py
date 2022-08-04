"""
Import as:

import oms.broker as ombroker
"""

import abc
import collections
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import market_data as mdata
import oms.oms_db as oomsdb
import oms.order as omorder

_LOG = logging.getLogger(__name__)


# #############################################################################
# Fill
# #############################################################################


# TODO(gp): Consider moving this in fill.py
class Fill:
    """
    Represent an order fill.

    An order can be filled partially or completely. Each fill can happen at
    different prices.

    The simplest case is for an order to be completely filled (e.g., at the end of
    its VWAP execution window) at a single price. In this case a single `Fill`
    object can represent the execution.
    """

    _fill_id = 0

    def __init__(
        self,
        order: omorder.Order,
        timestamp: pd.Timestamp,
        num_shares: float,
        price: float,
    ):
        """
        Constructor.

        :param num_shares: it's the number of shares that are filled, with
            respect to `diff_num_shares` in Order
        """
        _LOG.debug(hprint.to_str("order timestamp num_shares price"))
        self._fill_id = self._get_next_fill_id()
        # Pointer to the order.
        self.order = order
        # TODO(gp): An Order should contain a list of pointers to its fills for
        #  accounting purposes.
        #  We can verify the invariant that no more than the desired quantity
        #  was filled.
        # Timestamp of when it was completed.
        self.timestamp = timestamp
        # Number of shares executed. This has the same meaning as in Order, i.e., it
        # can be positive and negative depending on long / short.
        hdbg.dassert_ne(num_shares, 0)
        self.num_shares = num_shares
        # Price executed for the given shares.
        hdbg.dassert_lt(0, price)
        self.price = price

    def __str__(self) -> str:
        txt: List[str] = []
        txt.append("Fill:")
        dict_ = self.to_dict()
        for k, v in dict_.items():
            txt.append(f"{k}={v}")
        return " ".join(txt)

    def to_dict(self) -> Dict[str, Any]:
        dict_: Dict[str, Any] = collections.OrderedDict()
        dict_["asset_id"] = self.order.asset_id
        dict_["fill_id"] = self.order.order_id
        dict_["timestamp"] = self.timestamp
        dict_["num_shares"] = self.num_shares
        dict_["price"] = self.price
        return dict_

    @staticmethod
    def _get_next_fill_id() -> int:
        fill_id = Fill._fill_id
        Fill._fill_id += 1
        return fill_id


# #############################################################################
# Broker
# #############################################################################


class Broker(abc.ABC, hobject.PrintableMixin):
    """
    Represent a broker to which we can place orders and receive fills back.

    The broker:
    1) keeps an internal book keeping of orders submitted and deadlines when they
       are supposed to be executed
    2) passes the orders to the actual Order Management System (OMS) through an
       interface (e.g., DB, file system)
    3) waits for an acknowledgement of orders being submitted successfully by the OMS
    4) reports the order fills from the market
    """

    _submitted_order_id: int = 0

    def __init__(
        self,
        strategy_id: str,
        market_data: mdata.MarketData,
        *,
        account: Optional[str] = None,
        timestamp_col: str = "end_datetime",
        column_remap: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Constructor.

        :param account: allow to have multiple accounts. `None` means not used
        :param column_remap: (optional) remap columns when accessing a
            `MarketData` to retrieve execution prices. The required columns
            are "bid", "ask", "price", and "midpoint".
        """
        _LOG.debug(
            hprint.to_str(
                "strategy_id market_data account timestamp_col column_remap"
            )
        )
        self._strategy_id = strategy_id
        self._account = account
        #
        hdbg.dassert_issubclass(market_data, mdata.MarketData)
        self.market_data = market_data
        self._get_wall_clock_time = market_data.get_wall_clock_time
        self._timestamp_col = timestamp_col
        self._column_remap = column_remap
        # Track the orders for internal accounting, mapping wall clock when the
        # order was submitted to the submitted orders.
        self._orders: Dict[
            pd.Timestamp, List[omorder.Order]
        ] = collections.OrderedDict()
        # Map a timestamp to the orders with that execution time deadline.
        self._deadline_timestamp_to_orders: Dict[
            pd.Timestamp, List[omorder.Order]
        ] = collections.defaultdict(list)
        # Track the fills for internal accounting.
        self._fills: List[Fill] = []
        #
        _LOG.debug("After initialization:\n%s", repr(self))

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def account(self) -> str:
        return self._account

    @property
    def timestamp_col(self) -> str:
        return self._timestamp_col

    async def submit_orders(
        self,
        orders: List[omorder.Order],
        *,
        dry_run: bool = False,
    ) -> str:
        """
        Submit a list of orders to the broker.

        :param dry_run: do not submit orders to the OMS, but keep track of them
            internally
        :return: a string representing the receipt of submission / acceptance
            (e.g., path of the file created on S3 with the order info)
        """
        wall_clock_timestamp = self._get_wall_clock_time()
        # Log the order for internal book keeping.
        self._log_order_submissions(orders)
        # Enqueue the orders based on their completion deadline time.
        _LOG.debug("Submitting %d orders", len(orders))
        for order in orders:
            _LOG.debug("Submitting order %s", order.order_id)
            # hdbg.dassert_lte(
            #    order.start_timestamp,
            #    wall_clock_timestamp,
            #    "An order can only be executed in the future: order=",
            #    order,
            # )
            self._deadline_timestamp_to_orders[order.end_timestamp].append(order)
        # Submit the orders to the actual OMS.
        _LOG.debug("Submitting orders=\n%s", omorder.orders_to_string(orders))
        if self._strategy_id == "null":
            _LOG.warning(
                "Using dry-run mode since strategy_id='%s'", self._strategy_id
            )
            dry_run = True
        file_name = await self._submit_orders(
            orders, wall_clock_timestamp, dry_run=dry_run
        )
        _LOG.debug("The receipt is '%s'", file_name)
        #
        if not dry_run:
            _LOG.debug("Waiting for the accepted orders")
            await self._wait_for_accepted_orders(file_name)
        else:
            _LOG.warning(
                "Skipping waiting for the accepted orders because of dry_run=%s",
                dry_run,
            )
        return file_name

    @abc.abstractmethod
    def get_fills(self) -> List[Fill]:
        """
        Get any new fills filled since last execution.
        """
        ...

    @staticmethod
    def _get_next_submitted_order_id() -> int:
        submitted_order_id = Broker._submitted_order_id
        Broker._submitted_order_id += 1
        return submitted_order_id

    @abc.abstractmethod
    async def _submit_orders(
        self,
        orders: List[omorder.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool,
    ) -> str:
        """
        Submit orders to the actual OMS and wait for the orders to be accepted.

        :return: a string representing the receipt of submission / acceptance
        """
        ...

    @abc.abstractmethod
    async def _wait_for_accepted_orders(
        self,
        file_name: str,
    ) -> None:
        """
        Wait until orders are accepted.
        """
        ...

    def _get_fills_helper(self) -> List[Fill]:
        """
        Implement logic simulating orders being filled.
        """
        # We should always get the "next" orders, for this reason one should use
        # a priority queue.
        wall_clock_timestamp = self._get_wall_clock_time()
        timestamps = self._deadline_timestamp_to_orders.keys()
        _LOG.debug("Timestamps of orders in queue: %s", timestamps)
        if not timestamps:
            return []
        # In our current execution model, we should ask about the orders that are
        # terminating.
        hdbg.dassert_lte(min(timestamps), wall_clock_timestamp)
        orders_to_execute_timestamps = []
        orders_to_execute = []
        for timestamp in timestamps:
            if timestamp <= wall_clock_timestamp:
                orders_to_execute.extend(
                    self._deadline_timestamp_to_orders[timestamp]
                )
                orders_to_execute_timestamps.append(timestamp)
        _LOG.debug("Executing %d orders", len(orders_to_execute))
        # Ensure that no orders are included with `end_timestamp` greater than
        # `wall_clock_timestamp`, e.g., assume that in general orders take their
        # entire allotted window to fill.
        for order in orders_to_execute:
            hdbg.dassert_lte(order.end_timestamp, wall_clock_timestamp)
        # "Execute" the orders.
        # TODO(gp): Here there should be a programmable logic that decides
        #  how many shares are filled.
        fills = self._fully_fill(orders_to_execute)
        # NOTE: `self._fills` is not in `init()` in the abstract class.
        self._fills.extend(fills)
        # Remove the orders that have been executed.
        _LOG.debug(
            "Removing orders from queue with deadline earlier than=`%s`",
            wall_clock_timestamp,
        )
        for timestamp in orders_to_execute_timestamps:
            del self._deadline_timestamp_to_orders[timestamp]
        _LOG.debug("-> Returning fills:\n%s", str(fills))
        return fills

    # TODO(gp): Consider getting the wall clock, instead of passing it.
    def _fully_fill(
        self,
        orders: List[omorder.Order],
    ) -> List[Fill]:
        """
        Completely fill orders.
        """
        # TODO(Paul): The function `get_execution_prices()` should be
        #  configurable.
        prices = get_execution_prices(
            self.market_data,
            orders,
            timestamp_col=self._timestamp_col,
            column_remap=self._column_remap,
        )
        fills = []
        for order in orders:
            end_timestamp = order.end_timestamp
            num_shares = order.diff_num_shares
            hdbg.dassert_in(order.asset_id, prices.index)
            price = prices[order.asset_id]
            if not np.isfinite(price):
                _LOG.warning("Unable to fill order=\n%s", order)
                continue
            fill = Fill(order, end_timestamp, num_shares, price)
            fills.append(fill)
        return fills

    def _log_order_submissions(self, orders: List[omorder.Order]) -> None:
        """
        Add the orders to the internal book keeping.
        """
        hdbg.dassert_container_type(orders, list, omorder.Order)
        wall_clock_timestamp = self._get_wall_clock_time()
        _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        if self._orders:
            last_timestamp = next(reversed(self._orders))
            hdbg.dassert_lt(last_timestamp, wall_clock_timestamp)
        self._orders[wall_clock_timestamp] = orders


# #############################################################################
# SimulatedBroker
# #############################################################################


class SimulatedBroker(Broker):
    """
    Represent a broker to which we place orders and receive back fills:
    1) completely
    2) as soon as their deadline comes
    3) at the price from the Market

    There is no interaction with an OMS (e.g., no need to waiting for
    acceptance and execution).
    """

    # TODO(gp): Not sure this is needed.
    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

    def get_fills(self) -> List[Fill]:
        return self._get_fills_helper()

    async def _submit_orders(
        self,
        orders: List[omorder.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool,
    ) -> str:
        """
        Same as abstract method.
        """
        # All the simulated behavior is already in the abstract class so there
        # is nothing to do here.
        _ = orders, wall_clock_timestamp
        if dry_run:
            _LOG.warning("Not submitting orders to OMS because of dry_run")
        return "dummy_order_receipt"

    async def _wait_for_accepted_orders(
        self,
        file_name: str,
    ) -> None:
        """
        Same as abstract method.
        """
        # Orders are always immediately accepted in simulation, so there is
        # nothing to do here.
        _ = file_name


# #############################################################################
# DatabaseBroker
# #############################################################################


class DatabaseBroker(Broker):
    """
    An object that represents a broker backed by a DB with asynchronous updates
    to the state by an OMS handling the orders placed and then filled in the
    market place.

    The DB contains the following tables:
    - `submitted_orders`: store information about orders placed by strategies
    - `accepted_orders`: store information about orders accepted by the OMS
    """

    def __init__(
        self,
        *args: Any,
        db_connection: hsql.DbConnection,
        submitted_orders_table_name: str,
        accepted_orders_table_name: str,
        # TODO(gp): This doesn't work for some reason.
        # *,
        poll_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        """
        Construct object.

        :param poll_kwargs: polling instruction when waiting for acceptance of an
            order
        """
        _LOG.debug(
            hprint.to_str(
                "db_connection submitted_orders_table_name "
                "accepted_orders_table_name poll_kwargs"
            )
        )
        super().__init__(*args, **kwargs)
        self._db_connection = db_connection
        self._submitted_orders_table_name = submitted_orders_table_name
        self._accepted_orders_table_name = accepted_orders_table_name
        if poll_kwargs is None:
            poll_kwargs = hasynci.get_poll_kwargs(self._get_wall_clock_time)
        self._poll_kwargs = poll_kwargs
        # Store the submitted rows to the DB for internal book keeping.
        self._submissions: Dict[
            pd.Timestamp, pd.Series
        ] = collections.OrderedDict()
        #
        _LOG.debug("After initialization:\n%s", repr(self))

    def get_fills(self) -> List[Fill]:
        return self._get_fills_helper()

    async def _submit_orders(
        self,
        orders: List[omorder.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool = False,
    ) -> str:
        """
        Same as abstract method.

        :return: a `file_name` representing the id of the submitted order in the DB
        """
        # Add an order in the submitted orders table.
        submitted_order_id = self._get_next_submitted_order_id()
        orderlist: List[Tuple[str, Any]] = []
        file_name = f"filename_{submitted_order_id}.txt"
        orderlist.append(("filename", file_name))
        timestamp_db = self._get_wall_clock_time()
        orderlist.append(("timestamp_db", timestamp_db))
        orderlist.append(("orders_as_txt", omorder.orders_to_string(orders)))
        row = pd.Series(collections.OrderedDict(orderlist))
        # Store the order internally.
        self._submissions[timestamp_db] = row
        # Write the row into the DB.
        if dry_run:
            _LOG.warning("Not submitting orders because of dry_run")
        else:
            hsql.execute_insert_query(
                self._db_connection, row, self._submitted_orders_table_name
            )
        return file_name

    async def _wait_for_accepted_orders(
        self,
        file_name: str,
    ) -> None:
        """
        Same as abstract method.
        """
        _LOG.debug("Wait for accepted orders ...")
        await oomsdb.wait_for_order_acceptance(
            self._db_connection,
            file_name,
            self._poll_kwargs,
            table_name=self._accepted_orders_table_name,
            field_name="filename",
        )
        _LOG.debug("Wait for accepted orders ... done")


# #############################################################################
# Order execution simulation
# #############################################################################


def get_execution_prices(
    market_data: mdata.MarketData,
    orders: List[omorder.Order],
    *,
    timestamp_col: str = "end_datetime",
    column_remap: Optional[Dict[str, str]] = None,
) -> pd.Series:
    """
    Get the simulated execution prices of a list of orders.

    This method assumes that all orders in the list share a common:
      - order type
      - order start timestamp
      - order end timestamp
    """
    needed_columns = ["bid", "ask", "price", "midpoint"]
    if column_remap is None:
        column_remap = {col_name: col_name for col_name in needed_columns}
    hdbg.dassert_set_eq(column_remap.keys(), needed_columns)
    # Ensure that the list is nonempty.
    hdbg.dassert(orders)
    # Parse the order type.
    start_timestamps = set()
    end_timestamps = set()
    order_types = set()
    asset_ids = []
    # Ensure all orders share a common type, start_timestamp, and
    # end_timestamp.
    for order in orders:
        order_types.add(order.type_)
        start_timestamps.add(order.start_timestamp)
        end_timestamps.add(order.end_timestamp)
        asset_ids.append(order.asset_id)
    hdbg.dassert_eq(len(order_types), 1)
    hdbg.dassert_eq(len(start_timestamps), 1)
    hdbg.dassert_eq(len(end_timestamps), 1)
    # Extract the shared order properties.
    order_type = order_types.pop()
    start_timestamp = start_timestamps.pop()
    end_timestamp = end_timestamps.pop()
    # Parse the order type.
    config = order_type.split("@")
    hdbg.dassert_eq(len(config), 2, "Invalid type_='%s'", order_type)
    price_type, timing = config
    # Get the price depending on the price_type.
    if price_type in ("price", "midpoint"):
        column = column_remap[price_type]
        prices = _get_price_per_share(
            market_data,
            start_timestamp,
            end_timestamp,
            timestamp_col,
            asset_ids,
            column,
            timing,
        )
    elif price_type.startswith("partial_spread"):
        perc = float(price_type.split("_")[2])
        hdbg.dassert_lte(0, perc)
        hdbg.dassert_lte(perc, 1.0)
        bid_col = column_remap["bid"]
        bids = _get_price_per_share(
            market_data,
            start_timestamp,
            end_timestamp,
            timestamp_col,
            asset_ids,
            bid_col,
            timing,
        )
        ask_col = column_remap["ask"]
        asks = _get_price_per_share(
            market_data,
            start_timestamp,
            end_timestamp,
            timestamp_col,
            asset_ids,
            ask_col,
            timing,
        )
        is_buy = []
        for order in orders:
            if order.diff_num_shares >= 0:
                is_buy.append(True)
            else:
                is_buy.append(False)
        is_buy = pd.Series(is_buy, bids.index)
        is_sell = ~is_buy
        # If perc == 0, we buy at the bid and sell at the ask
        # (we collect the spread).
        # If perc == 1, we buy at the ask and sell at the bid
        # (we cross the spread).
        buy_prices = (1.0 - perc) * bids + perc * asks
        # _LOG.debug("buy_prices=\n%s", buy_prices)
        sell_prices = perc * bids + (1.0 - perc) * asks
        # _LOG.debug("sell_prices=\n%s", sell_prices)
        prices = is_buy * buy_prices + is_sell * sell_prices
    else:
        raise ValueError(f"Invalid type='{order_type}'")
    _LOG.debug(
        "type=%s, start_timestamp=%s, end_timestamp=%s -> execution prices=%s",
        order_type,
        start_timestamp,
        end_timestamp,
        hpandas.df_to_str(prices, precision=2),
    )
    return prices


def _get_price_per_share(
    mi: mdata.MarketData,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    timestamp_col_name: str,
    asset_ids: List[int],
    column: str,
    timing: str,
) -> pd.Series:
    """
    Get the price corresponding to a certain column and timing (e.g., `start`,
    `end`, `twap`).

    :param timestamp_col_name: column to use to filter based on
        start_timestamp and end_timestamp
    :param column: column to use to compute the price
    """
    if timing == "start":
        price = mi.get_data_at_timestamp(
            start_timestamp, timestamp_col_name, asset_ids
        )[column]
    elif timing == "end":
        price = mi.get_data_at_timestamp(
            end_timestamp, timestamp_col_name, asset_ids
        )[column]
    elif timing == "twap":
        price = mi.get_twap_price(
            start_timestamp,
            end_timestamp,
            timestamp_col_name,
            asset_ids,
            column,
        )
    else:
        raise ValueError(f"Invalid timing='{timing}'")
    hdbg.dassert_is_not(price, None)
    hdbg.dassert(not price.isna().all())
    return price


# TODO(Paul): This function allows us to get the execution price for one order
#   at a time. It supports multiple (but untested) ways of doing this. Consider
#   vectorizing this code or else adding a switch to invoke order-by-order
#   processing.
# def get_execution_price(
#     market_data: mdata.MarketData,
#     order: omorder.Order,
#     *,
#     timestamp_col: str = "end_datetime",
#     column_remap: Optional[Dict[str, str]] = None,
# ) -> float:
#     """
#     Get the simulated execution price of an order.
#     """
#     hdbg.dassert_isinstance(order, omorder.Order)
#     needed_columns = ["bid", "ask", "price", "midpoint"]
#     if column_remap is None:
#         column_remap = {col_name: col_name for col_name in needed_columns}
#     hdbg.dassert_set_eq(column_remap.keys(), needed_columns)
#     # Parse the order type.
#     config = order.type_.split("@")
#     hdbg.dassert_eq(len(config), 2, "Invalid type_='%s'", order.type_)
#     price_type, timing = config
#     # Get the price depending on the price_type.
#     if price_type in ("price", "midpoint"):
#         column = column_remap[price_type]
#         prices = _get_price_per_share(
#             market_data,
#             order.start_timestamp,
#             order.end_timestamp,
#             timestamp_col,
#             order.asset_id,
#             column,
#             timing,
#         )
#     elif price_type == "full_spread":
#         # Cross the spread depending on buy / sell.
#         if order.diff_num_shares >= 0:
#             column = "ask"
#         else:
#             column = "bid"
#         column = column_remap[column]
#         prices = _get_price_per_share(
#             market_data,
#             order.start_timestamp,
#             order.end_timestamp,
#             timestamp_col,
#             order.asset_id,
#             column,
#             timing,
#         )
#     elif price_type.startswith("partial_spread"):
#         # Pay part of the spread depending on the parameter encoded in the
#         # `price_type` (e.g., TWAP).
#         perc = float(price_type.split("_")[2])
#         hdbg.dassert_lte(0, perc)
#         hdbg.dassert_lte(perc, 1.0)
#         column = column_remap["bid"]
#         bid_price = _get_price_per_share(
#             market_data,
#             order.start_timestamp,
#             order.end_timestamp,
#             timestamp_col,
#             order.asset_id,
#             column,
#             timing,
#         )
#         column = column_remap["ask"]
#         ask_price = _get_price_per_share(
#             market_data,
#             order.start_timestamp,
#             order.end_timestamp,
#             timestamp_col,
#             order.asset_id,
#             column,
#             timing,
#         )
#         if order.diff_num_shares >= 0:
#             # We need to buy:
#             # - if perc == 1.0 pay ask (i.e., pay full-spread)
#             # - if perc == 0.5 pay midpoint
#             # - if perc == 0.0 pay bid
#             price = perc * ask_price + (1.0 - perc) * bid_price
#         else:
#             # We need to sell:
#             # - if perc == 1.0 pay bid (i.e., pay full-spread)
#             # - if perc == 0.5 pay midpoint
#             # - if perc == 0.0 pay ask
#             price = (1.0 - perc) * ask_price + perc * bid_price
#     else:
#         raise ValueError(f"Invalid type='{order.type_}'")
#     _LOG.debug(
#         "type=%s, start_timestamp=%s, end_timestamp=%s -> execution_price=%s",
#         order.type_,
#         order.start_timestamp,
#         order.end_timestamp,
#         price,
#     )
#     return prices
