import logging
import time

import helpers.htimer as htimer
import helpers.hunit_test as hunitest


class TestTimedScope(hunitest.TestCase):
    def test_1(self) -> None:
        """
        Test that elapsed time is correctly computed.
        """
        # Run the function to test.
        with htimer.TimedScope(logging.INFO, "Test") as ts:
            time.sleep(1)
        # Round actual time up to 1 decimal and compare it with expected.
        actual_rounded_time = round(ts.elapsed_time, 1)
        expected_rounded_time = 1.0
        self.assertEqual(actual_rounded_time, expected_rounded_time)
