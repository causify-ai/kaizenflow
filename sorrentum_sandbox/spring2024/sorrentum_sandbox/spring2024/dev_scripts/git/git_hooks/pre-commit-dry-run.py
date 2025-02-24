#!/usr/bin/env python

"""
Apply the Git hooks to the entire code base.

Import as:

import dev_scripts.git.git_hooks.pre-commit-dry-run as dsgghopr
"""

import argparse
import logging

import dev_scripts.git.git_hooks.utils as dsgghout
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # parser.add_argument("--text", action="store", type=str, required=True)
    # parser.add_argument("--step", action="store", type=int, required=True)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    _LOG.warning("\n%s", hprint.frame("This is a dry run!"))
    git_root = hgit.get_client_root(super_module=False)
    cmd = rf'''cd {git_root} && find . -type f -name "*" -not -path "*/\.git/*"'''
    _, file_list = hsystem.system_to_string(cmd)
    file_list = file_list.split("\n")
    #
    abort_on_error = False
    # dsgghout.check_master()
    # dsgghout.check_author()
    dsgghout.check_file_size(abort_on_error, file_list=file_list)
    dsgghout.check_words(abort_on_error, file_list=file_list)
    dsgghout.python_compile(abort_on_error, file_list=file_list)


if __name__ == "__main__":
    _main(_parse())
