"""
Import as:

import core.finance.volatility as cfinvola
"""
import logging
from typing import List, Optional

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def _validate_data(
    df: pd.DataFrame,
    cols: List[str],
) -> None:
    """
    Ensure that `cols` belong to `df` and check types.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_container_type(cols, container_type=list, elem_type=str)
    hdbg.dassert_is_subset(cols, df.columns)


def _package_var(
    srs: pd.Series,
    take_square_root: bool,
    name_prefix: str,
) -> pd.DataFrame:
    """
    Maybe convert var to vol, name srs appropriately, and convert to df.
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    if take_square_root:
        srs = np.sqrt(srs)
        srs.name = name_prefix + "_vol"
    else:
        srs.name = name_prefix + "_var"
    return srs.to_frame()


def estimate_squared_volatility(
    df: pd.DataFrame,
    estimators: List[str],
    *,
    open_col: Optional[str] = None,
    high_col: Optional[str] = None,
    low_col: Optional[str] = None,
    close_col: Optional[str] = None,
    apply_log: bool = True,
    take_square_root: bool = False,
) -> pd.DataFrame:
    hdbg.dassert_container_type(estimators, container_type=list, elem_type=str)
    hdbg.dassert_lt(0, len(estimators))
    vols = []
    for vol_name in estimators:
        if vol_name == "close":
            vol = compute_close_var(
                df,
                close_col,
                apply_log=apply_log,
                take_square_root=take_square_root,
            )
        elif vol_name == "parkinson":
            vol = compute_parkinson_var(
                df,
                high_col,
                low_col,
                apply_log,
                take_square_root,
            )
        elif vol_name == "garman_klass":
            vol = compute_garman_klass_var(
                df,
                open_col,
                high_col,
                low_col,
                close_col,
                apply_log,
                take_square_root,
            )
        else:
            raise ValueError("Unsupported vol `%s`", vol_name)
        vols.append(vol)
    vols = pd.concat(vols, axis=1)
    return vols


def compute_close_var(
    df: pd.DataFrame,
    close_col: str,
    *,
    apply_log: bool = True,
    take_square_root: bool = False,
) -> pd.DataFrame:
    """
    Compute the close-to-close volatility [squared].

    Note that this is equivalent to the squared return of close prices.

    :param df: dataframe of close bar values
    :param close_col: name of close col
    :param apply_log: apply `log()` to data prior to var calculation iff True
    :param take_square_root: apply `np.sqrt()` to variance before returning
    :return: 1-col dataframe with close-to-close variance or sqrt variance
    """
    # Sanity-check data.
    cols = [close_col]
    _validate_data(df, cols)
    #
    close = df[cols]
    if apply_log:
        close = np.log(close)
    # Compute variance.
    close_diff = close[close_col].diff()
    variance = np.square(close_diff)
    # Package and return.
    result = _package_var(variance, take_square_root, "close")
    return result


def compute_parkinson_var(
    df: pd.DataFrame,
    high_col: str,
    low_col: str,
    # TODO(gp): Add *
    # *,
    apply_log: bool = True,
    take_square_root: bool = False,
) -> pd.DataFrame:
    """
    Compute the squared Parkinson volatility [squared].

    The Extreme Value Method for Estimating the Variance of the Rate of Return
    Michael Parkinson
    The Journal of Business, Vol. 53, No. 1 (Jan., 1980), pp. 61-65
    The University of Chicago Press

    :param df: dataframe of high and low bar values
    :param high_col: name of high-value col
    :param low_col: name of low-value col
    :param apply_log: apply `log()` to data prior to var calculation iff True
    :param take_square_root: apply `np.sqrt()` to variance before returning
    :return: 1-col dataframe with Parkinson variance
    """
    # Sanity-check data.
    cols = [high_col, low_col]
    _validate_data(df, cols)
    #
    hl = df[cols]
    if apply_log:
        hl = np.log(hl)
    # Compute variance.
    coeff = 1 / (4 * np.log(2))
    hl_diff = hl[high_col] - hl[low_col]
    variance = coeff * np.square(hl_diff)
    # Package and return.
    result = _package_var(variance, take_square_root, "parkinson")
    return result


def compute_garman_klass_var(
    df: pd.DataFrame,
    open_col: str,
    high_col: str,
    low_col: str,
    close_col: str,
    # TODO(gp): Add *
    # *,
    apply_log: bool = True,
    take_square_root: bool = False,
) -> pd.DataFrame:
    """
    Compute the squared Garman-Klass volatility.

    On the Estimation of Security Price Volatilities from Historical Data
    Mark B. Garman and Michael J. Klass
    The Journal of Business, Vol. 53, No. 1 (Jan., 1980), pp. 67-78
    The University of Chicago Press
    http://www.jstor.org/stable/2352358

    Here we use the simpler, "more practical" estimator found on page 74.

    :param df: dataframe of OHLC bar data
    :param open_col: name of open col
    :param high_col: name of high-value col
    :param low_col: name of low-value col
    :param close_col: name of close col
    :param apply_log: apply `log()` to data prior to var calculation iff True
    :param take_square_root: apply `np.sqrt()` to variance before returning
    :return: 1-col dataframe with Garman-Klass variance
    """
    # Sanity-check data.
    cols = [open_col, high_col, low_col, close_col]
    _validate_data(df, cols)
    #
    ohlc = df[cols]
    if apply_log:
        ohlc = np.log(ohlc)
    # Compute variance.
    hl_diff = ohlc[high_col] - ohlc[low_col]
    co_diff = ohlc[close_col] - ohlc[open_col]
    variance = 0.5 * np.square(hl_diff) - (2 * np.log(2) - 1) * np.square(co_diff)
    # Package and return.
    result = _package_var(variance, take_square_root, "garman_klass")
    return result


# TODO(Paul): Implement the Rogers-Satchell estimator
