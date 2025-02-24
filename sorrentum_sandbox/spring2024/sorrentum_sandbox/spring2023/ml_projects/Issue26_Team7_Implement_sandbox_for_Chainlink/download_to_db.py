#!/usr/bin/env python
"""
Download chainlink data from Binance and save it into the DB.

Use as:

> ./download_to_db.py --pair BTC/USD --start_roundid 92233720368547792257 --target_table 'chainlink_real_time'
> ./download_to_db.py --pair BTC/USD --start_roundid 92233720368547792257 --end_roundid 92233720368547792260 --target_table 'chainlink_history'

"""
import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.db as ssempitisfcd
import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.download as sisebido

_LOG = logging.getLogger(__name__)


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--pair",
        action="store",
        required=True,
        type=str,
        help="Currency pair to download",
    )
    parser.add_argument(
        "--start_roundid",
        action="store",
        required=True,
        type=int,
        help="the first data to download",
    )
    parser.add_argument(
        "--end_roundid",
        action="store",
        required=False,
        type=int,
        help="the last data to download",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Name of the db table to save data into",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_download_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # Load data.

    if args.end_roundid is None:
        raw_data = sisebido.downloader(
            pair=args.pair, start_roundid=args.start_roundid
        )
    else:
        raw_data = sisebido.downloader(
            pair=args.pair,
            start_roundid=args.start_roundid,
            end_roundid=args.end_roundid,
        )

    # Save data to DB.
    db_conn = ssempitisfcd.get_db_connection()
    saver = ssempitisfcd.PostgresDataFrameSaver(db_conn)
    saver.save(raw_data, args.target_table)


if __name__ == "__main__":
    _main(_parse())
