"""
Import as:

import core.statistics.drawdown as cstadraw
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Drawdown statistics
# #############################################################################


def compute_drawdown_cdf(
    sharpe_ratio: float,
    volatility: float,
    drawdown: float,
    time: Optional[float] = None,
) -> float:
    """
    Compute the drawdown cdf for `drawdown` at `time` given SR, vol specs.

    - Refs:
      - https://www.jstor.org/stable/3318509
      - https://en.wikipedia.org/wiki/Reflected_Brownian_motion
    - DD has law like that of RBM(-mu, sigma ** 2)
    - RMB(-mu, sigma ** 2) converges in distribution as t -> infinity to an
      exponential distribution with parameter 2 * mu / (sigma ** 2)
    - The drawdown cdf for the asymptotic distribution can be expressed in a
      "scale-free" way via an exponential distribution with parameter 2 * SR
      provided we interpret the result as being expressed in units of
      volatility (see `compute_normalized_drawdown_cdf()`).

    NOTE: The maximum drawdown experienced up to time `time` may exceed any
        terminal drawdown.

    :param sharpe_ratio: Sharpe ratio
    :param volatility: volatility, with units compatible with those of the
        Sharpe ratio
    :param drawdown: drawdown as a positive ratio
    :param time: time in units consistent with those of SR and vol (i.e.,
        "years" if SR and vol are annualized)
    :return: Prob(drawdown at time `time` <= `drawdown`)
        - If time is `None`, then we use the limiting exponential distribution.
    """
    hdbg.dassert_lt(0, sharpe_ratio)
    hdbg.dassert_lt(0, volatility)
    hdbg.dassert_lt(0, drawdown)
    hdbg.dassert_lt(0, time)
    normalized_drawdown = drawdown / volatility
    probability = compute_normalized_drawdown_cdf(
        sharpe_ratio=sharpe_ratio,
        normalized_drawdown=normalized_drawdown,
        time=time,
    )
    return probability


def compute_normalized_drawdown_cdf(
    sharpe_ratio: float,
    normalized_drawdown: float,
    time: Optional[float] = None,
) -> float:
    """
    Compute the drawdown cdf for drawdown given in units of volatility.

    :param sharpe_ratio: Sharpe ratio
    :param normalized_drawdown: drawdown in units of volatility, e.g.,
        (actual) drawdown / volatility
    :param time: time in units consistent with those of SR
    :return: Prob(normalized drawdown at time `time` <= `normalized_drawdown`)
    """
    hdbg.dassert_lt(0, sharpe_ratio)
    hdbg.dassert_lt(0, normalized_drawdown)
    hdbg.dassert_lt(0, time)
    if time is None:
        a = np.inf
        b = np.inf
    else:
        # NOTE: SR and DD become unitless after these time multiplications.
        sr_mult_root_t = sharpe_ratio * np.sqrt(time)
        dd_div_root_t = normalized_drawdown / np.sqrt(time)
        a = sr_mult_root_t + dd_div_root_t
        b = sr_mult_root_t - dd_div_root_t
    probability: float = sp.stats.norm.cdf(a) - np.exp(
        -2 * sharpe_ratio * normalized_drawdown
    ) * sp.stats.norm.cdf(b)
    return probability


def compute_max_drawdown_approximate_cdf(
    sharpe_ratio: float, volatility: float, max_drawdown: float, time: float
) -> float:
    """
    Compute the approximate cdf for the maximum drawdown over a span of time.

    - https://www.sciencedirect.com/science/article/pii/S0304414913001695
    - G. F. Newell, Asymptotic Extreme Value Distribution for One-dimensional
      Diffusion Processes: https://www.jstor.org/stable/24900722

    TODO(*): Revisit units and rescaling.
    TODO(*): Maybe normalize drawdown.

    :return: estimate of
        Prob(max drawdown over time period of length `time` <= `max_drawdown`)
    """
    hdbg.dassert_lt(0, sharpe_ratio)
    hdbg.dassert_lt(0, volatility)
    hdbg.dassert_lt(0, max_drawdown)
    hdbg.dassert_lt(0, time)
    lambda_ = 2 * sharpe_ratio / volatility
    # lambda_ * max_drawdown is the same as
    #     -2 * sharpe_ratio * (max_drawdown / volatility)
    y = lambda_ * max_drawdown - np.log(time)
    probability: float = sp.stats.gumbel_r.cdf(y)
    return probability


def compute_max_drawdown(
    pnl: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate max drawdown statistic.

    :param pnl: series of per-period PnL
    :param prefix: optional prefix for metrics' outcome
    :return: max drawdown in units of PnL
    """
    hdbg.dassert_isinstance(pnl, pd.Series)
    prefix = prefix or ""
    result_index = [prefix + "max_drawdown"]
    nan_result = pd.Series(index=result_index, name=pnl.name, dtype="float64")
    if pnl.empty:
        _LOG.warning("Empty input series `%s`", pnl.name)
        return nan_result
    drawdown = compute_drawdown(pnl)
    max_drawdown = drawdown.max()
    result = pd.Series(data=max_drawdown, index=result_index, name=pnl.name)
    return result


def compute_drawdown(pnl: pd.Series) -> pd.Series:
    """
    Calculate drawdown of a time series of per-period PnL.

    At each point in time, drawdown is either zero (a new high-water mark is
    achieved), or positive, measuring the cumulative loss since the last
    high-water mark.

    According to our conventions, drawdown is always nonnegative.

    :param pnl: time series of per-period PnL
    :return: drawdown time series
    """
    hdbg.dassert_isinstance(pnl, pd.Series)
    pnl = hdatafr.apply_nan_mode(pnl, mode="fill_with_zero")
    cum_pnl = pnl.cumsum()
    running_max = np.maximum.accumulate(cum_pnl)  # pylint: disable=no-member
    drawdown = running_max - cum_pnl
    return drawdown


def compute_perc_loss_from_high_water_mark(log_rets: pd.Series) -> pd.Series:
    """
    Calculate drawdown in terms of percentage loss.

    :param log_rets: time series of log returns
    :return: drawdown time series as percentage loss
    """
    dd = compute_drawdown(log_rets)
    return 1 - np.exp(-dd)


def compute_time_under_water(pnl: pd.Series) -> pd.Series:
    """
    Generate time under water series.

    :param pnl: time series of per-period PnL
    :return: series of number of consecutive time points under water
    """
    drawdown = compute_drawdown(pnl)
    underwater_mask = drawdown != 0
    # Cumulatively count number of values in True/False groups.
    # Calculate the start of each underwater series.
    underwater_change = underwater_mask != underwater_mask.shift()
    # Assign each underwater series unique number, repeated inside each series.
    underwater_groups = underwater_change.cumsum()
    # Use `.cumcount()` on each underwater series.
    cumulative_count_groups = underwater_mask.groupby(
        underwater_groups
    ).cumcount()
    cumulative_count_groups += 1
    # Set zero drawdown counts to zero.
    n_timepoints_underwater = underwater_mask * cumulative_count_groups
    return n_timepoints_underwater
