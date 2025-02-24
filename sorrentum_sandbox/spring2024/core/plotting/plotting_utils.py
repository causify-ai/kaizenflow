"""
Import as:

import core.plotting.plotting_utils as cplpluti
"""


import logging
import math
from typing import Any, List, Optional, Tuple, Union

import matplotlib as mpl
import matplotlib.cm as mcm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

COLORMAP = Union[str, mpl.colors.Colormap]

FIG_SIZE = (20, 5)


def configure_notebook_for_presentation() -> None:
    """
    Update settings for plotting functions:

    - Higher quality for the plots.
    - Larger fonts on the plots.
    """
    # Set the higher quality of the graph.
    mpl.rcParams["figure.dpi"] = 300
    # Set the size of the font in the plot.
    small_size = 15
    medium_size = 15
    bigger_size = 15
    # Update the fonts for graph's constituents.
    plt.rc("font", size=small_size)  # controls default text sizes
    plt.rc("axes", titlesize=small_size)  # fontsize of the axes title
    plt.rc("axes", labelsize=medium_size)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=small_size)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=small_size)  # fontsize of the tick labels
    plt.rc("legend", fontsize=small_size)  # legend fontsize
    plt.rc("figure", titlesize=bigger_size)  # fontsize of the figure title


def get_multiple_plots(
    num_plots: int,
    num_cols: int,
    y_scale: Optional[float] = None,
    *args: Any,
    **kwargs: Any,
) -> Tuple[mpl.figure.Figure, np.array]:
    """
    Create figure to accommodate `num_plots` plots.

    The figure is arranged in rows with `num_cols` columns.

    :param num_plots: number of plots
    :param num_cols: number of columns to use in the subplot
    :param y_scale: the height of each plot. If `None`, the size of the whole
        figure equals the default `figsize`
    :return: figure and array of axes
    """
    hdbg.dassert_lte(1, num_plots)
    hdbg.dassert_lte(1, num_cols)
    # Heuristic to find the dimension of the fig.
    if y_scale is not None:
        hdbg.dassert_lt(0, y_scale)
        ysize = math.ceil(num_plots / num_cols) * y_scale
        figsize: Optional[Tuple[float, float]] = (20, ysize)
    else:
        figsize = None
    if "tight_layout" not in kwargs and not kwargs.get(
        "constrained_layout", False
    ):
        kwargs["tight_layout"] = True
    fig, ax = plt.subplots(
        math.ceil(num_plots / num_cols),
        num_cols,
        figsize=figsize,
        *args,
        **kwargs,
    )
    if isinstance(ax, np.ndarray):
        ax = ax.flatten()
    else:
        ax = np.array([ax])
    # Remove extra axes that can appear when `num_cols` > 1.
    empty_axes = ax[num_plots:]
    for empty_ax in empty_axes:
        empty_ax.remove()
    return fig, ax[:num_plots]


def maybe_add_events(
    ax: mpl.axes.Axes, events: Optional[List[Tuple[str, Optional[str]]]]
) -> None:
    """
    Add labeled vertical lines at events' dates on a plot.

    :param ax: axes
    :param events: list of tuples with dates and labels to point out on the plot
    """
    if not events:
        return None
    colors = mcm.get_cmap("Set1")(np.linspace(0, 1, len(events)))
    for event, color in zip(events, colors):
        ax.axvline(
            x=pd.Timestamp(event[0]),
            label=event[1],
            color=color,
            linestyle="--",
        )
    return None


def choose_scaling_coefficient(unit: str) -> int:
    if unit == "%":
        scale_coeff = 100
    elif unit == "bps":
        scale_coeff = 10000
    elif unit == "ratio":
        scale_coeff = 1
    else:
        raise ValueError("Invalid unit='%s'" % unit)
    return scale_coeff


def plot_barplot(
    srs: pd.Series,
    orientation: str = "vertical",
    annotation_mode: str = "pct",
    string_format: str = "%.2f",
    top_n_to_plot: Optional[int] = None,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    unicolor: bool = False,
    color_palette: Optional[List[Tuple[float, float, float]]] = None,
    figsize: Optional[Tuple[int, int]] = None,
    rotation: int = 0,
    ax: Optional[mpl.axes.Axes] = None,
    yscale: Optional[str] = None,
) -> None:
    """
    Plot a barplot.

    :param srs: pd.Series
    :param orientation: vertical or horizontal bars
    :param annotation_mode: `pct`, `value` or None
    :param string_format: format of bar annotations
    :param top_n_to_plot: number of top N integers to plot
    :param title: title of the plot
    :param xlabel: label of the X axis
    :param unicolor: if True, plot all bars in neutral blue color
    :param color_palette: color palette
    :param figsize: size of plot
    :param rotation: rotation of xtick labels
    :param ax: axes
    :param yscale: y-axis scale is "linear" (if None) or "log"
    """

    def _get_annotation_loc(
        x_: float, y_: float, height_: float, width_: float
    ) -> Tuple[float, float]:
        if orientation == "vertical":
            return x_, y_ + max(height_, 0)
        if orientation == "horizontal":
            return x_ + max(width_, 0), y_
        raise ValueError("Invalid orientation='%s'" % orientation)

    # Get default figure size.
    if figsize is None:
        figsize = FIG_SIZE
    if top_n_to_plot is None:
        # If top_n not specified, plot all values.
        srs_top_n = srs
    else:
        # Assert N>0.
        hdbg.dassert_lte(1, top_n_to_plot)
        # Sort in descending order.
        srs_sorted = srs.sort_values(ascending=False)
        # Select top N.
        srs_top_n = srs_sorted[:top_n_to_plot]
    # Choose colors.
    if unicolor:
        color = sns.color_palette("deep")[0]
    else:
        color_palette = color_palette or sns.diverging_palette(10, 133, n=2)
        color = (srs > 0).map({True: color_palette[-1], False: color_palette[0]})
    # Choose orientation.
    if orientation == "vertical":
        kind = "bar"
    elif orientation == "horizontal":
        kind = "barh"
    else:
        raise ValueError("Invalid orientation='%s'" % orientation)
    # Plot top N.
    ax = srs_top_n.plot(
        kind=kind, color=color, rot=rotation, title=title, ax=ax, figsize=figsize
    )
    # Choose scale.
    yscale = yscale or "linear"
    hdbg.dassert_in(yscale, ["log", "linear"], f"Invalid scale={yscale}")
    if orientation == "vertical":
        ax.set_yscale(yscale)
    elif orientation == "horizontal":
        # The axes get swapped, so y-axis becomes x-axis.
        ax.set_xscale(yscale)
    else:
        raise ValueError("Invalid orientation='%s'" % orientation)
    # Add annotations to bars.
    # Note: annotations in both modes are taken from
    # entire series, not top N.
    if annotation_mode:
        if annotation_mode == "pct":
            annotations = srs * 100 / srs.sum()
            string_format = string_format + "%%"
            annotations = annotations.apply(lambda z: string_format % z)
        elif annotation_mode == "value":
            annotations = srs.apply(lambda z: string_format % z)
        else:
            raise ValueError("Invalid annotations_mode='%s'" % annotation_mode)
        # Annotate bars.
        for i, p in enumerate(ax.patches):
            height = p.get_height()
            width = p.get_width()
            x, y = p.get_xy()
            annotation_loc = _get_annotation_loc(x, y, height, width)
            ax.annotate(annotations.iloc[i], annotation_loc)
    # Set X-axis label.
    if xlabel:
        ax.set(xlabel=xlabel)
