"""
Import as:

import core.signal_processing.misc_transformations as csprmitr
"""

import logging
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compress_tails(
    signal: Union[pd.DataFrame, pd.Series],
    scale: float = 1,
    rescale: float = 1,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Apply compression to data.

    :param signal: data
    :param scale: Divide data by scale and multiply compressed output by scale.
        Rescaling approximately preserves behavior in a neighborhood of the
        origin where the compression function is approximately linear.
    :param rescale: multiplier to apply prior to scaling and compression. This
        rescaling is not undone after the compression.
    :return: compressed data
    """
    hdbg.dassert_lt(0, scale)
    hdbg.dassert_lt(0, rescale)
    if rescale != 1:
        signal = rescale * signal
    return scale * np.tanh(signal / scale)


def discretize(
    signal: pd.Series, bin_boundaries: list, bin_values: list
) -> pd.Series:
    """
    Discretize `signal` into bins (`bin_boundaries`) with `bin_values`.
    """
    hdbg.dassert_isinstance(signal, pd.Series)
    hdbg.dassert_eq(len(bin_boundaries) - 1, len(bin_values))
    idx = signal.index
    # Drop NaNs to avoid numpy's NaN handling in `np.digitize()`.
    signal = signal.dropna()
    binned_signal = np.digitize(signal, bin_boundaries)
    discretized_signal = [bin_values[x - 1] for x in binned_signal]
    discretized_signal = pd.Series(
        discretized_signal, signal.index, name=signal.name
    )
    # Add back any NaNs.
    discretized_signal = discretized_signal.reindex(idx)
    return discretized_signal


def get_symmetric_equisized_bins(
    signal: pd.Series, bin_size: float, zero_in_bin_interior: bool = False
) -> np.array:
    """
    Get bins of equal size, symmetric about zero, adapted to `signal`.

    :param bin_size: width of bin
    :param zero_in_bin_interior: Determines whether `0` is a bin edge or not.
        If in interior, it is placed in the center of the bin.
    :return: array of bin boundaries
    """
    # Remove +/- inf for the purpose of calculating max/min.
    finite_signal = signal.replace([-np.inf, np.inf], np.nan).dropna()
    # Determine minimum and maximum bin boundaries based on values of `signal`.
    # Make them symmetric for simplicity.
    left = np.floor(finite_signal.min() / bin_size).astype(int) - 1
    right = np.ceil(finite_signal.max() / bin_size).astype(int) + 1
    bin_boundary = bin_size * np.maximum(np.abs(left), np.abs(right))
    if zero_in_bin_interior:
        right_start = bin_size / 2
    else:
        right_start = 0
    right_bins = np.arange(right_start, bin_boundary, bin_size)
    # Reflect `right_bins` to get `left_bins`.
    if zero_in_bin_interior:
        left_bins = -np.flip(right_bins)
    else:
        left_bins = -np.flip(right_bins[1:])
    # Combine `left_bins` and `right_bin` into one bin.
    return np.append(left_bins, right_bins)


def digitize(signal: pd.Series, bins: np.array, right: bool = False) -> pd.Series:
    """
    Digitize (i.e., discretize) `signal` into `bins`.

    - In the output, bins are referenced with integers and are such that `0`
      always belongs to bin `0`
    - The bin-referencing convention is optimized for studying signals centered
      at zero (e.g., returns, z-scored features, etc.)
    - For bins of equal size, the bin-referencing convention makes it easy to
      map back from the digitized signal to numerical ranges given
        - the bin number
        - the bin size

    :param bins: array-like bin boundaries. Must include max and min `signal`
        values.
    :param right: same as in `np.digitize`
    :return: digitized signal
    """
    # From https://docs.scipy.org/doc/numpy/reference/generated/numpy.digitize.html
    # (v 1.17):
    # > If values in x are beyond the bounds of bins, 0 or len(bins) is
    # > returned as appropriate.
    digitized = np.digitize(signal, bins, right)
    # Center so that `0` belongs to bin "0"
    bin_containing_zero = np.digitize([0], bins, right)
    digitized -= bin_containing_zero
    # Convert to pd.Series, since `np.digitize` only returns an np.array.
    digitized_srs = pd.Series(
        data=digitized, index=signal.index, name=signal.name
    )
    return digitized_srs


def _wrap(signal: pd.Series, num_cols: int) -> pd.DataFrame:
    """
    Convert a 1-d series into a 2-d dataframe left-to-right top-to-bottom.

    :param num_cols: number of columns to use for wrapping
    """
    hdbg.dassert_isinstance(signal, pd.Series)
    hdbg.dassert_lte(1, num_cols)
    values = signal.values
    _LOG.debug("num values=%d", values.size)
    # Calculate number of rows that wrapped pd.DataFrame should have.
    num_rows = np.ceil(values.size / num_cols).astype(int)
    _LOG.debug("num_rows=%d", num_rows)
    # Add padding, since numpy's `reshape` requires element counts to match
    # exactly.
    pad_size = num_rows * num_cols - values.size
    _LOG.debug("pad_size=%d", pad_size)
    padding = np.full(pad_size, np.nan)
    padded_values = np.append(values, padding)
    #
    wrapped = padded_values.reshape(num_rows, num_cols)
    return pd.DataFrame(wrapped)


def _unwrap(
    df: pd.DataFrame, idx: pd.Index, name: Optional[Any] = None
) -> pd.Series:
    """
    Undo `_wrap`.

    We allow `index.size` to be less than nrows * ncols of `df`, in which case
    values are truncated from the end of the unwrapped dataframe.

    :param idx: index of series provided to `_wrap` call
    """
    _LOG.debug("df.shape=%s", df.shape)
    values = df.values.flatten()
    pad_size = values.size - idx.size
    _LOG.debug("pad_size=%d", pad_size)
    if pad_size > 0:
        data = values[:-pad_size]
    else:
        data = values
    unwrapped = pd.Series(data=data, index=idx, name=name)
    return unwrapped


def skip_apply_func(
    signal: pd.DataFrame,
    skip_size: int,
    func: Callable[[pd.Series], pd.DataFrame],
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Apply `func` to each col of `signal` after a wrap, then unwrap and merge.

    :param skip_size: num_cols used for wrapping each col of `signal`
    :param kwargs: forwarded to `func`
    """
    cols = {}
    for col in signal.columns:
        wrapped = _wrap(signal[col], skip_size)
        funced = func(wrapped, **kwargs)
        unwrapped = _unwrap(funced, signal.index, col)
        cols[col] = unwrapped
    df = pd.DataFrame.from_dict(cols)
    return df


# TODO(Paul): Add test coverage.
def sign_normalize(
    signal: Union[pd.DataFrame, pd.Series],
    atol: float = 0,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Normalize nonzero values to +/- 1 according to sign.

    :param signal: series or 1-dimensional dataframe
    :param atol: values < atol are forced to zero
    :return: series/1-d dataframe with finite values of either -1, 0, or 1
    """
    # Convert to series before performing calculations.
    convert_to_frame = False
    if isinstance(signal, pd.DataFrame):
        signal = signal.squeeze()
        convert_to_frame = True
    hdbg.dassert_isinstance(
        signal,
        pd.Series,
        msg="Only series and 1-dimensional dataframes are admissible",
    )
    # Force small values to zero.
    atol_mask = signal.abs() < atol
    normalized_signal = signal.copy()
    normalized_signal.loc[atol_mask] = 0
    # Mask out zeros when rescaling nonzero values.
    zero_mask = normalized_signal == 0
    normalized_signal = normalized_signal.copy()
    normalized_signal.loc[~zero_mask] /= normalized_signal.loc[~zero_mask].abs()
    if convert_to_frame:
        normalized_signal = normalized_signal.to_frame()
    return normalized_signal


# TODO(Paul): Add test coverage.
def normalize(
    signal: pd.Series,
) -> pd.Series:
    """
    Normalize `signal` by dividing it by its l2 norm.
    """
    hdbg.dassert_isinstance(signal, pd.Series)
    hdbg.dassert(
        not signal.isna().any(),
        msg="NaNs detected at %s" % signal[signal.isna()].index,
    )
    norm = np.linalg.norm(signal)
    _LOG.debug("l2 norm=%f", norm)
    normalized = signal / norm
    return normalized


def split_positive_and_negative_parts(
    signal: Union[pd.Series, pd.DataFrame],
) -> pd.DataFrame:
    """
    Split `signal` into max(signal, 0) and max(-signal, 0).
    """
    if isinstance(signal, pd.DataFrame):
        hdbg.dassert_eq(len(signal.columns), 1)
        signal = signal.squeeze()
    hdbg.dassert_isinstance(signal, pd.Series)
    positive = ((signal + signal.abs()) / 2).rename("positive")
    negative = ((signal.abs() - signal) / 2).rename("negative")
    df = pd.concat([positive, negative], axis=1)
    return df


def compute_weighted_sum(
    df: pd.DataFrame, weights: pd.Series, *, convert_to_dataframe: bool = False
) -> pd.Series:
    """
    Perform a weighted sum of the columns of `df` using `weights`.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_isinstance(weights, pd.Series)
    hdbg.dassert_eq(
        df.columns.size,
        weights.index.size,
        "Number of columns of `df` must equal index size of `weights`.",
    )
    hdbg.dassert(
        df.columns.equals(weights.index),
        "Columns of `df` must equal index of `weights`.",
    )
    product = df.multiply(weights).sum(axis=1)
    product.name = weights.name
    if convert_to_dataframe:
        product = product.to_frame()
    return product
