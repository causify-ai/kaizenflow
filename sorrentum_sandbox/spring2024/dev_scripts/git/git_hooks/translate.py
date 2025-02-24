#!/usr/bin/env python

"""
Import as:

import dev_scripts.git.git_hooks.translate as dsgghotr
"""

import argparse
import logging

import dev_scripts.git.git_hooks.utils as dsgghout
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--text", action="store", type=str, required=True)
    parser.add_argument("--step", action="store", type=int, required=True)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    transformed_txt = dsgghout.caesar(args.text, args.step)
    print(transformed_txt)


if __name__ == "__main__":
    _main(_parse())
