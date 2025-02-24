"""
Import as:

import helpers.hretry as hretry
"""
import asyncio
import functools
import logging
import time
from typing import Any, Tuple

_LOG = logging.getLogger(__name__)


def sync_retry(
    num_attempts: int, exceptions: Tuple[Any], retry_delay_in_sec: int = 0
) -> object:
    """
    Decorator retrying the wrapped function/method num_attempts times if the
    `exceptions` listed in exceptions are thrown.

    :param num_attempts: the number of times to repeat the wrapped function/method
      - The function will be called `num_attempts` times.
    :param exceptions: list of exceptions that trigger a retry attempt
    :param retry_delay_in_sec: the number of seconds to wait between retry attempts
    :return: the result of the wrapped function/method
    """

    def decorator(func) -> object:
        @functools.wraps(func)
        def retry_wrapper(*args, **kwargs):
            attempts_count = 1
            last_exception = None
            while attempts_count < num_attempts + 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    _LOG.warning(
                        "Exception %s thrown when attempting to run %s, attempt "
                        "%d of %d",
                        e,
                        func,
                        attempts_count,
                        num_attempts,
                    )
                    attempts_count += 1
                    time.sleep(retry_delay_in_sec)
            _LOG.error("Function %s failed after %d attempts", func, num_attempts)
            raise last_exception

        return retry_wrapper

    return decorator


def async_retry(
    num_attempts: int, exceptions: Tuple[Any], retry_delay_in_sec: int = 0
) -> object:
    """
    Same as `sync_retry` decorator but for `async` functions.
    """

    def decorator(func) -> object:
        @functools.wraps(func)
        async def retry_wrapper(*args, **kwargs):
            attempts_count = 1
            last_exception = None
            while attempts_count < num_attempts + 1:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    _LOG.warning(
                        "Exception %s thrown when attempting to run %s, attempt "
                        "%d of %d",
                        e,
                        func,
                        attempts_count,
                        num_attempts,
                    )
                    attempts_count += 1
                    await asyncio.sleep(retry_delay_in_sec)
            _LOG.error("Function %s failed after %d attempts", func, num_attempts)
            raise last_exception

        return retry_wrapper

    return decorator
