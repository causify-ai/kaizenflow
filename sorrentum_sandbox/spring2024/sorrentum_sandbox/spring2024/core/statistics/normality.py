"""
Import as:

import core.statistics.normality as cstanorm
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def apply_normality_test(
    srs: pd.Series,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Test (indep) null hypotheses that each col is normally distributed.

    An omnibus test of normality that combines skew and kurtosis.

    :param prefix: optional prefix for metrics' outcome
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :return: series with statistics and p-value
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    result_index = [
        prefix + "stat",
        prefix + "pval",
    ]
    nan_result = pd.Series(data=np.nan, index=result_index, name=srs.name)
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        stat, pval = sp.stats.normaltest(data, nan_policy="raise")
    except ValueError as inst:
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        _LOG.warning(inst)
        return nan_result
    result_values = [
        stat,
        pval,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


def compute_centered_gaussian_total_log_likelihood(
    srs: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute the log likelihood that `srs` came from a centered Gaussian.
    """
    prefix = prefix or ""
    # Calculate variance assuming a population mean of zero.
    var = np.square(srs).mean()
    name = str(srs.name) + "var"
    var_srs = pd.Series(index=srs.index, data=var, name=name)
    df = pd.concat([srs, var_srs], axis=1)
    df_out = compute_centered_gaussian_log_likelihood_df(
        df, observation_col=srs.name, variance_col=name
    )
    log_likelihood = df_out["log_likelihood"].sum()
    result = pd.Series(
        data=[log_likelihood, var],
        index=[prefix + "log_likelihood", prefix + "centered_var"],
        name=srs.name,
    )
    return result


def compute_centered_gaussian_log_likelihood_df(
    df: pd.DataFrame,
    observation_col: str,
    variance_col: str,
    square_variance_col: bool = False,
    variance_shifts: int = 0,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return the log-likelihoods of independent draws from centered Gaussians.

    A higher log-likelihood score means that the model of independent
    Gaussian draws with given variances is a better fit.

    The log-likelihood of the series of observations may be obtained by
    summing the individual log-likelihood values.

    :param df: dataframe with float observation and variance columns
    :param observation_col: name of column containing observations
    :param variance_col: name of column containing variances
    :square_variance_col: if `True`, square the values in `variance_col`
        (use this if the column contains standard deviations)
    :variance_shifts: number of shifts to apply to `variance_col` prior to
        calculating log-likelihood. Use this if `variance_col` contains forward
        predictions.
    :prefix: prefix to add to name of output series
    :return: dataframe of log-likelihoods and adjusted observations
    """
    prefix = prefix or ""
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Extract observations and variance, with optional shift applied.
    obs = df[observation_col]
    var = df[variance_col].shift(variance_shifts)
    hdbg.dassert(not (var <= 0).any(), msg="Variance values must be positive.")
    if square_variance_col:
        var = np.square(var)
    # Restrict to relevant data and drop any rows with NaNs.
    idx = pd.concat([obs, var], axis=1).dropna().index
    obs = obs.loc[idx]
    var = var.loc[idx]
    # Ensure that there is at least one observation.
    n_obs = idx.size
    _LOG.debug("Number of non-NaN observations=%i", n_obs)
    hdbg.dassert_lt(0, n_obs)
    # Perform log-likelihood calculation.
    # This term only depends upon the presence of an observation. We preserve
    # it here to facilitate comparisons across series with different numbers of
    # observations.
    constant_term = -0.5 * np.log(2 * np.pi)
    # This term depends upon the observation values and variances.
    data_term = -0.5 * (np.log(var) + np.square(obs).divide(var))
    log_likelihoods = constant_term + data_term
    log_likelihoods.name = prefix + "log_likelihood"
    # Compute observations normalized by standard deviations.
    adj_obs = obs.divide(np.sqrt(var))
    adj_obs.name = prefix + "normalized_observations"
    # Construct output dataframe.
    df_out = pd.concat([adj_obs, log_likelihoods], axis=1)
    return df_out
