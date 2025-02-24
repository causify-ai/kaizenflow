"""
Import as:

import core.signal_processing.cross_correlation as csprcrco
"""

import collections
import logging
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def correlate_with_lag(
    df: pd.DataFrame, lag: Union[int, List[int]]
) -> pd.DataFrame:
    """
    Combine cols of `df` with their lags and compute the correlation matrix.

    :param df: dataframe of numeric values
    :param lag: number of lags to apply or list of number of lags
    :return: correlation matrix with `(1 + len(lag)) * df.columns` columns
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    if isinstance(lag, int):
        lag = [lag]
    elif isinstance(lag, list):
        pass
    else:
        raise ValueError("Invalid `type(lag)`='%s'" % type(lag))
    lagged_dfs = [df]
    for lag_curr in lag:
        df_lagged = df.shift(lag_curr)
        df_lagged.columns = df_lagged.columns.astype(str) + f"_lag_{lag_curr}"
        lagged_dfs.append(df_lagged)
    merged_df = pd.concat(lagged_dfs, axis=1)
    return merged_df.corr()


def correlate_with_lagged_cumsum(
    df: pd.DataFrame,
    lag: int,
    y_vars: List[str],
    x_vars: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Compute correlation matrix of `df` cols and lagged cumulative sums.

    The flow is the following:
        - Compute cumulative sums of `y_vars` columns for `num_steps = lag`
        - Lag them so that `x_t` aligns with `y_{t+1} + ... + y{t+lag}`
        - Compute correlation of `df` columns (other than `y_vars`) and the
          lagged cumulative sums of `y_vars`

    This function can be applied to compute correlations between predictors and
    cumulative log returns.

    :param df: dataframe of numeric values
    :param lag: number of time points to shift the data by. Number of steps to
        compute rolling sum is `lag` too.
    :param y_vars: names of columns for which to compute cumulative sum
    :param x_vars: names of columns to correlate the `y_vars` with. If `None`,
        defaults to all columns except `y_vars`
    :return: correlation matrix of `(len(x_vars), len(y_vars))` shape
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_isinstance(y_vars, list)
    x_vars = x_vars or df.columns.difference(y_vars).tolist()
    hdbg.dassert_isinstance(x_vars, list)
    hdbg.dassert_lte(
        1,
        len(x_vars),
        "There are no columns to compute the correlation of cumulative "
        "returns with. ",
    )
    df = df[x_vars + y_vars].copy()
    cumsum_df = _compute_lagged_cumsum(df, lag, y_vars=y_vars)
    corr_df = cumsum_df.corr()
    y_cumsum_vars = cumsum_df.columns.difference(x_vars)
    return corr_df.loc[x_vars, y_cumsum_vars]


def _compute_lagged_cumsum(
    df: pd.DataFrame,
    lag: int,
    y_vars: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Compute lagged cumulative sum for selected columns.

    Align `x_t` with `y_{t+1} + ... + y{t+lag}`.

    :param df: dataframe of numeric values
    :param lag: number of time points to shift the data by. Number of steps to
        compute rolling sum is `lag`
    :param y_vars: names of columns for which to compute cumulative sum. If
        `None`, compute for all columns
    :return: dataframe with lagged cumulative sum columns
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    y_vars = y_vars or df.columns.tolist()
    hdbg.dassert_isinstance(y_vars, list)
    x_vars = df.columns.difference(y_vars)
    y = df[y_vars].copy()
    x = df[x_vars].copy()
    # Compute cumulative sum.
    y_cumsum = y.rolling(window=lag).sum()
    y_cumsum.rename(columns=lambda x: f"{x}_cumsum_{lag}", inplace=True)
    # Let's lag `y` so that `x_t` aligns with `y_{t+1} + ... + y{t+lag}`.
    y_cumsum_lagged = y_cumsum.shift(-lag)
    y_cumsum_lagged.rename(columns=lambda z: f"{z}_lag_{lag}", inplace=True)
    #
    merged_df = x.merge(y_cumsum_lagged, left_index=True, right_index=True)
    return merged_df


def compute_inverse(
    df: pd.DataFrame,
    p_moment: Optional[Any] = None,
    info: Optional[collections.OrderedDict] = None,
) -> pd.DataFrame:
    """
    Calculate an inverse matrix.

    :param df: matrix to invert
    :param p_moment: order of the matrix norm as in `np.linalg.cond`
    :param info: dict with info to add the condition number to
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_eq(
        df.shape[0], df.shape[1], "Only square matrices are invertible."
    )
    hdbg.dassert(
        df.apply(lambda s: pd.to_numeric(s, errors="coerce").notnull()).all(
            axis=None
        ),
        "The matrix is not numeric.",
    )
    hdbg.dassert_ne(np.linalg.det(df), 0, "The matrix is non-invertible.")
    if info is not None:
        info["condition_number"] = np.linalg.cond(df, p_moment)
    return pd.DataFrame(np.linalg.inv(df), df.columns, df.index)


def compute_pseudoinverse(
    df: pd.DataFrame,
    rcond: Optional[float] = 1e-15,
    hermitian: Optional[bool] = False,
    p_moment: Optional[Any] = None,
    info: Optional[collections.OrderedDict] = None,
) -> pd.DataFrame:
    """
    Calculate the Moore-Penrose generalized inverse of a matrix.

    :param df: matrix to pseudo-invert
    :param rcond: cutoff for small singular values as in `np.linalg.pinv`
    :param hermitian: if True, `df` is assumed to be Hermitian
    :param p_moment: order of the matrix norm as in `np.linalg.cond`
    :param info: dict with info to add the condition number to
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert(
        df.apply(lambda s: pd.to_numeric(s, errors="coerce").notnull()).all(
            axis=None
        ),
        "The matrix is not numeric.",
    )
    if info is not None:
        info["condition_number"] = np.linalg.cond(df, p_moment)
    # Reverse `columns` and `index` because this is a pseudoinverse.
    return pd.DataFrame(
        np.linalg.pinv(df, rcond=rcond, hermitian=hermitian), df.columns, df.index
    )


def reduce_rank(
    df: pd.DataFrame,
    reduced_rank: int,
    invert: bool = False,
    conserve_shatten_norm: Optional[float] = None,
) -> pd.DataFrame:
    """
    Reduce the rank of a matrix using the SVD.

    :param df: numeric matrix as a dataframe
    :param reduced_rank: desired rank
    :param invert: invert the rank-reduced matrix (using SVD)
    :param conserve_shatten_norm: preserve the Schatten p-norm in the rank
        reduction
    :return: projection of df to first `reduced_rank` principal directions
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    max_dim = min(df.shape)
    hdbg.dassert_lte(0, reduced_rank)
    hdbg.dassert_lte(reduced_rank, max_dim)
    u, singular_values, v_transpose = np.linalg.svd(df, full_matrices=False)
    leading_singular_values = singular_values[:reduced_rank]
    if conserve_shatten_norm is not None:
        # Use an alias for brevity.
        ord = conserve_shatten_norm
        hdbg.dassert_lte(1, ord)
        p_norm = np.linalg.norm(singular_values, ord)
        multiplier = p_norm / np.linalg.norm(leading_singular_values, ord)
    else:
        multiplier = 1
    adjusted_leading_singular_values = leading_singular_values * multiplier
    if invert:
        adjusted_leading_singular_values = 1 / adjusted_leading_singular_values
    adjusted_singular_values = np.concatenate(
        (adjusted_leading_singular_values, np.zeros(max_dim - reduced_rank))
    )
    rank_reduced_matrix = np.matmul(
        u, np.matmul(np.diag(adjusted_singular_values), v_transpose)
    )
    rank_reduced_df = pd.DataFrame(
        rank_reduced_matrix, index=df.index, columns=df.columns
    )
    return rank_reduced_df


def compute_cross_correlation(
    df: pd.DataFrame,
    x_cols: List[Union[int, str]],
    y_col: Union[int, str],
    lags: List[int],
) -> pd.DataFrame:
    """
    Compute cross-correlations between `x_cols` and `y_col` at `lags`.

    :param df: data dataframe
    :param x_cols: x variable columns
    :param y_col: y variable column
    :param lags: list of integer lags to shift `x_cols` by
    :return: dataframe of cross correlation at lags
    """
    hdbg.dassert(not df.empty, msg="Dataframe must be nonempty")
    hdbg.dassert_isinstance(x_cols, list)
    hdbg.dassert_is_subset(x_cols, df.columns)
    hdbg.dassert_isinstance(y_col, (int, str))
    hdbg.dassert_in(y_col, df.columns)
    hdbg.dassert_isinstance(lags, list)
    # Drop rows with no y value.
    _LOG.debug("y_col=`%s` count=%i", y_col, df[y_col].count())
    df = df.dropna(subset=[y_col])
    x_vars = df[x_cols]
    y_var = df[y_col]
    correlations = []
    for lag in lags:
        corr = x_vars.shift(lag).apply(lambda x: x.corr(y_var))
        corr.name = lag
        correlations.append(corr)
    corr_df = pd.concat(correlations, axis=1)
    return corr_df.transpose()
