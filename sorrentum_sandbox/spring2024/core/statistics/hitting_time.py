"""
Import as:

import core.statistics.hitting_time as csthitim
"""

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Hitting time statistics
# #############################################################################


def get_standard_brownian_motion_hitting_time_truncated_cdf(
    grid_width: float,
    value: float,
) -> pd.Series:
    """
    Get CDF as a series for the SBM hitting time.

    The CDF is truncated at time T=1.

    :param grid_width: controls the CDF resolution
    :param value: the value for the SBM to hit
    :return: CDF as a series
    """
    hdbg.dassert_lte(grid_width, 0.5)
    hdbg.dassert_lt(0, grid_width)
    grid = np.arange(grid_width, 1 + grid_width, grid_width)
    # By the reflection principle it suffices to consider positive values.
    cdf_vals = 2 * sp.stats.norm.cdf(-abs(value) / np.sqrt(grid))
    cdf = pd.Series(cdf_vals, grid, name="sbm_hitting_time_cdf")
    return cdf


def compute_threshold_upcrossing_prob(
    thresholds: pd.Series,
) -> pd.Series:
    """
    Compute prob of SBM's crossing threshold within time 1.

    :param thresholds: series of thresholds
    :return: threshold upcrossing probability at each threshold
    """
    values = 2 * sp.stats.norm.cdf(-thresholds)
    result = pd.Series(values, thresholds.index, name="threshold_upcrossing_prob")
    return result


def compute_early_threshold_upcrossing_prob(
    thresholds: pd.Series,
    early_time: float,
) -> pd.Series:
    """
    Compute prob of SBM's crossing threshold by `early_time`.

    :param thresholds: series of thresholds
    :param early_time: a time between 0 and 1
    :return: threshold upcrossing probability at each threshold
    """
    hdbg.dassert_lte(0, early_time)
    hdbg.dassert_lte(early_time, 1)
    values = 2 * sp.stats.norm.cdf(-thresholds / np.sqrt(early_time))
    result = pd.Series(
        values, thresholds.index, name="early_threshold_upcrossing_prob"
    )
    return result


def compute_early_threshold_upcrossing_conditional_prob(
    thresholds: pd.Series,
    early_time: float,
) -> pd.Series:
    """
    Compute conditional prob of SBM's crossing threshold by `early_time`.

    :param thresholds: series of thresholds
    :param early_time: a time between 0 and 1
    :return: threshold upcrossing probability at each threshold given that an
        upcrossing occurs within time 1
    """
    prob_upcrossing = compute_threshold_upcrossing_prob(thresholds)
    prob_early_upcrossing = compute_early_threshold_upcrossing_prob(
        thresholds, early_time
    )
    result = prob_early_upcrossing / prob_upcrossing
    result.name = "early_threshold_upcrossing_conditional_prob"
    return result


def compute_expected_value_given_max(
    maximums: pd.Series,
) -> pd.Series:
    """
    Compute expected value at time 1 of SBM given interval maximum.
    """
    term1 = maximums
    c1 = np.sqrt(2 * np.pi)
    term2 = -c1 * sp.stats.norm.cdf(-maximums) * np.exp(0.5 * maximums**2)
    values = term1 + term2
    result = pd.Series(values, maximums.index)
    return result


def compute_expected_value_given_max_leq_threshold(
    thresholds: pd.Series,
) -> pd.Series:
    """
    Compute expected time 1 value given max(SBM) <= threshold.
    """
    prob_upcrossing = compute_threshold_upcrossing_prob(thresholds)
    expected_value = -thresholds * prob_upcrossing / (1 - prob_upcrossing)
    prob_one_event = prob_upcrossing >= 1
    expected_value[prob_one_event] = -np.sqrt(np.pi / 2)
    return expected_value


def compute_conditional_prob_given_max_leq_threshold(
    terminal_values: pd.Series,
    threshold: float,
) -> float:
    """
    Compute pdf of value at time 1 given max(SBM) <= `threshold`.

    :param terminal_value: value of SBM at time 1
    :param threshold: a threshold for which it is known that the max of the
        SBM over the unit time interval is less than the threshold.
    """
    sgns = (terminal_values <= threshold).astype(int)
    term1 = -np.exp(-0.5 * (2 * threshold - terminal_values) ** 2)
    term2 = -np.exp(-0.5 * terminal_values**2)
    const1 = np.sqrt(2 * np.pi)
    const2 = sp.special.erf(threshold / np.sqrt(2))
    values = sgns * (term1 - term2) / (const1 * const2)
    result = pd.Series(
        values,
        terminal_values.index,
        name="conditional_prob_given_max_leq_threshold",
    )
    return result


def compute_conditional_prob_given_max_not_leq_threshold(
    terminal_values: pd.Series,
    threshold: float,
) -> float:
    """
    Compute pdf of value at time 1 given max(SBM) > `threshold`.

    :param terminal_value: value of SBM at time 1
    :param threshold: a threshold for which it is known that the max of the
        SBM over the unit time interval is greater than the threshold.
    """
    term1_sgns = (terminal_values >= threshold).astype(int)
    term2_sgns = 1 - term1_sgns
    term1 = term1_sgns * np.exp(-0.5 * terminal_values**2)
    term2 = term2_sgns * np.exp(-0.5 * (2 * threshold - terminal_values) ** 2)
    const1 = np.sqrt(2 * np.pi)
    term3 = 2 * sp.stats.norm.cdf(-threshold)
    values = (term1 + term2) / (const1 * term3)
    result = pd.Series(
        values,
        terminal_values.index,
        name="conditional_prob_given_max_not_leq_threshold",
    )
    return result


def compute_threshold_upcrossing_probabilities(
    thresholds: List[float],
    early_upcrossing_threshold: float,
) -> pd.DataFrame:
    """
    Compute SBM-based upcrossing probabilities.

    TODO(Paul): Refactor this using the helpers above.
    """
    num_thresholds = len(thresholds)
    _LOG.debug("num thresholds=%d" % num_thresholds)
    upcrossing_probs = []
    early_upcrossing_probs_given_upcrossing = []
    for threshold in thresholds:
        # Compute upcrossing probabilities.
        upcrossing_prob = 2 * sp.stats.norm.cdf(-threshold)
        upcrossing_probs.append(upcrossing_prob)
        # Compute early upcrossing probabilities, given upcrossing.
        early_upcrossing_prob_given_upcrossing = (
            2
            * sp.stats.norm.cdf(-threshold / np.sqrt(early_upcrossing_threshold))
            / upcrossing_prob
        )
        early_upcrossing_probs_given_upcrossing.append(
            early_upcrossing_prob_given_upcrossing
        )
    upcrossing_probs_srs = pd.Series(
        upcrossing_probs, range(1, num_thresholds + 1)
    )
    first_upcrossing_probs = upcrossing_probs_srs.multiply(
        (1 - upcrossing_probs_srs).cumprod().shift(1), fill_value=1
    )
    dict_ = {
        "threshold": thresholds,
        "prob_upcrossing": upcrossing_probs,
        "prob_early_upcrossing_given_upcrossing": early_upcrossing_probs_given_upcrossing,
        "prob_first_upcrossing": first_upcrossing_probs.values,
    }
    df = pd.DataFrame(dict_, index=range(1, num_thresholds + 1))
    df.index.name = "trial"
    return df


# #############################################################################
# Hitting time tools
# #############################################################################


def get_first_threshold_upcrossing(
    srs: pd.Series,
    threshold: float,
    *,
    num_steps_to_skip: int = 0,
) -> Tuple[int, float]:
    """
    Return first threshold upcrossing, possibly with delay effects.

    TODO: Consider edge case around what constitutes a step to skip, etc.
    """
    num_steps = srs.size - 1
    _LOG.debug("num_steps=%d" % num_steps)
    hdbg.dassert_lte(0, num_steps_to_skip)
    hdbg.dassert_lt(num_steps_to_skip, num_steps)
    trimmed_rw = srs.reset_index(drop=True).iloc[num_steps_to_skip:]
    # If, after skipping `num_steps_to_skip`, the random walk location is
    # above `threshold`, we count it as an upcrossing and return a value from
    # the walk.
    upcrossing_step = trimmed_rw[trimmed_rw >= threshold].first_valid_index()
    if upcrossing_step is None:
        val = np.nan
        upcrossing_step = -1
    else:
        # If the trimmed walk is already above `threshold`, we
        #  conservatively take the smaller value.
        val_candidates = [trimmed_rw.loc[upcrossing_step]]
        if upcrossing_step > 0:
            val_candidates.append(srs.iloc[upcrossing_step - 1])
        val = max(min(val_candidates), threshold)
    _LOG.debug("upcrossing_step=%d" % upcrossing_step)
    return upcrossing_step, val
