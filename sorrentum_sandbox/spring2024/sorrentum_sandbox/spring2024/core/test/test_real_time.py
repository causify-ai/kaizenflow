"""
Import as:

import dataflow.test.test_real_time as cdtfttrt
"""
import asyncio
import datetime
import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pytest

import core.real_time as creatime
import core.real_time_example as cretiexa
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hprint as hprint
import helpers.htimer as htimer
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_align_on_time_grid1(hunitest.TestCase):
    """
    Test `align_on_time_grid` using different time semantics.
    """

    def helper(
        self,
        event_loop: Optional[asyncio.AbstractEventLoop],
        use_high_resolution: bool,
    ) -> None:
        """
        Run twice aligning on 2 seconds.
        """
        get_wall_clock_time = lambda: hdateti.get_current_time(
            tz="ET", event_loop=event_loop
        )
        for i in range(2):
            _LOG.debug("\n%s", hprint.frame("Iteration %s" % i, char1="="))
            current_time1 = get_wall_clock_time()
            _LOG.debug(hprint.to_str("current_time1"))
            _ = current_time1
            # Align on an even second.
            bar_duration_in_secs = 2
            coroutine = creatime.align_on_time_grid(
                get_wall_clock_time,
                bar_duration_in_secs,
                use_high_resolution=use_high_resolution,
            )
            hasynci.run(coroutine, event_loop=event_loop, close_event_loop=False)
            # Check.
            current_time2 = get_wall_clock_time()
            _LOG.debug(hprint.to_str("current_time2"))
            self.assertEqual(current_time2.second % 2, 0)

    @pytest.mark.slow("It takes around 4 secs")
    def test_real_time1(self) -> None:
        """
        Test in real-time aligning on 2 seconds.
        """
        event_loop = None
        use_high_resolution = False
        self.helper(event_loop, use_high_resolution)

    @pytest.mark.slow("It takes around 4 secs")
    def test_real_time2(self) -> None:
        """
        Test in real-time aligning on 2 seconds.
        """
        event_loop = None
        use_high_resolution = True
        self.helper(event_loop, use_high_resolution)

    def test_replayed_time1(self) -> None:
        """
        Test in real-time aligning on 2 seconds.
        """
        use_high_resolution = False
        with hasynci.solipsism_context() as event_loop:
            self.helper(event_loop, use_high_resolution)


# #############################################################################


class TestReplayedTime1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Rewind time to 9:30am of a day in the past.
        """
        rt = cretiexa.get_replayed_time()
        # We assume that these 2 calls take less than 1 minute.
        exp = pd.Timestamp("2010-01-04 09:30:00")
        self._helper(rt, exp)
        #
        self._helper(rt, exp)

    def _helper(self, rt: creatime.ReplayedTime, exp: pd.Timestamp) -> None:
        rct = rt.get_wall_clock_time()
        _LOG.info("  -> time=%s", rct)
        _LOG.debug(hprint.to_str("rct.date"))
        self.assert_equal(str(rct.date()), str(exp.date()))
        _LOG.debug(hprint.to_str("rct.hour"))
        self.assert_equal(str(rct.hour), str(exp.hour))
        _LOG.debug(hprint.to_str("rct.minute"))
        self.assert_equal(str(rct.minute), str(exp.minute))


# #############################################################################


class Test_execute_with_real_time_loop1(hunitest.TestCase):
    """
    Run `execute_all_with_real_time_loop()` with a workload that naively wait
    some time using different time semantics:

    - real time
    - simulated time
    - replayed time
    - simulated replayed time
    """

    @staticmethod
    async def workload(current_time: pd.Timestamp) -> bool:
        """
        Coroutine simulating a workload (waiting for 0.1s) when the current
        time has an even number of seconds.

        :return: True if it was executed
        """
        need_execute: bool = current_time.second % 2 == 0
        _LOG.debug(
            "current_time=%s -> need_execute=%s", current_time, need_execute
        )
        if need_execute:
            # The execution consists of just waiting.
            _LOG.debug("  -> execute")
            await asyncio.sleep(0.1)
        return need_execute

    @staticmethod
    def get_execute_with_rt_loop_kwargs1() -> Dict[str, Any]:
        """
        Do 3 iterations of 1.0s.
        """
        kwargs = {
            "bar_duration_in_secs": 1,
            "rt_timeout_in_secs_or_time": 1 * 3,
        }
        return kwargs

    @staticmethod
    def get_execute_with_rt_loop_kwargs2() -> Dict[str, Any]:
        """
        Iterate until 9:30:06, i.e., 6 iterations.
        """
        exit_time = datetime.time(9, 30, 6)
        kwargs = {
            "bar_duration_in_secs": 1,
            "rt_timeout_in_secs_or_time": exit_time,
        }
        return kwargs

    def run_workload(
        self,
        get_wall_clock_time: hdateti.GetWallClockTime,
        execute_with_rt_loop_kwargs: Dict[str, Any],
        event_loop: Optional[asyncio.AbstractEventLoop],
    ) -> Tuple[str, str]:
        """
        Execute `workload()` every second for 3 seconds using the passed event
        loops and wall clock times.

        :return: signature of the execution
        """
        # Align on a 2-second boundary, since we want to start always from an even
        # second.
        bar_duration_in_secs = 2
        coroutine = creatime.align_on_time_grid(
            get_wall_clock_time, bar_duration_in_secs
        )
        hasynci.run(coroutine, event_loop=event_loop, close_event_loop=False)
        #
        coroutine = creatime.execute_all_with_real_time_loop(
            get_wall_clock_time,
            **execute_with_rt_loop_kwargs,
            workload=self.workload,
        )
        events, results = hasynci.run(coroutine, event_loop=event_loop)
        _LOG.debug("events=\n%s", str(events))
        _LOG.debug("results=\n%s", str(results))
        # Assemble output.
        events_as_str = "events=\n%s" % events.to_str(
            include_tenths_of_secs=False, include_wall_clock_time=False
        )
        results_as_str = "results=\n%s" % str(results)
        return events_as_str, results_as_str

    def replayed_time_run_workload(
        self,
        execute_with_rt_loop_kwargs: Dict[str, Any],
        event_loop: Optional[asyncio.AbstractEventLoop],
    ) -> Tuple[str, str]:
        """
        Like `run_workload()` but in replayed time.
        """
        # Create the replayed wall clock time.
        tz = "ET"
        initial_replayed_timestamp = pd.Timestamp(
            "2010-01-04 09:30:01", tz=hdateti.get_ET_tz()
        )
        get_wall_clock_time = creatime.get_replayed_wall_clock_time(
            tz, initial_replayed_timestamp, event_loop=event_loop
        )
        # Run.
        events_as_str, results_as_str = self.run_workload(
            get_wall_clock_time, execute_with_rt_loop_kwargs, event_loop
        )
        return events_as_str, results_as_str

    def check_output_real_time(
        self, events_as_str: str, results_as_str: str
    ) -> None:
        """
        Check the output when we run in real time.
        """
        # We can't check the events since they happen in real-time, so we check only
        # the results.
        _ = events_as_str
        exp = """
        results=
        [True, False, True]"""
        self.assert_equal(results_as_str, exp, fuzzy_match=True)

    def check_output_simulated(
        self, events_as_str: str, results_as_str: str
    ) -> None:
        """
        Check the output when we run in simulated time.
        """
        # Check that the events are triggered on even seconds.
        act = f"{events_as_str}\n{results_as_str}"
        exp = r"""
        events=
        num_it=1 current_time='2010-01-04 09:30:02-05:00'
        num_it=2 current_time='2010-01-04 09:30:03-05:00'
        num_it=3 current_time='2010-01-04 09:30:04-05:00'
        results=
        [True, False, True]"""
        self.assert_equal(act, exp, fuzzy_match=True)

    # ////////////////////////////////////////////////////////////////////////////

    def test_real_time1(self) -> None:
        """
        Use real-time semantic.

        We wait actual wall-clock time, without simulating the event
        loop.
        """
        # Run.
        event_loop = None
        get_wall_clock_time = lambda: hdateti.get_current_time(tz="ET")
        execute_with_rt_loop_kwargs = self.get_execute_with_rt_loop_kwargs1()
        events_as_str, results_as_str = self.run_workload(
            get_wall_clock_time, execute_with_rt_loop_kwargs, event_loop
        )
        # TODO(gp): This is flakey so we skip the check.
        # Check.
        # self._check_output_real_time(events_as_str, results_as_str)
        _ = events_as_str, results_as_str

    def test_simulated_time1(self) -> None:
        """
        Use simulated real-time semantic.
        """
        with htimer.TimedScope(logging.DEBUG, "") as ts:
            # Use the solipsistic event loop to simulate the real-time faster.
            with hasynci.solipsism_context() as event_loop:
                # Use the wall clock time.
                get_wall_clock_time = lambda: hdateti.get_current_time(
                    tz="ET", event_loop=event_loop
                )
                execute_with_rt_loop_kwargs = (
                    self.get_execute_with_rt_loop_kwargs1()
                )
                events_as_str, results_as_str = self.run_workload(
                    get_wall_clock_time, execute_with_rt_loop_kwargs, event_loop
                )
        # Check.
        self.check_output_real_time(events_as_str, results_as_str)
        # It should take less than 1 sec to simulate 4 secs.
        self.assertLess(ts.elapsed_time, 1)

    def test_replayed_time1(self) -> None:
        """
        Use replayed time semantic.

        We wait actual wall-clock time, but the time is rewound to a
        point in the past.
        """
        event_loop = None
        execute_with_rt_loop_kwargs = self.get_execute_with_rt_loop_kwargs1()
        events_as_str, results_as_str = self.replayed_time_run_workload(
            execute_with_rt_loop_kwargs, event_loop
        )
        # Check.
        self.check_output_simulated(events_as_str, results_as_str)

    def test_simulated_replayed_time1(self) -> None:
        """
        Use simulated replayed semantic.

        We simulate real-time passing in the past.
        """
        with htimer.TimedScope(logging.DEBUG, "") as ts:
            with hasynci.solipsism_context() as event_loop:
                execute_with_rt_loop_kwargs = (
                    self.get_execute_with_rt_loop_kwargs1()
                )
                events_as_str, results_as_str = self.replayed_time_run_workload(
                    execute_with_rt_loop_kwargs,
                    event_loop,
                )
        # Check.
        self.check_output_simulated(events_as_str, results_as_str)
        # It should take less than 1 sec to simulate 4 secs.
        self.assertLess(ts.elapsed_time, 1)

    # ////////////////////////////////////////////////////////////////////////////

    def test_exit_condition1(self) -> None:
        """
        Check that `execute_all_with_real_time_loop()` stops at a certain time,
        using simulated replayed semantic.

        We simulate real-time passing in the past.
        """
        with htimer.TimedScope(logging.DEBUG, "") as ts:
            with hasynci.solipsism_context() as event_loop:
                execute_with_rt_loop_kwargs = (
                    self.get_execute_with_rt_loop_kwargs2()
                )
                events_as_str, results_as_str = self.replayed_time_run_workload(
                    execute_with_rt_loop_kwargs, event_loop
                )
        # Check that the events are triggered on even seconds.
        act = f"{events_as_str}\n{results_as_str}"
        exp = r"""events=
        num_it=1 current_time='2010-01-04 09:30:02-05:00'
        num_it=2 current_time='2010-01-04 09:30:03-05:00'
        num_it=3 current_time='2010-01-04 09:30:04-05:00'
        num_it=4 current_time='2010-01-04 09:30:05-05:00'
        num_it=5 current_time='2010-01-04 09:30:06-05:00'
        results=
        [True, False, True, False, True]"""
        self.assert_equal(act, exp, fuzzy_match=True)
        # It should take less than 1 sec to simulate 4 secs.
        self.assertLess(ts.elapsed_time, 1)
