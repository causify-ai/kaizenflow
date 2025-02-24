"""
Import as:

import core.signal_processing.outliers as csiprout
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# #############################################################################
# Outlier handling
# #############################################################################


def process_outliers(
    srs: pd.Series,
    mode: str,
    lower_quantile: float,
    upper_quantile: Optional[float] = None,
    window: Optional[int] = None,
    min_periods: Optional[int] = None,
    info: Optional[dict] = None,
) -> pd.Series:
    """
    Process outliers in different ways given lower / upper quantiles.

    Default behavior:
      - If `window` is `None`, set `window` to series length
        - This works like an expanding window (we always look at the full
          history, except for anything burned by `min_periods`)
      - If `min_periods` is `None` and `window` is `None`, set `min_periods` to
        `0`
        - Like an expanding window with no data burned
      - If `min_periods` is `None` and `window` is not `None`, set `min_periods`
        to `window`
        - This is a sliding window with leading data burned so that every
          estimate uses a full window's worth of data

    Note:
      - If `window` is set to `None` according to these conventions (i.e., we
        are in an "expanding window" mode), then outlier effects are never
        "forgotten" and the processing of the data can depend strongly upon
        where the series starts
      - For this reason, it is suggested that `window` be set to a finite value
        adapted to the data/frequency

    :param srs: pd.Series to process
    :param lower_quantile: lower quantile (in range [0, 1]) of the values to keep
        The interval of data kept without any changes is [lower, upper]. In other
        terms the outliers with quantiles strictly smaller and larger than the
        respective bounds are processed.
    :param upper_quantile: upper quantile with the same semantic as
        lower_quantile. If `None`, the quantile symmetric of the lower quantile
        with respect to 0.5 is taken. E.g., an upper quantile equal to 0.7 is
        taken for a lower_quantile = 0.3
    :param window: rolling window size
    :param min_periods: minimum number of observations in window required to
        calculate the quantiles. The first `min_periods` values will not be
        processed. If `None`, defaults to `window`.
    :param mode: it can be "winsorize", "set_to_nan", "set_to_zero"
    :param info: empty dict-like object that this function will populate with
        statistics about the performed operation

    :return: transformed series with the same number of elements as the input
        series. The operation is not in place.
    """
    # Check parameters.
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_lte(0.0, lower_quantile)
    if upper_quantile is None:
        upper_quantile = 1.0 - lower_quantile
    hdbg.dassert_lte(lower_quantile, upper_quantile)
    hdbg.dassert_lte(upper_quantile, 1.0)
    # Process default `min_periods` and `window` parameters.
    if min_periods is None:
        if window is None:
            min_periods = 0
        else:
            min_periods = window
    if window is None:
        window = srs.shape[0]
    if window < 30:
        _LOG.warning("`window`=`%s` < `30`", window)
    if min_periods > window:
        _LOG.warning("`min_periods`=`%s` > `window`=`%s`", min_periods, window)
    # Compute bounds.
    l_bound = srs.rolling(window, min_periods=min_periods, center=False).quantile(
        lower_quantile
    )
    u_bound = srs.rolling(window, min_periods=min_periods, center=False).quantile(
        upper_quantile
    )
    _LOG.debug(
        "Removing outliers in [%s, %s] with mode=%s",
        lower_quantile,
        upper_quantile,
        mode,
    )
    # Compute stats.
    if info is not None:
        hdbg.dassert_isinstance(info, dict)
        # Dictionary should be empty.
        hdbg.dassert(not info)
        info["series_name"] = srs.name
        info["num_elems_before"] = len(srs)
        info["num_nans_before"] = np.isnan(srs).sum()
        info["num_infs_before"] = np.isinf(srs).sum()
        info["quantiles"] = (lower_quantile, upper_quantile)
        info["mode"] = mode
    #
    srs = srs.copy()
    # Here we implement the functions instead of using library functions (e.g,
    # `scipy.stats.mstats.winsorize`) since we want to compute some statistics
    # that are not readily available from the library function.
    l_mask = srs < l_bound
    u_mask = u_bound < srs
    if mode == "winsorize":
        # Assign the outliers to the value of the bounds.
        srs[l_mask] = l_bound[l_mask]
        srs[u_mask] = u_bound[u_mask]
    else:
        mask = u_mask | l_mask
        if mode == "set_to_nan":
            srs[mask] = np.nan
        elif mode == "set_to_zero":
            srs[mask] = 0.0
        else:
            hdbg.dfatal("Invalid mode='%s'" % mode)
    # Append more the stats.
    if info is not None:
        info["bounds"] = pd.DataFrame({"l_bound": l_bound, "u_bound": u_bound})
        num_removed = l_mask.sum() + u_mask.sum()
        info["num_elems_removed"] = num_removed
        info["num_elems_after"] = (
            info["num_elems_before"] - info["num_elems_removed"]
        )
        info["percentage_removed"] = (
            100.0 * info["num_elems_removed"] / info["num_elems_before"]
        )
        info["num_nans_after"] = np.isnan(srs).sum()
        info["num_infs_after"] = np.isinf(srs).sum()
    return srs


def process_outlier_df(
    df: pd.DataFrame,
    mode: str,
    lower_quantile: float,
    upper_quantile: Optional[float] = None,
    window: Optional[int] = None,
    min_periods: Optional[int] = None,
    info: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Extend `process_outliers` to dataframes.

    TODO(*): Revisit this with a decorator approach:
    https://github.com/.../.../issues/568
    """
    if info is not None:
        hdbg.dassert_isinstance(info, dict)
        # Dictionary should be empty.
        hdbg.dassert(not info)
    cols = {}
    for col in df.columns:
        if info is not None:
            maybe_stats: Optional[Dict[str, Any]] = {}
        else:
            maybe_stats = None
        srs = process_outliers(
            df[col],
            mode,
            lower_quantile,
            upper_quantile=upper_quantile,
            window=window,
            min_periods=min_periods,
            info=maybe_stats,
        )
        cols[col] = srs
        if info is not None:
            info[col] = maybe_stats
    ret = pd.DataFrame.from_dict(cols)
    # Check that the columns are the same. We don't use dassert_eq because of
    # #665.
    hdbg.dassert(
        all(df.columns == ret.columns),
        "Columns are different:\ndf.columns=%s\nret.columns=%s",
        str(df.columns),
        str(ret.columns),
    )
    return ret


def process_nonfinite(
    srs: pd.Series,
    remove_nan: bool = True,
    remove_inf: bool = True,
    info: Optional[dict] = None,
) -> pd.Series:
    """
    Remove infinite and NaN values according to the parameters.

    :param srs: pd.Series to process
    :param remove_nan: remove NaN values if True and keep if False
    :param remove_inf: remove infinite values if True and keep if False
    :param info: empty dict-like object that this function will populate with
        statistics about how many items were removed
    :return: transformed copy of the input series
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mask = np.isnan(srs)
    inf_mask = np.isinf(srs)
    nan_inf_mask = nan_mask | inf_mask
    # Make a copy of input that will be processed
    if remove_nan & remove_inf:
        res = srs[~nan_inf_mask].copy()
    elif remove_nan & ~remove_inf:
        res = srs[~nan_mask].copy()
    elif ~remove_nan & remove_inf:
        res = srs[~inf_mask].copy()
    else:
        res = srs.copy()
    if info is not None:
        hdbg.dassert_isinstance(info, dict)
        # Dictionary should be empty.
        hdbg.dassert(not info)
        info["series_name"] = srs.name
        info["num_elems_before"] = len(srs)
        info["num_nans_before"] = np.isnan(srs).sum()
        info["num_infs_before"] = np.isinf(srs).sum()
        info["num_elems_removed"] = len(srs) - len(res)
        info["num_nans_removed"] = info["num_nans_before"] - np.isnan(res).sum()
        info["num_infs_removed"] = info["num_infs_before"] - np.isinf(res).sum()
        info["percentage_elems_removed"] = (
            100.0 * info["num_elems_removed"] / info["num_elems_before"]
        )
    return res
