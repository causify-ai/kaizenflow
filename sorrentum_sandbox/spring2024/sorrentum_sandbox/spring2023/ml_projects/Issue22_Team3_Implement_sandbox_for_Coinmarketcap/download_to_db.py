#!/usr/bin/env python
"""
Download CoinMarketCap data and save it into the MongoDB.

Use as:
> download_to_db.py --id '1' --collection_name coinmarketcap_data
"""
import argparse
import logging

import pandas as pd
import pymongo

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.examples.ml_projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap as coinmarketcap

coinmarketcap_db = coinmarketcap.db
coinmarketcap_download = coinmarketcap.download

_LOG = logging.getLogger(__name__)


def add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser.add_argument(
        "--id",
        action="store",
        required=True,
        type=str,
        help="One cryptocurrency CoinMarketCap ID",
    )
    parser.add_argument(
        "--collection_name",
        action="store",
        required=True,
        type=str,
        help="Path to the target directory to store CSV data into",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = add_download_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    downloader = coinmarketcap_download.CMCRestApiDownloader()
    raw_data = downloader.download(args.id)
    if len(raw_data.get_data()) > 0:
        mongo_saver = coinmarketcap_db.MongoDataSaver(
            mongo_client=pymongo.MongoClient(
                host="host.docker.internal",
                port=27017,
                username="mongo",
                password="mongo",
            ),
            db_name="CoinMarketCap",
        )
        mongo_saver.save(data=raw_data, collection_name=args.collection_name)
        _LOG.info("Saving data to MongoDB!")
    else:
        _LOG.info("Empty data")


if __name__ == "__main__":
    _main(_parse())
