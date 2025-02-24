#!/usr/bin/env python

"""
Import as:

import dev_scripts.remove_escape_chars as dsreesch
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_input_output_args(parser)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    print("cmd line: %s" % hdbg.get_command_line())
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    in_file_name, out_file_name = hparser.parse_input_output_args(
        args, clear_screen=False
    )
    txt = hparser.read_file(in_file_name)
    txt_tmp = "\n".join(txt)
    txt_tmp = hprint.remove_non_printable(txt_tmp)
    txt_tmp = txt_tmp.split("\n")
    hparser.write_file(txt_tmp, out_file_name)


if __name__ == "__main__":
    _main(_parse())
