"""
Extract part of the ETL and QA pipeline.

Import as:

import sorrentum_sandbox.examples.binance.download as ssexbido
"""

import logging
import time
from typing import Generator, Tuple

import pandas as pd
import requests
import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import sorrentum_sandbox.common.download as ssacodow

_LOG = logging.getLogger(__name__)


# #############################################################################
# OhlcvRestApiDownloader
# #############################################################################


class OhlcvRestApiDownloader(ssacodow.DataDownloader):
    """
    Class for downloading OHLCV data using REST API provided by Binance.
    """

    _MAX_LINES = 1000
    _UNIVERSE = {
        "binance": [
            "ETH_USDT",
            "BTC_USDT",
        ]
    }

    def __init__(self, use_binance_dot_com: bool = False) -> None:
        """
        Construct Binance downloader class instance.

        :param use_binance_dot_com: select the domain to use when downloading,
            e.g., "binance.com" or "binance.us"
        """
        self.use_binance_dot_com = use_binance_dot_com

    def download(
        self, start_timestamp: pd.Timestamp, end_timestamp: pd.Timestamp
    ) -> ssacodow.RawData:
        # Convert and check timestamps.
        hdateti.dassert_has_tz(start_timestamp)
        start_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
            start_timestamp
        )
        hdateti.dassert_has_tz(end_timestamp)
        end_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
            end_timestamp
        )
        hdbg.dassert_lt(
            start_timestamp_as_unix,
            end_timestamp_as_unix,
            msg="End timestamp should be greater then start timestamp.",
        )
        # Download data once symbol at a time.
        dfs = []
        for symbol in tqdm.tqdm(self._UNIVERSE["binance"]):
            # Download one chunk of data.
            for start_time, end_time in self._split_period_to_days(
                start_time=start_timestamp_as_unix, end_time=end_timestamp_as_unix
            ):
                url = self._build_url(
                    start_time,
                    end_time,
                    symbol=self._process_symbol(symbol),
                    limit=self._MAX_LINES,
                )
                response = requests.request(
                    method="GET",
                    url=url,
                    headers={"Content-Type": "application/json"},
                    data={},
                )
                hdbg.dassert_eq(response.status_code, 200)
                data = pd.DataFrame(
                    [
                        {
                            "currency_pair": symbol,
                            "open": row[1],
                            "high": row[2],
                            "low": row[3],
                            "close": row[4],
                            "volume": row[5],
                            # close_time from the raw response.
                            # The value is in ms, we add one millisecond, based on
                            # the Sorrentum protocol data interval specification,
                            # where interval [a, b) is labeled with timestamp 'b'.
                            "timestamp": int(row[6]) + 1,
                            "end_download_timestamp": hdateti.get_current_time(
                                "UTC"
                            ),
                        }
                        for row in response.json()
                    ]
                )
                dfs.append(data)
                # Delay for throttling in seconds.
                time.sleep(0.5)
        df = pd.concat(dfs, ignore_index=True)
        # It can happen that the API sends back data after the specified
        #  end_timestamp, so we need to filter out.
        df = df[df["timestamp"] <= end_timestamp_as_unix]
        _LOG.info(f"Downloaded data: \n\t {df.head()}")
        return ssacodow.RawData(df)

    @staticmethod
    def _process_symbol(symbol: str) -> str:
        """
        Transform symbol from universe to Binance format.
        """
        return symbol.replace("_", "")

    def _build_url(
        self,
        start_timestamp_as_unix_epoch: int,
        end_timestamp_as_unix_epoch: int,
        symbol: str,
        *,
        interval: str = "1m",
        limit: int = 500,
    ) -> str:
        """
        Build up URL with the placeholders from the args.
        """
        domain = "binance.com" if self.use_binance_dot_com else "binance.us"
        return (
            f"https://api.{domain}/api/v3/klines"
            f"?startTime={start_timestamp_as_unix_epoch}&endTime={end_timestamp_as_unix_epoch}"
            f"&symbol={symbol}&interval={interval}&limit={limit}"
        )

    def _split_period_to_days(
        self, start_time: int, end_time: int
    ) -> Generator[Tuple[int, int], None, None]:
        """
        Split period into chunks of the days.

        The reason is that Binance API doesn't allow to get more than 1500 rows at
        once. So to get 1 minute interval, we need to split a period into chunks
        that Binance allow us to get.

        :param start_time: timestamp for the start time
        :param end_time: timestamp for the end time
        :return: generator for loop
        """
        step = 1000 * 60 * self._MAX_LINES
        for i in range(start_time, end_time, step):
            yield i, min(i + step, end_time)
