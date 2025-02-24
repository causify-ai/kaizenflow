"""
Import as:

import core.plotting.portfolio_binned_stats as cppobist
"""

import logging
from typing import Dict, Optional, Union

import pandas as pd

import core.finance.portfolio_df_processing.binned_stats as cfpdpbist
import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def plot_portfolio_binned_stats(
    data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    proportion_of_data_per_bin: float,
    *,
    normalize_prediction_col_values: bool = False,
    y_scale: Optional[float] = 5,
) -> pd.DataFrame:
    """
    Plot binned PnL stats by prediction bin.

    :param data: 2-level column `portfolio_df` with "prediction" column as in
        `bin_prediction_annotated_portfolio_df()` or a dict of such DataFrames
    :param proportion_of_data_per_bin: as in `bin_prediction_annotated_portfolio_df()`
    :param normalize_prediction_col_values: as in `bin_prediction_annotated_portfolio_df()`
    :param y_scale: controls the size of the figures
    """
    if isinstance(data, pd.DataFrame):
        # Convert input data to a dict DataFrames.
        data = {"portfolio": data}
    # Get binned stats for each key and combine results in a single df.
    binned_stats_dict = {}
    for key, portfolio_df in data.items():
        hdbg.dassert_isinstance(portfolio_df, pd.DataFrame)
        binned_stats_df = _compute_portfolio_binned_stats(
            portfolio_df,
            proportion_of_data_per_bin,
            normalize_prediction_col_values=normalize_prediction_col_values,
        )
        binned_stats_dict[key] = binned_stats_df
    binned_stats = pd.concat(binned_stats_dict, axis=1)
    # Define plot axes.
    _, axes = cplpluti.get_multiple_plots(4, 2, y_scale=y_scale)
    # Plot PnL.
    pnl = binned_stats.T.xs("pnl", level=1).T
    pnl.plot(ax=axes[0], title="pnl", ylabel="mean of means (dollars)")
    # Plot PnL in bps.
    pnl_in_bps = binned_stats.T.xs("pnl_in_bps", level=1).T
    pnl_in_bps.plot(ax=axes[1], title="pnl_in_bps", ylabel="mean of means (bps)")
    # Compute correlations.
    sgn_corr = binned_stats.T.xs("sgn_corr", level=1).T
    corr = binned_stats.T.xs("corr", level=1).T
    # Subtract an offset from ylim_min for easier viewing.
    ylim_min = min(sgn_corr.min().min(), corr.min().min())
    ylim_max = max(sgn_corr.max().max(), corr.max().max())
    # Subtract a small percentage of the range from ylim_min for easier
    # viewing.
    ylim_range = ylim_max - ylim_min
    ylim_min -= 0.05 * ylim_range
    # Plot signed correlation.
    sgn_corr.plot(
        ax=axes[2],
        title="sgn_corr",
        ylabel="mean of means",
        ylim=[ylim_min, ylim_max],
    )
    # Plot correlation.
    corr.plot(
        ax=axes[3],
        title="corr",
        ylabel="mean of means",
        ylim=[ylim_min, ylim_max],
    )
    if len(data) == 1:
        # Drop unnecessary column level from result for a singular input
        # `portfolio_df`.
        binned_stats.columns = binned_stats.columns.droplevel(0)
    # TODO(Paul): Add ability to plot standard deviation.
    return binned_stats


def _compute_portfolio_binned_stats(
    df: pd.DataFrame,
    proportion_of_data_per_bin: float,
    *,
    normalize_prediction_col_values: bool = False,
) -> pd.DataFrame:
    """
    Compute binned PnL stats by prediction bin.

    :param df: as in `bin_prediction_annotated_portfolio_df()`
    :param proportion_of_data_per_bin: as in
        `bin_prediction_annotated_portfolio_df()`
    :param normalize_prediction_col_values: as in
        `bin_prediction_annotated_portfolio_df()`
    :return: binned PnL stats
    """
    # Input DataFrame should have 2 column levels.
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_eq(df.columns.nlevels, 2)
    # Set metric column names.
    output_cols = ["pnl", "pnl_in_bps", "sgn_corr", "corr"]
    # Get binned stats for each metric and combine results in a single df.
    out_srs = []
    for output_col in output_cols:
        binned_df = cfpdpbist.bin_prediction_annotated_portfolio_df(
            df,
            proportion_of_data_per_bin,
            output_col,
            normalize_prediction_col_values,
        )
        srs = binned_df["mean"].mean(axis=1).rename(output_col)
        out_srs.append(srs)
    df_res = pd.concat(out_srs, axis=1)
    return df_res
