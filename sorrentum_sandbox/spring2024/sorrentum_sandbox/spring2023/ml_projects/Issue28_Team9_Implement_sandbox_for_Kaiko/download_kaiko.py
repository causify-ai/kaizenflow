import logging
import time
from typing import Generator, Tuple

import common.download as ssandown
import kaiko as ka
import pandas as pd
import requests

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class KaikoDownloader(ssandown.DataDownloader):
    """
    Class for downloading kaiko Data using kaiko python library
    """


    _EXCHANGE = "cbse"
    _UNIVERSE = {
        "kaiko": [
            "eth-usd",
            "btc-usd",
        ]
    }
    # Setting a client with API key
    _API_KEY = "1d16b71fdfa506550a8a9cc5faa36fa4"
    _KC = ka.KaikoClient(api_key=_API_KEY)

    def download(
        self, start_timestamp: str, end_timestamp: str
    ) -> ssandown.RawData:
        dfs = []
        for symbol in self._UNIVERSE["kaiko"]:

            data = ka.TickTrades(
                exchange=self._EXCHANGE,
                instrument=symbol,
                start_time=start_timestamp,
                end_time=end_timestamp,
                client=self._KC,
            ).df

            data = data.reset_index()
            data["currency_pair"] = symbol

            dfs.append(data)
            # Delay for throttling in seconds.
            time.sleep(0.5)
        df = pd.concat(dfs, ignore_index=True)
        df.columns=[x.replace(' ','_').lower() for x in list(df.columns)]
        _LOG.info(f"Downloaded data: \n\t {df.head()}")
        return ssandown.RawData(df)


print("download_kaiko.py Done")
