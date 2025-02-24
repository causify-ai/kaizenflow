#!/usr/bin/env python

"""
Print the IM DB connection.

Import as:

import im.app.print_db_connection as imaprdbco
"""

import argparse
import logging
import os

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hsql as hsql

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    conn = hsql.get_connection(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    print(conn)


if __name__ == "__main__":
    _main(_parse())
