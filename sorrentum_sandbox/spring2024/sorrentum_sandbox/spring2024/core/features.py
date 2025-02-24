"""
Import as:

import core.features as cofeatur
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import scipy as sp

import core.signal_processing as csigproc
import core.statistics as costatis
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)
COL = Union[str, int]


# TODO(gp): Where is it used?


def get_lagged_feature_names(
    y_var: str, delay_lag: int, num_lags: int
) -> Tuple[List[int], List[str]]:
    hdbg.dassert(
        y_var.endswith("_0"),
        "y_var='%s' is not a valid name to generate lagging variables",
        y_var,
    )
    if delay_lag < 1:
        _LOG.warning(
            "Using anticausal features since delay_lag=%d < 1. This "
            "could be lead to future peeking",
            delay_lag,
        )
    hdbg.dassert_lte(1, num_lags)
    #
    x_var_shifts = list(range(1 + delay_lag, 1 + delay_lag + num_lags))
    x_vars = []
    for i in x_var_shifts:
        x_var = y_var.replace("_0", "_%d" % i)
        x_vars.append(x_var)
    hdbg.dassert_eq(len(x_vars), len(x_var_shifts))
    return x_var_shifts, x_vars


def compute_lagged_features(
    df: pd.DataFrame, y_var: str, delay_lag: int, num_lags: int
) -> Tuple[pd.DataFrame, collections.OrderedDict]:
    """
    Compute features by adding lags of `y_var` in `df`. The operation is
    performed in-place.

    :return: transformed df and info about the transformation.
    """
    info = collections.OrderedDict()
    hdbg.dassert_in(y_var, df.columns)
    _LOG.debug("df.shape=%s", df.shape)
    #
    _LOG.debug("y_var='%s'", y_var)
    info["y_var"] = y_var
    x_var_shifts, x_vars = get_lagged_feature_names(y_var, delay_lag, num_lags)
    _LOG.debug("x_vars=%s", x_vars)
    info["x_vars"] = x_vars
    for i, num_shifts in enumerate(x_var_shifts):
        x_var = x_vars[i]
        _LOG.debug("Computing var=%s", x_var)
        df[x_var] = df[y_var].shift(num_shifts)
    # TODO(gp): Add dropna stats using exp.dropna().
    info["before_df.shape"] = df.shape
    df = df.dropna()
    _LOG.debug("df.shape=%s", df.shape)
    info["after_df.shape"] = df.shape
    return df, info


# TODO(Paul): Clean this up. The interface has become a bit awkward.
def compute_lagged_columns(
    df: pd.DataFrame,
    lag_delay: int,
    num_lags: int,
    *,
    first_lag: int = 1,
    separator: str = "_",
) -> pd.DataFrame:
    """
    Compute lags of each column in df.
    """
    out_cols = []
    hdbg.dassert_isinstance(df, pd.DataFrame)
    for col in df.columns:
        out_col = compute_lags(df[col], lag_delay, num_lags, first_lag)
        out_col.rename(columns=lambda x: str(col) + separator + x, inplace=True)
        out_cols.append(out_col)
    return pd.concat(out_cols, axis=1)


def compute_lags(
    srs: pd.Series, lag_delay: int, num_lags: int, first_lag: int
) -> pd.DataFrame:
    """
    Compute `num_lags` lags of `srs` starting with a delay of `lag_delay`.
    """
    if lag_delay < 0:
        _LOG.warning(
            "Using anticausal features since lag_delay=%d < 0. This "
            "could lead to future peeking.",
            lag_delay,
        )
    hdbg.dassert_lte(1, num_lags)
    #
    shifts = list(range(first_lag + lag_delay, first_lag + lag_delay + num_lags))
    out_cols = []
    hdbg.dassert_isinstance(srs, pd.Series)
    for num_shifts in shifts:
        out_col = srs.shift(num_shifts)
        out_col.name = "lag%i" % num_shifts
        out_cols.append(out_col)
    return pd.concat(out_cols, axis=1)


def combine_columns(
    df: pd.DataFrame,
    term1_col: Union[str, int],
    term2_col: Union[str, int],
    out_col: Union[str, int],
    operation: str,
    arithmetic_kwargs: Optional[Dict[str, Any]] = None,
    term1_delay: Optional[int] = 0,
    term2_delay: Optional[int] = 0,
    replace_inf_with_nan_post_div: bool = True,
) -> pd.DataFrame:
    """
    Apply an arithmetic operation to two columns.

    :param df: input data
    :param term1_col: name of col for `term1` in `term1.operation(term2)`
    :param term2_col: name of col for `term2`
    :param out_col: name of dataframe column with result
    :param operation: "add", "sub", "mul", or "div"
    :param arithmetic_kwargs: kwargs for `operation()`
    :param term1_delay: number of shifts to preapply to term1
    :param term2_delay: number of shifts to preapply to term2
    :param replace_inf_with_nan_post_div: if `operation` == "div", replace
        infs with NaNs (as the division may introduce infs)
    :return: 1-column dataframe with result of binary operation
    """
    hdbg.dassert_in(term1_col, df.columns.to_list())
    hdbg.dassert_in(term2_col, df.columns.to_list())
    hdbg.dassert_not_in(out_col, df.columns.to_list())
    hdbg.dassert_in(operation, ["add", "sub", "mul", "div"])
    arithmetic_kwargs = arithmetic_kwargs or {}
    #
    term1 = df[term1_col].shift(term1_delay)
    term2 = df[term2_col].shift(term2_delay)
    result = getattr(term1, operation)(term2, **arithmetic_kwargs)
    result.name = out_col
    if operation == "div" and replace_inf_with_nan_post_div:
        result = result.replace([-np.inf, np.inf], np.nan)
    #
    return result.to_frame()


def perform_col_arithmetic(
    df: pd.DataFrame,
    col_groups: List[Tuple[COL, COL, str, COL]],
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Perform simple arithmetic operations on pairs of columns.

    :param df: dataframe with at least two columns (not necessarily
        unique)
    :param col_groups: a tuple of the following form:
        `(col1_name, col1_name, operation, out_col_name)`.
    :param join_output_with_input: whether to only return the requested columns
        or to join the requested columns to the input dataframe
    """
    if not col_groups:
        _LOG.debug("No operations requested.")
        return df
    results = []
    for col1, col2, operation, out_col_name in col_groups:
        hdbg.dassert_in(
            operation,
            ["multiply", "divide", "add", "subtract"],
            "Operation not supported.",
        )
        hdbg.dassert_in(col1, df.columns.to_list())
        hdbg.dassert_in(col2, df.columns.to_list())
        term1 = df[col1]
        term2 = df[col2]
        result = getattr(term1, operation)(term2)
        result = result.rename(out_col_name)
        results.append(result)
    out_df = pd.concat(results, axis=1)
    if join_output_with_input:
        out_df = out_df.merge(df, left_index=True, right_index=True, how="outer")
        hdbg.dassert(not out_df.columns.has_duplicates)
    hdbg.dassert(not out_df.columns.has_duplicates)
    return out_df


def cross_feature_pairs(
    df: pd.DataFrame,
    feature_groups: List[Tuple[COL, COL, List[COL], str]],
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Perform feature crosses of multiple pairs of columns.

    This function wraps `cross_feature_pair()`.

    :param df: dataframe with at least two feature columns (not necessarily
        unique)
    :param feature_groups: a tuple of the following form:
        `(feature1_col, feature2_col, requested_cols, prefix)`.
        The string `prefix` is prepended to the column names of
        `requested_cols` in the output.
    :param join_output_with_input: whether to only return the requested columns
        or to join the requested columns to the input dataframe
    """
    results = []
    for ftr1, ftr2, requested_cols, prefix in feature_groups:
        ftr_df = cross_feature_pair(df, ftr1, ftr2, requested_cols)
        ftr_df = ftr_df.rename(columns=lambda x: prefix + "." + str(x))
        results.append(ftr_df)
    out_df = pd.concat(results, axis=1)
    if join_output_with_input:
        out_df = out_df.merge(df, left_index=True, right_index=True, how="outer")
        hdbg.dassert(not out_df.columns.has_duplicates)
    hdbg.dassert(not out_df.columns.has_duplicates)
    return out_df


def cross_feature_pair(
    df: pd.DataFrame,
    feature1_col: COL,
    feature2_col: COL,
    requested_cols: Optional[List[COL]] = None,
    compression_scale: float = 4,
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Perform feature cross of two feature columns.

    - Features may be order-dependent (e.g., difference-type features).
    - Most feature crosses available in this function are neither linear nor
      bilinear
    - Some features are invariant with respect to uniform rescalings (e.g.,
      "normalized_difference"), and others are not
    - The compression-type features may benefit from pre-scaling
    - Some features require non-negative or strictly positive values

    :param df: dataframe with at least two feature columns (not necessarily
        unique)
    :param feature1_col: first feature column
    :param feature2_col: second feature column
    :param requested_cols: the requested output columns; `None` returns all
        available
    :param compression_scale: rescaling factor to use in "compression"
        features. A larger number means less compression. The maximum of the
        absolute value of the compressed feature cross is less than or equal to
         `compression_scale`.
    :param join_output_with_input: whether to only return the requested columns
        or to join the requested columns to the input dataframe
    """
    hdbg.dassert_in(feature1_col, df.columns.to_list())
    hdbg.dassert_in(feature2_col, df.columns.to_list())
    supported_cols = [
        #
        "difference",
        "compressed_difference",
        "normalized_difference",
        "normalized_difference_to_gaussian",
        "difference_of_logs",
        "compressed_difference_of_logs",
        #
        "mean",
        "compressed_mean",
        #
        "product",
        "compressed_product",
        #
        "geometric_mean",
        "harmonic_mean",
        "mean_of_logs",
    ]
    requested_cols = requested_cols or supported_cols
    hdbg.dassert_is_subset(
        requested_cols,
        supported_cols,
        "The available columns to request are %s",
        supported_cols,
    )
    hdbg.dassert(requested_cols)
    requested_cols = set(requested_cols)
    # TODO(*): Check requested columns
    # Extract feature values as series.
    ftr1 = df[feature1_col]
    ftr2 = df[feature2_col]
    # Calculate feature crosses.
    crosses = []
    #
    name = "difference"
    if name in requested_cols:
        # Optimized for variance-1 features.
        cross = ((ftr1 - ftr2) / np.sqrt(2)).rename(name)
        crosses.append(cross)
    #
    name = "compressed_difference"
    if name in requested_cols:
        # Optimized for variance-1 features.
        cross = csigproc.compress_tails(
            (ftr1 - ftr2) / np.sqrt(2), scale=compression_scale
        )
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "normalized_difference"
    if name in requested_cols:
        # A scale invariant cross.
        product = ftr1 * ftr2
        if (product < 0).any():
            _log_opposite_sign_warning(feature1_col, feature2_col, name)
        cross = ((ftr1 - ftr2) / (np.abs(ftr1) + np.abs(ftr2))).rename(name)
        crosses.append(cross)
    #
    name = "normalized_difference_to_gaussian"
    if name in requested_cols:
        hdbg.dassert(not (ftr1 < 0).any())
        hdbg.dassert(not (ftr2 < 0).any())
        frac = ftr1 / (ftr1 + ftr2)
        vals = sp.stats.norm.ppf(frac)
        cross = pd.Series(vals, df.index, name=name).clip(
            lower=-compression_scale, upper=compression_scale
        )
        crosses.append(cross)
    #
    name = "difference_of_logs"
    if name in requested_cols:
        # A scale invariant cross.
        quotient = ftr1 / ftr2
        if (quotient < 0).any():
            _log_opposite_sign_warning(feature1_col, feature2_col, name)
        cross = np.log(ftr1.abs()) - np.log(ftr2.abs())
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "compressed_difference_of_logs"
    if name in requested_cols:
        # Optimized for variance-1 difference of logs.
        quotient = ftr1 / ftr2
        if (quotient < 0).any():
            _log_opposite_sign_warning(feature1_col, feature2_col, name)
        cross = np.log(ftr1.abs()) - np.log(ftr2.abs())
        cross = csigproc.compress_tails(cross, scale=compression_scale)
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "mean"
    if name in requested_cols:
        # Optimized for variance-1 features.
        cross = ((ftr1 + ftr2) / np.sqrt(2)).rename(name)
        crosses.append(cross)
    #
    name = "compressed_mean"
    if name in requested_cols:
        # Optimized for variance-1 features.
        cross = csigproc.compress_tails(
            (ftr1 + ftr2) / np.sqrt(2), scale=compression_scale
        )
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "product"
    if name in requested_cols:
        cross = (ftr1 * ftr2).rename(name)
        crosses.append(cross)
    #
    name = "compressed_product"
    if name in requested_cols:
        # Optimized for variance-1 features.
        cross = csigproc.compress_tails(ftr1 * ftr2, scale=compression_scale)
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "geometric_mean"
    if name in requested_cols:
        if (ftr1 < 0).any() or (ftr2 < 0).any():
            _log_negative_value_warning(feature1_col, feature2_col, name)
        product = ftr1 * ftr2
        signs = csigproc.sign_normalize(product)
        cross = np.sqrt(product.abs()) * signs
        cross = cross.rename(name)
        crosses.append(cross)
    #
    name = "harmonic_mean"
    if name in requested_cols:
        if (ftr1 < 0).any() or (ftr2 < 0).any():
            _log_negative_value_warning(feature1_col, feature2_col, name)
        cross = ((2 * ftr1 * ftr2) / (ftr1 + ftr2)).rename(name)
        crosses.append(cross)
    #
    name = "mean_of_logs"
    if name in requested_cols:
        # Equivalent to the log of the geometric mean.
        product = ftr1 * ftr2
        if (product < 0).any():
            _log_opposite_sign_warning(feature1_col, feature2_col, name)
        cross = ((np.log(ftr1.abs()) + np.log(ftr2.abs())) / 2).rename(name)
        crosses.append(cross)
    out_df = pd.concat(crosses, axis=1)
    if join_output_with_input:
        out_df = out_df.merge(df, left_index=True, right_index=True, how="outer")
        hdbg.dassert(not out_df.columns.has_duplicates)
    return out_df


def _log_opposite_sign_warning(
    feature1_col: str,
    feature2_col: str,
    feature_cross: str,
) -> None:
    msg = "Calculating feature cross `%s`: features `%s` and `%s` have entries with opposite signs."
    _LOG.warning(msg, feature_cross, feature1_col, feature2_col)


def _log_negative_value_warning(
    feature1_col: str,
    feature2_col: str,
    feature_cross: str,
) -> None:
    msg = "Calculating feature cross `%s`: negative values detected in at least one of feature `%s` and `%s`."
    _LOG.warning(msg, feature_cross, feature1_col, feature2_col)


def compute_normalized_statistical_leverage_scores(
    df: pd.DataFrame,
    max_dim: Optional[int] = None,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> pd.DataFrame:
    """
    Compute normalized statistical leverage scores as in Mahoney and Drineas.

    Implements a key part of the "ColumnSelect" algorithm used in Mahoney and
    Drineas' CUR matrix decomposition algorithm
    (`www.pnas.org/cgi/doi/10.1073/pnas.0803205106`).

    :param df: a generic matrix
    :param max_dim: maximum number of dimensions for which to perform the
        calculation. `None` defaults to the number of columns of `df`.
    :param demean_cols: as in `_normalize_df()`
    :param normalize_cols: as in `_normalize_df()`
    :return: dataframe of normalized statistical leverage scores. Columns
        are as in `df`, and rows indicate the number of principal dimensions
        (which run from 1 up to and including `max_dim`).
    """
    n_cols = df.shape[1]
    max_dim = max_dim or n_cols
    hdbg.dassert_lt(0, max_dim)
    hdbg.dassert_lte(max_dim, n_cols)
    # Preprocess `df`.
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Compute SVD.
    _, _, v_transpose = np.linalg.svd(df, full_matrices=False)
    # Compute leverage scores.
    all_scores = []
    for curr_dim in range(1, max_dim + 1):
        # Project V^T onto the subspace spanned by the top `curr_dim` principal vectors.
        proj = np.concatenate((np.ones(curr_dim), np.zeros(n_cols - curr_dim)))
        v_transpose_proj = np.matmul(np.diag(proj), v_transpose)
        # Compute normalized statistical leverage scores as in CUR ColumnSelect.
        scores = np.sum(np.square(v_transpose_proj), axis=0) / curr_dim
        # Convert to a Series.
        scores = pd.Series(scores, index=df.columns, name=curr_dim)
        all_scores.append(scores)
    result = pd.concat(all_scores, axis=1).transpose()
    result.index.name = "proj_dim"
    return result


def compute_normalized_principal_loadings(
    df: pd.DataFrame,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> pd.DataFrame:
    """
    Represent cols of `df` in terms of the SVD `U` basis, normalized by nrows.

    Column `k` of the output provides the coefficients required to reconstruct
    column `k` of `df` given the columns of `U` of the SVD decomposition of
    `df` and the number of non-NaN rows of `df`.

    If each column of `df` has entries that are mean zero and variance one in
    expectation, then the normalized loadings may be interpreted as
    correlations.

    :param df: dataframe with features represented by columns, observation
        times by rows
    :param demean_cols: as in `_normalize_df()`
    :param normalize_cols: as in `_normalize_df()`
    :return: dataframe of loadings of the feature columns on the principal
        directions (e.g., columns of `U`), normalized by the square root of
        the number of non-NaN rows of `df`
    """
    # Preprocess `df`.
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Compute SVD.
    _, singular_values, v_transpose = np.linalg.svd(df, full_matrices=False)
    # Compute loadings.
    prod = np.matmul(np.diag(singular_values), v_transpose)
    # Normalize by number of rows.
    n_rows = df.shape[0]
    corr = prod / np.sqrt(n_rows)
    # Label the index.
    index = pd.RangeIndex(
        start=1, stop=singular_values.size + 1, name="principal_direction"
    )
    result = pd.DataFrame(corr, columns=df.columns, index=index)
    return result


def compare_subspaces(
    subspace1: pd.DataFrame,
    subspace2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the canonical correlations and angles between subspaces.

    :param subspace1: a subspace represented by a dataframe of orthonormal columns
    :param subspace2: like `subspace1`, with identical number of columns
    :return: dataframe of canonical correlations and principal angles per
        principal direction
    """
    hdbg.dassert_eq(subspace1.shape, subspace2.shape)
    # TODO(Paul): Check orthonormality of columns.
    # Compute the matrix product `subspace1.T * ut2`.
    prod = np.matmul(subspace1.values.transpose(), subspace2.values)
    _, singular_values, _ = np.linalg.svd(prod, full_matrices=False)
    # Due to numerical approximation, some singular values may be less than -1
    # or greater than +1, though theoretically they must lie in this range.
    # We enforce this here so that `np.arccos` does not raise.
    singular_values = np.clip(singular_values, -1, 1)
    # The singular values of `prod` are the canonical correlations.
    canonical_corr = pd.Series(singular_values, name="canonical_corr")
    # The arccosines of the canonical correlations are the principal angles.
    principal_angles = np.arccos(singular_values)
    principal_angles = pd.Series(principal_angles, name="principal_angle")
    df = pd.concat([canonical_corr, principal_angles], axis=1)
    index = pd.RangeIndex(
        start=1, stop=singular_values.size + 1, name="singular_value"
    )
    df.index = index
    return df


def evaluate_col_selection(
    df: pd.DataFrame,
    cols: list,
    eff_rank_alpha: float = 1.0,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> pd.Series:
    """
    Compute various quality stats for features `cols`.
    """
    # Perform column and dimension sanity checks.
    hdbg.dassert(cols)
    hdbg.dassert_no_duplicates(cols)
    hdbg.dassert_is_subset(cols, df.columns.to_list())
    dim = len(cols)
    hdbg.dassert_lte(dim, df.shape[0])
    # Preprocess `df`
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Compute the Grassmannian distance.
    u1 = _compute_principal_subspace(df, dim)
    u2 = _compute_principal_subspace(df[cols], dim)
    principal_angles = compare_subspaces(u1, u2)["principal_angle"]
    distance = np.sqrt(np.square(principal_angles).sum())
    # Compute projected volume.
    loadings = compute_normalized_principal_loadings(df)
    volume = np.linalg.det(loadings[cols].iloc[:dim])
    # Compute the effective ranks.
    df_eff_rank = compute_effective_rank(df, eff_rank_alpha)
    proj_cols_eff_rank = compute_effective_rank(df[cols], eff_rank_alpha)
    vals = {
        "distance": distance,
        "proj_volume": np.abs(volume),
        "df_eff_rank": df_eff_rank,
        "proj_cols_eff_rank": proj_cols_eff_rank,
    }
    result = pd.Series(vals)
    return result


def compute_effective_rank(
    df: pd.DataFrame,
    alpha: float,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> float:
    """
    Compute the effective rank for `df`.

    :param df: numerical data
    :param alpha: as in `cstat.compute_cardinality()`
    :param demean_cols: as in `_normalize_df()`
    :param normalize_cols: as in `_normalize_df()`
    :return: effective rank
    """
    # Preprocess `df`.
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Compute SVD.
    _, singular_values, _ = np.linalg.svd(df, full_matrices=False)
    # Compute effective rank
    sq_singular_values = pd.Series(np.square(singular_values))
    rank = costatis.compute_cardinality(sq_singular_values, alpha=alpha)
    return rank


def select_cols_by_greedy_grassmann(
    df: pd.DataFrame,
    n_cols: Optional[int] = None,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> list:
    """
    Select columns by greedily minimizing Grassmann distance.

    TODO(Paul): Allow fixing the comparison dimension and permit
    oversampling beyond that dimension.

    :param df: numerical feature dataframe
    :param n_cols: number of columns to select
    :param demean_cols: as in `_normalize_df()`
    :param normalize_cols: as in `_normalize_df()`
    :return: ordered list of selected columns
    """
    n_cols = n_cols or len(df.columns)
    hdbg.dassert_lte(n_cols, len(df.columns))
    # Preprocess `df`
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Greedily select columns until `n_cols` many have been selected.
    selected_cols = []
    while len(selected_cols) < n_cols:
        unselected_cols = set(df.columns).difference(set(selected_cols))
        distances = {}
        # Compute the Grassmann distance of df[selected_cols + [col]] for each
        # col in the set of unselected columns.
        dim = len(selected_cols) + 1
        u1 = _compute_principal_subspace(df, dim)
        for col in unselected_cols:
            # Compute the principal subspaces.
            u2 = _compute_principal_subspace(df[selected_cols + [col]], dim)
            principal_angles = compare_subspaces(u1, u2)["principal_angle"]
            # Compute the Grassmannian distance.
            distance = np.sqrt(np.square(principal_angles).sum())
            distances[col] = distance
        distances = pd.Series(distances)
        # Select the column that minimizes distance.
        selected_col = distances.idxmin()
        selected_cols.append(selected_col)
    return selected_cols


def select_cols_by_greedy_volume(
    df: pd.DataFrame,
    n_cols: Optional[int] = None,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> list:
    """
    Select columns by greedily maximizing volume of principal projections.

    At the k-th step (starting with k = 0), we have a collection of `k`
    selected columns. For each unselected column `col`, we consider the
    projection of the set of `k` selected columns and column `col` onto the
    first principal `k + 1` singular directions of `df`. The `col` that
    maximizes the volume of this projection is added to the set of selected
    columns. Selection continues until `n_cols` have been selected.

    :param df: numerical feature dataframe
    :param n_cols: number of columns to select
    :param demean_cols: as in `_normalize_df()`
    :param normalize_cols: as in `_normalize_df()`
    :return: ordered list of selected columns
    """
    n_cols = n_cols or len(df.columns)
    hdbg.dassert_lte(n_cols, len(df.columns))
    selected_cols = []
    # Preprocess `df`
    df = _drop_nans_for_svd(df)
    df = _normalize_df(df, demean_cols, normalize_cols)
    # Compute loadings.
    loadings = compute_normalized_principal_loadings(df)
    while len(selected_cols) < n_cols:
        unselected_cols = set(df.columns).difference(set(selected_cols))
        vals = {}
        for col in unselected_cols:
            col_set = selected_cols + [col]
            val = np.linalg.det(loadings[col_set].iloc[: len(col_set)])
            vals[col] = abs(val)
        vals = pd.Series(vals)
        # Select the column that maximizes the volume.
        selected_col = vals.idxmax()
        selected_cols.append(selected_col)
    return selected_cols


def combine_cols_instance1(
    df: pd.DataFrame,
    cols: Tuple[Union[int, str]],
) -> pd.DataFrame:
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_container_type(cols, container_type=tuple, elem_type=(int, str))
    hdbg.dassert_eq(3, len(cols))
    hdbg.dassert_is_subset(cols, df.columns)
    col_0 = df[cols[0]]
    col_1 = df[cols[1]]
    col_2 = df[cols[2]]
    const1 = 0.450158158
    do = (const1 * col_0 + const1 * col_1 + 0.5 * col_2).rename("do")
    const2 = 2.221441469
    la = (-2 * col_0 - 2 * col_1 + const2 * col_2).rename("la")
    const3 = 2.094395102
    const4 = 2.624934991
    const5 = 1.247775930
    ti = (
        -const3 * col_0 + const3 * col_1 + const4 * col_2.abs() + const5
    ).rename("ti")
    out_df = pd.concat([do, la, ti], axis=1)
    return out_df


def _drop_nans_for_svd(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Drop rows with NaNs to avoid a numpy raise.
    """
    total_num_rows = df.shape[0]
    df = df.dropna()
    num_rows = df.shape[0]
    frac_rows_dropped = (total_num_rows - num_rows) / total_num_rows
    _LOG.debug("Fraction of rows dropped = %0.2f", frac_rows_dropped)
    return df


def _normalize_df(
    df: pd.DataFrame,
    demean_cols: bool = False,
    normalize_cols: bool = False,
) -> pd.DataFrame:
    """
    Optionally demean and normalize columns of `df`.

    :param df: numerical matrix
    :param demean_cols: demean columns of `df` (independently)
    :param normalize_cols: normalized columns of `df` (independently)
    """
    if demean_cols:
        df = df - df.mean()
    if normalize_cols:
        df = df / df.std()
    return df


def _compute_principal_subspace(
    df: pd.DataFrame,
    dim: int,
) -> pd.DataFrame:
    """
    Compute the `dim`-dimensional principal subspace of `df`.

    :param df: numerical feature dataframe
    :param dim: number of hyperplane dimensions
    :return: the first `dim`-many principal orthonormal columns
    """
    hdbg.dassert_lt(0, dim)
    hdbg.dassert_lte(dim, len(df.columns))
    u, _, _ = np.linalg.svd(df, full_matrices=False)
    u_proj = u[:, :dim]
    return pd.DataFrame(u_proj, columns=range(1, dim + 1))
