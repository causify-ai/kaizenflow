#!/usr/bin/env python
r"""
Extract date from IB Gateway to S3.

Note, that IB Gateway app should be up.

Usage examples:
- Download NQ data to S3:
  > download_ib_data.py \
      --symbol NQ \
      --frequency D \
      --contract_type continuous \
      --asset_class Futures \
      --exchange GLOBEX \
      --currency USD

- Download data by parts:
  > download_ib_data.py \
      --symbol NQ \
      --frequency D \
      --contract_type continuous \
      --asset_class Futures \
      --exchange GLOBEX \
      --currency USD \
      --action download \
      --dst_dir ./tmp

- Push downloaded parts to S3:
  > download_ib_data.py \
      --symbol NQ \
      --frequency D \
      --contract_type continuous \
      --asset_class Futures \
      --exchange GLOBEX \
      --currency USD \
      --action push \

- Download data for all GLOBEX symbols with USD currency:
  > download_ib_data.py \
      --frequency D \
      --exchange GLOBEX \
      --currency USD

Import as:

import im.ib.data.extract.download_ib_data as imidedibda
"""
import argparse
import logging
from typing import List

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import im.common.data.types as imcodatyp
import im.common.metadata.symbols as imcomesym
import im.ib.data.extract.ib_data_extractor as imideidaex
import im.ib.data.load.ib_file_path_generator as imidlifpge
import im.ib.metadata.ib_symbols as imimeibsy

# from tqdm.notebook import tqdm

_LOG = logging.getLogger(__name__)
_DOWNLOAD_ACTION = "download"
_PUSH_TO_S3_ACTION = "push"

VALID_ACTIONS = [_DOWNLOAD_ACTION, _PUSH_TO_S3_ACTION]
DEFAULT_ACTIONS = [_DOWNLOAD_ACTION, _PUSH_TO_S3_ACTION]


def _get_symbols_from_args(args: argparse.Namespace) -> List[imcomesym.Symbol]:
    """
    Get list of symbols to extract.
    """
    # If all args are specified to extract only one symbol, return this symbol.
    if args.symbol and args.exchange and args.asset_class and args.currency:
        return [
            imcomesym.Symbol(
                ticker=args_symbol,
                exchange=args.exchange,
                asset_class=args.asset_class,
                contract_type=args.contract_type,
                currency=args.currency,
            )
            for args_symbol in args.symbol
        ]
    # Find all matched symbols otherwise.
    # Get file with symbols.
    latest_symbols_file = imidlifpge.IbFilePathGenerator.get_latest_symbols_file()
    # Get all symbols.
    symbol_universe = imimeibsy.IbSymbolUniverse(symbols_file=latest_symbols_file)
    # Keep only matched.
    if args.symbol is None:
        args_symbols = [args.symbol]
    else:
        args_symbols = args.symbol
    symbols: List[imcomesym.Symbol] = []
    for symbol in args_symbols:
        symbols.extend(
            symbol_universe.get(
                ticker=symbol,
                exchange=args.exchange,
                asset_class=args.asset_class,
                contract_type=args.contract_type,
                currency=args.currency,
            )
        )
    return symbols


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.shutup_chatty_modules()
    actions = hparser.select_actions(
        args, valid_actions=VALID_ACTIONS, default_actions=DEFAULT_ACTIONS
    )
    # Get symbols to retrieve.
    symbols = _get_symbols_from_args(args)
    # Extract the data.
    extractor = imideidaex.IbDataExtractor()
    for symbol in symbols:
        part_files_dir = args.dst_dir
        if part_files_dir is None:
            part_files_dir = extractor.get_default_part_files_dir(
                symbol=symbol.ticker,
                frequency=args.frequency,
                asset_class=symbol.asset_class,
                contract_type=symbol.contract_type,
                exchange=symbol.exchange,
                currency=symbol.currency,
            )
        # On local machine make sure that path exists.
        if not part_files_dir.startswith("s3://"):
            hio.create_dir(part_files_dir, incremental=True)
        if _DOWNLOAD_ACTION in actions:
            extractor.extract_data_parts_with_retry(
                exchange=symbol.exchange,
                symbol=symbol.ticker,
                asset_class=symbol.asset_class,
                frequency=args.frequency,
                currency=symbol.currency,
                contract_type=symbol.contract_type,
                start_ts=args.start_ts,
                end_ts=args.end_ts,
                incremental=args.incremental,
                part_files_dir=part_files_dir,
            )
        if _PUSH_TO_S3_ACTION in actions:
            extractor.update_archive(
                part_files_dir=part_files_dir,
                symbol=symbol.ticker,
                asset_class=symbol.asset_class,
                frequency=args.frequency,
                contract_type=symbol.contract_type,
                exchange=symbol.exchange,
                currency=symbol.currency,
            )


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
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
        type=imcodatyp.AssetClass,
        help="Asset class (e.g. Futures)",
        required=False,
    )
    parser.add_argument(
        "--contract_type",
        type=imcodatyp.ContractType,
        help="Contract type (e.g. Expiry)",
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
        type=imcodatyp.Frequency,
        help="Frequency of data (e.g. Minutely)",
        required=True,
    )
    parser.add_argument("--start_ts", type=pd.Timestamp)
    parser.add_argument("--end_ts", type=pd.Timestamp)
    parser.add_argument("--incremental", action="store_true", default=False)
    parser.add_argument(
        "--dst_dir", type=str, help="Path to extracted files with partial data"
    )
    hparser.add_action_arg(
        parser, valid_actions=VALID_ACTIONS, default_actions=DEFAULT_ACTIONS
    )
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
