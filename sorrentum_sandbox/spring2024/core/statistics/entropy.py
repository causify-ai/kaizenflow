"""
Import as:

import core.statistics.entropy as cstaentr
"""


import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_surprise(data: pd.Series, alpha: float) -> float:
    """
    Compute the alpha-surprise per entry after probability normalizing `data`.

    This treats `data` as a probability space. All values of `data` must be
    nonnegative. Before calculating surprise, the data is renormalized so that
    its sum is one.

    See the following for details:
    https://golem.ph.utexas.edu/category/2008/11/entropy_diversity_and_cardinal_1.html

    :param data: series of nonnegative numbers
    :param alpha: parameter in [0, np.inf]
    """
    hdbg.dassert_ne(
        1, alpha, "The special case `alpha=1` must be handled separately."
    )
    normalized_data = _check_alpha_and_normalize_data(data, alpha)
    surprise = (1 - normalized_data ** (alpha - 1)) / (alpha - 1)
    return surprise


def compute_diversity(data: pd.Series, alpha: float) -> float:
    """
    Compute the alpha-diversity of `data` after probability normalizing.

    Special cases:
      - alpha = 0: `data.count() - 1`
      - alpha = 1: Shannon entropy
      - alpha = 2: Simpson diversity
      - alpha = np.inf: 0

    Conceptually, this can be calculated by
        ```
        surpise = compute_surprise(data, alpha)
        normalized_data = data / data.sum()
        diversity = (normalized_data * surprise).sum()
        ```
    We implement the function differently so as to avoid numerical instability.

    :param data: series of nonnegative numbers
    :param alpha: parameter in [0, np.inf]
    :return: a number between 0 and the surprise of `1 / data.count()`.
    """
    normalized_data = _check_alpha_and_normalize_data(data, alpha)
    if alpha == 1:
        log_normalized_data = np.log(normalized_data)
        entropy = -(normalized_data * log_normalized_data).sum()
        diversity = np.exp(entropy)
    else:
        sum_of_powers = (normalized_data**alpha).sum()
        diversity = (1 - sum_of_powers) / (alpha - 1)
    return diversity


def compute_cardinality(data: pd.Series, alpha: float) -> float:
    """
    Compute the alpha-cardinality of `data` after probability normalizing.

    Special cases:
      - alpha = 0: `data.count()`
      - alpha = 1: exp(Shannon entropy)
      - alpha = 2: reciprocal Simpson
      - alpha = np.inf: 1 / max(normalized data)

    This is the exponential of the alpha-entropy.

    Conceptually, this can be calculated by
        ```
        diversity = compute_diversity(data, alpha)
        inverse_surprise = (1 - (alpha - 1) * diversity) ** (1 / (alpha - 1))
        cardinality = 1 / inverse_surprise
        ```
    We implement the function differently so as to avoid numerical instability.

    :param data: series of nonnegative numbers
    :param alpha: parameter in [0, np.inf]
    :return: a number between 1 and `data.count()`
    """
    normalized_data = _check_alpha_and_normalize_data(data, alpha)
    if np.isinf(alpha):
        cardinality = 1 / normalized_data.max()
    elif alpha == 1:
        log_normalized_data = np.log(normalized_data)
        entropy = -(normalized_data * log_normalized_data).sum()
        cardinality = np.exp(entropy)
    else:
        sum_of_powers = (normalized_data**alpha).sum()
        cardinality = sum_of_powers ** (1 / (1 - alpha))
    return cardinality


def compute_entropy(data: pd.Series, alpha: float) -> float:
    """
    Compute the alpha-entropy of `data` after probability normalizing.

    Special cases:
      - alpha = 0: `log(data.count())`
      - alpha = 1: Shannon entropy
      - alpha = 2: log reciprocal Simpson
      - alpha = np.inf: log reciprocal Berger-Parker

    This is the log of of the alpha-cardinality.

    :param data: series of nonnegative numbers
    :param alpha: parameter in [0, np.inf]
    :return: a number between 0 and `log(data.count())`
    """
    cardinality = compute_cardinality(data, alpha)
    entropy = np.log(cardinality)
    return entropy


# TODO(Paul): Deprecate and replace with `compute_cardinality()`.
def compute_hill_number(data: pd.Series, q: float) -> float:
    """
    Compute the Hill number as a measure of diversity.

    - The output is a number between zero and the number of points in `data`
    - The result can be used as an "effective count"
    - Note that q = 1 corresponds to exp(Shannon entropy)
    - The q = np.inf case is used in the calculation of stable rank

    Transformations of the Hill number can be related to
    - Shannon index
    - Renyi entropy
    - Simpson index
    - Gini-Simpson index
    - Berger-Parker index
    See https://en.wikipedia.org/wiki/Diversity_index for details.

    :param data: data representing class counts or probabilities
    :param q: order of the Hill number
      - q = 1 provides an entropy measure
      - increasing q puts more weight on top relative classes
    :return: a float between zero and data.size
    """
    hdbg.dassert_lte(1, q, "Order `q` must be greater than or equal to 1.")
    hdbg.dassert_isinstance(data, pd.Series)
    hdbg.dassert(
        (data >= 0).all(), "Series `data` must have only nonnegative values."
    )
    hill_number = compute_cardinality(data, q)
    return hill_number


def _check_alpha_and_normalize_data(data: pd.Series, alpha: float) -> pd.Series:
    """
    Check assumptions used in surprise, diversity, and entropy functions.

    :param data: series of nonnegative numbers
    :param alpha: parameter in [0, np.inf]
    """
    hdbg.dassert_lte(
        0, alpha, "Parameter `alpha` must be greater than or equal to 0."
    )
    hdbg.dassert_isinstance(data, pd.Series)
    hdbg.dassert(
        (data >= 0).all(), "Series `data` must have only nonnegative values."
    )
    # Normalize nonnegative data so that it sums to one.
    normalized_data = data / data.sum()
    return normalized_data
