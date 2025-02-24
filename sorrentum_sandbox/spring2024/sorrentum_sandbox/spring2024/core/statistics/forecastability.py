"""
Import as:

import core.statistics.forecastability as cstafore
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import scipy as sp

import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# TODO(Paul): Change the interface so that this returns a float.
def compute_forecastability(
    signal: pd.Series,
    mode: str = "welch",
    inf_mode: Optional[str] = None,
    nan_mode: Optional[str] = None,
    prefix: Optional[str] = None,
) -> pd.Series:
    r"""Compute frequency-domain-based "forecastability" of signal.

    Reference: https://arxiv.org/abs/1205.4591

    `signal` is assumed to be second-order stationary.

    Denote the forecastability estimator by \Omega(\cdot).
    Let x_t, y_t be time series. Properties of \Omega include:
    a) \Omega(y_t) = 0 iff y_t is white noise
    b) scale and shift-invariant:
         \Omega(a y_t + b) = \Omega(y_t) for real a, b, a \neq 0.
    c) max sub-additivity for uncorrelated processes:
         \Omega(\alpha x_t + \sqrt{1 - \alpha^2} y_t) \leq
         \max\{\Omega(x_t), \Omega(y_t)\},
       if \E(x_t y_s) = 0 for all s, t \in \Z;
       equality iff alpha \in \{0, 1\}.
    """
    hdbg.dassert_isinstance(signal, pd.Series)
    nan_mode = nan_mode or "fill_with_zero"
    inf_mode = inf_mode or "drop"
    prefix = prefix or ""
    data = hdatafr.apply_nan_mode(signal, mode=nan_mode)
    has_infs = (~data.apply(np.isfinite)).any()
    # Make an output for empty or too short inputs.
    nan_result = pd.Series(
        data=[np.nan],
        index=[prefix + "forecastability"],
        name=signal.name,
    )
    if has_infs:
        if inf_mode == "return_nan":
            return nan_result
        if inf_mode == "drop":
            # Replace inf with np.nan and drop.
            data = data.replace([-np.inf, np.inf], np.nan).dropna()
        else:
            raise ValueError(f"Unrecognized inf_mode `{inf_mode}")
    hdbg.dassert(data.apply(np.isfinite).all())
    # Return NaN if there is no data.
    if data.size == 0:
        _LOG.warning("Empty input signal `%s`", signal.name)
        nan_result = pd.Series(
            data=np.nan, index=[prefix + "forecastability"], name=signal.name
        )
        return nan_result
    if mode == "welch":
        _, psd = sp.signal.welch(data)
    elif mode == "periodogram":
        # TODO(Paul): Maybe log a warning about inconsistency of periodogram
        #     for estimating power spectral density.
        _, psd = sp.signal.periodogram(data)
    else:
        raise ValueError("Unsupported mode=`%s`" % mode)
    forecastability = 1 - sp.stats.entropy(psd, base=psd.size)
    res = pd.Series(
        data=[forecastability],
        index=[prefix + "forecastability"],
        name=signal.name,
    )
    return res
