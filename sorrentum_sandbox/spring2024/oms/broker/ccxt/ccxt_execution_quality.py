"""
Import as:

import oms.broker.ccxt.ccxt_execution_quality as obccexqu
"""
import logging
from typing import Dict, Tuple, Union

import numpy as np
import pandas as pd

import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu

_LOG = logging.getLogger(__name__)


# #############################################################################
# Child order handling.
# #############################################################################


# TODO(Paul): Note that this is for ccxt orders.
def get_limit_order_price(
    orders: pd.DataFrame, *, freq: str = "1s"
) -> pd.DataFrame:
    """
    Get limit order prices from orders.
    """
    # Generate DataFrame of buy limit orders.
    buys = orders[orders["diff_num_shares"] > 0]
    buys = buys.pivot(
        index="creation_timestamp", columns="asset_id", values="limit_price"
    )
    buys = buys.resample(freq, closed="right", label="right").mean()
    # Generate DataFrame of sell limit orders.
    sells = orders[orders["diff_num_shares"] < 0]
    sells = sells.pivot(
        index="creation_timestamp", columns="asset_id", values="limit_price"
    )
    sells = sells.resample(freq, closed="right", label="right").mean()
    #
    col_set = buys.columns.union(sells.columns)
    col_set = col_set.sort_values()
    buys = buys.reindex(columns=col_set)
    sells = sells.reindex(columns=col_set)
    #
    dict_ = {
        "buy_limit_order_price": buys,
        "sell_limit_order_price": sells,
    }
    df = pd.concat(dict_, axis=1)
    return df


def align_ccxt_orders_and_fills(
    child_order_response_df: pd.DataFrame,
    fills_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
        "order",
        "order_type",
        "time_in_force",
        "post_only",
        "reduce_only",
        "side",
        "order_price",
        "stop_price",
        "order_amount",
        "order_update_timestamp",
        "order_update_datetime",
    ]
    order_responses = child_order_response_df[cols].set_index("order")
    order_fills = obccagfu.aggregate_fills_by_order(fills_df)
    filled_orders = pd.merge(
        order_responses,
        order_fills,
        how="inner",
        left_index=True,
        right_index=True,
    )
    # TODO(Paul): Compute price improvement for filled orders.
    unfilled_orders = order_responses.loc[
        order_responses.index.difference(order_fills.index)
    ]
    return filled_orders, unfilled_orders


# #############################################################################


def compute_filled_order_execution_quality(
    df: pd.DataFrame,
    tick_decimals: int,
) -> pd.DataFrame:
    """
    Compute price improvement and fill rate for filled orders.

    :param df: a `filled_orders` DataFrame, from
        `align_ccxt_orders_and_fills()`
    :param tick_decimals: number of decimals of rounding for order quantities.
        This helps suppress machine precision artifacts.
    :return: DataFrame indexed by order id with the following columns:
      - direction (buy or sell as +1 or -1, respectively)
      - price_improvement_notional (with respect to limit price)
      - price_improvement_bps
      - underfill_quantity
      - underfill_pct
      - underfill_notional_at_limit_price
      - underfill_notional_at_transaction_price
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    required_cols = [
        "amount",
        "order_amount",
        "order_price",
        "price",
        "side",
    ]
    hdbg.dassert_is_subset(required_cols, df.columns)
    #
    srs_list = []
    is_buy = df["side"] == "buy"
    #
    direction = np.round(2 * is_buy.astype(int) - 1).rename("direction")
    srs_list.append(direction)
    #
    price_improvement_notional = (
        direction.multiply(df["order_price"] - df["price"])
        .round(tick_decimals)
        .replace(-0.0, 0.0)
        .rename("price_improvement_notional")
    )
    srs_list.append(price_improvement_notional)
    #
    price_improvement_bps = 1e4 * (
        price_improvement_notional / df["order_price"]
    ).rename("price_improvement_bps")
    srs_list.append(price_improvement_bps)
    #
    underfill_quantity = (df["order_amount"] - df["amount"]).rename(
        "underfill_quantity"
    )
    srs_list.append(underfill_quantity)
    #
    underfill_pct = (underfill_quantity / df["order_amount"]).rename(
        "underfill_pct"
    )
    srs_list.append(underfill_pct)
    #
    underfill_notional_at_limit_price = (
        underfill_quantity * df["order_price"]
    ).rename("underfill_notional_at_limit_price")
    srs_list.append(underfill_notional_at_limit_price)
    #
    underfill_notional_at_transaction_price = (
        underfill_quantity * df["price"]
    ).rename("underfill_notional_at_transaction_price")
    srs_list.append(underfill_notional_at_transaction_price)
    #
    return pd.concat(srs_list, axis=1)


def _check_buy_sell_overlap(fills_df: pd.DataFrame) -> None:
    """
    Check that `buy_count` and `sell_count` values don't overlap in the same
    timestamp index and are non-negative.

    There are 2 valid cases:
      - one is more that zero, another one is zero
      - both of them are zero

    :param fills_df: a fills dataframe aggregated by bar
    """
    for timestamp, sub_df in fills_df.groupby(level="bar_end_datetime"):
        # Check that buy and sell counts don't overlap.
        valid = (sub_df["buy_count"] > 0) ^ (sub_df["sell_count"] > 0) | (
            (sub_df["buy_count"] == 0) & (sub_df["sell_count"] == 0)
        )
        hdbg.dassert(
            valid.all(),
            f"Invalid buy/sell overlap at `{timestamp}`:\n\
            {hpandas.df_to_str(sub_df, num_rows=None)}",
        )
        # Check that buy and sell counts are non-negative.
        no_negative = (sub_df["buy_count"] >= 0) & (sub_df["sell_count"] >= 0)
        hdbg.dassert(
            no_negative.all(),
            f"Negative buy/sell count at `{timestamp}`:\n\
            {hpandas.df_to_str(sub_df, num_rows=None)}",
        )


def convert_bar_fills_to_portfolio_df(
    fills_df: pd.DataFrame,
    price_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a portfolio dataframe from a fills dataframe.

    :param fills_df: a fills dataframe aggregated by bar
    :param price_df: a bar reference price (e.g., TWAP or VWAP)
    :return: a portfolio-style dataframe, with holdings and trades in
        both shares and notional
    """
    cols = [
        "buy_count",
        "sell_count",
        "cost",
        "amount",
    ]
    hdbg.dassert_is_subset(cols, fills_df.columns)
    hpandas.dassert_time_indexed_df(
        fills_df, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        price_df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, fills_df.index.nlevels)
    # The frequency of `price_df` should not be `None`.
    hdbg.dassert(price_df.index.freq)
    freq = price_df.index.freq
    _check_buy_sell_overlap(fills_df)
    buy = (fills_df["buy_count"] > 0).astype(int)
    sell = (fills_df["sell_count"] > 0).astype(int)
    # Buy = +1, sell = -1.
    side = buy - sell
    # Compute "executed_trades_notional".
    signed_cost = side * fills_df["cost"]
    executed_trades_notional = (
        signed_cost.unstack().resample(freq).last().fillna(0)
    )
    hdbg.dassert(executed_trades_notional.index.freq)
    # Compute "executed_trades_shares".
    signed_amount = side * fills_df["amount"]
    executed_trades_shares = (
        signed_amount.unstack().resample(freq).last().fillna(0)
    )
    hdbg.dassert(executed_trades_shares.index.freq)
    # Compute "holdings_shares" by cumulatively summing executed trades.
    holdings_shares = executed_trades_shares.cumsum()
    hdbg.dassert(holdings_shares.index.freq)
    # Compute "holdings_notional" by multiplying holdings in shares by
    #   reference price.
    holdings_notional = holdings_shares.multiply(price_df)[
        holdings_shares.columns
    ]
    hdbg.dassert(holdings_notional.index.freq)
    # Compute PnL.
    pnl = holdings_notional.subtract(
        holdings_notional.shift(1), fill_value=0
    ).subtract(executed_trades_notional)
    hdbg.dassert(pnl.index.freq)
    # Construct the portfolio dataframe.
    portfolio_df = pd.concat(
        {
            "holdings_shares": holdings_shares,
            "holdings_notional": holdings_notional,
            "executed_trades_shares": executed_trades_shares,
            "executed_trades_notional": executed_trades_notional,
            "pnl": pnl,
        },
        axis=1,
    )
    return portfolio_df


def get_adjusted_close_price(
    close: float, open: float, volatility: float
) -> float:
    """
    Compute volatility-adjusted close price.

    :param close: is defined as the `open` price of the next child order within
    the same parent. This means that for the last child order in the parent,
     or if there was a single child order executed successfully, close == NaN
    :param open: the mid price of the child order
    :param volatility: is calculated by the volatility-based price computer
    :return: volatility-adjusted close price
    """
    adjusted_close = (close - open) / volatility
    return adjusted_close


# #############################################################################
# Fee summaries
# #############################################################################


def generate_fee_summary(
    fills_df: pd.DataFrame, group_by_col: str
) -> pd.DataFrame:
    """
    Summarize fees according to `group_by_col`.

    :param fills_df: the input DataFrame
    :param group_by_col: one of ["is_buy", "is_maker",
        "is_positive_realized_pnl", "wave_id"]
    """
    fills_df_copy = fills_df.copy()
    fills_df_copy["is_buy"] = fills_df["side"] == "buy"
    fills_df_copy["is_maker"] = fills_df["takerOrMaker"] == "maker"
    fills_df_copy["is_positive_realized_pnl"] = fills_df["realized_pnl"] > 0
    # Any row may have NaN issue (tests 3,4). Current fix: reindex with below.
    # Handle the non-common parts: `groupby_df`, `positive_realized_pnl` (only
    # when grouping by "takerOrMaker"), and `is_maker` (only when
    # grouping by `realized_pnl`).
    groupby_df = fills_df_copy.groupby(group_by_col)
    # Use common formulas for both cases.
    fill_count = groupby_df[group_by_col].count().rename("fill_count")
    fill_fees_dollars = (
        groupby_df["transaction_cost"].sum().rename("fill_fees_dollars")
    )
    #
    traded_dollar_volume = (
        groupby_df["cost"].sum().rename("traded_volume_dollars")
    )
    #
    fill_fees_bps = (1e4 * fill_fees_dollars / traded_dollar_volume).rename(
        "fill_fees_bps"
    )
    #
    realized_pnl_dollars = (
        groupby_df["realized_pnl"].sum().rename("realized_pnl_dollars")
    )
    #
    realized_pnl_bps = (1e4 * realized_pnl_dollars / traded_dollar_volume).rename(
        "realized_pnl_bps"
    )
    is_buy = groupby_df["is_buy"].sum()
    is_maker = groupby_df["is_maker"].sum()
    is_positive_realized_pnl = groupby_df["is_positive_realized_pnl"].sum()
    #
    fill_count["combined"] = fills_df.shape[0]
    fill_fees_dollars["combined"] = fills_df["transaction_cost"].sum()
    traded_dollar_volume["combined"] = fills_df["cost"].sum()
    fill_fees_bps["combined"] = (
        1e4
        * fills_df["transaction_cost"].sum()
        / traded_dollar_volume["combined"]
    )
    realized_pnl_dollars["combined"] = fills_df["realized_pnl"].sum()
    realized_pnl_bps["combined"] = (
        1e4 * fills_df["realized_pnl"].sum() / traded_dollar_volume["combined"]
    )
    is_buy["combined"] = fills_df_copy["is_buy"].sum()
    is_maker["combined"] = fills_df_copy["is_maker"].sum()
    is_positive_realized_pnl["combined"] = fills_df_copy[
        "is_positive_realized_pnl"
    ].sum()
    #
    srs_list = []
    srs_list.append(fill_count)
    srs_list.append(traded_dollar_volume)
    srs_list.append(fill_fees_dollars)
    srs_list.append(fill_fees_bps)
    srs_list.append(realized_pnl_dollars)
    srs_list.append(realized_pnl_bps)
    srs_list.append(is_buy)
    srs_list.append(is_maker)
    srs_list.append(is_positive_realized_pnl)
    #
    df = pd.concat(srs_list, axis=1).T
    return df


# #############################################################################
# Time profiling
# #############################################################################


def get_oms_child_order_timestamps(
    oms_child_order_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Get timing columns from oms child order DataFrame.

    :return: child order submission timestamps per child order
    """
    # Select bid/ask timestamp columns from the DB.
    bid_ask_timestamp_cols = [
        "exchange_timestamp",
        "end_download_timestamp",
        "knowledge_timestamp",
    ]
    timing_cols = submission_timestamp_cols = [
        "stats__submit_twap_child_order::bid_ask_market_data.start",
        "stats__submit_twap_child_order::bid_ask_market_data.done",
        "stats__submit_twap_child_order::get_open_positions.done",
        "stats__submit_twap_child_order::child_order.created",
        "stats__submit_twap_child_order::child_order.limit_price_calculated",
        "stats__submit_single_order_to_ccxt::start.timestamp",
        "stats__submit_single_order_to_ccxt::all_attempts_end.timestamp",
        "stats__submit_twap_child_order::child_order.submission_started",
        "stats__submit_twap_child_order::child_order.submitted",
    ]
    timing_cols = bid_ask_timestamp_cols + submission_timestamp_cols
    out_df = oms_child_order_df[timing_cols]
    # Convert to UTC.
    # The conversion is done using a loop since the DF is expected
    # to be indexed by `order_id`, i.e. not a datetime index.
    for timing_col in timing_cols:
        out_df[timing_col] = out_df[timing_col].dt.tz_convert("UTC")
    out_df = out_df.dropna(subset=submission_timestamp_cols)
    return out_df


def get_time_delay_between_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each timestamp, get delay in seconds before the previous timestamp.

    :param df: output of `get_oms_child_order_timestamps`
    """
    delays = df.subtract(df["exchange_timestamp"], axis=0)
    delays = delays.apply(lambda x: x.dt.total_seconds())
    # Verify that the timestamps increase left to right.
    # We expect the input DF to contain the data timestamps, e.g.
    # `exchange_timestamp`, `end_download_timestamp`, `knowledge_timestamp`,
    # and event timestamps, with labels starting with `stats_`. In rare cases
    # earliest `stats_` timestamp can be earlier than `knowledge_timestamp`,
    # which is not considered a bug, since new data could have appeared after
    # the first `stats_` event.
    stats_columns = [col for col in delays.columns if col.startswith("stats_")]
    data_columns = [col for col in delays.columns if col not in stats_columns]
    # Verify that stats timestamps strictly increase.
    hdbg.dassert_eq((delays[stats_columns].diff(axis=1) < 0).sum().sum(), 0)
    # Verify that data columns strictly increase.
    hdbg.dassert_eq((delays[data_columns].diff(axis=1) < 0).sum().sum(), 0)
    return delays


# #############################################################################
# Time-to-fill eCDF
# #############################################################################


def compute_time_to_fill(
    fills_df: pd.DataFrame,
    ccxt_order_response_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute time it took from the submission of the order to get a first fill.

    Note: it is not implied that the order was completely filled, but
    how much time it took from the acceptance of the order at the exchange
    before the first fill (trade) happened.

    :param fills_df: output of `CcxtLogger.load_ccxt_trades_df`
    :param ccxt_order_response_df: output of
        `CcxtLogger.load_ccxt_order_response_df`
    :return: CCXT fills and CCXT responses joined on `order`, with added
        'time_to_fill' and 'secs_to_fill' columns
    """
    # TODO(Danya): Convert order to int at the loading stage.
    ccxt_order_response_df["order"] = ccxt_order_response_df["order"].astype(int)
    # Join CCXT responses and trades on the `ccxt_id`.
    # Note: meaning of `order` in CCXT responses is identical to `ccxt_id`
    # elsewhere.
    df = (
        fills_df.groupby("order")
        .first()
        .join(
            ccxt_order_response_df.set_index("order"), rsuffix="order_response_"
        )
    )
    hdbg.dassert_in("wave_id", df.columns)
    # Get the seconds it took to conduct the trade, from the order's
    # acceptance at the exchange to the timestamp of the trade.
    df["time_to_fill"] = df["timestamp"] - df["order_update_datetime"]
    df["secs_to_fill"] = df["time_to_fill"].apply(lambda x: x.total_seconds())
    return df


def annotate_ccxt_order_response_df(
    ccxt_order_response_df: pd.DataFrame, oms_child_order_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Add OMS child order df columns to CCXT order responses.

    The order responses are annotated with:
    - `asset_id`
    - `wave_id` (for the child order wave of the corresponding order)

    :param ccxt_order_response_df: output of
        `CcxtLogger.load_ccxt_order_response_df`
    :param oms_child_order_df: output of
        `CcxtLogger.oms_child_order_df`
    :return: annotated ccxt_order_response_df, identical to the output of
        `CcxtLogger.load_ccxt_order_response_df`, but annotated with `wave_id`
        and `asset_id` columns
    """
    # Get child order df indexed by `ccxt_id`.
    submitted_child_orders = oms_child_order_df[
        oms_child_order_df["ccxt_id"] != -1
    ]
    # Get annotation columns.
    annotation_columns = ["asset_id"]
    # Add wave_id to annotation.
    # Child orders were not annotated with wave_id in earlier experiments,
    # so the column is optional.
    if "wave_id" in oms_child_order_df.columns:
        annotation_columns.append("wave_id")
    else:
        _LOG.warning("'wave_id' column not in OMS child order df columns.")
    ccxt_id_to_asset_id_srs = submitted_child_orders.set_index("ccxt_id")[
        annotation_columns
    ]
    #
    ccxt_order_response_df = ccxt_order_response_df.copy()
    # TODO(Danya): Convert order to int at the loading stage.
    ccxt_order_response_df["order"] = ccxt_order_response_df["order"].astype(int)
    # Add `asset_id` column.
    ccxt_order_response_df = ccxt_order_response_df.join(
        ccxt_id_to_asset_id_srs, on="order"
    )
    return ccxt_order_response_df


def annotate_fills_df_with_wave_id(
    fills_df: pd.DataFrame, oms_child_order_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Annotate fills df with `wave_id` from child order df.

    Each trade is assigned a wave_id of the corresponding child order based
    on the order's ccxt_id.

    :param fills_df: output of `CcxtLogger.load_ccxt_trades_df`
    :param oms_child_order_df: output of
        `CcxtLogger.oms_child_order_df`
    :return: fills_df with appended `wave_id` column
    """
    # Get wave_id indexed by the ccxt_id.
    # Get successfully submitted child orders.
    child_orders = oms_child_order_df[oms_child_order_df["ccxt_id"] != -1]
    # Get wave_id as Series.
    wave_ids = child_orders.set_index("ccxt_id")["wave_id"]
    # Annotate fills_df by ccxt_id of the order.
    #
    annotated_fills_df = fills_df.copy()
    # Temporarily set index as ccxt_id of the corresponding child order.
    annotated_fills_df = fills_df.set_index("order", drop=False)
    # Add wave_id column.
    annotated_fills_df["wave_id"] = wave_ids
    # Restore timestamp index.
    annotated_fills_df = annotated_fills_df.reset_index(drop=True).set_index(
        "timestamp", drop=False
    )
    return annotated_fills_df


def compute_adj_fill_ecdfs(
    fills_df: pd.DataFrame,
    ccxt_order_response_df: pd.DataFrame,
    oms_child_order_df: pd.DataFrame,
    *,
    by_wave: bool = False,
) -> Union[pd.DataFrame, Dict[int, pd.DataFrame]]:
    """
    Compute time-to-fill eCDFs by asset_id adjusted for underfills.

    :param fills_df: output of `CcxtLogger.load_ccxt_trades_df`
    :param ccxt_order_response_df: output of
        `CcxtLogger.load_ccxt_order_response_df`
    :param oms_child_order_df: output of
        `CcxtLogger.oms_child_order_df`
    :param by_wave: compute multiple ECDFs by child order wave ID
    :return: time-to-fill eCDFs DataFrame, or a dict if `by_wave` is enabled,
    for example:
        5115052901  1528092593  2484635488
    0.000    0.055375     0.02454    0.057143
    0.003    0.055375     0.02454    0.057143
    0.011    0.055375     0.02454    0.057143
    0.015    0.055375     0.02454    0.057143
    0.016    0.055375     0.02454    0.057143
    """
    # Add `asset_id` to CCXT order response DataFrame.
    ccxt_order_response_df = annotate_ccxt_order_response_df(
        ccxt_order_response_df, oms_child_order_df
    )
    # Add time to fill.
    time_to_fill_df = compute_time_to_fill(fills_df, ccxt_order_response_df)
    asset_id_col = "asset_id"
    if by_wave:
        # Get a dict of ECDFs by wave.
        hdbg.dassert_in("wave_id", oms_child_order_df.columns)
        hdbg.dassert_in("wave_id", ccxt_order_response_df.columns)
        hdbg.dassert_in("wave_id", time_to_fill_df.columns)
        adj_ecdf = {}
        waves = sorted(oms_child_order_df.wave_id.unique())
        for wave in waves:
            wave_responses = ccxt_order_response_df.loc[
                ccxt_order_response_df["wave_id"] == wave
            ]
            wave_time_to_fill = time_to_fill_df.loc[
                time_to_fill_df["wave_id"] == wave
            ]
            wave_fills = fills_df.loc[
                fills_df["order"].isin(wave_time_to_fill.index)
            ]
            adj_ecdf[wave] = _compute_adj_fill_ecdfs_for_single_df(
                wave_time_to_fill, wave_responses, wave_fills, asset_id_col
            )
    else:
        # Get ECDFs over all waves.
        adj_ecdf = _compute_adj_fill_ecdfs_for_single_df(
            time_to_fill_df, ccxt_order_response_df, fills_df, asset_id_col
        )
    return adj_ecdf


def _compute_adj_fill_ecdfs_for_single_df(
    time_to_fill_df: pd.DataFrame,
    ccxt_order_response_df: pd.DataFrame,
    fills_df: pd.DataFrame,
    asset_id_col: str,
) -> pd.DataFrame:
    """
    Generate a single ECDFs DataFrame.

    :return: time-to-fill eCDFs DataFrame, e.g.
        5115052901  1528092593  2484635488
    0.000    0.055375     0.02454    0.057143
    0.003    0.055375     0.02454    0.057143
    0.011    0.055375     0.02454    0.057143
    0.015    0.055375     0.02454    0.057143
    0.016    0.055375     0.02454    0.057143
    """
    num = time_to_fill_df[asset_id_col].value_counts()
    denom = (
        fills_df[asset_id_col].value_counts()
        - time_to_fill_df[asset_id_col].value_counts()
        + ccxt_order_response_df[asset_id_col].value_counts()
    )
    frac = num / denom
    # Compute eCDF by symbol.
    ecdfs = {}
    for symbol in time_to_fill_df[asset_id_col].unique():
        ecdf = costatis.compute_empirical_cdf(
            time_to_fill_df[time_to_fill_df[asset_id_col] == symbol][
                "secs_to_fill"
            ]
        )
        ecdf.name = symbol
        ecdfs[symbol] = ecdf
    adj_ecdfs = {}
    for symbol in ecdfs:
        adj_ecdfs[symbol] = ecdfs[symbol] * frac.loc[symbol]
    #
    if adj_ecdfs:
        adj_ecdf_df = (
            pd.concat(list(adj_ecdfs.values()), axis=1)
            .sort_index()
            .ffill()
            .fillna(0)
        )
    else:
        adj_ecdf_df = pd.DataFrame()
    return adj_ecdf_df
