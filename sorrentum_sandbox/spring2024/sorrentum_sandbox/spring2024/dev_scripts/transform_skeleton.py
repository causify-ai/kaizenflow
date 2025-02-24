#!/usr/bin/env python

"""
This is a skeleton example for a script that reads value from stdin or file,
transforms it, and writes it to stdout or file.

This pattern is useful for integrating with editors (e.g., vim).

Import as:

import dev_scripts.transform_skeleton as dsctrske
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser

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
    # Parse files.
    in_file_name, out_file_name = hparser.parse_input_output_args(args)
    _ = in_file_name, out_file_name
    # # Read file.
    # txt = hparser.read_file(in_file_name)
    # # Transform.
    # txt_tmp = "\n".join(txt)
    # cfile = htrace.parse_traceback(txt_tmp)
    # cfile_as_str = htrace.cfile_to_str(cfile)
    # # Write file.
    # hparser.write_file(cfile_as_str.split("\n"), out_file_name)


if __name__ == "__main__":
    _main(_parse())
