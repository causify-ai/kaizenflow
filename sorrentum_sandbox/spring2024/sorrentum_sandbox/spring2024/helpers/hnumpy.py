"""
Import as:

import helpers.hnumpy as hnumpy
"""

import contextlib
from typing import Iterator

import numpy as np

import helpers.hdbg as hdbg

# From https://stackoverflow.com/questions/49555991
@contextlib.contextmanager
def random_seed_context(seed: int) -> Iterator:
    """
    Context manager to isolate a numpy random seed.
    """
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        yield
    finally:
        np.random.set_state(state)


# TODO(Juraj): unit test in CmTask5092.
def floor_with_precision(value: float, amount_precision: int) -> float:
    """
    Floor a value using desired precision.
    
    The invariant for this function is that negative number are floored based
    on their absolute value: e.g floor_with_precision(-4.6, 0) == -4. This is
    useful for calculating share size where there are decimal precision
    limitations. The desired behavior is to rather round down than overfill.
    
    Other examples:
    floor_with_precision(0.125, 2) == 0.12
    floor_with_precision(0.4, 0) == 0.0
    
    :param value: value to floor with desire
    :param amount_precision: number of decimal points to floor to
    :return: value floored using desired precision.
    """
    # Custom solution to allow flooring using precision.
    # https://stackoverflow.com/questions/58065055/floor-and-ceil-with-number-of-decimals/58065394#58065394
    # Precision < 0 does not make sense.
    hdbg.dassert_lte(0, amount_precision)
    # Store sign and get absolute value to get the desire
    sign = -1 if value < 0 else 1
    value_abs = abs(value)
    value_floored = np.true_divide(
        np.floor(value_abs * 10**amount_precision), 
        10**amount_precision
    )
    return value_floored * sign
