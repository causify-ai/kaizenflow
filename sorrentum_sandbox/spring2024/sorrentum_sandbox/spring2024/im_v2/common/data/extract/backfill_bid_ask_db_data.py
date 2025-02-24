#!/usr/bin/env python
"""
A script to backfill DB with bid/ask data.

This script can be used to insert data from an S3 dataset into a database table
in case there is some data missing for a given time interval (e.g. when a
realtime downloader experiences an outage).

Import as:

import im_v2.common.extract.backfill_bid_ask_db_data as imvcebbadd

Usage sample:

./im_v2/common/data/extract/backfill_bid_ask_db_data.py \
   --start_timestamp '2023-01-01 00:01:00+00:00' \
   --end_timestamp '2023-01-02 00:00:00+00:00' \
   --stage 'dev' \
   --assert_missing_data true \
   --db_table 'ccxt_bid_ask_futures_resampled_1min' \
   --s3_dataset_signature 'periodic_daily.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0'
"""
import argparse
import logging

import pandas as pd

import data_schema.dataset_schema_utils as dsdascut
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)


def _check_gaps_by_interval_in_db(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    stage: str,
    db_table: str,
) -> bool:
    """
    Load data from DB and check gaps for the interval.

    :param start_timestamp: start datetime of the interval to load
    :param end_timestamp: end datetime of the interval to load
    :param stage: current stage to search
    :param db_table: the name of the DB table
    :return: true if gaps found
    """
    db_connection = imvcddbut.DbConnectionManager.get_connection(stage)
    data = imvcddbut.fetch_bid_ask_rt_db_data(
        db_connection, db_table, start_timestamp, end_timestamp
    )
    data_frequency = "T"
    checker = imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        start_timestamp, end_timestamp, data_frequency
    )
    return not checker.check(datasets=[data])


def _load_data_from_s3(
    stage: str,
    dataset_signature: str,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
) -> pd.DataFrame:
    """
    Load data from S3 given a dataset signature.

    :param stage: local, test, dev AKA pre-prod, and prod
    :param dataset_signature: dataset signature,
          e.g. 'periodic_daily.airflow.downloaded_1min.csv.bid_ask.futures.v7.crypto_chassis.binance.v1_0_0'
    :param start_timestamp: start datetime of an interval
    :param and_timestamp: end datetime of an interval
    :return: received data
    """
    # Load data from S3.
    reader = imvcdcimrdc.RawDataReader(signature=dataset_signature, stage=stage)
    data = reader.read_data(start_timestamp, end_timestamp)
    # Process data.
    # Convert timestamp from seconds to milliseconds
    # (CryptoChassis timestamp is stored in Unix seconds).
    data["timestamp"] *= 1000
    # Check gaps.
    data_frequency = "T"
    checker = imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        start_timestamp, end_timestamp, data_frequency
    )
    gap_check_result = checker.check(datasets=[data])
    if not gap_check_result:
        raise RuntimeError(f"The data from S3 have gaps: {checker.get_status()}")
    return data


def _run(args: argparse.Namespace) -> None:
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Process parameters.
    args = vars(args)
    start_timestamp = pd.Timestamp(args["start_timestamp"])
    end_timestamp = pd.Timestamp(args["end_timestamp"])
    hdateti.dassert_has_tz(start_timestamp)
    hdateti.dassert_tz_compatible(start_timestamp, end_timestamp)
    hdbg.dassert_lt(
        start_timestamp, end_timestamp, "end_timestamp is less than start_time"
    )
    hdbg.dassert_in(
        "resampled_1min",
        args["db_table"],
        "Table name not related to resampled_1min is not supported yet.",
    )
    hdbg.dassert_in(
        "resampled_1min",
        args["s3_dataset_signature"],
        "Dataset signature not related to resampled_1min is not supported yet.",
    )
    # Check gaps.
    if args["assert_missing_data"] == "true":
        gaps_found = _check_gaps_by_interval_in_db(
            start_timestamp,
            end_timestamp,
            args["stage"],
            args["db_table"],
        )
        if not gaps_found:
            raise RuntimeError(
                f"No gaps found in the given interval: "
                f"[{start_timestamp} - {end_timestamp}]"
            )
    # Load data from S3.
    s3_data = _load_data_from_s3(
        args["stage"],
        args["s3_dataset_signature"],
        start_timestamp,
        end_timestamp,
    )
    # Convert S3 data to DB format.
    data_for_db = imvcdttrut.transform_s3_to_db_format(s3_data)
    # Populate data to DB table.
    db_connection = imvcddbut.DbConnectionManager.get_connection(args["stage"])
    dataset_schema = dsdascut.get_dataset_schema()
    signature_args = dsdascut.parse_dataset_signature_to_args(
        args["s3_dataset_signature"], dataset_schema
    )
    imvcddbut.save_data_to_db(
        data_for_db,
        signature_args["data_type"],
        db_connection,
        args["db_table"],
        start_timestamp.tzname(),
    )
    _LOG.info(
        "%s rows successfully inserted into %s in %s stage.",
        data_for_db.shape[0],
        args["db_table"],
        args["stage"],
    )


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = hparser.add_verbosity_arg(parser)
    parser.add_argument(
        "--s3_dataset_signature",
        action="store",
        required=True,
        type=str,
        help="Source dataset used to backfill DB table",
    )
    parser.add_argument(
        "--assert_missing_data",
        action="store",
        required=True,
        type=bool,
        help="If True, raises an exception if no gaps (missing timestamps)"
        " in DB data are found in a specified time interval, "
        " otherwise proceeds without interruption",
    )
    parser.add_argument(
        "--db_table",
        action="store",
        required=True,
        type=str,
        help="DB table to backfill data into",
    )
    parser.add_argument(
        "--stage",
        action="store",
        required=True,
        type=str,
        help="Stage to run at: dev, local, pre-prod, prod.",
    )
    parser.add_argument(
        "--start_timestamp",
        action="store",
        required=True,
        type=str,
        help="Beginning of the datetime interval",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the datetime interval",
    )
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    _main(_parse())
