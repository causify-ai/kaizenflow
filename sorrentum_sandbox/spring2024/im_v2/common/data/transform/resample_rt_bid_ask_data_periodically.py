#!/usr/bin/env python
"""
Load raw bid/ask data from specified DB table every minute, resample to 1
minute and insert back in a specified time interval. Currently resamples only
top of the book.

# Usage sample:
> im_v2/common/data/transform/resample_rt_bid_ask_data_periodically.py \
    --db_stage 'test' \
    --src_table 'ccxt_bid_ask_futures_raw_test' \
    --dst_table 'ccxt_bid_ask_futures_resampled_1min_test' \
    --start_ts '2022-10-12 16:05:05+00:00' \
    --end_ts '2022-10-12 18:30:00+00:00' \
    --exchange_id 'binance'
"""
import argparse
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im_v2.common.data.extract.extract_utils as imvcdeexut

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use",
    )
    parser.add_argument(
        "--src_table",
        action="store",
        type=str,
        required=True,
        help="DB table to select raw bid/ask data from",
    )
    parser.add_argument(
        "--dst_table",
        action="store",
        type=str,
        required=True,
        help="DB table to insert resampled data into",
    )
    parser.add_argument(
        "--exchange_id",
        action="store",
        type=str,
        required=True,
        help="Which exchange to fetch data from",
    )
    parser.add_argument(
        "--start_ts",
        required=True,
        action="store",
        type=str,
        help="Beginning of the resample data period",
    )
    parser.add_argument(
        "--end_ts",
        action="store",
        required=True,
        type=str,
        help="End of the resampled data period",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    args = vars(args)
    imvcdeexut.resample_rt_bid_ask_data_periodically(
        args["db_stage"],
        args["src_table"],
        args["dst_table"],
        args["exchange_id"],
        pd.Timestamp(args["start_ts"]),
        pd.Timestamp(args["end_ts"]),
    )


if __name__ == "__main__":
    _main(_parse())
