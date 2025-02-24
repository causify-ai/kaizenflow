"""
Import as:

import helpers.hwall_clock_time as hwacltim
"""

# This should have no dependencies besides Python standard libraries since it's used
# in `helpers/hlogging.py`.

import datetime
import logging
from typing import Callable, Optional, Union

_LOG = logging.getLogger(__name__)

# TODO(gp): Consider adding a `import pandas as pd` to use the type hints.

# #############################################################################
# Simulated real time
# #############################################################################

# Copied from `helpers/hdatetime.py`
#
# Function returning the current (true, replayed, simulated) wall-clock time as a
# timestamp.
_GetWallClockTime = Callable[[], "pd.Timestamp"]

_get_wall_clock_time_func: Optional[_GetWallClockTime] = None


def set_wall_clock_time(get_wall_clock_time_func_: _GetWallClockTime) -> None:
    """
    Set the global function to retrieve the wall clock time.
    """
    assert callable(get_wall_clock_time_func_)
    global _get_wall_clock_time_func
    _get_wall_clock_time_func = get_wall_clock_time_func_


def get_wall_clock_time_func() -> Optional[_GetWallClockTime]:
    """
    Retrieve the global function retrieve the wall clock time.
    """
    return _get_wall_clock_time_func


# We don't want to import `Pandas` just for a type.
def get_wall_clock_time() -> Optional["pd.Timestamp"]:
    """
    Return the wall clock time (according to the set function) or `None` if no
    function was set.
    """
    func = _get_wall_clock_time_func
    if func is None:
        timestamp = None
    else:
        timestamp = func()
    return timestamp


# #############################################################################
# Real-world / machine real time.
# #############################################################################


# TODO(Sameep): Redundant fuction replace by `hdatetime.timestamp_to_str()`.
def to_timestamp_str(
    timestamp: "pd.Timestamp", include_msec: bool = False
) -> str:
    if include_msec:
        # Chop the last 4 miliseconds digits. This is needed for CcxtBroker_v2.
        return timestamp.strftime("%Y%m%d_%H%M%S%f")[:-4]
    else:
        return timestamp.strftime("%Y%m%d_%H%M%S")


# This is redundant with `hdatetime.get_current_time()` and
# `hdateti.get_current_timestamp_as_string()` but we keep them to simplify
# dependencies.
def get_machine_wall_clock_time(
    *,
    as_str: bool = False,
    include_msec: bool = False,
) -> Union[str, datetime.datetime]:
    ret = datetime.datetime.utcnow()
    if as_str:
        ret = to_timestamp_str(ret, include_msec)
    return ret


# #############################################################################
# Current bar being processed.
# #############################################################################


_CURR_BAR_TIMESTAMP: Optional["pd.Timestamp"] = None


def reset_current_bar_timestamp() -> None:
    global _CURR_BAR_TIMESTAMP
    _LOG.debug("Reset")
    _CURR_BAR_TIMESTAMP = None


def set_current_bar_timestamp(timestamp: "pd.Timestamp") -> None:
    _LOG.debug("timestamp=%s", timestamp)
    global _CURR_BAR_TIMESTAMP
    if _CURR_BAR_TIMESTAMP is not None:
        # TODO(Grisha): should we relax the check by using
        # `<=` instead of `<`?
        assert _CURR_BAR_TIMESTAMP < timestamp, (
            "Bar timestamp can only move forward: "
            + f"{_CURR_BAR_TIMESTAMP} <= {timestamp}"
        )
    _CURR_BAR_TIMESTAMP = timestamp


def get_current_bar_timestamp(
    *,
    as_str: bool = False,
    include_msec: bool = False,
) -> Optional[Union[str, "pd.Timestamp"]]:
    ret = _CURR_BAR_TIMESTAMP
    if _CURR_BAR_TIMESTAMP and as_str:
        ret = to_timestamp_str(ret, include_msec=include_msec)
    return ret
