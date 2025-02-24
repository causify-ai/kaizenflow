#!/usr/bin/env python
"""
Load and validate data within a specified time period from a PostgreSQL table,
resample, and load back the result into PostgreSQL.

# Load, validate and transform OHLCV data for binance:
> load_validate_transform.py \
    --start_timestamp '2022-10-20 12:00:00+00:00' \
    --end_timestamp '2022-10-21 12:00:00+00:00' \
    --source_table 'binance_ohlcv_spot_downloaded_1min' \
    --target_table 'binance_ohlcv_spot_resampled_5min'
"""
import argparse
import logging
from datetime import timedelta

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.validate as ssacoval
import sorrentum_sandbox.examples.binance.db as ssesbidb
import sorrentum_sandbox.examples.binance.validate as ssesbiva

_LOG = logging.getLogger(__name__)


# #############################################################################
# Data processing.
# #############################################################################


def _resample_data_to_5min(data: pd.DataFrame) -> pd.DataFrame:
    """
    Resample 1 minute OHLCV data to 5 minutes.

    :param data: DataFrame to resample
    """
    resample_func_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    # Convert unix epoch column to timestamp to enable pandas resampling.
    data["timestamp"] = data["timestamp"].apply(
        hdateti.convert_unix_epoch_to_timestamp
    )
    data = data.set_index("timestamp", drop=True)
    resampled_dfs = []
    for currency_pair in data["currency_pair"].unique():
        data_single_curr = data[data["currency_pair"] == currency_pair]
        resampled_data = data_single_curr.resample(
            "5T", closed="left", label="right"
        ).agg(resample_func_dict)
        resampled_data = resampled_data.reset_index()
        # Add currency_pair column back, as it was removed during resampling
        # process.
        resampled_data["currency_pair"] = currency_pair
        resampled_dfs.append(resampled_data)
    resampled_data = pd.concat(resampled_dfs, axis=0)
    # Convert timestamp column back to unix epoch.
    resampled_data["timestamp"] = resampled_data["timestamp"].apply(
        hdateti.convert_timestamp_to_unix_epoch
    )
    # This data is not downloaded so end_download_timestamp is None.
    resampled_data["end_download_timestamp"] = None
    return resampled_data


# #############################################################################
# Script.
# #############################################################################


def _add_load_args(
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
        required=True,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--source_table",
        action="store",
        required=True,
        type=str,
        help="DB table to load data from",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="DB table to save transformed data into",
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
    # 1) Load data.
    db_conn = ssesbidb.get_db_connection()
    db_client = ssesbidb.PostgresClient(db_conn)
    data = db_client.load(
        args.source_table,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    _LOG.info(f"Loaded data: \n {data.head()}")
    # 2) QA
    empty_dataset_check = ssesbiva.EmptyDatasetCheck()
    # Conforming to the (a, b] interval convention, remove 1 minute from the
    # end_timestamp.
    gaps_in_timestamp_check = ssesbiva.GapsInTimestampCheck(
        start_timestamp, end_timestamp - timedelta(minutes=1)
    )
    dataset_validator = ssacoval.SingleDatasetValidator(
        [empty_dataset_check, gaps_in_timestamp_check]
    )
    # Validate by running all QA checks, if one of them fails, the rest of the
    # code is not executed as it could produce faulty results.
    dataset_validator.run_all_checks([data])
    # 3) Transform data.
    resampled_data = _resample_data_to_5min(data)
    # 4) Save back to DB.
    _LOG.info(f"Transformed data: \n {resampled_data.head()}")
    db_saver = ssesbidb.PostgresDataFrameSaver(db_conn)
    db_saver.save(ssacodow.RawData(resampled_data), args.target_table)


if __name__ == "__main__":
    _main(_parse())
