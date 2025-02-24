"""
Import as:

import im_v2.ccxt.data.extract.cryptocom_extractor as imvcdecrex
"""

import logging
import time
from typing import Any, Optional

import pandas as pd
import tqdm

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import im_v2.ccxt.data.extract.extractor as imvcdexex

_LOG = logging.getLogger(__name__)


class CryptocomCcxtExtractor(imvcdexex.CcxtExtractor):
    def __init__(self, exchange_id: str, contract_type: str) -> None:
        _LOG.info("Logging using Cryptocom Extractor")
        hdbg.dassert_eq(exchange_id, "cryptocom")
        super().__init__(exchange_id, contract_type)

    def _download_ohlcv(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        bar_per_iteration: Optional[int] = 300,
        sleep_time_in_secs: float = 0.25,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download minute OHLCV bars.

        :param currency_pair: a currency pair, e.g. "BTC_USDT"
        :param start_timestamp: starting point for data
        :param end_timestamp: end point for data (included)
        :param bar_per_iteration: number of bars per iteration
        :param sleep_time_in_secs: time in seconds between iterations
        :return: OHLCV data from CCXT
        """
        # Assign exchange_id to make it symmetrical to other vendors.
        _ = exchange_id
        currency_pair = self.convert_currency_pair(currency_pair)
        hdbg.dassert(
            self._sync_exchange.has["fetchOHLCV"],
            "Exchange %s doesn't has fetch_ohlcv method",
            self._sync_exchange,
        )
        hdbg.dassert_in(
            currency_pair,
            self.currency_pairs,
            "Currency pair is not present in exchange",
        )
        # Get the latest bars if no timestamp is provided.
        if end_timestamp is None and start_timestamp is None:
            return self._fetch_ohlcv(
                currency_pair, bar_per_iteration=bar_per_iteration
            )
        # Verify that date parameters are of correct format.
        hdbg.dassert_isinstance(
            end_timestamp,
            pd.Timestamp,
        )
        hdbg.dassert_isinstance(
            start_timestamp,
            pd.Timestamp,
        )
        hdbg.dassert_lte(
            start_timestamp,
            end_timestamp,
        )
        # Convert datetime into ms.
        start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
        end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp)
        duration = self._sync_exchange.parse_timeframe("1m") * 1000
        all_bars = []
        # Iterate over the time period.
        # Note: the iteration goes from start date to end date in milliseconds,
        # with the step defined by `bar_per_iteration` parameter.
        # Because of this, the output can go slightly over the end date.
        for t in tqdm.tqdm(
            range(
                start_timestamp,
                end_timestamp + duration,
                duration * bar_per_iteration,
            )
        ):
            bars = self._fetch_ohlcv(
                currency_pair,
                since=start_timestamp,
                end_timestamp=t + (duration * bar_per_iteration),
                bar_per_iteration=bar_per_iteration,
            )
            all_bars.append(bars)
            time.sleep(sleep_time_in_secs)
        all_bars_df = pd.concat(all_bars)
        # Remove bars which are not part of the requested timerange to
        #  avoid confusion of receiving unsolicited data.
        all_bars_df = all_bars_df[
            (all_bars_df["timestamp"] >= start_timestamp)
            & (all_bars_df["timestamp"] <= end_timestamp)
        ]
        # It can happen that the received the data are not ordered by timestamp, which would
        #  make the is_monotonic_increasing check fail.
        all_bars_df = all_bars_df.sort_values("timestamp").reset_index(drop=True)
        hdbg.dassert(all_bars_df.timestamp.is_monotonic_increasing)
        # TODO(gp): Double check if dataframes are properly concatenated.
        return all_bars_df

    def _fetch_ohlcv(
        self,
        currency_pair: str,
        *,
        timeframe: str = "1m",
        since: Optional[int] = None,
        bar_per_iteration: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Wrapper for fetching one minute OHLCV bars.

        :param currency_pair: currency pair, e.g. "BTC_USDT"
        :param timeframe: fetch data for certain timeframe
        :param since: from when is data fetched in milliseconds
        :param bar_per_iteration: number of bars per iteration
        :param end_timestamp: end time till when is data fetched in
            milliseconds
        :return: OHLCV data from CCXT that looks like: ``` timestamp
            open high low close volume
            end_download_timestamp 0 1631145600000 46048.31
            46050.00 46002.02 46005.10 55.12298 2022-02-22
            18:00:06.091652+00:00 1 1631145660000 46008.34 46037.70
            45975.59 46037.70 70.45695 2022-02-22
            18:00:06.091652+00:00 ```
        """
        # Change currency pair to CCXT format.
        currency_pair = currency_pair.replace("_", "/")
        # Fetch the data through CCXT.
        bars = self._sync_exchange.fetch_ohlcv(
            currency_pair,
            timeframe=timeframe,
            params={
                "start_ts": since,
                "end_ts": end_timestamp,
                "count": bar_per_iteration,
            },
        )
        # Package the data.
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        bars = pd.DataFrame(bars, columns=columns)
        bars["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        return bars
    
    def _fetch_trades(
        self,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        sleep_time_in_secs: Optional[float] = 0.25,
        limit: Optional[int] = 1000,
    ) -> pd.DataFrame:
        """
        Fetch trades with the CCXT method.

        :param currency_pair: currency pair, e.g. "BTC_USDT"
        :param start_timestamp: start timestamp of the data to download.
        :param end_timestamp: end timestamp of the data to download.
        :param sleep_time_in_secs: time to sleep between iterations
        :param limit: number of trades per iteration
        :return: trades data from CCXT that looks like:
            ```
                timestamp      symbol      side    price     amount           end_download_timestamp
            0   1631145600000  BTC/USDT    buy     46048.31  0.001  2022-02-22 18:00:06.091652+00:00
            1   1631145600000  BTC/USDT    sell    46050.00  0.001  2022-02-22 18:00:06.091652+00:00
            ```
        """
        # Prepare parameters.
        columns = ["id", "timestamp", "symbol", "side", "price", "amount"]
        start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
        end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp)
        trades = []
        last_data_id: Optional[int] = None
        since: Optional[int] = None
        # Fetch the data through CCXT.
        while True:
            if last_data_id is None:
                # Start from beginning, get the data from the start timestamp.
                params = {"start_ts":start_timestamp, "end_ts":end_timestamp, "count":limit}
                data = self._sync_exchange.fetch_trades(
                    currency_pair,
                    params=params
                )
            else:
                data = self._sync_exchange.fetch_trades(
                    currency_pair, since=since, limit=limit
                )
            since = int(data[-1]["timestamp"]) + 1
            df = pd.DataFrame(data, columns=columns)
            trades.append(df)
            # Stop if there is no data.
            if df.empty:
                break
            # Stop if dataset has reached the end of the time range.
            if (df.timestamp > end_timestamp).any():
                break
            # Update the fromId parameter as next iteration's starting point.
            last_data_id = int(df["id"].iloc[-1]) + 1
            # Take a nap in order to avoid hitting the rate limit.
            time.sleep(sleep_time_in_secs)
        trades_df = pd.concat(trades).reset_index(drop=True).drop(columns=["id"])
        trades_df["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        # Cut the data if it exceeds the end timestamp.
        trades_df = trades_df[trades_df["timestamp"] < end_timestamp]
        return trades_df
