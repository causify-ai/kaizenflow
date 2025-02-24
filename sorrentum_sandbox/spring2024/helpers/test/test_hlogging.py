import asyncio
import logging
from typing import Optional

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hlogging as hloggin
import helpers.hunit_test as hunitest
import helpers.hwall_clock_time as hwacltim

_LOG = logging.getLogger(__name__)


# #############################################################################


class Test_logging1(hunitest.TestCase):
    def test_logging_levels1(self) -> None:
        hloggin.test_logger()


# #############################################################################


class Test_hlogging_asyncio1(hunitest.TestCase):
    @staticmethod
    async def workload(get_wall_clock_time: hdateti.GetWallClockTime) -> None:
        """
        Coroutine simulating a workload waiting for 1s.
        """
        # Set the coroutine name.
        task = asyncio.current_task()
        task.set_name("workload")

        def _print_time() -> None:
            true_wall_clock_time = hdateti.get_current_time("ET")
            _LOG.debug("wall_clock_time=%s", true_wall_clock_time)
            event_loop_time = get_wall_clock_time()
            _LOG.debug("event_loop_time=%s", event_loop_time)

        _print_time()
        _LOG.debug("  -> wait")
        await asyncio.sleep(1.0)
        _print_time()

    def run_test(
        self,
        event_loop: Optional[asyncio.AbstractEventLoop],
        get_wall_clock_time: hdateti.GetWallClockTime,
    ) -> None:
        coroutine = self.workload(get_wall_clock_time)
        hasynci.run(coroutine, event_loop=event_loop)

    # pylint: disable=line-too-long
    def test_real_time1(self) -> None:
        """
        Use the logger.

        The output is like:

        ```
        07:55:54 hunit_test.py setUp:932                             Resetting random.seed to 20000101
        07:55:54 hunit_test.py setUp:935                             Resetting np.random.seed to 20000101
        07:55:54 hunit_test.py setUp:944                             base_dir_name=/app/amp/helpers/test
        ```
        """
        # Use the wall clock time with no special event loop.
        get_wall_clock_time = lambda: hdateti.get_current_time(tz="ET")
        event_loop = None
        # Run.
        self.run_test(event_loop, get_wall_clock_time)

    # pylint: disable=line-too-long
    def test_simulated_time1(self) -> None:
        """
        Use the logger with event_loop and asyncio.

        The output is like:

        ```
        07:52:55 @ 2022-01-18 02:52:55 workload test_hlogging.py _print_time:28 wall_clock_time=2022-01-18 07:52:55.337574-05:00
        07:52:55 @ 2022-01-18 02:52:55 workload test_hlogging.py _print_time:30 event_loop_time=2022-01-18 07:52:55.310587-05:00
        07:52:55 @ 2022-01-18 02:52:55 workload test_hlogging.py workload:33     -> wait
        ```
        """
        with hasynci.solipsism_context() as event_loop:
            # Use the simulate wall clock time.
            get_wall_clock_time = lambda: hdateti.get_current_time(
                tz="ET", event_loop=event_loop
            )
            hwacltim.set_wall_clock_time(get_wall_clock_time)
            # Run.
            self.run_test(event_loop, get_wall_clock_time)
