"""
Import as:

import core.plotting.visual_stationarity_test as cpvistte
"""

import logging
from typing import Any, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import core.plotting.plotting_utils as cplpluti
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def plot_histograms_and_lagged_scatterplot(
    srs: pd.Series,
    lag: int,
    oos_start: Optional[str] = None,
    nan_mode: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Optional[Tuple] = None,
    hist_kwargs: Optional[Any] = None,
    scatter_kwargs: Optional[Any] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> None:
    """
    Plot histograms and scatterplot to test stationarity visually.

    Function plots histograms with density plot for 1st and 2nd part of the time
    series (splitted by oos_start if provided otherwise to two equal halves).
    If the timeseries is stationary, the histogram of the 1st part of
    the timeseries would be similar to the histogram of the 2nd part) and
    scatter-plot of time series observations versus their lagged values (x_t
    versus x_{t - lag}). If it is stationary the scatter-plot with its lagged
    values would resemble a circular cloud.

    :param axes: flat list of axes or `None`
    """
    hdbg.dassert(isinstance(srs, pd.Series), "Input must be Series")
    hpandas.dassert_monotonic_index(srs, "Index must be monotonic")
    figsize = figsize or (20, 10)
    hist_kwargs = hist_kwargs or {}
    scatter_kwargs = scatter_kwargs or {}
    # Handle inf and nan.
    srs = srs.replace([-np.inf, np.inf], np.nan)
    nan_mode = nan_mode or "drop"
    srs = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    # Divide timeseries to two parts.
    oos_start = oos_start or srs.index.tolist()[len(srs) // 2]
    srs_first_part = srs[:oos_start]  # type: ignore[misc]
    srs_second_part = srs[oos_start:]  # type: ignore[misc]
    # Plot histograms.
    if axes is None:
        # This is needed to keep y and x axes on the same scale for histograms.
        # More details in the matplotlib GH bug https://github.com/matplotlib/matplotlib/issues/11416.
        subplots_kwargs = {
            "sharex": "row",
            "sharey": "row",
            "subplot_kw": {"adjustable": "box"},
        }
        _, axes = cplpluti.get_multiple_plots(3, 2, y_scale=figsize[1] / 2, **subplots_kwargs)
        # Since histograms share the same y-axis, the y-axis labels are displayed only for the
        # 1st histogram by default, enable displaying labels for all histograms manually.
        for ax in axes:
            ax.yaxis.set_tick_params(labelleft=True)
        plt.suptitle(title or srs.name)
    sns.histplot(
        srs_first_part, ax=axes[0], kde=True, stat="probability", **hist_kwargs
    )
    axes[0].set(xlabel=None, ylabel=None, title="Sample distribution split 1")
    sns.histplot(
        srs_second_part,
        ax=axes[1],
        kde=True,
        stat="probability",
        **hist_kwargs,
    )
    axes[1].set(xlabel=None, ylabel=None, title="Sample distribution split 2")
    # Plot scatter plot.
    axes[2].scatter(srs, srs.shift(lag), **scatter_kwargs)
    # This is needed to keep the scatter plot square. 
    axes[2].set_box_aspect(1)
    axes[2].set(xlabel="Values", ylabel="Values with lag={}".format(lag))
    axes[2].set_title("Scatter-plot with lag={}".format(lag))
