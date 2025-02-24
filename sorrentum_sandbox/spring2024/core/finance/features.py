"""
Import as:

import core.finance.features as cfinfeat
"""

import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def compute_midrange(
    df: pd.DataFrame,
    high_col: str,
    low_col: str,
    # TODO(gp): Add *
    # *,
    apply_log: bool = False,
) -> pd.DataFrame:
    """
    Return midrange price, i.e., the price in the middle of [high, low] bar
    price.

    :param df: dataframe of high and low values
    :param high_col: name of high-value col
    :param low_col: name of low-value col
    :param apply_log: apply `log()` to data prior to calculation iff True
    :return: 1-col dataframe
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [high_col, low_col]
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)
    #
    hl = df[cols]
    if apply_log:
        hl = np.log(hl)
    high = hl[high_col]
    low = hl[low_col]
    midrange = 0.5 * (high + low)
    if apply_log:
        midrange.name = "log_midrange"
    else:
        midrange.name = "midrange"
    return midrange.to_frame()


def compute_money_transacted(
    df: pd.DataFrame,
    high_col: str,
    low_col: str,
    volume_col: str,
) -> pd.DataFrame:
    """
    Return estimated amount of money transacted in bar.

    :param df: dataframe of high, low, and volume values
    :param high_col: name of high-value col
    :param low_col:  name of low-value col
    :param volume_col: name of volume value col
    :return: 1-col dataframe
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [high_col, low_col, volume_col]
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)
    #
    hlv = df[cols]
    high = hlv[high_col]
    low = hlv[low_col]
    volume = hlv[volume_col]
    money = 0.5 * (high + low) * volume
    money.name = "money_transacted"
    return money.to_frame()


def compute_stochastic(
    df: pd.DataFrame,
    high_col: str,
    low_col: str,
    close_col: str,
    # TODO(gp): Add *
    # *,
    apply_log: bool = False,
) -> pd.DataFrame:
    """
    Compute intrabar close price relative to high/low range.

    The feature is scaled so that it lies between -1 and +1.

    :param df: dataframe of high, low, and close values
    :param high_col: name of high-value col
    :param low_col:  name of low-value col
    :param close_col: name of close value col
    :param apply_log: apply `log()` to data prior to calculation iff True
    :return: 1-col dataframe with indicator
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [high_col, low_col, close_col]
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)
    stochastic_col = "stochastic"
    hlc = df[cols]
    # Check that having high = low implies all prices in the bar are the same.
    high_equal_low_mask = hlc[high_col] == hlc[low_col]
    close_not_equal_high_mask = hlc[close_col] != hlc[high_col]
    high_equal_low_not_equal_close = hlc.loc[
        high_equal_low_mask & close_not_equal_high_mask
    ]
    hdbg.dassert_eq(
        high_equal_low_not_equal_close.shape[0],
        0,
        msg=f"There is a case when low=high!=close:\n{hpandas.df_to_str(high_equal_low_not_equal_close, num_rows=3)}\n",
    )
    #
    if apply_log:
        hlc = np.log(hlc)
    hlc[stochastic_col] = (2 * hlc[close_col] - hlc[high_col] - hlc[low_col]) / (
        hlc[high_col] - hlc[low_col]
    )
    # Having all prices equal results in 0 / 0 = np.nan, however zero is more
    # appropriate. However, np.nan == np.nan is False which means that NaNs
    # will be preserved as intended.
    hlc[stochastic_col].loc[high_equal_low_mask] = 0
    stochastic = hlc[stochastic_col]
    stochastic.name = stochastic_col
    return stochastic.to_frame()


def normalize_bar(
    df: pd.DataFrame,
    # TODO(gp): Add *
    # *,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.DataFrame:
    """
    Perform standard bar translation/rescaling of price.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [open_col, high_col, low_col, close_col, volume_col]
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)
    hdbg.dassert_lte(0.0, df[volume_col].min())
    #
    translated_hlc = df[[high_col, low_col, close_col]].subtract(
        df[open_col], axis=0
    )
    normalized_hlc = translated_hlc.divide(np.sqrt(df[volume_col]), axis=0)
    normalized_hlc = normalized_hlc.replace([-np.inf, np.inf], np.nan)
    normalized_hlc = normalized_hlc.rename(
        columns={
            high_col: "adj_high",
            low_col: "adj_low",
            close_col: "adj_close",
        },
    )
    return normalized_hlc


def compute_two_bar_diffs_and_sums(
    df: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.DataFrame:
    """
    Generate diffs and sums of OHLCV data.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    cols = [open_col, high_col, low_col, close_col, volume_col]
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)
    hdbg.dassert_lte(0.0, df[volume_col].min())
    #
    diffs = (
        df[cols]
        .diff()
        .rename(
            columns={
                open_col: "delta_open",
                high_col: "delta_high",
                low_col: "delta_low",
                close_col: "delta_close",
                volume_col: "delta_volume",
            },
        )
    )
    sums = (df[cols] + df[cols].shift(1)).rename(
        columns={
            open_col: "sigma_open",
            high_col: "sigma_high",
            low_col: "sigma_low",
            close_col: "sigma_close",
            volume_col: "sigma_volume",
        },
    )
    diffs_and_sums = pd.concat([diffs, sums], axis=1)
    return diffs_and_sums
