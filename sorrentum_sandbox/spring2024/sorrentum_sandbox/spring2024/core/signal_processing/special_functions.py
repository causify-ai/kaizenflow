"""
Import as:

import core.signal_processing.special_functions as csprspfu
"""

import logging
from typing import Union

import numpy as np

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def calculate_tau_from_com(com: float) -> Union[float, np.float64]:
    """
    Transform center-of-mass (com) into tau parameter.

    This is the function inverse of `calculate_com_from_tau`.
    """
    hdbg.dassert_lt(0, com)
    return 1.0 / np.log(1 + 1.0 / com)


def calculate_com_from_tau(tau: float) -> Union[float, np.float64]:
    """
    Transform tau parameter into center-of-mass (com).

    We use the tau parameter for kernels (as in Dacorogna, et al), but for the
    compute_ema operator want to take advantage of pandas' implementation, which uses
    different parameterizations. We adopt `com` because
        - It is almost equal to `tau`
        - We have used it historically

    :param tau: parameter used in (continuous) compute_ema and compute_ema-derived kernels. For
        typical ranges it is approximately but not exactly equal to the
        center-of-mass (com) associated with an compute_ema kernel.
    :return: com
    """
    hdbg.dassert_lt(0, tau)
    return 1.0 / (np.exp(1.0 / tau) - 1)


def c_infinity(x: float) -> float:
    """
    Return C-infinity function evaluated at x.

    This function is zero for x <= 0 and approaches exp(1) as x ->
    infinity.
    """
    if x > 0:
        return np.exp(-1 / x)
    return 0


def c_infinity_step_function(x: float) -> float:
    """
    Return C-infinity step function evaluated at x.

    This function is
      - 0 for x <= 0
      - 1 for x >= 1
    """
    fx = c_infinity(x)
    f1mx = c_infinity(1 - x)
    if fx + f1mx == 0:
        return np.nan
    return fx / (fx + f1mx)


def c_infinity_bump_function(x: float, a: float, b: float) -> float:
    """
    Return value of C-infinity bump function evaluated at x.

    :param x: point at which to evaluate
    :param a: function is 1 between -a and a
    :param b: function is zero for abs(x) >= b
    """
    hdbg.dassert_lt(0, a)
    hdbg.dassert_lt(a, b)
    y = (x**2 - a**2) / (b**2 - a**2)
    inverse_bump = c_infinity_step_function(y)
    return 1 - inverse_bump
