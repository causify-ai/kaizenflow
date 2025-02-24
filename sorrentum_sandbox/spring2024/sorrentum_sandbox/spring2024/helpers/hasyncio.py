"""
Import as:

import helpers.hasyncio as hasynci
"""
import asyncio
import contextlib
import datetime
import logging
import math
import time
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

import async_solipsism
import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hprint as hprint

# Avoid dependency from other `helpers` modules, such as `helpers.hsql`, to prevent
# import cycles.


_LOG = logging.getLogger(__name__)

# #############################################################################
# Wrappers around `asyncio` to switch among true and simulated real-time loops.
# #############################################################################


# TODO(gp): We could make this a mixin and add this behavior to both asyncio and
#  async_solipsism event loop.
# TODO(gp): -> _AsyncSolipsismEventLoop
# TODO(gp): Consider injecting a `get_wall_clock_time: hdatetim.GetWallClockTime`
#  in the event loop so we can simplify the interfaces. An event loop always needs
#  a function to get the wall clock.
class _EventLoop(async_solipsism.EventLoop):
    """
    An `async_solipsism.EventLoop` returning also the wall-clock time.
    """

    # TODO(gp): If we pass an `initial_replayed_timestamp` we could incorporate here also
    #  the replayed time approach and can remove `ReplayedTime` object.
    def __init__(self) -> None:
        super().__init__()
        self._initial_dt = datetime.datetime.utcnow()

    def get_current_time(self) -> datetime.datetime:
        # `loop.time()` returns the number of seconds as `float` from when the event
        # loop was created.
        try:
            num_secs = super().time()
        except AttributeError:
            # Sometimes we call the logger before `async_solipsism` is fully initialized.
            #   File "/app/amp/helpers/hdatetime.py", line 255, in get_current_time
            #     timestamp = event_loop.get_current_time()
            #   File "/app/amp/helpers/hasyncio.py", line 60, in get_current_time
            #     num_secs = super().time()
            #   File "/venv/lib/python3.8/site-packages/async_solipsism/loop.py", line 39, in time
            #     return self._selector.clock.time()
            # AttributeError: 'NoneType' object has no attribute 'clock'
            # Call stack:
            #   File "/app/amp/helpers/hcache.py", line 311, in clear_global_cache
            #     _LOG.info("After clear_global_cache: %s", info_after)
            # Message: 'After clear_global_cache: %s'
            # Arguments: ("'global mem' cache: path='/mnt/tmpfs/tmp.cache.mem', size=nan",)
            # To avoid the error above we just set the `num_secs` to 0.
            num_secs = 0
        return self._initial_dt + datetime.timedelta(seconds=num_secs)


# From https://stackoverflow.com/questions/49555991
@contextlib.contextmanager
def solipsism_context() -> Iterator:
    """
    Context manager to isolate an `asyncio_solipsism` event loop.
    """
    # Use the variation of solipsistic `EventLoop` above.
    event_loop = _EventLoop()
    asyncio.set_event_loop(event_loop)
    try:
        yield event_loop
    finally:
        asyncio.set_event_loop(None)


async def gather_coroutines_with_wall_clock(
    event_loop: asyncio.AbstractEventLoop, *coroutines: List[Coroutine]
) -> List[Any]:
    """
    Inject a wall clock associated to `event_loop` in all the coroutines and
    then gathers them in a single coroutine.
    """
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="ET", event_loop=event_loop
    )
    # Construct the coroutines here by passing the `get_wall_clock_time()`
    # function.
    coroutines = [coro(get_wall_clock_time) for coro in coroutines]
    #
    result: List[Any] = await asyncio.gather(*coroutines)
    return result


# TODO(gp): For some reason `asyncio.run()` doesn't seem to pick up the new event
#  loop. So we use a re-implementation of `run` that does that.
def run(
    coroutine: Coroutine,
    event_loop: Optional[asyncio.AbstractEventLoop],
    *,
    close_event_loop: bool = True,
) -> Any:
    """
    `asyncio.run()` wrapper that allows to use a specified `EventLoop`.

    :param coroutine: the coroutine to run
    :param event_loop: the event loop to use. `None` means the standard `asyncio`
        event loop
    :param close_event_loop: if False the event loop is not closed, so that we can
        run multiple times in the same event loop
    :return: same output of `run_until_complete()`
    """
    if event_loop is None:
        # Use a normal `asyncio` EventLoop.
        event_loop = asyncio.new_event_loop()
    hdbg.dassert_issubclass(event_loop, asyncio.AbstractEventLoop)
    hprint.log_frame(_LOG, "asyncio.run")
    try:
        ret = event_loop.run_until_complete(coroutine)
    finally:
        if close_event_loop:
            event_loop.close()
    return ret


# #############################################################################
# Synchronous / asynchronous polling.
# #############################################################################


# The result of a polling function in terms of a bool indicating success (which
# when True stops the polling) and a result.
PollOutput = Tuple[bool, Any]

# A polling function accepts any inputs and returns a `PollOutput` in terms of
# (success, result). Typically polling functions don't accept any inputs and are
# built through lambdas and closures.
PollingFunction = Callable[[Any], PollOutput]


def _get_max_num_iterations(
    sleep_in_secs: float,
    timeout_in_secs: float,
) -> int:
    hdbg.dassert_lt(0, sleep_in_secs)
    hdbg.dassert_lt(0, timeout_in_secs)
    max_num_iter = int(math.ceil(timeout_in_secs / sleep_in_secs))
    hdbg.dassert_lte(1, max_num_iter)
    return max_num_iter


# TODO(gp): This is probably better implemented with an iterator.
def _poll_iterate(
    polling_func: PollingFunction,
    sleep_in_secs: float,
    timeout_in_secs: float,
    get_wall_clock_time: hdateti.GetWallClockTime,
    num_iter: int,
    max_num_iter,
    tag: str,
) -> Tuple[int, PollOutput]:
    """
    Execute an iteration of the polling loop.

    :return: the number of iterations executed and the output of the
        polling function (sucess, return value)
    :raises: TimeoutError in case of timeout
    """
    _LOG.debug(
        "\n## %s: wall clock time=%s: iter=%s/%s",
        tag,
        get_wall_clock_time(),
        num_iter,
        max_num_iter,
    )
    hdbg.dassert_isinstance(get_wall_clock_time, Callable)
    # Poll.
    success, value = polling_func()
    _LOG.debug("success=%s, value=%s", success, value)
    if success:
        # If success, then exit.
        hprint.log_frame(
            _LOG,
            "%s: wall clock time=%s: poll done",
            tag,
            get_wall_clock_time(),
        )
    else:
        # Otherwise update state.
        num_iter += 1
        if num_iter > max_num_iter:
            msg = "Timeout for " + hprint.to_str(
                "polling_func sleep_in_secs timeout_in_secs tag"
            )
            _LOG.error(msg)
            raise TimeoutError(msg)
    return num_iter, (success, value)


# TODO(gp): -> async_poll
async def poll(
    polling_func: PollingFunction,
    sleep_in_secs: float,
    timeout_in_secs: float,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    tag: Optional[str] = None,
) -> Tuple[int, Any]:
    """
    Call `polling_func()` every `sleep_in_secs` secs until the polling function
    returns success or there is a timeout. A timeout happens if no success is
    achieved within `timeout_in_secs` secs.

    :param polling_func: function returning a tuple (success, value)
    :return:
        - number of iterations before a successful call to `polling_func`
        - result from `polling_func`
    :raises: TimeoutError in case of timeout
    """
    _LOG.debug(hprint.to_str("polling_func sleep_in_secs timeout_in_secs tag"))
    if tag is None:
        # Use the function calling this function.
        tag = hintros.get_function_name(count=0)
    max_num_iter = _get_max_num_iterations(sleep_in_secs, timeout_in_secs)
    num_iter = 1
    while True:
        num_iter, (success, value) = _poll_iterate(
            polling_func,
            sleep_in_secs,
            timeout_in_secs,
            get_wall_clock_time,
            num_iter,
            max_num_iter,
            tag,
        )
        if success:
            return num_iter, value
        _LOG.debug("sleep for %s secs", sleep_in_secs)
        await asyncio.sleep(sleep_in_secs)


def sync_poll(
    polling_func: PollingFunction,
    sleep_in_secs: float,
    timeout_in_secs: float,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    tag: Optional[str] = None,
) -> Tuple[int, Any]:
    """
    Same interface and behavior of `poll()` but using a synchronous
    implementation.
    """
    _LOG.debug(hprint.to_str("polling_func sleep_in_secs timeout_in_secs tag"))
    if tag is None:
        # Use the function calling this function.
        tag = hintros.get_function_name(count=0)
    max_num_iter = _get_max_num_iterations(sleep_in_secs, timeout_in_secs)
    num_iter = 1
    while True:
        num_iter, (success, value) = _poll_iterate(
            polling_func,
            sleep_in_secs,
            timeout_in_secs,
            get_wall_clock_time,
            num_iter,
            max_num_iter,
            tag,
        )
        if success:
            return success, value
        _LOG.debug("sleep for %s secs", sleep_in_secs)
        time.sleep(sleep_in_secs)


def get_poll_kwargs(
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    # TODO(gp): Avoid using defaults.
    sleep_in_secs: float = 1.0,
    timeout_in_secs: float = 10.0,
) -> Dict[str, Any]:
    hdbg.dassert_lt(0, sleep_in_secs)
    hdbg.dassert_lt(0, timeout_in_secs)
    hdbg.dassert_isinstance(get_wall_clock_time, Callable)
    poll_kwargs = {
        "sleep_in_secs": sleep_in_secs,
        "timeout_in_secs": timeout_in_secs,
        "get_wall_clock_time": get_wall_clock_time,
    }
    return poll_kwargs


# #############################################################################
# Wait.
# #############################################################################


# Represent a deterministic, if float, or random delay in [a, b] if a Tuple.
# All values are in seconds.
WaitInSecs = Union[float, Tuple[float, float]]


async def sleep(
    delay_in_secs: WaitInSecs,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    # TODO(gp): -> msg
    tag: Optional[str] = None,
    # TODO(gp): How to handle random seed here?
    seed: int = 42,
) -> None:
    """
    Wait a deterministic or a randomized delay.
    """
    if tag is None:
        # Use the name of the function calling this function.
        tag = hintros.get_function_name(count=0)
    # Extract or compute the delay.
    if isinstance(delay_in_secs, (int, float)):
        # Deterministic delay.
        pass
    elif isinstance(delay_in_secs, tuple):
        # Randomized delay.
        hdbg.dassert_eq(len(delay_in_secs), 2)
        min_, max_ = delay_in_secs
        hdbg.dassert_lte(0, min_)
        hdbg.dassert_lte(min_, max_)
        delay_in_secs = np.random.rand(min_, max_)
    else:
        raise ValueError(f"Invalid delay_in_secs='{delay_in_secs}'")
    # Wait.
    hprint.log_frame(
        _LOG,
        "%s: wall_clock_time=%s: started waiting for %s secs",
        tag,
        get_wall_clock_time(),
        delay_in_secs,
    )
    hdbg.dassert_lte(0, delay_in_secs)
    delay_in_secs = cast(float, delay_in_secs)
    await asyncio.sleep(delay_in_secs)
    hprint.log_frame(
        _LOG,
        "%s: wall_clock_time=%s: done waiting for %s secs",
        tag,
        get_wall_clock_time(),
        delay_in_secs,
    )


# //////////////////////////////////////////////////////////////////////////////////


def get_seconds_to_align_to_grid(
    bar_duration_in_secs: int,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    add_buffer_in_secs: int = 0,
) -> Tuple[pd.Timestamp, int]:
    """
    Given the current time return the amount of seconds to wait to align on a
    grid with period `bar_duration_in_secs`.

    E.g., current_time=9:31:02am, bar_duration_in_secs=120 -> return 58

    :param add_buffer_in_secs: number of seconds to add to make sure we
        are right after the grid time
    """
    hdbg.dassert_lte(0, add_buffer_in_secs)
    current_time = get_wall_clock_time()
    _LOG.debug("current_time=%s ...", current_time)
    # Align on the time grid.
    hdbg.dassert_isinstance(bar_duration_in_secs, int)
    hdbg.dassert_lt(0, bar_duration_in_secs)
    freq = f"{bar_duration_in_secs}S"
    target_time = current_time.ceil(freq)
    hdbg.dassert_lte(current_time, target_time)
    _LOG.debug("target_time=%s", target_time)
    secs_to_wait = (target_time - current_time).total_seconds()
    # E.g., for
    #   target_time=2022-07-11 11:30:00-04:00
    #   curr_time=2022-07-11 11:29:15.129365-04:00
    # The difference is 44secs, so we need to add 1 sec to make sure we pass
    # the target time.
    secs_to_wait += add_buffer_in_secs
    return target_time, secs_to_wait


def _wait_until(
    wait_until_timestamp: pd.Timestamp,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    tag: Optional[str] = None,
) -> float:
    """
    Return amount of seconds to wait for.

    More accurate version of _wait_until, uses total_seconds() which
    allows for returning fractional second values.
    """
    if tag is None:
        # Use the name of the function calling this function.
        tag = hintros.get_function_name(count=2)
    curr_timestamp = get_wall_clock_time()
    _LOG.debug(
        "wait_until_timestamp=%s, curr_timestamp=%s",
        wait_until_timestamp,
        curr_timestamp,
    )
    # We can only wait for times in the future.
    if curr_timestamp > wait_until_timestamp:
        _LOG.warning(
            "curr_timestamp=%s, wait_until_timestamp=%s is in the future: "
            "continuing ",
            curr_timestamp,
            wait_until_timestamp,
        )
        time_in_secs = 0
    else:
        time_in_secs = (wait_until_timestamp - curr_timestamp).total_seconds()
        _LOG.debug(
            "%s: wall_clock_time=%s: sleep for %s secs",
            tag,
            get_wall_clock_time(),
            time_in_secs,
        )
    return time_in_secs


def sync_wait_until(
    wait_until_timestamp: pd.Timestamp,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    tag: Optional[str] = None,
    log_verbosity: int = logging.DEBUG,
) -> None:
    """
    Synchronous wait until the wall clock time is `timestamp`.

    More accurate version of sync_wait_until allowing to wait for
    fractional seconds.
    """
    # Sync wait.
    time_in_secs = _wait_until(wait_until_timestamp, get_wall_clock_time, tag=tag)
    hdbg.dassert_lte(0, time_in_secs)
    # TODO(gp): Consider using part of align_on_time_grid for high-precision clock.
    time.sleep(time_in_secs)
    #
    hprint.log_frame(
        _LOG,
        "%s: wall_clock_time=%s: done waiting",
        tag,
        get_wall_clock_time(),
        verbosity=log_verbosity,
    )


async def async_wait_until(
    wait_until_timestamp: pd.Timestamp,
    get_wall_clock_time: hdateti.GetWallClockTime,
    *,
    # TODO(gp): -> msg
    tag: Optional[str] = None,
) -> None:
    """
    Asynchronous wait until the wall clock time is `timestamp`.
    """
    _LOG.debug(hprint.to_str("wait_until_timestamp"))
    time_in_secs = _wait_until(wait_until_timestamp, get_wall_clock_time, tag=tag)
    # Async wait.
    hdbg.dassert_lte(0, time_in_secs)
    await asyncio.sleep(time_in_secs)
    #
    hprint.log_frame(
        _LOG, "%s: wall_clock_time=%s: done waiting", tag, get_wall_clock_time()
    )
