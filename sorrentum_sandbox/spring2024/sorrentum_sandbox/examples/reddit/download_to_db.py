#!/usr/bin/env python
"""
Download reddit data and save it into the DB.

Use as:
> download_to_db.py \
    --start_timestamp '2022-10-20 10:00:00+00:00' \
    --end_timestamp '2022-10-21 15:30:00+00:00' \
    --collection_name posts
"""
import argparse
import logging

import pandas as pd
import pymongo

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.examples.reddit.db as ssexredb
import sorrentum_sandbox.examples.reddit.download as ssexredo

_LOG = logging.getLogger(__name__)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # Convert timestamps.
    start_timestamp = pd.Timestamp(args.start_timestamp)
    end_timestamp = pd.Timestamp(args.end_timestamp)
    downloader = ssexredo.PostsDownloader()
    raw_data = downloader.download(
        start_timestamp=start_timestamp, end_timestamp=end_timestamp
    )
    if len(raw_data.get_data()) > 0:
        _LOG.info("Connecting to Mongo")
        mongo_saver = ssexredb.MongoDataSaver(
            mongo_client=pymongo.MongoClient(
                host=ssexredb.MONGO_HOST,
                port=27017,
                username="mongo",
                password="mongo",
            ),
            db_name="reddit",
        )
        _LOG.info("Saving %s records into Mongo", len(raw_data.get_data()))
        mongo_saver.save(data=raw_data, collection_name=args.collection_name)
    else:
        _LOG.info(
            "Empty output for datetime range: %s - %s",
            args.start_timestamp,
            args.end_timestamp,
        )


def add_download_args(
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
        help="Beginning of the downloaded period, "
        "e.g. 2022-02-09 10:00:00+00:00",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the downloaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--collection_name",
        action="store",
        required=False,
        default="posts",
        type=str,
        help="Collection name to save raw data in the MongoDB",
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


if __name__ == "__main__":
    _main(_parse())
