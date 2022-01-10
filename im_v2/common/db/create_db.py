#!/usr/bin/env python
"""
Script to create IM (Instrument Master) database using the given connection.

# Create a DB named 'test_db' using environment variables:
> im/common/db/create_db.py --db-name 'test_db'
"""

import argparse
import os

import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsql as hsql
import im_v2.common.db.utils as imvcodbut

# TODO(gp): Consider converting create_db and remove_db into invoke tasks.


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--credentials",
        action="store",
        default="from_env",
        type=str,
        help=(
            "Connection string"
            "or path to json file with credentials to DB"
            "or parameters from environment with"
        ),
    )
    parser.add_argument(
        # TODO(gp): @danya -> db_name (we prefer underscores in options).
        "--db-name",
        action="store",
        required=True,
        type=str,
        help="DB to create",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="To overwrite existing DB",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    json_exists = os.path.exists(os.path.abspath(args.credentials))
    # TODO(gp): @danya deprecate passing credentials from env vars.
    if args.credentials == "from_env":
        connection = hsql.get_connection_from_env_vars()
    elif json_exists:
        connection = hsql.get_connection(**hio.from_json(args.credentials))
    else:
        connection = hsql.get_connection_from_string(args.credentials)
    # Create DB with all tables.
    imvcodbut.create_im_database(
        connection=connection, new_db=args.db_name, overwrite=args.overwrite
    )


if __name__ == "__main__":
    _main(_parse())
