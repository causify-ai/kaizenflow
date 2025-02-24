#!/usr/bin/env python
"""
Download OHLCV data from Binance and save it into the DB.

Use as:
> download_to_db.py \
    --start_timestamp '2022-10-21 10:00:00+00:00' \
    --end_timestamp '2022-10-21 15:30:00+00:00' \
    --target_table 'binance_ohlcv_spot_downloaded_1min'
"""
import argparse
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.examples.ml_projects.Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap.db as ssempitisfbaud
import sorrentum_sandbox.examples.ml_projects.Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap.download as sisebido

_LOG = logging.getLogger(__name__)


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. 2022-02-09 10:00:00+00:00",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=False,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Name of the db table to save data into",
    )

    parser.add_argument(
        "--live_flag",
        action="store_true",
        required=False,
        help="Flag for running in live mode"
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
    start_timestamp = (args.start_timestamp)
    end_timestamp = (args.end_timestamp)

    target_table = (args.target_table)
    live_flag = (args.live_flag)
    # downloader = sisebido.bitqueryApiDownloader()  ## TODO Alter here, create if statement and flag for realtime data
    raw_data = sisebido.run_bitquery_query(start_timestamp, target_table, end_timestamp,live_flag)

    # Save data to DB.
    db_conn = sisebidb.get_db_connection()
    saver = sisebidb.PostgresDataFrameSaver(db_conn,target_table)
    saver.save(raw_data, args.target_table)


if __name__ == "__main__":
    _main(_parse())
