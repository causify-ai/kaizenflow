#!/usr/bin/env python
"""
Script to download OHLCV data for a single exchange from CCXT.

Use as:

# Download OHLCV spot data for binance 'v7', saving dev_stage:
> im_v2/ccxt/data/extract/download_exchange_data_to_db.py \
    --download_mode 'bulk' \
    --downloading_entity 'manual' \
    --action_tag 'downloaded_1min' \
    --vendor 'ccxt' \
    --start_timestamp '2022-11-03 18:00:00+00:00' \
    --end_timestamp '2022-11-03 19:10:00+00:00' \
    --exchange_id 'binance' \
    --universe 'v7' \
    --db_stage 'dev' \
    --db_table 'ccxt_ohlcv_test' \
    --data_type 'ohlcv' \
    --data_format 'postgres' \
    --contract_type 'spot'
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hs3 as hs3
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = hparser.add_verbosity_arg(parser)
    parser = imvcdeexut.add_exchange_download_args(parser)
    parser = imvcddbut.add_db_args(parser)
    parser = hs3.add_s3_args(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Initialize the Extractor class.
    exchange = imvcdeexut.get_CcxtExtractor(args.exchange_id, args.contract_type)
    args = vars(args)
    # The vendor argument is added for compatibility so for CCXT-specific
    #  scripts it should be 'ccxt'.
    hdbg.dassert_eq(args["vendor"], "ccxt")
    imvcdeexut.download_exchange_data_to_db(args, exchange)


if __name__ == "__main__":
    _main(_parse())
