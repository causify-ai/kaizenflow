#!/usr/bin/env python
"""
Example implementation of abstract classes for ETL and QA pipeline.

Download OHLCV data from Binance and save it as CSV locally.

Use as:
# Download OHLCV data for binance:
> download_to_csv.py \
    --start_timestamp '2022-10-20 10:00:00+00:00' \
    --end_timestamp '2022-10-21 15:30:00+00:00' \
    --target_dir '.'
"""
import argparse
import logging
import os
import time
from typing import Any, Generator, Tuple

import pandas as pd
import requests
import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import surrentum_infra_sandbox.download as sinsadow
import surrentum_infra_sandbox.save as sinsasav
import surrentum_infra_sandbox.examples.binance.download as sisebido

_LOG = logging.getLogger(__name__)


class CSVDataFrameSaver(sinsasav.DataSaver):
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

        :param data: data to persists into CSV.
        """
        if not isinstance(data.get_data(), pd.DataFrame):
            raise ValueError("Only DataFrame is supported.")
        # TODO(Juraj): rewrite using dataset_schema_utils.
        signature = (
            "bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0"
        )
        signature += ".csv"
        target_path = os.path.join(self.target_dir, signature)
        data.get_data().to_csv(target_path, index=False)
        
        
# ################################################################################


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # Convert timestamps.
    start_timestamp = pd.Timestamp(args.start_timestamp)
    end_timestamp = pd.Timestamp(args.end_timestamp)
    downloader = sisebido.OhlcvBinanceRestApiDownloader()
    raw_data = downloader.download(start_timestamp, end_timestamp)
    saver = CSVDataFrameSaver(args.target_dir)
    saver.save(raw_data)


def add_download_args(
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
        help="Beginning of the loaded period, e.g. 2022-02-09 10:00:00+00:00",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=True,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--target_dir",
        action="store",
        required=True,
        type=str,
        help="Absolute path to the target directory to store data to",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = add_download_args(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
