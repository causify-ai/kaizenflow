#!/usr/bin/env python
"""
Download data from Chainlink and save it as CSV locally.

Use as:

> download_to_csv.py --pair BTC/USD --start_roundid 92233720368547792257 --target_dir 'chainlink_data'
> download_to_csv.py --pair BTC/USD --start_roundid 92233720368547792257 --end_roundid 92233720368547792260 --target_dir 'chainlink_data'

"""
import argparse
import logging
import os
from typing import Any

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as sinsadow
import sorrentum_sandbox.common.save as sinsasav
import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.download as sisebido

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
        hdbg.dassert_isinstance(
            data.get_data(), pd.DataFrame, "Only DataFrame is supported."
        )
        signature = "chainlink_data"
        signature += ".csv"
        hio.create_dir(self.target_dir, incremental=True)
        target_path = os.path.join(self.target_dir, signature)
        data.get_data().to_csv(target_path, index=False)


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--pair",
        action="store",
        required=True,
        type=str,
        help="Currency pair to download",
    )
    parser.add_argument(
        "--start_roundid",
        action="store",
        required=True,
        type=int,
        help="the first data to download",
    )
    parser.add_argument(
        "--end_roundid",
        action="store",
        required=False,
        type=int,
        help="the last data to dowlonad",
    )

    parser.add_argument(
        "--target_dir",
        action="store",
        required=True,
        type=str,
        help="Path to the target directory to store CSV data into",
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

    if args.end_roundid is None:
        raw_data = sisebido.downloader(
            pair=args.pair, start_roundid=args.start_roundid
        )
    else:
        raw_data = sisebido.downloader(
            pair=args.pair,
            start_roundid=args.start_roundid,
            end_roundid=args.end_roundid,
        )

    # Save data as CSV.
    saver = CsvDataFrameSaver(args.target_dir)
    saver.save(raw_data)


if __name__ == "__main__":
    _main(_parse())
