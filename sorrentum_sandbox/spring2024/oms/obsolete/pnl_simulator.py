"""
Import as:

import oms.obsolete.pnl_simulator as oobpnsim
"""
import collections
import copy
import logging
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.htqdm as htqdm

_LOG = logging.getLogger(__name__)

# if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug = _LOG.info

# TODO(gp): Generalize for different intervals, besides 5 mins trading.
# TODO(gp): Extend for computing PnL on multiple stocks.
# TODO(gp): Consider ts -> datetime_, {start,end}_ts -> {start,end}_datetime for
#  uniformity with the rest of the code.
# TODO(gp): Find a better name for `future_snoop_allocation` that represents the
#  intent rather than how it's achieve it (e.g., `force_ideal_allocation`).


def _ts_to_str(ts: pd.Timestamp) -> str:
    """
    Print timestamp as string only in terms of time.

    This is useful to simplify the debug output of intraday trading.
    """
    val = "'%s'" % str(ts.time())
    return val


def get_random_market_data(num_samples: int, seed: int = 42) -> pd.DataFrame:
    """
    Generate random 1-minute market data in terms of `price`, `ask`, `bid`.
    """
    np.random.seed(seed)
    date_range = pd.date_range("2021-09-12 09:30", periods=num_samples, freq="1T")
    # Random walk for `price`.
    diff = np.random.normal(0, 1, size=len(date_range))
    diff = diff.cumsum()
    price = 100.0 + diff
    df = pd.DataFrame(price, index=date_range, columns=["price"])
    # Add `ask`, `bid` (note that `price` is not the midpoint).
    df["ask"] = price + np.abs(np.random.normal(0, 1, size=len(date_range)))
    df["bid"] = price - np.abs(np.random.normal(0, 1, size=len(date_range)))
    return df


def resample_data(df: pd.DataFrame, mode: str, seed: int = 42) -> pd.DataFrame:
    """
    Resample 1-min market data to 5 minutes to match the trading pattern and
    add random predictions.

    This data is used by the lag-based computation and has the same semantic as
    Dataflow approach.
    - intervals are (a, b]
    - everything is computed by the end of the interval whose timestamp is the label
      of the row
    - predictions are computed instantaneously using the data available up to b for
      an interval (a, b]
    """
    # Sample on 5 minute bars, labeling and close interval on the right.
    df_5mins = df.resample("5T", closed="right", label="right")
    if mode == "instantaneous":
        df_5mins = df_5mins.last()
    elif mode == "twap":
        # This allows to use TWAP prices instead of instantaneous prices, using the
        # same lag-based PnL code.
        # TODO(gp): We might need to delay 1 min to make it more similar to real-time.
        df_5mins = df_5mins.mean()
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    # Compute ret_0.
    df_5mins["ret_0"] = df_5mins["price"].pct_change()
    # Compute random predictions.
    np.random.seed(seed)
    vals = (np.random.random(df_5mins.shape[0]) >= 0.5) * 2.0 - 1.0
    # Zero out the last two predictions since we need two lags to realize (enter /
    # exit) a prediction.
    vals[-2:] = 0
    df_5mins["preds"] = vals
    return df_5mins


# #############################################################################


def get_example_market_data1() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Handcrafted small example.
    """
    date_range = pd.date_range("2021-09-12 09:30", periods=5, freq="5T")
    df_5mins = pd.DataFrame(
        [
            [100, 1.0],
            [90, -1.0],
            [80, 1.0],
            [90, 0.0],
            [70, 0.0],
        ],
        index=date_range,
        columns=["price", "preds"],
    )
    df_5mins["ret_0"] = df_5mins["price"].pct_change()
    df = df_5mins.copy()
    return df, df_5mins


def get_example_market_data2(
    num_samples: int, seed: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fixed random example.
    """
    # Generate some random data.
    df = get_random_market_data(num_samples, seed=seed)
    mode = "instantaneous"
    df_5mins = resample_data(df, mode)
    return df, df_5mins


# #############################################################################


def compute_pnl_level1(
    initial_wealth: float, df: pd.DataFrame, df_5mins: pd.DataFrame, prefix="sim1"
) -> Tuple[float, float, pd.DataFrame]:
    """
    In this implementation:

    - we act on each prediction at the time the prediction is available, by
      buying / selling looking into the future prices. Thus for each timestamp, we
      can associate each PnL to that prediction.
    - the execution is instantaneous at the end of the trading interval
    - there are no costs

    This is equivalent to the `compute_lag_pnl()` but using a little more detail.
    """
    columns = [
        "num_shares",
        "diff",
        "wealth",
    ]
    accounting = _create_accounting_stats(columns)

    def _update(key: str, value: float) -> None:
        prev_value = accounting[key][-1] if accounting[key] else None
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s=%s -> %s", key, prev_value, value)
        accounting[key].append(value)

    # Initial balance.
    wealth = initial_wealth
    # Skip the last two rows since we need two rows to enter / exit the position.
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    num_rows = df_5mins.shape[0] - 2
    for ts, row in tqdm(df_5mins[:-2].iterrows(), total=num_rows, file=tqdm_out):
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.frame("# ts=%s" % _ts_to_str(ts), char1="<"))
        pred = row["preds"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("wealth=%s", wealth)
        #
        ts_5 = ts + pd.DateOffset(minutes=5)
        hdbg.dassert_in(ts_5, df.index)
        price_5 = df.loc[ts_5]["price"]
        #
        ts_10 = ts + pd.DateOffset(minutes=10)
        hdbg.dassert_in(ts_10, df.index)
        price_10 = df.loc[ts_10]["price"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("pred=%s price_5=%s price_10=%s", pred, price_5, price_10)
        #
        num_shares = wealth / price_5
        # The magnitude of the prediction is interpreted as amount of leverage.
        num_shares *= abs(pred)
        _update("num_shares", num_shares)
        if pred > 0:
            # Go long.
            buy_pnl = num_shares * price_5
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Buy: @ ts_5=%s for price_5=$%s -> buy_pnl=$%s",
                    _ts_to_str(ts_5),
                    price_5,
                    buy_pnl,
                )
            sell_pnl = num_shares * price_10
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Sell: @ ts_10=%s for price_10=$%s -> sell_pnl=$%s",
                    _ts_to_str(ts_10),
                    price_10,
                    sell_pnl,
                )
            diff = -buy_pnl + sell_pnl
        elif pred < 0:
            # Short sell.
            sell_pnl = num_shares * price_5
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Short sell: @ ts_5=%s for price_5=$%s -> sell_pnl=$%s",
                    _ts_to_str(ts_5),
                    price_5,
                    sell_pnl,
                )
            buy_pnl = num_shares * price_10
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Cover: @ ts_10=%s for price_10=$%s -> buy_pnl=$%s",
                    _ts_to_str(ts_10),
                    price_10,
                    buy_pnl,
                )
            diff = sell_pnl - buy_pnl
        elif pred == 0:
            # Stay flat.
            diff = 0.0
        else:
            raise ValueError
        _update("diff", diff)
        wealth += diff
        _update("wealth", wealth)
    # Update the df with intermediate results.
    df_5mins = _append_accounting_df(df_5mins, accounting, prefix)
    # Little index gymnastic to introduce the initial value, given that the
    # semantic of the interval is at the end of the interval.
    col_name = _get_col_name("wealth", prefix)
    wealth_srs = pd.Series([initial_wealth] + df_5mins[col_name].values.tolist())
    # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug("wealth_srs=%s", wealth_srs)
    col_name = _get_col_name("pnl", prefix)
    df_5mins[col_name] = wealth_srs.pct_change().values[1:]
    # Compute total return.
    total_ret = (wealth - initial_wealth) / initial_wealth
    return wealth, total_ret, df_5mins


def compute_lag_pnl(df_5mins: pd.DataFrame, prefix: str = "lag") -> pd.DataFrame:
    """
    Compute PnL using vectorized equation as in post-processing of
    `ResultBundles`.
    """
    col_name = _get_col_name("pnl", prefix)
    df_5mins[col_name] = df_5mins["preds"] * df_5mins["ret_0"].shift(-2)
    tot_ret_lag = (1 + df_5mins[col_name]).prod() - 1
    return tot_ret_lag, df_5mins


# #############################################################################
# Price computation.
# #############################################################################

# if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug = _LOG.info
# if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug = lambda *_: 0

# debug_mode = True
debug_mode = False

# s/dbg.dassert/if debug_mode: hdbg.dassert/
# s/if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug/if debug_mode: if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug/


class MarketInterface:
    def __init__(
        self,
        df: pd.DataFrame,
        use_cache: bool,
        columns: Optional[List[str]] = None,
    ):
        self._use_cache = use_cache
        hdbg.dassert(df.index.is_monotonic_increasing)
        self._df = df
        if self._use_cache:
            _LOG.info("Caching")
            self._cached = {}
            hdbg.dassert_is_not(columns, None)
            columns = cast(List[str], columns)
            for column in tqdm(columns):
                hdbg.dassert_in(column, df.columns)
                self._cached[column] = df[column].to_dict()
            _LOG.info("Caching done")

    def get_instantaneous_price(
        self,
        ts: pd.Timestamp,
        column: str,
    ) -> float:
        price: float
        if self._use_cache:
            price = self._cached[column][ts]
        else:
            hdbg.dassert_in(ts, self._df.index)
            price = self._df.loc[ts][column]
            # idx = df.index.searchsorted(ts)
            # price: float = df.iloc[idx][column]
        hdbg.dassert(np.isfinite(price), "price=%s at ts=%s", price, ts)
        return price

    def get_twap_price(
        self, ts_start: pd.Timestamp, ts_end: pd.Timestamp, column: str
    ) -> float:
        """
        Compute TWAP of the column `column` in (ts_start, ts_end].

        E.g., TWAP for (9:30, 9:35] means avg(p(9:31), ..., p(9:35)).

        The function should be called `get_twa_price()` or `get_twap()`.
        """
        # TODO(gp): For use_cache=True it's not clear how to speed this up.
        hdbg.dassert_lt(ts_start, ts_end)
        # Get the slice (ts_start, ts_end] of prices.
        # TODO(gp): Maybe binary search can help.
        hdbg.dassert_in(ts_start, self._df.index)
        hdbg.dassert_in(ts_end, self._df.index)
        prices = self._df[ts_start:ts_end][column]
        prices = prices.iloc[1:]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("prices=\n%s", prices)
        hdbg.dassert_lte(1, prices.shape[0])
        price: float = prices.mean()
        return price


# #############################################################################
# Order
# #############################################################################


class Order:
    def __init__(
        self,
        mi: MarketInterface,
        type_: str,
        ts_start: pd.Timestamp,
        ts_end: pd.Timestamp,
        num_shares: float,
    ):
        """
        Represent an order executed in (ts_start, ts_end].
        """
        self._mi = mi
        # An order has 2 characteristics:
        # 1) what price is executed at, e.g.,
        #    - "price": the (historical) realized price
        #    - "midpoint": the midpoint
        #    - "full_spread": always cross the spread to hit ask or lift bid
        #    - "partial_spread": pay a percentage of spread
        # 2) timing semantic, i.e., when it is executed
        #    - "start": at beginning of interval
        #    - "end": at end of interval
        #    - "twap"
        #    - "vwap"
        self.type_ = type_
        hdbg.dassert_lt(ts_start, ts_end)
        self.ts_start = ts_start
        self.ts_end = ts_end
        self.num_shares = num_shares

    def __str__(self) -> str:
        return (
            f"Order: type={self.type_} "
            + f"ts=[{self.ts_start}, {self.ts_end}] "
            + f"num_shares={self.num_shares}"
        )

    @staticmethod
    def get_price(
        mi: MarketInterface,
        type_: str,
        ts_start: pd.Timestamp,
        ts_end: pd.Timestamp,
        num_shares: float,
    ) -> float:
        """
        Get price that one order with given parameters would achieve.
        """
        # Parse the type.
        config = type_.split("@")
        hdbg.dassert_eq(len(config), 2, "Invalid type_='%s'", type_)
        price_type, timing = config
        # Get the price depending on the price_type.
        if price_type in ("price", "midpoint"):
            column = price_type
            price = Order._get_price(mi, ts_start, ts_end, column, timing)
        elif price_type == "full_spread":
            # Cross the spread depending on buy / sell.
            if num_shares >= 0:
                column = "ask"
            else:
                column = "bid"
            price = Order._get_price(mi, ts_start, ts_end, column, timing)
        elif price_type.startswith("partial_spread"):
            perc = float(price_type.split("_")[2])
            hdbg.dassert_lte(0, perc)
            hdbg.dassert_lte(perc, 1.0)
            bid_price = Order._get_price(mi, ts_start, ts_end, "bid", timing)
            ask_price = Order._get_price(mi, ts_start, ts_end, "ask", timing)
            if num_shares >= 0:
                # We need to buy:
                # - if perc == 1.0 pay ask (i.e., pay full-spread)
                # - if perc == 0.5 pay midpoint
                # - if perc == 0.0 pay bid
                price = perc * ask_price + (1.0 - perc) * bid_price
            else:
                # We need to sell:
                # - if perc == 1.0 pay bid
                # - if perc == 0.5 pay midpoint
                # - if perc == 0.0 pay ask
                price = (1.0 - perc) * ask_price + perc * bid_price
        else:
            raise ValueError("Invalid type='%s'", type_)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "type=%s, ts_start=%s, ts_end=%s -> execution_price=%s",
                type_,
                ts_start,
                ts_end,
                price,
            )
        return price

    def get_execution_price(self) -> float:
        """
        Get price that this order executes at.
        """
        price = self.get_price(
            self._mi, self.type_, self.ts_start, self.ts_end, self.num_shares
        )
        return price

    def is_mergeable(self, rhs: "Order") -> bool:
        """
        Return whether this order can be merged (i.e., internal crossed) with
        `rhs`.
        """
        return (
            (self.type_ == rhs.type_)
            and (self.ts_start == rhs.ts_start)
            and (self.ts_end == rhs.ts_end)
        )

    def merge(self, rhs: "Order") -> "Order":
        """
        Accumulate current order with `rhs` and return the merged order.
        """
        # Only orders for the same type / interval, with different num_shares can
        # be merged.
        hdbg.dassert(self.is_mergeable(rhs))
        num_shares = self.num_shares + rhs.num_shares
        order = Order(
            self._mi, self.type_, self.ts_start, self.ts_end, num_shares
        )
        return order

    def copy(self) -> "Order":
        return copy.copy(self)

    @staticmethod
    def _get_price(
        mi: MarketInterface,
        ts_start: pd.Timestamp,
        ts_end: pd.Timestamp,
        column: str,
        timing: str,
    ) -> float:
        """
        Get the price corresponding to a certain column and timing.
        """
        if timing == "start":
            price = mi.get_instantaneous_price(ts_start, column)
        elif timing == "end":
            price = mi.get_instantaneous_price(ts_end, column)
        elif timing == "twap":
            price = mi.get_twap_price(ts_start, ts_end, column)
        else:
            raise ValueError("Invalid timing='%s'", timing)
        return price


def get_orders_to_execute(orders: List[Order], ts: pd.Timestamp) -> List[Order]:
    """
    Return the orders from `orders` that can be executed at timestamp `ts`.
    """
    orders.sort(key=lambda x: x.ts_start, reverse=False)
    hdbg.dassert_lte(orders[0].ts_start, ts)
    # TODO(gp): This is inefficient. Use binary search.
    curr_orders = []
    for order in orders:
        if order.ts_start == ts:
            curr_orders.append(order)
    return curr_orders


def orders_to_string(orders: List[Order]) -> str:
    return str(list(map(str, orders)))


# #############################################################################
# Accounting functions.
# #############################################################################

Accounting = Dict[str, List[float]]


def _create_accounting_stats(columns: List[str]) -> Accounting:
    accounting = collections.OrderedDict()
    for column in columns:
        accounting[column] = []
    return accounting


def _get_col_name(col_name: str, prefix: str) -> str:
    if prefix != "":
        col_name = prefix + "." + col_name
    return col_name


def _append_accounting_df(
    df_5mins: pd.DataFrame,
    accounting: Accounting,
    prefix: str,
) -> pd.DataFrame:
    """
    Update the df with intermediate results.
    """
    dfs = []
    for key, value in accounting.items():
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("key=%s", key)
        num_vals = len(accounting[key])
        buffer = [np.nan] * (df_5mins.shape[0] - num_vals)
        col_name = _get_col_name(key, prefix)
        df = pd.DataFrame(
            value + buffer, index=df_5mins.index, columns=[col_name]
        )
        hdbg.dassert_eq(df.shape[0], df_5mins.shape[0])
        dfs.append(df)
    df_5mins = pd.concat([df_5mins] + dfs, axis=1)
    return df_5mins


# TODO(gp): Move to MarketInterface?
def get_total_wealth(
    mi: MarketInterface,
    ts: pd.Timestamp,
    cash: float,
    holdings: float,
    column: str,
) -> float:
    """
    Return the value of the portfolio at time ts.
    """
    price = mi.get_instantaneous_price(ts, column)
    hdbg.dassert(np.isfinite(price), "price=%s", price)
    hdbg.dassert(np.isfinite(holdings), "holdings=%s", holdings)
    holdings_value = holdings * price
    # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug(
    #     "Marking at ts=%s holdings=%s at %s -> value=%s",
    #     _ts_to_str(ts),
    #     holdings,
    #     price,
    #     holdings_value,
    # )
    wealth = cash + holdings_value
    return wealth


# #############################################################################


def _get_orders_to_execute(ts: pd.Timestamp, orders: List[Order]) -> List[Order]:
    if True:
        if orders[0].ts_start == ts:
            return [orders.pop()]
        # hdbg.dassert_eq(len(orders), 1, "%s", orders_to_string(orders))
        assert 0
    orders_to_execute = get_orders_to_execute(orders, ts)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("orders_to_execute=%s", orders_to_string(orders_to_execute))
    # Merge the orders.
    merged_orders = []
    while orders_to_execute:
        order = orders_to_execute.pop()
        orders_to_execute_tmp = orders_to_execute[:]
        for next_order in orders_to_execute_tmp:
            if order.is_mergeable(next_order):
                order = order.merge(next_order)
                orders_to_execute_tmp.remove(next_order)
        merged_orders.append(order)
        orders_to_execute = orders_to_execute_tmp
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            "After merging:\n  merged_orders=%s\n  orders_to_execute=%s",
            orders_to_string(merged_orders),
            orders_to_string(orders_to_execute),
        )
    return merged_orders


def compute_pnl_level2(
    mi: MarketInterface,
    df_5mins: pd.DataFrame,
    initial_wealth: float,
    config: Dict[str, Any],
    prefix: str = "sim2",
) -> pd.DataFrame:
    print(df_5mins)
    hdbg.dassert(df_5mins.index.is_monotonic_increasing)
    # Create the accounting data structure.
    columns = [
        "target_n_shares",
        "cash",
        "holdings",
        "wealth",
        "diff_n_shares",
        #
        "filled_n_shares",
        "cash+1",
        "holdings+1",
        # "wealth.after",
    ]
    accounting = _create_accounting_stats(columns)
    preds = list(zip(df_5mins.index, df_5mins["preds"].values))
    # Run the simulation.
    accounting = _compute_pnl_level2(
        mi, preds, initial_wealth, config, accounting
    )
    # Update the df with intermediate results.
    df_5mins = _append_accounting_df(df_5mins, accounting, prefix)
    pnl = _get_col_name("pnl", prefix)
    wealth = _get_col_name("wealth", prefix)
    df_5mins[pnl] = df_5mins[wealth].pct_change()
    return df_5mins


def _compute_pnl_level2(
    mi: MarketInterface,
    preds: List[Tuple[pd.Timestamp, float]],
    initial_wealth: float,
    config: Dict[str, Any],
    accounting: Accounting,
) -> Accounting:
    """
    In this implementation we use the prediction to place orders, that are
    realized over the span of two intervals of time (i.e., two lags).

    - The PnL is realized two intervals of time after the corresponding prediction
    - The columns reported in the df are for the beginning of the interval of time
    - The columns ending with `+1` represent what happens in the next interval
      of time
    """

    def _update(key: str, value: float) -> None:
        prev_value = accounting[key][-1] if accounting[key] else None
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s=%s -> %s", key, prev_value, value)
        accounting[key].append(value)

    orders: List[Order] = []
    # Initial balance.
    holdings = 0.0
    cash = initial_wealth
    # Cache some variables used many times.
    last_index, _ = preds[-1]
    price_column = config["price_column"]
    offset_5min = pd.DateOffset(minutes=5)
    order_type = config["order_type"]
    #
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    num_rows = len(preds)
    for ts, pred in tqdm(preds, total=num_rows, file=tqdm_out):
        # if _LOG.isEnabledFor(logging.DEBUG): _LOG.debug(hprint.frame("# ts=%s" % _ts_to_str(ts)))
        # 1) Place orders based on the predictions, if needed.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("pred=%s", pred)
        hdbg.dassert(np.isfinite(pred), "pred=%s", pred)
        # Mark the portfolio to market.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Mark portfolio to market")
        wealth = get_total_wealth(mi, ts, cash, holdings, price_column)
        hdbg.dassert(np.isfinite(wealth), "wealth=%s", wealth)
        _update("wealth", wealth)
        if ts == last_index:
            # For the last timestamp we only need to mark to market, but not post
            # any more orders.
            continue
        # Use current price to convert forecasts in position intents.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Decide how much to trade")
        # Enter position between [0, 5].
        ts_start = ts
        ts_end = ts + offset_5min
        if config.get("future_snoop_allocation", False):
            # - In the vectorized PnL case we assume we work in terms of dollar and
            #   not shares: we assume we can buy the entire amount of wealth in terms
            #   of shares (i.e., we assume that we know the future execution price)
            # - In the real set-up, we need to place order for a certain number of
            #   shares before we know what price we will get. Thus we use the price
            #   at the decision time to estimate the number of shares, which means
            #   that we can't always invest exactly the whole available wealth.
            # The direction of the trade is enough to determine the price.
            num_shares_proxy = pred
            price_0 = Order.get_price(
                mi, order_type, ts_start, ts_end, num_shares_proxy
            )
            hdbg.dassert(np.isfinite(price_0), "price_0=%s", pred)
            wealth_to_allocate = get_total_wealth(
                mi, ts_end, cash, holdings, price_column
            )
        else:
            price_0 = mi.get_instantaneous_price(ts, price_column)
            wealth_to_allocate = wealth
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("price_0=%s", price_0)
        target_num_shares = wealth_to_allocate / price_0
        target_num_shares *= pred
        _update("target_n_shares", target_num_shares)
        _update("cash", cash)
        _update("holdings", holdings)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Place orders")
        diff = target_num_shares - holdings
        _update("diff_n_shares", diff)
        # Create order.
        order = Order(mi, order_type, ts_start, ts_end, diff)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("order=%s", order)
        orders.append(order)
        # 2) Execute the orders.
        # INV: When we get here all the orders for the current timestamp `ts` have
        # been placed since we acted on the predictions for `ts` and we can't place
        # orders in the past.
        # Find all the orders with the current timestamp.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Get orders to execute")
        merged_orders = _get_orders_to_execute(ts, orders)
        # Execute the merged orders.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("# Execute orders")
        # TODO(gp): We rely on the assumption that order span only one time step.
        #  so we can evaluate an order starting now and ending in the next time step.
        #  A more accurate simulation requires to attach "callbacks" representing
        #  actions to timestamp.
        # TODO(gp): For now there should be at most one order.
        hdbg.dassert_lte(len(merged_orders), 1)
        order = merged_orders[0]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("order=%s", order)
        num_shares = order.num_shares
        _update("filled_n_shares", num_shares)
        holdings += num_shares
        _update("holdings+1", holdings)
        executed_price = order.get_execution_price()
        cash -= executed_price * num_shares
        _update("cash+1", cash)
    if use_profiler:
        profiler.print_stats()
    return accounting


use_profiler = False
# use_profiler = True


if use_profiler:
    import line_profiler

    profiler = line_profiler.LineProfiler()
    _compute_pnl_level2 = profiler(_compute_pnl_level2)
