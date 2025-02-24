#!/usr/bin/env python

"""
This script reads value from stdin/file, transforms it using Pandoc and writes
the result to stdout/file.

To run in vim:
```
:'<,'>!dev_scripts/documentation/run_pandoc.py -i - -o - -v CRITICAL
```

This script is derived from `dev_scripts/transform_skeleton.py`.
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


# #############################################################################


def _convert_pandoc_md_to_latex(
    txt: str,
) -> str:
    """
    Run Pandoc to convert a markdown file to a latex file.
    """
    # Save to tmp file.
    in_file_name = "./tmp.run_pandoc_in.md"
    hio.to_file(in_file_name, txt)
    # Run Pandoc.
    out_file_name = "./tmp.run_pandoc_out.tex"
    cmd = (
        f"pandoc --read=markdown --write=latex -o {out_file_name}"
        f" {in_file_name}"
    )
    hsystem.system(cmd)
    # Read tmp file.
    res = hio.from_file(out_file_name)
    return res


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_input_output_args(parser)
    parser.add_argument(
        "--action",
        action="store",
        default="convert_md_to_latex",
        help="Action to perform",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Parse files.
    in_file_name, out_file_name = hparser.parse_input_output_args(args)
    # Read file.
    txt = hparser.read_file(in_file_name)
    # Transform.
    txt_tmp = "\n".join(txt)
    if args.action == "convert_md_to_latex":
        txt_out = _convert_pandoc_md_to_latex(txt_tmp)
    else:
        hdbg.dfatal("Invalid action='%s'", args.action)
    # Write file.
    hparser.write_file(txt_out.split("\n"), out_file_name)


if __name__ == "__main__":
    _main(_parse())
