"""
Import as:

import core.statistics.binning as cstabinn
"""

import logging
from typing import Tuple, Union

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def get_symmetric_normal_quantiles(bin_width: float) -> Tuple[list, list]:
    """
    Get centered quantiles of normal distribution.

    This function creates a centered bin of width `bin_width` about zero and
    then adds bins on either side until the entire distribution is captured.
    All bins carry an equal percentage of the normal distribution, with the
    possible exception of the two tail bins.

    :param bin_width: percentage of normal distribution to capture in each bin
    :return: ordered endpoints of bins, including `-np.inf` and `np.inf`
    """
    hdbg.dassert_lt(0, bin_width)
    hdbg.dassert_lt(bin_width, 1)
    half_bin_width = bin_width / 2
    #
    positive_bin_boundaries = [
        sp.stats.norm.ppf(x + 0.5)
        for x in np.arange(half_bin_width, 0.5, bin_width)
    ]
    positive_bin_medians = [
        sp.stats.norm.ppf(x + 0.5) for x in np.arange(bin_width, 0.5, bin_width)
    ]
    # Handle the corner case where not enough bin medians are calculated in
    # the iteration.
    if len(positive_bin_medians) < len(positive_bin_boundaries):
        last_bin_cutoff = positive_bin_boundaries[-1]
        sf = sp.stats.norm.sf(last_bin_cutoff)
        last_median = sp.stats.norm.ppf(1 - sf / 2)
        positive_bin_medians.extend([last_median])
    # Reflect the bin boundaries.
    positive_bin_boundaries.append(np.inf)
    negative_bin_boundaries = [-x for x in reversed(positive_bin_boundaries)]
    bin_boundaries = negative_bin_boundaries + positive_bin_boundaries
    # Reflect the bin medians and include `0`.
    negative_bin_medians = [-x for x in reversed(positive_bin_medians)]
    bin_medians = negative_bin_medians + [0] + positive_bin_medians
    # Ensure that the number of bin boundaries and bins matches.
    num_bins = len(bin_boundaries) - 1
    _LOG.debug("num_bins=%d", num_bins)
    hdbg.dassert_eq(num_bins, len(bin_medians))
    #
    return bin_boundaries, bin_medians


def group_by_bin(
    df: pd.DataFrame,
    bin_col: Union[str, int],
    bin_width: float,
    aggregation_col: Union[str, int],
    normalize_bin_col_values: bool = False,
) -> pd.DataFrame:
    """
    Compute aggregations in `aggregation_col` according to bins from `bin_col`.

    :param df: dataframe with numerical cols
    :param bin_col: a column used for binning; ideally the values are centered
        and approximately normally distributed, though not necessarily
        standardized
    :param bin_width: the percentage of data to be captured by each (non-tail)
        bin
    :param aggregation_col: the numerical col to aggregate
    :param normalize_bin_col_values: divide `bin_col` values by their standard
        deviation iff `True`
    :return: dataframe with count, mean, stdev of `aggregation_col` by bin
    """
    # Get bin boundaries assuming a normal distribution. Using theoretical
    # boundaries rather than empirical ones facilities comparisons across
    # different data.
    bin_boundaries, _ = get_symmetric_normal_quantiles(bin_width)
    # Standardize the binning column and cut.
    bin_col_values = df[bin_col]
    if normalize_bin_col_values:
        bin_col_values /= bin_col_values.std()
        _LOG.debug("Standardizing bin_col=%s values", bin_col)
    cuts = pd.cut(bin_col_values, bin_boundaries)
    # Group the aggregation column according to the bins.
    grouped_col_values = df.groupby(cuts, observed=False)[aggregation_col]
    # Aggregate the grouped result.
    count = grouped_col_values.count().rename("count")
    mean = grouped_col_values.mean().rename("mean")
    stdev = grouped_col_values.std().rename("stdev")
    # Join aggregation and counts.
    result_df = pd.concat(
        [
            count,
            mean,
            stdev,
        ],
        axis=1,
    )
    return result_df
