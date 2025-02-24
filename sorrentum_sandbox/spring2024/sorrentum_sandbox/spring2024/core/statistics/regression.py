"""
Import as:

import core.statistics.regression as cstaregr
"""
import collections
import logging
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import scipy as sp
from tqdm.autonotebook import tqdm

import core.statistics.entropy as cstaentr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_regression_coefficients(
    df: pd.DataFrame,
    x_cols: List[Union[int, str]],
    y_col: Union[int, str],
    *,
    x_col_shift: int = 0,
    sample_weight_col: Optional[Union[int, str]] = None,
) -> pd.DataFrame:
    """
    Regresses `y_col` on each `x_col` independently.

    This function assumes (but does not check) that the x and y variables are
    centered.

    :param df: data dataframe
    :param x_cols: x variable columns
    :param y_col: y variable column
    :param sample_weight_col: optional nonnegative sample observation weights.
        If `None`, then equal weights are used. Weights do not need to be
        normalized.
    :return: dataframe of regression coefficients and related stats
    """
    hdbg.dassert(not df.empty, msg="Dataframe must be nonempty")
    hdbg.dassert_isinstance(x_cols, list)
    hdbg.dassert_is_subset(x_cols, df.columns)
    hdbg.dassert_isinstance(y_col, (int, str))
    hdbg.dassert_in(y_col, df.columns)
    # Drop rows with no y value.
    _LOG.debug("y_col=`%s` count=%i", y_col, df[y_col].count())
    df = df.dropna(subset=[y_col])
    # Extract x variables.
    x_vars = df[x_cols].shift(x_col_shift)
    if sample_weight_col is not None:
        hdbg.dassert_in(sample_weight_col, df.columns)
        x_vars_with_weights = df[x_cols + [sample_weight_col]].shift(x_col_shift)
        y_var_with_weights = df[[y_col] + [sample_weight_col]]
    else:
        x_vars_with_weights = df[x_cols].shift(x_col_shift)
        y_var_with_weights = df[[y_col]]
    x_var_coefficients = compute_centered_process_stats(
        x_vars_with_weights, sample_weight_col
    )
    weight_df = _get_weight_df(x_vars_with_weights, sample_weight_col)
    weight_sums = weight_df.sum(axis=0)
    weights = _get_weight_df(y_var_with_weights, sample_weight_col)[y_col]
    # Calculate sign correlation.
    sgn_rho = (
        x_vars.multiply(df[y_col], axis=0)
        .apply(np.sign)
        .multiply(weight_df, axis=0)
        .sum(axis=0)
        .divide(weight_sums)
        .rename("sgn_rho")
    )
    # Calculate covariance assuming x variables and y variable are centered.
    covariance = (
        x_vars.multiply(df[y_col], axis=0)
        .multiply(weight_df, axis=0)
        .sum(axis=0)
        .divide(weight_sums)
        .rename("covar")
    )
    # Calculate y variance assuming variable is centered.
    # NOTE: We calculate only one estimate of the variance of y, using all
    #     available data (regardless of whether a particular `x_col` is NaN or
    #     not). If samples of `x_cols` are not substantially aligned, then this
    #     may be undesirable.
    y_variance = df[y_col].pow(2).multiply(weights).sum() / weights.sum()
    _LOG.debug("y_col=`%s` variance=%f", y_col, y_variance)
    # Calculate correlation from covariances and variances.
    x_variance = x_var_coefficients["var"]
    rho = covariance.divide(np.sqrt(x_variance) * np.sqrt(y_variance)).rename(
        "rho"
    )
    # Calculate beta coefficients and associated statistics.
    beta = covariance.divide(x_variance).rename("beta")
    # The `x_var_eff_counts` term makes this invariant with respect to
    # rescalings of the weight column.
    x_var_eff_counts = x_var_coefficients["eff_count"]
    beta_se = np.sqrt(
        y_variance / (x_variance.multiply(x_var_eff_counts))
    ).rename("SE(beta)")
    z_scores = beta.divide(beta_se).rename("beta_z_scored")
    # Calculate two-sided p-values.
    p_val_array = 2 * sp.stats.norm.sf(z_scores.abs())
    p_val = pd.Series(index=z_scores.index, data=p_val_array, name="p_val_2s")
    # Consolidate stats.
    xy_coefficients = [
        covariance,
        sgn_rho,
        rho,
        beta,
        beta_se,
        z_scores,
        p_val,
    ]
    xy_coefficients = pd.concat(xy_coefficients, axis=1)
    result = pd.concat([x_var_coefficients, xy_coefficients], axis=1)
    cols = [
        "count",
        "eff_count",
        "mean",
        "var",
        "covar",
        "sgn_rho",
        "rho",
        "beta",
        "SE(beta)",
        "beta_z_scored",
        "p_val_2s",
        "autocovar",
        "autocorr",
        "turn",
    ]
    return result[cols]


def compute_centered_process_stats(
    df: pd.DataFrame,
    sample_weight_col: Optional[Union[int, str]] = None,
) -> pd.DataFrame:
    """
    Compute stats for mean zero processes.

    :param df: Dataframe where each col represents samples for a process. No
        correction is made for non-independence. Variance is calculated under
        the hypothesis that the mean is zero.
    :param sample_weight_col: optional column for sample weighting
    """
    weight_df = _get_weight_df(df, sample_weight_col)
    weight_sums = weight_df.sum(axis=0)
    process_df = df
    if sample_weight_col is not None:
        process_df = process_df.drop(sample_weight_col, axis=1)
    counts = process_df.count().rename("count")
    # We use the 2-cardinality of the weights. This is equivalent to using
    # Kish's effective sample size.
    eff_counts = weight_df.apply(
        lambda x: cstaentr.compute_cardinality(x.dropna(), 2)
    ).rename("eff_count")
    # Calculate mean.
    mean = (
        process_df.multiply(weight_df, axis=0)
        .sum(axis=0)
        .divide(weight_sums)
        .rename("mean")
    )
    # Calculate variance assuming x variables are centered at zero.
    variance = (
        process_df.pow(2)
        .multiply(weight_df, axis=0)
        .sum(axis=0)
        .divide(weight_sums)
        .rename("var")
    )
    # Calculate autocovariance-related stats of x variables.
    autocovariance = (
        process_df.multiply(process_df.shift(1), axis=0)
        .multiply(weight_df, axis=0)
        .sum(axis=0)
        .divide(weight_sums)
        .rename("autocovar")
    )
    # Normalize autocovariance to get autocorrelation.
    autocorrelation = autocovariance.divide(variance).rename("autocorr")
    turn = np.sqrt(2 * (1 - autocorrelation)).rename("turn")
    # Consolidate stats.
    coefficients = [
        counts,
        eff_counts,
        mean,
        variance,
        autocovariance,
        autocorrelation,
        turn,
    ]
    return pd.concat(coefficients, axis=1)


def compute_centered_process_stats_by_group(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute process stats for each col of each group.

    :param df: as in `compute_centered_process_stats()`
    :return: output of `compute_centered_process_stats()` concatenated with
        group on index.
    """
    func = compute_centered_process_stats
    func_kwargs = {}
    result_df = _compute_func_by_group(df, func, func_kwargs)
    return result_df


def compute_regression_coefficients_by_group(
    df: pd.DataFrame,
    x_cols: List[Union[int, str]],
    y_col: Union[int, str],
    *,
    x_col_shift: int = 0,
) -> pd.DataFrame:
    """
    Compute regression coefficients for each col of each group.

    :param df: as in `compute_regression_coefficients()`
    :param x_cols_: as in `compute_regression_coefficients()`
    :param y_col: as in `compute_regression_coefficients()`
    :param x_col_shift: as in `compute_regression_coefficients()`
    :return: output of `compute_regression_coefficients()` concatenated with
        group on index.
    """
    func = compute_regression_coefficients
    func_kwargs = {
        "x_cols": x_cols,
        "y_col": y_col,
        "x_col_shift": x_col_shift,
    }
    result_df = _compute_func_by_group(df, func, func_kwargs)
    return result_df


def _compute_func_by_group(
    df: pd.DataFrame,
    func: Callable[..., pd.DataFrame],
    func_kwargs: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Apply `func` to dfs from groups coming from col level 1.

    :param func: function to apply to dataframe; should return a dataframe
    :param func_kwargs: kwargs to forward to `func`
    :return: output dataframes with index level 0 given by group
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_eq(df.columns.nlevels, 2)
    groups = df.columns.levels[1].to_list()
    _LOG.debug("Num groups=%d", len(groups))
    results = collections.OrderedDict()
    if func_kwargs is None:
        func_kwargs = {}
    for group in tqdm(groups, desc="Processing groups"):
        group_df = df.T.xs(group, level=1).T
        if group_df.empty:
            _LOG.debug("Empty dataframe for group=%d", group)
            continue
        result = func(group_df, **func_kwargs)
        hdbg.dassert_isinstance(result, pd.DataFrame)
        results[group] = result
    result_df = pd.concat(results)
    return result_df


def _get_weight_df(
    df: pd.DataFrame,
    sample_weight_col: Optional[Union[int, str]] = None,
) -> pd.DataFrame:
    hdbg.dassert(not df.empty, msg="Dataframe must be nonempty")
    if sample_weight_col is not None:
        hdbg.dassert_in(sample_weight_col, df.columns)
        weights = df[sample_weight_col].rename("weight")
    else:
        weights = pd.Series(index=df.index, data=1, name="weight")
    # Ensure that no weights are negative.
    hdbg.dassert(not (weights < 0).any())
    # Ensure that the total weight is positive.
    hdbg.dassert((weights > 0).any())
    # Create a per-`x_col` weight dataframe to reflect possibly different NaN
    # positions. This is used to generate accurate weighted sums and effective
    # sample sizes.
    cols = [x for x in df.columns if x != sample_weight_col]
    # if sample_weight_col is not None:
    #    cols = cols - [sample_weight_col]
    weight_df = pd.DataFrame(index=df.index, columns=cols)
    for col in cols:
        weight_df[col] = weights.reindex(df[col].dropna().index)
    return weight_df
