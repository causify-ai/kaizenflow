"""
Import as:

import core.plotting.drawdown as cplodraw
"""

import logging
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

import core.plotting.plotting_utils as cplpluti
import core.statistics as costatis

_LOG = logging.getLogger(__name__)


# TODO(*): Reinstate options to change scale based on type of input series.
def plot_drawdown(
    pnl: pd.Series,
    ylim: Optional[str] = None,
    # unit: str = "%",
    title_suffix: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot drawdown.

    :param pnl: series of per-period PnL
    :param ylim: either "fixed", "scalable" or None. default is None corresponds
        to "scalable". If y_lim is set to "fixed", the axes limit relies on units
        with possible values of -1 for "ratio", -100 for "%" and -10000 for "bps"
    :param unit: `ratio`, `%`, input series is rescaled appropriately
    :param title_suffix: suffix added to the title
    :param ax: axes
    :param events: list of tuples with dates and labels to point out on the plot
    """
    ylim = ylim or "scalable"
    title_suffix = title_suffix or ""
    # scale_coeff = _choose_scaling_coefficient(unit)
    scale_coeff = 1
    drawdown = -scale_coeff * costatis.compute_drawdown(pnl)
    label = drawdown.name or "drawdown"
    # title = f"Drawdown ({unit})"
    title = "Drawdown"
    ax = ax or plt.gca()
    drawdown.plot(ax=ax, label="_nolegend_", color="b", linewidth=3.5)
    drawdown.plot.area(
        ax=ax, title=f"{title}{title_suffix}", label=label, color="b", alpha=0.3
    )
    cplpluti.maybe_add_events(ax=ax, events=events)
    if ylim == "scalable":
        ax.set_ylim(top=0)
    # The drawdown is negative is either -1, -100 or -10000 according to units.
    elif ylim == "fixed":
        ax.set_ylim(bottom=-scale_coeff, top=0)
    else:
        raise ValueError("Invalid bottom ylim='%s'" % ylim)
    # ax.set_ylabel(unit)
    ax.set_ylabel("drawdown")
    ax.legend()
