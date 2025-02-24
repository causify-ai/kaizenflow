"""
Import as:

import core.statistics.descriptive as cstadesc
"""

import logging
from typing import Optional, Union, cast

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# #############################################################################
# Sampling statistics: start, end, frequency, NaNs, infs, etc.
# #############################################################################


def summarize_time_index_info(
    srs: pd.Series,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Return summarized information about datetime index of the input.

    :param srs: pandas series of floats
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for output's index
    :return: series with information about input's index
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    original_index = srs.index
    # Assert that input series has a sorted datetime index.
    hdbg.dassert_isinstance(original_index, pd.DatetimeIndex)
    hpandas.dassert_strictly_increasing_index(original_index)
    freq = original_index.freq
    clear_srs = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    clear_index = clear_srs.index
    result = {}
    if clear_srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        result["start_time"] = np.nan
        result["end_time"] = np.nan
    else:
        result["start_time"] = clear_index[0]
        result["end_time"] = clear_index[-1]
    result["n_sampling_points"] = len(clear_index)
    result["frequency"] = freq
    if freq is None:
        sampling_points_per_year = clear_srs.resample("Y").count().mean()
    else:
        sampling_points_per_year = hdatafr.compute_points_per_year_for_given_freq(
            freq
        )
    result["sampling_points_per_year"] = sampling_points_per_year
    # Compute input time span as a number of `freq` units in
    # `clear_index`.
    if not clear_srs.empty:
        if freq is None:
            clear_index_time_span = (clear_index[-1] - clear_index[0]).days
            sampling_points_per_year = (
                hdatafr.compute_points_per_year_for_given_freq("D")
            )
        else:
            clear_index_time_span = len(srs[clear_index[0] : clear_index[-1]])
    else:
        clear_index_time_span = 0
    result["time_span_in_years"] = (
        clear_index_time_span / sampling_points_per_year
    )
    result = pd.Series(result, dtype="object")
    result.index = prefix + result.index
    return result


def compute_special_value_stats(
    srs: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate special value statistics in time series.

    :param srs: pandas series of floats
    :param prefix: optional prefix for metrics' outcome
    :return: series of statistics
    """
    prefix = prefix or ""
    hdbg.dassert_isinstance(srs, pd.Series)
    result_index = [
        prefix + "n_rows",
        prefix + "frac_zero",
        prefix + "frac_nan",
        prefix + "frac_inf",
        prefix + "frac_constant",
        prefix + "num_finite_samples",
        prefix + "num_finite_samples_inv",
        prefix + "num_finite_samples_inv_dyadic_scale",
        prefix + "num_finite_samples_sqrt",
        prefix + "num_finite_samples_sqrt_inv",
        prefix + "num_finite_samples_sqrt_inv_dyadic_scale",
        prefix + "num_unique_values",
    ]
    nan_result = pd.Series(np.nan, index=result_index, name=srs.name)
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    num_finite_samples = count_num_finite_samples(srs)
    result_values = [
        len(srs),
        compute_frac_zero(srs),
        compute_frac_nan(srs),
        compute_frac_inf(srs),
        compute_zero_diff_proportion(srs).iloc[1],
        num_finite_samples,
        1 / num_finite_samples,
        compute_dyadic_scale(1 / num_finite_samples),
        np.sqrt(num_finite_samples),
        1 / np.sqrt(num_finite_samples),
        compute_dyadic_scale(1 / np.sqrt(num_finite_samples)),
        count_num_unique_values(srs),
    ]
    result = pd.Series(
        data=result_values, index=result_index, name=srs.name, dtype=object
    )
    return result


# TODO(*): Move this function out of this library.
def replace_infs_with_nans(
    data: Union[pd.Series, pd.DataFrame],
) -> Union[pd.Series, pd.DataFrame]:
    """
    Replace infs with nans in a copy of `data`.
    """
    if data.empty:
        _LOG.warning("Empty input!")
    return data.replace([np.inf, -np.inf], np.nan)


def compute_frac_zero(
    data: Union[pd.Series, pd.DataFrame],
    atol: float = 0.0,
    axis: Optional[int] = 0,
) -> Union[float, pd.Series]:
    """
    Calculate fraction of zeros in a numerical series or dataframe.

    :param data: numeric series or dataframe
    :param atol: absolute tolerance, as in `np.isclose`
    :param axis: numpy axis for summation
    """
    # Create an ndarray of zeros of the same shape.
    zeros = np.zeros(data.shape)
    # Compare values of `df` to `zeros`.
    is_close_to_zero = np.isclose(data.values, zeros, atol=atol)
    num_zeros = is_close_to_zero.sum(axis=axis)
    return _compute_denominator_and_package(num_zeros, data, axis)


def compute_frac_nan(
    data: Union[pd.Series, pd.DataFrame], axis: Optional[int] = 0
) -> Union[float, pd.Series]:
    """
    Calculate fraction of nans in `data`.

    :param data: numeric series or dataframe
    :param axis: numpy axis for summation
    """
    num_nans = data.isna().values.sum(axis=axis)
    return _compute_denominator_and_package(num_nans, data, axis)


def compute_frac_inf(
    data: Union[pd.Series, pd.DataFrame], axis: Optional[int] = 0
) -> Union[float, pd.Series]:
    """
    Count fraction of infs in a numerical series or dataframe.

    :param data: numeric series or dataframe
    :param axis: numpy axis for summation
    """
    num_infs = np.isinf(data.values).sum(axis=axis)
    return _compute_denominator_and_package(num_infs, data, axis)


# TODO(Paul): Refactor to work with dataframes as well. Consider how to handle
#     `axis`, which the pd.Series version of `copy()` does not take.
def count_num_finite_samples(data: pd.Series) -> Union[int, float]:
    """
    Count number of finite data points in a given time series.

    :param data: numeric series or dataframe
    """
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return np.nan  # type: ignore
    data = data.copy()
    data = replace_infs_with_nans(data)
    ret = data.count()
    ret = cast(int, ret)
    return ret


# TODO(Paul): Extend to dataframes.
def count_num_unique_values(data: pd.Series) -> Union[int, float]:
    """
    Count number of unique values in the series.
    """
    if data.empty:
        _LOG.warning("Empty input series `%s`", data.name)
        return np.nan
    srs = pd.Series(data=data.unique())
    return count_num_finite_samples(srs)


def compute_zero_diff_proportion(
    srs: pd.Series,
    atol: Optional[float] = None,
    rtol: Optional[float] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute proportion of unvarying periods in a series.

    https://numpy.org/doc/stable/reference/generated/numpy.isclose.html

    :param srs: pandas series of floats
    :param atol: as in numpy.isclose
    :param rtol: as in numpy.isclose
    :param nan_mode: argument for hdatafr.apply_nan_mode()
        If `nan_mode` is "leave_unchanged":
          - consecutive `NaN`s are not counted as a constant period
          - repeated values with `NaN` in between are not counted as a constant
            period
        If `nan_mode` is "drop":
          - the denominator is reduced by the number of `NaN` and `inf` values
          - repeated values with `NaN` in between are counted as a constant
            period
        If `nan_mode` is "ffill":
          - consecutive `NaN`s are counted as a constant period
          - repeated values with `NaN` in between are counted as a constant
            period
    :param prefix: optional prefix for metrics' outcome
    :return: series with proportion of unvarying periods
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    atol = atol or 0
    rtol = rtol or 1e-05
    nan_mode = nan_mode or "leave_unchanged"
    prefix = prefix or ""
    srs = srs.replace([np.inf, -np.inf], np.nan)
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    result_index = [
        prefix + "approx_const_count",
        prefix + "approx_const_frac",
    ]
    if data.shape[0] < 2:
        _LOG.warning(
            "Input series `%s` with size '%d' is too small",
            srs.name,
            data.shape[0],
        )
        nan_result = pd.Series(data=np.nan, index=result_index, name=srs.name)
        return nan_result
    # Compute if neighboring elements are equal within the given tolerance.
    equal_ngb_srs = np.isclose(data.shift(1)[1:], data[1:], atol=atol, rtol=rtol)
    # Compute number and proportion of equals among all neighbors pairs.
    approx_const_count = equal_ngb_srs.sum()
    n_pairs = data.shape[0] - 1
    approx_const_frac = approx_const_count / n_pairs
    result_values = [approx_const_count, approx_const_frac]
    res = pd.Series(data=result_values, index=result_index, name=srs.name)
    return res


def compute_dyadic_scale(num: float) -> int:
    """
    Return the dyadic scale of a number.

    We take this to be the integer `j` such that 2 ** j <= abs(num) < 2
    ** (j + 1)
    """
    abs_num = np.abs(num)
    hdbg.dassert_lt(0, abs_num)
    j = np.floor(np.log2(abs_num))
    return int(j)


# #############################################################################
# Summary statistics: location, spread, shape
# #############################################################################


# TODO(Paul): Double-check axes in used in calculation.
def compute_moments(
    srs: pd.Series,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate, mean, standard deviation, skew, and kurtosis.

    :param srs: input series for computing moments
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series of computed moments
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    data = replace_infs_with_nans(srs)
    data = hdatafr.apply_nan_mode(data, mode=nan_mode)
    result_index = [
        prefix + "mean",
        prefix + "std",
        prefix + "skew",
        prefix + "kurtosis",
    ]
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        nan_result = pd.Series(np.nan, index=result_index, name=srs.name)
        return nan_result
    # TODO(*): re-applyg stricter sp.stats nan_policy after we handle inf's.
    result_values = [
        data.mean(),
        data.std(),
        sp.stats.skew(data, nan_policy="omit"),
        sp.stats.kurtosis(data, nan_policy="omit"),
    ]
    result = pd.Series(data=result_values, index=result_index, name=srs.name)
    return result


def compute_jensen_ratio(
    signal: pd.Series,
    p_norm: float = 2,
    inf_mode: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Calculate a 0 < ratio <= 1 based on Jensen's inequality.

    TODO(Paul): Rename this "J-ratio" and the function `compute_j_ratio()` for
        short.

    Definition and derivation:
      - The result is the expectation of abs(f) divided by the p-th root of the
        expectation of the p-th power of abs(f). If we apply Jensen's
        inequality to (abs(signal)**p)**(1/p), renormalizing the greater value
        to 1, then the lesser value is the valued calculated by this function.
      - An alternative derivation is to apply Holder's inequality to `signal`,
        using the constant function `1` on the support of the `signal` as the
        2nd function.

    Interpretation:
      - If we apply this function to returns in the case where the expected
        value of returns is 0 and we take p_norm = 2, then the result of this
        function can be interpreted as a renormalized realized (inverse)
        volatility.
      - For a Gaussian signal, the expected value is np.sqrt(2 / np.pi), which
        is approximately 0.80. This holds regardless of the volatility of the
        Gaussian (so the measure is scale invariant).
      - For a stationary function, the expected value does not change with
        sampled series length.
      - For a signal that is t-distributed with 4 dof, the expected value is
        approximately 0.71.
    """
    hdbg.dassert_isinstance(signal, pd.Series)
    # Require that we evaluate a norm.
    hdbg.dassert_lte(1, p_norm)
    # TODO(*): Maybe add l-infinity support. For many stochastic signals, we
    # should not expect a finite value in the continuous limit.
    hdbg.dassert(np.isfinite(p_norm))
    # Set reasonable defaults for inf and nan modes.
    inf_mode = inf_mode or "drop"
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(signal, mode=nan_mode)
    nan_result = pd.Series(
        data=np.nan, index=[prefix + "jensen_ratio"], name=signal.name
    )
    hdbg.dassert(not data.isna().any())
    # Handle infs.
    # TODO(*): apply special functions for inf_mode after #2624 is completed.
    has_infs = (~data.apply(np.isfinite)).any()
    if has_infs:
        if inf_mode == "return_nan":
            # According to a strict interpretation, each norm is infinite, and
            # and so their quotient is undefined.
            return nan_result
        if inf_mode == "drop":
            # Replace inf values with np.nan and drop.
            data = data.replace([-np.inf, np.inf], np.nan).dropna()
        else:
            raise ValueError(f"Unrecognized inf_mode `{inf_mode}")
    hdbg.dassert(data.apply(np.isfinite).all())
    # Return NaN if there is no data.
    if data.size == 0:
        _LOG.warning("Empty input signal `%s`", signal.name)
        return nan_result
    # Calculate norms.
    lp = sp.linalg.norm(data, ord=p_norm)
    l1 = sp.linalg.norm(data, ord=1)
    # Ignore support where `signal` has NaNs.
    scaled_support = data.size ** (1 - 1 / p_norm)
    jensen_ratio = l1 / (scaled_support * lp)
    res = pd.Series(
        data=[jensen_ratio], index=[prefix + "jensen_ratio"], name=signal.name
    )
    return res


def compute_t_distribution_j_2(nu: float):
    """
    Compute the Jensen ratio with `p_norm = 2` for a standard t-distribution.

    :param nu: degrees of freedom
    :return: the theoretical J-ratio for a standard t-distribution with `nu`
        degrees of freedom.
    """
    hdbg.dassert_lte(2, nu, "The Jensen ratio is only well defined for nu >= 2.")
    if nu == np.inf:
        jensen_2 = np.sqrt(2 / np.pi)
    elif nu == 2:
        jensen_2 = 0
    else:
        if nu > 300:
            _LOG.warning("Computation is unstable for large values of `nu`.")
        const = 2 / np.sqrt(np.pi)
        dist = sp.special.gamma((nu + 1) / 2) / (
            sp.special.gamma(nu / 2) * (nu - 1)
        )
        jensen_2 = const * dist * np.sqrt(nu - 2)
    return jensen_2


def _compute_denominator_and_package(
    reduction: Union[float, np.ndarray],
    data: Union[pd.Series, pd.DataFrame],
    axis: Optional[float] = None,
) -> Union[float, pd.Series]:
    """
    Normalize and package `reduction` according to `axis` and `data` metadata.

    This is a helper function used for several `compute_frac_*` functions:
    - It determines the denominator to use in normalization (for the `frac`
      part)
    - It packages the output so that it has index/column information as
      appropriate

    :param reduction: contains a reduction of `data` along `axis`
    :param data: numeric series or dataframe
    :param axis: indicates row or column or else `None` for ignoring 2d
        structure
    """
    if isinstance(data, pd.Series):
        df = data.to_frame()
    else:
        df = data
    nrows, ncols = df.shape
    # Ensure that there is data available.
    # TODO(Paul): Consider adding a check on the column data type.
    if nrows == 0 or ncols == 0:
        _LOG.warning("No data available!")
        return np.nan
    # Determine the correct denominator based on `axis`.
    if axis is None:
        denom = nrows * ncols
    elif axis == 0:
        denom = nrows
    elif axis == 1:
        denom = ncols
    else:
        raise ValueError("axis=%i" % axis)
    normalized = reduction / denom
    # Return float or pd.Series as appropriate based on dimensions and axis.
    if isinstance(normalized, float):
        hdbg.dassert(not axis)
        return normalized
    hdbg.dassert_isinstance(normalized, np.ndarray)
    if axis == 0:
        return pd.Series(data=normalized, index=df.columns)
    if axis == 1:
        return pd.Series(data=normalized, index=df.index)
    raise ValueError("axis=`%s` but expected to be `0` or `1`!" % axis)
