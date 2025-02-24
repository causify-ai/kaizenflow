#!/usr/bin/env python
"""
`timeout` decorator which is used to limit function execution time.

Import as:

import helpers.hthreading as hthread
"""

import _thread
import sys
import threading
from typing import Any


def _timeout_handler() -> None:
    sys.stderr.flush()
    # Raise KeyboardInterrupt.
    _thread.interrupt_main()


def timeout(timeout_sec: int) -> Any:
    """
    Exit process if its execution takes longer than timeout_sec seconds. This
    is a decorator that issue a KeyboardInterrupt, that will be raised if time
    limit is exceed.

    :param timeout_sec: time limit
    """

    def outer(fn: Any) -> Any:
        def inner(*args: Any, **kwargs: Any) -> Any:
            timer = threading.Timer(timeout_sec, _timeout_handler)
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result

        return inner

    return outer
