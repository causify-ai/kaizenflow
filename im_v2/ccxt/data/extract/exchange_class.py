"""
Import as:

import im_v2.ccxt.data.extract.exchange_class as imvcdeexcl
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

import ccxt
import pandas as pd
import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio

_LOG = logging.getLogger(__name__)

API_KEYS_PATH = "/data/shared/data/API_keys.json"


class CcxtExchange:
    """
    A class for accessing CCXT exchange data.

    This class implements an access layer that:
    - logs into an exchange using the proper credentials
    - retrieves data in multiple chunks to avoid throttling
    """

    def __init__(
        self, exchange_id: str, api_keys_path: Optional[str] = None
    ) -> None:
        """
        Constructor.

        :param: exchange_id: CCXT exchange id (e.g., `binance`)
        :param: api_keys_path: path to JSON file with API credentials
        """
        self.exchange_id = exchange_id
        self.api_keys_path = api_keys_path or API_KEYS_PATH
        self._exchange = self.log_into_exchange()
        self.currency_pairs = self.get_exchange_currencies()

    def load_api_credentials(self) -> Dict[str, Dict[str, Union[str, bool]]]:
        """
        Load JSON file with available CCXT credentials for all exchanges.

        :return: JSON file with API credentials
        """
        hdbg.dassert_file_extension(self.api_keys_path, "json")
        all_credentials = hio.from_json(self.api_keys_path)
        return all_credentials

    def log_into_exchange(self) -> ccxt.Exchange:
        """
        Log into an exchange via CCXT and return the corresponding `ccxt.Exchange`
        object.
        """
        # Load all the exchange credentials.
        all_credentials = self.load_api_credentials()
        hdbg.dassert_in(
            self.exchange_id,
            all_credentials,
            msg="Exchange ID `%s` is incorrect." % self.exchange_id,
        )
        # Select credentials for provided exchange.
        credentials = all_credentials[self.exchange_id]
        # Enable rate limit.
        credentials["rateLimit"] = True
        exchange_class = getattr(ccxt, self.exchange_id)
        # Create a CCXT Exchange class object.
        exchange = exchange_class(credentials)
        hdbg.dassert(
            exchange.checkRequiredCredentials(),
            msg="Required credentials not passed",
        )
        return exchange

    # TODO(gp): @danya -> get_exchange_currency_pairs
    def get_exchange_currencies(self) -> List[str]:
        """
        Get all the currency pairs available for the exchange.
        """
        return list(self._exchange.load_markets().keys())

    def download_ohlcv_data(
        self,
        # TODO(gp): @danya -> currency_pair
        curr_symbol: str,
        start_datetime: Optional[pd.Timestamp] = None,
        end_datetime: Optional[pd.Timestamp] = None,
        # TODO(gp): @danya -> bar_per_iteration
        step: Optional[int] = 500,
        # TODO(gp): @danya -> sleep_time_in_secs
        sleep_time: int = 1,
    ) -> pd.DataFrame:
        """
        Download minute OHLCV bars.

        :param curr_symbol: a currency pair, e.g. "BTC_USDT"
        :param start_datetime: starting point for data
        :param end_datetime: end point for data (included)
        :param step: number of bars per iteration
        :param sleep_time: time in seconds between iterations
        :return: OHLCV data from CCXT
        """
        hdbg.dassert(
            self._exchange.has["fetchOHLCV"],
            "Exchange %s doesn't has fetch_ohlcv method",
            self._exchange,
        )
        hdbg.dassert_in(
            curr_symbol,
            self.currency_pairs,
            "Currency pair is not present in exchange",
        )
        # Get latest bars if no datetime is provided.
        if end_datetime is None and start_datetime is None:
            return self._fetch_ohlcv(curr_symbol, step=step)
        # Verify that date parameters are of correct format.
        hdbg.dassert_isinstance(
            end_datetime,
            pd.Timestamp,
        )
        hdbg.dassert_isinstance(
            start_datetime,
            pd.Timestamp,
        )
        hdbg.dassert_lte(
            start_datetime,
            end_datetime,
        )
        # Convert datetime into ms.
        start_datetime = start_datetime.asm8.astype(int) // 1000000
        end_datetime = end_datetime.asm8.astype(int) // 1000000
        duration = self._exchange.parse_timeframe("1m") * 1000
        all_bars = []
        # Iterate over the time period.
        # Note: the iteration goes from start date to end date in milliseconds,
        # with the step defined by `step` parameter. Because of this, the output
        # can go slightly over the end date.
        for t in tqdm.tqdm(
            range(start_datetime, end_datetime + duration, duration * step)
        ):
            bars = self._fetch_ohlcv(curr_symbol, since=t, step=step)
            all_bars.append(bars)
            time.sleep(sleep_time)
        # TODO(gp): Double check if dataframes are properly concatenated.
        return pd.concat(all_bars)

    # TODO(gp): @Danya curr_pair -> currency_pair
    def download_order_book(self, curr_pair: str) -> Dict[str, Any]:
        """
        Download order book for a currency pair.

        :param curr_pair: a currency pair, e.g. 'BTC_USDT'
        :return: order book status. output is a nested dictionary with order book
        at the moment of request. E.g.,
            ```
            {
                'symbol': 'BTC/USDT',
                'bids': [[62715.84, 0.002], [62714.0, 0.002], [62712.55, 0.0094]],
                'asks': [[62715.85, 0.002], [62717.25, 0.1674]],
                'timestamp': 1635248738159,
                'datetime': '2021-10-26T11:45:38.159Z',
                'nonce': None
            }
            ```
        """
        # Change currency pair to CCXT format.
        curr_pair = curr_pair.replace("_", "/")
        hdbg.dassert(
            self._exchange.has["fetchOrderBook"],
            "Exchange %s doesn't have fetchOrderBook",
            self._exchange,
        )
        hdbg.dassert_in(curr_pair, self.currency_pairs)
        # Download current order book.
        # TODO(Grisha): use `_` instead of `/` as currencies separator in `symbol`.
        order_book = self._exchange.fetch_order_book(curr_pair)
        return order_book

    def _fetch_ohlcv(
        self,
        currency_pair: str,
        timeframe: str = "1m",
        since: int = None,
        step: int = None,
    ) -> pd.DataFrame:
        """
        Wrapper for fetching one minute OHLCV bars.

        :param currency_pair: currency pair, e.g. "BTC_USDT"
        :param timeframe: fetch data for certain timeframe
        :param since: from when is data fetched in milliseconds
        :param step: number of bars per iteration

        :return: OHLCV data from CCXT that looks like:
            TODO(gp): @danya Add snippet of data
            ```
            ...
            ```
        """
        # Change currency pair to CCXT format.
        currency_pair = currency_pair.replace("_", "/")
        # Fetch the data through CCX.
        bars = self._exchange.fetch_ohlcv(
            currency_pair, timeframe=timeframe, since=since, limit=step
        )
        # Package the data.
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        bars = pd.DataFrame(bars, columns=columns)
        bars["created_at"] = str(hdateti.get_current_time("UTC"))
        return bars
