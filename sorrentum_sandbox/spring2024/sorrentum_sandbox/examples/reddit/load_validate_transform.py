#!/usr/bin/env python
"""
Load and validate data within a specified time period from MongoDB collection,
extract features and load back to the DB.

# Load Reddit data:
> load_validate_transform.py \
    --start_timestamp '2022-10-20 12:00:00+00:00' \
    --end_timestamp '2022-10-21 12:00:00+00:00' \
    --source_collection 'posts' \
    --target_collection 'processed_posts'
"""
import argparse
import logging

import pandas as pd
import pymongo

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.validate as ssacoval
import sorrentum_sandbox.examples.reddit.db as ssexredb
import sorrentum_sandbox.examples.reddit.transform as ssexretr
import sorrentum_sandbox.examples.reddit.validate as ssexreva

_LOG = logging.getLogger(__name__)

# #############################################################################
# Script.
# #############################################################################


def _add_load_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. `2022-02-09 10:00:00+00:00`",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the loaded period, e.g. `2022-02-10 10:00:00+00:00`",
    )
    parser.add_argument(
        "--source_collection",
        action="store",
        required=False,
        type=str,
        default="posts",
        help="DB collection to load data from",
    )
    parser.add_argument(
        "--target_collection",
        action="store",
        required=False,
        default="processed_posts",
        type=str,
        help="DB collection to save transformed data into",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_load_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(use_exec_path=True)
    # Convert timestamps.
    start_timestamp = pd.Timestamp(args.start_timestamp)
    end_timestamp = pd.Timestamp(args.end_timestamp)
    # 1) Build client.
    mongodb_client = pymongo.MongoClient(
        host=ssexredb.MONGO_HOST, port=27017, username="mongo", password="mongo"
    )
    reddit_mongo_client = ssexredb.MongoClient(mongodb_client, "reddit")
    # 2) Load data.
    data = reddit_mongo_client.load(
        dataset_signature=args.source_collection,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    if len(data) == 0:
        _LOG.info("Loaded dataset is empty.")
        return
    _LOG.info("Loaded data: \n %s", data.head())
    empty_title_check = ssexreva.EmptyTitleCheck()
    positive_number_of_comments_check = ssexreva.PositiveNumberOfCommentsCheck()
    dataset_validator = ssacoval.SingleDatasetValidator(
        [empty_title_check, positive_number_of_comments_check]
    )
    # 3) Validate data.
    dataset_validator.run_all_checks([data])
    # 4) Transform data.
    features = ssexretr.extract_features(data)
    # 5) Save back to db.
    _LOG.info("Extracted features: \n %s", features.head())
    db_saver = ssexredb.MongoDataSaver(
        mongo_client=mongodb_client, db_name="reddit"
    )
    db_saver.save(
        data=ssacodow.RawData(features), collection_name=args.target_collection
    )
    _LOG.info("Features saved to MongoDB.")


if __name__ == "__main__":
    _main(_parse())
