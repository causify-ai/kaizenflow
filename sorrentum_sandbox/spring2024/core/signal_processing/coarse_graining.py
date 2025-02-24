"""
Import as:

import core.signal_processing.coarse_graining as csprcogr
"""

import logging
from typing import Tuple, Union

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def coarse_grain(
    sig: Union[pd.DataFrame, pd.Series],
    depth: int = 1,
    timing_mode: str = "zero_phase",
    output_mode: str = "peaks_and_valleys",
) -> pd.DataFrame:
    """
    Coarse grain a series using multiscale local peaks and valleys.

    :param sig: input signal
    :param depth: the number of coarse graining iterations to perform.
    :param timing_mode: supported timing modes are
      - "knowledge_time"
      - "zero_phase"
    :param output_mode: valid output modes are
      - "peaks"
      - "valleys"
      - "peaks_and_valleys" (the union)
    :return: dataframe of signal peak/valley values. Columns are indexed by
        level.
    """
    sig = hpandas.as_series(sig)
    hdbg.dassert_lte(1, depth)
    peaks = {}
    valleys = {}
    grains = {}
    peak_srs = sig
    valley_srs = sig
    for level in range(1, depth + 1):
        peak_srs, _ = _get_peaks_and_valleys_helper(peak_srs, timing_mode)
        _, valley_srs = _get_peaks_and_valleys_helper(valley_srs, timing_mode)
        peaks[level] = peak_srs.copy()
        valleys[level] = valley_srs.copy()
        grain = peak_srs.add(valley_srs, fill_value=0)
        grains[level] = grain.copy()
    if output_mode == "peaks":
        df = pd.DataFrame(peaks)
    elif output_mode == "valleys":
        df = pd.DataFrame(valleys)
    elif output_mode == "peaks_and_valleys":
        df = pd.DataFrame(grains)
    else:
        raise ValueError(f"Unsupported output_mode `{output_mode}`")
    df = df.reindex(index=sig.index)
    return df


def get_peaks_and_valleys(
    srs: pd.Series,
    level: int = 1,
    timing_mode: str = "zero_phase",
) -> Tuple[pd.Series, pd.Series]:
    """
    Return the `level`-level coarse grained peaks and valleys.
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_lte(1, level)
    peak_srs = srs
    valley_srs = srs
    for level in range(1, level + 1):
        peak_srs, _ = _get_peaks_and_valleys_helper(peak_srs, timing_mode)
        _, valley_srs = _get_peaks_and_valleys_helper(valley_srs, timing_mode)
    return peak_srs, valley_srs


def _get_peaks_and_valleys_helper(
    srs: pd.Series,
    timing_mode: str = "zero_phase",
) -> Tuple[pd.Series, pd.Series]:
    # Check types.
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_isinstance(timing_mode, str)
    # Compute peaks and values.
    peaks = (srs > srs.shift(1)) & (srs > srs.shift(-1))
    valleys = (srs < srs.shift(1)) & (srs < srs.shift(-1))
    # Extract `srs` values at peaks and valleys.
    peak_vals = srs.loc[peaks]
    valley_vals = srs.loc[valleys]
    # Perform timing mode adjustment.
    if timing_mode == "zero_phase":
        pass
    elif timing_mode == "knowledge_time":
        peak_vals = peak_vals.reindex(index=srs.index).shift(1).dropna()
        valley_vals = valley_vals.reindex(index=srs.index).shift(1).dropna()
    else:
        raise ValueError(f"Unsupported timing_mode `{timing_mode}`")
    return peak_vals, valley_vals


def compute_wavelengths(srs: pd.Series, depth: int) -> pd.DataFrame:
    idx = srs.index
    peaks = coarse_grain(srs, depth, "zero_phase", "peaks")
    valleys = coarse_grain(srs, depth, "zero_phase", "valleys")
    peak_wavelengths = peaks.apply(_compute_wavelength_helper)
    valley_wavelengths = valleys.apply(_compute_wavelength_helper)
    wavelengths = peak_wavelengths.add(valley_wavelengths, fill_value=0)
    wavelengths = wavelengths.reindex(index=idx)
    return wavelengths


def _compute_wavelength_helper(srs: pd.Series) -> pd.Series:
    idx = srs.index
    positions = pd.Series(list(range(0, idx.size)), idx)
    non_nan_idx = srs[~srs.isna()].index
    wavelengths = positions.loc[non_nan_idx].diff()
    wavelengths = wavelengths.reindex(index=idx)
    return wavelengths
