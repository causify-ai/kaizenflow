"""
Import as:

import core.statistics.requires_statsmodels as cstresta
"""

import logging
from typing import Optional, Union, cast

import numpy as np
import pandas as pd
import statsmodels
import statsmodels.api as sm

import core.statistics.returns_and_volatility as csreanvo
import core.statistics.signed_runs as cstsirun
import core.statistics.t_test as cstttes
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_kratio(pnl: pd.Series) -> float:
    """
    Calculate K-Ratio of a time series.

    :param pnl: time series of log returns
    :return: K-Ratio
    """
    hdbg.dassert_isinstance(pnl, pd.Series)
    # TODO(Paul): Remove the implicit resampling.
    # pnl = maybe_resample(pnl)
    pnl = hdatafr.apply_nan_mode(pnl, mode="fill_with_zero")
    cum_rets = pnl.cumsum()
    # Fit the best line to the daily rets.
    x = range(len(cum_rets))
    x = sm.add_constant(x)
    reg = sm.OLS(cum_rets, x)
    model = reg.fit()
    # Compute k-ratio as slope / std err of slope.
    slope_name = "x1"
    hdbg.dassert_in(slope_name, model.params)
    hdbg.dassert_in(slope_name, model.bse)
    kratio = model.params[slope_name] / model.bse[slope_name]
    # Adjust k-ratio by the number of observations and points per year.
    ppy = hdatafr.infer_sampling_points_per_year(pnl)
    kratio = kratio * np.sqrt(ppy) / len(pnl)
    kratio = cast(float, kratio)
    return kratio


# #############################################################################
# Stationarity statistics
# #############################################################################


# TODO(*): Maybe add `inf_mode`.
def apply_adf_test(
    srs: pd.Series,
    maxlag: Optional[int] = None,
    regression: Optional[str] = None,
    autolag: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Implement a wrapper around statsmodels' adfuller test.

    :param srs: pandas series of floats
    :param maxlag: as in stattools.adfuller
    :param regression: as in stattools.adfuller
    :param autolag: as in stattools.adfuller
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue, and related info
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    regression = regression or "c"
    autolag = autolag or "AIC"
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    # Hack until we factor out inf handling.
    srs = srs.replace([np.inf, -np.inf], np.nan)
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html
    result_index = [
        prefix + "stat",
        prefix + "pval",
        prefix + "used_lag",
        prefix + "nobs",
        prefix + "critical_values_1%",
        prefix + "critical_values_5%",
        prefix + "critical_values_10%",
        prefix + "ic_best",
    ]
    nan_result = pd.Series(
        data=np.nan,
        index=result_index,
        name=data.name,
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        # The output of sm.tsa.stattools.adfuller in this case can only be
        # of the length 6 so ignore the lint.
        (
            adf_stat,
            pval,
            usedlag,
            nobs,
            critical_values,
            icbest,
        ) = sm.tsa.stattools.adfuller(
            data.values, maxlag=maxlag, regression=regression, autolag=autolag
        )
    except ValueError as inst:
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        _LOG.warning(inst)
        return nan_result
        #
    result_values = [
        adf_stat,
        pval,
        usedlag,
        nobs,
        critical_values["1%"],
        critical_values["5%"],
        critical_values["10%"],
        icbest,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


def apply_kpss_test(
    srs: pd.Series,
    regression: Optional[str] = None,
    nlags: Optional[Union[int, str]] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Implement a wrapper around statsmodels' KPSS test.

    http://debis.deu.edu.tr/userweb//onder.hanedar/dosyalar/kpss.pdf

    :param srs: pandas series of floats
    :param regression: as in stattools.kpss
    :param nlags: as in stattools.kpss
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue, and related info
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    regression = regression or "c"
    nan_mode = nan_mode or "drop"
    nlags = nlags or "auto"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html
    result_index = [
        prefix + "stat",
        prefix + "pval",
        prefix + "lags",
        prefix + "critical_values_1%",
        prefix + "critical_values_5%",
        prefix + "critical_values_10%",
    ]
    nan_result = pd.Series(
        data=np.nan,
        index=result_index,
        name=data.name,
    )
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        (
            kpss_stat,
            pval,
            lags,
            critical_values,
        ) = sm.tsa.stattools.kpss(data.values, regression=regression, nlags=nlags)
    except (ValueError, OverflowError):
        # This can raise if there are not enough data points, but the number
        # required can depend upon the input parameters.
        # TODO(Julia): Debug OverflowError.
        return nan_result
        #
    result_values = [
        kpss_stat,
        pval,
        lags,
        critical_values["1%"],
        critical_values["5%"],
        critical_values["10%"],
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result


# #############################################################################
# Autocorrelation and cross-correlation statistics
# #############################################################################


def apply_ljung_box_test(
    srs: pd.Series,
    lags: Optional[Union[int, pd.Series]] = None,
    model_df: Optional[int] = None,
    period: Optional[int] = None,
    return_df: Optional[bool] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Implement a wrapper around statsmodels' Ljung-Box test.

    :param srs: pandas series of floats
    :param lags: as in diagnostic.acorr_ljungbox
    :param model_df: as in diagnostic.acorr_ljungbox
    :param period: as in diagnostic.acorr_ljungbox
    :param return_df: as in diagnostic.acorr_ljungbox
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: test statistic, pvalue
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    model_df = model_df or 0
    return_df = return_df or True
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    # https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html
    columns = [
        prefix + "stat",
        prefix + "pval",
    ]
    # Make an output for empty or too short inputs.
    nan_result = pd.DataFrame([[np.nan, np.nan]], columns=columns)
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        result = sm.stats.diagnostic.acorr_ljungbox(
            data.values,
            lags=lags,
            model_df=model_df,
            period=period,
            return_df=return_df,
        )
    except ValueError as inst:
        _LOG.warning(inst)
        return nan_result
    #
    if return_df:
        df_result = result
    else:
        df_result = pd.DataFrame(result).T
    df_result.columns = columns
    return df_result


# #############################################################################
# Hit rate: MDA
# #############################################################################


# TODO(Grisha): can we use `scipy.stats.binomtest.proportion_ci` instead?
# to get rid of `statsmodels` dependency?
def calculate_hit_rate(
    srs: pd.Series,
    alpha: Optional[float] = None,
    method: Optional[str] = None,
    threshold: Optional[float] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate hit rate statistics.

    :param srs: pandas series
    :param alpha: as in
        statsmodels.stats.proportion.proportion_confint()
    :param method: as in
        statsmodels.stats.proportion.proportion_confint()
    :param threshold: threshold value around zero to exclude from
        calculations
    :param prefix: optional prefix for metrics' outcome
    :return: hit rate statistics: point estimate, lower bound, upper
        bound
    """
    alpha = alpha or 0.05
    method = method or "jeffreys"
    hdbg.dassert_lte(0, alpha)
    hdbg.dassert_lte(alpha, 1)
    hdbg.dassert_isinstance(srs, pd.Series)
    threshold = threshold or 0
    hdbg.dassert_lte(0, threshold)
    prefix = prefix or ""
    # Process series.
    conf_alpha = (1 - alpha / 2) * 100
    # TODO(Grisha): @Dan change format to `hit_rate.{alpha:.2f}.CI_lower_bound[%]`,
    # also remove `point_est` suffix, should be just `hit_rate[%]`.
    result_index = [
        prefix + "hit_rate_point_est_(%)",
        prefix + f"hit_rate_{conf_alpha:.2f}%CI_lower_bound_(%)",
        prefix + f"hit_rate_{conf_alpha:.2f}%CI_upper_bound_(%)",
    ]
    # Set all the values whose absolute values are closer to zero than
    #    the absolute value of the threshold equal to NaN.
    srs = srs.mask(abs(srs) < threshold)
    # Set all the inf values equal to NaN.
    srs = srs.replace([np.inf, -np.inf, 0], np.nan)
    # Drop all the NaN values.
    srs = hdatafr.apply_nan_mode(srs, mode="drop")
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        nan_result = pd.Series(index=result_index, name=srs.name, dtype="float64")
        return nan_result
    hit_mask = srs >= threshold
    # Calculate confidence intervals.
    point_estimate = hit_mask.mean()
    hit_lower, hit_upper = statsmodels.stats.proportion.proportion_confint(
        count=hit_mask.sum(), nobs=hit_mask.count(), alpha=alpha, method=method
    )
    result_values_pct = [100 * point_estimate, 100 * hit_lower, 100 * hit_upper]
    result = pd.Series(data=result_values_pct, index=result_index, name=srs.name)
    return result


# #############################################################################
# Hypothesis testing
# #############################################################################


def multipletests(
    srs: pd.Series,
    method: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Wrap statsmodel's multipletests.

    Returns results in a series indexed like srs.
    Documentation at
    https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html

    :param srs: Series with pvalues
    :param method: `method` for scipy's multipletests
    :param nan_mode: approach to deal with NaNs, can be "strict" or "drop"
    :param prefix: optional prefix for metrics' outcome
    :return: Series of adjusted p-values
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    method = method or "fdr_bh"
    nan_mode = nan_mode or "strict"
    hdbg.dassert_in(nan_mode, ["strict", "drop"])
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return pd.Series([np.nan], name=prefix + "adj_pval")
    pvals_corrected = statsmodels.stats.multitest.multipletests(
        data, method=method
    )[1]
    return pd.Series(pvals_corrected, index=data.index, name=prefix + "adj_pval")


def multi_ttest(
    data: pd.DataFrame,
    popmean: Optional[float] = None,
    nan_mode: Optional[str] = None,
    method: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Combine ttest and multitest pvalue adjustment.
    """
    popmean = popmean or 0
    nan_mode = nan_mode or "drop"
    method = method or "fdr_bh"
    prefix = prefix or ""
    hdbg.dassert_isinstance(data, pd.DataFrame)
    if data.empty:
        _LOG.warning("Empty input!")
        return pd.DataFrame(
            np.nan,
            index=[prefix + "tval", prefix + "pval", prefix + "adj_pval"],
            columns=[data.columns],
        )
    res = data.apply(
        cstttes.ttest_1samp, popmean=popmean, nan_mode=nan_mode, prefix=prefix
    ).T
    res[prefix + "adj_pval"] = multipletests(res[prefix + "pval"], method=method)
    return res


def compute_bet_stats(
    positions: pd.Series,
    returns: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate average returns for grouped bets.

    :param positions: series of long/short positions
    :param returns: returns
    :param prefix: optional prefix for metrics' outcome
    :return: series of average returns for winning/losing and long/short bets,
        number of positions and bets. In `average_num_bets_per_year`, "year" is
        not the calendar year, but an approximate number of data points in a
        year
    """
    # TODO(Paul): Consider requiring `freq` on the index.
    prefix = prefix or ""
    bet_lengths = cstsirun.compute_signed_run_lengths(positions)
    returns_per_bet = csreanvo.compute_returns_per_bet(positions, returns)
    #
    stats = dict()
    stats["num_positions"] = int(bet_lengths.abs().sum())
    stats["num_bets"] = bet_lengths.size
    stats["long_bets_frac"] = (bet_lengths > 0).sum() / bet_lengths.size
    if positions.index.freq is not None:
        n_years = positions.size / hdatafr.infer_sampling_points_per_year(
            positions
        )
        stats["mean_num_bets_per_year"] = bet_lengths.size / n_years
    # Format index.freq outcome to the word that represents its frequency.
    #    E.g. if `srs.index.freq` is equal to `<MonthEnd>` then
    #    this line will convert it to the string "Month".
    freq = str(positions.index.freq)[1:-1].split("End")[0]
    stats["mean_bet_length"] = bet_lengths.abs().mean()
    stats["bet_length_units"] = freq
    bet_hit_rate = calculate_hit_rate(returns_per_bet, prefix="bet_")
    stats.update(bet_hit_rate)
    #
    mean_returns_winning_bets = returns_per_bet.loc[returns_per_bet > 0].mean()
    stats["mean_return_winning_bets"] = mean_returns_winning_bets
    mean_returns_losing_bets = returns_per_bet.loc[returns_per_bet < 0].mean()
    stats["mean_return_losing_bets"] = mean_returns_losing_bets
    mean_returns_long_bet = returns_per_bet.loc[bet_lengths > 0].mean()
    stats["mean_return_long_bet"] = mean_returns_long_bet
    mean_returns_short_bet = returns_per_bet.loc[bet_lengths < 0].mean()
    stats["mean_return_short_bet"] = mean_returns_short_bet
    #
    srs = pd.Series(stats, name=returns.name)
    srs.index = prefix + srs.index
    return srs
