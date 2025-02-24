"""
Extract part of the ETL and QA pipeline.

Import as:

import Block_download as ssexbido
"""

import logging
import time
from typing import Generator, Tuple

import common_download as ssandown
import pandas as pd
import requests
import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class OhlcvRestApiDownloader(ssandown.DataDownloader):
    """
    Class for downloading OHLCV data using REST API provided by Blockchain.
    """

    def __init__(self, api: str, chart_name: str):
        self.api = api
        self.chart_name = chart_name

    def download(
        self,
        start_timestamp: str,
        time_span: str,
    ) -> ssandown.RawData:
        # Download data once symbol at a time.
        dfs = []
        url = self._build_url(
            api=self.api,
            chart_Name=self.chart_name,
            start_timestamp=start_timestamp,
            time_span=time_span,
            format="json",
        )

        # request data here
        response = requests.request(
            method="GET",
            url=url,
            # headers={"Content-Type": "application/json", "X-CMC_PRO_API_KEY": api_key, "Accepts": "application/json"},
            data={},
        )

        hdbg.dassert_eq(response.status_code, 200)
        data = pd.json_normalize(response.json())
        # Convert data into dataframe
        timestamp = list()
        value = list()
        for i in data["values"].iloc[0]:
            timestamp.append(i["x"])
            value.append(i["y"])
        df = pd.DataFrame(zip(timestamp, value), columns=["Timestamp", "Values"])

        dfs.append(df)
        # Delay for throttling in seconds.
        time.sleep(0.5)
        df = pd.concat(dfs, ignore_index=True)
        _LOG.info(f"Downloaded data: \n\t {df.head()}")
        return ssandown.RawData(df)

    @staticmethod
    def _build_url(
        api: str,
        chart_Name: str,
        start_timestamp: str,
        time_span: str,
        format: str = "json",
    ) -> str:
        """
        Build up URL with the placeholders from the args.
        """
        end_timestamp = start_timestamp + time_span
        return (
            f"{api}/{chart_Name}?timespan={time_span}&"
            + f"start={start_timestamp}&format={format}"
        )
