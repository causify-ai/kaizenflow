"""
Import as:

import core.plotting.execution_stats as cplexsta
"""

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd

import core.plotting.plotting_utils as cplpluti
import core.statistics as costatis
import helpers.hdbg as hdbg
import oms.broker.ccxt.ccxt_execution_quality as obccexqu

_LOG = logging.getLogger(__name__)


def plot_execution_stats(
    df: pd.DataFrame,
    *,
    y_scale: Optional[float] = 5,
) -> None:
    """
    Plots stats of a portfolio bar metrics dataframe, possibly multiindex.

    :param df: an `execution_quality_stats_df`
    :param y_scale: controls the size of the figures
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Make the `df` a df with a two-level column index.
    if df.columns.nlevels == 1:
        df = pd.concat([df], axis=1, keys=["strategy"])
    hdbg.dassert_eq(df.columns.nlevels, 2)
    # Define plot axes.
    _, axes = cplpluti.get_multiple_plots(10, 2, y_scale=y_scale)
    # Compute slippage.
    slippage_notional = df.T.xs("slippage_notional", level=1).T
    slippage_notional = slippage_notional.fillna(0)
    # Plot dollar cumulative slippage and cumulative slippage with respect to
    #  cumulative dollar volume.
    slippage_notional.cumsum().plot(
        ax=axes[0], title="Cumulative Slippage", ylabel="dollars"
    )
    gross_volume = df.T.xs("gross_volume", level=1).T
    cumulative_slippage_rel_volume = slippage_notional.cumsum().divide(
        gross_volume.cumsum()
    )
    (1e4 * cumulative_slippage_rel_volume).plot(
        ax=axes[1],
        title="Cumulative Slippage/Cumulative Gross Volume",
        ylabel="bps",
    )
    # Compute underfill opportunity cost.
    underfill_cost = df.T.xs(
        "underfill_opportunity_cost_realized_notional", level=1
    ).T
    # Plot dollar cumulative underfill cost and cumulative underfill cost with
    #  respect to cumulative dollar volume.
    underfill_cost.cumsum().plot(
        ax=axes[2],
        title="Cumulative Underfill Cost",
        ylabel="dollars",
    )
    cumulative_underfill_cost_rel_volume = underfill_cost.cumsum().divide(
        gross_volume.cumsum()
    )
    (1e4 * cumulative_underfill_cost_rel_volume).plot(
        ax=axes[3],
        title="Cumulative Underfill Cost/Cumulative Gross Volume",
        ylabel="bps",
    )
    # Combine slippage and underfill costs.
    net_tc = slippage_notional + underfill_cost
    net_tc.cumsum().plot(ax=axes[4], title="Cumulative Net TC", ylabel="dollars")
    cumulative_net_tc_rel_volume = net_tc.cumsum().divide(gross_volume.cumsum())
    (1e4 * cumulative_net_tc_rel_volume).plot(
        ax=axes[5],
        title="Cumulative Net TC/Cumulative Gross Volume",
        ylabel="bps",
    )
    pnl = df.T.xs("pnl", level=1).T
    # Plot dollar cumulative PnL and cumulative PnL with respect to
    #  cumulative dollar volume.
    pnl.cumsum().plot(ax=axes[6], title="Cumulative PnL", ylabel="dollars")
    cumulative_pnl_rel_volume = pnl.cumsum().divide(gross_volume.cumsum())
    (1e4 * cumulative_pnl_rel_volume).plot(
        ax=axes[7],
        title="Cumulative PnL/Cumulative Gross Volume",
        ylabel="bps",
    )
    # Plot "idealized PnL" (without slippage or underfills).
    idealized_pnl = pnl + net_tc
    idealized_pnl.cumsum().plot(
        ax=axes[8], title="Idealized Cumulative PnL", ylabel="dollars"
    )
    idealized_cumulative_pnl_rel_volume = idealized_pnl.cumsum().divide(
        gross_volume.cumsum()
    )
    (1e4 * idealized_cumulative_pnl_rel_volume).plot(
        ax=axes[9],
        title="Idealized Cumulative PnL/Cumulative Gross Volume",
        ylabel="bps",
    )


def plot_execution_ecdfs(
    df: pd.DataFrame,
    *,
    y_scale: Optional[float] = 5,
) -> None:
    """
    Plot ecdfs for various execution-related quantities.

    :param df: an `execution_quality_df`
    :param y_scale: controls the size of the figures
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [
        "fill_rate",
        "slippage_in_bps",
        "underfill_opportunity_cost_notional",
        "is_buy",
        "is_sell",
        "is_benchmark_profitable",
    ]
    stacked = df[cols].stack()
    # Define plot axes.
    _, axes = cplpluti.get_multiple_plots(6, 1, y_scale=y_scale)
    yticks = np.arange(0, 1.1, 0.1)
    # Plot slippage according to profitability.
    is_profitable_slippage_ecdf = _get_profitability_ecdfs(
        stacked, "slippage_in_bps"
    )
    is_profitable_slippage_ecdf.plot(
        ax=axes[0],
        title="Slippage in bps by profitability",
        yticks=yticks,
    )
    # Plot slippage according to buy/sell.
    buy_sell_slippage_ecdf = _get_buy_sell_ecdfs(stacked, "slippage_in_bps")
    buy_sell_slippage_ecdf.plot(
        ax=axes[1],
        title="Slippage in bps by buy/sell",
        yticks=yticks,
    )
    # Plot fill rate by profitability.
    is_profitable_fill_rate_ecdf = _get_profitability_ecdfs(
        stacked,
        "fill_rate",
    )
    is_profitable_fill_rate_ecdf.plot(
        ax=axes[2],
        title="Fill rate by profitability",
        yticks=yticks,
    )
    # Plot fill rate by buy/sell.
    buy_sell_fill_rate_ecdf = _get_buy_sell_ecdfs(stacked, "fill_rate")
    buy_sell_fill_rate_ecdf.plot(
        ax=axes[3],
        title="Fill rate by buy/sell",
        yticks=yticks,
    )
    # Plot underfill cost.
    underfill_cost_ecdf = costatis.compute_empirical_cdf(
        stacked["underfill_opportunity_cost_notional"],
    )
    underfill_cost_ecdf.plot(
        ax=axes[4],
        title="Underfill opportunity cost in dollars",
        yticks=yticks,
    )
    # Plot underfill cost by buy/sell.
    buy_sell_underfill_cost_ecdf = _get_buy_sell_ecdfs(
        stacked, "underfill_opportunity_cost_notional"
    )
    buy_sell_underfill_cost_ecdf.plot(
        ax=axes[5],
        title="Underfill opportunity cost in dollars by buy/sell",
        yticks=yticks,
    )


def plot_adj_fill_ecdfs(
    fills_df: pd.DataFrame,
    ccxt_order_response_df: pd.DataFrame,
    oms_child_order_df: pd.DataFrame,
) -> None:
    """
    Plot multiple ECDFs by child order wave.

    The resulting plots have a unified X-axix.

    :param fills_df: output of `CcxtLogger.load_ccxt_trades_df`
    :param ccxt_order_response_df: output of
        `CcxtLogger.load_ccxt_order_response_df`
    :param oms_child_order_df: output of
        `CcxtLogger.oms_child_order_df`
    """
    adj_fill_ecdfs = obccexqu.compute_adj_fill_ecdfs(
        fills_df,
        ccxt_order_response_df,
        oms_child_order_df,
        by_wave=True,
    )
    # Find the maximum timestamp value among non-empty DataFrames to use as a common X-axis.
    x_sec_max = max(
        max(df.index) for wave_id, df in adj_fill_ecdfs.items() if not df.empty
    )
    for wave_id, df in adj_fill_ecdfs.items():
        _plot_adj_fill_ecdfs_single_df(df, wave_id, x_sec_max)


def _plot_adj_fill_ecdfs_single_df(
    adj_fill_ecdfs: pd.DataFrame,
    wave_id: int,
    x_sec_max: float,
) -> None:
    """
    Plot ECDFs for a single child order wave.

    :param adj_fill_ecdfs: eCDFs DataFrame
    :param wave_id: child order wave number
    :param x_sec_max: maximum timestamp value among non-empty DataFrames
    """
    if not adj_fill_ecdfs.empty:
        if adj_fill_ecdfs.shape[0] == 1:
            # Len of 1 indicates that all trades were conducted during the same timestamp.
            # If there are multiple assets traded, we expect all taking 0 secs to fill, indicating
            # "taker" orders. If there is a different value for secs_to_fill, we expect there to be
            # trades for a single asset, and multiple assets with a single secs_to_fill for a
            # trade need to be investigated.
            hdbg.dassert_eq(
                adj_fill_ecdfs.index[0] == 0.0
                or len(adj_fill_ecdfs.columns) == 1,
                True,
                "Invalid DataFrame format: expected a zero timestamp or a non-zero timestamp \
                  with a single traded asset.",
            )
            _LOG.info(
                "All trades for wave_id=%d were conducted immediately (with rounding)",
                wave_id,
            )
        else:
            adj_fill_ecdfs.plot(
                title=f"wave_id: {wave_id}",
                xlim=(0, x_sec_max),
                xticks=range(0, math.ceil(x_sec_max) + 1, 1),
            )
    else:
        _LOG.info("No trades found for wave id=%d", wave_id)


def _get_profitability_ecdfs(
    df: pd.DataFrame,
    col: str,
) -> pd.DataFrame:
    profitable = df[df["is_benchmark_profitable"] > 0][col].rename(
        col + "_when_benchmark_profitable"
    )
    not_profitable = df[df["is_benchmark_profitable"] <= 0][col].rename(
        col + "_when_not_benchmark_profitable"
    )
    ecdf = costatis.compute_and_combine_empirical_cdfs(
        [profitable, not_profitable]
    )
    return ecdf


def _get_buy_sell_ecdfs(
    df: pd.DataFrame,
    col: str,
) -> pd.DataFrame:
    buy = df[df["is_buy"]][col].rename(col + "_buy")
    sell = df[df["is_sell"]][col].rename(col + "_sell")
    ecdf = costatis.compute_and_combine_empirical_cdfs([buy, sell])
    return ecdf
