"""
Import as:

import core.finance.target_position_df_processing.fill_stats as cftpdpfst
"""

import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(Paul): Add unit tests.
# TODO(Paul): Debug infs in fill rates.
def compute_fill_stats(target_position_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare target trades and holdings to realized.

    Uses a target position dataframe to compare target holdings and target
    trades to those realized in execution. Because execution prices or
    notionals are not tracked in this dataframe, slippage is not one of the
    outputs.

    To break down according to buys/sells, filter the output dataframe, then
      inspect desired column.

    :param target_position_df: a target position dataframe.
    :return: fills dataframe
    """
    # Ensure `df` is in the form of a target position dataframe.
    hpandas.dassert_time_indexed_df(
        target_position_df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(2, target_position_df.columns.nlevels)
    cols = [
        "holdings_notional",
        "holdings_shares",
        "price",
        "target_holdings_notional",
        "target_holdings_shares",
        "target_trades_shares",
    ]
    hdbg.dassert_is_subset(cols, target_position_df.columns.levels[0])
    # The trades and shares are signed to indicate the side.
    executed_trades_shares = target_position_df["holdings_shares"].subtract(
        target_position_df["holdings_shares"].shift(1), fill_value=0
    )
    # Buy = +1, sell = -1.
    buy = (executed_trades_shares > 0).astype(int)
    sell = (executed_trades_shares < 0).astype(int)
    side = buy - sell
    # TODO(Paul): Consider having two bool cols instead of a pseudo-ternary
    #  column.
    # Whether trades executed within the end-of-bar-indexed bar would have
    # been profitable had they been closed out in the subsequent bar.
    is_benchmark_profitable = side * np.sign(
        target_position_df["price"].diff().shift(-1)
    )
    # These are end-of-bar time-indexed.
    fill_rate = (
        executed_trades_shares
        / target_position_df["target_trades_shares"].shift(1)
    ).abs()
    # TODO(Paul): Ensure that executed_trades_shares is zero when we do not
    #  intend to trade.
    no_trade_loc = target_position_df["target_trades_shares"].shift(1) == 0
    fill_rate[no_trade_loc] = np.nan
    # Compute underfills.
    underfill_share_count = (
        target_position_df["target_trades_shares"].shift(1).abs()
        - executed_trades_shares.abs()
    )
    # Compute underfill notional opportunity cost with respect to baseline price.
    target_side = np.sign(target_position_df["target_trades_shares"].shift(2))
    underfill_notional = underfill_share_count * target_position_df[
        "price"
    ].shift(1)
    # TODO(Paul): Align the variable name with the column name.
    underfill_notional_cost = (
        target_side
        * underfill_share_count.shift(1)
        * target_position_df["price"].subtract(
            target_position_df["price"].shift(1)
        )
    )
    # Compute the difference between realized holdings and target holdings.
    tracking_error_shares = target_position_df[
        "holdings_shares"
    ] - target_position_df["target_holdings_shares"].shift(1)
    tracking_error_notional = target_position_df[
        "holdings_notional"
    ] - target_position_df["target_holdings_notional"].shift(1)
    tracking_error_bps = (
        1e4
        * tracking_error_notional
        / target_position_df["target_holdings_notional"].shift(1)
    )
    tracking_error_bps[no_trade_loc] = np.nan
    #
    fills_df = pd.concat(
        {
            "executed_trades_shares": executed_trades_shares,
            "fill_rate": fill_rate,
            "underfill_share_count": underfill_share_count,
            "underfill_notional": underfill_notional,
            "underfill_opportunity_cost_realized_notional": underfill_notional_cost,
            "underfill_opportunity_cost_notional": underfill_notional_cost.shift(
                -1
            ),
            "tracking_error_shares": tracking_error_shares,
            "tracking_error_notional": tracking_error_notional,
            "tracking_error_bps": tracking_error_bps,
            "is_buy": buy.astype(bool),
            "is_sell": sell.astype(bool),
            "is_benchmark_profitable": is_benchmark_profitable,
        },
        axis=1,
    )
    return fills_df
