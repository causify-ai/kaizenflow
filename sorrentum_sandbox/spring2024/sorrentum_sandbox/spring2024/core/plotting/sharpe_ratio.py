"""
Import as:

import core.plotting.sharpe_ratio as cplshrat
"""

import logging
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy as sp

import core.finance as cofinanc
import core.plotting.plotting_utils as cplpluti
import core.signal_processing as csigproc
import core.statistics as costatis
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def plot_sharpe_ratio_panel(
    log_rets: pd.Series,
    frequencies: Optional[List[str]] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot how SRs vary under resampling.

    :param log_rets: log returns
    :param frequencies: frequencies to calculate SR for
    :param ax: axis
    """
    hdbg.dassert_isinstance(log_rets, pd.Series)
    frequencies = frequencies or ["B", "D", "W", "M", "Q"]
    srs_freq = pd.infer_freq(log_rets.index)
    if not srs_freq:
        _LOG.warning("Input has no frequency and it has been rescaled to 'D'")
        srs_freq = "D"
    # Resample input for assuring input frequency in calculations.
    log_rets = cofinanc.resample(log_rets, rule=srs_freq).sum()
    # Initiate series for Sharpe ratios of selected frequencies.
    sr_series = pd.Series([], dtype="object")
    # Initiate list for Sharpe ratios' standard errors for error bars.
    res_se = []
    # Initiate list for frequencies that do not lead to upsampling.
    valid_frequencies = []
    # Compute input frequency points per year for identifying upsampling.
    input_freq_points_per_year = hdatafr.infer_sampling_points_per_year(log_rets)
    for freq in frequencies:
        freq_points_per_year = hdatafr.compute_points_per_year_for_given_freq(
            freq
        )
        if freq_points_per_year > input_freq_points_per_year:
            _LOG.warning(
                "Upsampling from input freq='%s' to freq='%s' is blocked",
                srs_freq,
                freq,
            )
            continue
        resampled_log_rets = cofinanc.resample(log_rets, rule=freq).sum()
        if len(resampled_log_rets) == 1:
            _LOG.warning(
                "Resampling to freq='%s' is blocked because resampled series "
                "has only 1 observation",
                freq,
            )
            continue
        sr = costatis.compute_annualized_sharpe_ratio(resampled_log_rets)
        se = costatis.compute_annualized_sharpe_ratio_standard_error(
            resampled_log_rets
        )
        sr_series[freq] = sr
        res_se.append(se)
        valid_frequencies.append(freq)
    ax = ax or plt.gca()
    sr_series.plot(
        yerr=res_se, marker="o", capsize=2, ax=ax, label="Sharpe ratio"
    )
    ax.set_xticks(range(len(valid_frequencies)))
    ax.set_xticklabels(valid_frequencies)
    ax.set_xlabel("Frequencies")
    ax.legend()


def plot_rolling_annualized_sharpe_ratio(
    srs: pd.Series,
    tau: float,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
    ci: float = 0.95,
    title_suffix: Optional[str] = None,
    trim_index: Optional[bool] = False,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot rolling annualized Sharpe ratio.

    :param srs: input series
    :param tau: argument as for csigproc.compute_smooth_moving_average
    :param min_depth: argument as for csigproc.compute_smooth_moving_average
    :param max_depth: argument as for csigproc.compute_smooth_moving_average
    :param p_moment: argument as for csigproc.compute_smooth_moving_average
    :param ci: confidence interval
    :param title_suffix: suffix added to the title
    :param trim_index: start plot at original index if True
    :param ax: axes
    :param events: list of tuples with dates and labels to point out on the plot
    """
    title_suffix = title_suffix or ""
    srs = hdatafr.apply_nan_mode(srs, mode="fill_with_zero")
    # Resample to business daily time scale.
    srs = srs.resample("B").sum(min_count=1)
    points_per_year = hdatafr.infer_sampling_points_per_year(srs)
    min_periods = tau * max_depth
    rolling_sharpe = csigproc.compute_rolling_annualized_sharpe_ratio(
        srs,
        tau,
        points_per_year=points_per_year,
        min_periods=min_periods,
        min_depth=min_depth,
        max_depth=max_depth,
        p_moment=p_moment,
    )
    # Remove leading `NaNs`.
    first_valid_index = rolling_sharpe.first_valid_index()
    rolling_sharpe = rolling_sharpe.loc[first_valid_index:]
    # Prepare for plotting SE band.
    z = sp.stats.norm.ppf((1 - ci) / 2)
    rolling_sharpe["sr-z*se"] = (
        rolling_sharpe["annualized_SR"] + z * rolling_sharpe["annualized_SE(SR)"]
    )
    rolling_sharpe["sr+z*se"] = (
        rolling_sharpe["annualized_SR"] - z * rolling_sharpe["annualized_SE(SR)"]
    )
    # Plot.
    ax = rolling_sharpe["annualized_SR"].plot(
        ax=ax, title=f"Annualized rolling Sharpe ratio{title_suffix}", label="SR"
    )
    ax.fill_between(
        rolling_sharpe.index,
        rolling_sharpe["sr-z*se"],
        rolling_sharpe["sr+z*se"],
        alpha=0.4,
        label=f"{100*ci:.2f}% confidence interval",
    )
    mean_sharpe_ratio = (
        rolling_sharpe["annualized_SR"]
        .replace([np.inf, -np.inf], value=np.nan)
        .mean()
    )
    ax = ax or plt.gca()
    ax.axhline(
        mean_sharpe_ratio,
        linestyle="--",
        linewidth=2,
        color="green",
        label="average SR",
    )
    ax.axhline(0, linewidth=0.8, color="black", label="0")
    cplpluti.maybe_add_events(ax=ax, events=events)
    # Start plot from original index if specified.
    if not trim_index:
        ax.set_xlim([min(srs.index), max(srs.index)])
    ax.set_ylabel("annualized SR")
    ax.legend()
