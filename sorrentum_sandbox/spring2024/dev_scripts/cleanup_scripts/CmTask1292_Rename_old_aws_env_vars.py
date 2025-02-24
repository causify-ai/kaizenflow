#!/usr/bin/env python
"""
Simple replacement of AWS env variables.

Simple usage:

> ./dev_scripts/cleanup_scripts/CmTask1292_Rename_old_aws_env_vars.py
"""

import argparse
import logging
import re

import dev_scripts.replace_text as dscretex
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Environment variables to replace.
    variables = [
        ("AM_S3_BUCKET", "AM_AWS_S3_BUCKET"),
        ("AWS_ACCESS_KEY_ID", "AM_AWS_ACCESS_KEY_ID"),
        ("AWS_SECRET_ACCESS_KEY", "AM_AWS_SECRET_ACCESS_KEY"),
        ("AWS_DEFAULT_REGION", "AM_AWS_DEFAULT_REGION"),
    ]
    all_files = dscretex._get_all_files(
        ["."], ["py", "ipynb", "txt", "log", "sh"]
    )
    # Remove current script from the result.
    if __file__ in all_files:
        all_files.remove(__file__)
    for file_name in all_files:
        file_string = hio.from_file(file_name, encoding=dscretex._ENCODING)
        for old_env_var, new_env_var in variables:
            if old_env_var not in file_string:
                continue
            # Replace exact matches.
            file_string = re.sub(rf"\b{old_env_var}\b", new_env_var, file_string)
        hio.to_file(file_name, file_string)


if __name__ == "__main__":
    _main(_parse())
