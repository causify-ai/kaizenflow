#!/usr/bin/env python

# TODO(*): Is this still needed or superseded by app/convert_s3_to_sql.py
r"""
Converts Kibot data on S3 from .csv.gz to SQL and inserts it into DB.

Kibot-specific converter.
Better to use `im.common.data.transform.convert_s3_to_sql`

Usage:
    1. Convert daily data from S3 to SQL:
    > convert_s3_to_sql_kibot.py \
        --dataset sp_500_daily \
        --exchange NYSE

    2. Convert daily data from S3 to SQL specifying connection:
    > convert_s3_to_sql_kibot.py \
        --dataset sp_500_daily \
        --exchange NYSE \
        --dbname im_postgres_db_local \
        --dbhost im_postgres_local \
        --dbuser menjgbcvejlpcbejlc \
        --dbpass eidvlbaresntlcdbresntdjlrs \
        --dbport 5432

"""

import argparse
import logging
import os

import helpers.dbg as dbg
import helpers.parser as hparse
import im.common.data.transform.transform as icdttr
import im.kibot.data.config as ikdcon
import im.kibot.data.load as ikdloa
import im.kibot.data.load.dataset_name_parser as ikdlda
import im.kibot.data.load.kibot_sql_data_loader as ikdlki
import im.kibot.data.transform.kibot_s3_to_sql_transformer as ikdtki
import im.kibot.sql_writer as ikkibo
import im.kibot.metadata.load.s3_backend as ikmls3

_LOG = logging.getLogger(__name__)

_JOBLIB_NUM_CPUS = 10
_JOBLIB_VERBOSITY = 1

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="Download data serially",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Process a specific dataset (or all datasets if omitted)",
        choices=ikdcon.DATASETS,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--exchange",
        type=str,
        help="Selected Exchange",
        required=True,
        default=None,
    )
    parser.add_argument(
        "--dbuser",
        type=str,
        help="Postgres User",
        default=os.environ.get("POSTGRES_USER", None),
    )
    parser.add_argument(
        "--dbpass",
        type=str,
        help="Postgres Password",
        default=os.environ.get("POSTGRES_PASSWORD", None),
    )
    parser.add_argument(
        "--dbhost",
        type=str,
        help="Postgres Host",
        default=os.environ.get("POSTGRES_HOST", None),
    )
    parser.add_argument(
        "--dbport",
        type=int,
        help="Postgres Port",
        default=os.environ.get("POSTGRES_PORT", None),
    )
    parser.add_argument(
        "--dbname",
        type=str,
        help="Postgres DB",
        default=os.environ.get("POSTGRES_DB", None),
    )
    parser.add_argument(
        "--max_num_assets",
        action="store",
        type=int,
        default=None,
        help="Maximum number of assets to copy (for debug)",
    )
    parser.add_argument(
        "--max_num_rows",
        action="store",
        type=int,
        default=None,
        help="Maximum number of rows per asset to copy (for debug)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Continue loading from the last interruption point if any.",
    )
    hparse.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    dbg.shutup_chatty_modules()
    #
    s3_to_sql_transformer = ikdtki.S3ToSqlTransformer()
    #
    kibot_data_loader = ikdloa.KibotS3DataLoader()
    #
    s3_backend = ikmls3.S3Backend()
    #
    dataset_name_parser = ikdlda.DatasetNameParser()
    #
    sql_writer_backed = ikkibo.KibotSqlWriter(
        dbname=args.dbname,
        user=args.dbuser,
        password=args.dbpass,
        host=args.dbhost,
        port=args.dbport,
    )
    #
    sql_data_loader = ikdlki.KibotSqlDataLoader(
        dbname=args.dbname,
        user=args.dbuser,
        password=args.dbpass,
        host=args.dbhost,
        port=args.dbport,
    )
    _LOG.info("Connected to database")
    #
    sql_writer_backed.ensure_exchange_exists(args.exchange)
    exchange_id = sql_data_loader.get_exchange_id(args.exchange)
    # Construct list of parameters to run.
    params_list = []
    # Go over selected datasets or all datasets.
    datasets_to_process = args.dataset or ikdcon.DATASETS
    for dataset in datasets_to_process:
        # Get the symbols from S3.
        symbols = s3_backend.get_symbols_for_dataset(dataset)
        if args.max_num_assets is not None:
            dbg.dassert_lte(1, args.max_num_assets)
            symbols = symbols[: args.max_num_assets]
        # Parse dataset name and extract parameters.
        (
            asset_class,
            contract_type,
            frequency,
            unadjusted,
        ) = dataset_name_parser.parse_dataset_name(dataset)
        for symbol in symbols:
            params_list.append(
                dict(
                    symbol=symbol,
                    max_num_rows=args.max_num_rows,
                    s3_data_loader=kibot_data_loader,
                    sql_writer_backend=sql_writer_backed,
                    sql_data_loader=sql_data_loader,
                    s3_to_sql_transformer=s3_to_sql_transformer,
                    asset_class=asset_class,
                    contract_type=contract_type,
                    frequency=frequency,
                    unadjusted=unadjusted,
                    exchange_id=exchange_id,
                    exchange=args.exchange,
                    incremental=args.incremental,
                )
            )
    _LOG.info("Found %i items to load to database", len(params_list))
    # Run converting.
    icdttr.convert_s3_to_sql_bulk(serial=args.serial, params_list=params_list)
    _LOG.info("Closing database connection")
    sql_writer_backed.close()
    sql_data_loader.conn.close()


if __name__ == "__main__":
    _main(_parse())
