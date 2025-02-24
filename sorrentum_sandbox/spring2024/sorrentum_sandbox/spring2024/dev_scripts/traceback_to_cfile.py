#!/usr/bin/env python

"""
Parse a file with a traceback and generate a cfile to be used with vim to
navigate the stack trace.

# Run pytest and save the output on a file:
> pytest helpers/test/test_traceback.py 2>&1 | tee tmp.pytest.log
# Navigate the stacktrace with vim:
> dev_scripts/traceback_to_cfile.py -i log.txt
> vim -c "cfile cfile"

# Navigate the stacktrace from the sytem clipboard:
> pbpaste | traceback_to_cfile.py -i -

Import as:

import dev_scripts.traceback_to_cfile as dstrtocf
"""

import argparse
import logging
import sys

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.htraceback as htraceb

_LOG = logging.getLogger(__name__)

# #############################################################################

_NEWEST_LOG_FILE = "__NEWEST_LOG_FILE__"


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    in_default = _NEWEST_LOG_FILE
    parser = hparser.add_input_output_args(
        parser, in_default=in_default, out_default="cfile"
    )
    parser = hparser.add_bool_arg(
        parser,
        "purify_from_client",
        default_value=True,
        help_="Make references to files in the current client",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=False)
    # Parse files.
    in_file_name, out_file_name = hparser.parse_input_output_args(
        args, clear_screen=True
    )
    if in_file_name == _NEWEST_LOG_FILE:
        cmd = 'find . -type f -name "*.log" | xargs ls -1 -t'
        # > find . -type f -name "*.log" | xargs ls -1 -t
        # ./run.log
        # ./amp/core/dataflow/backtest/run_config_list.py.log
        # ./experiments/RH1E/result_1/run_notebook.1.log
        # ./experiments/RH1E/result_0/run_notebook.0.log
        dir_name = None
        remove_files_non_present = False
        files = hsystem.system_to_files(cmd, dir_name, remove_files_non_present)
        # Pick the newest file.
        in_file_name = files[0]
    _LOG.info("in_file_name=%s", in_file_name)
    if out_file_name != "-":
        hio.delete_file(out_file_name)
    # Read file.
    txt = hparser.read_file(in_file_name)
    # Transform.
    txt_tmp = "\n".join(txt)
    cfile, traceback = htraceb.parse_traceback(
        txt_tmp, purify_from_client=args.purify_from_client
    )
    if traceback is None:
        _LOG.error("Can't find traceback in the file")
        sys.exit(-1)
    print(hprint.frame("traceback", char1="-") + "\n" + traceback)
    cfile_as_str = htraceb.cfile_to_str(cfile)
    print(hprint.frame("cfile", char1="-") + "\n" + cfile_as_str)
    # Write file.
    hparser.write_file(cfile_as_str.split("\n"), out_file_name)


if __name__ == "__main__":
    _main(_parse())
