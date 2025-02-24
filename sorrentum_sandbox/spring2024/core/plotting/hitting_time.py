"""
Import as:

import core.plotting.hitting_time as cplhitim
"""

import logging
from typing import List, Optional

import pandas as pd

import core.statistics as costatis
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def plot_hitting_time_cdf(
    time_window: float,
    grid_width: float,
    value: float,
    *,
    vline_time_points: Optional[List[float]] = None,
) -> pd.Series:
    """
    :param time_window: length of time (e.g., in seconds)
    :param grid_width: grid width in terms of time unit (e.g., seconds)
    :param value: value to hit (measured in units of Brownian motion standard
      deviations over the time window)
    :param vline_time_points: time points inside `time_window` at which to
        plot a vertical line
    """
    #
    hitting_time_cdf = (
        costatis.get_standard_brownian_motion_hitting_time_truncated_cdf(
            grid_width / time_window,
            value,
        )
    )
    ax = hitting_time_cdf.plot(
        ylim=(0, 1),
    )
    if vline_time_points is not None:
        for time_point in vline_time_points:
            normalized_time_point = time_point / time_window
            hdbg.dassert_lte(0, normalized_time_point)
            hdbg.dassert_lte(normalized_time_point, 1)
            ax.axvline(normalized_time_point, color="red")
    return hitting_time_cdf
