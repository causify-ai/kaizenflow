#!/usr/bin/env python

import argparse
import logging
import os
from typing import Any

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hio as hio
import common.download as sinsadow
import Issue29_Team10_Implement_sandbox_for_coingecko.download_coingecko as sisebido
import common.save as sinsasav


_LOG = logging.getLogger(__name__)


class CsvDataFrameSaver(sinsasav.DataSaver):
    """
    Class for saving pandas DataFrame as CSV to a local filesystem at desired
    location.
    """

    def __init__(self, target_dir: str) -> None:
        """
        Constructor.

        :param target_dir: path to save data to.
        """
        self.target_dir = target_dir

    def save(self, data: sinsadow.RawData, **kwargs: Any) -> None:
        """
        Save RawData storing a DataFrame to CSV.

        :param data: data to persists into CSV
        """
        hdbg.dassert_isinstance(data.get_data(), pd.DataFrame, "Only DataFrame is supported.")
        signature = (
            "bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0"
        )
        signature += ".csv"
        hio.create_dir(self.target_dir, incremental=True)
        target_path = os.path.join(self.target_dir, signature)
        data.get_data().to_csv(target_path, index=False)


# #############################################################################


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for download.
    """
    parser.add_argument(
        "--from_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, in UNIX",
    )
    parser.add_argument(
        "--to_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the loaded period, in UNIX",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Name of the db table to save data into",
    )
    parser.add_argument(
        "--id",
        action="store",
        required=True,
        type=str,
        help="Name of coin to load"
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_download_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(
        verbosity=args.log_level,
        use_exec_path=True,
        # report_memory_usage=True
    )
    # Download data.
    from_timestamp = str(args.from_timestamp)
    to_timestamp = str(args.to_timestamp)
    id = str(args.id)
    downloader = sisebido.CGDownloader()
    raw_data = downloader.download(id, from_timestamp, to_timestamp)
    # Save data as CSV.
    saver = CsvDataFrameSaver(args.target_table)
    saver.save(raw_data)


if __name__ == "__main__":
    _main(_parse())
