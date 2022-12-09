#!/usr/bin/env python
"""
Script to download OHLCV data for a single exchange from Talos.

Use as:

# Download OHLCV data for binance 'v03', saving dev_stage:
> im_v2/talos/data/extract/download_exchange_data_to_db.py \
    --start_timestamp '2021-11-10T10:11:00.000000Z' \
    --end_timestamp '2021-11-10T10:12:00.000000Z' \
    --exchange_id 'binance' \
    --universe 'v1' \
    --db_stage 'dev' \
    --db_table 'talos_ohlcv' \
    --api_stage 'sandbox' \
    --aws_profile 'ck' \
    --s3_path 's3://<ck-data>/real_time/talos' \
    --data_type 'ohlcv'
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hs3 as hs3
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.db.db_utils as imvcddbut
import im_v2.talos.data.extract.extractor as imvtdexex

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--api_stage",
        action="store",
        required=False,
        default="sandbox",
        type=str,
        help="(Optional) API 'stage' to use ('sandbox' or 'prod'), default: 'sandbox'",
    )
    parser.add_argument(
        "--data_type",
        action="store",
        required=True,
        type=str,
        help="OHLCV, bid/ask or trades data.",
    )
    parser.add_argument("--incremental", action="store_true")
    parser = hparser.add_verbosity_arg(parser)
    parser = imvcdeexut.add_exchange_download_args(parser)
    parser = imvcddbut.add_db_args(parser)
    parser = hs3.add_s3_args(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Initialize the Talos Extractor class.
    exchange = imvtdexex.TalosExtractor(args.api_stage)
    args = vars(args)
    imvcdeexut.download_exchange_data_to_db(args, exchange)


if __name__ == "__main__":
    _main(_parse())
