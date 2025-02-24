"""
Import as:

import optimizer.utils as oputils
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# TODO(Paul): Write a function to check for PSD.
# TODO(Paul): Rename to `optimizer_utils.py`.


def is_symmetric(matrix: pd.DataFrame, **kwargs) -> bool:
    hdbg.dassert_isinstance(matrix, pd.DataFrame)
    m, n = matrix.shape
    hdbg.dassert_eq(m, n)
    return np.allclose(matrix, matrix.T, **kwargs)


def compute_tangency_portfolio(
    mu_rows: pd.DataFrame,
    *,
    covariance: Optional[pd.DataFrame] = None,
    precision: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Compute the Markowitz tangency portfolio (up to a scale factor).

    The computation performed is `precision @ mu_rows`.

    Notes:
    1. The volatility may change substantially from row to row. For a fixed
       target volatility, execute `rescale_to_target_volatility()` on the
       result of this function.
    2. The GMV may change from row to row. For a fixed target GMV, execute
       `rescale_to_target_gmv()` on the result of this function.
    3. The expected SR for each row is given by
        `compute_quadratic_form(mu_rows, precision)`
        where `precision` is the inverse of the covariance matrix

    :param mu_rows: mean excess returns (along rows)
    :param covariance: covariance matrix
    :param precision: precision matrix, i.e., the inverse of the covariance
        matrix
    :return: rows of weights
    """
    hdbg.dassert_isinstance(mu_rows, pd.DataFrame)
    if covariance is not None:
        hdbg.dassert(
            precision is None,
            "Exactly one of `covariance` and `precision` must be not `None`.",
        )
        hdbg.dassert(is_symmetric(covariance))
        pseudoinverse = np.linalg.pinv(covariance, hermitian=True)
        # Reverse `columns` and `index` because this is a pseudoinverse.
        precision = pd.DataFrame(
            pseudoinverse, covariance.columns, covariance.index
        )
    else:
        hdbg.dassert(
            precision is not None,
            "Exactly one of `covariance` and `precision` must be not `None`.",
        )
        hdbg.dassert(is_symmetric(precision))
    weights = mu_rows.dot(precision)
    return weights


def compute_quadratic_form(
    row_vectors: pd.DataFrame, symmetric_matrix: pd.DataFrame
) -> pd.DataFrame:
    """
    Given a fixed real symmetric_matrix matrix `A`, compute `v.T A v` row-wise.

    :param row_vectors: numerical dataframe
    :param symmetric_matrix: a real symmetric matrix (aligned with columns of
        `row_vectors`)
    :return: quadratic form evaluated on each row vector
    """
    hdbg.dassert(is_symmetric(symmetric_matrix))
    # For each row `v` of `df`, compute `v.T * symmetric_matrix * v`.
    quadratic = row_vectors.multiply(row_vectors.dot(symmetric_matrix)).sum(
        min_count=1, axis=1
    )
    return quadratic


def neutralize(row_vectors: pd.DataFrame) -> pd.DataFrame:
    """
    Orthogonally project row vectors onto subspace orthogonal to all ones.

    (In other words, we demean each row).

    If the rows of `row_vectors` represent dollar positions, then this operation
    will dollar neutralize each row.

    :param row_vectors: numerical dataframe
    :return: neutralized `row_vectors` (i.e., demeaned)
    """
    mean = row_vectors.mean(axis=1)
    projection = row_vectors.subtract(mean, axis=0)
    return projection


def rescale_to_target_volatility(
    weight_rows: pd.DataFrame,
    covariance: pd.DataFrame,
    target_volatility: float,
) -> pd.DataFrame:
    """
    Rescale so that `(v.T A v)^0.5` is `target_volatility` for each element.

    :param weight_rows: weights organized in rows
    :param covariance: a covariance or correlation matrix
    :param target_volatility: target volatilty in units compatible with units
        of weights
    :return: `weight_rows` adjusted row-wise
    """
    hdbg.dassert_lt(0, target_volatility)
    volatility = np.sqrt(compute_quadratic_form(weight_rows, covariance))
    adjustment_factor = target_volatility / volatility
    rescaled_weights = weight_rows.multiply(adjustment_factor, axis=0)
    return rescaled_weights


def rescale_to_target_gmv(
    weight_rows: pd.DataFrame,
    target_gmv: float,
) -> pd.DataFrame:
    """
    Rescale so that l1 norm of each row is equal to `target_gmv`.

    :param weight_rows: weights organized in rows
    :param target_gmv: total (long + short) gmv
    :return: `weight_rows` adjusted row-wise
    """
    hdbg.dassert_lt(0, target_gmv)
    # Take absolute values to count both longs and shorts toward total gmv.
    total_gmv = weight_rows.abs().sum(min_count=1, axis=1)
    adjustment_factor = target_gmv / total_gmv
    rescaled_weights = weight_rows.multiply(adjustment_factor, axis=0)
    return rescaled_weights
