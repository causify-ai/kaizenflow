#!/usr/bin/env python
"""
Extract part of the ETL and QA pipeline.

Import as:

import sorrentum_sandbox.examples.ml_projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap as coinmarketcap
coinmarketcap_download = coinmarketcap.download
"""

import logging
import os
import time
from typing import Generator, Tuple

import pandas as pd
import requests
import tqdm
from dotenv import load_dotenv

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import sorrentum_sandbox.common.download as ssacodow

_LOG = logging.getLogger(__name__)
# Load the environment variables from the ../../../devops/.env file
load_dotenv(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "devops", ".env")
)

COINMARKETCAP_API_KEY = os.environ["COINMARKETCAP_API_KEY"]
_MAX_LINES = 5000

# #############################################################################
# CoinMarketCap(CMC) Api Downloader
# #############################################################################


class CMCRestApiDownloader(ssacodow.DataDownloader):
    """
    Class for downloading data using REST API provided by CoinMarketCap.
    """

    def __init__(self) -> None:
        self.api_key = os.environ["COINMARKETCAP_API_KEY"]

    def get_data(self, id):
        url = self._build_url(self, id)
        _LOG.info("Request url: {}".format(url))
        # Request error and exception handling
        try:
            _LOG.info("Requesting data...")
            response = requests.request(
                method="GET",
                url=url,
                headers={
                    "Content-Type": "application/json",
                    "X-CMC_PRO_API_KEY": self.api_key,
                    "Accepts": "application/json",
                },
                data={},
            )

            if response.status_code == 200:
                _LOG.info("Request successful!")
                # return data
                # Convert all int to str to avoid OverflowError: MongoDB can only handle up to 8-byte ints
                return response.json(parse_int=str)["data"]
            else:
                _LOG.info(
                    "Request failed, status code:{}".format(
                        response.json()["status"]["error_code"]
                    )
                )
        except Exception as e:
            _LOG.info(f"Request exception:{e}")

    def download(self, id) -> ssacodow.RawData:
        # request data
        cmc_data = self.get_data(id)
        _LOG.info(f"Downloaded data")
        _LOG.info(f"Show the First Data: {cmc_data}")
        return ssacodow.RawData(cmc_data)

    @staticmethod
    def _build_url(
        self,
        id: int = 1,
        convert: str = "USD",
    ) -> str:
        """
        Build up URL with the placeholders from the args.
        """
        return (
            f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?"
            f"id={id}&convert={convert}"
        )
