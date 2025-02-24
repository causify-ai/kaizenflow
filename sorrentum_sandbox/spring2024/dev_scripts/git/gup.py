#!/usr/bin/env python

"""
Update a git client by:

- stashing
- rebasing
- reapplying the stashed changes

Import as:

import dev_scripts.git.gup as dscgigup
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

_LOG_LEVEL = "echo"

# #############################################################################


def _system(cmd, *args, **kwargs):
    hsystem.system(cmd, log_level=_LOG_LEVEL, *args, **kwargs)


def _print(msg):
    msg = hprint.color_highlight(msg, "blue")
    print("\n" + msg)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    #
    git_ll = "git log --date=local --oneline --graph --date-order --decorate"
    _print("# Checking what are the differences with master...")
    cmd = "%s ..origin/master" % git_ll
    _system(cmd, suppress_output=False)
    #
    cmd = "%s origin/master..." % git_ll
    _system(cmd, suppress_output=False)
    #
    _print("# Saving local changes...")
    tag, was_stashed = hgit.git_stash_push("gup", log_level=_LOG_LEVEL)
    print("tag='%s'" % tag)
    if not was_stashed:
        # raise RuntimeError(msg)
        pass
    #
    _print("# Getting new commits...")
    cmd = "git pull --rebase"
    _system(cmd, suppress_output=False)
    #
    if was_stashed:
        _print("# Restoring local changes...")
        hgit.git_stash_apply(mode="pop", log_level=_LOG_LEVEL)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
