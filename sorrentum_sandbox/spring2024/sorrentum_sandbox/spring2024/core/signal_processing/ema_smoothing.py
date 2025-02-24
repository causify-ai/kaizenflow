"""
Import as:

import core.signal_processing.ema_smoothing as cspremsm
"""

import functools
import logging
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

import core.signal_processing.fir_utils as csprfiut
import core.signal_processing.special_functions as csprspfu
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_ema(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int,
    depth: int = 1,
) -> Union[pd.DataFrame, pd.Series]:
    r"""Implement iterated EMA operator (e.g., see 3.3.6 of Dacorogna, et al).

    depth=1 corresponds to a single application of exponential smoothing.

    Greater depth tempers impulse response, introducing a phase lag.

    Dacorogna use the convention $\text{compute_ema}(t) = \exp(-t / \tau) / \tau$.

    If $s_n = \lambda x_n + (1 - \lambda) s_{n - 1}$, where $s_n$ is the compute_ema
    output, then $1 - \lambda = \exp(-1 / \tau)$. Now
    $\lambda = 1 / (1 + \text{com})$, and rearranging gives
    $\log(1 + 1 / \text{com}) = 1 / \tau$. Expanding in a Taylor series
    leads to $\tau \approx \text{com}$.

    The kernel for an compute_ema of depth $n$ is
    $(1 / (n - 1)!) (t / \tau)^{n - 1} \exp^{-t / \tau} / \tau$.

    Arbitrary kernels can be approximated by a combination of iterated emas.

    For an iterated compute_ema with given tau and depth n, we have
      - range = n \tau
      - <t^2> = n(n + 1) \tau^2
      - width = \sqrt{n} \tau
      - aspect ratio = \sqrt{1 + 1 / n}
    """
    hdbg.dassert_isinstance(depth, int)
    hdbg.dassert_lte(1, depth)
    hdbg.dassert_lt(0, tau)
    _LOG.debug("Calculating iterated ema of depth %i", depth)
    _LOG.debug("range = %0.2f", depth * tau)
    _LOG.debug("<t^2>^{1/2} = %0.2f", np.sqrt(depth * (depth + 1)) * tau)
    _LOG.debug("width = %0.2f", np.sqrt(depth) * tau)
    _LOG.debug("aspect ratio = %0.2f", np.sqrt(1 + 1.0 / depth))
    _LOG.debug("tau = %0.2f", tau)
    com = csprspfu.calculate_com_from_tau(tau)
    _LOG.debug("com = %0.2f", com)
    signal_hat = signal.copy()
    for _ in range(0, depth):
        signal_hat = signal_hat.ewm(
            com=com, min_periods=min_periods, adjust=True, ignore_na=False, axis=0
        ).mean()
    return signal_hat


def compute_smooth_derivative(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int,
    scaling: int = 1,
    order: int = 1,
) -> Union[pd.DataFrame, pd.Series]:
    r"""Compute a "low-noise" differential operator.

    'Low-noise' differential operator as in 3.3.9 of Dacorogna, et al.

    - Computes difference of around time "now" over a time interval \tau_1 and
      an average around time "now - \tau" over a time interval \tau_2
    - Here, \tau_1, \tau_2 are taken to be approximately `tau`/ 2

    The normalization factors are chosen so that
      - the differential of a constant is zero
      - the differential (`scaling` = 0) of `t` is approximately `tau`
      - the derivative (`order` = 1) of `t` is approximately 1

    The `scaling` parameter refers to the exponential weighting of inverse
    tau.

    The `order` parameter refers to the number of times the
    compute_smooth_derivative operator is applied to the original signal.
    """
    hdbg.dassert_isinstance(order, int)
    hdbg.dassert_lte(0, order)
    gamma = 1.22208
    beta = 0.65
    alpha = 1.0 / (gamma * (8 * beta - 3))
    _LOG.debug("alpha = %0.2f", alpha)
    tau1 = alpha * tau
    _LOG.debug("tau1 = %0.2f", tau1)
    tau2 = alpha * beta * tau
    _LOG.debug("tau2 = %0.2f", tau2)

    def order_one(
        signal: Union[pd.DataFrame, pd.Series]
    ) -> Union[pd.DataFrame, pd.Series]:
        s1 = compute_ema(signal, tau1, min_periods, 1)
        s2 = compute_ema(signal, tau1, min_periods, 2)
        s3 = -2.0 * compute_ema(signal, tau2, min_periods, 4)
        differential = gamma * (s1 + s2 + s3)
        if scaling == 0:
            return differential
        return differential / (tau**scaling)

    signal_diff = signal.copy()
    for _ in range(0, order):
        signal_diff = order_one(signal_diff)
    return signal_diff


def compute_smooth_moving_average(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
) -> Union[pd.DataFrame, pd.Series]:
    """Implement moving average operator defined in terms of iterated compute_ema's.
    Choosing min_depth > 1 results in a lagged operator.
    Choosing min_depth = max_depth = 1 reduces to a single compute_ema.

    Abrupt impulse response that tapers off smoothly like a sigmoid
    (hence smoother than an equally-weighted moving average).

    For min_depth = 1 and large max_depth, the series is approximately
    constant for t << 2 * range_. In particular, when max_depth >= 5,
    the kernels are more rectangular than compute_ema-like.
    """
    hdbg.dassert_isinstance(min_depth, int)
    hdbg.dassert_isinstance(max_depth, int)
    hdbg.dassert_lte(1, min_depth)
    hdbg.dassert_lte(min_depth, max_depth)
    range_ = tau * (min_depth + max_depth) / 2.0
    _LOG.debug("Range = %0.2f", range_)
    ema_eval = functools.partial(compute_ema, signal, tau, min_periods)
    denom = float(max_depth - min_depth + 1)
    # Not the most efficient implementation, but follows 3.56 of Dacorogna
    # directly.
    return sum(map(ema_eval, range(min_depth, max_depth + 1))) / denom


def extract_smooth_moving_average_weights(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_depth: int = 1,
    max_depth: int = 1,
    index_location: Optional[Any] = None,
) -> pd.DataFrame:
    """
    Return present and historical weights used in SMA up to `index_location`.

    The results are approximate, since the underlying weight extract technique
    is only exact for FIR filters.

    :param signal: as in `extract_fir_filter_weights()`
    :param tau: as in `compute_smooth_moving_average()`
    :param min_depth: as in `compute_smooth_moving_average()`
    :param max_depth: as in `compute_smooth_moving_average()`
    :param index_location: as in `extract_fir_filter_weights()`
    :return: as in `extract_fir_filter_weights()`
    """
    hdbg.dassert_lt(0, tau)
    range_ = tau * (min_depth + max_depth) / 2.0
    warmup_length = int(np.round(10 * range_))
    weights = csprfiut.extract_fir_filter_weights(
        signal,
        func=compute_smooth_moving_average,
        func_kwargs={"tau": tau, "min_depth": min_depth, "max_depth": max_depth},
        warmup_length=warmup_length,
        index_location=index_location,
    )
    return weights


# #############################################################################
# Rolling moments, norms, z-scoring, demeaning, etc.
# #############################################################################


def compute_rolling_moment(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    return compute_smooth_moving_average(
        np.abs(signal) ** p_moment, tau, min_periods, min_depth, max_depth
    )


def compute_rolling_norm(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
    delay: float = 0,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Implement smooth moving average norm (when p_moment >= 1).

    Moving average corresponds to compute_ema when min_depth = max_depth = 1.
    """
    hdbg.dassert_lte(0, delay, "Requested delay=%i is non-causal.", delay)
    signal = signal.shift(delay)
    signal_p = compute_rolling_moment(
        signal, tau, min_periods, min_depth, max_depth, p_moment
    )
    return signal_p ** (1.0 / p_moment)


def compute_rolling_var(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Implement smooth moving average central moment.

    Moving average corresponds to compute_ema when min_depth = max_depth = 1.
    """
    signal_ma = compute_smooth_moving_average(
        signal, tau, min_periods, min_depth, max_depth
    )
    return compute_rolling_moment(
        signal - signal_ma, tau, min_periods, min_depth, max_depth, p_moment
    )


def compute_rolling_std(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Implement normalized smooth moving average central moment.

    Moving average corresponds to compute_ema when min_depth = max_depth = 1.
    """
    signal_tmp = compute_rolling_var(
        signal, tau, min_periods, min_depth, max_depth, p_moment
    )
    return signal_tmp ** (1.0 / p_moment)


def compute_rolling_demean(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Demean signal on a rolling basis with compute_smooth_moving_average.
    """
    signal_ma = compute_smooth_moving_average(
        signal, tau, min_periods, min_depth, max_depth
    )
    return signal - signal_ma


def compute_rolling_zscore(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
    demean: bool = True,
    delay: int = 0,
    atol: float = 0,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Z-score using compute_smooth_moving_average and compute_rolling_std.

    If delay > 0, then pay special attention to 0 and NaN handling to avoid
    extreme values.

    Moving average corresponds to compute_ema when min_depth = max_depth = 1.

    If denominator.abs() <= atol, Z-score value is set to np.nan in order to
    avoid extreme value spikes.

    TODO(Paul): determine whether signal == signal.shift(0) always.
    """
    if demean:
        # Equivalent to invoking compute_rolling_demean and compute_rolling_std, but
        # this way we avoid calculating signal_ma twice.
        signal_ma = compute_smooth_moving_average(
            signal, tau, min_periods, min_depth, max_depth
        )
        signal_std = compute_rolling_norm(
            signal - signal_ma, tau, min_periods, min_depth, max_depth, p_moment
        )
        numerator = signal - signal_ma.shift(delay)
    else:
        signal_std = compute_rolling_norm(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        numerator = signal
    denominator = signal_std.shift(delay)
    denominator[denominator.abs() <= atol] = np.nan
    ret = numerator / denominator
    return ret


def compute_rolling_skew(
    signal: Union[pd.DataFrame, pd.Series],
    tau_z: float,
    tau_s: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Smooth moving average skew of z-scored signal.
    """
    z_signal = compute_rolling_zscore(
        signal, tau_z, min_periods, min_depth, max_depth, p_moment
    )
    skew = compute_smooth_moving_average(
        z_signal**3, tau_s, min_periods, min_depth, max_depth
    )
    return skew


def compute_rolling_kurtosis(
    signal: Union[pd.DataFrame, pd.Series],
    tau_z: float,
    tau_s: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Smooth moving average kurtosis of z-scored signal.
    """
    z_signal = compute_rolling_zscore(
        signal, tau_z, min_periods, min_depth, max_depth, p_moment
    )
    kurt = compute_smooth_moving_average(
        z_signal**4, tau_s, min_periods, min_depth, max_depth
    )
    return kurt


# #############################################################################
# Rolling Sharpe ratio
# #############################################################################


def compute_rolling_annualized_sharpe_ratio(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    points_per_year: float,
    min_periods: int = 2,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Compute rolling annualized Sharpe ratio and standard error.

    The standard error adjustment uses the range of the smooth moving
    average kernel as an estimate of the "number of data points" used in
    the calculation of the Sharpe ratio.
    """
    sr = compute_rolling_sharpe_ratio(
        signal, tau, min_periods, min_depth, max_depth, p_moment
    )
    # TODO(*): May need to rescale denominator by a constant.
    se_sr = np.sqrt((1 + (sr**2) / 2) / (tau * max_depth))
    rescaled_sr = np.sqrt(points_per_year) * sr
    rescaled_se_sr = np.sqrt(points_per_year) * se_sr
    df = pd.DataFrame(index=signal.index)
    df["annualized_SR"] = rescaled_sr
    df["annualized_SE(SR)"] = rescaled_se_sr
    return df


def compute_rolling_sharpe_ratio(
    signal: Union[pd.DataFrame, pd.Series],
    tau: float,
    min_periods: int = 2,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Sharpe ratio using compute_smooth_moving_average and compute_rolling_std.
    """
    signal_ma = compute_smooth_moving_average(
        signal, tau, min_periods, min_depth, max_depth
    )
    # Use `zero` as the mean in the standard deviation calculation.
    signal_std = compute_rolling_norm(
        signal, tau, min_periods, min_depth, max_depth, p_moment
    )
    return signal_ma / signal_std


# #############################################################################
# Rolling correlation functions
# #############################################################################


# TODO(Paul): Change the interface so that the two series are cols of a df.
def compute_rolling_cov(
    srs1: Union[pd.DataFrame, pd.Series],
    srs2: Union[pd.DataFrame, pd.Series],
    tau: float,
    demean: bool = True,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Smooth moving covariance.
    """
    if demean:
        srs1_adj = srs1 - compute_smooth_moving_average(
            srs1, tau, min_periods, min_depth, max_depth
        )
        srs2_adj = srs2 - compute_smooth_moving_average(
            srs2, tau, min_periods, min_depth, max_depth
        )
    else:
        srs1_adj = srs1
        srs2_adj = srs2
    smooth_prod = compute_smooth_moving_average(
        srs1_adj.multiply(srs2_adj), tau, min_periods, min_depth, max_depth
    )
    return smooth_prod


def compute_rolling_corr(
    srs1: Union[pd.DataFrame, pd.Series],
    srs2: Union[pd.DataFrame, pd.Series],
    tau: float,
    demean: bool = True,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Smooth moving correlation.
    """
    if demean:
        srs1_adj = srs1 - compute_smooth_moving_average(
            srs1, tau, min_periods, min_depth, max_depth
        )
        srs2_adj = srs2 - compute_smooth_moving_average(
            srs2, tau, min_periods, min_depth, max_depth
        )
    else:
        srs1_adj = srs1
        srs2_adj = srs2
    smooth_prod = compute_smooth_moving_average(
        srs1_adj.multiply(srs2_adj), tau, min_periods, min_depth, max_depth
    )
    srs1_std = compute_rolling_norm(
        srs1_adj, tau, min_periods, min_depth, max_depth, p_moment
    )
    srs2_std = compute_rolling_norm(
        srs2_adj, tau, min_periods, min_depth, max_depth, p_moment
    )
    return smooth_prod / (srs1_std * srs2_std)


def compute_rolling_zcorr(
    srs1: Union[pd.DataFrame, pd.Series],
    srs2: Union[pd.DataFrame, pd.Series],
    tau: float,
    demean: bool = True,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Z-score srs1, srs2 then calculate moving average of product.

    Not guaranteed to lie in [-1, 1], but bilinear in the z-scored
    variables.
    """
    if demean:
        z_srs1 = compute_rolling_zscore(
            srs1, tau, min_periods, min_depth, max_depth, p_moment
        )
        z_srs2 = compute_rolling_zscore(
            srs2, tau, min_periods, min_depth, max_depth, p_moment
        )
    else:
        z_srs1 = srs1 / compute_rolling_norm(
            srs1, tau, min_periods, min_depth, max_depth, p_moment
        )
        z_srs2 = srs2 / compute_rolling_norm(
            srs2, tau, min_periods, min_depth, max_depth, p_moment
        )
    return compute_smooth_moving_average(
        z_srs1.multiply(z_srs2), tau, min_periods, min_depth, max_depth
    )


def get_dyadic_zscored(
    sig: pd.Series, demean: bool = False, **kwargs: Any
) -> pd.DataFrame:
    """
    Z-score `sig` with successive powers of 2.

    :return: dataframe with cols named according to the exponent of 2. Number
        of cols is determined based on signal length.
    """
    pow2_ceil = int(np.ceil(np.log2(sig.size)))
    zscored = {}
    for tau_pow in range(1, pow2_ceil):
        zscored[tau_pow] = compute_rolling_zscore(
            sig, tau=2**tau_pow, demean=demean, **kwargs
        )
    df = pd.DataFrame.from_dict(zscored)
    return df


def get_trend_residual_decomp(
    signal: pd.Series,
    tau: float,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    nan_mode: Optional[str] = None,
) -> pd.DataFrame:
    """
    Decompose a signal into trend + residual.

    - The `trend` warm-up period is set by `min_periods`
    - If `min_periods` is positive, then leading values of `trend` are NaN
      - If `nan_mode = "propagate"`, then `residual` and `trend` are Nan
        whenever at least one is
      - If `nan_mode = "restore_to_residual", then `residual` is always non-NaN
        whenever `residual` is
        - E.g., so, in particular, during any `trend` warm-up period,
          `signal = residual` and `signal = trend + residual` always holds
        - However, when the warm-up phase ends, `residual` may experience a
          large jump

    :return: dataframe with columns "trend" and "residual", indexed like
        "signal"
    """
    if nan_mode is None:
        nan_mode = "propagate"
    signal_ma = compute_smooth_moving_average(
        signal, tau, min_periods, min_depth, max_depth
    )
    df = pd.DataFrame(index=signal.index)
    df["trend"] = signal_ma
    detrended = signal - signal_ma
    if nan_mode == "restore_to_residual":
        # Restore `signal` values if `detrended` is NaN due to detrending artifacts
        # (e.g., from setting `min_periods`).
        detrended.loc[detrended.isna()] = signal
    elif nan_mode == "propagate":
        pass
    else:
        raise ValueError(f"Unrecognized nan_mode `{nan_mode}`")
    df["residual"] = detrended
    return df
