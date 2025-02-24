#!/usr/bin/env python
"""
Download google trends data and save it as CSV locally.
"""
import argparse
import os
from typing import Any

import common.save as sinsasav
import pandas as pd
from utilities import custom_logger

import src.download as sisebido


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

    def save(self, data: pd.DataFrame, **kwargs: Any) -> None:
        """
        storing a DataFrame to CSV.

        :param data: data to persists into CSV
        **kwargs.topic: name of the topic to name the CSV file accordingly.
        """
        # hdbg.dassert_isinstance(data, pd.DataFrame, "Only DataFrame is supported.")

        for filename in os.listdir(self.target_dir):
            file_path = os.path.join(self.target_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

        topic = kwargs.get("topic")

        signature = topic + ".csv"
        target_path = os.path.join(self.target_dir, signature)
        data.to_csv(target_path, index=False)


# #############################################################################


def _add_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start_timestamp",
        required=False,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. 2022-02-09",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=False,
        type=str,
        help="End of the loaded period, e.g. 2022-02-10",
    )
    parser.add_argument(
        "--target_dir",
        action="store",
        required=True,
        type=str,
        help="Path to the target directory to store CSV data into",
    )
    parser.add_argument(
        "--use_api",
        action="store",
        required=True,
        type=str,
        help="Fetch method, swich between using a pre-build Json or using the API",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_download_args(parser)
    # parser = hparser.add_verbosity_arg(parser)
    return parser


log_path = "/var/lib/app/data/"
_LOG = custom_logger.logger(log_path + "download_to_csv.py.log")


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    start_timestamp = args.start_timestamp
    end_timestamp = args.end_timestamp
    target_dir = args.target_dir
    use_api = True if args.use_api == "True" else False

    raw_data = None

    topic = "ipad"
    topic = topic.lower()
    _LOG.info("\n-------------------------------------------")
    _LOG.info("Topic to fetch: " + topic)

    _LOG.info("Prepping the Downloader")
    downloader = sisebido.OhlcvRestApiDownloader()
    # print("Start: ", start_timestamp)
    # print("End: ", end_timestamp)
    # print("Target: ", target_dir)
    # print("API: ", use_api)

    if use_api:
        _LOG.info("Downloading the data using the Google Trends API...")
    else:
        _LOG.info("Fetching the Json from /root/data/data.json")
    raw_data = downloader.download(
        topic=topic,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        use_api=use_api,
    )

    _LOG.info("Json fetched and converted to DataFrame")

    # Save data as CSV.
    _LOG.info("Creating a Saver...")
    # change this to a volume later
    saver = CsvDataFrameSaver(target_dir)

    _LOG.info("Saving the Dataframe as a CSV..")
    saver.save(raw_data, topic=topic)

    _LOG.info("CSV Saved to" + target_dir + " as " + topic + ".csv")


# #############################################################################
if __name__ == "__main__":
    _main(_parse())
