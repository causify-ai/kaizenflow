"""
Import as:

import core.finance.prediction_processing as cfiprpro
"""
import datetime
import logging
from typing import List, Optional, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_bar_start_timestamps(
    data: Union[pd.Series, pd.DataFrame],
) -> pd.Series:
    """
    Given data on a uniform grid indexed by end times, return start times.

    :param data: a dataframe or series with a `DatetimeIndex` that has a `freq`.
        It is assumed that the timestamps in the index are times corresponding
        to the end of bars. For this particular function, assumptions around
        which endpoints are open or closed are not important.
    :return: a series with index `data.index` (of bar end timestamps) and values
        equal to bar start timestamps
    """
    freq = data.index.freq
    hdbg.dassert(freq, msg="DatetimeIndex must have a frequency.")
    size = data.index.size
    hdbg.dassert_lte(1, size, msg="DatetimeIndex has size=%i values" % size)
    date_range = data.index.shift(-1)
    srs = pd.Series(index=data.index, data=date_range, name="bar_start_timestamp")
    return srs


def compute_epoch(
    data: Union[pd.Series, pd.DataFrame], *, unit: Optional[str] = None
) -> Union[pd.Series, pd.DataFrame]:
    """
    Convert datetime index times to minutes, seconds, or nanoseconds.

    :param data: a dataframe or series with a `DatetimeIndex`
    :param unit: unit for reporting epoch. Supported units are:
        "minute", "second', "nanosecond". Default is "minute".
    :return: series of int64's with epoch in minutes, seconds, or nanoseconds
    """
    unit = unit or "minute"
    hdbg.dassert_isinstance(data.index, pd.DatetimeIndex)
    nanoseconds = data.index.view(np.int64)
    if unit == "minute":
        epochs = np.int64(nanoseconds * 1e-9 / 60)
    elif unit == "second":
        epochs = np.int64(nanoseconds * 1e-9)
    elif unit == "nanosecond":
        epochs = nanoseconds
    else:
        raise ValueError(
            f"Unsupported unit=`{unit}`. Supported units are "
            "'minute', 'second', and 'nanosecond'."
        )
    srs = pd.Series(index=data.index, data=epochs, name=unit)
    if isinstance(data, pd.DataFrame):
        return srs.to_frame()
    return srs


def stack_prediction_df(
    df: pd.DataFrame,
    id_col: str,
    close_price_col: str,
    vwap_col: str,
    ret_col: str,
    prediction_col: str,
    ath_start: datetime.time,
    ath_end: datetime.time,
    *,
    remove_weekends: bool = True,
) -> pd.DataFrame:
    """
    Process and stack a dataframe of predictions and financial data.

    :param df: dataframe of the following form:
        - DatetimeIndex with `freq`
            - datetimes are end-of-bar datetimes (e.g., so all column values
              are knowable at the timestamp, modulo the computation time
              required for the prediction)
        - Two column levels
            - innermost level consists of the names/asset ids
            - outermost level has features/market data
    :param id_col: name to use for identifier col in output
    :param close_price_col: col name for bar close price
    :param vwap_col: col name for vwap
    :param ret_col: col name for percentage returns
    :param prediction_col: col name for returns prediction
    :param ath_start: active trading hours start time
    :param ath_end: active trading hours end time
    :param remove_weekends: remove any weekend data iff `True`
    :return: dataframe of the following form:
        - RangeIndex
        - Single column level, with columns for timestamps, asset ids, market
          data, predictions, etc.
        - Predictions are moved from the end-of-bar semantic to
          beginning-of-bar semantic
        - Epoch and timestamps are for beginning-of-bar rather than end
    """
    # Avoid modifying the input dataframe.
    df = df.copy()
    # TODO(Paul): Make this more robust.
    idx_name = df.columns.names[1]
    if idx_name is None:
        idx_name = "level_1"
    # Reindex according to start time.
    bar_start_ts = compute_bar_start_timestamps(df).rename("start_bar_et_ts")
    df.index = bar_start_ts
    bar_start_ts.index = bar_start_ts
    epoch = compute_epoch(df).squeeze().rename("minute_index")
    # Extract market data (price, return, vwap).
    dfs: List[pd.DataFrame] = []
    dfs.append(
        df[[close_price_col]].rename(columns={close_price_col: "eob_close"})
    )
    dfs.append(df[[vwap_col]].rename(columns={vwap_col: "eob_vwap"}))
    dfs.append(df[[ret_col]].rename(columns={ret_col: "eob_ret"}))
    # Perform time shifts for previous-bar price and move prediction to
    # beginning-of-bar semantic.
    dfs.append(
        df[[close_price_col]]
        .shift(1)
        .rename(columns={close_price_col: "eopb_close"})
    )
    dfs.append(
        df[[prediction_col]].shift(1).rename(columns={prediction_col: "alpha"})
    )
    # Consolidate the dataframes.
    out_df = pd.concat(dfs, axis=1)
    # Perform ATH time filtering.
    out_df = out_df.between_time(ath_start, ath_end)
    # Maybe remove weekends.
    if remove_weekends:
        out_df = out_df[out_df.index.day_of_week < 5]
    # TODO(Paul): Handle NaNs.
    # Stack data and annotate id column.
    out_df = (
        out_df.stack().reset_index(level=1).rename(columns={idx_name: id_col})
    )
    # Add epoch and bar start timestamps.
    out_df = out_df.join(epoch.to_frame())
    out_df = out_df.join(bar_start_ts.apply(lambda x: x.isoformat()).to_frame())
    # Reset the index.
    return out_df.reset_index(drop=True)
