#!/usr/bin/env python
# TODO(Grisha): the script might become more general purpose, e.g. dump any data from db.
"""
The script saves market data from the DB to a file.

> dataflow_amp/system/Cx/Cx_dump_market_data.py \
    --dst_file_path '/shared_data/prod_reconciliation/tmp.file_name.csv.gz' \
    --start_timestamp_as_str 20221010_060500 \
    --end_timestamp_as_str 20221010_080000 \
    --db_stage 'prod' \
    --table_name 'ccxt_ohlcv_futures' \
    --universe 'v7.4'
"""
import argparse

import dataflow_amp.system.Cx.utils as dtfasycxut
import helpers.hdbg as hdbg
import helpers.hparser as hparser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dst_file_path",
        action="store",
        required=True,
        type=str,
        help="File path to save market data in."
        "E.g., `/downloads/tmp.file_name.csv.gz`",
    )
    parser.add_argument(
        "--start_timestamp_as_str",
        action="store",
        required=True,
        type=str,
        help="String representation of the earliest date timestamp to load data for.",
    )
    parser.add_argument(
        "--end_timestamp_as_str",
        action="store",
        required=True,
        type=str,
        help="String representation of the latest date timestamp to load data for.",
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        help="Stage of the database to use, e.g. 'prod' or 'local'.",
        required=True,
    )
    parser.add_argument(
        "--table_name",
        action="store",
        required=True,
        type=str,
        help="Name of the table from database",
    )
    parser.add_argument(
        "--universe",
        action="store",
        required=True,
        type=str,
        help="Version of the universe.",
    )
    parser = hparser.add_verbosity_arg(parser)
    # TODO(gp): For some reason, not even this makes mypy happy.
    # cast(argparse.ArgumentParser, parser)
    return parser  # type: ignore


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.dassert_file_extension(args.dst_file_path, "csv.gz")
    dtfasycxut.dump_market_data_from_db(
        args.dst_file_path,
        args.start_timestamp_as_str,
        args.end_timestamp_as_str,
        args.db_stage,
        args.table_name,
        args.universe,
    )


if __name__ == "__main__":
    _main(_parse())
