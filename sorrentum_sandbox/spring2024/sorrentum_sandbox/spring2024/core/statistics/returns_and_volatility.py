"""
Import as:

import core.statistics.returns_and_volatility as csreanvo
"""
import logging
from typing import Optional, cast

import numpy as np
import pandas as pd

import core.statistics.signed_runs as cstsirun
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def compute_annualized_return_and_volatility(
    srs: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Annualized mean return and sample volatility in units of `srs`.

    :param srs: series with datetimeindex with `freq`
    :param prefix: optional prefix for metrics' outcome
    :return: annualized pd.Series with return and volatility
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    prefix = prefix or ""
    result_index = [
        prefix + "annualized_mean_return",
        prefix + "annualized_volatility",
    ]
    nan_result = pd.Series(
        np.nan, index=result_index, name=srs.name, dtype="float64"
    )
    if srs.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    annualized_mean_return = compute_annualized_return(srs)
    annualized_volatility = compute_annualized_volatility(srs)
    result = pd.Series(
        data=[annualized_mean_return, annualized_volatility],
        index=result_index,
        name=srs.name,
    )
    return result


def compute_annualized_return(srs: pd.Series) -> float:
    """
    Annualize mean return.

    :param srs: series with datetimeindex with `freq`
    :return: annualized return; pct rets if `srs` consists of pct rets,
        log rets if `srs` consists of log rets.
    """
    srs = maybe_resample(srs)
    srs = hdatafr.apply_nan_mode(srs, mode="fill_with_zero")
    ppy = hdatafr.infer_sampling_points_per_year(srs)
    mean_rets = srs.mean()
    annualized_mean_rets = ppy * mean_rets
    annualized_mean_rets = cast(float, annualized_mean_rets)
    return annualized_mean_rets


def compute_annualized_volatility(srs: pd.Series) -> float:
    """
    Annualize sample volatility.

    :param srs: series with datetimeindex with `freq`
    :return: annualized volatility (stdev)
    """
    srs = maybe_resample(srs)
    srs = hdatafr.apply_nan_mode(srs, mode="fill_with_zero")
    ppy = hdatafr.infer_sampling_points_per_year(srs)
    std = srs.std()
    annualized_volatility = np.sqrt(ppy) * std
    annualized_volatility = cast(float, annualized_volatility)
    return annualized_volatility


def maybe_resample(srs: pd.Series) -> pd.Series:
    """
    Return `srs` resampled to "B" `srs.index.freq` if is `None`.

    This is a no-op if `srs.index.freq` is not `None`.
    """
    hdbg.dassert_isinstance(srs.index, pd.DatetimeIndex)
    if srs.index.freq is None:
        _LOG.debug("No `freq` detected; resampling to 'B'.")
        srs = srs.resample("B").sum(min_count=1)
    return srs


def compute_returns_per_bet(
    positions: pd.Series, returns: pd.Series
) -> pd.Series:
    """
    Calculate returns for each bet.

    :param positions: series of long/short positions
    :param returns: percentage returns
    :return: signed returns for each bet (in units of `positions`), index
        corresponds to the last date of bet
    """
    hdbg.dassert(positions.index.equals(returns.index))
    hpandas.dassert_strictly_increasing_index(returns)
    bet_ends = cstsirun.compute_signed_run_ends(positions)
    # Retrieve locations of bet starts and bet ends.
    bet_ends_idx = bet_ends.loc[bet_ends != 0].dropna().index
    pnl_bets = returns * positions
    bet_rets_cumsum = pnl_bets.cumsum().ffill()
    # Select rets cumsum for periods when bets end.
    bet_rets_cumsum_ends = bet_rets_cumsum.loc[bet_ends_idx].reset_index(
        drop=True
    )
    # Difference between rets cumsum of bet ends is equal to the rets cumsum
    # for the time between these bet ends i.e. rets cumsum per bet.
    returns_per_bet = bet_rets_cumsum_ends.diff()
    # The 1st element of returns_per_bet equals the 1st one of bet_rets_cumsum_ends
    # because it is the first bet so nothing to subtract from it.
    returns_per_bet[0] = bet_rets_cumsum_ends[0]
    returns_per_bet = pd.Series(
        data=returns_per_bet.values, index=bet_ends_idx, name=returns.name
    )
    return returns_per_bet
