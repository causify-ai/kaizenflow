#!/usr/bin/env python
"""
Download data from CoinMarketCap and save it as CSV locally.

Use as:
> download_to_jsonfile.py --id 1

id: specific id of the cryptocurrency

"""
import argparse
import json
import logging
import os
from typing import Any

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.save as ssacosav
import sorrentum_sandbox.examples.ml_projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap as coinmarketcap

coinmarketcap_download = coinmarketcap.download

_LOG = logging.getLogger(__name__)


def save_to_json(data) -> None:
    """
    Save RawData storing a DataFrame to JSON file.
    """
    with open("CoinMarketData.json", "w+") as f:
        json.dump(data, f)
        _LOG.info("Saving data to json file 'CoinMarketCap.json'")


# #############################################################################


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--id",
        action="store",
        required=False,
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
    downloader = coinmarketcap_download.CMCRestApiDownloader()
    raw_data = downloader.download(args.id)
    # Save data as CSV.
    save_to_json(raw_data.get_data())


if __name__ == "__main__":
    _main(_parse())
