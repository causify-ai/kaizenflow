#!/usr/bin/env python
"""
Download OHLCV data from BlockChain and save it into the DB.
Use as:
> download_to_db.py \
    --start_timestamp '2016-01-01 ' \
    --time_span '6years' \
    --target_table 'Historical_Market_Price'\
    --api 'https://api.blockchain.info/charts'\
    --chart_name 'market-price'
"""
import argparse
import logging

import Block_db as sisebidb
import Block_download as sisebido
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser

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
        help="Beginning of the loaded period, e.g. 2016-01-01 ",
    )
    parser.add_argument(
        "--time_span",
        action="store",
        required=True,
        type=str,
        help="Time span from the start time, e.g. 6year",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Path to the target table to store data",
    )

    parser.add_argument(
        "--api",
        action="store",
        default="https://api.blockchain.info/charts",
        type=str,
        help="Base URL for the API",
    )

    parser.add_argument(
        "--chart_name",
        action="store",
        default="market-price",
        required=True,
        type=str,
        help="Name of the chart to download",
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
    downloader = sisebido.OhlcvRestApiDownloader(
        api=args.api, chart_name=args.chart_name
    )
    raw_data = downloader.download(args.start_timestamp, args.time_span)
    # Save data to DB.
    db_conn = sisebidb.get_db_connection()
    saver = sisebidb.PostgresDataFrameSaver(db_conn)
    saver.save(raw_data, args.target_table)


if __name__ == "__main__":
    _main(_parse())
