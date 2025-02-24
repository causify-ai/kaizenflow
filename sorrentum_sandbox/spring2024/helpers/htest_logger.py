#!/usr/bin/env python

"""
Add a description of what the script does and examples of command lines.

Check dev_scripts/linter.py to see an example of a script using this
template.

Import as:

import dev_scripts.script_skeleton as dscscske
"""


import argparse
import logging

import helpers.hlogging as hloggin
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("positional", nargs="*", help="...")
    parser.add_argument("--dst_dir", action="store", help="Destination dir")
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hparser.parse_verbosity_args(args, use_exec_path=True)
    hloggin.test_logger()
    #
    # logging.disable(logging.WARNING)
    hloggin.shut_up_log_debug(_LOG)
    hloggin.test_logger()


if __name__ == "__main__":
    _main(_parse())
