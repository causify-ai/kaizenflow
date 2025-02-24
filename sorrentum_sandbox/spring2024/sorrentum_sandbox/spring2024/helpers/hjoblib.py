"""
Import as:

import helpers.hjoblib as hjoblib
"""

import concurrent.futures
import logging
import math
import os
import pprint
import random
import sys
import traceback
from functools import wraps
from multiprocessing import Process, Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import joblib
from joblib._store_backends import StoreBackendBase, StoreBackendMixin
from tqdm.autonotebook import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.htimer as htimer
import helpers.htqdm as htqdm

# Avoid dependency from other `helpers` modules, such as `helpers.hcache`, to
# prevent import cycles.


_LOG = logging.getLogger(__name__)

# - Assume one wants to execute `n` invocations of a given `func`
#   - E.g., `func(param_1), func(param_2), ..., func(param_n)`
#   - Each `param` is a tuple of `*args` and `**kwargs` to apply to `func`
# - A `Workload` is composed of:
#   - `workload_func`: the function to execute
#   - `func_name`: the name / description of the function `func`
#   - `tasks`: a list of `n` set of parameters `*args`, `**kwargs` to apply
#      to the function (e.g., `param_1`, ..., `param_n`)
# - Each `Task` executes a subset of the functions
# - `Tasks` are a partition of the function invocations, i.e., each function
#   invocation is executed by one and only one task
# - The `n` `Tasks` are then executed by `k` threads in parallel or serially
#   - Note that a single task can correspond to processing of multiple logical
#     chunks of work, because they need to be processed together or because we
#     want to enforce that it is executed on a single processor
#   - E.g., if we want to concatenate files we can map multiple filenames in a
#     single `Task`. In this case the `Task` contains a list of filenames to
#     concatenate together

# #############################################################################
# Task
# #############################################################################

# A `Task` contains the parameters to pass to the function that needs to be
# executed.
# A `Task` is represented by a tuple of `*args` and `**kwargs`, e.g.,
# ```
# args=()
# kwargs={
#   'asset_col_name': 'asset',
#   'dst_dir': './tmp.s3_out',
#   'parquet_file_names': [
#           './tmp.s3/20220110/data.parquet',
#           './tmp.s3/20220111/data.parquet',
#           './tmp.s3/20220112/data.parquet']
# }
# ```
Task = Tuple[Tuple[Any], Dict[str, Any]]


# TODO(gp): @Nikola add unit tests
def split_list_in_tasks(
    list_in: List[Any],
    n: int,
    *,
    keep_order: bool = False,
    num_elems_per_task: Optional[int] = None,
) -> List[List[Any]]:
    """
    Split a list in tasks based on the number of threads or elements per
    partition.

    :param num_elems_per_task: force each task to have the given number of elements
    :param keep_order: split the list so that consecutive elements of the list
        are in different tasks. This favors executing the workload in order on `n`
        threads
    :return: list of lists of elements, where each list can be assigned to an
        execution thread

    - E.g., [a, b, c, d, e] executed on 3 threads [1, 2, 3] gives the allocation
      for `keep_order=True`:
        ```
        1 -> [a, d]
        2 -> [b, e]
        3 -> [c]
        ```
    - For `keep_order=False` the allocation is:
        ```
        1 -> [a, b]
        2 -> [c, d]
        3 -> [e]
        ```
    - For `num_elems_per_task=3` the allocation is:
        ```
        1 -> [a, b, c]
        2 -> [d, e]
        3 -> []
        ```
    """
    hdbg.dassert_lte(1, n)
    hdbg.dassert_lte(n, len(list_in), "There are fewer tasks than threads")
    if keep_order:
        hdbg.dassert_is(
            num_elems_per_task,
            None,
            "Can't specify num_elems_per_task with keep_order",
        )
        list_out: List[list] = [[] for _ in range(n)]
        for i, elem in enumerate(list_in):
            _LOG.debug("%s: %s -> %s", i, elem, i % n)
            list_out[i % n].append(elem)
    else:
        if num_elems_per_task is None:
            k = int(math.ceil(len(list_in) / n))
        else:
            k = num_elems_per_task
        hdbg.dassert_lte(1, k)
        list_out = [list_in[i : i + k] for i in range(0, len(list_in), k)]
    # Ensure that the elements are all distributed.
    hdbg.dassert_eq(sum(len(l_) for l_ in list_out), len(list_in))
    return list_out


def apply_incremental_mode(
    src_dst_file_name_map: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    """
    Apply incremental mode to a map of source to destination files.

    Often the function in a `Workload` corresponds to reading a file, processing it,
    and writing the output in a file. In this case, applying the incremental mode
    means removing the tuples in the src_file -> dst_file mapping where the dst file
    already exists.

    :return: filtered mapping
    """
    hdbg.dassert_container_type(src_dst_file_name_map, list, tuple)
    #
    src_dst_file_name_map_tmp = []
    for src_dst_file_name in src_dst_file_name_map:
        # Parse the element of the mapping.
        hdbg.dassert_eq(len(src_dst_file_name), 2)
        src_file_name, dst_file_name = src_dst_file_name
        _LOG.debug("%s -> %s", src_file_name, dst_file_name)
        # Discard the mapping element if the destination file already exists.
        hdbg.dassert_path_exists(src_file_name)
        if os.path.exists(dst_file_name):
            _LOG.debug("Skipping %s -> %s", src_file_name, dst_file_name)
        else:
            src_dst_file_name_map_tmp.append((src_file_name, dst_file_name))
    _LOG.info(
        "After applying incremental mode, there are %s / %s files to process",
        len(src_dst_file_name_map_tmp),
        len(src_dst_file_name_map),
    )
    return src_dst_file_name_map_tmp


def validate_task(task: Task) -> bool:
    """
    Assert if `Task` is malformed, otherwise return True.

    A valid `Task` is a tuple `(*args, **kwargs)`.
    """
    # A `Task` is a tuple.
    hdbg.dassert_isinstance(task, tuple)
    hdbg.dassert_eq(len(task), 2)
    # Parse the `Task`.
    args, kwargs = task
    _LOG.debug("task.args=%s", pprint.pformat(args))
    hdbg.dassert_isinstance(args, tuple)
    _LOG.debug("task.kwargs=%s", pprint.pformat(kwargs))
    hdbg.dassert_isinstance(kwargs, dict)
    return True


def task_to_string(task: Task, *, use_pprint: bool = True) -> str:
    hdbg.dassert(validate_task(task))
    args, kwargs = task
    txt = []
    if use_pprint:
        txt.append(f"args={pprint.pformat(args)}")
        txt.append(f"kwargs={pprint.pformat(kwargs)}")
    else:
        txt.append(f"args={str(args)}")
        txt.append(f"kwargs={str(kwargs)}")
    txt = "\n".join(txt)
    return txt


# #############################################################################
# Workload
# #############################################################################

# A `Workload` consists of multiple executions of a function with different
# parameters represented by `Tasks`.
# Note: `joblib_helper` can be used together with caching. The workload function
# doesn't have to be the one that is cached, but it can trigger caching of function
# results in the call stack.
Workload = Tuple[
    # `func`: the function representing the workload to execute
    Callable,
    # `func_name`: the mnemonic name of the function, which is used for debugging
    #   info and for naming the directory storing the cache
    # - E.g., `vltbut.get_cached_bar_data_for_date_interval`
    # - Note that the `func_name` can be different than the name of `func`
    #   - E.g., we can call
    #     `vltbut.get_cached_bar_data_for_date_interval_for_interval` inside `func`,
    #     in order to create a cache for
    #     `vltbut.get_cached_bar_data_for_date_interval`, so the cache name
    #     should be for `vltbut.get_cached_bar_data_for_date_interval`
    str,
    # `tasks`: a list of (*args, **kwargs) to pass to `func`
    List[Task],
]


def validate_workload(workload: Workload) -> bool:
    """
    Assert if the `Workload` is malformed, otherwise return True.

    A valid `Workload` is a triple `(func, func_name, List[Task])`.
    """
    # A valid workload` is a triple.
    hdbg.dassert_isinstance(workload, tuple)
    hdbg.dassert_eq(len(workload), 3)
    # Parse.
    workload_func, func_name, tasks = workload
    # Check each component.
    hdbg.dassert_isinstance(workload_func, Callable)
    hdbg.dassert_isinstance(func_name, str)
    hdbg.dassert_container_type(tasks, List, tuple)
    hdbg.dassert(all(validate_task(task) for task in tasks))
    return True


def randomize_workload(
    workload: Workload, *, seed: Optional[int] = None
) -> Workload:
    validate_workload(workload)
    # Parse the workload.
    workload_func, func_name, tasks = workload
    # Randomize `tasks`.
    seed = seed or 42
    random.seed(seed)
    random.shuffle(tasks)
    # Build a new workload.
    workload = (workload_func, func_name, tasks)
    validate_workload(workload)
    return workload


def reverse_workload(
    workload: Workload, *, seed: Optional[int] = None
) -> Workload:
    """
    Reverse the workload.

    Typically we generate workload in chronological order, but sometimes
    we want to run from most recent data to least recent, so that we
    have the results about the most recent periods first, which is what
    we care most about.
    """
    validate_workload(workload)
    # Parse the workload.
    workload_func, func_name, tasks = workload
    # Reverse.
    _LOG.warning("Reversing the workload as per user request")
    tasks = list(reversed(tasks))
    # Build a new workload.
    workload = (workload_func, func_name, tasks)
    validate_workload(workload)
    return workload


def truncate_workload(
    workload: Workload,
    max_num: int,
) -> Workload:
    """
    Limit the workload to the first `max_num` tasks.
    """
    validate_workload(workload)
    # Parse the workload.
    workload_func, func_name, tasks = workload
    # Truncate the workload.
    _LOG.warning("Considering only the first %d / %d tasks", max_num, len(tasks))
    hdbg.dassert_lte(1, max_num)
    hdbg.dassert_lte(max_num, len(tasks))
    tasks = tasks[:max_num]
    # Build a new workload.
    workload = (workload_func, func_name, tasks)
    validate_workload(workload)
    return workload


def workload_to_string(workload: Workload, *, use_pprint: bool = True) -> str:
    """
    Print the workload.

    E.g.,

    ```
    workload_func=_LimeTask317_process_chunk
    func_name=_LimeTask317_process_chunk
    # task 1 / 3
    args=([('./tmp.s3/20220110/data.parquet',
        './tmp.s3_out/./tmp.s3/20220110/data.parquet')],)
    kwargs={}
    # task 2 / 3
    args=([('./tmp.s3/20220111/data.parquet',
       './tmp.s3_out/./tmp.s3/20220111/data.parquet')],)
    kwargs={}
    # task 3 / 3
    args=([('./tmp.s3/20220112/data.parquet',
       './tmp.s3_out/./tmp.s3/20220112/data.parquet')],)
    kwargs={}
    ```
    """
    validate_workload(workload)
    workload_func, func_name, tasks = workload
    txt = []
    txt.append(f"workload_func={workload_func.__name__}")
    txt.append(f"func_name={func_name}")
    for i, task in enumerate(tasks):
        txt.append(f"# task {i + 1} / {len(tasks)}")
        txt.append(task_to_string(task, use_pprint=use_pprint))
    txt = "\n".join(txt)
    return txt


# #############################################################################
# Template for functions to execute in parallel.
# #############################################################################

# NOTE: the workload function:
# - asserts if there is an error, since the return value is a string with a summary
#   of the execution
# - doesn't have to be the function that we intend to cache


def _workload_function(*args: Any, **kwargs: Any) -> str:
    """
    Execute the function task.

    :raises: in case of error
    :return: string representing information about the cached function
        execution
    """
    _ = args
    incremental = kwargs.pop("incremental")
    num_attempts = kwargs.pop("num_attempts")
    _ = incremental, num_attempts
    func_output: List[str] = []
    func_output = "\n".join(func_output)
    return func_output


def _get_workload(
    # args: argparse.Namespace
) -> Workload:
    """
    Prepare the workload using the parameters from command line.
    """
    # _ = args


# #############################################################################
# Layer passing information from `parallel_execute` to the function to execute
# in parallel.
# #############################################################################


def get_num_executing_threads(args_num_threads: Union[str, int]) -> int:
    """
    Return the number of executing threads based on the value of
    `args.num_threads`.

    E.g.,
        - `serial` corresponds to 1
        - `-1` corresponds to all available CPUs
    """
    if args_num_threads == "serial":
        num_executing_threads = 1
    elif args_num_threads == -1:
        # All CPUs available.
        num_executing_threads = joblib.cpu_count()
    else:
        # Assume it's an int.
        num_executing_threads = int(args_num_threads)
    hdbg.dassert_lte(1, num_executing_threads)
    return num_executing_threads


# TODO(grisha): Add type hints, add unit test to understand the behavior.
# From https://gist.github.com/schlamar/2311116
# Note that this is not going to work with joblib.parallel with
# backend="multiprocessing" returning an error
# AssertionError: daemonic processes are not allowed to have children
def processify(func):
    """
    Decorator to run a function as a process.

    Be sure that every argument and the return value is *pickable*. The
    created process is joined, so the code does not run in parallel.
    """

    def process_func(q: Queue, *args: Any, **kwargs: Any) -> None:
        """
        Run function as a process and store output in the input Queue.
        """
        _LOG.debug("pid after processify=", os.getpid())
        try:
            ret = func(*args, **kwargs)
        except Exception:
            # Store error logs in the queue.
            ex_type, ex_value, tb = sys.exc_info()
            error = ex_type, ex_value, "".join(traceback.format_tb(tb))
            ret = None
        else:
            error = None
        q.put((ret, error))

    # Register original function with different name in `sys.modules` so it is
    # pickable.
    process_func.__name__ = func.__name__ + "processify_func"
    setattr(sys.modules[__name__], process_func.__name__, process_func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        q = Queue()
        p = Process(target=process_func, args=[q] + list(args), kwargs=kwargs)
        p.start()
        ret, error = q.get()
        p.join()
        if error:
            ex_type, ex_value, tb_str = error
            message = "%s (in subprocess)\n%s" % (ex_value.message, tb_str)
            raise ex_type(message)
        return ret

    return wrapper


def _parallel_execute_decorator(
    task_idx: int,
    task_len: int,
    incremental: bool,
    abort_on_error: bool,
    num_attempts: int,
    log_file: str,
    # TODO(gp): Pass these parameters first.
    workload_func: Callable,
    func_name: str,
    processify_func: bool,
    task: Task,
) -> Any:
    """
    Parameters have the same meaning as in `parallel_execute()`.

    :param abort_on_error: control whether to abort on `workload_func` function
        that is failing and asserting
        - If `workload_func` fails:
            - if `abort_on_error=True` the exception from `workload_func` is
              propagated and the return value is `None`
            - if `abort_on_error=False` the exception is not propagated, but the
              return value is the string representation of the exception
    :param processify_func: switch to enable wrapping a function into a process
    :return: the return value of the workload function or the exception string
    """
    # Validate very carefully all the parameters.
    hdbg.dassert_lte(0, task_idx)
    hdbg.dassert_lt(task_idx, task_len)
    hdbg.dassert_isinstance(incremental, bool)
    hdbg.dassert_isinstance(abort_on_error, bool)
    hdbg.dassert_lte(1, num_attempts)
    hdbg.dassert_isinstance(log_file, str)
    hdbg.dassert_isinstance(workload_func, Callable)
    hdbg.dassert_isinstance(func_name, str)
    hdbg.dassert(validate_task(task))
    # Redirect the logging output of each task to a different file.
    # TODO(gp): This file should go in the `task_dst_dir`.
    # log_to_file = True
    log_to_file = False
    if log_to_file:
        dst_dir = os.path.dirname(os.path.abspath(log_file))
        print(dst_dir)
        hio.create_dir(dst_dir, incremental=True)
        file_name = os.path.join(
            dst_dir, f"{func_name}.{task_idx + 1}_{task_len}.log"
        )
        _LOG.warning("Logging to %s", file_name)
        file_handler = logging.FileHandler(file_name)
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    # Save information about the function to be executed.
    txt = []
    # `start_ts` needs to be before running the function.
    start_ts = hdateti.get_current_timestamp_as_string("naive_ET")
    tag = f"{task_idx + 1}/{task_len} ({start_ts})"
    txt.append("\n" + hprint.frame(tag) + "\n")
    txt.append(f"tag={tag}")
    txt.append(f"workload_func={workload_func.__name__}")
    txt.append(f"func_name={func_name}")
    txt.append(task_to_string(task))
    # Run the workload.
    args, kwargs = task
    kwargs.update({"incremental": incremental, "num_attempts": num_attempts})
    with htimer.TimedScope(
        logging.DEBUG, f"Execute '{workload_func.__name__}'"
    ) as ts:
        try:
            if processify_func:
                _LOG.debug("Using processify")
                # Wrap the function into a process to enforce de-allocating
                # memory at the end of the execution (see
                # CmampTask5854: Resolve backtest memory leakage).
                _LOG.debug("pid before processify=%s", os.getpid())
                workload_func = processify(workload_func)
            res = workload_func(*args, **kwargs)
            error = False
        except Exception as e:  # pylint: disable=broad-except
            exception = e
            txt.append(f"exception='{str(e)}'")
            res = None
            error = True
            _LOG.error("Execution failed")
    # Save information about the execution of the function.
    elapsed_time = ts.elapsed_time
    end_ts = hdateti.get_current_timestamp_as_string("naive_ET")
    # TODO(gp): -> func_result
    txt.append(f"func_res=\n{hprint.indent(str(res))}")
    txt.append(f"elapsed_time_in_secs={elapsed_time}")
    txt.append(f"start_ts={start_ts}")
    txt.append(f"end_ts={end_ts}")
    txt.append(f"error={error}")
    # Update log file.
    txt = "\n".join(txt)
    _LOG.debug("txt=\n%s", hprint.indent(txt))
    hio.to_file(log_file, txt, mode="a")
    if error:
        # The execution wasn't successful.
        _LOG.error(txt)
        if abort_on_error:
            _LOG.error("Aborting since abort_on_error=%s", abort_on_error)
            raise exception  # noqa: F821
        _LOG.error("Continuing execution since abort_on_error=%s", abort_on_error)
        res = str(exception)
    else:
        # The execution was successful.
        pass
    return res


# TODO(gp): Pass a `task_dst_dir` to each task so it can write there.
#  This is a generalization of `experiment_result_dir` for `run_config_list` and
#  `run_notebook`.
def parallel_execute(
    workload: Workload,
    # Options for the `parallel_execute` framework.
    dry_run: bool,
    num_threads: Union[str, int],
    incremental: bool,
    abort_on_error: bool,
    num_attempts: int,
    log_file: str,
    *,
    backend: str = "loky",
) -> Optional[List[Any]]:
    """
    Run a workload in parallel using joblib or asyncio.

    :param workload: the workload to execute
    :param dry_run: if True, print the workload and exit without executing it
    :param num_threads: joblib parameter to control how many threads to use
    :param incremental: parameter passed to the function to execute to control if
        we want to re-execute tasks already executed or not
    :param abort_on_error: when True, if one task asserts then stop executing the
        workload and return the exception of the failing task
        - If False, the execution continues
    :param num_attempts: number of times to attempt running a function before
        declaring an error
    :param log_file: file used to log information about the execution
    :param backend: specify the backend type (e.g., joblib `loky` or
        `asyncio_process_executor`)

    :return: list with the results from executing `func` or the exception of the
        failing function
        - NOTE: if `abort_on_error=True` and one task fails, `joblib` doesn't return
          the output of the already executed tasks. In this case, the best we can do
          is to return the exception of the failing task
    """
    # Print the parameters.
    print(hprint.frame("Workload"))
    # It's too verbose to print all the workload.
    # print(workload_to_string(workload, use_pprint=False))
    _LOG.info(
        hprint.to_str(
            "dry_run num_threads incremental num_attempts abort_on_error"
        )
    )
    # Parse the workload.
    validate_workload(workload)
    workload_func, func_name, tasks = workload
    _LOG.info("Saving log info in '%s'", log_file)
    _LOG.info(
        "Number of executing threads=%s (%s)",
        get_num_executing_threads(num_threads),
        num_threads,
    )
    _LOG.info("Number of tasks=%s", len(tasks))
    #
    if dry_run:
        file_name = "./tmp.parallel_execute.workload.txt"
        workload_as_str = workload_to_string(workload, use_pprint=False)
        hio.to_file(file_name, workload_as_str)
        _LOG.warning("Workload saved at '%s'", file_name)
        _LOG.warning("Exiting without executing workload, as per user request")
        return None
    # Run.
    task_len = len(tasks)
    tqdm_out = htqdm.TqdmToLogger(_LOG, level=logging.INFO)
    tqdm_iter = tqdm(
        enumerate(tasks),
        total=task_len,
        file=tqdm_out,
        desc=f"num_threads={num_threads} backend={backend}",
    )
    if backend == "threading":
        # Enable wrapping a function into a process for threading backend
        # to force memory de-allocation.
        # TODO(Grisha): unclear if there are cases when we want to use
        #  `False` with `threading` backends, consider exposing to the
        #  interface.
        # TODO(Grisha): should we enable the switch for `num_threads="serial"`? will it work?
        processify_func = True
    else:
        processify_func = False
    if num_threads == "serial":
        # Execute the tasks serially.
        res = []
        for task_idx, task in tqdm_iter:
            _LOG.debug("\n%s", hprint.frame(f"Task {task_idx + 1} / {task_len}"))
            # Execute.
            res_tmp = _parallel_execute_decorator(
                task_idx,
                task_len,
                incremental,
                abort_on_error,
                num_attempts,
                log_file,
                #
                workload_func,
                func_name,
                processify_func,
                task,
            )
            res.append(res_tmp)
    else:
        # Execute the tasks in parallel.
        num_threads = int(num_threads)
        # -1 is interpreted by joblib like for all cores.
        _LOG.info("Using %d threads, backend='%s'", num_threads, backend)
        if backend in ("loky", "threading", "multiprocessing"):
            # from joblib.externals.loky import set_loky_pickler
            # set_loky_pickler('cloudpickle')
            res = joblib.Parallel(
                n_jobs=num_threads, backend=backend, verbose=200
            )(
                joblib.delayed(_parallel_execute_decorator)(
                    task_idx,
                    task_len,
                    incremental,
                    abort_on_error,
                    num_attempts,
                    log_file,
                    #
                    workload_func,
                    func_name,
                    processify_func,
                    task,
                )
                # We can't use `tqdm_iter` since this only shows the submission of
                # the jobs but not their completion.
                for task_idx, task in enumerate(tasks)
            )
        elif backend in ("asyncio_threading", "asyncio_multiprocessing"):
            if backend == "asyncio_threading":
                executor = concurrent.futures.ThreadPoolExecutor
            elif backend == "asyncio_multiprocessing":
                executor = concurrent.futures.ProcessPoolExecutor
            else:
                raise ValueError(f"Invalid backend='{backend}'")
            func = lambda args_: _parallel_execute_decorator(
                args_[0],
                task_len,
                incremental,
                abort_on_error,
                num_attempts,
                log_file,
                #
                workload_func,
                func_name,
                processify_func,
                args_[1],
            )
            args = list(enumerate(tasks))
            use_progress_bar = True
            if not use_progress_bar:
                # Implementation without progress bar.
                with executor(max_workers=num_threads) as executor_:
                    res = list(executor_.map(func, args))
            else:
                # Implementation with progress bar.
                res = []
                with tqdm_iter as pbar:
                    with executor(max_workers=num_threads) as executor_:
                        futures = {
                            executor_.submit(func, arg): arg for arg in args
                        }
                        _LOG.debug("done submitting")
                        for future in concurrent.futures.as_completed(futures):
                            res_tmp = future.result()
                            res.append(res_tmp)
                            pbar.update(1)
        else:
            raise ValueError(f"Invalid backend='{backend}'")
    _LOG.info("Saved log info in '%s'", log_file)
    return res


# #############################################################################
# joblib storage backend for S3.
# #############################################################################

# This allows to store a joblib cache on S3.

# Adapted from https://github.com/aabadie/joblib-s3


class _S3FSStoreBackend(StoreBackendBase, StoreBackendMixin):
    """
    A StoreBackend for S3 cloud storage file system.
    """

    def __init__(self) -> None:
        super().__init__()
        self._objs: List[Any] = []

    def clear_location(self, location: str) -> None:
        """
        Check if object exists in store.
        """
        if self.storage.exists(location):
            self._flush()
            self.storage.rm(location, recursive=True)

    def create_location(self, location: str) -> None:
        """
        Create object location on store.
        """
        self._mkdirp(location)

    def get_items(self) -> List[Any]:
        """
        Return the whole list of items available in cache.
        """
        _ = self
        return []

    def configure(
        self,
        location: str,
        backend_options: Dict[str, Any],
        verbose: int = 0,
    ) -> None:
        """
        Configure the store backend.
        """
        options = backend_options
        hdbg.dassert_in("s3fs", options)
        self.storage = options["s3fs"]
        hdbg.dassert_in("bucket", options)
        bucket = options["bucket"]
        # Ensure the given bucket exists.
        root_bucket = os.path.join("s3://", bucket)
        if not self.storage.exists(root_bucket):
            self.storage.mkdir(root_bucket)
        if location.startswith("/"):
            location.replace("/", "")
        self.location = os.path.join(root_bucket, location)
        if not self.storage.exists(self.location):
            self.storage.mkdir(self.location)
        # Computation results can be stored compressed for faster I/O.
        self.compress = backend_options["compress"]
        # Memory map mode is not supported.
        self.mmap_mode = None

    def _flush(self) -> None:
        _ = self
        # TODO(gp): No need to flush for now.
        # for fd in self._objs:
        #    fd.flush(force=True)

    def _open_item(self, fd: Any, mode: str) -> Any:
        self._objs.append(fd)
        return self.storage.open(fd, mode)

    def _item_exists(self, path: str) -> bool:
        self._flush()
        ret: bool = self.storage.exists(path)
        return ret

    def _move_item(self, src: str, dst: str) -> None:
        self.storage.mv(src, dst)

    def _mkdirp(self, directory: str) -> None:
        """
        Create recursively a directory on the S3 store.
        """
        # Remove root cachedir from input directory to create as it should
        # have already been created in the configure function.
        if directory.startswith(self.location):
            directory = directory.replace(self.location + "/", "")
        current_path = self.location
        for sub_dir in directory.split("/"):
            current_path = os.path.join(current_path, sub_dir)
            self.storage.mkdir(current_path)


_REGISTER_S3FS_STORE = False


def register_s3fs_store_backend() -> None:
    """
    Register the S3 store backend for joblib memory caching.
    """
    global _REGISTER_S3FS_STORE
    if not _REGISTER_S3FS_STORE:
        joblib.register_store_backend("s3", _S3FSStoreBackend)
        _REGISTER_S3FS_STORE = True
