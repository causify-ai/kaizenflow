"""
Import as:

import core.plotting.normality as cplonorm
"""

import logging
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr

_LOG = logging.getLogger(__name__)


def plot_qq(
    srs: pd.Series,
    ax: Optional[mpl.axes.Axes] = None,
    dist: Optional[str] = None,
    nan_mode: Optional[str] = None,
) -> None:
    """
    Plot ordered values against theoretical quantiles of the given
    distribution.

    :param srs: data to plot
    :param ax: axes in which to draw the plot
    :param dist: distribution name
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    """
    dist = dist or "norm"
    ax = ax or plt.gca()
    nan_mode = nan_mode or "drop"
    x_plot = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    sp.stats.probplot(x_plot, dist=dist, plot=ax)
    ax.set_title(f"{dist} probability plot")
