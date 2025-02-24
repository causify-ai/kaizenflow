"""
Import as:

import core.statistics.empirical_distribution_function as csemdifu
"""

import logging
from typing import List

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def compute_empirical_cdf(srs: pd.Series) -> pd.Series:
    """
    Compute the empirical cdf from data.

    TODO(Paul): Compare to now-available scipy.stats.ecdf.

    :param srs: data series
    :return: series with
      - x values equal to sorted `srs`
      - y values equal to percentage of data leq x value
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    # Sort the series, drop NaNs, and account for multiplicities.
    nonan_srs = srs.dropna()
    sorted_data_counts = nonan_srs.value_counts().sort_index()
    # The new index comes from the sorted values. Rename for clarity.
    new_idx = sorted_data_counts.index
    if srs.name is None:
        name = "ecdf"
    else:
        name = srs.name + ".ecdf"
    if nonan_srs.count() == 0:
        ecdf = pd.Series(name=name, dtype="float64")
    else:
        # Create the values representing cumulative percentage seen.
        increment = 1 / nonan_srs.count()
        new_values = (sorted_data_counts * increment).cumsum()
        ecdf = pd.Series(new_values, new_idx, name=name)
    return ecdf


def combine_empirical_cdfs(ecdfs: List[pd.Series]) -> pd.DataFrame:
    """
    Combine multiple ecdfs into a dataframe (e.g., for easy plotting).

    :param ecdfs: list of ecdfs represented as pd.Series
    :return: dataframe with each ecdf as a column and index as a union of
        the indices
    """
    hdbg.dassert_container_type(ecdfs, list, pd.Series)
    valid_ecdfs = []
    for ecdf in ecdfs:
        if ecdf.empty:
            _LOG.debug("Omitting empty series `%s`", ecdf.name)
            continue
        hpandas.dassert_increasing_index(ecdf)
        hdbg.dassert(not ecdf.isna().any())
        values_are_sorted = np.all(ecdf.values[:-1] <= ecdf.values[1:])
        hdbg.dassert(values_are_sorted)
        hdbg.dassert_lte(0, ecdf.min())
        hdbg.dassert_lte(abs(1 - ecdf.max()), 1e-9)
        valid_ecdfs.append(ecdf)
    combined_ecdfs = pd.concat(valid_ecdfs, axis=1).sort_index().ffill().fillna(0)
    return combined_ecdfs


def compute_and_combine_empirical_cdfs(data: List[pd.Series]) -> pd.DataFrame:
    """
    Compute ecdfs for each series and combine into a single dataframe.
    """
    ecdfs = []
    for srs in data:
        ecdf = compute_empirical_cdf(srs)
        ecdfs.append(ecdf)
    combined_ecdfs = combine_empirical_cdfs(ecdfs)
    return combined_ecdfs


def compute_empirical_cdf_with_bounds(
    srs: pd.Series, alpha: float
) -> pd.DataFrame:
    """
    Compute the empirical cdf from data.

    The confidence interval is calculated using the
    Dvoretzky–Kiefer–Wolfowitz inequality.

    :param srs: data series
    :param alpha: interval contains true CDF with probability 1 - alpha
    :return: dataframe with the ecdf and lower/upper CI bounds
    """
    hdbg.dassert_lt(0, alpha)
    hdbg.dassert_lt(alpha, 1)
    ecdf = compute_empirical_cdf(srs)
    count = ecdf.count()
    epsilon = np.sqrt(np.log(2 / alpha) / (2 * count))
    lower_CI = (ecdf - epsilon).clip(lower=0.0).rename("lower_CI")
    upper_CI = (ecdf + epsilon).clip(upper=1.0).rename("upper_CI")
    df = pd.concat([ecdf, lower_CI, upper_CI], axis=1)
    return df
