"""
Functions removing data from data frames.

Import as:

import core.finance.ablation as cfinabla
"""
import datetime
import logging
from typing import Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


def remove_dates_with_no_data(
    df: pd.DataFrame, report_stats: bool
) -> pd.DataFrame:
    """
    Given a df indexed with timestamps, filter out data with all nans.

    :param report_stats: if True report information about the performed
        operation
    :return: filtered df
    """
    # This is not strictly necessary.
    hpandas.dassert_strictly_increasing_index(df)
    # Store the dates of the days removed because of all NaNs.
    removed_days = []
    # Accumulate the df for all the days that are not discarded.
    df_out = []
    # Store the days processed.
    num_days = 0
    # Scan the df by date.
    for date, df_tmp in df.groupby(df.index.date):
        if np.isnan(df_tmp).all(axis=1).all():
            _LOG.debug("No data on %s", date)
            removed_days.append(date)
        else:
            df_out.append(df_tmp)
        num_days += 1
    df_out = pd.concat(df_out)
    hpandas.dassert_strictly_increasing_index(df_out)
    #
    if report_stats:
        # Stats for rows.
        _LOG.info("df.index in [%s, %s]", df.index.min(), df.index.max())
        removed_perc = hprint.perc(df.shape[0] - df_out.shape[0], df.shape[0])
        _LOG.info("Rows removed: %s", removed_perc)
        # Stats for all days.
        removed_perc = hprint.perc(len(removed_days), num_days)
        _LOG.info("Number of removed days: %s", removed_perc)
        # Find week days.
        removed_weekdays = [d for d in removed_days if d.weekday() < 5]
        removed_perc = hprint.perc(len(removed_weekdays), len(removed_days))
        _LOG.info("Number of removed weekdays: %s", removed_perc)
        _LOG.info("Weekdays removed: %s", ", ".join(map(str, removed_weekdays)))
        # Stats for weekend days.
        removed_perc = hprint.perc(
            len(removed_days) - len(removed_weekdays), len(removed_days)
        )
        _LOG.info("Number of removed weekend days: %s", removed_perc)
    return df_out


# TODO(gp): Active trading hours and days are specific of different assets.
#  Consider explicitly passing this information instead of using defaults.
def set_non_ath_to_nan(
    data: Union[pd.Series, pd.DataFrame],
    *,
    start_time: Optional[datetime.time] = None,
    end_time: Optional[datetime.time] = None,
) -> pd.DataFrame:
    """
    Filter according to active trading hours.

    We assume time intervals are:
    - left closed, right open `[a, b)`
    - labeled right

    Row is not set to `np.nan` iff its `time` satisfies:
      - `start_time < time`, and
      - `time <= end_time`
    """
    hdbg.dassert_isinstance(data.index, pd.DatetimeIndex)
    hpandas.dassert_strictly_increasing_index(data)
    if start_time is None:
        start_time = datetime.time(9, 30)
    if end_time is None:
        end_time = datetime.time(16, 0)
    hdbg.dassert_lte(start_time, end_time)
    # Compute the indices to remove.
    times = data.index.time
    to_remove_mask = (times <= start_time) | (end_time < times)
    # Make a copy and filter.
    data = data.copy()
    # As part of LimeTask2163 we have found out that the naive Pandas approach
    # to add nan for data outside trading hours, as below:
    #   data[to_remove_mask] = np.nan
    # is 100x slower than the following approach.
    data_index = data.index
    if isinstance(data, pd.Series):
        data = data.loc[~to_remove_mask].reindex(data_index)
    elif isinstance(data, pd.DataFrame):
        data = data.loc[~to_remove_mask, :].reindex(data_index)
    else:
        raise ValueError("Invalid data='%s' of type '%s'" % (data, type(data)))
    return data


def remove_times_outside_window(
    df: pd.DataFrame,
    start_time: datetime.time,
    end_time: datetime.time,
    # TODO(gp): Add *
    # *,
    bypass: bool = False,
) -> pd.DataFrame:
    """
    Remove times outside of (start_time, end_time].
    """
    # Perform sanity checks.
    hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    hpandas.dassert_strictly_increasing_index(df)
    hdbg.dassert_isinstance(start_time, datetime.time)
    hdbg.dassert_isinstance(end_time, datetime.time)
    hdbg.dassert_lte(start_time, end_time)
    if bypass:
        return df
    # Compute the indices to remove.
    times = df.index.time
    to_remove_mask = (times <= start_time) | (end_time < times)
    return df[~to_remove_mask]


def set_weekends_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter out weekends setting the corresponding values to `np.nan`.
    """
    hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    # 5 = Saturday, 6 = Sunday.
    to_remove_mask = df.index.dayofweek.isin([5, 6])
    df = df.copy()
    df[to_remove_mask] = np.nan
    return df


def remove_weekends(
    df: pd.DataFrame,
    # TODO(gp): Add *
    # *,
    bypass: bool = False
) -> pd.DataFrame:
    """
    Remove weekends from `df`.
    """
    hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
    # 5 = Saturday, 6 = Sunday.
    if bypass:
        return df
    to_remove_mask = df.index.dayofweek.isin([5, 6])
    return df[~to_remove_mask]
