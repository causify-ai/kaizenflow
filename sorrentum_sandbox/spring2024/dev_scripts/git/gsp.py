#!/usr/bin/env python

"""
Stash the changes in a Git client without changing the client, besides a reset
of the index.

Import as:

import dev_scripts.git.gsp as dscgigsp
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _system(cmd, *args, **kwargs):
    hsystem.system(cmd, log_level=logging.INFO, *args, **kwargs)


def _print(msg):
    msg = hprint.color_highlight(msg, "blue")
    print("\n" + msg)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    #
    _print("# Saving local changes...")
    tag, was_stashed = hgit.git_stash_push(
        "gsp", msg=args.message, log_level=logging.INFO
    )
    print("tag='%s'" % tag)
    if not was_stashed:
        # raise RuntimeError(msg)
        pass
    else:
        _print("# Restoring local changes...")
        hgit.git_stash_apply(mode="apply", log_level=logging.INFO)
    #
    _print("# Stash state ...")
    cmd = r"git stash list"
    _system(cmd, suppress_output=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-m", default=None, dest="message", help="Add message to commit"
    )
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parser())
