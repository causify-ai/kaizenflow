"""
Import as:

import core.plotting.turnover as cploturn
"""

import logging
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

import core.plotting.plotting_utils as cplpluti
import core.statistics as costatis

_LOG = logging.getLogger(__name__)


def plot_holding_diffs(
    holdings: pd.Series,
    unit: str = "ratio",
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot holding changes over time.

    Indicates how much to increase or decrease holdings from current point in
    time to the next one in order to achieve the target position. Since the
    difference is between current and next time periods, the holdings change
    from t0 to t1 has a timestamp t0.

    :param holdings: series to plot
    :param unit: "ratio", "%" or "bps" scaling coefficient
    :param ax: axes in which to draw the plot
    """
    ax = ax or plt.gca()
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    holdings = scale_coeff * holdings
    holdings = -holdings.diff(-1)
    holdings.plot(linewidth=1, ax=ax, label="holding changes")
    ax.set_ylabel(unit)
    ax.legend()
    ax.set_title(f"Holding changes over time (in {unit})")


def plot_turnover(
    positions: pd.Series,
    unit: str = "ratio",
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot turnover, average turnover by month and overall average turnover.

    :param positions: series of positions to plot
    :param unit: "ratio", "%" or "bps" scaling coefficient
    :param ax: axes in which to draw the plot
    :param events: list of tuples with dates and labels to point out on the plot
    """
    ax = ax or plt.gca()
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    turnover = costatis.compute_turnover(positions)
    turnover = scale_coeff * turnover
    turnover.plot(linewidth=1, ax=ax, label="turnover")
    turnover.resample("M").mean().plot(
        linewidth=2.5, ax=ax, label="average turnover by month"
    )
    ax.axhline(
        turnover.mean(),
        linestyle="--",
        color="green",
        label="average turnover, overall",
    )
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.set_ylabel(unit)
    ax.legend()
    ax.set_title(f"Turnover ({unit})")
