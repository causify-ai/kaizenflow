"""
Import as:

import core.statistics.local_level_model as cslolemo
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def compute_local_level_model_stats(
    srs: pd.Series,
    prefix: Optional[str] = None,
) -> pd.Series:
    """
    Compute statistics assuming a steady-state local level model.

    E.g.,
       y_t = \mu_t + \epsilon_t
       \mu_{t + 1} = \mu_t + \eta_t

    This is equivalent to modeling `srs` of {y_t} as a random walk + noise at
    steady-state, or as ARIMA(0,1,1).

    See Harvey, Section 4.1.2, page 175.
    """
    prefix = prefix or ""
    hdbg.dassert_isinstance(srs, pd.Series)
    diff = srs.diff()
    demeaned_diff = diff - diff.mean()
    gamma0 = demeaned_diff.multiply(demeaned_diff).mean()
    gamma1 = demeaned_diff.multiply(demeaned_diff.shift(1)).mean()
    # This is the variance of \epsilon.
    var_epsilon = -1 * gamma1
    hdbg.dassert_lte(0, var_epsilon)
    # This is the variance of \eta.
    var_eta = gamma0 - 2 * var_epsilon
    hdbg.dassert_lte(0, var_eta)
    # This is the first autocorrelation coefficient.
    rho1 = gamma1 / gamma0
    # The signal-to-noise ratio `snr` is commonly denoted `q`.
    snr = var_eta / var_epsilon
    p = 0.5 * (snr + np.sqrt(snr**2 + 4 * snr))
    # Equivalent to EMA lambda in m_t = (1 - \lambda) m_{t - 1} + \lambda y_t.
    kalman_gain = p / (p + 1)
    # Convert to center-of-mass.
    com = 1 / kalman_gain - 1
    result_index = [
        prefix + "gamma0",
        prefix + "gamma1",
        prefix + "var_epsilon",
        prefix + "var_eta",
        prefix + "rho1",
        prefix + "snr",
        prefix + "kalman_gain",
        prefix + "com",
    ]
    result_values = [
        gamma0,
        gamma1,
        var_epsilon,
        var_eta,
        rho1,
        snr,
        kalman_gain,
        com,
    ]
    result = pd.Series(data=result_values, index=result_index, name=srs.name)
    return result
