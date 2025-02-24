#!/usr/bin/env python

"""
Import as:

import helpers.logging_testing.logging_main as hlteloma
"""

import logging
import sys
from typing import Union

import helpers.hlogging as hloggin

_LOG = logging.getLogger(__name__)
print(f"_LOG={_LOG}")


def install_basic_formatter() -> None:
    # The output looks like
    # ```
    # DEBUG:__main__: message
    # ```
    logging.basicConfig()


def _install_formatter(
    formatter: Union[hloggin.CustomFormatter, logging.Formatter]
) -> None:
    root_logger_ = logging.getLogger()
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root_logger_.addHandler(ch)


def install_current_formatter() -> None:
    date_fmt = "%m-%d_%H:%M"
    log_format = (
        # 04-28_08:08 INFO :
        "%(asctime)-5s %(levelname)-5s"
    )
    log_format += (
        # lib_tasks _delete_branches
        " %(module)-20s: %(funcName)-30s:"
        # 142: ...
        " %(lineno)-4d:"
        " %(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt=date_fmt)
    #
    _install_formatter(formatter)


def install_custom_formatter() -> None:
    formatter = hloggin.CustomFormatter()
    _install_formatter(formatter)


if __name__ == "__main__":
    #
    print("\n# Installing formatter")
    # install_basic_formatter()
    # install_current_formatter()
    install_custom_formatter()
    #
    print("\n# Loggers before setLevel")
    root_logger = logging.getLogger()
    print(f"root_logger={root_logger}")
    # Show the loggers that have registered.
    print(f"loggers={hloggin.get_all_loggers()}")
    #
    verbosity = logging.DEBUG
    # verbosity = logging.ERROR
    print(f"\n# Loggers after setLevel {verbosity}")
    root_logger.setLevel(verbosity)
    # Setting the verbosity for the root logger sets the verbosity for all the
    # children ones.
    print(f"root_logger={root_logger}")
    print(f"loggers={hloggin.get_all_loggers()}")
    #
    hloggin.test_logger()
