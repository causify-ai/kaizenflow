"""
Import as:

import core.statistics.interarrival_time as cstintim
"""

import logging
from typing import Optional

import pandas as pd

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# #############################################################################
# Interarrival time statistics
# #############################################################################


def get_interarrival_time(
    srs: pd.Series,
    nan_mode: Optional[str] = None,
) -> Optional[pd.Series]:
    """
    Get interrarival time from index of a time series.

    :param srs: pandas series of floats
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :return: series with interrarival time
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    if data.empty:
        _LOG.warning("Empty input `%s`", srs.name)
        return None
    index = data.index
    # Check index of a series. We require that the input
    #     series have a sorted datetime index.
    hdbg.dassert_isinstance(index, pd.DatetimeIndex)
    hpandas.dassert_strictly_increasing_index(index)
    # Compute a series of interrairival time.
    interrarival_time = pd.Series(index).diff()
    return interrarival_time


def compute_interarrival_time_stats(
    srs: pd.Series,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute interarrival time statistics.

    :param srs: pandas series of interrarival time
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series with statistic and related info
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    result_index = [
        prefix + "n_unique",
        prefix + "mean",
        prefix + "std",
        prefix + "min",
        prefix + "max",
    ]
    nan_result = pd.Series(index=result_index, name=data.name, dtype="object")
    if data.shape[0] < 2:
        _LOG.warning(
            "Input series `%s` with size '%d' is too small",
            srs.name,
            data.shape[0],
        )
        return nan_result
    interarrival_time = get_interarrival_time(data)
    if interarrival_time is None:
        return nan_result
    n_unique = interarrival_time.nunique()
    mean = interarrival_time.mean()
    std = interarrival_time.std()
    min_value = interarrival_time.min()
    max_value = interarrival_time.max()
    #
    result_values = [n_unique, mean, std, min_value, max_value]
    res = pd.Series(
        data=result_values, index=result_index, name=srs.name, dtype="object"
    )
    return res
