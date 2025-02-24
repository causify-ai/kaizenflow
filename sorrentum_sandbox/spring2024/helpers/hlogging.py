"""
Import as:

import helpers.hlogging as hloggin
"""

import asyncio
import contextlib
import copy
import datetime
import logging
from typing import Any, Iterable, List, Optional, Tuple, Union

# Avoid dependency from other helpers modules since this is used when the code
# is bootstrapped.


_LOG = logging.getLogger(__name__)


# #############################################################################


# Copied from `helpers/hsystem.py` to avoid circular imports.
def _is_running_in_ipynb() -> bool:
    try:
        _ = get_ipython().config  # type: ignore
        res = True
    except NameError:
        res = False
    return res


# Copied from `helpers/hsystem.py` to avoid circular dependencies.
def get_user_name() -> str:
    import getpass

    res = getpass.getuser()
    return res


# #############################################################################
# Memory usage
# #############################################################################

# TODO(gp): Consider moving to hmemory.py


MemoryUsage = Tuple[float, float, float]


def get_memory_usage(process: Optional[Any] = None) -> MemoryUsage:
    """
    Return the memory usage in terms of resident, virtual, and percent of total
    used memory.
    """
    if process is None:
        import psutil

        process = psutil.Process()
    rss_in_GB = process.memory_info().rss / (1024**3)
    vms_in_GB = process.memory_info().vms / (1024**3)
    mem_pct = process.memory_percent()
    return (rss_in_GB, vms_in_GB, mem_pct)


def memory_to_str(resource_use: MemoryUsage, *, verbose: bool = True) -> str:
    (rss_in_GB, vms_in_GB, mem_pct) = resource_use
    if verbose:
        txt = "rss=%.3fGB vms=%.3fGB mem_pct=%.0f%%" % (
            rss_in_GB,
            vms_in_GB,
            mem_pct,
        )
    else:
        txt = "%.3fGB %.3fGB %.0f%%" % (rss_in_GB, vms_in_GB, mem_pct)
    return txt


def get_memory_usage_as_str(process: Optional[Any] = None) -> str:
    """
    Like `get_memory_usage()` but returning a formatted string.
    """
    resource_use = get_memory_usage(process)
    txt = memory_to_str(resource_use)
    return txt


# #############################################################################
# Utils.
# #############################################################################

# White: 37.
# Red: 31
# Green: 32
# Yellow: 33
# Blu: 34
# Cyan: 36
# White on red background: 41

_COLOR_MAPPING = {
    # Green.
    "TRACE": (32, "TRACE"),
    # Blu.
    "DEBUG": (34, "DEBUG"),
    # Cyan.
    "INFO": (36, "INFO "),
    # White on red background.
    "WARNING": (41, "WARN "),
    "ERROR": (41, "ERROR"),
    "CRITICAL": (41, "CRTCL"),
}


def reset_logger() -> None:
    import importlib

    print("Resetting logger...")
    logging.shutdown()
    importlib.reload(logging)


def get_all_loggers() -> List:
    """
    Return list of all registered loggers.
    """
    logger_dict = logging.root.manager.loggerDict  # type: ignore  # pylint: disable=no-member
    loggers = [logging.getLogger(name) for name in logger_dict]
    return loggers


def get_matching_loggers(
    module_names: Union[str, Iterable[str]], verbose: bool
) -> List:
    """
    Find loggers that match a name or a name in a set.
    """
    if isinstance(module_names, str):
        module_names = [module_names]
    loggers = get_all_loggers()
    if verbose:
        print("loggers=\n", "\n".join(map(str, loggers)))
    #
    sel_loggers = []
    for module_name in module_names:
        if verbose:
            print(f"module_name={module_name}")
        # TODO(gp): We should have a regex.
        # str(logger) looks like `<Logger tornado.application (DEBUG)>`
        sel_loggers_tmp = [
            logger
            for logger in loggers
            if str(logger).startswith("<Logger " + module_name)
            # logger for logger in loggers if module_name in str(logger)
        ]
        # print(sel_loggers_tmp)
        sel_loggers.extend(sel_loggers_tmp)
    if verbose:
        print(f"sel_loggers={sel_loggers}")
    return sel_loggers


def shutup_chatty_modules(
    verbosity: int = logging.CRITICAL, verbose: bool = False
) -> None:
    """
    Reduce the verbosity for external modules that are very chatty.

    :param verbosity: level of verbosity used for chatty modules: the
        higher the better
    :param verbose: print extra information
    """
    module_names = [
        "aiobotocore",
        "asyncio",
        "boto",
        "boto3",
        "botocore",
        # CCXT also needs to be shut up after the `exchange` is built.
        "ccxt",
        "fsspec",
        "hooks",
        # "ib_insync",
        "invoke",
        "matplotlib",
        "nose",
        "s3fs",
        "s3transfer",
        "urllib3",
    ]
    # verbose = True
    loggers = get_matching_loggers(module_names, verbose)
    loggers = sorted(loggers, key=lambda logger: logger.name)
    for logger in loggers:
        logger.setLevel(verbosity)
    if len(loggers) > 0:
        logger_names = list(set([logger.name for logger in loggers]))
        _LOG.debug(
            "Shut up %d modules: %s", len(loggers), ", ".join(logger_names)
        )
        # if _LOG.getEffectiveLevel() < logging.DEBUG:
        #    print(WARNING +
        #       " Shutting up %d modules: %s"
        #       % (len(loggers), ", ".join([logger.name for logger in loggers]))
        #    )


# #############################################################################
# Logging formatter v1
# #############################################################################


# From https://stackoverflow.com/questions/32402502
class _LocalTimeZoneFormatter:
    """
    Override logging.Formatter to use an aware datetime object.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]
        try:
            # TODO(gp): Automatically detect the time zone. It might be complicated in
            #  Docker.
            import pytz

            self._tzinfo = pytz.timezone("America/New_York")
        except ModuleNotFoundError as e:
            #print(f"Can't import pytz: using UTC\n{str(e)}")
            self._tzinfo = None

    def converter(self, timestamp: float) -> datetime.datetime:
        # To make the linter happy and respecting the signature of the
        # superclass method.
        _ = self
        # timestamp=1622423570.0147252
        dt = datetime.datetime.utcfromtimestamp(timestamp)
        # Convert it to an aware datetime object in UTC time.
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        if self._tzinfo is not None:
            # Convert it to desired timezone.
            dt = dt.astimezone(self._tzinfo)
        return dt

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s


# #############################################################################


# [mypy] error: Definition of "converter" in base class
# "_LocalTimeZoneFormatter" is incompatible with definition in base class
# "Formatter"
class _ColoredFormatter(  # type: ignore[misc]
    _LocalTimeZoneFormatter, logging.Formatter
):
    """
    Logging formatter using colors for different levels.
    """

    _SKIP_DEBUG = True

    def format(self, record: logging.LogRecord) -> str:
        colored_record = copy.copy(record)
        # `levelname` is the internal name and can't be changed to `level_name`
        # as per our conventions.
        levelname = colored_record.levelname
        if _ColoredFormatter._SKIP_DEBUG and levelname == "DEBUG":
            colored_levelname = ""
        else:
            # Use white as default.
            prefix = "\033["
            suffix = "\033[0m"
            assert levelname in _COLOR_MAPPING, "Can't find info '%s'"
            color_code, tag = _COLOR_MAPPING[levelname]
            # Align the level name.
            colored_levelname = f"{prefix}{color_code}m{tag}{suffix}"
        colored_record.levelname = colored_levelname
        return logging.Formatter.format(self, colored_record)


# From https://stackoverflow.com/questions/2183233
def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5
    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError(
            "{} already defined in logging module".format(levelName)
        )
    if hasattr(logging, methodName):
        raise AttributeError(
            "{} already defined in logging module".format(methodName)
        )
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError(
            "{} already defined in logger class".format(methodName)
        )

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


addLoggingLevel("TRACE", 5)


# Note that this doesn't avoid evaluating the call.
# The only way to be completely sure that there is no evaluation is:
# ```
# if False: _LOG.debug(...)
# ```
def shut_up_log_debug(logger: logging.Logger) -> None:
    logging.disable(logging.DEBUG)
    # logger.debug = lambda *_: 0
    # logger.trace = lambda *_: 0


# #############################################################################


# From https://stackoverflow.com/questions/10848342
# and https://docs.python.org/3/howto/logging-cookbook.html#filters-contextual
class ResourceUsageFilter(logging.Filter):
    """
    Add fields to the logger about memory and CPU use.
    """

    def __init__(self, report_cpu_usage: bool):
        super().__init__()
        import psutil

        self._process = psutil.Process()
        self._report_cpu_usage = report_cpu_usage
        if self._report_cpu_usage:
            # Start sampling the CPU usage.
            self._process.cpu_percent(interval=1.0)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Override `logging.Filter()`, adding several fields to the logger.
        """
        p = self._process
        # Report memory usage.
        resource_use = get_memory_usage_as_str(p)
        # Report CPU usage.
        if self._report_cpu_usage:
            # CPU usage since the previous call.
            cpu_use = p.cpu_percent(interval=None)
            resource_use += " cpu=%.0f%%" % cpu_use
        record.resource_use = resource_use  # type: ignore
        return True


# #############################################################################


# TODO(gp): Replace `force_print_format` and `force_verbose_format` with `mode`.
def _get_logging_format(
    force_print_format: bool,
    force_verbose_format: bool,
    force_no_warning: bool,
    report_memory_usage: bool,
    date_format_mode: str = "time",
) -> Tuple[str, str]:
    """
    Compute the logging format depending whether running on notebook or in a
    shell.

    The logging format can be:
    - print: looks like a `print` statement

    :param force_print_format: force to use the non-verbose format
    :param force_verbose_format: force to use the verbose format
    """
    if _is_running_in_ipynb() and not force_no_warning:
        print("WARNING: Running in Jupyter")
    verbose_format = not _is_running_in_ipynb()
    #
    assert not (force_verbose_format and force_print_format), (
        f"Can't use both force_verbose_format={force_verbose_format} "
        + f"and force_print_format={force_print_format}"
    )
    if force_verbose_format:
        verbose_format = True
    if force_print_format:
        verbose_format = False
        #
    if verbose_format:
        # TODO(gp): We would like to have filename:name:funcName:lineno all
        #  justified on 15 chars.
        #  See https://docs.python.org/3/howto/logging-cookbook.html#use-of
        #  -alternative-formatting-styles
        #  Something like:
        #   {{asctime}-5s {{filename}{name}{funcname}{linedo}d}-15s {message}
        #
        # %(pathname)s Full pathname of the source file where the logging call was
        #   issued (if available).
        # %(filename)s Filename portion of pathname.
        # %(module)s Module (name portion of filename).
        if True:
            log_format = (
                # 04-28_08:08 INFO :
                "%(asctime)-5s %(levelname)-5s"
            )
            if report_memory_usage:
                # rss=0.3GB vms=2.0GB mem_pct=2% cpu=91%
                log_format += " [%(resource_use)-40s]"
            log_format += (
                # lib_tasks _delete_branches
                " %(module)-20s: %(funcName)-30s:"
                # 142: ...
                " %(lineno)-4d:"
                " %(message)s"
            )
        else:
            # Super verbose: to help with debugging print more info without trimming.
            log_format = (
                # 04-28_08:08 INFO :
                "%(asctime)-5s %(levelname)-5s"
                # .../src/lem1/amp/helpers/system_interaction.py
                # _system       :
                " %(pathname)s %(funcName)-20s "
                # 199: ...
                " %(lineno)d:"
                " %(message)s"
            )
        if date_format_mode == "time":
            date_fmt = "%H:%M:%S"
        elif date_format_mode == "date_time":
            date_fmt = "%m-%d_%H:%M"
        elif date_format_mode == "date_timestamp":
            date_fmt = "%Y-%m-%d %I:%M:%S %p"
        else:
            raise ValueError(f"Invalid date_format_mode='{date_format_mode}'")
    else:
        # Make logging look like a normal print().
        # TODO(gp): We want to still prefix with WARNING and ERROR.
        log_format = "%(message)s"
        date_fmt = ""
    return date_fmt, log_format


def set_v1_formatter(
    ch: Any,
    root_logger: Any,
    force_no_warning: bool,
    force_print_format: bool,
    force_verbose_format: bool,
    report_cpu_usage: bool,
    report_memory_usage: bool,
) -> _ColoredFormatter:
    # Decide whether to use verbose or print format.
    date_fmt, log_format = _get_logging_format(
        force_print_format,
        force_verbose_format,
        force_no_warning,
        report_memory_usage,
    )
    # Use normal formatter.
    # formatter = logging.Formatter(log_format, datefmt=date_fmt)
    # Use formatter with colors.
    formatter = _ColoredFormatter(log_format, date_fmt)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)
    # Report resource usage.
    if report_memory_usage:
        # Get root logger.
        log = logging.getLogger("")
        # Create filter.
        f = ResourceUsageFilter(report_cpu_usage)
        # The ugly part:adding filter to handler.
        log.handlers[0].addFilter(f)
    return formatter


# #############################################################################
# Logging formatter v2
# #############################################################################


# pylint: disable=line-too-long
class CustomFormatter(logging.Formatter):
    """
    Override `format` to implement a completely custom logging formatting.

    The logging output looks like:
    ```
    07:37:17 /app/amp/helpers/hunit_test.py setUp 932 - Resetting random.seed to 20000101
    ```
    or for simulated time:
    ```
    07:43:17 @ 2022-01-18 02:43:17 workload /app/amp/helpers/test/test_hlogging.py workload:33 -   -> wait
    ```
    """

    def __init__(
        self,
        *args: Any,
        date_format_mode: str = "time",
        report_memory_usage: bool = False,
        report_cpu_usage: bool = False,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._date_fmt = self._get_date_format(date_format_mode)
        #
        try:
            # TODO(gp): Automatically detect the time zone. It might be complicated
            #  in Docker.
            import pytz

            self._tzinfo = pytz.timezone("America/New_York")
        except ModuleNotFoundError as e:
            #print(f"Can't import pytz: using UTC\n{str(e)}")
            self._tzinfo = None
        #
        self._report_memory_usage = report_memory_usage
        self._report_cpu_usage = report_cpu_usage
        if self._report_memory_usage or self._report_cpu_usage:
            import psutil

            self._process = psutil.Process()
            if self._report_cpu_usage:
                # Start sampling the CPU usage.
                self._process.cpu_percent(interval=1.0)

    def format(self, record: logging.LogRecord) -> str:
        # record = copy.copy(record)
        # print(pprint.pformat(record.__dict__))
        # `record` looks like:
        # {'args': (30,),
        #  'created': 1642456725.5569131,
        #  'exc_info': None,
        #  'exc_text': None,
        #  'filename': 'logging_main.py',
        #  'funcName': 'test_logger',
        #  'levelname': 'WARNING',
        #  'levelno': 30,
        #  'lineno': 105,
        #  'module': 'logging_main',
        #  'msecs': 556.9131374359131,
        #  'msg': 'WARNING=%s',
        #  'name': '__main__',
        #  'pathname': 'helpers/logging_testing/logging_main.py',
        #  'process': 16484,
        #  'processName': 'MainProcess',
        #  'relativeCreated': 29.956817626953125,
        #  'stack_info': None,
        #  'thread': 140250120021824,
        #  'threadName': 'MainThread'}
        msg = ""
        # Add the wall clock time.
        msg += self._get_wall_clock_time()
        # Report memory usage, if needed.
        # rss=0.240GB vms=1.407GB mem_pct=2% cpu=92%
        if self._report_memory_usage:
            msg_tmp = get_memory_usage_as_str(self._process)
            # Escape the % to avoid confusing for a string to expand.
            msg_tmp = msg_tmp.replace("%", "%%")
            msg += " " + msg_tmp
        # Report CPU usage, if needed.
        if self._report_cpu_usage:
            # CPU usage since the previous call.
            msg_tmp = " cpu=%.0f" % self._process.cpu_percent(interval=None)
            # Escape the % to avoid confusing for a string to expand.
            msg_tmp += "%%"
            msg += msg_tmp
        # Get the (typically) simulated wall clock time.
        import helpers.hwall_clock_time as hwacltim

        simulated_wall_clock_time = hwacltim.get_wall_clock_time()
        if simulated_wall_clock_time is not None:
            date_fmt = "%Y-%m-%d %I:%M:%S"
            msg += " @ " + self._convert_time_to_string(
                simulated_wall_clock_time, date_fmt
            )
        # Colorize / shorten the logging level if it's not DEBUG.
        if record.levelno != logging.DEBUG:
            msg += f" - {self._colorize_level(record.levelname)}"
        # Add information about which coroutine we are running in.
        try:
            asyncio.get_running_loop()
            task = asyncio.current_task()
            if task is not None:
                msg += f" {task.get_name()}"
        except (RuntimeError, AttributeError):
            pass
        # Add information about the caller.
        # ```
        # /helpers/hunit_test.py setUp:932
        # ```
        # pathname = record.pathname.replace("/amp", "")
        # msg += f" {pathname} {record.funcName}:{record.lineno}"
        # ```
        # test_hlogging.py _print_time:28
        # ```
        msg += f" {record.filename} {record.funcName}:{record.lineno}"
        # Indent.
        if len(msg) < 50:
            msg = "%-60s" % msg
        else:
            msg = "%-80s" % msg
        # Add the caller string.
        msg += f" {record.msg}"
        record.msg = msg
        return super().format(record)

    @staticmethod
    def _get_date_format(date_format_mode: str) -> str:
        if date_format_mode == "time":
            date_fmt = "%H:%M:%S"
        elif date_format_mode == "date_time":
            date_fmt = "%m-%d_%H:%M"
        elif date_format_mode == "date_timestamp":
            date_fmt = "%Y-%m-%d %I:%M:%S %p"
        else:
            raise ValueError("Invalid date_format")
        return date_fmt

    def _convert_time_to_string(
        self, now: datetime.datetime, date_fmt: str
    ) -> str:
        # Convert it to an tz-aware datetime object in UTC time.
        dt = now.replace(tzinfo=datetime.timezone.utc)
        if self._tzinfo is not None:
            # Convert it to desired timezone.
            dt = dt.astimezone(self._tzinfo)
        time_as_str = dt.strftime(date_fmt)
        return time_as_str

    def _get_wall_clock_time(self) -> str:
        dt = datetime.datetime.utcnow()
        return self._convert_time_to_string(dt, self._date_fmt)

    def _colorize_level(self, level_name: str) -> str:
        # Use white as default.
        prefix = "\033["
        suffix = "\033[0m"
        # Print stacktrace to debug.
        if False:
            import traceback

            txt = traceback.format_stack()
            txt = "".join(txt)
            print(txt)

        assert level_name in _COLOR_MAPPING, "Can't find info '%s'"
        color_code, tag = _COLOR_MAPPING[level_name]
        colored_level_name = f"{prefix}{color_code}m{tag}{suffix}"
        return colored_level_name


def set_v2_formatter(
    ch: Any,
    root_logger: Any,
    force_no_warning: bool,
    force_print_format: bool,
    force_verbose_format: bool,
    report_memory_usage: bool,
    report_cpu_usage: bool,
) -> Union[logging.Formatter, CustomFormatter]:
    """
    See params in `init_logger()`.
    """
    assert not (force_verbose_format and force_print_format), (
        f"Can't use both force_verbose_format={force_verbose_format} "
        + f"and force_print_format={force_print_format}"
    )
    # When running in a notebook make logging behave like a `print`.
    verbose_format = True
    if _is_running_in_ipynb():
        verbose_format = False
        if not force_no_warning:
            print("WARNING: Running in Jupyter")
    #
    if force_verbose_format:
        verbose_format = True
    if force_print_format:
        verbose_format = False
    #
    if verbose_format:
        # Force to report memory / CPU usage.
        # report_memory_usage = report_cpu_usage = True
        # print(
        #     "report_memory_usage=%s report_cpu_usage=%s"
        #     % (report_memory_usage, report_cpu_usage)
        # )
        formatter: Union[logging.Formatter, CustomFormatter] = CustomFormatter(
            report_memory_usage=report_memory_usage,
            report_cpu_usage=report_cpu_usage,
        )
    else:
        # Make logging look like a normal `print()`.
        log_format = "%(levelname)-5s %(message)s"
        date_fmt = ""
        formatter = logging.Formatter(log_format, datefmt=date_fmt)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)
    return formatter


@contextlib.contextmanager
def set_level(logger: Any, level: int) -> None:
    """
    Context manager changing the verbosity level.
    """
    previous_level = logger.getEffectiveLevel()
    try:
        logger.setLevel(level)
        yield
    finally:
        logger.setLevel(previous_level)
    assert logger.getEffectiveLevel() == previous_level


# #############################################################################


def test_logger() -> None:
    print("# Testing logger ...")
    print("effective level=", _LOG.getEffectiveLevel())
    #
    _LOG.trace("TRACE=%s", logging.TRACE)
    #
    _LOG.debug("DEBUG=%s", logging.DEBUG)
    #
    _LOG.info("INFO=%s", logging.INFO)
    #
    _LOG.warning("WARNING=%s", logging.WARNING)
    #
    _LOG.error("ERROR=%s", logging.ERROR)
    #
    _LOG.critical("CRITICAL=%s", logging.CRITICAL)
