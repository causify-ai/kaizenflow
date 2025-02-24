"""
Import as:

import core.real_time_example as cretiexa
"""

import asyncio
import logging
from typing import Callable, Optional, Tuple

import pandas as pd

import core.real_time as creatime
import helpers.hdatetime as hdateti
import helpers.htypes as htypes

_LOG = logging.getLogger(__name__)


def get_test_data_builder1() -> Tuple[Callable, htypes.Kwargs]:
    """
    Return a data builder producing between "2010-01-04 09:30:00" and
    "2010-01-04 09:35:00" (for 5 minutes) every second.

    :return: `data_builder` and its kwargs for use inside a dataflow node.
    """
    data_builder = creatime.generate_synthetic_data
    data_builder_kwargs = {
        "columns": ["close", "volume"],
        "start_datetime": pd.Timestamp("2010-01-04 09:30:00"),
        "end_datetime": pd.Timestamp("2010-01-05 09:30:00"),
        "freq": "1S",
        "seed": 42,
    }
    return data_builder, data_builder_kwargs


def get_test_data_builder2() -> Tuple[Callable, htypes.Kwargs]:
    """
    Return a data builder producing data between "2010-01-04 09:30:00" and
    "2010-01-04 09:30:05" (for 5 seconds) every second.

    :return: `data_builder` and its kwargs for use inside a dataflow node.
    """
    data_builder = creatime.generate_synthetic_data
    data_builder_kwargs = {
        "columns": ["close", "volume"],
        "start_datetime": pd.Timestamp("2010-01-04 09:30:00"),
        "end_datetime": pd.Timestamp("2010-01-04 09:30:05"),
        "freq": "1S",
        "seed": 42,
    }
    return data_builder, data_builder_kwargs


# TODO(gp): -> _get_replayed_time? This should not be used.
# TODO(gp): Make `event_loop` mandatory.
def get_replayed_time(
    *,
    event_loop: Optional[asyncio.AbstractEventLoop] = None,
) -> creatime.ReplayedTime:
    """
    Build a `ReplayedTime` object starting at the same time as the data (i.e.,
    "2010-01-04 09:30:00").
    """
    start_datetime = pd.Timestamp("2010-01-04 09:30:00")
    # Use a replayed real-time starting at the same time as the data.
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="naive_ET", event_loop=event_loop
    )
    rt = creatime.ReplayedTime(start_datetime, get_wall_clock_time)
    return rt


# TODO(gp): Make `event_loop` mandatory.
def get_replayed_time_execute_rt_loop_kwargs(
    bar_duration_in_secs: int,
    *,
    event_loop: Optional[asyncio.AbstractEventLoop] = None,
) -> htypes.Kwargs:
    """
    Return kwargs for a call to `execute_with_real_time_loop()` using replayed time.

    Same params as `execute_with_real_time_loop()`

    :param bar_duration_in_secs: the loop wakes up every `bar_duration_in_secs`
        true or simulated seconds
    """
    # TODO(gp): Replace all these with `get_replayed_wall_clock_time()`.
    rt = get_replayed_time(event_loop=event_loop)
    get_wall_clock_time = rt.get_wall_clock_time
    execute_rt_loop_kwargs = {
        "get_wall_clock_time": get_wall_clock_time,
        "bar_duration_in_secs": bar_duration_in_secs,
        "rt_timeout_in_secs_or_time": 3 * bar_duration_in_secs,
    }
    return execute_rt_loop_kwargs


# TODO(gp): move rt_timeout_in_secs_or_time to defaults, then kill the example.
# TODO(gp): Add "_example" to the end of the name.
def get_real_time_execute_rt_loop_kwargs(
    bar_duration_in_secs: int,
    *,
    event_loop: Optional[asyncio.AbstractEventLoop],
) -> htypes.Kwargs:
    """
    Return kwargs for a call to `execute_rt_loop` using real time.
    """
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="naive_ET", event_loop=event_loop
    )
    execute_rt_loop_kwargs = {
        "get_wall_clock_time": get_wall_clock_time,
        "bar_duration_in_secs": bar_duration_in_secs,
        # TODO(gp): This is the number of seconds the real time loop runs for.
        #  Change the name to something more intuitive.
        "rt_timeout_in_secs_or_time": 3 * bar_duration_in_secs,
    }
    return execute_rt_loop_kwargs
