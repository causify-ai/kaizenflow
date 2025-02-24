"""
Import as:

import oms.broker.broker as obrobrok
"""

import abc
import collections
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import market_data as mdata
import oms.child_order_quantity_computer as ochorquco
import oms.fill as omfill
import oms.limit_price_computer as oliprcom
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)
_TRACE = False

# TODO(gp): -> oms_broker_utils.py

# #############################################################################
# Order execution simulation
# #############################################################################


# An order can be simulated with different level of fidelity. E.g., a TWAP
# order can be simulated:
# 1) as a single order executing at the end of the execution interval at a single
#    TWAP price
# 2) as multiple fills equally spaced in the execution interval
#
# The following functions implement the approach 1).


def _extract_order_properties(
    orders: List[oordorde.Order],
) -> Tuple[str, pd.Timestamp, pd.Timestamp, List[int]]:
    """
    Return the common order type, start timestamp, end timestamp and the union
    of the target asset ids.
    """
    # Ensure that the list is nonempty.
    hdbg.dassert(orders)
    # Accumulate information about the orders.
    start_timestamps = set()
    end_timestamps = set()
    order_types = set()
    asset_ids: Set[int] = set()
    for order in orders:
        _LOG.debug(hprint.to_str("order"))
        order_types.add(order.type_)
        start_timestamps.add(order.start_timestamp)
        end_timestamps.add(order.end_timestamp)
        asset_ids.add(order.asset_id)
    # Ensure all orders share a common type, start timestamp, and end timestamp.
    hdbg.dassert_eq(len(order_types), 1)
    hdbg.dassert_eq(len(start_timestamps), 1)
    hdbg.dassert_eq(len(end_timestamps), 1)
    hdbg.dassert_lte(1, len(asset_ids))
    asset_ids = sorted(list(asset_ids))
    # Extract the shared order properties.
    order_type = order_types.pop()
    start_timestamp = start_timestamps.pop()
    end_timestamp = end_timestamps.pop()
    hdbg.dassert_lt(start_timestamp, end_timestamp)
    return order_type, start_timestamp, end_timestamp, asset_ids


def _get_price_per_share(
    market_data: mdata.MarketData,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    timestamp_col_name: str,
    asset_ids: List[int],
    column: str,
    timing: str,
) -> pd.DataFrame:
    """
    Get the price corresponding to a certain column and timing (e.g., `start`,
    `end`, `twap`).

    :param timestamp_col_name: column to use to filter looking for start / end
        timestamp, typically the end of the interval `end_datetime`.
    :param column: column to use to compute the price
    :return: a df, e.g.,
        ```
                         price
        asset_id
        101             997.93
        ```
    """
    _LOG.debug(
        hprint.to_str(
            "start_timestamp end_timestamp timestamp_col_name"
            " asset_ids column timing"
        )
    )
    hdbg.dassert_isinstance(asset_ids, List)
    if timing == "start":
        # Align to the nearest bar, `MarketData` works with 1-minute OHLCV bars.
        # `start_timestamp` is typically equal to the bar start timestamp plus
        # the DAG execution time (e.g., 09:40:10 when we submit an order at 9:40,
        # after 10 seconds computation). We need to round the timestamp down to
        # the closest bar, since `MarketData` currently works on 1 min grid.
        # TODO(Grisha): remove the 1 minute bar length assumption, `MarketData`
        # should know bar length internally.
        # TODO(Grisha): unclear if we should round here or delegate it to
        # `MarketData`.
        bar_duration_in_secs = 60
        # Allow order generation to take some time. E.g., a bar starts at
        # 08:15:00 and orders are generated at 08:15:20, then it is okay that
        # there is a 20 seconds distance between the order creation timestamp
        # and bar start timestamp. But ensure that it does not spill over in
        # the next minute.
        max_distance_in_secs = 60
        # Round down to the last bar, because rounding up leads to future
        # peeking. E.g., at 16:45:45 use prices that correspond to 16:45:00.
        mode = "floor"
        start_timestamp = hdateti.find_bar_timestamp(
            start_timestamp,
            bar_duration_in_secs,
            mode=mode,
            max_distance_in_secs=max_distance_in_secs,
        )
        prices_df = market_data.get_data_at_timestamp(
            start_timestamp, timestamp_col_name, asset_ids
        )
    elif timing == "end":
        prices_df = market_data.get_data_at_timestamp(
            end_timestamp, timestamp_col_name, asset_ids
        )
    elif timing == "twap":
        # In simulation, for bar 9:35-9:40 we make the assumption that a TWAP
        # order covers an interval (a, b] where a is the time where we actually
        # place the order after the DAG computation (a=9:35 assuming that the
        # DAG executes in less than 1 minute) b is the end of the bar (i.e.,
        # 9:40), so in practice we assume that the TWAP is on (9:35, 9:40] =
        # [9:36, 9:40].
        # The TWAP order is either executed at the market side (i.e., we send
        # the order to the market and thus there is no propagation delay from
        # market to us anymore, so it’s possible to get the 9:40 price exactly),
        # or we assume that we do local TWAP execution but we wait for a bar to
        # be complete. In both cases we can actually observe the 9:40 price
        # without future peaking. For all these reasons we can set `ignore_delay`
        # to True.
        # See CmTask #3369 "Fix `Order.end_timestamp` and allow to ignore market
        # delay".
        ignore_delay = True
        prices_df = market_data.get_twap_price(
            start_timestamp,
            end_timestamp,
            timestamp_col_name,
            asset_ids,
            column,
            ignore_delay=ignore_delay,
        )
    else:
        raise ValueError(f"Invalid timing='{timing}'")
    if _TRACE:
        _LOG.trace("prices_df=\n%s", hpandas.df_to_str(prices_df, precision=2))
    # prices_df looks like:
    # ```
    #                            asset_id            start_datetime   price
    # end_datetime
    # 2000-01-01 09:35:00-05:00       101 2000-01-01 09:30:00-05:00  997.93
    # ```
    prices_srs = market_data.to_price_series(prices_df, column)
    # Check output.
    if _TRACE:
        _LOG.trace("prices_srs=\n%s", hpandas.df_to_str(prices_srs, precision=2))
    hdbg.dassert_isinstance(prices_srs, pd.Series)
    hdbg.dassert_is_not(prices_srs, None)
    hdbg.dassert(not prices_srs.isna().all(), "price_srs=%s", prices_srs)
    return prices_srs


def _get_execution_prices(
    market_data: mdata.MarketData,
    orders: List[oordorde.Order],
    *,
    # TODO(gp): Remove these defaults, if possible.
    timestamp_col: str = "end_datetime",
    column_remap: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Get the simulated execution prices of a list of orders.

    This method assumes that all orders in the list share a common:
      - order type
      - order start timestamp
      - order end timestamp

    :param column_remap: remap columns from `market_data` to the canonical
        columns (e.g., "bid", "ask", "price", "midpoint")
    :return: a df, e.g.,
        ```
                         price
        asset_id
        101             997.93
        ```
    """
    _LOG.debug(hprint.to_str("orders"))
    needed_columns = ["bid", "ask", "price", "midpoint"]
    if column_remap is None:
        column_remap = {col_name: col_name for col_name in needed_columns}
    hdbg.dassert_set_eq(column_remap.keys(), needed_columns)
    # Extract the property of the orders.
    (
        order_type,
        start_timestamp,
        end_timestamp,
        asset_ids,
    ) = _extract_order_properties(orders)
    # Parse the order type.
    _LOG.debug(
        hprint.to_str("order_type start_timestamp end_timestamp asset_ids")
    )
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
        # If perc == 0, we buy at the bid and sell at the ask (we collect the
        # spread).
        # If perc == 1, we buy at the ask and sell at the bid (we cross the spread).
        buy_prices = (1.0 - perc) * bids + perc * asks
        # _LOG.debug("buy_prices=\n%s", buy_prices)
        sell_prices = perc * bids + (1.0 - perc) * asks
        # _LOG.debug("sell_prices=\n%s", sell_prices)
        prices = is_buy * buy_prices + is_sell * sell_prices
    else:
        raise ValueError(f"Invalid type='{order_type}'")
    _LOG.debug(hprint.to_str("order_type start_timestamp end_timestamp"))
    #
    hdbg.dassert_isinstance(prices, pd.Series)
    if _TRACE:
        _LOG.trace("prices=\n%s", hpandas.df_to_str(prices, precision=2))
    return prices


# TODO(Paul): This function allows us to get the execution price for one order
#   at a time. It supports multiple (but untested) ways of doing this. Consider
#   vectorizing this code or else adding a switch to invoke order-by-order
#   processing.
# def _get_execution_price(
#     market_data: mdata.MarketData,
#     order: oordorde.Order,
#     *,
#     timestamp_col: str = "end_datetime",
#     column_remap: Optional[Dict[str, str]] = None,
# ) -> float:
#     """
#     Get the simulated execution price of an order.
#     """
#     hdbg.dassert_isinstance(order, oordorde.Order)
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


# #############################################################################
# Order filling
# #############################################################################


def fill_orders_fully_at_once(
    market_data: mdata.MarketData,
    timestamp_col: str,
    column_remap: Dict[str, str],
    orders: List[oordorde.Order],
) -> List[omfill.Fill]:
    """
    Execute orders fully (i.e., with no missing fills) with one single fill.

    :param market_data, timestamp_col, column_remap: used to retrieve
    prices
    :param orders: list of orders to execute
    """
    _LOG.debug(hprint.to_str("orders"))
    # TODO(Paul): The function `_get_execution_prices()` should be
    #  configurable.
    prices = _get_execution_prices(
        market_data,
        orders,
        timestamp_col=timestamp_col,
        column_remap=column_remap,
    )
    fills = []
    for order in orders:
        _LOG.debug(hprint.to_str("order"))
        # Extract the information from the order.
        end_timestamp = order.end_timestamp
        num_shares = order.diff_num_shares
        hdbg.dassert_in(order.asset_id, prices.index)
        price = prices[order.asset_id]
        if not np.isfinite(price):
            _LOG.warning("Unable to fill order=\n%s", order)
            continue
        # Build the corresponding fill.
        fill = omfill.Fill(order, end_timestamp, num_shares, price)
        _LOG.debug(hprint.to_str("fill"))
        fills.append(fill)
    return fills


def _split_in_child_twap_orders(
    orders: List[oordorde.Order],
    freq_as_pd_string: str,
) -> List[oordorde.Order]:
    """
    Split orders into corresponding child orders implementing a TWAP
    scheduling.
    """
    _LOG.debug(hprint.to_str("orders freq_as_pd_string"))
    order_type, start_timestamp, end_timestamp, _ = _extract_order_properties(
        orders
    )
    _LOG.debug(hprint.to_str("order_type, start_timestamp, end_timestamp"))
    # Split the parent order period into child order periods.
    child_intervals = pd.date_range(
        start_timestamp, end_timestamp, freq=freq_as_pd_string
    ).tolist()
    hdbg.dassert_eq(child_intervals[0], start_timestamp)
    hdbg.dassert_eq(child_intervals[-1], end_timestamp)
    num_intervals = len(child_intervals) - 1
    _LOG.debug(hprint.to_str("child_intervals num_intervals"))
    # Scan the orders.
    child_orders = []
    for order in orders:
        # Split each parent order.
        curr_num_shares = 0
        diff_num_shares = order.diff_num_shares / num_intervals
        # Scan the child intervals.
        for idx in range(num_intervals):
            child_start_timestamp = child_intervals[idx]
            child_end_timestamp = child_intervals[idx + 1]
            prev_num_shares = curr_num_shares
            curr_num_shares += diff_num_shares
            diff_num_shares = round(curr_num_shares) - round(prev_num_shares)
            order_tmp = oordorde.Order(
                # For simplicity, we assume that child orders have the same
                # creation timestamp as the parent order, since it should not
                # matter from the execution point of view.
                order.creation_timestamp,
                order.asset_id,
                order.type_,
                child_start_timestamp,
                child_end_timestamp,
                curr_num_shares,
                diff_num_shares,
            )
            child_orders.append(order_tmp)
        hpandas.dassert_approx_eq(curr_num_shares, order.diff_num_shares)
    return child_orders


def fill_orders_fully_twap(
    market_data: mdata.MarketData,
    timestamp_col: str,
    column_remap: Dict[str, str],
    orders: List[oordorde.Order],
    *,
    freq_as_pd_string: str = "1T",
) -> List[omfill.Fill]:
    """
    Completely execute orders with multiple fills according to a TWAP schedule
    (i.e., with child orders equally spaced in the parent order interval).

    Same params as `fill_orders_fully_at_once`.
    :param freq_as_pd_string: period used to split the execution interval using
        Pandas convention (e.g., "1T", "5T")
    """
    order_type, start_timestamp, end_timestamp, _ = _extract_order_properties(
        orders
    )
    hdbg.dassert(
        order_type.endswith("@twap"), "Invalid order type='%s'", order_type
    )
    # Split the orders in child orders over the period of time.
    child_orders = _split_in_child_twap_orders(orders, freq_as_pd_string)
    #
    fills = []
    for order in child_orders:
        fills_tmp = fill_orders_fully_at_once(
            market_data, timestamp_col, column_remap, [order]
        )
        hdbg.dassert_eq(len(fills_tmp), 1)
        fills.append(fills_tmp[0])
    return fills


# #############################################################################
# Broker
# #############################################################################


# TODO(gp): -> AbstractBroker
class Broker(abc.ABC, hobject.PrintableMixin):
    """
    Represent a broker to which we can place orders and receive fills back.

    In other words a broker adapts the internal representation of `Order` and
    `Fill`s to the ones that are specific to the target exchange.

    The broker:
    1) keeps an internal bookkeeping of orders submitted and deadlines when they
       are supposed to be executed
    2) passes the orders to the actual Order Management System (OMS) through an
       interface (e.g., DB, file system)
    3) waits for an acknowledgement of orders being submitted successfully by the OMS
    4) reports the order fills from the market

    The broker contains all the logic to handle fills:
    - in the set-up with `DataFramePortfolio`, the broker (specifically the
      `DataFrameBroker`) executes the orders in terms of price and fills.
    - in the set-up with `DatabasePortfolio` and `OrderProcessor`, the broker
      (specifically the `DatabaseBroker`) passes information to the `OrderProcessor`
      about the timing of the fills
    """

    # TODO(gp): This can be part of the state, instead of having to be reset.
    _submitted_order_id: int = 0

    def __init__(
        self,
        strategy_id: str,
        market_data: mdata.MarketData,
        universe_version: str,
        stage: str,
        *,
        account: Optional[str] = None,
        timestamp_col: str = "end_datetime",
        column_remap: Optional[Dict[str, str]] = None,
        log_dir: Optional[str] = None,
        limit_price_computer: Optional[
            oliprcom.AbstractLimitPriceComputer
        ] = None,
        child_order_quantity_computer: Optional[
            ochorquco.AbstractChildOrderQuantityComputer
        ] = None,
    ) -> None:
        """
        Constructor.

        :param strategy_id: trading strategy, e.g. 'C1b'
        :param market_data: interface to access trading and price data
        :param universe_version: version of the universe to use
        :param stage:
            - "preprod" preproduction stage
            - "local" debugging stage
        :param account: allow to have multiple accounts. `None` means not used
        :param timestamp_col: timestamp column label in the MarketData
        :param column_remap: (optional) remap columns when accessing a
            `MarketData` to retrieve execution prices. The required columns
            are "bid", "ask", "price", and "midpoint".
        :param log_dir: logging folder, e.g. '/shared_data/system_log_dir'
        :param limit_price_computer: AbstractLimitPriceComputer object
        :param child_order_quantity_computer: object for calculating filing schedule
        """
        _LOG.debug(
            hprint.to_str(
                "strategy_id market_data universe_version stage account timestamp_col column_remap log_dir"
            )
        )
        self.stage = stage
        self._strategy_id = strategy_id
        self._account = account
        self._universe_version = universe_version
        #
        hdbg.dassert_issubclass(market_data, mdata.MarketData)
        self.market_data = market_data
        self._get_wall_clock_time = market_data.get_wall_clock_time
        self._timestamp_col = timestamp_col
        self._column_remap = column_remap
        self._log_dir = log_dir
        # Track the orders for internal accounting, mapping wall clock when the
        # order was submitted to the submitted orders.
        self._orders: Dict[
            pd.Timestamp, List[oordorde.Order]
        ] = collections.OrderedDict()
        # Map a timestamp to the orders with that execution time deadline.
        self._deadline_timestamp_to_orders: Dict[
            pd.Timestamp, List[oordorde.Order]
        ] = collections.defaultdict(list)
        # Track the fills for internal accounting.
        self._fills: List[omfill.Fill] = []
        # Set the price calculation strategy.
        self._limit_price_computer = limit_price_computer
        self._child_order_quantity_computer = child_order_quantity_computer
        #
        _LOG.debug("After initialization:\n%s", repr(self))

    # ///////////////////////////////////////////////////////////////////////////
    # Print.
    # ///////////////////////////////////////////////////////////////////////////

    def __str__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_orders", "_deadline_timestamp_to_orders"])
        return super().__str__(attr_names_to_skip=attr_names_to_skip)

    def __repr__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_orders", "_deadline_timestamp_to_orders"])
        return super().__repr__(attr_names_to_skip=attr_names_to_skip)

    # ///////////////////////////////////////////////////////////////////////////
    # Accessors.
    # ///////////////////////////////////////////////////////////////////////////

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def account(self) -> str:
        return self._account

    @property
    def timestamp_col(self) -> str:
        return self._timestamp_col

    # ///////////////////////////////////////////////////////////////////////////
    # Accessors.
    # ///////////////////////////////////////////////////////////////////////////

    async def submit_orders(
        self,
        orders: List[oordorde.Order],
        order_type: str,
        *,
        execution_freq: Optional[str] = "1T",
        dry_run: bool = False,
    ) -> Tuple[str, pd.DataFrame]:
        """
        Submit a list of orders to the actual trading market.

        The handling of the orders can happen through:
        - DMA (direct market access) by submitting to the exchange directly (e.g.,
          Binance)
        - an actual third-party broker/OMS (e.g., Morgan Stanley, Goldman Sachs)

        The actual implementation is delegated to `_submit_orders()` in the
        subclasses.

        :param orders: orders to submit
        :param order_type: currently we assume that all the orders have the
            same "type" (e.g., TWAP, market). In the future, each order will
            have its own (potentially different) type
        :param orders: list of orders to submit
        :param dry_run: the order is created, logged in the log_dir, but not placed
            to the execution system (e.g., if the execution system requires a file
            on a file system, the file is not written on the file system)
        :return:
            - string: represent the receipt id of the submitted order (e.g., a
              filename if the order was saved in a file, a path of the file
              created on S3 with the order info)
            - dataframe: a representation of the orders to log in a file
        """
        if self._strategy_id == "null":
            _LOG.warning(
                "Using dry-run mode since strategy_id='%s'", self._strategy_id
            )
            dry_run = True
        wall_clock_timestamp = self._get_wall_clock_time()
        # Log the orders for internal bookkeeping.
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
        # Submit the orders to the trading exchange.
        _LOG.debug("Submitting orders=\n%s", oordorde.orders_to_string(orders))
        # Submit the orders to the OMS.
        if order_type.endswith("twap"):
            receipt, sent_orders = await self._submit_twap_orders(
                orders, execution_freq=execution_freq
            )
        # TODO(Grisha): unclear if we should check all order types here.
        elif order_type in [
            "limit",
            "market",
            "price@end",
            "price@start",
            "midpoint@end",
        ]:
            receipt, sent_orders = await self._submit_market_orders(
                orders, wall_clock_timestamp, dry_run=dry_run
            )
        else:
            raise ValueError("Invalid order_type='%s'" % order_type)
        # Build the Dataframe with the order result information.
        order_dicts = [order.to_dict() for order in sent_orders]
        order_df = pd.DataFrame(order_dicts)
        # Process the receipt.
        hdbg.dassert_isinstance(receipt, str)
        _LOG.debug("The receipt is '%s'", receipt)
        # Log the orders, if needed.
        if self._log_dir:
            wall_clock_time = self._get_wall_clock_time()
            wall_clock_time_str = wall_clock_time.strftime("%Y%m%d_%H%M%S")
            file_name = f"order.{wall_clock_time_str}.csv"
            file_name = os.path.join(self._log_dir, file_name)
            hio.create_enclosing_dir(file_name, incremental=True)
            order_df.to_csv(file_name)
            _LOG.debug("Saved log file '%s'", file_name)
        # Wait for acceptance.
        if not dry_run:
            _LOG.debug("Waiting for the accepted orders")
            await self._wait_for_accepted_orders(receipt)
        else:
            _LOG.warning(
                "Skipping waiting for the accepted orders because of dry_run=%s",
                dry_run,
            )
        return receipt, order_df

    @abc.abstractmethod
    def get_fills(self) -> List[omfill.Fill]:
        """
        Get any new fills filled since last invocation.

        This is used by `DataframePortfolio` and `OrderProcessor` to find out how
        to update the `Portfolio` state at the end of the bar.
        """
        ...

    # //////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # //////////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _get_next_submitted_order_id() -> int:
        submitted_order_id = Broker._submitted_order_id
        Broker._submitted_order_id += 1
        return submitted_order_id

    @abc.abstractmethod
    async def _submit_market_orders(
        self,
        orders: List[oordorde.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool = False,
    ) -> Tuple[str, pd.DataFrame]:
        """
        Submit orders to the actual trading system and wait for the orders to
        be accepted.

        Same interface as `submit_orders()`.
        """
        ...

    @abc.abstractmethod
    async def _wait_for_accepted_orders(
        self,
        order_receipt: str,
    ) -> None:
        """
        Wait until orders are accepted by the trading exchange or the actual
        OMS.
        """
        ...

    def _log_order_submissions(self, orders: List[oordorde.Order]) -> None:
        """
        Add the orders to the internal bookkeeping.
        """
        hdbg.dassert_container_type(orders, list, oordorde.Order)
        wall_clock_timestamp = self._get_wall_clock_time()
        _LOG.debug("wall_clock_timestamp=%s", wall_clock_timestamp)
        if self._orders:
            last_timestamp = next(reversed(self._orders))
            hdbg.dassert_lte(last_timestamp, wall_clock_timestamp)
        self._orders[wall_clock_timestamp] = orders

    def _get_limit_price_dict(
        self,
        data: pd.DataFrame,
        side: str,
        price_precision: int,
        execution_freq: pd.Timedelta,
        *,
        wave_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate limit prices (e.g., based on bid-ask data).

        This method requires a limit price computer object passed to the
        broker.

        :param data: data (e.g., recent bid/ask data of a particular
            asset)
        :param side: "buy" or "sell"
        :param price_precision: set the required decimal precision for
            limit price
        :param execution_freq: frequency of child order wave submission
        :param wave_id: number of the child order wave (e.g., a limit
            price computer may use this to calculate a different limit
            price for each wave)
        """
        hdbg.dassert_is_not(
            self._limit_price_computer,
            None,
            "This method requires a LimitPriceComputer",
        )
        price_dict = self._limit_price_computer.calculate_limit_price(
            data,
            side,
            price_precision,
            execution_freq,
            wave_id,
        )
        return price_dict
