"""
Import as:

import core.finance.bar_processing as cfibapro
"""
import datetime
import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): -> _dassert_is_valid_df
def _is_valid_df(df: pd.DataFrame) -> None:
    hpandas.dassert_time_indexed_df(
        df,
        allow_empty=False,
        strictly_increasing=True,
    )
    # Optional checks, but applicable to all current use cases.
    hdbg.dassert_eq(df.columns.nlevels, 1)
    hdbg.dassert_in(
        df.columns.dtype.type, [np.int64], "The asset ids should be integers."
    )


def infer_active_bars(df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Apply the heuristic that all-NaN bars are "inactive".

    This heuristic can be used to prune weekends, holidays, short trading
    days, and non-active trading hours.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: index of active bars
    """
    _is_valid_df(df)
    return df.dropna(how="all").index


def infer_active_times(df: pd.DataFrame) -> pd.Index:
    """
    Return each time of day corresponding to an "active bar".

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: index of `datetime.time`, each corresponding to at least one
        active bar
    """
    _is_valid_df(df)
    active_time_counts = df.dropna(how="all").groupby(lambda x: x.time()).count()
    active_times = active_time_counts.index
    hdbg.dassert_container_type(active_times, pd.Index, datetime.time)
    return active_times


def infer_daily_universe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add asset to universe on date iff it has non-NaN data on date.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: bool dataframe of dates indicating universe membership
    """
    _is_valid_df(df)
    bar_counts = df.dropna(how="all").groupby(lambda x: x.date()).count()
    return bar_counts != 0


def infer_splits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Infer splits from price data.

    The implemented heuristic suffers from both false positive and false
    negatives, but should effectively detect N-for-1 splits.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: float dataframe of beginning-of-day share multipliers
    """
    _is_valid_df(df)
    bod = retrieve_beginning_of_day_values(df)
    eod = retrieve_end_of_day_values(df)
    overnight_pct_change = (bod - eod.shift(1)) / eod.shift(1)
    inferred_splits = (1 / (1 + overnight_pct_change)).round()
    #
    num_splits_by_date = (
        inferred_splits[inferred_splits != 1].count(axis=1).rename("num_splits")
    )
    split_dates = num_splits_by_date[num_splits_by_date > 0]
    _LOG.info("num dates with splits=%d", split_dates.size)
    _LOG.debug("split_dates=\n%s", hpandas.df_to_str(split_dates))
    #
    split_grid = inferred_splits.loc[split_dates.index]
    split_grid = split_grid[split_grid != 1].dropna(how="all", axis=1)
    _LOG.info("num assets with splits=%d", split_grid.columns.size)
    _LOG.debug("split_grid=\n%s", hpandas.df_to_str(split_grid))
    return inferred_splits


def retrieve_beginning_of_day_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retrieve beginning of day "active bar" timestamps for each day.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: dataframe of beginning-of-day timestamps
    """
    _is_valid_df(df)
    df = df.dropna(how="all")
    timestamps = pd.DataFrame(
        df.index.to_list(),
        df.index,
        ["timestamp"],
    )
    bod_timestamps = timestamps.groupby(lambda x: x.date()).min()
    return bod_timestamps


def retrieve_end_of_day_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retrieve end of day "active bar" timestamps for each day.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return: dataframe of end-of-day timestamps
    """
    _is_valid_df(df)
    df = df.dropna(how="all")
    timestamps = pd.DataFrame(
        df.index.to_list(),
        df.index,
        ["timestamp"],
    )
    eod_timestamps = timestamps.groupby(lambda x: x.date()).max()
    return eod_timestamps


def retrieve_beginning_of_day_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retrieve first "active bar" values by asset for each active date.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return:  float dataframe of beginning-of-day values
    """
    _is_valid_df(df)
    return df.dropna(how="all").groupby(lambda x: x.date()).first()


def retrieve_end_of_day_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retrieve last "active bar" values by asset for each active date.

    :param df: datetime-indexed dataframe with int asset ids as cols
    :return:  float dataframe of end-of-day values
    """
    _is_valid_df(df)
    return df.dropna(how="all").groupby(lambda x: x.date()).last()


def replace_end_of_day_values(
    df1: pd.DataFrame, df2: pd.DataFrame
) -> pd.DataFrame:
    """
    Replace end-of-day values in `df1` with values from `df2`.
    """
    hpandas.dassert_time_indexed_df(
        df1,
        allow_empty=False,
        strictly_increasing=True,
    )
    hpandas.dassert_time_indexed_df(
        df2,
        allow_empty=False,
        strictly_increasing=True,
    )
    hpandas.dassert_columns_equal(df1, df2)
    eod_timestamps = retrieve_end_of_day_timestamps(df1)
    df1 = df1.copy()
    df1.loc[eod_timestamps["timestamp"], :] = df2.loc[
        eod_timestamps["timestamp"], :
    ]
    return df1
