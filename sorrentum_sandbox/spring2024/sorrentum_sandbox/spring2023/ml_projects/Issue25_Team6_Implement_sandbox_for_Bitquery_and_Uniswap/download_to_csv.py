#!/usr/bin/env python
"""
Download Uniswap data using GraphQL API and save it as CSV locally.

end_timestamp is an optional flag, without it data will be grabed
from start_timestamp to present

Use as:
> download_to_csv.py \
    --start_timestamp '2022-10-20 10:00:00+00:00' \
    --target_dir 'uniswap_data'

    optional flags:
    --end_timestamp '2022-10-21 15:30:00+00:00' \


"""
import argparse
import logging
import os
from typing import Any

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.save as ssacosav
import sorrentum_sandbox.examples.ml_projects.Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap.download as sisebido

_LOG = logging.getLogger(__name__)


class CsvDataFrameSaver(ssacosav.DataSaver):
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

    def save(self, data: ssacodow.RawData, **kwargs: Any) -> None:
        """
        Save RawData storing a DataFrame to CSV.

        :param data: data to persists into CSV
        """
        hdbg.dassert_isinstance(data.get_data(), pd.DataFrame, "Only DataFrame is supported.")
        signature = ("uniswap")
        signature = "uniswap_table"
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
        help="Beginning of the loaded period, e.g. 2022-02-09 10:00:00+00:00",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=False,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10 10:00:00+00:00",
    )
    parser.add_argument(
        "--target_dir",
        action="store",
        required=True,
        type=str,
        help="Path to the target directory to store CSV data into",
    )

    parser.add_argument(
        "--live_flag",
        action="store_true",
        required=False,
        help="Flag for running in live mode"
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
    # Load data.
    start_timestamp = (args.start_timestamp)
    end_timestamp = (args.end_timestamp)
    live_flag = (args.live_flag)
    raw_data = sisebido.run_bitquery_query(start_timestamp, None, end_timestamp,False)
    # Save data as CSV.
    saver = CsvDataFrameSaver(args.target_dir)
    saver.save(raw_data)

if __name__ == "__main__":
    _main(_parse())
