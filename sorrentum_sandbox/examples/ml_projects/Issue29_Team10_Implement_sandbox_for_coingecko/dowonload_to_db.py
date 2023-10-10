import argparse
import logging

import Issue29_Team10_Implement_sandbox_for_coingecko.db_coingecko as sisebidb
import Issue29_Team10_Implement_sandbox_for_coingecko.download_coingecko as sisebido
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser

"""
Download data from CoinGecko and save it into the DB.
Use as:
> dowonload_to_db.py \
    --from_timestamp '1679016228 ' \
    --to_timestamp '1681694628' \
    --target_table 'coingecko_historic'\
    --api 'CoinGeckoAPI()'\
    --id 'bitcoin'
"""
_LOG = logging.getLogger(__name__)


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--from_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, in UNIX",
    )
    parser.add_argument(
        "--to_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the loaded period, in UNIX",
    )
    parser.add_argument(
        "--api",
        action="store",
        default="CoinGeckoAPI()",
        type=str,
        help="Base API",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Name of the db table to save data into",
    )
    parser.add_argument(
        "--id",
        action="store",
        required=True,
        type=str,
        help="Name of coin to load",
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
    from_timestamp = str(args.from_timestamp)
    to_timestamp = str(args.to_timestamp)
    id = str(args.id)
    downloader = sisebido.CGDownloader(api=args.api)
    raw_data = downloader.download(id, from_timestamp, to_timestamp)
    # Save data to DB.
    db_conn = sisebidb.get_db_connection()
    saver = sisebidb.PostgresDataFrameSaver(db_conn)
    saver.save(raw_data, args.target_table)


if __name__ == "__main__":
    _main(_parse())
