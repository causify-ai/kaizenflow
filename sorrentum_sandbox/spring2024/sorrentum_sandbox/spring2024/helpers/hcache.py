"""
See `helpers/cache.md` for implementation details.

Import as:

import helpers.hcache as hcache
"""

import atexit
import copy
import functools
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import joblib
import joblib.func_inspect as jfunci
import joblib.memory as jmemor

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import helpers.htimer as htimer

_LOG = logging.getLogger(__name__)
# Enable extra verbose debugging. Do not commit.
_TRACE = False

# #############################################################################


_IS_CACHE_ENABLED: bool = True


def enable_caching(val: bool) -> None:
    """
    Enable or disable all caching, i.e., global, tagged global, function-
    specific.
    """
    global _IS_CACHE_ENABLED
    if _TRACE:
        _LOG.trace("")
    _LOG.warning("Setting caching to %s -> %s", _IS_CACHE_ENABLED, val)
    _IS_CACHE_ENABLED = val


def is_caching_enabled() -> bool:
    """
    Check if cache is enabled.

    :return: whether the cache is enabled or not
    """
    if _TRACE:
        _LOG.trace("")
    return _IS_CACHE_ENABLED


# Global switch to allow or prevent clearing the cache.
_IS_CLEAR_CACHE_ENABLED: bool = True


def enable_clear_cache(val: bool) -> None:
    """
    Enable or disable clearing a cache (both global and function-specific).
    """
    global _IS_CLEAR_CACHE_ENABLED
    if _TRACE:
        _LOG.trace("")
    _LOG.warning("Enabling clear cache to %s -> %s", _IS_CLEAR_CACHE_ENABLED, val)
    _IS_CLEAR_CACHE_ENABLED = val


def get_global_cache_info(
    tag: Optional[str] = None, add_banner: bool = False
) -> str:
    """
    Report information on global cache.
    """
    if _TRACE:
        _LOG.trace("")
    txt = []
    if add_banner:
        txt.append(hprint.frame("get_global_cache_info()", char1="<"))
    txt.append(f"is global cache enabled={is_caching_enabled()}")
    #
    cache_types = _get_cache_types()
    txt.append(f"cache_types={str(cache_types)}")
    for cache_type in cache_types:
        path = _get_global_cache_path(cache_type, tag=tag)
        description = f"global {cache_type}"
        cache_info = _get_cache_size(path, description)
        txt.append(cache_info)
    txt = "\n".join(txt)
    return txt


# #############################################################################
# Global cache interface
# #############################################################################


def _get_cache_types() -> List[str]:
    """
    Return the types (aka levels) of the cache.
    """
    return ["mem", "disk"]


def _dassert_is_valid_cache_type(cache_type: str) -> None:
    """
    Assert that `cache_type` is a valid cache type.
    """
    hdbg.dassert_in(cache_type, _get_cache_types())


def _get_global_cache_name(cache_type: str, tag: Optional[str] = None) -> str:
    """
    Get the canonical cache name for a type of cache and tag, both global and
    function-specific.

    E.g., `tmp.cache.{cache_type}.{tag}` like `tmp.cache.mem.unit_tests`

    :param cache_type: type of a cache
    :param tag: optional unique tag of the cache
    :return: name of the folder for a cache
    """
    _dassert_is_valid_cache_type(cache_type)
    cache_name = f"tmp.cache.{cache_type}"
    if tag is not None:
        cache_name += f".{tag}"
    return cache_name


def _get_global_cache_path(cache_type: str, tag: Optional[str] = None) -> str:
    """
    Get path to the directory storing the cache.

    For a memory cache, the path is in a predefined RAM disk.
    For a disk cache, the path is on the file system relative to Git root.

    :return: the file system path to the cache
    """
    if _TRACE:
        _LOG.trace("")
    _dassert_is_valid_cache_type(cache_type)
    # Get the cache name.
    cache_name = _get_global_cache_name(cache_type, tag)
    # Get the enclosing directory path.
    if cache_type == "mem":
        if hsystem.get_os_name() == "Darwin":
            root_path = "/tmp"
        else:
            root_path = "/mnt/tmpfs"
    elif cache_type == "disk":
        root_path = hgit.get_client_root(super_module=True)
    # Compute path.
    file_name = os.path.join(root_path, cache_name)
    file_name = os.path.abspath(file_name)
    return file_name


def _get_cache_size(path: str, description: str) -> str:
    """
    Report information about a cache (global or function) stored at a given
    path.
    """
    if _TRACE:
        _LOG.trace("")
    if path is None:
        txt = f"'{description}' cache: path='{path}' doesn't exist yet"
    else:
        if os.path.exists(path):
            size_in_bytes = hsystem.du(path)
            size_as_str = hintros.format_size(size_in_bytes)
        else:
            size_as_str = "nan"
        # TODO(gp): Compute number of files.
        txt = f"'{description}' cache: path='{path}', size={size_as_str}"
    return txt


# This is the global memory cache.
_MEMORY_CACHE: Optional[joblib.Memory] = None


# This is the global disk cache.
_DISK_CACHE: Optional[joblib.Memory] = None


def _create_global_cache_backend(
    cache_type: str, tag: Optional[str] = None
) -> joblib.Memory:
    """
    Create a Joblib memory object storing a cache.

    :return: cache backend object
    """
    if _TRACE:
        _LOG.trace("")
    _dassert_is_valid_cache_type(cache_type)
    dir_name = _get_global_cache_path(cache_type, tag)
    _LOG.debug(
        "Creating cache for cache_type='%s' and tag='%s' at '%s'",
        cache_type,
        tag,
        dir_name,
    )
    cache_backend = joblib.Memory(dir_name, verbose=0, compress=True)
    return cache_backend


# TODO(gp): -> _get_global_cache
def get_global_cache(cache_type: str, tag: Optional[str] = None) -> joblib.Memory:
    """
    Get global cache by cache type.

    :return: caching backend
    """
    if _TRACE:
        _LOG.trace("")
    _dassert_is_valid_cache_type(cache_type)
    global _MEMORY_CACHE
    global _DISK_CACHE
    if tag is None:
        if cache_type == "mem":
            # Create global memory cache if it doesn't exist.
            if _MEMORY_CACHE is None:
                _MEMORY_CACHE = _create_global_cache_backend(cache_type)
            global_cache = _MEMORY_CACHE
        elif cache_type == "disk":
            # Create global disk cache if it doesn't exist.
            if _DISK_CACHE is None:
                _DISK_CACHE = _create_global_cache_backend(cache_type)
            global_cache = _DISK_CACHE
    else:
        # Build a one-off cache using tag.
        global_cache = _create_global_cache_backend(cache_type, tag)
    return global_cache


def set_global_cache(cache_type: str, cache_backend: joblib.Memory) -> None:
    """
    Set global cache by cache type.

    :param cache_type: type of a cache
    :param cache_backend: caching backend
    """
    if _TRACE:
        _LOG.trace("")
    _dassert_is_valid_cache_type(cache_type)
    global _MEMORY_CACHE
    global _DISK_CACHE
    if cache_type == "mem":
        _MEMORY_CACHE = cache_backend
    elif cache_type == "disk":
        _DISK_CACHE = cache_backend


def clear_global_cache(
    cache_type: str, tag: Optional[str] = None, destroy: bool = False
) -> None:
    """
    Reset the global cache by cache type.

    :param cache_type: type of a cache. `None` to clear all the caches.
    :param tag: optional unique tag of the cache, empty by default
    :param destroy: remove physical directory
    """
    if _TRACE:
        _LOG.trace("")
    if cache_type == "all":
        for cache_type_tmp in _get_cache_types():
            clear_global_cache(cache_type_tmp, tag=tag, destroy=destroy)
        return
    _dassert_is_valid_cache_type(cache_type)
    # Clear and / or destroy the cache `cache_type` with the given `tag`.
    cache_path = _get_global_cache_path(cache_type, tag)
    if not _IS_CLEAR_CACHE_ENABLED:
        hdbg.dfatal(f"Trying to delete cache '{cache_path}'")
    description = f"global {cache_type}"
    try:
        # TODO(ShaopengZ): in some test run outside CK infra, the
        # _get_cache_size() hangs.
        info_before = _get_cache_size(cache_path, description)
    except ValueError:
        _LOG.warning("Cache has already been deleted by another process.")
        return
    _LOG.info("Before clear_global_cache: %s", info_before)
    _LOG.warning("Resetting 'global %s' cache '%s'", cache_type, cache_path)
    if hs3.is_s3_path(cache_path):
        # For now we only allow to delete caches under the unit test path.
        _, abs_path = hs3.split_path(cache_path)
        hdbg.dassert(
            abs_path.startswith("/tmp/cache.unit_test/"),
            "The path '%s' is not valid",
            abs_path,
        )
    if destroy:
        _LOG.warning("Destroying '%s' ...", cache_path)
        hio.delete_dir(cache_path)
    else:
        cache_backend = get_global_cache(cache_type, tag)
        try:
            cache_backend.clear(warn=True)
        except FileNotFoundError as e:
            # A race condition can cause:
            # FileNotFoundError: [Errno 2] No such file or directory: '/app/tmp.cache.disk/joblib'
            _LOG.error("Caught %s: continuing", str(e))
    # Report stats before and after.
    try:
        info_after = _get_cache_size(cache_path, description)
    except ValueError:
        _LOG.warning("Cache has already been deleted by another process.")
        return
    _LOG.info("After clear_global_cache: %s", info_after)


# #############################################################################


class CachedValueException(RuntimeError):
    """
    A cached function is run for a value present in the cache.

    This exception is thrown when the `check_only_if_present` mode is
    used.
    """


class NotCachedValueException(RuntimeError):
    """
    A cached function is run for a value not present in the cache.

    This exception is thrown when the `enable_read_only` mode is used.
    """


class _Cached:
    # pylint: disable=protected-access
    """
    Implement a cache in memory and disk for a function.

    If the function value was not cached either in memory or on disk, the function
    `f()` is executed and the value is stored in both caches for future calls.

    This class uses 2 levels of caching:
    - memory cache: useful for caching across multiple executions of a function in
      a process or in notebooks without resetting the state
    - disk cache: useful for retrieving the state among different executions of a
      process or when a notebook is reset
    """

    # TODO(gp): Either allow users to initialize `mem_cache_path` here or with
    #  `set_function_cache_path()` but not both code paths. It's unclear which option
    #  is better. On the one side `set_function_cache_path()` is more explicit, but
    #  it can't be changed. On the other side the wrapper needs to be initialized in
    #  one shot.
    def __init__(
        self,
        func: Callable,
        *,
        use_mem_cache: bool = True,
        use_disk_cache: bool = True,
        verbose: bool = False,
        tag: Optional[str] = None,
        disk_cache_path: Optional[str] = None,
        aws_profile: Optional[str] = "am",
    ):
        """
        Construct the class.

        :param func: function to cache
        :param use_mem_cache, use_disk_cache: whether we allow memory and disk caching
        :param verbose: print high-level information about the cache
            behavior, e.g.,
            - whether a function was cached or not
            - from which level the data was retrieved
            - the execution time
            - the amount of data retrieved
        :param tag: a tag added to the global cache path to make it specific (e.g.,
            when running unit tests we want to use a different cache)
        :param disk_cache_path: path of the function-specific cache
        :param aws_profile: the AWS profile to use in case of S3 backend
        """
        # Make the class have the same attributes (e.g., `__name__`, `__doc__`,
        # `__dict__`) as the called function.
        functools.update_wrapper(self, func)
        if _TRACE:
            _LOG.trace("")
        # Save interface parameters.
        hdbg.dassert_callable(func)
        self._func = func
        # TODO(gp): We should use memory cache only inside Jupyter notebooks.
        self._use_mem_cache = use_mem_cache
        self._use_disk_cache = use_disk_cache
        self._is_verbose = verbose
        self._tag = tag
        self._disk_cache_path = disk_cache_path
        self._aws_profile = aws_profile
        #
        self._reset_cache_tracing()
        # Create the memory and disk cache objects for this function.
        # TODO(gp): We might simplify the code by using a dict instead of 2 variables.
        # Store the Joblib memory cache object for this function.
        self._memory_cached_func = self._create_function_memory_cache()
        # Store the Joblib memory object and the Joblib memory cache object for
        # this function.
        (
            self._disk_cache,
            self._disk_cached_func,
        ) = self._create_function_disk_cache()
        # Enable a mode where an exception `NotCachedValueException` is thrown if
        # the value is not in the cache.
        self._enable_read_only = False
        # Enable a mode where an exception `NotCachedValueException` is thrown if
        # the value is in the cache, instead of accessing the value.
        self._check_only_if_present = False

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the wrapped function using the caches, if needed.

        :return: object returned by the wrapped function
        """
        if _TRACE:
            _LOG.trace("")
        perf_counter_start: float
        if self._is_verbose:
            perf_counter_start = time.perf_counter()
        # Execute the cached function.
        if not is_caching_enabled():
            # No caching is allowed: execute the function.
            _LOG.warning("All caching is disabled")
            self._last_used_disk_cache = self._last_used_mem_cache = False
            obj = self._func(*args, **kwargs)
        else:
            # Caching is allowed.
            self._reset_cache_tracing()
            obj = self._execute_func(*args, **kwargs)
            _LOG.debug(
                "%s: executed from '%s'",
                self._func.__name__,
                self.get_last_cache_accessed(),
            )
            # TODO(gp): Not sure making a deep copy is a good idea. In the end,
            #  the client should not modify a cached value.
            obj = copy.deepcopy(obj)
        # Print caching info.
        if self._is_verbose:
            # Get time.
            elapsed_time = time.perf_counter() - perf_counter_start
            # Get memory.
            # TODO(gp): This is very slow.
            # obj_size = hintros.get_size_in_bytes(obj)
            # obj_size_as_str = hintros.format_size(obj_size)
            obj_size_as_str = "nan"
            last_cache = self.get_last_cache_accessed()
            cache_dir = self._get_cache_dir(last_cache, self._tag)
            _LOG.info(
                "  --> Cache data for '%s' from '%s' cache "
                "(size=%s, time=%.2f s, tag=%s, loc=%s)",
                self._func.__name__,
                last_cache,
                obj_size_as_str,
                elapsed_time,
                self._tag,
                cache_dir,
            )
        return obj

    def get_function_cache_info(self, add_banner: bool = False) -> str:
        """
        Return info about the caching properties for this function.
        """
        if _TRACE:
            _LOG.trace("")
        txt = []
        if add_banner:
            txt.append(hprint.frame("get_global_cache_info()", char1="<"))
        has_func_cache = self.has_function_cache()
        txt.append(f"has function-specific cache={has_func_cache}")
        if has_func_cache:
            # Function-specific cache: print the paths of the local cache.
            cache_type = "disk"
            txt.append(f"local {cache_type} cache path={self._disk_cache_path}")
        txt = "\n".join(txt)
        return txt

    def get_last_cache_accessed(self) -> str:
        """
        Get the cache used in the latest call of the wrapped function.

        :return: type of cache used in the last call
        """
        if _TRACE:
            _LOG.trace("")
        if self._last_used_mem_cache:
            ret = "mem"
        elif self._last_used_disk_cache:
            # If the disk cache was used, then the memory cache should not been used.
            hdbg.dassert(not self._last_used_mem_cache)
            ret = "disk"
        else:
            ret = "no_cache"
        return ret

    def enable_read_only(self, val: bool) -> None:
        """
        If set to True, the cached function can only read from the cache but
        not execute for new values.

        Otherwise a `NotCachedValueException` is thrown.
        """
        if _TRACE:
            _LOG.trace("")
        _LOG.warning(
            "Setting enable_read_only to %s -> %s", self._enable_read_only, val
        )
        self._enable_read_only = val

    def enable_check_only_if_present(self, val: bool) -> None:
        """
        If set to True, the cached function a `CachedValueException` is thrown
        if a function invocation was cached, instead of executing it.

        This can be used to check if a value was already cached without
        triggering retrieving the value from the cache, e.g., when
        probing the content of the cache.
        """
        _LOG.warning(
            "Setting check_only_if_present to %s -> %s",
            self._check_only_if_present,
            val,
        )
        self._check_only_if_present = val

    def update_func_code_without_invalidating_cache(self) -> None:
        """
        Update the Python code stored in the cache.

        This is used when we make changes to the cached function but we don't want
        to invalidate the cache.

        NOTE: here the caller must guarantee that the new function yields exactly
        the same results than the previous ones. Use carefully.
        """
        if _TRACE:
            _LOG.trace("")
        hdbg.dassert(
            self.has_function_cache(),
            "This is used only for function-specific caches",
        )
        # From `store_cached_func_code` in
        # https://github.com/joblib/joblib/tree/master/joblib/_store_backends.py
        func_path = self._get_function_specific_code_path()
        # Archive old code.
        new_func_path = (
            func_path + "." + hdateti.get_current_timestamp_as_string(tz="ET")
        )
        _LOG.debug("new_func_path='%s'", new_func_path)
        # Get the store backend.
        cache_type = "disk"
        memorized_result = self._get_memorized_result(cache_type)
        store_backend = memorized_result.store_backend
        hdbg.dassert(
            not store_backend._item_exists(new_func_path),
            "'%s' already exists",
            new_func_path,
        )
        store_backend._move_item(func_path, new_func_path)
        # Write out function code to the cache.
        func_code, _, first_line = jfunci.get_func_code(memorized_result.func)
        memorized_result._write_func_code(func_code, first_line)
        _LOG.debug("Updated func_path='%s'", func_path)

    # ///////////////////////////////////////////////////////////////////////////
    # Function-specific cache.
    # ///////////////////////////////////////////////////////////////////////////

    def has_function_cache(self) -> bool:
        """
        Return whether this function has a function-specific cache or uses the
        global cache.
        """
        if _TRACE:
            _LOG.trace("")
        has_func_cache = self._disk_cache_path is not None
        return has_func_cache

    # TODO(gp): Can we reuse the same code for `clear_function_cache` as above?
    def clear_function_cache(self, destroy: bool = False) -> None:
        """
        Clear a function-specific cache.
        """
        if _TRACE:
            _LOG.trace("")
        hdbg.dassert(
            self.has_function_cache(),
            "This function has no function-specific cache",
        )
        # Get the path for the disk cache.
        cache_path = self._disk_cache_path
        hdbg.dassert_is_not(cache_path, None)
        cache_path = cast(str, cache_path)
        if not _IS_CLEAR_CACHE_ENABLED:
            hdbg.dfatal(f"Trying to delete function cache '{cache_path}'")
        # Collect info before.
        cache_type = "disk"
        description = f"function {cache_type}"
        info_before = _get_cache_size(cache_path, description)
        _LOG.info("Before clear_function_cache: %s", info_before)
        # Clear / destroy the cache.
        _LOG.warning(
            "Resetting '%s' cache for function '%s' in dir '%s'",
            cache_type,
            self._func.__name__,
            cache_path,
        )
        if hs3.is_s3_path(cache_path):
            # For now we only allow to delete caches under the unit test path.
            _, abs_path = hs3.split_path(cache_path)
            hdbg.dassert(
                abs_path.startswith("/tmp/"),
                "The path '%s' is not valid",
                abs_path,
            )
        if destroy:
            _LOG.warning("Destroying '%s' ...", cache_path)
            hio.delete_dir(cache_path)
        else:
            self._disk_cache.clear()
        # Print stats.
        info_after = _get_cache_size(cache_path, description)
        _LOG.info("After clear_function_cache: %s", info_after)

    def set_function_cache_path(self, cache_path: Optional[str]) -> None:
        """
        Set the path for the function-specific cache for a cache type.

        :param cache_path: cache directory or `None` to use global cache
        """
        if _TRACE:
            _LOG.trace("")
        if cache_path:
            hdbg.dassert_dir_exists(cache_path)
        # We need to disable the memory cache.
        if cache_path:
            self._use_mem_cache = False
        else:
            self._use_mem_cache = True
        self._disk_cache_path = cache_path
        (
            self._disk_cache,
            self._disk_cached_func,
        ) = self._create_function_disk_cache()

    def _get_function_specific_code_path(self) -> str:
        if _TRACE:
            _LOG.trace("")
        # Get the store backend.
        cache_type = "disk"
        memorized_result = self._get_memorized_result(cache_type)
        store_backend = memorized_result.store_backend
        # Get the function id (which is the full path).
        func_id = jmemor._build_func_identifier(self._func)
        # Assemble the path.
        func_path = os.path.join(store_backend.location, func_id, "func_code.py")
        _LOG.debug("func_path='%s'", func_path)
        hdbg.dassert(
            store_backend._item_exists(func_path), "Can't find '%s'", func_path
        )
        return func_path

    def _create_function_memory_cache(self) -> joblib.Memory:
        """
        Initialize Joblib object storing a memory cache for this function.
        """
        if _TRACE:
            _LOG.trace("")
        _LOG.debug("Create memory cache")
        # For memory always use the global cache.
        cache_type = "mem"
        memory_cache = get_global_cache(cache_type, self._tag)
        # Get the Joblib object corresponding to the cached function.
        return memory_cache.cache(self._func)

    def _create_function_disk_cache(
        self,
    ) -> Tuple[joblib.Memory, joblib.memory.MemorizedFunc]:
        """
        Initialize Joblib object storing a disk cache for this function.
        """
        if _TRACE:
            _LOG.trace("")
        if self.has_function_cache():
            hdbg.dassert(
                not self._use_mem_cache,
                "When using function cache the memory cache needs to be disabled",
            )
            # Create a function-specific cache.
            memory_kwargs: Dict[str, Any] = {
                "verbose": 0,
                "compress": True,
            }
            if hs3.is_s3_path(self._disk_cache_path):
                import helpers.hjoblib as hjoblib

                # Register the S3 backend.
                hjoblib.register_s3fs_store_backend()
                s3fs = hs3.get_s3fs(self._aws_profile)
                bucket, path = hs3.split_path(self._disk_cache_path)
                # Remove the initial `/` from the path that makes the path
                # absolute, since `Joblib.Memory` wants a path relative to the
                # bucket.
                hdbg.dassert(
                    path.startswith("/"),
                    "The path should be absolute instead of %s",
                    path,
                )
                path = path[1:]
                memory_kwargs.update(
                    {
                        "backend": "s3",
                        "backend_options": {"s3fs": s3fs, "bucket": bucket},
                    }
                )
            else:
                path = self._disk_cache_path
            _LOG.debug("path='%s'\nmemory_kwargs=\n%s", path, str(memory_kwargs))
            disk_cache = joblib.Memory(path, **memory_kwargs)
        else:
            # Use the global cache.
            cache_type = "disk"
            disk_cache = get_global_cache(cache_type, self._tag)
        # Get the Joblib object corresponding to the cached function.
        disk_cached_func = disk_cache.cache(self._func)
        return disk_cache, disk_cached_func

    # ///////////////////////////////////////////////////////////////////////////

    # TODO(gp): We should use the actual stored dir.
    def _get_cache_dir(self, cache_type: str, tag: Optional[str]) -> str:
        """
        Return the dir of the cache corresponding to `cache_type` and `tag`.
        """
        if _TRACE:
            _LOG.trace("")
        if cache_type == "no_cache":
            return "no_cache"
        if self.has_function_cache():
            hdbg.dassert_eq(cache_type, "disk")
            ret = self._disk_cache_path
        else:
            ret = _get_global_cache_path(cache_type, tag=tag)
        ret = cast(str, ret)
        return ret

    def _get_memorized_result(self, cache_type: str) -> joblib.MemorizedResult:
        """
        Get the instance of a cache by type.

        From https://github.com/joblib/joblib/blob/master/joblib/memory.py
        A `MemorizedResult` is an object representing a cached value

        :param cache_type: type of a cache
        :return: instance of the Joblib cache
        """
        if _TRACE:
            _LOG.trace("")
        _dassert_is_valid_cache_type(cache_type)
        if cache_type == "mem":
            memorized_result = self._memory_cached_func
        elif cache_type == "disk":
            memorized_result = self._disk_cached_func
        _LOG.debug("memorized_result=%s", memorized_result)
        return memorized_result

    def _get_identifiers(
        self, cache_type: str, *args: Any, **kwargs: Any
    ) -> Tuple[str, str]:
        """
        Get digests for current function and arguments to be used in cache.

        :param cache_type: type of a cache
        :param args: original arguments of the call
        :param kwargs: original kw-arguments of the call
        :return: digests of the function and current arguments
        """
        memorized_result = self._get_memorized_result(cache_type)
        _LOG.debug("memorized_result=%s", memorized_result)
        hdbg.dassert_is_not(
            memorized_result,
            None,
            "Cache backend not initialized for %s",
            cache_type,
        )
        func_id, args_id = memorized_result._get_output_identifiers(
            *args, **kwargs
        )
        _LOG.debug("func_id=%s args_id=%s", func_id, args_id)
        return func_id, args_id

    def _has_cached_version(
        self, cache_type: str, func_id: str, args_id: str
    ) -> bool:
        """
        Check if a cache contains an entry for a corresponding function and
        arguments digests, and that function source has not changed.

        :param cache_type: type of a cache
        :param func_id: digest of the function obtained from _get_identifiers
        :param args_id: digest of arguments obtained from _get_identifiers
        :return: whether there is an entry in a cache
        """
        if _TRACE:
            _LOG.trace("")
        memorized_result = self._get_memorized_result(cache_type)
        has_cached_version = memorized_result.store_backend.contains_item(
            [func_id, args_id]
        )
        _LOG.debug("has_cached_version=%s", has_cached_version)
        if has_cached_version:
            # We must check that the source of the function is the same, otherwise,
            # cache tracing will not be correct.
            # First, try faster check via joblib hash.
            if self._func in jmemor._FUNCTION_HASHES:
                func_hash = memorized_result._hash_func()
                if func_hash == jmemor._FUNCTION_HASHES[self._func]:
                    return True
            # Otherwise, check the the source of the function is still the same.
            func_code, _, _ = jmemor.get_func_code(self._func)
            old_func_code_cache = (
                memorized_result.store_backend.get_cached_func_code([func_id])
            )
            old_func_code, _ = jmemor.extract_first_line(old_func_code_cache)
            if func_code == old_func_code:
                return True
        return False

    def _store_cached_version(
        self, cache_type: str, func_id: str, args_id: str, obj: Any
    ) -> None:
        """
        Store returned value from the intrinsic function in the cache.

        :param cache_type: type of a cache
        :param func_id: digest of the function obtained from `_get_identifiers()`
        :param args_id: digest of arguments obtained from `_get_identifiers()`
        :param obj: return value of the intrinsic function
        """
        if _TRACE:
            _LOG.trace("")
        # This corresponds to
        # /venv/lib/python3.8/site-packages/joblib/memory.py
        # __call__
        if self._enable_read_only:
            raise NotCachedValueException
        memorized_result = self._get_memorized_result(cache_type)
        # Write out function code to the cache.
        func_code, _, first_line = jfunci.get_func_code(memorized_result.func)
        memorized_result._write_func_code(func_code, first_line)
        # Store the returned value into the cache.
        memorized_result.store_backend.dump_item([func_id, args_id], obj)
        #

    # ///////////////////////////////////////////////////////////////////////////

    def _reset_cache_tracing(self) -> None:
        """
        Reset the values used to track which cache we are hitting when
        executing the cached function.
        """
        if _TRACE:
            _LOG.trace("")
        # The reset values depend on which caches are enabled.
        self._last_used_disk_cache = self._use_disk_cache
        self._last_used_mem_cache = self._use_mem_cache

    def _execute_func_from_disk_cache(self, *args: Any, **kwargs: Any) -> Any:
        if _TRACE:
            _LOG.trace("")
        func_info = (
            f"{self._func.__name__}(args={str(args)} kwargs={str(kwargs)})"
        )
        # Get the function signature.
        func_id, args_id = self._get_identifiers("disk", *args, **kwargs)
        if self._has_cached_version("disk", func_id, args_id):
            _LOG.debug("There is a disk cached version")
            with htimer.TimedScope(
                logging.INFO, "Loading cached version from disk"
            ):
                obj = self._disk_cached_func(*args, **kwargs)
            if self._check_only_if_present:
                raise CachedValueException(func_info)
        else:
            # INV: we didn't hit neither memory nor the disk cache.
            self._last_used_disk_cache = False
            #
            _LOG.debug(
                "%s: execute the intrinsic function",
                func_info,
            )
            # If the cache was read-only, then assert.
            if self._enable_read_only:
                msg = f"{func_info}: trying to execute"
                raise NotCachedValueException(msg)
            with htimer.TimedScope(
                logging.INFO, "Updating cached version on disk"
            ):
                obj = self._disk_cached_func(*args, **kwargs)
            # obj = self._execute_intrinsic_function(*args, **kwargs)
            # The function was not cached in disk, so now we need to update the
            # memory cache.
            # self._store_cached_version("disk", func_id, args_id, obj)
        return obj

    def _execute_func_from_mem_cache(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the function from memory cache and if not possible try the
        lower cache levels.
        """
        if _TRACE:
            _LOG.trace("")
        func_info = (
            f"{self._func.__name__}(args={str(args)} kwargs={str(kwargs)})"
        )
        # Get the function signature.
        func_id, args_id = self._get_identifiers("mem", *args, **kwargs)
        if self._has_cached_version("mem", func_id, args_id):
            _LOG.debug("There is a mem cached version")
            if self._check_only_if_present:
                raise CachedValueException(func_info)
            # The function execution was cached in the mem cache.
            with htimer.TimedScope(
                logging.INFO, "Loading cached version from memory"
            ):
                obj = self._memory_cached_func(*args, **kwargs)
        else:
            # INV: we know that we didn't hit the memory cache, but we don't know
            # about the disk cache.
            _LOG.debug("There is not a mem cached version")
            self._last_used_mem_cache = False
            #
            if self._use_disk_cache:
                # Try the disk cache.
                _LOG.debug(
                    "Trying to retrieve from disk",
                )
                obj = self._execute_func_from_disk_cache(*args, **kwargs)
            else:
                _LOG.warning("Skipping disk cache")
                obj = self._execute_intrinsic_function(*args, **kwargs)
            # The function was not cached in memory, so now we need to update the
            # memory cache.
            self._store_cached_version("mem", func_id, args_id, obj)
        return obj

    def _execute_intrinsic_function(self, *args: Any, **kwargs: Any) -> Any:
        if _TRACE:
            _LOG.trace("")
        with htimer.TimedScope(logging.INFO, "Executing intrinsic function"):
            func_info = (
                f"{self._func.__name__}(args={str(args)} kwargs={str(kwargs)})"
            )
            _LOG.debug("%s: execute intrinsic function", func_info)
            if self._enable_read_only:
                msg = f"{func_info}: trying to execute"
                raise NotCachedValueException(msg)
            obj = self._func(*args, **kwargs)
        return obj

    def _execute_func(self, *args: Any, **kwargs: Any) -> Any:
        if _TRACE:
            _LOG.trace("")
        func_info = (
            f"{self._func.__name__}(args={str(args)} kwargs={str(kwargs)})"
        )
        _LOG.debug(
            "%s: use_mem_cache=%s use_disk_cache=%s",
            func_info,
            self._use_mem_cache,
            self._use_disk_cache,
        )
        if self._use_mem_cache:
            _LOG.debug("Trying to retrieve from memory")
            obj = self._execute_func_from_mem_cache(*args, **kwargs)
        else:
            if self.has_function_cache():
                # For function-specific cache, skipping the memory cache is the
                # normal behavior.
                _LOG.debug(
                    "Function has function-specific cache: skipping memory cache"
                )
            else:
                _LOG.warning("Skipping memory cache")
            self._last_used_mem_cache = False
            if self._use_disk_cache:
                obj = self._execute_func_from_disk_cache(*args, **kwargs)
            else:
                _LOG.warning("Skipping disk cache")
                self._last_used_disk_cache = False
                obj = self._execute_intrinsic_function(*args, **kwargs)
        return obj


# #############################################################################
# Decorator
# #############################################################################


def cache(
    use_mem_cache: bool = True,
    use_disk_cache: bool = True,
    set_verbose_mode: bool = False,
    tag: Optional[str] = None,
    disk_cache_path: Optional[str] = None,
    aws_profile: Optional[str] = None,
) -> Union[Callable, _Cached]:
    """
    Decorate a function with a cache.

    The parameters are the same as `hcache._Cached`.

    Usage examples:
    ```
    import helpers.hcache as hcache

    @hcache.cache()
    def add(x: int, y: int) -> int:
        return x + y

    @hcache.cache(use_mem_cache=False)
    def add(x: int, y: int) -> int:
        return x + y
    ```
    """

    def wrapper(func: Callable) -> _Cached:
        return _Cached(
            func,
            use_mem_cache=use_mem_cache,
            use_disk_cache=use_disk_cache,
            verbose=set_verbose_mode,
            tag=tag,
            disk_cache_path=disk_cache_path,
            aws_profile=aws_profile,
        )

    return wrapper


# #############################################################################

# Clean up the memory cache on-exit.
# TODO(gp): Add another function and make it silent.
atexit.register(clear_global_cache, cache_type="mem", destroy="true")
