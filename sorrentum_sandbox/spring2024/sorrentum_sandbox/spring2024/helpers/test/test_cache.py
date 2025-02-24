import logging
import tempfile
import time
from typing import Any, Callable, Tuple

import numpy as np
import pandas as pd
import pytest

import helpers.hcache as hcache
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# TODO(gp): Do not commit this.
# _LOG.debug = _LOG.info


# TODO(gp): Use hprint.log_frame
def _LOG_frame(txt: str) -> None:
    _LOG.debug("\n%s", hprint.frame(txt))


# #############################################################################


def _get_add_function() -> Callable:
    """
    Return a function with the ability to track state, used for testing.
    """

    def func(x: int, y: int) -> int:
        func.executed = True  # type: ignore[attr-defined]
        return x + y

    func.executed = False  # type: ignore[attr-defined]
    return func


def _reset_add_function(func: Callable) -> None:
    """
    Reset the function before another execution, so we can verify if it was
    executed or not.

    We should do this every time we run the cached version of the
    function.
    """
    func.executed = False  # type: ignore[attr-defined]
    hdbg.dassert(not func.executed)  # type: ignore[attr-defined]


# #############################################################################


class _ResetGlobalCacheHelper(hunitest.TestCase):
    """
    Create a global cache for each test method and resets it at every test
    method invocation.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Create a tag like "TestCacheFeatures::test_without_caching1".
        self.cache_tag = f"{self.__class__.__name__}::{self._testMethodName}"
        # Clean all the caches before this test method is run.
        self._remove_all_caches()

    def tear_down_test(self) -> None:
        # Clean and remove all the caches after the test method is run.
        self._remove_all_caches()

    def _remove_all_caches(self) -> None:
        """
        Clean and remove all the caches for this test.
        """
        cache_type = "all"
        hcache.clear_global_cache(cache_type, tag=self.cache_tag, destroy=True)

    def _get_f_cf_functions(
        self, **cached_kwargs: Any
    ) -> Tuple[Callable, hcache._Cached]:
        """
        Create the intrinsic function `f` and its cached version `cf`.
        """
        # Make sure that we are using the unit test cache.
        # disk_cache_name = hcache._get_global_cache_name("disk", self.cache_tag)
        # _LOG.debug("disk_cache_name=%s", disk_cache_name)
        # _LOG.debug(
        #     "disk_cache_path=%s", hcache._get_global_cache_path("disk", self.cache_tag)
        # )
        # TODO(gp): Add an assertion.
        # Create the intrinsic function.
        f = _get_add_function()
        # Create the cached function.
        cf = hcache._Cached(f, tag=self.cache_tag, **cached_kwargs)
        # Reset all the caches.
        hcache.clear_global_cache("all", self.cache_tag)
        cf._reset_cache_tracing()
        return f, cf

    def _execute_and_check_state(
        self,
        f: Callable,
        cf: hcache._Cached,
        val1: int,
        val2: int,
        exp_cf_state: str,
    ) -> None:
        """
        Call the function `f(val1, val2) and its cached function `cf(val1,
        val2)` and check whether the intrinsic function was executed and what
        caches were used, according to `exp_f_state` and `exp_cf_state`.
        """
        # If there was no caching then we must have executed the function.
        exp_f_state = exp_cf_state == "no_cache"
        _LOG.debug(
            "\n%s",
            hprint.frame(
                f"val1={val1}, val2={val2}, exp_f_state={exp_f_state}, "
                f"exp_cf_state={exp_cf_state}",
                char1="<",
            ),
        )
        # Reset the intrinsic function since we want to verify if it was called
        # or not when we call the cached function.
        _reset_add_function(f)
        # Call the cached function.
        act = cf(val1, val2)
        exp = val1 + val2
        # Check the result.
        self.assertEqual(act, exp)
        # Check which function was executed and what caches were used.
        _LOG.debug(
            "f.executed=%s vs %s",
            f.executed,  # type: ignore[attr-defined]
            exp_f_state,
        )
        _LOG.debug(
            "cf.get_last_cache_accessed=%s vs %s",
            cf.get_last_cache_accessed(),
            exp_cf_state,
        )
        self.assertEqual(f.executed, exp_f_state)  # type: ignore[attr-defined]
        self.assertEqual(cf.get_last_cache_accessed(), exp_cf_state)


# #############################################################################


class TestCacheFunctions(hunitest.TestCase):
    def test_get_cache_name1(self) -> None:
        """
        Make sure we are using the unit test cache and not the development
        cache, by checking the name of the disk cache.
        """
        cache_tag = "unittest"
        disk_cache_name = hcache._get_global_cache_name("disk", cache_tag)
        _LOG.debug("disk_cache_name=%s", disk_cache_name)
        self.assertIn(cache_tag, disk_cache_name)


# #############################################################################


class TestGlobalCache1(_ResetGlobalCacheHelper):
    def test_without_caching1(self) -> None:
        """
        If we execute two times without caching, we get two executions of the
        intrinsic function.
        """
        f = _get_add_function()
        self.assertFalse(f.executed)  # type: ignore[attr-defined]
        # Execute.
        act = f(3, 4)
        self.assertEqual(act, 7)
        # The function was executed.
        self.assertTrue(f.executed)  # type: ignore[attr-defined]
        # Reset.
        _reset_add_function(f)
        self.assertFalse(f.executed)  # type: ignore[attr-defined]
        # Execute again.
        act = f(3, 4)
        self.assertEqual(act, 7)
        # Check that the function is executed again, since there is no caching.
        self.assertTrue(f.executed)  # type: ignore[attr-defined]

    def test_with_caching1(self) -> None:
        """
        - Leave the caches enabled
        - Show that the memory cache is used
        """
        # Both memory and disk cache enabled.
        f, cf = self._get_f_cf_functions()
        # 1) Execute and verify that it is executed, since it was not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Execute and verify that it is not executed, since it's cached in memory.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        # 3) Execute and verify that it is not executed, since it's cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")

    def test_with_caching2(self) -> None:
        """
        - Leave the caches enabled
        - Cache different values
        """
        # Both memory and disk cache enabled.
        f, cf = self._get_f_cf_functions()
        # 1) Execute and verify that it is executed, since it's not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Use a different workload.
        _LOG.debug("\n%s", hprint.frame("Execute"))
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")
        # 3) Execute the second time: verify that it is not executed, since cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        # 4) Use a different workload: not executed since cached.
        _LOG.debug("\n%s", hprint.frame("Execute"))
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="mem")

    def test_with_caching3(self) -> None:
        """
        - Disable both mem and disk cache
        - Cache a single value
        """
        # Disable both memory and disk cache.
        f, cf = self._get_f_cf_functions(
            use_mem_cache=False, use_disk_cache=False
        )
        # 1) Execute the first time: executed since it's not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")
        # 2) Execute the second time: executed since it's not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")

    def test_with_caching4(self) -> None:
        """
        - Disable only the disk cache
        - Cache different values
        """
        # Use only memory cache.
        f, cf = self._get_f_cf_functions(use_mem_cache=True, use_disk_cache=False)
        # 1) Execute and verify that it is executed since not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")
        # 2) Execute the second time: verify that it was cached from memory.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="mem")

    def test_with_caching5(self) -> None:
        """
        - Disable only the memory cache
        - Cache different values
        """
        # Use only disk cache.
        f, cf = self._get_f_cf_functions(use_mem_cache=False, use_disk_cache=True)
        # 1) Verify that it is executed since there is no cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")
        # 2) Verify that it is executed, since it's cached in memory.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        #
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="disk")

    # ////////////////////////////////////////////////////////////////////////////

    def test_with_caching_mem_reset(self) -> None:
        """
        - Use only the memory cache
        - Execute and cache
        - Reset the mem cache
        - Execute again
        - Check that the cached function is recomputed
        """
        # Use only memory cache.
        f, cf = self._get_f_cf_functions(use_mem_cache=True, use_disk_cache=False)
        # 1) Verify that it is executed, since it's not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Verify that it is not executed, since it's cached in memory.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        # 3) Reset memory cache.
        _LOG.debug("\n%s", hprint.frame("Reset memory cache"))
        hcache.clear_global_cache("mem", self.cache_tag)
        # 4) Verify that it is executed, since the cache was emptied.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")

    def test_with_caching_disk_reset(self) -> None:
        """
        Same as `test_with_caching_mem_reset()` but using the disk cache.
        """
        # Use only disk cache.
        f, cf = self._get_f_cf_functions(use_mem_cache=False, use_disk_cache=True)
        # 1) Verify that it is executed, since it's not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Verify that it is not executed, since cached in disk.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        # 3) Reset disk cache.
        _LOG.debug("\n%s", hprint.frame("Reset memory cache"))
        hcache.clear_global_cache("disk", self.cache_tag)
        # 4) Verify that it is executed, since the cache was emptied.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")

    def test_with_caching_mem_reset2(self) -> None:
        """
        - Use both caches
        - Execute and cache
        - Reset the mem cache
        - Execute again
        - Check that the cached value is found in the disk cache
        """
        # Use both memory and disk cache
        f, cf = self._get_f_cf_functions(use_mem_cache=True, use_disk_cache=True)
        # 1) Verify that it is executed.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Verify that it is not executed, since it's cached in memory.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        # 3) Reset memory cache.
        hcache.clear_global_cache("mem", self.cache_tag)
        # 4) Verify that it is not executed, since it's in the disk cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")

    # ////////////////////////////////////////////////////////////////////////////

    def test_redefined_function(self) -> None:
        """
        If the cached function is redefined, but it's still the same, then the
        intrinsic function should not be recomputed.
        """
        # Define the function inline imitating working in a notebook.
        _LOG.debug("\n%s", hprint.frame("Define function"))
        add = _get_add_function()
        cached_add = hcache._Cached(add, tag=self.cache_tag)
        # 1) Execute the first time.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(
            add, cached_add, 1, 2, exp_cf_state="no_cache"
        )
        # 2) Execute the second time. Must use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="mem")
        # 3) Redefine the function inline.
        _LOG.debug("\n%s", hprint.frame("Redefine function"))
        add = _get_add_function()
        cached_add = hcache._Cached(add, tag=self.cache_tag)
        # 4) Execute the third time. Should still use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="mem")
        # 5) Execute the fourth time. Should still use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 4th time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="mem")
        # 6) Check that call with other arguments miss the cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 5th time"))
        self._execute_and_check_state(
            add, cached_add, 3, 4, exp_cf_state="no_cache"
        )

    def test_changed_function(self) -> None:
        """
        If the function is redefined, but the code is not the same, then the
        intrinsic function should be recomputed.
        """
        # Define the function imitating working in a notebook.
        _LOG.debug("\n%s", hprint.frame("Define function"))

        def add(x: int, y: int) -> int:
            add.executed = True  # type: ignore[attr-defined]
            return x + y

        cached_add = hcache._Cached(add, tag=self.cache_tag)
        # 1) Execute the first time.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(
            add, cached_add, 1, 2, exp_cf_state="no_cache"
        )
        # 2) Execute the second time. Must use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="mem")
        # 3) Redefine the function with different code.
        _LOG.debug("\n%s", hprint.frame("Redefine function"))

        # pylint: disable=function-redefined
        def add(x: int, y: int) -> int:  # type: ignore[no-redef]
            add.executed = True  # type: ignore[attr-defined]
            z = x + y
            return z

        cached_add = hcache._Cached(add, tag=self.cache_tag)
        # 4) Execute the third time. Should still use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(
            add, cached_add, 1, 2, exp_cf_state="no_cache"
        )
        # 5) Execute the fourth time. Should still use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 4th time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="mem")
        # 6) Check that call with other arguments miss the cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 5th time"))
        self._execute_and_check_state(
            add, cached_add, 3, 4, exp_cf_state="no_cache"
        )


# #############################################################################


class _ResetFunctionSpecificCacheHelper(_ResetGlobalCacheHelper):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test2()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test2(self) -> None:
        self.set_up_test()
        # Create temp directories to store the cache.
        self.disk_cache_dir = tempfile.mkdtemp()
        # Clear global cache.
        hcache.clear_global_cache("all", tag=self.cache_tag)


class TestFunctionSpecificCache1(_ResetFunctionSpecificCacheHelper):
    def test_with_caching1(self) -> None:
        """
        - Test using the function-specific disk cache
        - Disable function-specific cache and switching to global cache
        - Test using the global cache
        """
        # Use a global cache and
        _LOG.debug("\n%s", hprint.frame("Starting"))
        _LOG.debug(
            "# get_global_cache_info()=\n%s",
            hcache.get_global_cache_info(tag=self.cache_tag),
        )
        f, cf = self._get_f_cf_functions(
            use_mem_cache=False,
            use_disk_cache=True,
            disk_cache_path=self.disk_cache_dir,
        )
        _LOG.debug(
            "# cf.get_function_cache_info()=\n%s", cf.get_function_cache_info()
        )
        # 1) Execute and verify that it is executed.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Execute and verify that it is not executed, since it's cached on disk.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        # 3) Clear the global cache.
        _LOG.debug("\n%s", hprint.frame("clear_global_cache"))
        hcache.clear_global_cache("all")
        # 4) Execute and verify that it is not executed, since it's cached on disk.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")

    def test_with_caching2(self) -> None:
        """
        - Test using the function-specific disk cache
        - Disable function-specific cache and switching to global cache
        - Test using the global cache
        """
        # Use only per-function disk cache.
        f, cf = self._get_f_cf_functions(
            use_mem_cache=False, disk_cache_path=self.disk_cache_dir
        )
        # 1) Execute and verify that it is executed.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Clear the global cache.
        _LOG.debug("\n%s", hprint.frame("clear_global_cache"))
        hcache.clear_global_cache("all")
        # 3) Execute and verify that it is not executed.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        # 4) Use the global cache.
        _LOG.debug(
            "\n%s", hprint.frame("Disable function cache and use global cache")
        )
        cf.set_function_cache_path(None)
        # 5) Execute and verify that function is executed with global cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 6) Execute. Now we get the value from the memory cache since disabling
        #    the function cache means enabling the memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 4th time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="mem")
        # 7) Restore back specific cache.
        _LOG.debug("\n%s", hprint.frame("Restore function cache"))
        cf.set_function_cache_path(self.disk_cache_dir)
        # Verify that it is *NOT* executed with specific cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 5th time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")


# #############################################################################


class TestCachePerformance(_ResetGlobalCacheHelper):
    def test_performance_dataframe(self) -> None:
        """
        Test performance of the cache over pandas DataFrame.
        """
        # Create a somewhat big DataFrame with random data.
        df = pd.DataFrame(
            np.random.randint(0, 100, size=(100, 4)), columns=list("ABCD")
        )
        print("testing pandas dataframe, with sample size", df.shape)
        self._test_performance(df)

    def test_performance_series(self) -> None:
        """
        Test performance of the cache over pandas Series.
        """
        # Create a somewhat big DataFrame with random data.
        s = pd.Series(np.random.randint(0, 100, size=100))
        print("testing pandas series, with sample size", s.shape)
        self._test_performance(s)

    @staticmethod
    # pylint: disable=unused-argument
    def _computation(*args: Any) -> None:
        """
        Simulate work.

        :param args: throw away arguments
        """
        # Emulate small quantity of work.
        time.sleep(0.01)

    @staticmethod
    def _timeit(func: Callable, *args: Any) -> float:
        """
        Get performance measure of the call to fn with args.

        :param fn: callable function
        :param args: any arguments to pass to the function fn
        :return: precise time in seconds
        """
        perf_start = time.perf_counter()
        func(*args)
        perf_diff = time.perf_counter() - perf_start
        return perf_diff

    def _test_performance(self, val: Any) -> None:
        """
        Test performance of the cache over some argument val.

        :param val: any hashable argument
        """
        # Create cached versions of the computation function.
        _mem_cached_computation = hcache._Cached(
            self._computation,
            tag=self.cache_tag,
            use_mem_cache=True,
            use_disk_cache=False,
        )
        _disk_cached_computation = hcache._Cached(
            self._computation,
            tag=self.cache_tag,
            use_mem_cache=False,
            use_disk_cache=True,
        )
        # First step: no cache.
        no_cache_ct = self._timeit(lambda: self._computation(val))
        print(f"no cache run time={no_cache_ct}")
        # Second step: memory cache.
        memory_no_cache_ct = self._timeit(lambda: _mem_cached_computation(val))
        print(f"empty memory cache run time={memory_no_cache_ct}")
        print(f"empty memory cache overhead={memory_no_cache_ct - no_cache_ct}")
        memory_cache_ct = self._timeit(lambda: _mem_cached_computation(val))
        print(f"hot memory cache run time={memory_cache_ct}")
        print(f"hot memory cache benefit={no_cache_ct - memory_cache_ct}")
        # Third step: disk cache.
        disk_no_cache_ct = self._timeit(lambda: _disk_cached_computation(val))
        print(f"empty disk cache run time={disk_no_cache_ct}")
        print(f"empty disk cache overhead={disk_no_cache_ct - no_cache_ct}")
        disk_cache_ct = self._timeit(lambda: _disk_cached_computation(val))
        print(f"hot disk cache run time={disk_cache_ct}")
        print(f"hot disk cache benefit={no_cache_ct - disk_cache_ct}")


# #############################################################################


class TestCacheDecorator(_ResetGlobalCacheHelper):
    def test_decorated_function(self) -> None:
        """
        Test decorator with both caches enabled.
        """

        # Define the function inline imitating working in a notebook.
        @hcache.cache(tag=self.cache_tag)
        def add(x: int, y: int) -> int:
            add.__wrapped__.executed = True
            return x + y

        # Execute the first time.
        self._execute_and_check_state(
            add.__wrapped__, add, 1, 2, exp_cf_state="no_cache"
        )
        # Execute the second time. Must use memory cache.
        self._execute_and_check_state(
            add.__wrapped__, add, 1, 2, exp_cf_state="mem"
        )

    def test_decorated_function_no_mem(self) -> None:
        """
        Test decorator with only disk cache.
        """

        # Define the function inline imitating working in a notebook.
        @hcache.cache(tag=self.cache_tag, use_mem_cache=False)
        def add(x: int, y: int) -> int:
            add.__wrapped__.executed = True
            return x + y

        # Execute the first time.
        self._execute_and_check_state(
            add.__wrapped__, add, 1, 2, exp_cf_state="no_cache"
        )
        # Execute the second time. Must use disk cache.
        self._execute_and_check_state(
            add.__wrapped__, add, 1, 2, exp_cf_state="disk"
        )


# #############################################################################


class TestAmpTask1407(_ResetGlobalCacheHelper):
    def test1(self) -> None:
        """
        A class method can't be cached.
        """

        class _AmpTask1407Class:
            def __init__(self, string: str) -> None:
                self._string = string

            @hcache.cache(tag=self.cache_tag)
            def print(self, n: int) -> str:
                string = ""
                for _ in range(n):
                    string += "hello" + ("o" * len(self._string)) + " "
                return string

        obj = _AmpTask1407Class("test")
        with self.assertRaises(ValueError):
            obj.print(5)

    def test2(self) -> None:
        """
        A static method can be cached.
        """

        class _AmpTask1407Class:
            def __init__(self, string: str) -> None:
                self._string = string

            @staticmethod
            @hcache.cache(tag=self.cache_tag)
            def static_print(n: int) -> str:
                print("--> hello: ", n)
                string = ""
                for _ in range(n):
                    string += "hello" + ("o" * len("world")) + " "
                return string

            @hcache.cache(tag=self.cache_tag)
            def print(self, n: int) -> str:
                string = ""
                for _ in range(n):
                    string += "hello" + ("o" * len(self._string)) + " "
                return string

        obj = _AmpTask1407Class("test")
        obj.static_print(5)
        self.assertEqual(obj.static_print.get_last_cache_accessed(), "no_cache")
        #
        obj.static_print(5)
        self.assertEqual(obj.static_print.get_last_cache_accessed(), "mem")
        obj.static_print(5)
        self.assertEqual(obj.static_print.get_last_cache_accessed(), "mem")
        #
        obj.static_print(6)
        self.assertEqual(obj.static_print.get_last_cache_accessed(), "no_cache")
        obj.static_print(6)
        self.assertEqual(obj.static_print.get_last_cache_accessed(), "mem")


# #############################################################################


class TestCachingOnS3(_ResetFunctionSpecificCacheHelper):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test3()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test3(self) -> None:
        self.set_up_test2()
        # Get a directory to store the cache on S3.
        self.disk_cache_dir = self.get_s3_scratch_dir()
        self.aws_profile = "am"
        # Clear global cache.
        hcache.clear_global_cache("all", tag=self.cache_tag)

    @pytest.mark.skip(reason="See CMTask #952.")
    def test_with_caching1(self) -> None:
        """
        - Test using the function-specific cache
        - Disable function-specific cache and switching to global cache
        - Test using the global cache
        """
        _LOG.debug("\n%s", hprint.frame("Starting"))
        _LOG.debug(
            "\n%s",
            hcache.get_global_cache_info(tag=self.cache_tag, add_banner=True),
        )
        f, cf = self._get_f_cf_functions(
            use_mem_cache=False,
            disk_cache_path=self.disk_cache_dir,
            aws_profile=self.aws_profile,
        )
        _LOG.debug("\n%s", cf.get_function_cache_info(add_banner=True))
        cf.clear_function_cache(destroy=False)
        # 1) Execute and verify that it is executed, since the value is not cached.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 2) Execute and verify that it is not executed, since it's cached on disk.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        # 3) Clear the global cache.
        _LOG.debug("\n%s", hprint.frame("Clear global cache"))
        hcache.clear_global_cache("all")
        # 4) Verify that it is *NOT* executed, since the S3 cache is used.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")
        # 5) Clear the function cache.
        _LOG.debug("\n%s", hprint.frame("Clear function cache"))
        cf.clear_function_cache()
        # 6) Clear the function cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 4th time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # 7) Verify that it is executed.
        _LOG.debug("\n%s", hprint.frame("Execute the 5th time"))
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="disk")


# #############################################################################


class TestCacheEnableReadOnly1(_ResetGlobalCacheHelper):
    def test_mem_cache1(self) -> None:
        self._helper(cache_from="mem", use_mem_cache=True, use_disk_cache=False)

    def test_disk_cache1(self) -> None:
        self._helper(cache_from="disk", use_mem_cache=False, use_disk_cache=True)

    def test_mem_disk_cache1(self) -> None:
        self._helper(cache_from="mem", use_mem_cache=True, use_disk_cache=True)

    def _helper(self, cache_from: str, **kwargs: Any) -> None:
        """
        Test that when enabling read-only mode we get an assertion only if the
        function invocation was not cached.
        """
        # Both memory and disk cache enabled, although we use only memory.
        f, cf = self._get_f_cf_functions(**kwargs)
        # Execute and verify that it is executed, since it was not cached.
        _LOG_frame("Execute the 1st time")
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state="no_cache")
        # Execute and verify that it is not executed, since it's cached in memory.
        _LOG_frame("Execute the 2nd time")
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state=cache_from)
        _LOG_frame("Execute the 3rd time")
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state=cache_from)
        #
        # Enable the read-only mode.
        #
        _LOG_frame("Enable read-only mode")
        cf.enable_read_only(True)
        # This is cached so it doesn't raise.
        self._execute_and_check_state(f, cf, 3, 4, exp_cf_state=cache_from)
        # This is not cached so it should raise.
        with self.assertRaises(hcache.NotCachedValueException) as cm:
            self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")
        act = str(cm.exception)
        self.check_string(act)
        #
        # Disable the read-only mode.
        #
        _LOG_frame("Disable read-only mode")
        cf.enable_read_only(False)
        # Now this doesn't assert even if it's not in the cache.
        self._execute_and_check_state(f, cf, 4, 4, exp_cf_state="no_cache")


# #############################################################################


class TestCacheUpdateFunction1(_ResetGlobalCacheHelper):
    def test1(self) -> None:
        # Define the function imitating working in a notebook.
        _LOG.debug("\n%s", hprint.frame("Define function"))

        def add(x: int, y: int) -> int:
            add.executed = True  # type: ignore[attr-defined]
            return x + y

        disk_cache_dir = self.get_scratch_space()
        _LOG.debug("disk_cache_dir=%s", disk_cache_dir)
        cached_add = hcache._Cached(
            add,
            use_mem_cache=False,
            use_disk_cache=True,
            disk_cache_path=disk_cache_dir,
        )
        # 1) Execute the first time.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(
            add, cached_add, 1, 2, exp_cf_state="no_cache"
        )
        # 2) Execute the second time. Must use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        func_path = cached_add._get_function_specific_code_path()
        code_before = hio.from_file(func_path)
        _LOG.debug("code_before=\n%s", code_before)
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="disk")
        # 3) Redefine the function with different code while running.
        _LOG.debug("\n%s", hprint.frame("Update function"))

        def add(x: int, y: int) -> int:  # type: ignore[no-redef]
            add.executed = True  # type: ignore[attr-defined]
            return x * y

        cached_add._func = add
        cached_add._disk_cached_func.func = add
        cached_add.update_func_code_without_invalidating_cache()
        #
        code_after = hio.from_file(func_path)
        _LOG.debug("code_after=\n%s", code_after)
        self.assertNotEqual(code_before, code_after)
        # 4) Execute the second time. Must use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(add, cached_add, 1, 2, exp_cf_state="disk")


# #############################################################################


class TestCacheEnableCheckOnlyIfPresent1(_ResetGlobalCacheHelper):
    def test_mem_cache1(self) -> None:
        self._helper(cache_from="mem", use_mem_cache=True, use_disk_cache=False)

    def test_disk_cache1(self) -> None:
        self._helper(cache_from="disk", use_mem_cache=False, use_disk_cache=True)

    def test_mem_disk_cache1(self) -> None:
        self._helper(cache_from="mem", use_mem_cache=True, use_disk_cache=True)

    def _helper(self, cache_from: str, **kwargs: Any) -> None:
        # Both memory and disk cache enabled.
        f, cf = self._get_f_cf_functions(**kwargs)
        # 1) Execute the first time.
        _LOG.debug("\n%s", hprint.frame("Execute the 1st time"))
        self._execute_and_check_state(f, cf, 1, 2, exp_cf_state="no_cache")
        # 2) Execute the second time. Must use memory cache.
        _LOG.debug("\n%s", hprint.frame("Execute the 2nd time"))
        self._execute_and_check_state(f, cf, 1, 2, exp_cf_state=cache_from)
        # 3) Enable the `check_only_if_present` mode.
        _LOG.debug("\n%s", hprint.frame("Enable check_only_if_present"))
        cf.enable_check_only_if_present(True)
        # Since the value was cached, we should get an assertion.
        with self.assertRaises(hcache.CachedValueException) as cm:
            self._execute_and_check_state(f, cf, 1, 2, exp_cf_state=cache_from)
        act = str(cm.exception)
        self.check_string(act)
        # 4) Try with a new value.
        _LOG.debug("\n%s", hprint.frame("Execute the 3rd time"))
        self._execute_and_check_state(f, cf, 2, 2, exp_cf_state="no_cache")
        # 5) Disable the `check_only_if_present` mode.
        _LOG.debug("\n%s", hprint.frame("Disable check_only_if_present"))
        cf.enable_check_only_if_present(False)
        # 6) Execute a value: we should get a cache hit.
        _LOG.debug("\n%s", hprint.frame("Execute the 4rd time"))
        self._execute_and_check_state(f, cf, 1, 2, exp_cf_state=cache_from)
        # 7) Execute a value: we should get a cache hit.
        _LOG.debug("\n%s", hprint.frame("Execute the 5th time"))
        self._execute_and_check_state(f, cf, 2, 2, exp_cf_state=cache_from)


# TODO(gp): Add a test for verbose mode in __call__
# TODO(gp): get_function_cache_info
