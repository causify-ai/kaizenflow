"""
Import as:

import helpers.hnumba as hnumba
"""

import logging
from typing import Any, Callable, TypeVar

try:
    import numba

    numba_available = True
except ImportError:
    numba_available = False

_LOG = logging.getLogger(__name__)

# Switch to enable numba at run-time.
# For using in notebooks you need to force a reload of the library, like:
#   import importlib
#   importlib.reload(numba_)
#   numba_.USE_NUMBA = False

USE_NUMBA = True
RT = TypeVar("RT")  # Return type for decorator.


def jit(f: Callable[..., RT]) -> Callable[..., RT]:

    if USE_NUMBA and not numba_available:
        _LOG.warning("numba is not installed")
    use_numba = USE_NUMBA and numba_available

    if use_numba:
        _LOG.debug("Using numba!")
        wrapper: Callable[..., RT] = numba.jit(f)
    else:

        def wrapper(*args: Any, **kwargs: Any) -> RT:
            _LOG.debug("Not using numba!")
            return f(*args, **kwargs)

    return wrapper
