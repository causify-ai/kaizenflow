import logging
import time
from typing import Any, Optional
import pandas as pd
import requests
from pycoingecko import CoinGeckoAPI

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import sorrentum_sandbox.common.download as ssandown
import pendulum

_LOG = logging.getLogger(__name__)
###ok
class CGDownloader(ssandown.DataDownloader):
    """
    Class for downloading Coingecko Data for ETH and BTC
    """

    # def __init__(self, api: str):
    #     self.api = api
    def __init__(self):
        self = self

    def download(
        self, id: str, from_timestamp: str, to_timestamp: str, *args: Any, **kwargs: Any
    ) -> ssandown.RawData:

        # for symbol in self._UNIVERSE["coingecko"]:
        # cg = self.api
        cg = CoinGeckoAPI()
        # start_time = pendulum.parse(from_timestamp).int_timestamp
        # end_time = pendulum.parse(to_timestamp).int_timestamp
        data = cg.get_coin_market_chart_range_by_id(
        id= id,
        vs_currency= 'usd',
        from_timestamp = from_timestamp,
        to_timestamp= to_timestamp)

        price = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        mc = pd.DataFrame(data['market_caps'], columns=['timestamp', 'market_cap'])
        vol = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'total_volume'])
        price.set_index('timestamp', inplace=True)
        mc.set_index('timestamp', inplace=True)
        vol.set_index('timestamp', inplace=True)
        df = pd.concat([price, mc, vol], axis=1)
        df['id'] = id
        df.reset_index(inplace=True)
        print(df.columns)

        _LOG.info(f"Downloaded data: \n\t {df.head()}")
        return ssandown.RawData(df)
