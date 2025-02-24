"""
Extract part of the ETL and QA pipeline.

Import as:
import src.download as ssexbido
"""

import json
import logging
import os
import subprocess
from typing import Any

import common.download as ssandown
import pandas as pd
from dotenv import load_dotenv
from serpapi import GoogleSearch

_LOG = logging.getLogger(__name__)


# #############################################################################
# OhlcvRestApiDownloader
# #############################################################################


class OhlcvRestApiDownloader(ssandown.DataDownloader):
    """
    Class for downloading google trends data using REST API provided by SerpAPI.
    """

    def __init__(self) -> None:
        """
        Construct google ternds downloader class instance.
        """

    def download(self, start_timestamp: str, end_timestamp: str, **kwargs) -> Any:
        topic = kwargs.get("topic")
        use_api = kwargs.get("use_api")
        real_time_data = kwargs.get("real_time_data")

        file_to_use = None

        if use_api:
            load_dotenv("/cmamp/airflow/.env")

            timeframe = None

            if real_time_data:
                timeframe = "now 1-H"

            else:
                timeframe = "all"
                if start_timestamp is not None and end_timestamp is not None:
                    timeframe = start_timestamp + " " + end_timestamp
            params = {
                "engine": "google_trends",
                "q": topic,
                "data_type": "TIMESERIES",
                "date": timeframe,
                "api_key": os.environ.get("API_KEY"),
            }

            # performing a query
            search = GoogleSearch(params)
            results = search.get_dict()
            file_to_use = results["interest_over_time"]

        else:
            with open("/cmamp/files/data.json", "r") as file:
                file_to_use = json.load(file)

        # formatting the data
        columns = ["Topic", "Time", "Frequency"]
        cleaned_data = []
        raw_data = file_to_use["timeline_data"]

        for record in raw_data:
            cleaned_data.append(
                [
                    record["values"][0]["query"],
                    record["date"].replace("\u2009", " "),
                    record["values"][0]["extracted_value"],
                ]
            )

        # constructing a dataframe out of the data
        df = pd.DataFrame(cleaned_data, columns=columns)

        return df
