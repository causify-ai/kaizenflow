#!/usr/bin/env python
"""
Download OHLCV data from BlockChain and save it as CSV locally.
Use as:
> download_to_db.py \
    --start_timestamp '2016-01-01 ' \
    --time_span '6years' \
    --target_dir 'Data'\
    --api 'https://api.blockchain.info/charts'\
    --chart_name 'market-price'
"""
import argparse
import logging
import os
from typing import Any

import Block_download as sisebido
import common_download as sinsadow
import common_save as sinsasav
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


class CsvDataFrameSaver(sinsasav.DataSaver):
    """
    Class for saving pandas DataFrame as CSV to a local filesystem at desired
    location.
    """

    def __init__(self, target_dir: str, chart_name: str) -> None:
        """
        Constructor.
        :param target_dir: path to save data to.
        """
        self.target_dir = target_dir
        self.chart_name = chart_name

    def save(self, data: sinsadow.RawData, **kwargs: Any) -> None:
        """
        Save RawData storing a DataFrame to CSV.
        :param data: data to persists into CSV
        """
        hdbg.dassert_isinstance(
            data.get_data(), pd.DataFrame, "Only DataFrame is supported."
        )
        timestamp_str = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
        signature = f"{self.chart_name}.{timestamp_str}"
        signature += ".csv"
        hio.create_dir(self.target_dir, incremental=True)
        target_path = os.path.join(self.target_dir, signature)
        data.get_data().to_csv(target_path, index=False)


# #############################################################################


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. 2016-01-01 ",
    )
    parser.add_argument(
        "--time_span",
        action="store",
        required=True,
        type=str,
        help="Time span from the start time, e.g. 6year",
    )
    parser.add_argument(
        "--target_dir",
        action="store",
        required=True,
        type=str,
        help="Path to the target directory to store data",
    )

    parser.add_argument(
        "--api",
        action="store",
        default="https://api.blockchain.info/charts",
        type=str,
        help="Base URL for the API",
    )

    parser.add_argument(
        "--chart_name",
        action="store",
        default="market-price",
        required=True,
        type=str,
        help="Name of the chart to download",
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

    downloader = sisebido.OhlcvRestApiDownloader(
        api=args.api, chart_name=args.chart_name
    )
    raw_data = downloader.download(args.start_timestamp, args.time_span)

    # Save data as CSV.
    saver = CsvDataFrameSaver(args.target_dir, args.chart_name)
    saver.save(raw_data)


if __name__ == "__main__":
    _main(_parse())
