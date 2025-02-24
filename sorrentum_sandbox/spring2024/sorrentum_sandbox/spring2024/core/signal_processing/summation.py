"""
Import as:

import core.signal_processing.summation as csiprsum
"""

import logging
from typing import List, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def combine_standardized_signals(
    df: pd.DataFrame,
    weights: List[Tuple[Union[str, int], int]],
    *,
    skipna: bool = False,
) -> pd.DataFrame:
    """
    Combine standardized signals and normalize to unit variance.

    :param df: dataframe of standardized signals
    :param weights: list of tuples consisting of column names and weights
    :param skipna: param propagated to `.sum()`. By default, all columns must
        have non-NaN values for the sum to be calculated. If `True`,
        standardization may no longer hold for the result.
    :return: 1-col dataframe with weighted sum
    """
    # Perform type checks.
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_isinstance(weights, list)
    # Collect the names associated with the weights.
    weight_idx = [weight[0] for weight in weights]
    # Assert that the weight names are present as columns in `df`.
    hdbg.dassert_is_subset(weight_idx, df.columns)
    # Extract the values of the weights.
    weight_vals = [weight[1] for weight in weights]
    # Construct a weight `pd.Series` derived from `weights`.
    weight_srs = pd.Series(weight_vals, weight_idx)
    # Calculate the reweighting factor require to standardize the variance
    # of the weighted sum.
    renormalization_factor = np.sqrt(1 / (weight_srs**2).sum())
    # Calculate the weighted sum, renormalized to unit variance.
    normalized_weighted_sum = (
        renormalization_factor * df[weight_idx] * weight_srs
    ).sum(axis=1, skipna=skipna)
    normalized_weighted_sum.name = "sum"
    return normalized_weighted_sum.to_frame()
