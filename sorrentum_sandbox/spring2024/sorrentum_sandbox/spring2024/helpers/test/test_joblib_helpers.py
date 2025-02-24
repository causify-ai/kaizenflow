import logging
import os
import time
from typing import Any, List, Optional, Union

import pytest

import helpers.hjoblib as hjoblib
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# #############################################################################


def workload_function(
    val1: int,
    val2: str,
    #
    **kwargs: Any,
) -> str:
    """
    Execute the test workload.
    """
    _LOG.info("Starting workload %s", val1)
    incremental = kwargs.pop("incremental")
    num_attempts = kwargs.pop("num_attempts")
    _ = val1, val2, incremental, num_attempts
    res: str = hprint.to_str("val1 val2 incremental num_attempts kwargs")
    _LOG.debug("res=%s", res)
    sleep = 0.01
    # sleep = 2
    time.sleep(sleep)
    _LOG.info("Ending workload %s", val1)
    if val1 == -1:
        raise ValueError(f"Error: {res}")
    return res


# #############################################################################
# Test_parallel_execute1
# #############################################################################


def get_workload1(
    randomize: bool, *, seed: Optional[int] = None
) -> hjoblib.Workload:
    """
    Return a workload for `workload_function()` with 5 tasks that succeeds.
    """
    tasks = []
    for i in range(5):
        # val1, val2
        task = ((i, 2 * i), {f"hello{i}": f"world{2 * i}", "good": "bye"})
        tasks.append(task)
    workload: hjoblib.Workload = (workload_function, "workload_function", tasks)
    if randomize:
        # Randomize workload.
        workload = hjoblib.randomize_workload(workload, seed=seed)
    return workload


class Test_parallel_execute1(hunitest.TestCase):
    """
    Execute a workload of 5 tasks that all succeed.
    """

    def test_dry_run1(self) -> None:
        """
        Dry-run a workload.
        """
        workload = get_workload1(randomize=True)
        dry_run = True
        num_threads = "serial"
        incremental = True
        num_attempts = 1
        abort_on_error = True
        log_file = os.path.join(self.get_scratch_space(), "log.txt")
        res = hjoblib.parallel_execute(
            workload,
            dry_run,
            num_threads,
            incremental,
            abort_on_error,
            num_attempts,
            log_file,
        )
        _LOG.debug("res=%s", str(res))
        self.assertIs(res, None)

    # pylint: disable=line-too-long
    EXPECTED_RETURN = r"""val1=0, val2=0, incremental=True, num_attempts=1, kwargs={'hello0': 'world0', 'good': 'bye'}
val1=1, val2=2, incremental=True, num_attempts=1, kwargs={'hello1': 'world2', 'good': 'bye'}
val1=2, val2=4, incremental=True, num_attempts=1, kwargs={'hello2': 'world4', 'good': 'bye'}
val1=3, val2=6, incremental=True, num_attempts=1, kwargs={'hello3': 'world6', 'good': 'bye'}
val1=4, val2=8, incremental=True, num_attempts=1, kwargs={'hello4': 'world8', 'good': 'bye'}"""
    # pylint: enable=line-too-long

    def test_serial1(self) -> None:
        num_threads = "serial"
        backend = ""
        self._run_test(num_threads, backend)

    def test_parallel_loky1(self) -> None:
        num_threads = "1"
        backend = "loky"
        self._run_test(num_threads, backend)

    @pytest.mark.requires_ck_infra
    @pytest.mark.slow("~6 seconds, see CmTask4951.")
    def test_parallel_loky2(self) -> None:
        num_threads = "3"
        backend = "loky"
        self._run_test(num_threads, backend)

    def test_parallel_asyncio_threading1(self) -> None:
        num_threads = "1"
        backend = "asyncio_threading"
        self._run_test(num_threads, backend)

    def test_parallel_asyncio_threading2(self) -> None:
        num_threads = "3"
        backend = "asyncio_threading"
        self._run_test(num_threads, backend)

    def _run_test(self, num_threads: Union[str, int], backend: str) -> None:
        workload = get_workload1(randomize=True)
        abort_on_error = True
        #
        expected_return = self.EXPECTED_RETURN
        _helper_success(
            self, workload, num_threads, abort_on_error, expected_return, backend
        )


# #############################################################################
# Test_parallel_execute2
# #############################################################################


def get_workload2() -> hjoblib.Workload:
    """
    Return a workload for `workload_function()` with 1 task that fails.
    """
    task = ((-1, 7), {"hello2": "world2", "good2": "bye2"})
    tasks = [task]
    workload: hjoblib.Workload = (workload_function, "workload_function", tasks)
    return workload


class Test_parallel_execute2(hunitest.TestCase):
    """
    Execute a workload of 1 task that fails.
    """

    # pylint: disable=line-too-long
    EXPECTED_STRING = r"""Error: val1=-1, val2=7, incremental=True, num_attempts=1, kwargs={'hello2': 'world2', 'good2': 'bye2'}"""

    def test_serial1(self) -> None:
        num_threads = "serial"
        abort_on_error = True
        backend = ""
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_serial2(self) -> None:
        num_threads = "serial"
        abort_on_error = False
        backend = ""
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    @pytest.mark.requires_ck_infra
    def test_parallel_loky1(self) -> None:
        num_threads = 2
        abort_on_error = True
        backend = "loky"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    @pytest.mark.requires_ck_infra
    def test_parallel_loky2(self) -> None:
        num_threads = 2
        abort_on_error = False
        backend = "loky"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading1(self) -> None:
        num_threads = 2
        abort_on_error = True
        backend = "asyncio_threading"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading2(self) -> None:
        num_threads = 2
        abort_on_error = False
        backend = "asyncio_threading"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    # pylint: enable=line-too-long

    def _run_test(
        self,
        abort_on_error: bool,
        num_threads: Union[str, int],
        backend: str,
        should_succeed: bool,
    ) -> None:
        workload = get_workload2()
        #
        expected_return = self.EXPECTED_STRING
        if should_succeed:
            _helper_success(
                self,
                workload,
                num_threads,
                abort_on_error,
                expected_return,
                backend,
            )
        else:
            _helper_fail(
                self,
                workload,
                num_threads,
                abort_on_error,
                expected_return,
                backend,
            )


# #############################################################################
# Test_parallel_execute3
# #############################################################################


def get_workload3(
    randomize: bool, seed: Optional[int] = None
) -> hjoblib.Workload:
    """
    Return a workload for `workload_function()` with 5 tasks succeeding and one
    task failing.
    """
    workload: hjoblib.Workload = get_workload1(randomize=True)
    # Modify the workflow in place.
    (workload_func, func_name, tasks) = workload
    _ = workload_func, func_name
    task = ((-1, 7), {"hello2": "world2", "good2": "bye2"})
    tasks.append(task)
    if randomize:
        # Randomize workload.
        workload = hjoblib.randomize_workload(workload, seed=seed)
    return workload


class Test_parallel_execute3(hunitest.TestCase):
    """
    Execute a workload with 5 tasks that succeed and 1 task that fails.
    """

    # pylint: disable=line-too-long
    EXPECTED_STRING1 = r"""Error: val1=-1, val2=7, incremental=True, num_attempts=1, kwargs={'hello2': 'world2', 'good2': 'bye2'}"""

    EXPECTED_STRING2 = r"""Error: val1=-1, val2=7, incremental=True, num_attempts=1, kwargs={'hello2': 'world2', 'good2': 'bye2'}
val1=0, val2=0, incremental=True, num_attempts=1, kwargs={'hello0': 'world0', 'good': 'bye'}
val1=1, val2=2, incremental=True, num_attempts=1, kwargs={'hello1': 'world2', 'good': 'bye'}
val1=2, val2=4, incremental=True, num_attempts=1, kwargs={'hello2': 'world4', 'good': 'bye'}
val1=3, val2=6, incremental=True, num_attempts=1, kwargs={'hello3': 'world6', 'good': 'bye'}
val1=4, val2=8, incremental=True, num_attempts=1, kwargs={'hello4': 'world8', 'good': 'bye'}"""

    def test_serial1(self) -> None:
        num_threads = "serial"
        abort_on_error = True
        backend = ""
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_serial2(self) -> None:
        """
        Execute:
        - a workload with 5 tasks that succeed and 1 task that fails
        - serially
        - don't abort because abort_on_error=False
        """
        num_threads = "serial"
        abort_on_error = False
        backend = ""
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_loky1(self) -> None:
        num_threads = "1"
        abort_on_error = True
        backend = "loky"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    @pytest.mark.requires_ck_infra
    def test_parallel_loky2(self) -> None:
        num_threads = "3"
        abort_on_error = True
        backend = "loky"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_loky3(self) -> None:
        num_threads = "1"
        abort_on_error = False
        backend = "loky"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    @pytest.mark.slow("~5 seconds.")
    def test_parallel_loky4(self) -> None:
        num_threads = "3"
        abort_on_error = False
        backend = "loky"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading1(self) -> None:
        num_threads = "1"
        abort_on_error = True
        backend = "asyncio_threading"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading2(self) -> None:
        num_threads = "3"
        abort_on_error = True
        backend = "asyncio_threading"
        #
        should_succeed = False
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading3(self) -> None:
        num_threads = "1"
        abort_on_error = False
        backend = "asyncio_threading"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    def test_parallel_asyncio_threading4(self) -> None:
        num_threads = "3"
        abort_on_error = False
        backend = "asyncio_threading"
        #
        should_succeed = True
        self._run_test(abort_on_error, num_threads, backend, should_succeed)

    # pylint: enable=line-too-long

    def _run_test(
        self,
        abort_on_error: bool,
        num_threads: Union[str, int],
        backend: str,
        should_succeed: bool,
    ) -> None:
        workload = get_workload3(randomize=False)
        # Since there is an error and `abort_on_error=True` we only get information
        # about the failed task.
        if should_succeed:
            expected_return = self.EXPECTED_STRING2
            _helper_success(
                self,
                workload,
                num_threads,
                abort_on_error,
                expected_return,
                backend,
            )
        else:
            # Since there is an error and `abort_on_error=True` we only get information
            # about the failed task.
            expected_exception = self.EXPECTED_STRING1
            _helper_fail(
                self,
                workload,
                num_threads,
                abort_on_error,
                expected_exception,
                backend,
            )


# #############################################################################


@pytest.mark.skip(reason="Just for experimenting with joblib")
class Test_joblib_example1(hunitest.TestCase):
    @staticmethod
    def func(val: int) -> int:
        print(f"val={val}")
        if val == -1:
            raise ValueError(f"val={val}")
        print(f"  out={val}")
        return val

    def test1(self) -> None:
        """
        Show that when a job fails the entire `joblib.Parallel` fails without
        returning anything, but just propagating the exception.
        """
        # num_threads = 5
        num_threads = 1
        vals = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        # vals[1] = -1
        vals[5] = -1
        import joblib

        backend = "loky"
        res = joblib.Parallel(n_jobs=num_threads, backend=backend, verbose=200)(
            joblib.delayed(Test_joblib_example1.func)(val) for val in vals
        )
        print(f"res={str(res)}")


# #############################################################################


def _outcome_to_string(outcome: List[str]) -> str:
    outcome = "\n".join(sorted(map(str, outcome)))
    return outcome


def _helper_success(
    self_: Any,
    workload: hjoblib.Workload,
    num_threads: Union[str, int],
    abort_on_error: bool,
    expected_return: str,
    backend: str,
) -> None:
    """
    Run a workload that is supposed to succeed and check its result.
    """
    dry_run = False
    incremental = True
    num_attempts = 1
    log_file = os.path.join(self_.get_scratch_space(), "log.txt")
    #
    res = hjoblib.parallel_execute(
        workload,
        dry_run,
        num_threads,
        incremental,
        abort_on_error,
        num_attempts,
        log_file,
        backend=backend,
    )
    # Check.
    _LOG.debug("res=%s", str(res))
    act = _outcome_to_string(res)
    self_.assert_equal(act, expected_return)


def _helper_fail(
    self_: Any,
    workload: hjoblib.Workload,
    num_threads: Union[str, int],
    abort_on_error: bool,
    expected_assertion: str,
    backend: str,
) -> None:
    dry_run = False
    incremental = True
    num_attempts = 1
    log_file = os.path.join(self_.get_scratch_space(), "log.txt")
    #
    with self_.assertRaises(ValueError) as cm:
        res = hjoblib.parallel_execute(
            workload,
            dry_run,
            num_threads,
            incremental,
            abort_on_error,
            num_attempts,
            log_file,
            backend=backend,
        )
        # Print result if it succeeds.
        _LOG.debug("res=%s", str(res))
    # Check.
    act = str(cm.exception)
    self_.assert_equal(act, expected_assertion)


# # To observe the output in real-time.
# if __name__ == "__main__":
#     hdbg.init_logger(verbosity=logging.INFO)
#     workload = get_workload1(randomize=True)
#     # num_threads = "serial"
#     num_threads = "1"
#     # num_threads = "5"
#     # backend = "loky"
#     backend = "asyncio_threading"
#     # backend = "asyncio_multiprocessing"
#     abort_on_error = True
#     #
#     dry_run = False
#     incremental = True
#     num_attempts = 1
#     log_file = "./log.txt"
#     #
#     _LOG.info("\n" + hprint.frame("Start workload"))
#     with htimer.TimedScope(logging.INFO, "Execute workload"):
#         res = hjoblib.parallel_execute(
#             workload,
#             dry_run,
#             num_threads,
#             incremental,
#             abort_on_error,
#             num_attempts,
#             log_file,
#             backend=backend,
#         )
#     _LOG.info("\n" + hprint.frame("Results"))
#     import pprint
#
#     print(pprint.pformat(res))
