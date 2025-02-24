#!/usr/bin/env python

"""
Import as:

import im.ib.data.extract.gateway.download_ib_data_single_file_with_loop as imidegdidsfwl
"""

import argparse
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.utils as imidegaut

# from tqdm.notebook import tqdm

_LOG = logging.getLogger(__name__)


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
    elif False:
        df = pd.read_csv("./ib_futures.csv")
        # print(df)
        symbols = df["IB SYMBOL"][:10]
    # Set up.
    symbols = [args.symbol]
    args.exchange
    target = args.asset_class
    frequency = args.frequency
    currency = "USD"
    ib = imidegaut.ib_connect(0, is_notebook=False)
    use_rth = False
    start_ts = None
    end_ts = None
    num_threads = "serial"
    dst_dir = args.dst_dir
    incremental = args.incremental
    client_id_base = 5
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
    file_names = imidegddil.download_ib_data(
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
    parser.add_argument(
        "--symbol", action="store", required=True, help="Symbol ticker"
    )
    parser.add_argument(
        "--exchange",
        action="store",
        required=True,
        help="Symbol trading exchange",
    )
    parser.add_argument(
        "--asset_class",
        action="store",
        required=True,
        help="Asset class of the symbol",
    )
    parser.add_argument(
        "--frequency",
        action="store",
        required=True,
        help="intraday or day or hour",
    )
    parser.add_argument("--incremental", action="store_true", default=True)
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
