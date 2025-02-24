import asyncio
import logging
from typing import Optional

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_hasyncio1(hunitest.TestCase):
    """
    Execute a workload using different time semantics:

    - real time
    - simulated time
    """

    @staticmethod
    async def workload(get_wall_clock_time: hdateti.GetWallClockTime) -> None:
        """
        Coroutine simulating a workload waiting for 1s.
        """

        def _print_time() -> None:
            true_wall_clock_time = hdateti.get_current_time("ET")
            _LOG.debug("wall_clock_time=%s", true_wall_clock_time)
            event_loop_time = get_wall_clock_time()
            _LOG.debug("event_loop_time=%s", event_loop_time)

        _print_time()
        # The execution here is just waiting.
        _LOG.debug("  -> execute")
        await asyncio.sleep(1.0)
        #
        _print_time()

    def run_test(
        self,
        event_loop: Optional[asyncio.AbstractEventLoop],
        get_wall_clock_time: hdateti.GetWallClockTime,
    ) -> None:
        coroutine = self.workload(get_wall_clock_time)
        hasynci.run(coroutine, event_loop=event_loop)

    def test_real_time1(self) -> None:
        """
        Use real-time semantic.

        In this case:
        ```
        wall_clock_time=2021-09-27 20:40:43.775683-04:00
        event_loop_time=2021-09-27 20:40:43.799074-04:00
          -> execute
        wall_clock_time=2021-09-27 20:40:44.808990-04:00
        event_loop_time=2021-09-27 20:40:44.812472-04:00
        ```

        - the wall clock time and the event loop time both advance
        """
        # Use the wall clock time with no special event loop.
        get_wall_clock_time = lambda: hdateti.get_current_time(tz="ET")
        event_loop = None
        # Run.
        self.run_test(event_loop, get_wall_clock_time)

    def test_simulated_time1(self) -> None:
        """
        Use simulated time semantic.

        In this case:
        ```
        wall_clock_time=2021-09-27 20:38:47.843501-04:00
        event_loop_time=2021-09-27 20:38:47.841555-04:00
          -> execute
        wall_clock_time=2021-09-27 20:38:47.868272-04:00
        event_loop_time=2021-09-27 20:38:48.841555-04:00
        ```

        - the wall_clock time doesn't advance since the execution is instantaneous
        - the event loop time moves forward 1 sec
        """
        # Use the solipsistic event loop to simulate the real-time faster.
        with hasynci.solipsism_context() as event_loop:
            # Use the simulated wall clock time.
            get_wall_clock_time = lambda: hdateti.get_current_time(
                tz="ET", event_loop=event_loop
            )
            # Run.
            self.run_test(event_loop, get_wall_clock_time)
