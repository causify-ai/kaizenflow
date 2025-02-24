"""
Import as:

import core.statistics.covariance_shrinkage as cstcoshr
"""

import logging
from typing import Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)
COL = Union[str, int]


# TODO(Paul): The same check is also found in "optimizer/utils.py". Unify.
def is_symmetric(matrix: pd.DataFrame, **kwargs) -> bool:
    hdbg.dassert_isinstance(matrix, pd.DataFrame)
    m, n = matrix.shape
    hdbg.dassert_eq(m, n)
    return np.allclose(matrix, matrix.T, **kwargs)


def compute_mv_loss(
    estimated_cov: pd.DataFrame,
    cov: pd.DataFrame,
) -> float:
    hdbg.dassert(is_symmetric(estimated_cov))
    hdbg.dassert(is_symmetric(cov))
    dim = estimated_cov.shape[0]
    hdbg.dassert_lt(0, dim)
    hdbg.dassert_eq(dim, cov.shape[0])
    #
    est_inv = np.linalg.inv(estimated_cov)
    #
    term1_num = np.trace(est_inv @ cov @ est_inv) / dim
    term1_denom = np.square(np.trace(est_inv) / dim)
    term2 = -dim / np.trace(est_inv)
    #
    loss = term1_num / term1_denom + term2
    return loss


# TODO(Paul): Check the validity of this implementation near the critical
#  sampling threshold. It seems to start breaking down around q > 0.75 or 0.8.
# TODO(Paul): Consider profiling if the dimension of the space goes from ~100
#  to ~1000.
def compute_analytical_nonlinear_shrinkage_estimator(
    sample_covariance_matrix: pd.DataFrame,
    num_observations: int,
) -> pd.DataFrame:
    """
    Implement the "analytical nonlinear shrinkage" estimator.

    See Ledoit and Wolf, The Annals of Statistics, 2020.
    https://doi.org/10.1214/19-AOS1921

    :param sample_covariance_matrix: the sample covariance matrix to "shrink"
    :param num_observations: the number of observations (samples) used to
        generate `sample_covariance_matrix`
    :return: estimated (shrunk) covariance matrix
    """
    # Create a short alias.
    scm = sample_covariance_matrix
    hdbg.dassert(is_symmetric(scm))
    n = num_observations
    hdbg.dassert_lt(0, num_observations)
    # Compute spectral decomposition.
    u, singular_values, v_transpose = np.linalg.svd(scm)
    # Set global bandwidth.
    h_n = n ** (-1 / 3)
    # Set the locally adaptive bandwidth.
    h_n_j = singular_values * h_n
    # Estimate the spectral density.
    esd = [
        _estimate_spectral_density(x, singular_values, h_n_j)
        for x in singular_values
    ]
    esd = np.asarray(esd)
    # Estimate the Hilbert transform of the spectral density.
    ht = [
        _estimate_hilbert_transform(x, singular_values, h_n_j)
        for x in singular_values
    ]
    ht = np.asarray(ht)
    # Compute the asymptotically optimal nonlinear shrinkage.
    d_n = _compute_shrinkage_coefficients(
        singular_values, esd, ht, num_observations
    )
    # Construct the covariance matrix estimator.
    covariance_estimator = (u * d_n) @ v_transpose
    df = pd.DataFrame(covariance_estimator, index=scm.index, columns=scm.columns)
    # TODO: Perform some sanity checks and return.
    return df


def compute_epanechnikov_kernel(
    real: float,
) -> float:
    """
    Implements the Epanechnikov kernel.

    :param real: a real number
    :return: the value of the kernel at `real`
    """
    sq = real**2
    scale = 3 / (4 * np.sqrt(5))
    val = scale * max(0, 1 - sq / 5)
    return val


def compute_epanechnikov_hilbert_transform(
    real: float,
) -> float:
    """
    Implements the Hilbert transform of the Epanechnikov kernel.

    :param real: a real number
    :return: the value of the kernel at `real`
    """
    term1 = -3 * real / (10 * np.pi)
    if np.abs(real) == np.sqrt(5):
        term2 = 0
    else:
        sq = real**2
        scale = 3 / (4 * np.sqrt(5) * np.pi)
        log = np.abs((np.sqrt(5) - real) / (np.sqrt(5) + real))
        term2 = scale * (1 - sq / 5) * np.log(log)
    return term1 + term2


def _compute_shrinkage_coefficients(
    singular_values: np.ndarray,
    spectral_density: np.ndarray,
    hilbert_transform: np.ndarray,
    num_observations: int,
) -> np.ndarray:
    p = len(singular_values)
    frac = p / num_observations
    term1 = np.square(np.pi * frac * singular_values * spectral_density)
    term2 = np.square(
        1 - frac - np.pi * frac * singular_values * hilbert_transform
    )
    d_n = singular_values / (term1 + term2)
    return d_n


def _estimate_spectral_density(
    x: float,
    singular_values: np.ndarray,
    local_bandwidths: np.ndarray,
) -> float:
    vec_arg = (x - singular_values) / local_bandwidths
    vals = np.vectorize(compute_epanechnikov_kernel)(vec_arg)
    vals = vals / local_bandwidths
    return vals.mean()


def _estimate_hilbert_transform(
    x: float,
    singular_values: np.ndarray,
    local_bandwidths: np.ndarray,
) -> float:
    vec_arg = (x - singular_values) / local_bandwidths
    vals = np.vectorize(compute_epanechnikov_hilbert_transform)(vec_arg)
    vals = vals / local_bandwidths
    return vals.mean()
