"""
Import as:

import core.real_time as creatime
"""

import asyncio
import collections
import datetime
import logging
from typing import Any, AsyncGenerator, Callable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hnumpy as hnumpy
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)
# Enable extra verbose debugging. Do not commit.
_TRACE = False

# There are different ways of reproducing real-time behaviors:
# 1) True real-time
#    - We are running against the real prod / QA system
#    - The query to a DB returns the true real-time values, with different results
#      depending on the actual wall-clock time
# 2) Simulated real-time
#   - The advancing of time is simulated through calling a method (e.g.,
#     `set_current_time(simulated_time)`) or through a simulated version of the
#     `asyncio` `EventLoop`
# 3) Replayed time
#    - The wall-clock time is transformed into a historical wall-clock time
#    - E.g., 5:30pm today is remapped to 9:30pm of 2021-01-04
#    - Data is returned depending on the current wall-clock time
#      - The data can be frozen from a real-time system or synthetic
# 4) Simulated replayed time
#    - The time is simulated in terms of events and replayed in the past

# #############################################################################
# ReplayedTime.
# #############################################################################


# TODO(gp): -> _ReplayedTime
class ReplayedTime:
    """
    Allow to test a real-time system replaying current times in the past.

    A use case is the following:
    - Assume we have captured data in an interval starting on `2021-01-04 9:30am`
      (called `initial_replayed_timestamp`) until the following day `2021-01-05 9:30am`
    - We want to replay this data in real-time starting now, which is by example
      `2021-06-04 10:30am` (called `initial_wall_clock_dt`)
    - We use this class to map times after `2021-06-04 10:30am` to the corresponding
      time after `2021-01-04 9:30am`
    - E.g., when we ask to this class the current "replayed" time at (wall clock
      time) `2021-06-04 12:00pm`, the class returns `2021-01-04 11:00am`, since 1hr
      has passed since the `initial_wall_clock_dt`

    In other terms this class mocks `datetime.datetime.now()` so that the actual
    wall clock time `initial_wall_clock_dt` corresponds to `initial_replayed_timestamp`.
    """

    def __init__(
        self,
        initial_replayed_timestamp: pd.Timestamp,
        get_wall_clock_time: hdateti.GetWallClockTime,
        *,
        speed_up_factor: float = 1.0,
    ):
        """
        Construct the class instance.

        If param `initial_replayed_timestamp` has timezone info then this class works in
        the same timezone.

        :param initial_replayed_timestamp: the time that we want the current wall clock
            time to correspond to
        :param get_wall_clock_time: return the wall clock time. It is usually
            a closure of `hdateti.get_wall_clock_time()`. The returned time needs
            to have the same timezone as `initial_replayed_timestamp`
        """
        # This is the original time we want to "rewind" to.
        hdbg.dassert_isinstance(initial_replayed_timestamp, pd.Timestamp)
        self._initial_replayed_timestamp = initial_replayed_timestamp
        hdbg.dassert_isinstance(get_wall_clock_time, Callable)
        self._get_wall_clock_time = get_wall_clock_time
        hdbg.dassert_lt(0, speed_up_factor)
        self._speed_up_factor = speed_up_factor
        # This is when the experiment starts.
        self._initial_wall_clock_dt = self._get_wall_clock_time()
        _LOG.debug(
            hprint.to_str(
                "self._initial_replayed_timestamp self._initial_wall_clock_dt"
            )
        )
        hdateti.dassert_tz_compatible(
            self._initial_replayed_timestamp, self._initial_wall_clock_dt
        )
        # TODO(gp): Difference between amp and cmamp.
        # hdbg.dassert_lte(
        #    self._initial_replayed_timestamp,
        #    self._initial_wall_clock_dt,
        #    msg="Replaying time can be done only for the past. "
        #    "The future can't be replayed yet",
        # )

    def get_wall_clock_time(self) -> pd.Timestamp:
        """
        Transform the current time into the time corresponding to the real-time
        experiment starting at `initial_replayed_timestamp`.
        """
        now = self._get_wall_clock_time()
        hdbg.dassert_lte(self._initial_wall_clock_dt, now)
        elapsed_time = now - self._initial_wall_clock_dt
        current_replayed_timestamp = (
            self._initial_replayed_timestamp
            + self._speed_up_factor * elapsed_time
        )
        return current_replayed_timestamp


def get_replayed_wall_clock_time(
    tz: str,
    initial_replayed_timestamp: pd.Timestamp,
    *,
    event_loop: Optional[asyncio.AbstractEventLoop] = None,
    speed_up_factor: float = 1.0,
) -> hdateti.GetWallClockTime:
    """
    Return a function reporting the wall clock time using a replayed approach
    for real and simulated time.
    """
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz, event_loop=event_loop
    )
    replayed_time = ReplayedTime(
        initial_replayed_timestamp,
        get_wall_clock_time,
        speed_up_factor=speed_up_factor,
    )
    return replayed_time.get_wall_clock_time


# #############################################################################


# TODO(gp): This doesn't belong here, but it's not clear where should it go.
def generate_synthetic_data(
    columns: List[str],
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    *,
    freq: str = "1T",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic data used to mimic real-time data.
    """
    hdateti.dassert_tz_compatible(start_datetime, end_datetime)
    hdbg.dassert_lte(start_datetime, end_datetime)
    dates = pd.date_range(start_datetime, end_datetime, freq=freq)
    # TODO(gp): Filter by ATH, if needed.
    # Random walk with increments independent and uniform in [-0.5, 0.5].
    with hnumpy.random_seed_context(seed):
        data = np.random.rand(len(dates), len(columns)) - 0.5  # type: ignore[var-annotated]
    df = pd.DataFrame(data, columns=columns, index=dates)
    df = df.cumsum()
    return df


# TODO(gp): datetime_ -> as_of_timestamp
def get_data_as_of_datetime(
    df: pd.DataFrame,
    knowledge_datetime_col_name: Optional[str],
    datetime_: pd.Timestamp,
    *,
    delay_in_secs: int = 0,
    allow_future_peeking: bool = False,
) -> pd.DataFrame:
    """
    Extract data available at `datetime_` from a df indexed with knowledge
    time.

    :param df: df indexed with timestamp representing knowledge time
    :param knowledge_datetime_col_name: column in the df representing the knowledge time,
        or `None` for using the index
    :param datetime_: the "as of" timestamp (in the sense of `<=`)
    :param delay_in_secs: represent how long it takes for the simulated system to
        respond. E.g., if the data comes from a DB, `delay_in_secs` is the delay
        of the data query with respect to the knowledge time.

    E.g., if the "as of" timestamp is `2021-07-13 13:01:00` and the simulated system
    takes 4 seconds to respond, all and only data before `2021-07-13 13:00:56` is
    returned.
    """
    _LOG.debug(
        hprint.to_str(
            "knowledge_datetime_col_name datetime_ delay_in_secs allow_future_peeking"
        )
    )
    if _TRACE:
        _LOG.trace(
            hpandas.df_to_str(
                df, print_shape_info=True, tag="Before get_data_as_of_datetime"
            )
        )
    hdbg.dassert_lte(0, delay_in_secs)
    datetime_eff = datetime_ - datetime.timedelta(seconds=delay_in_secs)
    # TODO(gp): We could / should use binary search.
    hdateti.dassert_tz_compatible_timestamp_with_df(
        datetime_, df, knowledge_datetime_col_name
    )
    if not allow_future_peeking:
        # Filter the df to the values before and including `datetime_eff`.
        start_ts = None
        end_ts = datetime_eff
        left_close = True
        right_close = True
        # TODO(Grisha): decide if we should do either `[start_ts, end_ts)` or
        #  `[start_ts, end_ts]`.
        df = hpandas.trim_df(
            df,
            knowledge_datetime_col_name,
            start_ts,
            end_ts,
            left_close,
            right_close,
        )
    else:
        # Sometimes we need to allow the future peeking. E.g., to know what's the
        # execution price of an order that will terminate in the future.
        raise ValueError("Future peeking")
        # pass
    if _TRACE:
        _LOG.trace(
            hpandas.df_to_str(
                df, print_shape_info=True, tag="After get_data_as_of_datetime"
            )
        )
    return df


# #############################################################################
# Real time.
# #############################################################################


# TODO(gp): Move to hasyncio.py

# TODO(gp): Inline this function.
async def _sleep(sleep_in_secs: float) -> None:
    hdbg.dassert_lte(0, sleep_in_secs)
    await asyncio.sleep(sleep_in_secs)


async def align_on_time_grid(
    get_wall_clock_time: hdateti.GetWallClockTime,
    bar_duration_in_secs: int,
    *,
    use_high_resolution: bool = False,
) -> None:
    """
    Wait until the current wall clock time is aligned on
    `bar_duration_in_secs`.

    E.g., for `bar_duration_in_secs` = 2, if wall clock time is `2021-07-29 10:45:51`,
    then this function terminates when the wall clock is `2021-07-29 10:46:00`.

    :param use_high_resolution: `time.sleep()` has low resolution, so by
        default this function spins on the wall clock until the proper amount of
        time has elapsed
    """
    _LOG.info("Aligning on %s secs", bar_duration_in_secs)

    async def _wait(sleep_in_secs: float) -> None:
        _LOG.debug("wall_clock=%s", get_wall_clock_time())
        _LOG.debug("wait for %s secs", sleep_in_secs)
        if sleep_in_secs > 0:
            await asyncio.sleep(sleep_in_secs)
            _LOG.debug("wall_clock=%s", get_wall_clock_time())

    # _LOG.debug("Aligning at wall_clock=%s ...", get_wall_clock_time())
    target_time, secs_to_wait = hasynci.get_seconds_to_align_to_grid(
        bar_duration_in_secs, get_wall_clock_time
    )
    #
    if use_high_resolution:
        # Wait for a bit and then busy wait.
        await _wait(secs_to_wait - 1)
        # Busy waiting. Operating system courses say to never do this, but in this
        # case we need a high-resolution wait.
        while True:
            current_time = get_wall_clock_time()
            if current_time >= target_time:
                break
    else:
        await _wait(secs_to_wait)
    _LOG.debug("Aligning done at wall_clock=%s", get_wall_clock_time())


class Event(
    collections.namedtuple("Event", "num_it current_time wall_clock_time")
):
    """
    Information about the real time execution.

    :param num_it: number of iteration of the clock
    :param current_time: the simulated time
    :param wall_clock_time: the actual wall clock time of the running system for
        accounting
    """

    def __str__(self) -> str:
        return self.to_str(
            include_tenths_of_secs=False, include_wall_clock_time=True
        )

    # From
    # https://docs.python.org/3/library/collections.html#
    #    namedtuple-factory-function-for-tuples-with-named-fields

    def to_str(
        self, include_tenths_of_secs: bool, include_wall_clock_time: bool
    ) -> str:
        vals = []
        vals.append(f"num_it={self.num_it}")
        #
        current_time = self.current_time
        if not include_tenths_of_secs:
            current_time = current_time.replace(microsecond=0, nanosecond=0)
        vals.append(f"current_time='{current_time}'")
        #
        if include_wall_clock_time:
            vals.append(f"wall_clock_time='{self.wall_clock_time}'")
        return " ".join(vals)


class Events(List[Event]):
    """
    A list of events.
    """

    def __str__(self) -> str:
        return "\n".join(map(str, self))

    def to_str(self, *args: Any, **kwargs: Any) -> str:
        return "\n".join([x.to_str(*args, **kwargs) for x in self])


async def execute_with_real_time_loop(
    get_wall_clock_time: hdateti.GetWallClockTime,
    bar_duration_in_secs: int,
    # TODO(gp): -> exit_condition
    rt_timeout_in_secs_or_time: Optional[Union[int, datetime.time, pd.Timestamp]],
    workload: Callable[[pd.Timestamp], Any],
) -> AsyncGenerator[Tuple[Event, Any], None]:
    """
    Execute a function using an event loop.

    :param get_wall_clock_time: function returning the current true or simulated time
    :param bar_duration_in_secs: the loop wakes up every `bar_duration_in_secs`
        true or simulated seconds
    :param rt_timeout_in_secs_or_time: for how long to execute the loop
        - int: number of iterations to execute
        - datetime.time: time of the day to iterate until, in the same timezone
            as `get_wall_clock_time()`
        - `None` means an infinite loop
    :param workload: function executing the workload

    :return: a Tuple with:
        - an execution trace representing the events in the real-time loop; and
        - a list of results returned by the workload function
    """
    _LOG.debug(hprint.to_str("bar_duration_in_secs rt_timeout_in_secs_or_time"))
    hdbg.dassert(
        callable(get_wall_clock_time),
        "get_wall_clock_time='%s' is not callable",
        str(get_wall_clock_time),
    )
    hdbg.dassert_isinstance(bar_duration_in_secs, int)
    hdbg.dassert_lt(0, bar_duration_in_secs)
    # Number of iterations executed.
    num_it = 1
    while True:
        wall_clock_time = get_wall_clock_time()
        # For the wall clock time, we always use the real one. This is used only for
        # book-keeping.
        real_wall_clock_time = hdateti.get_current_time(tz="ET")
        hprint.log_frame(
            _LOG,
            "Real-time loop: "
            + "num_it=%s: rt_time_out_in_secs=%s wall_clock_time='%s' real_wall_clock_time='%s'",
            num_it,
            rt_timeout_in_secs_or_time,
            wall_clock_time,
            real_wall_clock_time,
            level=1,
            verbosity=logging.INFO,
        )
        # Update the current events.
        event = Event(num_it, wall_clock_time, real_wall_clock_time)
        _LOG.debug("event='%s'", str(event))
        # Execute workload.
        _LOG.debug(
            "await for next bar (bar_duration_in_secs=%s wall_clock_time=%s) ...",
            bar_duration_in_secs,
            get_wall_clock_time(),
        )
        # TODO(gp): Compensate for drift.
        result = await asyncio.gather(  # type: ignore[var-annotated]
            asyncio.sleep(bar_duration_in_secs),
            # We need to use the passed `wall_clock_time` since that's what being
            # used as real, simulated, replayed time.
            workload(wall_clock_time),
        )
        _LOG.debug("await done (wall_clock_time=%s)", get_wall_clock_time())
        _, workload_result = result
        yield event, workload_result
        # Exit, if needed.
        if rt_timeout_in_secs_or_time is not None:
            if isinstance(rt_timeout_in_secs_or_time, int):
                num_iterations = int(
                    rt_timeout_in_secs_or_time / bar_duration_in_secs
                )
                hdbg.dassert_lt(0, num_iterations)
                is_done = num_it >= num_iterations
                _LOG.debug(
                    hprint.to_str(
                        "rt_timeout_in_secs_or_time "
                        "bar_duration_in_secs "
                        "num_it "
                        "num_iterations "
                        "is_done"
                    )
                )
                if is_done:
                    _LOG.info(
                        "Exiting loop: %s", hprint.to_str("num_it num_iterations")
                    )
                    break
            elif isinstance(rt_timeout_in_secs_or_time, datetime.time):
                curr_time = wall_clock_time.time()
                is_done = curr_time >= rt_timeout_in_secs_or_time
                _LOG.debug(
                    hprint.to_str("rt_timeout_in_secs_or_time curr_time is_done")
                )
                if is_done:
                    _LOG.info(
                        "Exiting loop: %s",
                        hprint.to_str("curr_time rt_timeout_in_secs_or_time"),
                    )
                    break
            elif isinstance(rt_timeout_in_secs_or_time, pd.Timestamp):
                curr_time = wall_clock_time
                _LOG.debug(hprint.to_str("curr_time rt_timeout_in_secs_or_time"))
                if curr_time >= rt_timeout_in_secs_or_time:
                    _LOG.debug(
                        "Exiting loop: %s",
                        hprint.to_str("curr_time rt_timeout_in_secs_or_time"),
                    )
                    break
            else:
                raise ValueError(
                    f"Can't process rt_timeout_in_secs_or_time={rt_timeout_in_secs_or_time} of type "
                    + f"'{type(rt_timeout_in_secs_or_time)}'"
                )
        num_it += 1


async def execute_all_with_real_time_loop(
    *args: Any, **kwargs: Any
) -> Tuple[List[Event], List[Any]]:
    """
    Execute the entire event loop until the end.

    This is a way to bridge the async to sync semantic. It is
    conceptually equivalent to adding a list around a Python generator.
    """
    vals = zip(*[v async for v in execute_with_real_time_loop(*args, **kwargs)])
    events, results = list(vals)
    events = Events(events)
    results = list(results)
    return events, results
