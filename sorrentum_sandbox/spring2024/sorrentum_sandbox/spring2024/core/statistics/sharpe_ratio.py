"""
Import as:

import core.statistics.sharpe_ratio as cstshrat
"""

import logging
import numbers
from typing import Any, Optional, Union, cast

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Sharpe ratio
# #############################################################################


def summarize_sharpe_ratio(
    pnl: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate SR, SE(SR) from rets with an index freq and annualize.

    TODO(*): Consider de-biasing when the number of sample points is small,
        e.g., https://www.twosigma.com/wp-content/uploads/sharpe-tr-1.pdf
    """
    prefix = prefix or ""
    sr = compute_annualized_sharpe_ratio(pnl)
    sr_se_estimate = compute_annualized_sharpe_ratio_standard_error(pnl)
    res = pd.Series(
        data=[sr, sr_se_estimate],
        index=[prefix + "sharpe_ratio", prefix + "sharpe_ratio_standard_error"],
        name=pnl.name,
    )
    return res


def zscore_oos_sharpe_ratio(
    pnl: pd.Series, oos: Any, prefix: Optional[str] = None
) -> pd.Series:
    """
    Z-score the observed OOS SR wrt the INS SR and inflated SE.

    Calculate the following stats:
      - SR, SE(SR) for INS
      - SR, SE(SR) for OOS
      - z-scored OOS SR

    TODO(*): Consider factoring out pieces and/or returning more info.

    :param pnl: time series of per-period PnL
    :param oos: start of OOS (right endpoint)
    :param prefix: prefix for the output series index
    :return: series of SR stats
    """
    prefix = prefix or ""
    # Create ins/oos masks.
    ins_mask = pnl.index < oos
    hdbg.dassert(ins_mask.any())
    ins_nobs = ins_mask.sum()
    oos_mask = pnl.index >= oos
    hdbg.dassert(oos_mask.any())
    oos_nobs = oos_mask.sum()
    #
    inflation = compute_sharpe_ratio_prediction_interval_inflation_factor(
        ins_nobs, oos_nobs
    )
    #
    ins_srs = pnl.loc[ins_mask].copy()
    oos_srs = pnl.loc[oos_mask].copy()
    # Compute INS Sharpe ratio and SE.
    ins_sr_and_se = summarize_sharpe_ratio(ins_srs, prefix="INS_")
    # Compute OOS Sharpe ratio and SE.
    oos_sr_and_se = summarize_sharpe_ratio(oos_srs, prefix="OOS_")
    # Z-score OOS SR using INS SR and inflated SE.
    pred_sr_se = inflation * ins_sr_and_se.loc["INS_sharpe_ratio_standard_error"]
    zscored_oos_sr = (
        oos_sr_and_se.loc["OOS_sharpe_ratio"]
        - ins_sr_and_se.loc["INS_sharpe_ratio"]
    ) / pred_sr_se
    # Combine results.
    zscored_oos_sr_srs = pd.Series(
        [zscored_oos_sr],
        name=oos_sr_and_se.name,
        index=["zscored_OOS_sharpe_ratio"],
    )
    res = pd.concat([ins_sr_and_se, oos_sr_and_se, zscored_oos_sr_srs])
    res.index = prefix + res.index
    return res


def compute_annualized_sharpe_ratio(
    pnl: Union[pd.Series, pd.DataFrame],
) -> Union[float, pd.Series]:
    """
    Compute SR from rets with an index freq and annualize.

    :param pnl: time series of per-period PnL
    :return: annualized Sharpe ratio
    """
    pnl = maybe_resample(pnl)
    points_per_year = hdatafr.infer_sampling_points_per_year(pnl)
    if isinstance(pnl, pd.Series):
        pnl = hdatafr.apply_nan_mode(pnl, mode="fill_with_zero")
    if isinstance(pnl, pd.DataFrame):
        pnl = pnl.apply(hdatafr.apply_nan_mode, mode="fill_with_zero")
    sr = compute_sharpe_ratio(pnl, points_per_year)
    return sr


def compute_annualized_sharpe_ratio_standard_error(
    pnl: Union[pd.Series, pd.DataFrame],
) -> Union[float, pd.Series]:
    """
    Compute SE(SR) from rets with an index freq and annualize.

    This function calculates the standard error with respect to the original
    sampling frequency and then rescales to turn it into a standard error
    for the corresponding annualized Sharpe ratio.

    :param pnl: time series of per-period PnL
    :return: standard error estimate of annualized Sharpe ratio
    """
    pnl = maybe_resample(pnl)
    points_per_year = hdatafr.infer_sampling_points_per_year(pnl)
    pnl = hdatafr.apply_nan_mode(pnl, mode="fill_with_zero")
    se_sr = compute_sharpe_ratio_standard_error(pnl, points_per_year)
    return se_sr


def compute_sharpe_ratio(
    pnl: Union[pd.Series, pd.DataFrame], time_scaling: Union[int, float] = 1
) -> Union[float, pd.Series]:
    r"""Calculate Sharpe Ratio (SR) from pnl and rescale.

    For a detailed exploration of SR, see
    http://www.gilgamath.com/pages/ssc.html.

    :param pnl: time series of per-period PnL
    :param time_scaling: rescales SR by a factor of \sqrt(time_scaling).
        - For SR with respect to the sampling frequency, set equal to 1
        - For annualization, set equal to the number of sampling frequency
          ticks per year (e.g., =252 if daily returns are provided)
    :return: Sharpe Ratio
    """
    hdbg.dassert_lte(1, time_scaling, f"time_scaling=`{time_scaling}`")
    sr = pnl.mean() / pnl.std()
    sr *= np.sqrt(time_scaling)
    if isinstance(sr, pd.Series):
        sr.name = "SR"
    return sr


def compute_sharpe_ratio_standard_error(
    pnl: Union[pd.Series, pd.DataFrame], time_scaling: Union[int, float] = 1
) -> Union[float, pd.Series]:
    """
    Calculate Sharpe Ratio standard error from pnl and rescale.

    :param pnl: time series of per-period PnL
    :param time_scaling: as in `compute_sharpe_ratio`
    :return: Sharpe ratio standard error estimate
    """
    hdbg.dassert_lte(1, time_scaling, f"time_scaling=`{time_scaling}`")
    # Compute the Sharpe ratio using the sampling frequency units[
    sr = compute_sharpe_ratio(pnl, time_scaling=1)
    srs_size = hdatafr.apply_nan_mode(pnl, mode="drop").size
    hdbg.dassert_lt(1, srs_size)
    sr_var_estimate = (1 + (sr**2) / 2) / (srs_size - 1)
    sr_se_estimate = np.sqrt(sr_var_estimate)
    # Rescale.
    rescaled_sr_se_estimate = np.sqrt(time_scaling) * sr_se_estimate
    if isinstance(sr, pd.Series):
        rescaled_sr_se_estimate = "SE(SR)"
    return rescaled_sr_se_estimate


# #############################################################################
# Sharpe ratio tests
# #############################################################################


def apply_ttest_power_rule(
    alpha: float,
    power: float,
    two_sided: bool = False,
    years: Optional[float] = None,
    sharpe_ratio: Optional[float] = None,
) -> pd.Series:
    """Apply t-test power rule to SR will null hypothesis SR = 0.

    - The `power` is with respect to a specific type I error probability
      `alpha`
    - Supply exactly one of `years` and `sharpe_ratio`; the other is computed
      - E.g., if `sharpe_ratio` is supplied, then `years` can be interpreted
        as the required sample size
      - If `years` is supplied, then `sharpe_ratio` is the threshold at which
        the specified power holds.

    :param alpha: type I error probability
    :param power: 1 - type II error probability
    :param two_sided: one or two-sided t-test
    :param years: number of years
    :param sharpe_ratio: annualized Sharpe ratio
    :return: pd.Series of power rule formula values and assumptions
    """
    const = compute_ttest_power_rule_constant(
        alpha=alpha, power=power, two_sided=two_sided
    )
    if years is None and sharpe_ratio is not None:
        hdbg.dassert_isinstance(sharpe_ratio, numbers.Number)
        years = const / (sharpe_ratio**2)
    elif years is not None and sharpe_ratio is None:
        hdbg.dassert_isinstance(years, numbers.Number)
        sharpe_ratio = np.sqrt(const / years)
    else:
        raise ValueError(
            "Precisely one of `years` and `sharpe_ratio` should not be `None`"
        )
    idx = [
        "sharpe_ratio",
        "years",
        "power_rule_const",
        "type_I_error",
        "two_sided",
        "type_II_error",
        "power",
    ]
    data = [sharpe_ratio, years, const, alpha, two_sided, 1 - power, power]
    srs = pd.Series(index=idx, data=data, name="ttest_power_rule")
    return srs


def compute_ttest_power_rule_constant(
    alpha: float, power: float, two_sided: bool = False
) -> float:
    """
    Compute the constant to use in the t-test power law.

    E.g., http://www.vanbelle.org/chapters/webchapter2.pdf

    A special case of this is known as Lehr's rule.

    :param alpha: type I error rate
    :param power: 1 - type II error rate
    :param two_sided: one or two-sided t-test
    :return: constant to use in (one sample) t-test power law
    """
    hdbg.dassert_lt(0, alpha)
    hdbg.dassert_lt(alpha, 1)
    hdbg.dassert_lt(0, power)
    hdbg.dassert_lt(power, 1)
    if two_sided:
        alpha /= 2
    const: float = (sp.stats.norm.ppf(1 - alpha) + sp.stats.norm.ppf(power)) ** 2
    return const


def compute_sharpe_ratio_prediction_interval_inflation_factor(
    ins_nobs: Union[int, float], oos_nobs: Union[int, float]
) -> float:
    """
    Compute the SE(SR) inflation factor for obtaining conditional OOS bounds.

    :param ins_nobs: number of observations in-sample
    :param oos_nobs: number of observations out-of-sample
    :return: float > 1
    """
    se_inflation_factor = np.sqrt(1 + ins_nobs / oos_nobs)
    se_inflation_factor = cast(float, se_inflation_factor)
    return se_inflation_factor


def apply_sharpe_ratio_correlation_conversion(
    points_per_year: float,
    sharpe_ratio: Optional[float] = None,
    correlation: Optional[float] = None,
) -> float:
    """
    Convert annualized SR to correlation or vice-versa.

    :param points_per_year: number of trading periods per year
    :param sharpe_ratio: annualized Sharpe ratio
    :param correlation: correlation coefficient
    :return: annualized Sharpe ratio if correlation is provided; correlation
        if annualized Sharpe ratio is provided.
    """
    if sharpe_ratio is not None and correlation is None:
        sharpe_ratio /= np.sqrt(points_per_year)
        return sharpe_ratio / np.sqrt(1 - sharpe_ratio**2)
    if sharpe_ratio is None and correlation is not None:
        sharpe_ratio = correlation / np.sqrt(1 + correlation**2)
        return sharpe_ratio * np.sqrt(points_per_year)
    raise ValueError(
        "Precisely one of `sharpe_ratio` and `correlation` should not be `None`"
    )


def compute_implied_correlation(pnl: pd.Series) -> float:
    """
    Infer correlation of prediction with returns given PnL.

    The inferred correlation is an estimate based on the following assumptions:
      1. Returns are Gaussian
      2. Positions are proportional to predictions
      3. Every value of `pnl` corresponds to a unique position and prediction
         (so the pnl frequency is the same as the prediction frequency)
    The principle is to estimate the correlation from the Sharpe ratio of
    `pnl`. This function addresses the issue of calculating the appropriate
    scaling factors required to perform the conversion correctly.

    :param pnl: PnL stream with `freq`
    :return: estimated correlation of the predictions that, when combined with
        returns, generated `pnl`
    """
    count_per_year = hdatafr.compute_count_per_year(pnl)
    sr = compute_annualized_sharpe_ratio(pnl)
    corr = apply_sharpe_ratio_correlation_conversion(
        count_per_year, sharpe_ratio=sr
    )
    return corr


def compute_implied_sharpe_ratio(srs: pd.Series, corr: float) -> float:
    """
    Infer implied Sharpe ratio given `corr` and predictions at `srs` non-NaNs.

    Same assumptions as `compute_implied_correlation()`, and `srs` must
    have a `DatetimeIndex` with a `freq`. The values of `srs` are not
    used directly, but rather only the knowledge of whether they are
    included in `srs.count()`, e.g., are non-NaN, non-inf, etc.
    """
    hdbg.dassert_lte(-1, corr)
    hdbg.dassert_lte(corr, 1)
    count_per_year = hdatafr.compute_count_per_year(srs)
    sr = apply_sharpe_ratio_correlation_conversion(
        count_per_year, correlation=corr
    )
    return sr


def compute_hit_rate_implied_by_correlation(
    corr: float, j_ratio: Optional[float] = None
) -> float:
    """
    Infer hit rate given `corr`.

    This approximation is only valid under certain distributional
    assumptions.
    """
    j_ratio = j_ratio or np.sqrt(2 / np.pi)
    hdbg.dassert_lt(0, j_ratio)
    hdbg.dassert_lte(j_ratio, 1)
    hdbg.dassert_lte(-1, corr)
    hdbg.dassert_lte(corr, 1)
    return sp.stats.norm.sf(-1 * corr / j_ratio)


def compute_correlation_implied_by_hit_rate(
    hit_rate: float, j_ratio: Optional[float] = None
) -> float:
    """
    Infer correlation given `hit_rate`. Assumes normal-like series.

    This inverts `compute_hit_rate_implied_by_correlation()` and is
    similarly only valid under certain distributional assumptions.
    """
    j_ratio = j_ratio or np.sqrt(2 / np.pi)
    hdbg.dassert_lt(0, j_ratio)
    hdbg.dassert_lte(j_ratio, 1)
    hdbg.dassert_lte(0, hit_rate)
    hdbg.dassert_lte(hit_rate, 1)
    return j_ratio * sp.stats.norm.ppf(hit_rate)


# TODO(Paul): Consider centralizing this.
def maybe_resample(srs: pd.Series) -> pd.Series:
    """
    Return `srs` resampled to "B" `srs.index.freq` if is `None`.

    This is a no-op if `srs.index.freq` is not `None`.
    """
    hdbg.dassert_isinstance(srs.index, pd.DatetimeIndex)
    if srs.index.freq is None:
        _LOG.debug("No `freq` detected; resampling to 'B'.")
        srs = srs.resample("B").sum(min_count=1)
    return srs
