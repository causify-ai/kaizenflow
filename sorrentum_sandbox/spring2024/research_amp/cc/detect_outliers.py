"""
Code to detect outliers.

Import as:

import research_amp.cc.detect_outliers as raccdeou
"""
import logging

import numpy as np
import pandas as pd

import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def detect_outlier_at_index(
    srs: pd.Series,
    idx: int,
    n_samples: int,
    z_score_threshold: float,
) -> bool:
    """
    Check if a value at index `idx` in a series is an outlier.

    The passed series is supposed to be ordered by increasing timestamps.

    This function
    - detects z-score window index boundaries with respeect to index order and number of samples
    - computes the z-score of the current element with respect to the z-score window values
    - compares the z-score to the threshold to declare the current element an outlier

    :param srs: input series
    :param idx: numerical index of a value to check
    :param n_samples: number of samples in z-score window
    :param z_score_threshold: threshold to mark a value as an outlier based on
        its z-score in the window
    :return: whether the element at index idx is an outlier
    """
    # Set z-score window boundaries.
    window_first_index = max(0, idx - n_samples)
    # Get a series window to compute z-score for.
    window_srs = srs.iloc[window_first_index : idx + 1]
    # Compute z-score of a value at index.
    z_score = (srs.iloc[idx] - window_srs.mean()) / window_srs.std()
    # Return if a value at index is an outlier.
    # Done via `<=` since a series can contain None values that should be detected
    # as well but will result to NaN if compared to the threshold directly.
    is_outlier = not (abs(z_score) <= z_score_threshold)
    return is_outlier


def detect_outliers(
    srs: pd.Series,
    n_samples: int,
    z_score_threshold: float,
) -> np.array:
    """
    Return the mask representing the outliers.

    Check if a value at index `idx` in a series is an outlier with respect to
    the previous `n_samples`.

    The passed series is supposed to be ordered by increasing timestamps.

    This function
    - masks the values of srs before `idx` using `mask` to remove the previously found outliers
    - computes the z-score of each element consequtively with respect to the remaining values
    - compares the z-score to the threshold to declare an element as an outlier

    :param srs: input series
    :param n_samples: number of samples in Z-score window
    :param z_score_threshold: threshold to mark a value as an outlier based on
        its z-score in the window
    :return: whether the element at index idx is an outlier
    """
    hpandas.dassert_monotonic_index(srs)
    # Initialize mask for outliers.
    mask = np.array([False] * srs.shape[0])
    # Set outlier count.
    outlier_count = 0
    # Iterate over each element and update the mask for it.
    for idx in range(1, srs.shape[0]):
        # Drop already detected outliers.
        valid_srs = srs[~mask]
        # Adjust numerical index to the number of dropped outliers.
        idx_adj = idx - outlier_count
        # Detect if a value at requested numerical index is an outlier
        # and reflect it in the mask.
        mask[idx] = detect_outlier_at_index(
            valid_srs, idx_adj, n_samples, z_score_threshold
        )
        # Increase the outlier count if an outlier was detected.
        if mask[idx]:
            outlier_count = outlier_count + 1
    return mask
