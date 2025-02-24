#!/usr/bin/env python

"""
Import as:

import im.ib.data.extract.gateway.download_realtime_data as imidegdrda
"""

import argparse
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im.ib.data.extract.gateway.utils as imidegaut

# from tqdm.notebook import tqdm

_LOG = logging.getLogger(__name__)


def on_bar_update(bars, has_new_bar):
    print(has_new_bar)
    print(bars)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.shutup_chatty_modules()
    #
    if False:
        target = "forex"
        frequency = "intraday"
        symbols = ["EURUSD"]
    elif False:
        target = "futures"
        frequency = "intraday"
        symbols = ["ES"]
    elif True:
        target = "continuous_futures"
        frequency = "intraday"
        symbols = ["ES"]
    currency = "USD"
    symbols = "ES CL NG".split()
    try:
        ib = imidegaut.ib_connect(0, is_notebook=False)
        bars = ib.reqRealTimeBars(contract, 5, "MIDPOINT", False)
        bars.updateEvent += onBarUpdate
    finally:
        ib.disconnect()
    use_rth = False
    start_ts = None
    # start_ts = pd.Timestamp("2020-12-13 18:00:00-05:00")
    end_ts = None
    # end_ts = pd.Timestamp("2020-12-23 18:00:00-05:00")
    tasks = imidegaut.get_tasks(
        ib=ib,
        target=target,
        frequency=frequency,
        currency=currency,
        symbols=symbols,
        start_ts=start_ts,
        end_ts=end_ts,
        use_rth=use_rth,
    )
    num_threads = 3
    num_threads = "serial"
    dst_dir = args.dst_dir
    incremental = not args.not_incremental
    client_id_base = 5
    file_names = imidegaut.download_ib_data(
        client_id_base, tasks, incremental, dst_dir, num_threads
    )
    _LOG.info("file_names=%s", file_names)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("positional", nargs="*", help="...")
    parser.add_argument(
        "--dst_dir",
        action="store",
        default="./tmp.download_data",
        help="Destination dir",
    )
    parser.add_argument("--not_incremental", action="store_true", default=False)
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    user_start_ts = pd.Timestamp("2018-02-01")
    user_end_ts = pd.Timestamp("2019-06-01")
    _main(_parse())
