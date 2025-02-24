"""
Import as:

import core.finance.target_position_df_processing.combine_with_portfolio_df as cftpdpcwpd
"""

import logging
from typing import Tuple

import pandas as pd

import core.finance.per_bar_portfolio_metrics as cfpbpome
import core.finance.portfolio_df_processing.slippage as cfpdprsl
import core.finance.target_position_df_processing.fill_stats as cftpdpfst

_LOG = logging.getLogger(__name__)


# TODO(Paul): Rename this function.
def compute_execution_quality_df(
    portfolio_df: pd.DataFrame,
    target_position_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute notional slippage and underfill costs.

    This is more accurate than slippage computed from `Portfolio` alone,
    because `target_position_df` provides baseline prices even when
    `holdings_shares` is zero (in which case we cannot compute the
    baseline price from `Portfolio`).
    """
    # TODO(Paul): Add sanity-checks for `portfolio_df` and `target_position_df`.
    # TODO(Paul): We can add consistency checks, e.g., to make sure that
    #  `portfolio_df` and `target_position_df` are compatible.
    fill_stats = cftpdpfst.compute_fill_stats(target_position_df)
    # Compute notional slippage.
    # NOTE: `executed_trades_notional` is the key piece of information needed
    #  from `portfolio_df` for computing slippage.
    portfolio_df["executed_trades_notional"]
    # Get baseline price.
    price_df = target_position_df["price"]
    slippage = cfpdprsl.compute_share_prices_and_slippage(
        portfolio_df, price_df=price_df
    )
    # Drop columns that overlap with `fill_stats` columns.
    # TODO(Paul): Consider cross-checking these with those in `fill_stats`.
    slippage = slippage.drop(
        columns=[
            "is_buy",
            "is_sell",
            "is_benchmark_profitable",
        ]
    )
    execution_quality_df = pd.concat([fill_stats, slippage], axis=1)
    # TODO(Paul): Clean up this temporary fix once the column sets are the
    #  same.
    holdings_notional = portfolio_df["holdings_notional"]
    executed_trades_notional = portfolio_df["executed_trades_notional"]
    cols = holdings_notional.columns.union(executed_trades_notional.columns)
    holdings_notional = holdings_notional.reindex(columns=cols, fill_value=0)
    executed_trades_notional = executed_trades_notional.reindex(
        columns=cols, fill_value=0
    )
    portfolio_stats_df = cfpbpome.compute_bar_metrics(
        holdings_notional,
        -executed_trades_notional,
        portfolio_df["pnl"],
    )
    #
    summary_cols = [
        "underfill_opportunity_cost_realized_notional",
        "slippage_notional",
    ]
    stats_df = (
        execution_quality_df[summary_cols].T.groupby(level=0).sum(min_count=1).T
    )
    execution_quality_stats_df = pd.concat([stats_df, portfolio_stats_df], axis=1)
    return execution_quality_df, execution_quality_stats_df


# TODO(Paul): Update this in view of changes to `compute_notional_costs()`.
def summarize_notional_costs(df: pd.DataFrame, aggregation: str) -> pd.DataFrame:
    """
    Aggregate notional costs by bar or by asset.

    :param df: output of `compute_notional_costs()`
    :param aggregation: "by_bar" or "by_asset"
    :return: dataframe with columns ["slippage_notional",
        "underfill_notional_cost", "net"]
    """
    if aggregation == "by_bar":
        agg = df.groupby(axis=1, level=0).sum(min_count=1)
    elif aggregation == "by_asset":
        agg = df.sum(min_count=1).unstack(level=-1)
        agg = agg.T
    else:
        raise ValueError("Invalid aggregation=%s", aggregation)
    agg["net"] = agg.sum(axis=1, min_count=1)
    return agg
