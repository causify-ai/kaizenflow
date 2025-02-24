"""
Import as:

import core.statistics.t_test as cstttes
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def ttest_1samp(
    srs: pd.Series,
    popmean: Optional[float] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Thin wrapper around scipy's ttest.

    :param srs: input series for computing statistics
    :param popmean: assumed population mean for test
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param prefix: optional prefix for metrics' outcome
    :return: series with t-value and p-value
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    nan_mode = nan_mode or "drop"
    prefix = prefix or ""
    popmean = popmean or 0
    data = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    result_index = [
        prefix + "tval",
        prefix + "pval",
    ]
    nan_result = pd.Series(data=np.nan, index=result_index, name=srs.name)
    if data.empty:
        _LOG.warning("Empty input series `%s`", srs.name)
        return nan_result
    try:
        tval, pval = sp.stats.ttest_1samp(
            data, popmean=popmean, nan_policy="raise"
        )
    except ValueError as inst:
        _LOG.warning(inst)
        return nan_result
    result_values = [
        tval,
        pval,
    ]
    result = pd.Series(data=result_values, index=result_index, name=data.name)
    return result
