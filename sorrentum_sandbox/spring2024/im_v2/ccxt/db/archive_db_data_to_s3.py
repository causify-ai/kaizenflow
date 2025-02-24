#!/usr/bin/env python
"""
Archive data older than specified timestamp from a DB table into S3 folder. The
archive is saved as a `parquet` dataset with multiple .pq files.

Use as:
> im_v2/ccxt/db/archive_db_data_to_s3.py \
   --db_stage 'dev' \
   --start_timestamp '2023-10-20 15:46:00+00:00' \
   --end_timestamp '2023-10-30 15:46:00+00:00' \
   --dataset_signature 'periodic_daily.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.binance.v1_0_0' \
   --s3_path 's3://cryptokaizen-data-test/' \
   --dry_run
   --mode 'archive_and_delete'

Import as:

import im_v2.ccxt.db.archive_db_data_to_s3 as imvcdaddts
"""
import argparse
import logging

import pandas as pd

import data_schema.dataset_schema_utils as dsdascut
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hs3 as hs3
import helpers.hsql as hsql
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)

_AWS_PROFILE = "ck"


def _assert_data_continuity(
    db_data: pd.DataFrame,
    last_archived_row: pd.DataFrame,
    table_timestamp_column: str,
    warn_only: bool,
) -> None:
    """
    #TODO(Juraj): we might relax the constraint for bid/ask data to ~5 seconds.
    #TODO(Juraj): a perfect solution would go symbol by symbol to assert the continuity.
    Perform two types of assertions.
        1. Assert that the last archived row is not more than 1 second (1 minute) apart from the
    first to-be-archived row for bid/ask (OHLCV) data.
        2. Assert that the last archived row is not later than the first to-be-archived row.
    If warn_only is True, the script is
    not aborted if a time gap is found, only a warning log message is issued.
    """


def _assert_db_args(
    connection: hsql.DbConnection, db_table: str, table_timestamp_column: str
) -> None:
    """
    Assert the DB table exists and contains the specified column.
    """
    tables = hsql.get_table_names(connection)
    hdbg.dassert_in(db_table, tables)
    table_columns = hsql.get_table_columns(connection, db_table)
    hdbg.dassert_in(table_timestamp_column, table_columns)

# Deprecated in CmTask5432.
# def _assert_archival_mode(
#     # Deprecated in CmTask5432.
#     # incremental: bool,
#     s3_path: str,
# ) -> None:
#     """
#     Assert that the path corresponding to the DB stage and DB table exists if
#     incremental is True, assert the path doesn't exist.

#     :param incremental: if True, the path must exist
#     :param s3_path: path to the S3 folder
#     """
#     # Deprecated in CmTask5432.
#     # if incremental:
#     #     # The profile won't change for the foreseeable future so
#     #     # so we can keep hardcoded.
#     #     hs3.dassert_path_exists(s3_path, aws_profile=_AWS_PROFILE)
#     # else:
#     hs3.dassert_path_not_exists(s3_path, aws_profile=_AWS_PROFILE)


# TODO(Juraj): Create a mechanism to check data continuity.
# def _fetch_latest_row_from_s3(
#     s3_path: str, timestamp: pd.Timestamp
# ) -> pd.DataFrame:
#     """
#     Fetch the latest archived row.
#     """
#     # Assume that archival happens more often than once a month.
#     end_ts = timestamp
#     start_ts = end_ts - timedelta(months=1)
#     timestamp_filters = hparque.get_parquet_filters_from_timestamp_interval(
#         "by_year_month",
#         self.start_ts,
#         timestamp,
#     )
#     # Read data corresponding to given time range.
#     archived_data = hparque.from_parquet(
#         s3_path, filters=timestamp_filters, aws_profile=_AWS_PROFILE
#     )
#     # Data should be sorted but sort again as an insurance.
#     archived_data = archived_data.sort_values("timestamp", ascending=False)
#     return latest_archived_data.head(1)


def _assert_correct_archival(db_data: pd.DataFrame, s3_path: str) -> None:
    """
    Safety check that the data were archived successfully.
    """


def _delete_data_from_db(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    db_conn: hsql.DbConnection,
    db_table: str,
    table_timestamp_column: str,
    exchange_id: str,
    dry_run: bool,
) -> None:
    """
    Delete data from DB table.

    :param connection: DB connection
    :param db_table: DB table name
    :param table_timestamp_column: name of the column containing timestamp
    :param dry_run: if True, the data are not deleted
    """
    # TODO(Sonaal): Should we remove this, it is not getting called. 
    if dry_run:
        _LOG.info("Dry run. Data not deleted.")
        return
    # Delete data from DB.
    num_deleted = imvcddbut.drop_db_data_within_age(
        start_timestamp, end_timestamp, db_conn, db_table, table_timestamp_column, exchange_id
    )
    _LOG.info("Deleted %d rows from DB.", num_deleted)


def _archive_db_data_to_s3(args: argparse.Namespace) -> None:
    """
    Archive data from DB table older than specified timestamp into a S3
    storage, based on `timestamp` column of the table.
    """
    # Transform and assign args for readability.
    (
        # Deprecated in CmTask5432.
        # incremental,
        s3_path,
        db_stage,
        dataset_signature,
        dry_run,
        table_timestamp_column,
        skip_time_continuity_assertion,
        mode,
    ) = (
        # Deprecated in CmTask5432.
        # args.incremental,
        args.s3_path,
        args.db_stage,
        args.dataset_signature,
        args.dry_run,
        args.table_timestamp_column,
        args.skip_time_continuity_assertion,
        args.mode,
    )
    # Get db table name from dataset signature.
    dataset_schema = dsdascut.get_dataset_schema()
    db_table = dsdascut.get_im_db_table_name_from_signature(
        dataset_signature, dataset_schema
    )
    # Replace "download" with "archive" in the dataset signature
    #  and set data format to parquet.
    args_from_signature = dsdascut.parse_dataset_signature_to_args(
        dataset_signature, dataset_schema
    )
    args_from_signature["action_tag"] = args_from_signature["action_tag"].replace(
        "downloaded", "archived"
    )
    args_from_signature["data_format"] = "parquet"
    # Construct S3 path from args.
    s3_dataset_path = dsdascut.build_s3_dataset_path_from_args(
        s3_path, args_from_signature
    )
    start_timestamp = pd.Timestamp(args.start_timestamp, tz="UTC")
    end_timestamp = pd.Timestamp(args.end_timestamp, tz="UTC")
    # Get database connection.
    db_conn = imvcddbut.DbConnectionManager.get_connection(db_stage)
    # Perform argument assertions.
    _assert_db_args(db_conn, db_table, table_timestamp_column)
    # TODO(Sameep): Verify with Juraj if we need this. Deprecated in CmTask5432.
    # _assert_archival_mode(incremental, s3_dataset_path)
    # Fetch DB data.
    db_data = pd.DataFrame()
    if mode in ("archive_only", "archive_and_delete"):
        db_data = imvcddbut.fetch_data_within_age(
            start_timestamp,
            end_timestamp,
            db_conn,
            db_table,
            table_timestamp_column,
            args_from_signature["exchange_id"],
        )
        if db_data.empty:
            _LOG.warning(
                f"There is no data between '{start_timestamp}' and \
                '{end_timestamp}' in '{db_table}' table."
            )
        else:
            _LOG.info(f"Fetched {db_data.shape[0]} rows from '{db_table}'.")
    # Deprecated in CmTask5432.
    # # Fetch latest S3 row upon incremental archival.
    # if incremental:
    #     # TODO(Juraj): CmTask#3087 think about a HW resource friendly solution to this.
    #     # latest_row = _fetch_latest_row_from_s3(s3_path, timestamp)
    #     # Assert time continuity of both datasets.
    #     # _assert_data_continuity(latest_row, skip_time_continuity_assertion)
    #     pass
    if dry_run:
        _LOG.info("Dry run of data archival finished successfully.")
    else:
        if not db_data.empty:
            # Archive the data
            if mode in ("archive_only", "archive_and_delete"):
                unit = "ms"
                data_type = args_from_signature["data_type"]
                # Partition by year, month and day for bid_ask and trades data.
                if data_type in ("bid_ask", "trades"):
                    partition_mode = "by_year_month_day"
                else:
                    partition_mode = "by_year_month"
                imvcdeexut.save_parquet(
                    db_data,
                    s3_dataset_path,
                    unit,
                    _AWS_PROFILE,
                    data_type,
                    # The `id` column is most likely not needed once the data is in S3.
                    drop_columns=["id"],
                    mode="append",
                    partition_mode=partition_mode,
                )
            # Double check archival was successful
            # TODO(Juraj): CmTask#3087 this might a be pretty difficult problem.
            # _assert_correct_archival(db_data, s3_path)
        # Drop DB data.
        if mode in ("archive_and_delete", "delete_only"):
            _delete_data_from_db(
                start_timestamp,
                end_timestamp,
                db_conn,
                db_table,
                table_timestamp_column,
                args_from_signature["exchange_id"],
                dry_run,
            )
        _LOG.info("Data archival finished successfully.")


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _LOG.info(args)
    _archive_db_data_to_s3(args)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        action="store",
        required=False,
        choices=["archive_only", "archive_and_delete", "delete_only"],
        default="archive_only",
        type=str,
        help=(
            """
            How to process the archiving process.
            - `archive_only`: archive only data older than the specified timestamp
            - `archive_and_delete`: archive data older than the specified timestamp (like `archive_only`) but delete the data after it's archived
            - `delete_only`: delete from the DB data older than the specified timestamp
            """
        ),
    )
    parser.add_argument(
        "--start_timestamp",
        action="store",
        required=True,
        type=str,
        help="Time threshold for archival. Data for which"
        + "`table_timestamp_column` > `start_timestamp`, gets archived and dropped",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="Time threshold for archival. Data for which"
        + "`table_timestamp_column` < `end_timestamp`, gets archived and dropped",
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use",
    )
    parser.add_argument(
        "--dataset_signature",
        action="store",
        required=True,
        type=str,
        help="Signature of the dataset (uniquely specifies a particular data set)",
    )
    # TODO(Juraj): for now we assume that the only column used for archival
    #  will be `timestamp`.
    parser.add_argument(
        "--table_timestamp_column",
        action="store",
        required=False,
        default="timestamp",
        type=str,
        help="Table column to use when applying the time threshold",
    )
    # #########################################################################
    # Only a base path needs to be provided, i.e.
    #  when archiving DB table `ccxt_ohlcv_spot` for dev DB
    #  you only need to provide s3://cryptokaizen-data/
    #  The script automatically creates/maintains the subfolder
    #  structure from the dataset signature.
    parser.add_argument(
        "--s3_path",
        action="store",
        required=True,
        type=str,
        help="S3 location to archive data into",
    )
    # Deprecated in CmTask5432.
    # parser.add_argument(
    #     "--incremental",
    #     action="store_true",
    #     required=False,
    #     help="Archival mode, if True the script fails if there is no archive yet \
    #         for the specified table at specified path, vice versa for False",
    # )
    parser.add_argument(
        "--skip_time_continuity_assertion",
        action="store_true",
        required=False,
        help="If specified, the script only warns if the archival operation \
            creates a time gap in the archive data \
            but doesn't abort the execution.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        required=False,
        help="If specified, simulates the execution but doesn't delete \
            DB data nor save any data to s3",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


if __name__ == "__main__":
    _main(_parse())
