"""
Import as:

import core.finance.accumulation as cfinaccu
"""
import datetime
import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): -> _dassert_valid_...
def _is_valid_start_end_time_pair(
    start_time: datetime.time,
    end_time: datetime.time,
) -> None:
    """
    Check if start_time <= end_time otherwise asserts.
    """
    hdbg.dassert_isinstance(start_time, datetime.time)
    hdbg.dassert_isinstance(end_time, datetime.time)
    hdbg.dassert_lte(start_time, end_time)


def accumulate_returns_and_volatility(
    df: pd.DataFrame,
    returns_col: str,
    volatility_col: str,
    start_time: datetime.time,
    end_time: datetime.time,
) -> pd.DataFrame:
    """
    Accumulate intraday returns and volatility over a window [a, b).

    :param df: datetime indexed dataframe with log rets and volatility
    :param returns_col: name of returns column
    :param volatility_col: name of volatility column
    :param start_time: start of intraday accumulation
    :param end_time: end of intraday accumulation
    :return: dataframe with `returns_col`, `volatility_col` accumulated
        intraday
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=True, strictly_increasing=True
    )
    # NOTE: Excluding multilevel columns may not be necessary.
    hdbg.dassert_eq(df.columns.nlevels, 1)
    # Ensure required columns exist.
    hdbg.dassert_is_subset([returns_col, volatility_col], df.columns)
    _is_valid_start_end_time_pair(start_time, end_time)
    # Trim to returns and volatility columns.
    df = df[[returns_col, volatility_col]]
    # TODO(Paul): Maybe import ablation for this operation, but check
    #  endpoint boundaries.
    # Remove times outside of accumulation window.
    times = df.index.time
    to_remove_mask = (times <= start_time) | (end_time < times)
    df = df[~to_remove_mask]
    # Square the volatility column before accumulation.
    df[volatility_col] = np.square(df[volatility_col])
    # Accumulate independently over each day.
    df = df.groupby(lambda x: x.date()).cumsum()
    # Recover volatility from variance by taking the square root.
    df[volatility_col] = np.sqrt(df[volatility_col])
    return df


def reverse_accumulate_returns(
    df: pd.DataFrame,
    returns_col: str,
    start_time: datetime.time,
    end_time: datetime.time,
) -> pd.DataFrame:
    """
    Accumulate intraday returns over increasing backward-looking windows.

    :param df: datetime indexed dataframe with log rets and volatility
    :param returns_col: name of returns column
    :param start_time: defines start of backward-looking window
    :param end_time: end point and knowledge time of all accumulated returns
    :return: dataframe indexed at `end_time` on each day and with int cols;
        the `0` column denotes the single-bar return ending at `end_time`,
        and successive columns (`1`, `2`, etc.) denote aggregations over
        increasing backward-looking windows
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=True, strictly_increasing=True
    )
    hdbg.dassert_eq(df.columns.nlevels, 1)
    hdbg.dassert_in(returns_col, df.columns)
    _is_valid_start_end_time_pair(start_time, end_time)
    # Extract returns series.
    returns = df[returns_col]
    hdbg.dassert_isinstance(returns, pd.Series)
    # Remove times outside of accumulation window.
    times = returns.index.time
    to_remove_mask = (times <= start_time) | (end_time < times)
    returns = returns[~to_remove_mask]
    # Independently process each day.
    results = []
    groupby_obj = returns.groupby(lambda x: x.date())
    for _, srs in groupby_obj:
        # Reverse accumulate returns.
        srs = srs.loc[::-1].cumsum()
        n = len(srs)
        # Reshape the result into multiple columns indexed by the knowledge
        # time.
        result = pd.DataFrame(srs.values.reshape(1, n), [srs.index.max()])
        results.append(result)
    #
    return pd.concat(results)
