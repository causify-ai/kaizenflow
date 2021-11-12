#!/usr/bin/env python

# TODO(gp): CmampTask413: This is useful in general it should be generalized 
# and go in im/scripts

r"""
Convert data from S3 to SQL and inserts it into DB.

Usage examples:
- Convert daily data for AAPL and provider "kibot":
  > convert_s3_to_sql.py \
      --provider kibot \
      --symbol AAPL \
      --frequency D \
      --contract_type continuous \
      --asset_class stocks \
      --exchange NYSE \
      --currency USD

- Convert daily data for AAPL, Kibot provider, specifying connection:
  > convert_s3_to_sql.py \
      --provider kibot \
      --symbol AAPL \
      --frequency D \
      --contract_type continuous \
      --asset_class stocks \
      --exchange NYSE \
      --currency USD \
      --dbname im_postgres_db_local \
      --dbhost im_postgres_local \
      --dbuser menjgbcvejlpcbejlc \
      --dbpass eidvlbaresntlcdbresntdjlrs \
      --dbport 5432

- Convert daily data for all continuous futures symbols for IB:
  > convert_s3_to_sql.py \
      --provider ib \
      --frequency D \
      --contract_type continuous \
      --asset_class futures \
      --exchange NYMEX \
      --currency USD

- Convert daily data for all continuous futures for IB for a date range:
  > convert_s3_to_sql.py \
      --provider ib \
      --frequency D \
      --contract_type continuous \
      --asset_class futures \
      --exchange NYMEX \
      --currency USD \
      --start_ts 20210101000000 \
      --end_ts 20210301000000 \
      --incremental
"""

import argparse
import logging
import os
from typing import List

import pandas as pd

import helpers.dbg as dbg
import helpers.parser as hparse
import im.app.services.file_path_generator_factory as iasfil
import im.app.services.loader_factory as iasloa
import im.app.services.sql_writer_factory as iassql
import im.app.services.symbol_universe_factory as iassym
import im.app.services.transformer_factory as iastra
import im.common.data.load.abstract_data_loader as icdlab
import im.common.data.transform.transform as icdttr
import im.common.data.types as icdtyp
import im.common.metadata.symbols as icmsym

_LOG = logging.getLogger(__name__)


# TODO(*): Pass symbol, exchange, ... and add some unit testing to this.
#  We can use playback for creating unit tests.
def _get_symbols_from_args(args: argparse.Namespace) -> List[icmsym.Symbol]:
    """
    Get list of symbols to extract.
    """
    # If all args are specified to extract only one symbol, return this symbol.
    if args.symbol and args.exchange and args.asset_class and args.currency:
        return [
            icmsym.Symbol(
                ticker=args_symbol,
                exchange=args.exchange,
                asset_class=args.asset_class,
                contract_type=args.contract_type,
                currency=args.currency,
            )
            for args_symbol in args.symbol
        ]
    # Find all matched symbols otherwise.
    file_path_generator = iasfil.FilePathGeneratorFactory.get_file_path_generator(
        args.provider
    )
    latest_symbols_file = file_path_generator.get_latest_symbols_file()
    symbol_universe = iassym.SymbolUniverseFactory.get_symbol_universe(
        args.provider, symbols_file=latest_symbols_file
    )
    if args.symbol is None:
        args_symbols = [args.symbol]
    else:
        args_symbols = args.symbol
    symbols: List[icmsym.Symbol] = []
    for symbol in args_symbols:
        symbols.extend(
            symbol_universe.get(
                ticker=symbol,
                exchange=args.exchange,
                asset_class=args.asset_class,
                contract_type=args.contract_type,
                currency=args.currency,
                is_downloaded=True,
                frequency=args.frequency,
                path_generator=file_path_generator,
            )
        )
    return symbols


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--provider",
        type=str,
        help="Provider to transform",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="Download data serially",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Symbols to process",
        action="append",
        required=False,
    )
    parser.add_argument(
        "--exchange",
        type=str,
        help="Selected Exchange",
        required=False,
    )
    parser.add_argument(
        "--asset_class",
        type=icdtyp.AssetClass,
        help="Asset class (e.g. Futures)",
        required=False,
    )
    parser.add_argument(
        "--currency",
        type=str,
        help="Symbol currency (e.g. USD)",
        required=False,
    )
    parser.add_argument(
        "--frequency",
        type=icdtyp.Frequency,
        help="Frequency of data (e.g. Minutely)",
        required=True,
    )
    parser.add_argument(
        "--contract_type",
        type=icdtyp.ContractType,
        help="Contract type (e.g. Expiry)",
        required=False,
    )
    parser.add_argument(
        "--start_ts",
        type=pd.Timestamp,
        help="Start timestamp. Example: 2021-02-01T00:00:00",
    )
    parser.add_argument(
        "--end_ts",
        type=pd.Timestamp,
        help="Ending timestamp. Example: 2021-02-05T00:00:00",
    )
    parser.add_argument("--incremental", action="store_true", default=False)
    parser.add_argument(
        "--unadjusted",
        action="store_true",
        help="Set if data is unadjusted in S3",
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
    hparse.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level)
    dbg.shutup_chatty_modules()
    # Set up parameters for running.
    provider = args.provider
    symbols = _get_symbols_from_args(args)
    s3_data_loader: icdlab.AbstractS3DataLoader = iasloa.LoaderFactory.get_loader(
        storage_type="s3", provider=provider
    )
    s3_to_sql_transformer = iastra.TransformerFactory.get_s3_to_sql_transformer(
        provider=provider
    )
    sql_writer_backend = iassql.SqlWriterFactory.get_sql_writer_backend(
        provider=provider,
        dbname=args.dbname,
        user=args.dbuser,
        password=args.dbpass,
        host=args.dbhost,
        port=args.dbport,
    )
    sql_data_loader: icdlab.AbstractSqlDataLoader = (
        iasloa.LoaderFactory.get_loader(
            storage_type="sql",
            provider=provider,
            dbname=args.dbname,
            user=args.dbuser,
            password=args.dbpass,
            host=args.dbhost,
            port=args.dbport,
        )
    )
    _LOG.info("Connecting to database")
    sql_writer_backend.ensure_exchange_exists(args.exchange)
    exchange_id = sql_data_loader.get_exchange_id(args.exchange)
    # Select symbols to process.
    if args.max_num_assets is not None:
        _LOG.warning(
            "Selected only %d symbols as per user request", args.max_num_assets
        )
        dbg.dassert_lte(1, args.max_num_assets)
        symbols = symbols[: args.max_num_assets]
    # Construct list of parameters.
    params_list = []
    for symbol in symbols:
        params_list.append(
            dict(
                symbol=symbol.ticker,
                max_num_rows=args.max_num_rows,
                s3_data_loader=s3_data_loader,
                sql_writer_backend=sql_writer_backend,
                sql_data_loader=sql_data_loader,
                s3_to_sql_transformer=s3_to_sql_transformer,
                asset_class=symbol.asset_class,
                contract_type=symbol.contract_type,
                frequency=args.frequency,
                unadjusted=args.unadjusted,
                exchange_id=exchange_id,
                exchange=symbol.exchange,
                currency=symbol.currency,
                incremental=args.incremental,
                start_ts=args.start_ts,
                end_ts=args.end_ts,
            )
        )
    # Run converting.
    icdttr.convert_s3_to_sql_bulk(serial=args.serial, params_list=params_list)
    _LOG.info("Closing database connection")
    sql_writer_backend.close()
    sql_data_loader.conn.close()


if __name__ == "__main__":
    _main(_parse())
