"""
Import as:

import core.finance.execution as cfinexec
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

import core.finance.resampling as cfinresa
import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): -> private
def generate_limit_order_price(
    df: pd.DataFrame,
    bid_col: str,
    ask_col: str,
    buy_reference_price_col: str,
    sell_reference_price_col: str,
    buy_spread_frac_offset: float,
    sell_spread_frac_offset: float,
    subsample_freq: str,
    freq_offset: str,
    ffill_limit: int,
    tick_decimals: int,
) -> pd.DataFrame:
    """
    Generate limit order prices from sub-sampled reference prices and an
    offset.

    E.g., place order 5% from the bid or ask level, repricing every 2 minutes.

    :param df: datetime-indexed dataframe with a reference price column
    :param bid_col: name of column with last bid price for bar
    :param ask_col: like `bid_col` but for ask
    :param buy_reference_price_col: name of df column with reference prices
        for submitting buy limit orders
    :param sell_reference_price_col: like `buy_reference_price_col` but for
        submitting sell limit orders
    :param buy_spread_frac_offset: fraction of quoted spread to add to the
        buy reference price to determine the limit price
    :param sell_spread_frac_offset: fraction of quoted spread to add to the
        sell reference price to determine the limit price
    :param subsample_freq: resampling frequency to use for subsampling, e.g.,
        "15T" for a dataframe of one-minute bars
    :param freq_offset: offset to use for subsampling; this can be used to
        simulate expected processing or computation times
    :param ffill_limit: number of ffill bars to propagate limit orders, e.g.,
        if we use one-minute bars, take `subsample_freq="15T"`, and let
        `ffill_limit=4`, then the execution window will be 1 + 4 = 5 minutes.
    :param tick_decimals: number of decimals to round prices to
    :return: a dataframe of limit order prices named `{buy,sell}_limit_order_price`
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=True, strictly_increasing=True
    )
    required_cols = [
        bid_col,
        ask_col,
        buy_reference_price_col,
        sell_reference_price_col,
    ]
    hdbg.dassert_is_subset(required_cols, df.columns)
    hdbg.dassert_isinstance(buy_spread_frac_offset, float)
    hdbg.dassert_isinstance(sell_spread_frac_offset, float)
    hdbg.dassert_isinstance(subsample_freq, str)
    hdbg.dassert_isinstance(freq_offset, str)
    hdbg.dassert_isinstance(ffill_limit, int)
    # Subsample the reference price col, e.g., take samples every "15T" on a
    # "1T" series.
    buy_subsampled = cfinresa.resample(
        df[buy_reference_price_col],
        rule=subsample_freq,
        offset=freq_offset,
    ).last()
    sell_subsampled = cfinresa.resample(
        df[sell_reference_price_col],
        rule=subsample_freq,
        offset=freq_offset,
    ).last()
    quoted_spread = df[ask_col] - df[bid_col]
    # Apply a dollar offset to the subsampled prices.
    buy_subsampled = buy_subsampled + buy_spread_frac_offset * quoted_spread
    buy_subsampled = buy_subsampled.round(tick_decimals).rename(
        "buy_limit_order_price"
    )
    # Treat each subsampled limit price as the initiation of a new order.
    buy_order_num = np.sign(buy_subsampled).abs().cumsum().rename("buy_order_num")
    # Perform the analogous operations for sells.
    sell_subsampled = sell_subsampled + sell_spread_frac_offset * quoted_spread
    sell_subsampled = sell_subsampled.round(tick_decimals).rename(
        "sell_limit_order_price"
    )
    sell_order_num = (
        np.sign(sell_subsampled).abs().cumsum().rename("sell_order_num")
    )
    # Combine buy and sell limits along with buy and sell order numbers.
    subsampled = pd.concat(
        [buy_subsampled, sell_subsampled, buy_order_num, sell_order_num], axis=1
    )
    # Reindex to the original frequency (imputing NaNs).
    subsampled = subsampled.reindex(index=df.index)
    # Forward fill the limit prices and order numbers `ffill_limit` steps.
    subsampled = subsampled.ffill(limit=ffill_limit)
    return subsampled


# TODO(gp): -> private
def estimate_limit_order_execution(
    df: pd.DataFrame,
    bid_col: str,
    ask_col: str,
    buy_limit_price_col: str,
    sell_limit_price_col: str,
    buy_order_num_col: str,
    sell_order_num_col: str,
) -> pd.Series:
    """
    Estimate passive fills.

    :param df: datetime-indexed dataframe with price data
    :param bid_col: name of column with last bid price for bar
    :param ask_col: like `bid_col` but for ask
    :param buy_limit_price_col: name of column with limit order price; NaN
        represents no order.
    :param sell_limit_price_col: like `buy_limit_price_col` but for selling
    :param buy_order_num_col: col with numerical order numbers for buys
    :param sell_order_num_col: col with numerical order numbers for sells
    :return: dataframe with two bool columns, `limit_buy_executed` and
        `limit_sell_executed`
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=True, strictly_increasing=True
    )
    hdbg.dassert_isinstance(bid_col, str)
    hdbg.dassert_isinstance(ask_col, str)
    # Ensure that all required columns are in the dataframe.
    cols = [
        bid_col,
        ask_col,
        buy_limit_price_col,
        sell_limit_price_col,
        buy_order_num_col,
        sell_order_num_col,
    ]
    hdbg.dassert_is_subset(cols, df.columns)
    # TODO(Paul): Add a switch to allow in/equality.
    # Determine buy execution times.
    # Delay by one bar the limit price columns. The columns are indexed by
    # knowledge time (the limit price to use is known at end-of-bar), and so
    # earliest execution takes place in the next bar.
    buy_limit_marketable = (
        df[ask_col] <= df[buy_limit_price_col].shift(1)
    ).rename("limit_buy_marketable")
    buy_times = pd.concat(
        [
            pd.Series(df.index, df.index, name="timestamp"),
            df[buy_order_num_col].shift(1),
        ],
        axis=1,
    )
    buy_times = buy_times.loc[buy_limit_marketable]
    buy_limit_executed = buy_times.groupby(buy_order_num_col)["timestamp"].min()
    # Determine sell execution times.
    sell_limit_marketable = (
        df[bid_col] >= df[sell_limit_price_col].shift(1)
    ).rename("limit_sell_marketable")
    sell_times = pd.concat(
        [
            pd.Series(df.index, df.index, name="timestamp"),
            df[sell_order_num_col].shift(1),
        ],
        axis=1,
    )
    sell_times = sell_times.loc[sell_limit_marketable]
    sell_limit_executed = sell_times.groupby(sell_order_num_col)[
        "timestamp"
    ].min()
    # Determine buy/sell trade prices.
    # - If a buy limit price is not marketable, it executes at the limit
    #   on touch and is removed from the book.
    # - If a buy limit price is marketable, it executes at the ask and does not
    #   stay on the book.
    buy_price = df[buy_limit_price_col].shift(1)
    # TODO(Paul): Add a switch for in/equality.
    # TODO(Paul): Consider adding this to the output as a boolean column.
    use_ask = df[buy_limit_price_col].shift(1) >= df[ask_col].shift(1)
    # Treat the buy like a market order.
    buy_price.loc[use_ask] = df[ask_col].shift(1)
    buy_trades = buy_price.loc[buy_limit_executed]
    # Perform analogous operations for sells.
    sell_price = df[sell_limit_price_col].shift(1)
    use_bid = df[sell_limit_price_col].shift(1) <= df[bid_col].shift(1)
    sell_price.loc[use_bid] = df[bid_col].shift(1)
    sell_trades = sell_price.loc[sell_limit_executed]
    # Reindex according to original index.
    buy_trades = buy_trades.reindex(index=df.index).rename("buy_trade_price")
    sell_trades = sell_trades.reindex(index=df.index).rename("sell_trade_price")
    buy_limit_executed = pd.Series(
        True, index=buy_limit_executed, name="limit_buy_executed"
    ).reindex(index=df.index, fill_value=False)
    sell_limit_executed = pd.Series(
        True, index=sell_limit_executed, name="limit_sell_executed"
    ).reindex(index=df.index, fill_value=False)
    # Combine bool and trade price cols.
    execution_df = pd.concat(
        [
            buy_limit_executed,
            sell_limit_executed,
            buy_trades,
            sell_trades,
        ],
        axis=1,
    )
    return execution_df


# TODO(gp): -> private
def generate_limit_orders_and_estimate_execution(
    df: pd.DataFrame,
    bid_col: str,
    ask_col: str,
    buy_reference_price_col: str,
    sell_reference_price_col: str,
    buy_spread_frac_offset: float,
    sell_spread_frac_offset: float,
    subsample_freq: str,
    freq_offset: str,
    ffill_limit: int,
    tick_decimals: int,
) -> pd.DataFrame:
    """
    Generate limit buy/sells and estimate execution.

    :param df: datetime-indexed dataframe with price data
    :param bid_col: bid col for estimating buy limit order execution
    :param ask_col: ask col for estimating sell limit order execution
    :param buy_reference_price_col: reference price col for buy limit orders
    :param buy_spread_frac_offset: amount to add to buy reference price
    :param sell_reference_price_col: reference price col for sell limit orders
    :param sell_spread_frac_offset: amount to add to sell reference price
    :param subsample_freq: as in `generate_limit_order_price()`
    :param freq_offset: as in `generate_limit_order_price()`
    :param ffill_limit: as in `generate_limit_order_price()`
    :param tick_decimals: as in `generate_limit_order_price()`
    :return: dataframe with limit order price and execution cols
    """
    limit_order_prices = generate_limit_order_price(
        df,
        bid_col,
        ask_col,
        buy_reference_price_col,
        sell_reference_price_col,
        buy_spread_frac_offset,
        sell_spread_frac_offset,
        subsample_freq,
        freq_offset,
        ffill_limit,
        tick_decimals,
    )
    execution_df = estimate_limit_order_execution(
        pd.concat([df, limit_order_prices], axis=1),
        bid_col,
        ask_col,
        "buy_limit_order_price",
        "sell_limit_order_price",
        "buy_order_num",
        "sell_order_num",
    )
    limit_price_and_execution_df = pd.concat(
        [limit_order_prices, execution_df],
        axis=1,
    )
    return limit_price_and_execution_df


def apply_execution_prices_to_trades(
    trade: pd.DataFrame,
    buy_price: pd.DataFrame,
    sell_price: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply buy/sell prices to trades.
    """
    # Sanity-check inputs.
    hpandas.dassert_time_indexed_df(
        trade, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        buy_price, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        sell_price, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_axes_equal(buy_price, trade)
    hpandas.dassert_axes_equal(sell_price, trade)
    # Ensure all buys may be filled.
    use_buy_price = trade > 0
    no_buy_price_available = buy_price.isna()
    # TODO(Paul): Factor out trimming a boolean df to rows and cols with
    # `True`.
    no_buy_fills = use_buy_price & no_buy_price_available
    no_buy_fills = no_buy_fills.loc[no_buy_fills.any(axis=1)]
    hdbg.dassert(not no_buy_fills.any().any(), msg=str(no_buy_fills))
    use_buy_price = use_buy_price.replace(True, 1.0).replace(False, np.nan)
    # Ensure all sells may be filled.
    use_sell_price = trade < 0
    no_sell_price_available = sell_price.isna()
    no_sell_fills = use_sell_price & no_sell_price_available
    no_sell_fills = no_sell_fills.loc[no_sell_fills.any(axis=1)]
    hdbg.dassert(not no_sell_fills.any().any(), msg=str(no_sell_fills))
    use_sell_price = use_sell_price.replace(True, 1.0).replace(False, np.nan)
    # Splice buy and sell prices.
    execution_price = buy_price.multiply(use_buy_price).add(
        sell_price.multiply(use_sell_price), fill_value=0.0
    )
    return execution_price


def compute_bid_ask_execution_quality(
    df: pd.DataFrame,
    bid_col: str,
    ask_col: str,
    buy_trade_price_col: str,
    sell_trade_price_col: str,
) -> pd.DataFrame:
    """
    Compute trade price stats relative to bid/ask prices.

    :param bid_col: top-of-book bid price col
    :param ask_col: top-of-book ask price col
    :param buy_trade_price_col: price at which a "buy" was executed
    :param sell_trade_price_col: price at which a "sell" was executed
    :return: dataframe with several notions of execution quality, in notional
        amounts and relative amounts (bps or pct)
    """
    data = []
    # Compute midpoint and spread.
    bid_ask_midpoint = 0.5 * (df[bid_col] + df[ask_col])
    bid_ask_midpoint.name = "bid_ask_midpoint"
    data.append(bid_ask_midpoint)
    spread_notional = df[ask_col] - df[bid_col]
    spread_notional.name = "spread_notional"
    data.append(spread_notional)
    spread_bps = 1e4 * spread_notional / bid_ask_midpoint
    spread_bps.name = "spread_bps"
    data.append(spread_bps)
    # Compute buy trade price improvement.
    buy_trade_price_improvement_notional = df[ask_col] - df[buy_trade_price_col]
    buy_trade_price_improvement_notional.name = (
        "buy_trade_price_improvement_notional"
    )
    data.append(buy_trade_price_improvement_notional)
    buy_trade_price_improvement_bps = (
        1e4 * buy_trade_price_improvement_notional / df[ask_col]
    )
    buy_trade_price_improvement_bps.name = "buy_trade_price_improvement_bps"
    data.append(buy_trade_price_improvement_bps)
    buy_trade_price_improvement_spread_pct = (
        1e2 * buy_trade_price_improvement_notional / spread_notional
    )
    buy_trade_price_improvement_spread_pct.name = (
        "buy_trade_price_improvement_spread_pct"
    )
    data.append(buy_trade_price_improvement_spread_pct)
    # Compute sell trade price improvement.
    sell_trade_price_improvement_notional = df[sell_trade_price_col] - df[bid_col]
    sell_trade_price_improvement_notional.name = (
        "sell_trade_price_improvement_notional"
    )
    data.append(sell_trade_price_improvement_notional)
    sell_trade_price_improvement_bps = (
        1e4 * sell_trade_price_improvement_notional / df[bid_col]
    )
    sell_trade_price_improvement_bps.name = "sell_trade_price_improvement_bps"
    data.append(sell_trade_price_improvement_bps)
    sell_trade_price_improvement_spread_pct = (
        1e2 * sell_trade_price_improvement_notional / spread_notional
    )
    sell_trade_price_improvement_spread_pct.name = (
        "sell_trade_price_improvement_spread_pct"
    )
    data.append(sell_trade_price_improvement_spread_pct)
    # Compute buy trade slippage.
    buy_trade_midpoint_slippage_notional = (
        df[buy_trade_price_col] - bid_ask_midpoint
    )
    buy_trade_midpoint_slippage_notional.name = (
        "buy_trade_midpoint_slippage_notional"
    )
    data.append(buy_trade_midpoint_slippage_notional)
    buy_trade_midpoint_slippage_bps = (
        1e4 * buy_trade_midpoint_slippage_notional / bid_ask_midpoint
    )
    buy_trade_midpoint_slippage_bps.name = "buy_trade_midpoint_slippage_bps"
    data.append(buy_trade_midpoint_slippage_bps)
    # Compute sell trade slippage.
    sell_trade_midpoint_slippage_notional = (
        bid_ask_midpoint - df[sell_trade_price_col]
    )
    sell_trade_midpoint_slippage_notional.name = (
        "sell_trade_midpoint_slippage_notional"
    )
    data.append(sell_trade_midpoint_slippage_notional)
    sell_trade_midpoint_slippage_bps = (
        1e4 * sell_trade_midpoint_slippage_notional / bid_ask_midpoint
    )
    sell_trade_midpoint_slippage_bps.name = "sell_trade_midpoint_slippage_bps"
    data.append(sell_trade_midpoint_slippage_bps)
    # Combine computed columns.
    df_out = pd.concat(data, axis=1)
    return df_out


def compute_ref_price_execution_quality(
    df: pd.DataFrame,
    buy_trade_reference_price_col: str,
    sell_trade_reference_price_col: str,
    buy_trade_price_col: str,
    sell_trade_price_col: str,
) -> pd.DataFrame:
    """
    Compute buy/sell slippage in notional and bps wrt reference price.

    Analogous to `compute_bid_ask_execution_quality()` but with reference
    prices that are not necessarily bid/ask prices.

    :param df: DataFrame, possibly with multiple column levels (assets in
        inner level)
    :param buy_trade_reference_price_col: name of col with reference (e.g.,
        TWAP, VWAP) price for buy orders
    :param sell_trade_reference_price_col: name of col with reference price
        for sell orders; may be the same as `buy_trade_reference_price_col`
    :param buy_trade_price_col: name of col with buy trade price
    :param sell_trade_price_col: name of col with sell trade price
    :return: DataFrame, possibly with multiple column levels, of notional and
        relative slippage
    """
    # Compute buy trade slippage.
    buy_trade_slippage_notional = (
        df[buy_trade_price_col] - df[buy_trade_reference_price_col]
    )
    buy_trade_slippage_bps = 1e4 * buy_trade_slippage_notional.divide(
        df[buy_trade_reference_price_col]
    )
    # Compute sell trade slippage.
    sell_trade_slippage_notional = (
        df[sell_trade_reference_price_col] - df[sell_trade_price_col]
    )
    sell_trade_slippage_bps = 1e4 * sell_trade_slippage_notional.divide(
        df[sell_trade_reference_price_col]
    )
    dict_ = {
        "buy_trade_slippage_notional": buy_trade_slippage_notional,
        "buy_trade_slippage_bps": buy_trade_slippage_bps,
        "sell_trade_slippage_notional": sell_trade_slippage_notional,
        "sell_trade_slippage_bps": sell_trade_slippage_bps,
    }
    df_out = pd.concat(dict_, axis=1)
    return df_out


def compute_trade_vs_limit_execution_quality(
    df: pd.DataFrame,
    buy_limit_price_col: str,
    sell_limit_price_col: str,
    buy_trade_price_col: str,
    sell_trade_price_col: str,
) -> pd.DataFrame:
    data = []
    # Compute buy trade slippage.
    buy_trade_limit_slippage_notional = (
        df[buy_trade_price_col] - df[buy_limit_price_col]
    )
    buy_trade_limit_slippage_notional.name = "buy_trade_limit_slippage_notional"
    data.append(buy_trade_limit_slippage_notional)
    buy_trade_limit_slippage_bps = (
        1e4 * buy_trade_limit_slippage_notional / df[buy_limit_price_col]
    )
    buy_trade_limit_slippage_bps.name = "buy_trade_limit_slippage_bps"
    data.append(buy_trade_limit_slippage_bps)
    # Compute sell trade slippage.
    sell_trade_limit_slippage_notional = (
        df[sell_limit_price_col] - df[sell_trade_price_col]
    )
    sell_trade_limit_slippage_notional.name = "sell_trade_limit_slippage_notional"
    data.append(sell_trade_limit_slippage_notional)
    sell_trade_limit_slippage_bps = (
        1e4 * sell_trade_limit_slippage_notional / df[sell_limit_price_col]
    )
    sell_trade_limit_slippage_bps.name = "sell_trade_limit_slippage_bps"
    data.append(sell_trade_limit_slippage_bps)
    # Combine computed columns.
    df_out = pd.concat(data, axis=1)
    return df_out


def simulate_limit_order_execution(
    open_price: float,
    close_price: float,
    volatility: float,
    limit_price: float,
    is_buy: bool,
    delay_as_frac: float,
    n_steps: int,
    seed: int,
) -> Tuple[int, float]:
    """
    Simulate the execution of a limit order.

    Interpolate price between `open_price` and `close_price` using a
    Brownian bridge and specified `volatility`.

    :param open_price: beginning-of-bar price
    :param close_price: end-of-bar price
    :param volatility: close-to-close volatility of return
    :param limit_price: price of limit order
    :param is_buy: boolean to indicate side
    :param delay_as_frac: percentage of bar consumed by order submission
        latency
    :param n_steps: number of steps in Brownian bridge
    :param seed: seed for random increments
    :return: (step of fill, execution price), or (-1, np.nan) if no fill
    """
    bb = costatis.interpolate_with_brownian_bridge(
        open_price,
        close_price,
        volatility,
        n_steps,
        seed,
    )
    num_steps_to_skip = int(delay_as_frac * n_steps)
    # If side is "buy", use reflection to convert the problem into an
    # equivalent "sell" problem, then reflect again to recover the
    # correct result.
    if is_buy:
        step, val = costatis.get_first_threshold_upcrossing(
            -bb,
            -limit_price,
            num_steps_to_skip=num_steps_to_skip,
        )
        val *= -1
    else:
        step, val = costatis.get_first_threshold_upcrossing(
            bb,
            limit_price,
            num_steps_to_skip=num_steps_to_skip,
        )
    return step, val
