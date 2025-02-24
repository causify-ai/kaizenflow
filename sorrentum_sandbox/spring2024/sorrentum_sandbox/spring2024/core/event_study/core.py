"""
See `docs/dataflow/ck.event_study.explanation.md` for design principles and
notes on intended usage.

Sketch of flow:

events         grid_data -------------------
  |              |                          |
  |              |                          |
resample ----- `reindex_event_features`     |
  |              |                          |
  |              |                          |
  |            kernel (ema, etc.) -------- merge
  |                                         |
  |                                         |
`build_local_timeseries` -------------------
  |                                         |
  |                                         |
drop multiindex                             |
  |                                         |
  |                                         |
linear modeling                             |
  |                                         |
  |                                         |
`unwrap_local_timeseries` ------------------
  |
  ...

Import as:

import core.event_study.core as cevstcor
"""


import logging
from typing import Any, Dict, Iterable, Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# #############################################################################
# Event/data alignment
# #############################################################################


def reindex_event_features(
    events: pd.DataFrame,
    grid_data: pd.DataFrame,
    **kwargs: Dict[str, Any],
) -> pd.DataFrame:
    """
    Reindex `events` so that it aligns with `grid_data`.

    Suppose `events` contains features to be studied in the event study.
    Then one may use this function to add such features to `grid_data` so that
    they may be studied downstream.

    Example usage:
    ```
    # Reindex along grid_data.
    aligned_events = reindex_event_features(events, grid_data)
    # Apply kernel. Use `fillna` for correct application of kernel.
    event_signal = sigp.smooth_moving_average(aligned_events.fillna(0), tau=8)
    # Merge the derived `events` features with `grid_data`.
    grid_data2 = event_signal.join(grid_data, how="right")
    # Use the merged dataset downstream.
    grid_data = grid_data2
    ```

    :param kwargs: forwarded to `reindex`
    """
    reindexed = events.reindex(index=grid_data.index, **kwargs)
    return reindexed


# #############################################################################
# Local time series
# #############################################################################


def build_local_timeseries(
    events: pd.DataFrame,
    grid_data: pd.DataFrame,
    relative_grid_indices: Iterable[int],
    freq: Optional[Union[pd.DateOffset, pd.Timedelta, str]] = None,
    info: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Construct relative time series of `grid_data` around each event.

    The effect of this function is to grab uniform time slices of `grid_data`
    around each event time indicated in `events.index`.

    :param events: reference dataframe of events
        -   has monotonically increasing DatetimeIndex
        -   has at least one column (e.g., indicator column)
    :param grid_data: tabular data
        -   has monotonically increasing DatetimeIndex
        -   datetimes should represent uniform time bars
        -   has at least one column (e.g., response)
    :param relative_grid_indices: time points on grid relative to event time
        of "0", e.g., [-2, -1, 0, 1] denotes t_{-2} < t_{-1} < t_0 < t_1,
        where "t_0" is the event time.
    :param freq: as in pandas `shift`
    :return: multiindexed dataframe
        -   level 0: relative grid indices
        -   level 1: event time (e.g., "t_0") for each event
                Note that the event time needs to be adjusted by
                relative_grid_index grid points in order to obtain the data
                timestamps
        -   cols: same as grid_data cols
    """
    # Enforce assumptions on inputs.
    hdbg.dassert_isinstance(events, pd.DataFrame)
    hdbg.dassert_isinstance(grid_data, pd.DataFrame)
    hpandas.dassert_strictly_increasing_index(events.index)
    hpandas.dassert_strictly_increasing_index(grid_data.index)
    # Make `relative_grid_indices` a sorted list.
    if not isinstance(relative_grid_indices, list):
        relative_grid_indices = list(relative_grid_indices)
    hdbg.dassert(relative_grid_indices)
    relative_grid_indices.sort()
    # Gather the data and, if requested, info.
    relative_data = {}
    for idx in relative_grid_indices:
        if info is not None:
            info_for_idx = {}
        else:
            info_for_idx = None
        # Switch sign of `idx` since a pandas period of `n` selects t_{-n}.
        data_at_idx = _shift_and_select(
            events.index, grid_data, -idx, freq, info_for_idx
        )
        #
        if info is not None:
            info[idx] = info_for_idx
        relative_data[idx] = data_at_idx
    # Turn the data dictionary into a multiindexed dataframe.
    df = pd.concat(relative_data)
    hpandas.dassert_strictly_increasing_index(df)
    return df


# TODO(Paul): Think about whether we want to add `freq` here or just remove it
# everywhere.
def unwrap_local_timeseries(
    local_ts: pd.DataFrame,
    grid_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert relative times in local_ts back to grid_data and align values.

    One use case is to take predictions generated modeling local time series
    and project them back onto the linear time axis (e.g., to generate PnL
    streams).

    :param local_ts: like the return value of `build_local_timeseries`
    :param grid_data: as in `build_local_timeseries`
    :return: dataframe with
        - cols as in local_ts
        - index like grid_data.index
    """
    relative_times = local_ts.index.unique(level=0)
    df_list = []
    for time in relative_times:
        # Grab df at time.
        local_df = local_ts.loc[time]
        # Reindex according to grid_data. This is important for getting adjacent
        # grid point times. NaNs used datetimes outside of local_df.index.
        reindexed = local_df.reindex(index=grid_data.index)
        # Undo time shift used to generate the local time series.
        shifted = reindexed.shift(time)
        #
        df_list.append(shifted.dropna(how="all"))
    # Concatenate the unwrapped local time series.
    df = pd.concat(df_list)
    # Handle overlaps by taking mean (respects response variables).
    # This ensures that the resulting index is unique
    df_mean = df.groupby(by=lambda x: x).mean()
    # Reindex according to grid_data.
    df_reindexed = df_mean.reindex(index=grid_data.index)
    #
    hpandas.dassert_strictly_increasing_index(df_reindexed)
    return df_reindexed


def _shift_and_select(
    idx: pd.Index,
    grid_data: pd.DataFrame,
    periods: int,
    freq: Optional[Union[pd.DateOffset, pd.Timedelta, str]] = None,
    info: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Shift by `periods` and select `idx`.

    This private helper encapsulates and isolates time-shifting behavior.

    :param idx: reference index (e.g., of datetimes of events)
    :param grid_data: tabular data
    :param periods: as in pandas `shift` functions
    :param freq: as in pandas `shift` functions
    :param info: optional empty dict-like object to be populated with stats
        about the operation performed
    """
    # Shift.
    shifted_grid_data = grid_data.shift(periods, freq)
    # Select.
    intersection = idx.intersection(shifted_grid_data.index)
    hdbg.dassert(not intersection.empty)
    selected = shifted_grid_data.loc[intersection]
    # Maybe add info.
    if info is not None:
        hdbg.dassert_isinstance(info, dict)
        # Ensure `info` is empty.
        hdbg.dassert(not info)
        info["indices_with_no_data"] = intersection.difference(idx)
        info["pct_found"] = intersection.size / idx.size
        info["periods"] = periods
        if freq is not None:
            info["freq"] = freq
    return selected


# #############################################################################
# Modeling
# #############################################################################


# TODO(Paul): Move to `statistics.py`.
def regression(x: pd.DataFrame, y: pd.Series, info: Optional[dict] = None):
    """
    Linear regression of y_var on x_vars with info.

    Constant regression term not included but must be supplied by caller.

    Returns beta_hat along with beta_hat_covar and z-scores for the hypothesis
    that a beta_j = 0.
    """
    # Determine number of non-NaN y-values.
    nan_filter = ~np.isnan(y)
    nobs = np.count_nonzero(nan_filter)
    # Filter NaNs.
    x = x[nan_filter]
    y = y[nan_filter]
    y_mean = np.mean(y)
    # Compute total sum of squares.
    tss = (y - y_mean).dot(y - y_mean)
    # Perform linear regression (estimate \beta).
    regress = np.linalg.lstsq(x, y, rcond=None)
    beta_hat = regress[0]
    # Ensure full rank.
    hdbg.dassert_eq(regress[2], x.shape[1])
    # Extract residual sum of squares.
    rss = np.asscalar(regress[1])
    # Compute r^2.
    r_sq = 1 - rss / tss
    # Estimate variance sigma_hat_sq.
    xtx_inv = np.linalg.inv((x.transpose().dot(x)))
    sigma_hat_sq = rss / (nobs - x.shape[1])
    # Estimate covariance of \beta.
    beta_hat_covar = xtx_inv * sigma_hat_sq
    # Z-score \beta coefficients (e.g., for hypothesis testing).
    beta_hat_z_score = beta_hat / np.sqrt(sigma_hat_sq * np.diagonal(xtx_inv))
    # Maybe add info.
    if info is not None:
        hdbg.dassert_isinstance(info, dict)
        hdbg.dassert(not info)
        info["nobs (resp)=%d"] = nobs
        info["y_mean=%f"] = y_mean
        info["tss=%f"] = tss
        info["beta_hat=%s"] = np.array2string(beta_hat)
        info["rss=%f"] = rss
        info["r^2=%f"] = r_sq
        info["sigma_hat_sq=%s"] = sigma_hat_sq
        info["beta_hat_covar=%s"] = np.array2string(beta_hat_covar)
        info["beta_hat_z_score=%s"] = np.array2string(beta_hat_z_score)
    # Calculate predicted values
    y_hat = np.matmul(x.values, beta_hat)
    return pd.Series(data=y_hat, index=y.index)
