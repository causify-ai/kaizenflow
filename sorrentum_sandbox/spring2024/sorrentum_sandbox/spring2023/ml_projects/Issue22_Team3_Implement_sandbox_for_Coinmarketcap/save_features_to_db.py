#!/usr/bin/env python
"""
Load and validate data within a specified time period from MongoDB collection,
extract features and load back to the DB.

# Load Reddit data:
> load_validate_transform.py \
    --source_collection 'posts' \
    --target_collection 'processed_posts'
"""
import argparse
import logging
import pytz
import pandas as pd
import pandas as pd
import pymongo

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as ssandown
import sorrentum_sandbox.common.validate as sinsaval

import sorrentum_sandbox.examples.ml_projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap as coinmarketcap

coinmarketcap_load = coinmarketcap.load_data_from_db
coinmarketcap_db = coinmarketcap.db
coinmarketcap_features = coinmarketcap.compute_features


_LOG = logging.getLogger(__name__)

# #############################################################################
# Script.
# #############################################################################

def _add_load_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
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


def process_data(cmc_data):
    """
    Process data from source_collection.

    :param cmc_data: Dataframe containing data from source_collection
    :return: Dataframe containing processed data
    """
    cmc_data = cmc_data.rename(columns={'1': 'data'})
    cmc_data = pd.concat([cmc_data[cmc_data.columns.difference(['data'])], pd.json_normalize(cmc_data.data)], axis=1)
    kept_columns = ['name','quote.USD.last_updated','max_supply','total_supply','circulating_supply', 'quote.USD.price', 'quote.USD.market_cap', 'quote.USD.market_cap_dominance', 'quote.USD.fully_diluted_market_cap','quote.USD.volume_24h', ]

    cmc_data = cmc_data[kept_columns]
    cmc_data.columns = cmc_data.columns.str.replace('quote.USD.', '')
    # cmc_data['last_updated'] = pd.to_datetime(cmc_data['last_updated'])
    _LOG.info("Processed data tail: \n %s", cmc_data.tail(20))    

    return cmc_data

def fliter_new_data(cmc_data, features_last_updated):
    """
    Filter out data that has already been processed.

    :param cmc_data: Dataframe containing data from source_collection
    :param features_last_updated: Dataframe containing last updated value from features collection
    :return: Dataframe containing data that has not been processed yet
    """
    if not features_last_updated.empty:
        features_last_updated_value = features_last_updated['last_updated'].iloc[0]
        _LOG.info("1. features_last_updated: \n %s", features_last_updated)
        _LOG.info("2. Last updated value in cmc_data collection: %s", cmc_data['last_updated'].iloc[-1])
        _LOG.info("3. Last updated value in target collection: %s", features_last_updated_value)
        # Find rows index where 'last_updated' is equal to 'features_last_updated'
        matching_row = cmc_data.loc[cmc_data['last_updated'] == features_last_updated_value]
        _LOG.info("4. Matching row: \n %s", matching_row.head())
        if not matching_row.empty:
            # Get rows where 'last_updated' is later than the maximum 'last_updated' value in 'matching_rows'
            later_rows = cmc_data.loc[cmc_data['last_updated'] > matching_row['last_updated'].iloc[0]]
            cmc_data = later_rows
            _LOG.info("5. New data to process: \n %s", cmc_data.head())
            _LOG.info("6. [ %s ] New Data to process.", len(cmc_data))
            return cmc_data
        else:
            _LOG.info("No new data to process.")
            return pd.DataFrame()

def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(use_exec_path=True)


    # Build client
    mongodb_client = pymongo.MongoClient(
        host="host.docker.internal", 
        port=27017, 
        username="mongo", 
        password="mongo"
    )
    coinmarketcap_mongo_client = coinmarketcap_db.MongoClient(mongodb_client, "CoinMarketCap")

    # Load data
    cmc_data = coinmarketcap_mongo_client.load(collection_name=args.source_collection)

    if len(cmc_data) == 0:
        _LOG.info("Loaded dataset is empty.")
        return
    _LOG.info("Loaded data: \n %s", cmc_data.head())

    # Process data
    cmc_data = process_data(cmc_data)


    # Get last updated data from target collection
    features_last_updated = coinmarketcap_mongo_client.get_last_updated(collection_name=args.target_collection)

    # Filter new data to process
    cmc_data = fliter_new_data(cmc_data, features_last_updated)

    # Check if there is new data to process
    if cmc_data.empty:
        return

    # Transform data
    features = coinmarketcap_features.extract_features(cmc_data)

    # Save back to db
    _LOG.info("Extracted features: \n %s", features.head())
    db_saver = coinmarketcap_db.MongoDataSaver(
        mongo_client=mongodb_client, db_name="CoinMarketCap"
    )
    db_saver.save_many(
        data=ssandown.RawData(features), collection_name=args.target_collection
    )
    _LOG.info("Features saved to MongoDB.")

if __name__ == "__main__":
    _main(_parse())