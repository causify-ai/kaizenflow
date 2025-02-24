"""
Import as:

import core.plotting.counts as cplocoun
"""

import logging
import math
from typing import Any, Optional, Tuple

import matplotlib as mpl
import pandas as pd

import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


FIG_SIZE = (20, 5)


# #############################################################################
# Data count plots.
# #############################################################################


def plot_value_counts(
    srs: pd.Series,
    dropna: bool = True,
    ax: Optional[mpl.axes.Axes] = None,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Plot barplots for the counts of a series and print the values.

    Same interface as plot_count_series() but computing the count of the
    given series `srs`.
    """
    # Compute the counts.
    counts = srs.value_counts(dropna=dropna)
    # Plot.
    return plot_counts(counts, *args, ax=ax, **kwargs)


def plot_counts(
    counts: pd.Series,
    top_n_to_print: int = 10,
    top_n_to_plot: Optional[int] = None,
    plot_title: Optional[str] = None,
    label: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    figsize: Optional[Tuple[int, int]] = None,
    rotation: int = 0,
) -> None:
    """
    Plot barplots for series containing counts and print the values.

    If the number of labels is over 20, the plot is oriented horizontally
    and the height of the plot is automatically adjusted.

    :param counts: series to plot value counts for
    :param top_n_to_print: top N values by count to print. None for all. 0 for
        no values
    :param top_n_to_plot: like top_n_to_print, but for the plot
    :param plot_title: title of the barplot
    :param label: label of the X axis
    :param figsize: size of the plot
    :param rotation: rotation of xtick labels
    """
    hdbg.dassert_isinstance(counts, pd.Series)
    figsize = figsize or FIG_SIZE
    counts = counts.sort_values(ascending=False)
    # Display the top n counts.
    top_n_to_print = top_n_to_print or counts.size
    if top_n_to_print != 0:
        top_n_to_print = min(top_n_to_print, counts.size)
        print(
            f"First {top_n_to_print} out of {counts.size} labels:\n"
            f"{counts[:top_n_to_print].to_string()}"
        )
    # Plot the top n counts.
    if top_n_to_plot == 0:
        return
    top_n_to_plot = top_n_to_plot or counts.size
    # Plot horizontally or vertically, depending on counts number.
    if top_n_to_plot > 20:
        ylen = math.ceil(top_n_to_plot / 26) * 5
        figsize = (figsize[0], ylen)
        orientation = "horizontal"
    else:
        orientation = "vertical"
    cplpluti.plot_barplot(
        counts[:top_n_to_plot],
        orientation=orientation,
        title=plot_title,
        figsize=figsize,
        xlabel=label,
        rotation=rotation,
        unicolor=True,
        ax=ax,
    )
