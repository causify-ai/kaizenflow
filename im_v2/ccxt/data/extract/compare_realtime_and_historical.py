#!/usr/bin/env python
"""
Compare data on DB and S3, raising when difference was found.

Use as:
# Compare daily S3 and realtime data for binance.
> im_v2/ccxt/data/extract/compare_realtime_and_historical.py \
   --db_stage 'dev' \
   --start_timestamp 20220216-000000 \
   --end_timestamp 20220217-000000 \
   --exchange_id 'binance' \
   --db_table 'ccxt_ohlcv_test' \
   --aws_profile 'ck' \
   --s3_path 's3://cryptokaizen-data-test/daily_staged/'

Import as:

import im_v2.ccxt.data.extract.compare_realtime_and_historical as imvcdecrah
"""
import argparse
import logging
import os

import pandas as pd
import psycopg2

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hparser as hparser
import helpers.hs3 as hs3
import helpers.hsql as hsql
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.im_lib_tasks as imvimlita

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--start_timestamp",
        action="store",
        required=True,
        type=str,
        help="Beginning of the compared period",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the compared period",
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use",
    )
    parser.add_argument(
        "--exchange_id",
        action="store",
        required=True,
        type=str,
        help="Exchange for which the comparison should be done",
    )
    parser.add_argument(
        "--db_table",
        action="store",
        required=False,
        default="ccxt_ohlcv",
        type=str,
        help="(Optional) DB table to use, default: 'ccxt_ohlcv'",
    )
    parser = hparser.add_verbosity_arg(parser)
    parser = hs3.add_s3_args(parser)
    return parser  # type: ignore[no-any-return]


def _filter_duplicates(data: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates from data based on exchange id and timestamp.

    Keeps the row with the latest 'knowledge_timestamp' value.

    :param data: Dataframe to process
    :return: data with duplicates removed
    """
    duplicate_columns = ["exchange_id", "timestamp", "currency_pair"]
    # Sort values.
    data = data.sort_values("knowledge_timestamp", ascending=False)
    use_index = False
    _LOG.info("Dataframe length before duplicate rows removed: %s", len(data))
    # Remove duplicates.
    data = hpandas.drop_duplicates(
        data, use_index, subset=duplicate_columns
    ).sort_index()
    _LOG.info("Dataframe length after duplicate rows removed: %s", len(data))
    return data


def _run(args: argparse.Namespace) -> None:
    # Get time range for last 24 hours.
    start_timestamp = pd.Timestamp(args.start_timestamp, tz="UTC")
    end_timestamp = pd.Timestamp(args.end_timestamp, tz="UTC")
    # Connect to database.
    env_file = imvimlita.get_db_env_path(args.db_stage)
    try:
        # Connect with the parameters from the env file.
        connection_params = hsql.get_connection_info_from_env_file(env_file)
        connection = hsql.get_connection(*connection_params)
    except psycopg2.OperationalError:
        # Connect with the dynamic parameters (usually during tests).
        actual_details = hsql.db_connection_to_tuple(args.connection)._asdict()
        connection_params = hsql.DbConnectionInfo(
            host=actual_details["host"],
            dbname=actual_details["dbname"],
            port=int(actual_details["port"]),
            user=actual_details["user"],
            password=actual_details["password"],
        )
        connection = hsql.get_connection(*connection_params)
    # Convert timestamps to unix ms format used in OHLCV data.
    unix_start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
        start_timestamp
    )
    unix_end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp)
    # Read data from DB.
    query = (
        f"SELECT * FROM {args.db_table} WHERE timestamp >='{unix_start_timestamp}'"
        f" AND timestamp <= '{unix_end_timestamp}' AND exchange_id='{args.exchange_id}'"
    )
    rt_data = hsql.execute_query_to_df(connection, query)
    # Remove duplicate rows.
    rt_data_filtered = _filter_duplicates(rt_data)
    expected_columns = [
        "timestamp",
        "currency_pair",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    # Reindex the data.
    rt_data_reindex = imvcdttrut.reindex_on_custom_columns(
        rt_data_filtered, expected_columns[:2], expected_columns
    )
    # List files for given exchange.
    exchange_path = os.path.join(args.s3_path, args.exchange_id) + "/"
    timestamp_filters = hparque.get_parquet_filters_from_timestamp_interval(
        "by_year_month", start_timestamp, end_timestamp
    )
    # Read data corresponding to given time range.
    daily_data = hparque.from_parquet(
        exchange_path, filters=timestamp_filters, aws_profile=args.aws_profile
    )

    daily_data = daily_data.loc[daily_data["timestamp"] >= unix_start_timestamp]
    daily_data = daily_data.loc[daily_data["timestamp"] <= unix_end_timestamp]
    # Remove duplicate rows.
    daily_data_filtered = _filter_duplicates(daily_data)
    # Reindex the data.
    daily_data_reindex = imvcdttrut.reindex_on_custom_columns(
        daily_data_filtered, expected_columns[:2], expected_columns
    )
    # Inform if both dataframes are empty,
    # most likely there is a wrong arg value given.
    if rt_data_reindex.empty and daily_data_reindex.empty:
        message = (
            "Both realtime and staged data are missing, \n"
            + "Did you provide correct arguments?"
        )
        hdbg.dfatal(message=message)
    # Get missing data.
    rt_missing_data, daily_missing_data = hpandas.find_gaps_in_dataframes(
        rt_data_reindex, daily_data_reindex
    )
    # Compare dataframe contents.
    data_difference = hpandas.compare_dataframe_rows(
        rt_data_reindex, daily_data_reindex
    )
    # Show difference and raise if one is found.
    error_message = []
    if not rt_missing_data.empty:
        error_message.append("Missing real time data:")
        error_message.append(
            hpandas.get_df_signature(
                rt_missing_data, num_rows=len(rt_missing_data)
            )
        )
    if not daily_missing_data.empty:
        error_message.append("Missing daily data:")
        error_message.append(
            hpandas.get_df_signature(
                daily_missing_data, num_rows=len(daily_missing_data)
            )
        )
    if not data_difference.empty:
        error_message.append("Differing table contents:")
        error_message.append(
            hpandas.get_df_signature(
                data_difference, num_rows=len(data_difference)
            )
        )
    if error_message:
        hdbg.dfatal(message="\n".join(error_message))
    _LOG.info("No differences were found between real time and daily data")


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args)


if __name__ == "__main__":
    _main(_parse())
