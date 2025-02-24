"""
Import as:

import core.signal_processing.swt as csiprswt
"""

import functools
import logging
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pywt

import core.signal_processing.fir_utils as csprfiut
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def get_swt(
    sig: Union[pd.DataFrame, pd.Series],
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
    output_mode: Optional[str] = None,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Get stationary wt details and smooths for all available scales.

    If sig.index.freq == "B", then there is the following rough correspondence
    between wavelet levels and time scales:
      weekly ~ 2-3
      monthly ~ 4-5
      quarterly ~ 6
      annual ~ 8
      business cycle ~ 11

    If sig.index.freq == "T", then the approximate scales are:
      5 min ~ 2-3
      quarter hourly ~ 4
      hourly ~ 6
      daily ~ 10-11

    :param sig: input signal
    :param wavelet: pywt wavelet name, e.g., "db8";
        see all available names by invoking `pywt.wavelist()`;
        see all available families by invoking `pywt.families()`.
    :param depth: the number of decomposition steps to perform. Corresponds to
        "level" parameter in `pywt.swt`
    :param timing_mode: supported timing modes are
        - "knowledge_time":
            - reindex transform according to knowledge times
            - remove warm-up artifacts
        - "zero_phase":
            - no reindexing (e.g., no phase lag in output, but transform
              timestamps are not necessarily knowledge times)
            - remove warm-up artifacts
        - "raw": `pywt.swt` as-is
    :param output_mode: valid output modes are
        - "tuple": return (smooth_df, detail_df)
        - "smooth": return smooth_df
        - "detail": return detail_df
        - "detail_and_last_smooth": detail and `depth` smooth, as one dataframe
    :return: see `output_mode`
    """
    # Choice of wavelet may significantly impact results.
    wavelet = wavelet or "haar"
    # _LOG.debug("wavelet=`%s`", wavelet)
    sig = hpandas.as_series(sig)
    if timing_mode is None:
        timing_mode = "knowledge_time"
    # _LOG.debug("timing_mode=`%s`", timing_mode)
    if output_mode is None:
        output_mode = "tuple"
    # _LOG.debug("output_mode=`%s`", output_mode)
    smooth_df, detail_df = pad_compute_swt_and_trim(sig, wavelet, depth)
    levels = detail_df.shape[1]
    # Record wavelet width (required for removing warm-up artifacts).
    # width = len(pywt.Wavelet(wavelet).filter_bank[0])
    width = pywt.Wavelet(wavelet).dec_len
    # _LOG.debug("wavelet width=%s", width)
    if timing_mode == "knowledge_time":
        for j in range(1, levels + 1):
            # Remove "warm-up" artifacts.
            _set_warmup_region_to_nan(detail_df[j], width, j)
            _set_warmup_region_to_nan(smooth_df[j], width, j)
            # Index by knowledge time.
            detail_df[j] = _reindex_by_knowledge_time(detail_df[j], width, j)
            smooth_df[j] = _reindex_by_knowledge_time(smooth_df[j], width, j)
    elif timing_mode == "zero_phase":
        for j in range(1, levels + 1):
            # Delete "warm-up" artifacts.
            _set_warmup_region_to_nan(detail_df[j], width, j)
            _set_warmup_region_to_nan(smooth_df[j], width, j)
    elif timing_mode == "raw":
        pass
    else:
        raise ValueError(f"Unsupported timing_mode `{timing_mode}`")
    # Drop columns that are all-NaNs (e.g., artifacts of padding).
    smooth_df.dropna(how="all", axis=1, inplace=True)
    detail_df.dropna(how="all", axis=1, inplace=True)
    if depth:
        cols = set(range(1, depth + 1))
        msg = "Insufficient data to generate transform up to requested depth."
        if not cols.issubset(smooth_df.columns):
            raise ValueError(msg)
        if not cols.issubset(detail_df.columns):
            raise ValueError(msg)
    if output_mode == "tuple":
        return smooth_df, detail_df
    if output_mode == "smooth":
        return smooth_df
    if output_mode == "detail":
        return detail_df
    if output_mode == "detail_and_last_smooth":
        effective_levels = smooth_df.columns.size
        hdbg.dassert_in(effective_levels, smooth_df.columns)
        detail_df[f"{effective_levels}_smooth"] = smooth_df[effective_levels]
        return detail_df
    raise ValueError(f"Unsupported output_mode `{output_mode}`")


def get_swt_level(
    sig: Union[pd.DataFrame, pd.Series],
    level: int,
    wavelet: Optional[str] = None,
    timing_mode: Optional[str] = None,
    output_mode: Optional[str] = None,
) -> pd.Series:
    """
    Wraps `get_swt` and extracts a single wavelet level.

    :param sig: input signal
    :param level: the wavelet level to extract
    :param wavelet: pywt wavelet name, e.g., "db8"
    :param timing_mode: supported timing modes are
        - "knowledge_time":
            - reindex transform according to knowledge times
            - remove warm-up artifacts
        - "zero_phase":
            - no reindexing (e.g., no phase lag in output, but transform
              timestamps are not necessarily knowledge times)
            - remove warm-up artifacts
        - "raw": `pywt.swt` as-is
    :param output_mode: valid output modes are
        - "smooth": return smooth_df for `level`
        - "detail": return detail_df for `level`
    :return: see `output_mode`
    """
    hdbg.dassert_in(output_mode, ["smooth", "detail"])
    swt = get_swt(
        sig,
        wavelet=wavelet,
        depth=level,
        timing_mode=timing_mode,
        output_mode=output_mode,
    )
    hdbg.dassert_in(level, swt.columns)
    return swt[level]


def apply_swt(
    sig: pd.DataFrame,
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
    output_mode: Optional[str] = None,
) -> pd.DataFrame:
    hdbg.dassert_isinstance(sig, pd.DataFrame)
    if output_mode is None or output_mode == "tuple":
        raise AssertionError("Unsupported `output_mode`=%s" % str(output_mode))
    dfs = []
    for col in sig.columns:
        df = get_swt(sig[col], wavelet, depth, timing_mode, output_mode)
        df = df.rename(columns=lambda x: str(col) + "_" + str(x))
        dfs.append(df)
    df = pd.concat(dfs, axis=1)
    return df


def get_mra_renormalization_srs(depth: int) -> pd.Series:
    detail_levels = range(1, depth + 1)
    renorm_srs = pd.Series([2 ** (j / 2) for j in detail_levels], detail_levels)
    renorm_srs[f"{depth}_smooth"] = renorm_srs[depth]
    return renorm_srs


def compute_and_combine_swt_levels(
    sig: pd.Series,
    weights: List[int],
    *,
    norm: bool = True,
) -> pd.Series:
    depth = len(weights) - 1
    swt = get_swt(sig, "haar", depth, output_mode="detail_and_last_smooth")
    level_idx = swt.columns
    weight_srs = pd.Series(
        weights,
        level_idx,
    )
    if not norm:
        renorm_srs = get_mra_renormalization_srs(depth)
        weight_srs *= renorm_srs
    combined = (swt * weight_srs).sum(axis=1, skipna=False)
    combined.name = sig.name
    return combined


def compute_lag_weights(
    weights: List[int],
    *,
    norm: bool = True,
) -> pd.Series:
    depth = len(weights) - 1
    warmup_length = (
        get_knowledge_time_warmup_lengths(["haar"], depth).loc[depth].squeeze()
    )
    srs = pd.Series([0] * (2 * warmup_length))
    #
    func = functools.partial(compute_and_combine_swt_levels, norm=norm)
    filter_weights = csprfiut.extract_fir_filter_weights(
        srs, func, {"weights": weights}, warmup_length + 1
    )
    filter_weights = filter_weights["normalized_weight"][::-1].reset_index(
        drop=True
    )
    filter_weights.index.name = "lag"
    zero_pad = filter_weights.loc[2**depth :]
    hdbg.dassert_eq(zero_pad.abs().sum(), 0)
    return filter_weights.loc[: 2**depth - 1]


# #############################################################################
# Low/high pass filters
# #############################################################################


def compute_swt_low_pass(
    sig: Union[pd.DataFrame, pd.Series],
    level: int,
    wavelet: Optional[str] = None,
    timing_mode: Optional[str] = None,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Perform a FIR low-pass filtering using the `level` swt smooth.
    """
    if isinstance(sig, pd.Series):
        return _compute_swt_low_pass(
            sig,
            level,
            wavelet,
            timing_mode,
        )
    df = sig.apply(
        lambda x: _compute_swt_low_pass(
            x,
            level,
            wavelet,
            timing_mode,
        )
    )
    return df


def _compute_swt_low_pass(
    sig: Union[pd.DataFrame, pd.Series],
    level: int,
    wavelet: Optional[str] = None,
    timing_mode: Optional[str] = None,
) -> pd.Series:
    sig = hpandas.as_series(sig)
    signal_name = sig.name
    low_freq = get_swt_level(sig, level, wavelet, timing_mode, "smooth")
    low_freq.name = signal_name
    return low_freq


def compute_swt_high_pass(
    sig: Union[pd.DataFrame, pd.Series],
    level: int,
    wavelet: Optional[str] = None,
    timing_mode: Optional[str] = None,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Perform a FIR high-pass filtering by subtracting the `level` swt smooth.
    """
    if isinstance(sig, pd.Series):
        return _compute_swt_high_pass(
            sig,
            level,
            wavelet,
            timing_mode,
        )
    df = sig.apply(
        lambda x: _compute_swt_high_pass(
            x,
            level,
            wavelet,
            timing_mode,
        )
    )
    return df


def _compute_swt_high_pass(
    sig: Union[pd.DataFrame, pd.Series],
    level: int,
    wavelet: str = "haar",
    timing_mode: Optional[str] = None,
) -> pd.Series:
    sig = hpandas.as_series(sig)
    signal_name = sig.name
    low_freq = compute_swt_low_pass(sig, level, wavelet, timing_mode)
    # Remove the low frequency component.
    high_freq = sig - low_freq
    high_freq.name = signal_name
    return high_freq


# #############################################################################
# Wavelet properties
# #############################################################################


def get_knowledge_time_warmup_lengths(
    wavelets: List[str],
    depth: int,
) -> pd.Series:
    """
    Return knowledge-time warm-up lengths required.

    Stratified by wavelet name and level.
    """
    hdbg.dassert_container_type(wavelets, list, str)
    hdbg.dassert_isinstance(depth, int)
    hdbg.dassert_lt(0, depth)
    wavelet_warmups = []
    for wavelet in wavelets:
        width = len(pywt.Wavelet(wavelet).filter_bank[0])
        lengths = {}
        for level in range(1, depth + 1):
            length = 2 * _get_artifact_length(width, level)
            lengths[level] = length
        srs = pd.Series(lengths, name=wavelet)
        srs.index.name = "level"
        wavelet_warmups.append(srs)
    df = pd.concat(wavelet_warmups, axis=1)
    df.columns.name = "wavelet"
    return df


def summarize_wavelet(wavelet: pywt.Wavelet) -> pd.Series:
    """
    Summarize wavelet properties of frequent interest.
    """
    hdbg.dassert_isinstance(wavelet, pywt.Wavelet)
    _LOG.debug("wavelet=%s", wavelet)
    dict_ = {
        "family_name": wavelet.family_name,
        "short_family_name": wavelet.short_family_name,
        "family_number": wavelet.family_number,
        "name": wavelet.name,
        "number": wavelet.number,
        "orthogonal": wavelet.orthogonal,
        "biorthogonal": wavelet.biorthogonal,
        "symmetry": wavelet.symmetry,
        "vanishing_moments_phi": wavelet.vanishing_moments_phi,
        "vanishing_moments_psi": wavelet.vanishing_moments_psi,
        "width": len(wavelet.filter_bank[0]),
    }
    srs = pd.Series(dict_)
    return srs


def summarize_discrete_wavelets() -> pd.DataFrame:
    """
    Summarize properties of all available discrete wavelets.
    """
    wavelist = pywt.wavelist(kind="discrete")
    _LOG.debug("discrete wavelist=%s", wavelist)
    wavelet_summaries = []
    for wavelet_name in wavelist:
        wavelet = pywt.Wavelet(wavelet_name)
        wavelet_summary = summarize_wavelet(wavelet)
        wavelet_summaries.append(wavelet_summary)
    df = pd.concat(wavelet_summaries, axis=1).T
    return df


# #############################################################################
# Helpers.
# #############################################################################


def pad_compute_swt_and_trim(
    sig: pd.Series,
    wavelet: str,
    level: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Pad `sig` so that its length is a power of 2, apply swt, and trim.

    :param sig: pd.Series of data
    :param wavelet: as in `pywt.swt`
    :param level: as in `pywt.swt`
    :return: tuple of smooth and detail dataframes
    """
    hdbg.dassert_isinstance(sig, pd.Series)
    # Convert to numpy and pad, since the pywt swt implementation
    # requires that the input be a power of 2 in length.
    sig_len = sig.size
    padded = _pad_to_pow_of_2(sig.values)
    # Perform the wavelet decomposition.
    decomp = pywt.swt(padded, wavelet=wavelet, level=level, norm=True)
    # Ensure we have at least one level.
    levels = len(decomp)
    # _LOG.debug("levels=%d", levels)
    hdbg.dassert_lt(0, levels)
    # Reorganize wavelet coefficients. `pywt.swt` output is of the form
    #     [(cAn, cDn), ..., (cA2, cD2), (cA1, cD1)]
    smooth, detail = zip(*reversed(decomp))
    # Reorganize `swt` output into a dataframe
    # - columns indexed by `int` wavelet level (1 up to `level`)
    # - index identical to `sig.index` (padded portion deleted)
    detail_dict = {}
    smooth_dict = {}
    for level in range(1, levels + 1):
        detail_dict[level] = detail[level - 1][:sig_len]
        smooth_dict[level] = smooth[level - 1][:sig_len]
    detail_df = pd.DataFrame.from_dict(data=detail_dict)
    detail_df.index = sig.index
    smooth_df = pd.DataFrame.from_dict(data=smooth_dict)
    smooth_df.index = sig.index
    return smooth_df, detail_df


def _get_artifact_length(
    width: int,
    level: int,
) -> int:
    """
    Get artifact length based on wavelet width and level.

    :width: width (length of support of mother wavelet)
    :level: wavelet level
    :return: length of required warm-up period
    """
    # See Sec 5.11. Compare to
    # (width - 1) * (2 ** level - 1) - 1.
    length = width * 2 ** (level - 1) - width // 2
    return length


def _pad_to_pow_of_2(arr: np.array) -> np.array:
    """
    Minimally extend `arr` with zeros so that len is a power of 2.
    """
    arr_len = arr.shape[0]
    # _LOG.debug("array length=%d", arr_len)
    pow2_ceil = int(2 ** np.ceil(np.log2(arr_len)))
    padded = np.pad(arr, (0, pow2_ceil - arr_len))
    # _LOG.debug("padded array length=%d", len(padded))
    return padded


def _set_warmup_region_to_nan(srs: pd.Series, width: int, level: int) -> None:
    """
    Remove warm-up artifacts by setting to `NaN`.

    NOTE: Modifies `srs` in-place.

    :srs: swt
    :width: width (length of support of mother wavelet)
    :level: wavelet level
    """
    warmup_region = _get_artifact_length(width, level)
    srs.iloc[:warmup_region] = np.nan


def _reindex_by_knowledge_time(
    srs: pd.Series, width: int, level: int
) -> pd.Series:
    """
    Shift series so that indexing is according to knowledge time.

    :srs: swt
    :width: width (length of support of mother wavelet)
    :level: wavelet level
    """
    warmup_region = _get_artifact_length(width, level)
    return srs.shift(warmup_region)


# #############################################################################
# Wavelet variance/covariance
# #############################################################################


def compute_swt_var(
    sig: Union[pd.DataFrame, pd.Series],
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
    axis: int = 1,
) -> pd.DataFrame:
    """
    Get swt var using levels up to `depth`.

    Params as in `get_swt()`.
    """
    if isinstance(sig, pd.Series):
        sig = sig.to_frame()
    hdbg.dassert_eq(len(sig.columns), 1)
    col = sig.columns[0]
    df = compute_swt_covar(
        sig,
        col1=col,
        col2=col,
        wavelet=wavelet,
        depth=depth,
        timing_mode=timing_mode,
        axis=axis,
    )
    hdbg.dassert_in("swt_var", df.columns)
    return df


def compute_swt_covar(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
    axis: int = 1,
) -> pd.DataFrame:
    """
    Get swt covar using details up to `depth`.

    Params as in `get_swt()`.
    """
    dfs = {}
    for col in [col1, col2]:
        dfs[col] = get_swt(
            df[col],
            wavelet=wavelet,
            depth=depth,
            timing_mode=timing_mode,
            output_mode="detail",
        )
    # Take the level-wise product.
    prod = dfs[col1].multiply(dfs[col2])
    fvi = prod.first_valid_index()
    col1_df = dfs[col1].loc[fvi:]
    col2_df = dfs[col2].loc[fvi:]
    if axis == 0:
        prod = prod.dropna()
        col1_df = col1_df.dropna()
        col2_df = col2_df.dropna()
    results = []
    covar_name = "swt_covar" if col1 != col2 else "swt_var"
    covar = prod.sum(axis=axis, skipna=False).rename(covar_name)
    results.append(covar)
    if col1 != col2:
        col1_var = (
            np.square(col1_df)
            .sum(axis=axis, skipna=False)
            .rename(str(col1) + "_swt_var")
        )
        results.append(col1_var)
        col2_var = (
            np.square(col2_df)
            .sum(axis=axis, skipna=False)
            .rename(str(col2) + "_swt_var")
        )
        results.append(col2_var)
        corr = covar.divide(np.sqrt(col1_var.multiply(col2_var))).rename(
            "swt_corr"
        )
        results.append(corr)
    return pd.concat(results, axis=1)


# TODO(*): Make this a decorator.
def compute_fir_zscore(
    signal: Union[pd.DataFrame, pd.Series],
    dyadic_tau: int,
    demean: bool = True,
    variance_delay: int = 0,
    wavelet: Optional[str] = None,
) -> pd.DataFrame:
    """
    Z-score with a FIR filter.

    :param signal: a series of dataframe of series
    :param dyadic_tau: a larger number means more smoothing and a longer
        lookback
    :param demean: demean before variance-adjusting; set to `False` if, e.g.,
        there are prior reasons to suppose the true mean of `signal` is zero
    :param variance_delay: amount by which to lag the variance adjustment
    :param wavelet: wavelet to use in filtering
    :return: a dataframe (single-column if the input was a series)
    """
    if isinstance(signal, pd.Series):
        return _compute_fir_zscore(
            signal,
            dyadic_tau,
            demean,
            variance_delay,
            wavelet,
        )
    df = signal.apply(
        lambda x: _compute_fir_zscore(
            x,
            dyadic_tau,
            demean,
            variance_delay,
            wavelet,
        )
    )
    return df


def _compute_fir_zscore(
    signal: Union[pd.DataFrame, pd.Series],
    dyadic_tau: int,
    demean: bool = True,
    variance_delay: int = 0,
    wavelet: Optional[str] = None,
) -> pd.Series:
    """
    Z-score with a FIR filter.

    Demeaning (if selected) is performed using a high-pass filter. Variance
    for z-scoring is computed using a low-pass filter.

    TODO(Paul): Adjust scaling depending upon `wavelet`.
    """
    signal = hpandas.as_series(signal)
    if demean:
        _LOG.debug("Demeaning signal...")
        signal = compute_swt_high_pass(signal, dyadic_tau, wavelet)
    var = compute_swt_low_pass(
        signal**2,
        dyadic_tau,
        wavelet,
    ).shift(variance_delay)
    # TODO(Paul): Maybe add delay-based rescaling.
    srs = signal / np.sqrt(var)
    srs = srs.replace([-np.inf, np.inf], np.nan)
    return srs


def compute_zscored_mra(
    sig: Union[pd.DataFrame, pd.Series],
    depth: int,
) -> pd.DataFrame:
    swt = get_swt(sig, depth=depth, output_mode="detail_and_last_smooth")
    var = get_swt(sig**2, depth=depth + 1, output_mode="smooth")
    detail_levels = range(1, depth + 1)
    shift_srs = get_knowledge_time_warmup_lengths(["haar"], depth + 1)["haar"]
    mra = pd.DataFrame()
    for level in detail_levels:
        mra[level] = swt[level] / np.sqrt(var[level + 1]).shift(shift_srs[level])
    mra[f"{depth}_smooth"] = swt[f"{depth}_smooth"] / np.sqrt(
        var[depth + 1]
    ).shift(shift_srs[depth + 1])
    renorm_srs = get_mra_renormalization_srs(depth)
    mra *= renorm_srs
    return mra


def compute_swt_var_summary(
    sig: Union[pd.DataFrame, pd.Series],
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute swt var using scales up to `depth`.

    Params as in `csigproc.get_swt()`.
    """
    swt_var = compute_swt_var(
        sig, wavelet=wavelet, depth=depth, timing_mode=timing_mode, axis=0
    )
    hdbg.dassert_in("swt_var", swt_var.columns)
    # Use the "cross-sectional" var calculation to determine the first index
    # valid for all levels up to `depth`.
    srs = compute_swt_var(
        sig, wavelet=wavelet, depth=depth, timing_mode=timing_mode, axis=1
    )
    fvi = srs.first_valid_index()
    # Normalize by the number of non-NaN observations.
    decomp = swt_var / srs.loc[fvi:].count()
    decomp["cum_swt_var"] = decomp["swt_var"].cumsum()
    decomp["perc"] = decomp["swt_var"] / sig.loc[fvi:].var()
    decomp["cum_perc"] = decomp["perc"].cumsum()
    return decomp


def compute_swt_covar_summary(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    wavelet: Optional[str] = None,
    depth: Optional[int] = None,
    timing_mode: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute swt var using scales up to `depth`.

    Params as in `csigproc.get_swt()`.
    """
    hdbg.dassert_ne(col1, col2)
    swt_covar = compute_swt_covar(
        df,
        col1,
        col2,
        wavelet=wavelet,
        depth=depth,
        timing_mode=timing_mode,
        axis=0,
    )
    hdbg.dassert_in("swt_covar", swt_covar.columns)
    srs = compute_swt_covar(
        df,
        col1,
        col2,
        wavelet=wavelet,
        depth=depth,
        timing_mode=timing_mode,
        axis=1,
    )
    fvi = srs.first_valid_index()
    decomp = swt_covar / srs.loc[fvi:].count()
    var1_col = str(col1) + "_swt_var"
    var2_col = str(col2) + "_swt_var"
    hdbg.dassert_in(var1_col, decomp.columns)
    hdbg.dassert_in(var2_col, decomp.columns)
    decomp["swt_corr"] = decomp["swt_covar"].divide(
        np.sqrt(decomp[var1_col].multiply(decomp[var2_col]))
    )
    return decomp
