#!/usr/bin/env python
"""
Download data from CoinMarketCap and save it as CSV locally.

Use as:
> download_to_jsonfile.py --start 1 --limit 100

"""
import json
import argparse
import logging
import os
from typing import Any

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hio as hio
import sorrentum_sandbox.common.download as sinsadow
import sorrentum_sandbox.projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap.download as sisebido
import sorrentum_sandbox.common.save as sinsasav

_LOG = logging.getLogger(__name__)




def save_to_json(data) -> None:
    """
    Save RawData storing a DataFrame to JSON file.
    """
    with open('CoinMarketData.json', 'w+') as f:
        json.dump(data, f)

# #############################################################################

def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start",
        action="store",
        required=True,
        type=int,
        help="Path to the target directory to store CSV data into",
    )
    parser.add_argument(
        "--limit",
        action="store",
        required=True,
        type=int,
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
    downloader = sisebido.CMCRestApiDownloader()
    raw_data = downloader.download(args.start,args.limit)
    # Save data as CSV.
    save_to_json(raw_data.get_data())


if __name__ == "__main__":
    _main(_parse())
