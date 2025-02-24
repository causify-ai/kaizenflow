#!/usr/bin/env python

"""
Import as:

import dev_scripts.old.create_conda.install.print_conda_packages as dsoccipcp
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.old.env2 as holdenv2

_LOG = logging.getLogger(__name__)


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    parser.add_argument(
        "--conda_env_name",
        help="Environment name",
        type=str,
        required=True,
    )
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    msg, file_name = holdenv2.save_env_file(args.conda_env_name, dir_name=None)
    print(f"file_name={file_name}")
    print(msg)


if __name__ == "__main__":
    _main()
