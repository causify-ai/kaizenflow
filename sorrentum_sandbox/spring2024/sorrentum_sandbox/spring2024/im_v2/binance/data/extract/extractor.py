"""
Binance native data extractor.

This module provides functionalities to extract data from Binance,
including historical data download from Binance public data repository
available at https://github.com/binance/binance-public-data/.

Real-time data capabilities of this class include WebSocket data download
for OHLCV, bid/ask, and trade data. The real-time data extraction
functionality is sourced from the Binance Futures Connector Python library,
accessible at https://github.com/binance/binance-futures-connector-python/.

Import as:

import im_v2.binance.data.extract.extractor as imvbdexex
"""
import asyncio
import copy
import enum
import glob
import json
import logging
import os
import time
import urllib.request as urlreq
import uuid
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import aiohttp
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import im_v2.binance.websocket.websocket_client as imvbwwecl
import im_v2.common.data.extract.extractor as ivcdexex

_LOG = logging.getLogger(__name__)
BASE_URL = "https://data.binance.vision/"
CHUNK_SIZE = 20000
TRADES_COLUMNS = {
    "futures": ["id", "price", "qty", "quote_qty", "time", "is_buyer_maker"],
    "spot": [
        "id",
        "price",
        "qty",
        "quote_qty",
        "time",
        "is_buyer_maker",
        "is_best_match",
    ],
}


class BinanceNativeTimePeriod(enum.Enum):
    """
    Binance native data time period.
    """

    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BinanceExtractor(ivcdexex.Extractor):
    """
    Extracts data from the Binance native data API.
    """

    def __init__(
        self,
        contract_type: str,
        time_period: BinanceNativeTimePeriod,
        data_type: str,
        *,
        allow_data_gaps: Optional[bool] = False,
        max_attempts: int = 0,
    ) -> None:
        """
        Construct Binance native data extractor.

        :param contract_type: spot or futures contracts to extract
        :param time_period: time period of the data to extract
            By the nature of Binance data, we can extract data only for a:
            - daily
            - monthly
            - yearly
            time period.
            The choice of the time period is depends on the data we want to
            extract. For example, if we want to extract data for a few days,
            then we should choose daily time period. If we want to extract
            data for a few months, then we should choose monthly time period.
        :param allow_data_gaps: whether to allow data gaps
            Example: if we have data for 2020-01-01 and 2020-01-03, but not for
            2020-01-02, then we have a data gap.
            So, if allow_data_gaps is True, we will just log a warning and
            continue. If allow_data_gaps is False, we will raise an exception.
        """
        self.base_dir = "./tmp/binance"
        self.allow_data_gaps = allow_data_gaps
        hdbg.dassert_in(
            contract_type,
            ["futures", "spot"],
            msg="Supported contract types: futures, spot",
        )
        self.contract_type = contract_type
        self.vendor = "Binance"
        self.time_period = time_period
        self._ohlcv = {}
        self._trades = {}
        self._websocket_data_buffer = {}
        # Store the list of currency pairs which got subscribed, in case of disconnect
        # we would like to subscribe again.
        self.currency_pairs = []
        self.bid_ask_depth = None
        self.data_type = data_type
        if data_type == "bid_ask":
            message_handler = self._handle_orderbook_message
        elif data_type == "trades":
            message_handler = self._handle_trades_message
        elif data_type == "ohlcv":
            message_handler = self._handle_ohlcv_message
        else:
            raise NotImplementedError
        self._client = imvbwwecl.UMFuturesWebsocketClient(
            on_message=message_handler,
            on_error=self._handle_error,
            on_disconnect=self._handle_disconnect,
            # max attempts for retry on failed subscription
            max_attempts=max_attempts,
        )
        super().__init__()

    def __del__(self) -> None:
        """
        Destructor of the Binance Extractor.
        """
        # Remove the temporary directory.
        if hasattr(self, "tmp_dir_path") and os.path.exists(self.tmp_dir_path):
            hio.delete_dir(self.tmp_dir_path)

    def convert_currency_pair(self, currency_pair: str) -> str:
        """
        Convert currency pair to Binance native format.

        :param currency_pair: currency pair to convert, e.g. `BTC_USDT`
        :return: converted currency pair, e.g. `BTCUSDT`
        """
        return currency_pair.replace("_", "")

    async def sleep(self, time: int):
        """
        :param time: sleep time in milliseconds
        """
        await asyncio.sleep(time / 1000)

    def close(self):
        """
        Close the connection of exchange.
        """
        self._client.stop()

    def _handle_disconnect(self, _) -> None:
        _LOG.warning("Websocket connection closed, subscribing again.")
        exchange_id = "Binance"
        if self.data_type == "bid_ask":
            coroutine = self._subscribe_to_websocket_bid_ask_multiple_symbols(
                exchange_id, self.currency_pairs, bid_ask_depth=self.bid_ask_depth
            )
        elif self.data_type == "ohlcv":
            coroutine = self._subscribe_to_websocket_ohlcv_multiple_symbols(
                exchange_id, self.currency_pairs
            )
        elif self.data_type == "trades":
            coroutine = self._subscribe_to_websocket_trades_multiple_symbols(
                exchange_id, self.currency_pairs
            )
        else:
            raise NotImplementedError
        asyncio.run(coroutine)

    def _handle_error(self, _, exception) -> None:
        raise exception

    def _handle_orderbook_message(self, _, message: str) -> None:
        """
        Handle single orderbook message.
        """
        message = json.loads(message)
        # Convert back to our default format:
        if "s" in message:
            info = {}
            symbol = message["s"]
            info["timestamp"] = message["T"]
            info["bids"] = message["b"]
            info["asks"] = message["a"]
            info["symbol"] = symbol
            self._websocket_data_buffer[symbol].append(info)
        else:
            # TODO(Sonaal): Find out a neat way to handle errors.
            self._websocket_data_buffer["error"] = message

    def _handle_ohlcv_message(self, _, message):
        """
        Handle single ohlcv message.
        """
        info = json.loads(message)
        if "s" in info:
            ohlcv_data = info["k"]
            currency_pair = info["s"]
            self._ohlcv[currency_pair][ohlcv_data["t"]] = [
                ohlcv_data["t"],
                ohlcv_data["o"],
                ohlcv_data["h"],
                ohlcv_data["l"],
                ohlcv_data["c"],
                ohlcv_data["v"],
            ]
        else:
            self._ohlcv["error"] = message

    def _handle_trades_message(self, _, message):
        """
        Handle single trades message.
        """
        info = json.loads(message)
        if "s" in info:
            currency_pair = info["s"]
            id = info["t"]
            side = "sell" if info["m"] is False else "buy"
            if info["X"] == "MARKET":
                self._trades[currency_pair].append(
                    {
                        "id": id,
                        "timestamp": info["T"],
                        "side": side,
                        "price": info["p"],
                        "amount": info["q"],
                    }
                )
        else:
            self._trades["error"] = message

    def _make_tmp_dir(self) -> str:
        """
        Make temporary directory.

        :return: path to temporary directory
        """
        dir_id = uuid.uuid4()
        self.tmp_dir_path = os.path.join(self.base_dir, str(dir_id))
        hio.create_dir(self.tmp_dir_path, incremental=False)
        return self.tmp_dir_path

    async def _download_single_binance_file(
        self,
        session: aiohttp.ClientSession,
        file_url: str,
        file_name: str,
        dst_path: Optional[str] = None,
    ) -> bool:
        """
        Download a single file from Binance asynchronously.

        :param session: aiohttp ClientSession
        :param file_url: url of the file to download
        :param file_name: name of the file to download
        :param dst_path: path to save the file to
        :return: True if the file was downloaded, False otherwise
        """
        if dst_path is None:
            dst_path = self.tmp_dir_path
        save_path = os.path.join(dst_path, file_name)
        if os.path.exists(save_path):
            raise FileExistsError(save_path)
        try:
            download_url = f"{BASE_URL}{file_url}{file_name}"
            async with session.get(download_url) as response:
                response.raise_for_status()
                length = int(response.headers.get("content-length"))
                blocksize = max(4096, length // 100)
                with open(save_path, "wb") as out_file:
                    dl_progress = 0
                    async for chunk in response.content.iter_chunked(blocksize):
                        if not chunk:
                            break
                        dl_progress += len(chunk)
                        out_file.write(chunk)
                        done = int(50 * dl_progress / length)
                        print(f"\r[{'#' * done}{'.' * (50 - done)}]", end="")
        except aiohttp.ClientResponseError as e:
            if self.allow_data_gaps:
                _LOG.warning("File not found: %s", download_url)
                return False
            else:
                raise FileNotFoundError(download_url)
        return True

    def _get_binance_file_path(
        self,
        trading_type: str,
        market_data_type: str,
        time_period: str,
        symbol: str,
        interval: Optional[str] = None,
    ) -> str:
        """
        Get the path to the file on Binance.

        :param trading_type: spot or futures
        :param market_data_type: trades or klines
        :param time_period: daily, monthly or yearly
        :param symbol: currency pair
        :param interval: time interval. Example: 1m, 1h, 1d
        :return: path to the data on Binance
            Example: data/futures/daily/trades/BTCUSDT/
        """
        trading_type_path = "data/spot"
        if trading_type != "spot":
            trading_type_path = f"data/futures/{trading_type}"
        if interval is not None:
            path = (
                f"{trading_type_path}/"
                f"{time_period}/"
                f"{market_data_type}/"
                f"{symbol.upper()}/"
                f"{interval}/"
            )
        else:
            path = (
                f"{trading_type_path}/"
                f"{time_period}/"
                f"{market_data_type}/"
                f"{symbol.upper()}/"
            )
        return path

    def _get_file_name_by_period(
        self,
        time_period: BinanceNativeTimePeriod,
        currency_pair: str,
        period: pd.Timestamp,
    ) -> str:
        """
        Get the file name based on the time period.

        :param time_period: time period
        :param currency_pair: currency pair to download
        :param period: current period
        :return: file name
        """
        if time_period == BinanceNativeTimePeriod.DAILY:
            file_name = (
                f"{currency_pair.upper()}-trades"
                f"-{period.strftime('%Y-%m-%d')}.zip"
            )
        elif time_period == BinanceNativeTimePeriod.MONTHLY:
            file_name = (
                f"{currency_pair.upper()}-trades"
                f"-{period.year}"
                f"-{period.month:02d}.zip"
            )
        else:
            raise ValueError(f"Unsupported time period: {self.time_period}")
        return file_name

    async def _download_binance_files(
        self,
        currency_pair: str,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
        dst_path: str,
        *,
        batch_size: int = 10,
    ) -> None:
        """
        Download files from Binance asynchronously.

        :param currency_pair: currency pair to download
        :param start_timestamp: start date
        :param end_timestamp: end date
        :param dst_path: path to save the files to
        :param batch_size: number of files to download concurrently
        """
        async with aiohttp.ClientSession() as session:
            # Get the list of periods to download.
            binance_to_pandas_time_period = {
                BinanceNativeTimePeriod.DAILY: "D",
                BinanceNativeTimePeriod.MONTHLY: "M",
            }
            periods = pd.date_range(
                start=start_timestamp,
                end=end_timestamp,
                freq=binance_to_pandas_time_period[self.time_period],
            )
            _LOG.debug("Downloading data for periods %s", periods)
            # TODO(Vlad): Refactor this when we add more data types.
            # Get the path to the data on Binance.
            if self.contract_type == "futures":
                trading_type = "um"
            else:
                trading_type = "spot"
            market_data_type = "trades"
            path = self._get_binance_file_path(
                trading_type,
                market_data_type,
                self.time_period.value,
                currency_pair,
            )
            # Create tasks for downloading files
            tasks = []
            for period in periods:
                file_name = self._get_file_name_by_period(
                    self.time_period, currency_pair, period
                )
                task = self._download_single_binance_file(
                    session, path, file_name, dst_path
                )
                tasks.append(task)
                if len(tasks) == batch_size:
                    await asyncio.gather(*tasks)
                    tasks.clear()
            # Download remaining files if any
            if tasks:
                await asyncio.gather(*tasks)

    def _read_trades_from_csv_file(self, file_path: str) -> pd.DataFrame:
        """
        Read trades from a file.

        :param file_path: path to the file to read trades from
        :return: trades
        """
        # Check if the file has headers.
        two_rows = pd.read_csv(file_path, nrows=2)
        # Compare the values from the first line with the trades columns.
        if set(two_rows.columns) == set(TRADES_COLUMNS[self.contract_type]):
            trades = pd.read_csv(file_path)
        else:
            trades = pd.read_csv(
                file_path, names=TRADES_COLUMNS[self.contract_type]
            )
        return trades

    def _read_trades_from_chunks_by_days(
        self,
        data: Iterator[pd.DataFrame],
    ) -> Iterator[pd.DataFrame]:
        """
        Read trades from chunks by days.

        :param data: iterator of chunks
        :return: iterator of days
        """
        current_day = 0
        trades = []
        timestamp_column = "time"
        # Go through the chunks.
        for chunk in data:
            # Get days from the chunk.
            days_from_chunk = (
                chunk[timestamp_column]
                .apply(pd.Timestamp, unit="ms")
                .dt.day.unique()
            )
            if len(days_from_chunk) == 1:
                if days_from_chunk[0] == current_day:
                    trades.append(chunk)
                else:
                    if len(trades) > 0:
                        yield pd.concat(trades)
                    trades = [chunk]
                    current_day = days_from_chunk[0]
            # If there are more than one day in the chunk we need to split it.
            elif len(days_from_chunk) >= 2:
                # Get the first day.
                first_day = days_from_chunk[0]
                if first_day == current_day:
                    trades.append(
                        chunk[
                            chunk[timestamp_column]
                            .apply(pd.Timestamp, unit="ms")
                            .dt.day
                            == current_day
                        ]
                    )
                else:
                    if len(trades) > 0:
                        yield pd.concat(trades)
                    trades = [
                        chunk[
                            chunk[timestamp_column]
                            .apply(pd.Timestamp, unit="ms")
                            .dt.day
                            == first_day
                        ]
                    ]
                    current_day = first_day
                # Get the rest of the days.
                for day in days_from_chunk[1:]:
                    if len(trades) > 0:
                        yield pd.concat(trades)
                    trades = [
                        chunk[
                            chunk[timestamp_column]
                            .apply(pd.Timestamp, unit="ms")
                            .dt.day
                            == day
                        ]
                    ]
                    current_day = day
        # Yield the last day.
        if len(trades) > 0:
            yield pd.concat(trades)

    def _read_trades_from_csv_file_by_chunks(
        self, file_path: str
    ) -> Iterator[pd.DataFrame]:
        """
        Read trades from a file.

        :param file_path: path to the file to read trades from
        :return: trades
        """
        # TODO(Vlad): Extract the logic to define the header to a separate
        #  function.
        # Check if the file has headers.
        two_rows = pd.read_csv(file_path, nrows=2)
        # Compare the values from the first line with the trades columns.
        if set(two_rows.columns) == set(TRADES_COLUMNS[self.contract_type]):
            trades = pd.read_csv(file_path, chunksize=CHUNK_SIZE)
        else:
            trades = pd.read_csv(
                file_path,
                names=TRADES_COLUMNS[self.contract_type],
                chunksize=CHUNK_SIZE,
            )
        return trades

    def _extract_data_from_binance_files(
        self,
        src_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Extract data from the local Binance files.

        :param src_path: path to the files to extract data from
        :return: binance data
        """
        data = []
        if src_path is None:
            src_path = self.tmp_dir_path
        search_path = f"{src_path}/**/*.zip"
        for file_name in glob.glob(search_path, recursive=True):
            _LOG.info("Extracting %s", file_name)
            data.append(self._read_trades_from_csv_file(file_name))
        if len(data) == 0 and self.allow_data_gaps:
            _LOG.warning("No data found in %s", src_path)
            return pd.DataFrame(columns=TRADES_COLUMNS[self.contract_type])
        return pd.concat(data).reset_index(drop=True)

    def _post_process_binance_data(
        self,
        data: pd.DataFrame,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Post-process Binance data. It's necessary to post-process the data
        because the data from Binance is not in the correct format. We need to:

                - rename the columns
                - add the side column
                - add the end_download_timestamp column
                - filter the data by the start and end timestamps

        :param data: data to post-process
        :param start_timestamp: start date
        :param end_timestamp: end date
        :return: post-processed data
            Example:
                timestamp     | price | amount | side | end_download_timestamp
                1681131717000 | 0.001 | 1.0    | buy  | 1681131717000
        """
        start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
            start_timestamp, unit="ms"
        )
        end_timestamp = hdateti.convert_timestamp_to_unix_epoch(
            end_timestamp, unit="ms"
        )
        data["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        data.rename(columns={"time": "timestamp", "qty": "amount"}, inplace=True)
        data = data[
            [
                "timestamp",
                "price",
                "amount",
                "is_buyer_maker",
                "end_download_timestamp",
                "id",
                "quote_qty",
            ]
        ]
        return data[data.timestamp.between(start_timestamp, end_timestamp)]

    async def _get_binance_data_iterator(
        self,
        src_path: str,
    ) -> Iterator[pd.DataFrame]:
        """
        Get iterator over the Binance data asynchronously.

        :param src_path: path to the files to extract data from
        :return: iterator over Binance data that return pandas DataFrame
            with the data splitted by days
        """

        async def _process_file(file_name):
            data = []
            chunks = self._read_trades_from_csv_file_by_chunks(file_name)
            for df in self._read_trades_from_chunks_by_days(chunks):
                data.append(df)
            return data

        search_path = f"{src_path}/**/*.zip"
        data_iterator = []
        tasks = [
            _process_file(file_name)
            for file_name in glob.glob(search_path, recursive=True)
        ]
        for result in await asyncio.gather(*tasks):
            data_iterator.extend(result)
        return data_iterator

    def _get_trades_iterator(
        self,
        currency_pair: str,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
    ) -> Iterator[pd.DataFrame]:
        """
        Get the iterator that retrieve trades from Binance.

        :param currency_pair: currency pair to download
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: iterator over trades grouped by days that return pandas
            DataFrame with the data splitted by days
        """
        # Make temporary directory.
        tmp_dir = self._make_tmp_dir()
        # Download files locally.
        coroutine = self._download_binance_files(
            currency_pair, start_timestamp, end_timestamp, tmp_dir
        )
        asyncio.run(coroutine)
        # Get iterator over the files and chunks.
        coroutine = self._get_binance_data_iterator(tmp_dir)
        data_iterator = asyncio.run(coroutine)
        # Wrap the iterator with the data post-processing.
        data_iterator = (
            self._post_process_binance_data(data, start_timestamp, end_timestamp)
            for data in data_iterator
        )
        return data_iterator

    def _fetch_trades(
        self,
        currency_pair: str,
        start_timestamp: pd.Timestamp,
        end_timestamp: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Fetch trades from Binance.

        :param currency_pair: currency pair to download
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: trades data
        """
        # Make temporary directory.
        tmp_dir = self._make_tmp_dir()
        # Download files locally.
        coroutine = self._download_binance_files(
            currency_pair, start_timestamp, end_timestamp, tmp_dir
        )
        asyncio.run(coroutine)
        # Extract data from files.
        trades_df = self._extract_data_from_binance_files(tmp_dir)
        # Remove temporary directory.
        hio.delete_dir(tmp_dir)
        # Filter data by timestamp.
        start_timestamp_epoch = hdateti.convert_timestamp_to_unix_epoch(
            start_timestamp
        )
        end_timestamp_epoch = hdateti.convert_timestamp_to_unix_epoch(
            end_timestamp
        )
        trades_df = trades_df[
            trades_df.time.between(start_timestamp_epoch, end_timestamp_epoch)
        ]
        # Convert data.
        trades_df["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        trades_df.rename(
            columns={"time": "timestamp", "qty": "amount"}, inplace=True
        )
        trades_df["side"] = trades_df.is_buyer_maker.map(
            {False: "sell", True: "buy"}
        )
        trades_df = trades_df[
            ["timestamp", "price", "amount", "side", "end_download_timestamp"]
        ]
        # Return data.
        return trades_df

    def _get_currency_pairs(
        self,
        data_type: str,
    ) -> List[str]:
        """
        Get list of currency pairs.

        :param data_type: data type to get currency pairs for
        :return: list of currency pairs
        """
        if data_type == "trades":
            response = urlreq.urlopen(
                "https://fapi.binance.com/fapi/v1/exchangeInfo"
            ).read()
        else:
            raise ValueError(f"Data type {data_type} not supported")
        pairs = [symbol["symbol"] for symbol in json.loads(response)["symbols"]]
        return pairs

    def _download_trades(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> Union[Iterator[pd.DataFrame], pd.DataFrame]:
        """
        Download trades from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data:
            - if `time_period` is `BinanceNativeTimePeriod.MONTHLY` then
                iterator over monthly trades grouped by days that return
                pandas DataFrame with the data splitted by days
            - if `time_period` is `BinanceNativeTimePeriod.DAILY` then
                pandas DataFrame with the data
        """
        # Verify that exchange_id is correct.
        hdbg.dassert_eq(exchange_id, "binance")
        # Convert symbol to Binance Native format, e.g. "BTC_USDT" -> "BTCUSDT".
        currency_pair = self.convert_currency_pair(
            currency_pair,
        )
        data_type = "trades"
        currency_pairs = self._get_currency_pairs(data_type)
        hdbg.dassert_in(
            currency_pair,
            currency_pairs,
            "Currency pair is not present in exchange",
        )
        # Verify that date parameters are of correct format.
        hdbg.dassert_isinstance(end_timestamp, pd.Timestamp)
        hdbg.dassert_isinstance(start_timestamp, pd.Timestamp)
        hdbg.dassert_lte(start_timestamp, end_timestamp)
        # Fetch trades.
        if self.time_period in (
            BinanceNativeTimePeriod.MONTHLY,
            BinanceNativeTimePeriod.DAILY,
        ):
            trades = self._get_trades_iterator(
                currency_pair,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
        else:
            raise ValueError(f"Time period {self.time_period} not supported")
        return trades

    def _download_bid_ask(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download bid-ask data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        raise NotImplementedError("This method is not implemented yet.")

    def _download_ohlcv(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download OHLCV data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        raise NotImplementedError("This method is not implemented yet.")

    def _download_websocket_bid_ask(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download bid-ask data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        symbol = self.convert_currency_pair(currency_pair)
        if len(self._websocket_data_buffer[symbol]) > 0:
            data = copy.deepcopy(self._websocket_data_buffer[symbol][-1])
        else:
            data = {}
            data["timestamp"] = None
            data["bids"] = []
            data["asks"] = []
        self._websocket_data_buffer[symbol] = []
        data["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        data["symbol"] = currency_pair
        if data.get("bids") != None and data.get("asks") != None:
            (
                data["bids"],
                data["asks"],
            ) = self._pad_bids_asks_to_equal_len(data["bids"], data["asks"])
        return data

    def _download_websocket_ohlcv(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        Download OHLCV data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        data = {}
        data["currency_pair"] = currency_pair
        currency_pair = self.convert_currency_pair(currency_pair)
        data["ohlcv"] = list(self._ohlcv[currency_pair].values())
        data["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        if len(data["ohlcv"]) == 0:
            return None
        return data

    def _download_websocket_trades(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download trades data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        data = {}
        data["currency_pair"] = currency_pair
        currency_pair = self.convert_currency_pair(currency_pair)
        data["data"] = copy.deepcopy(list(self._trades[currency_pair]))
        self._trades[currency_pair] = []
        data["end_download_timestamp"] = str(hdateti.get_current_time("UTC"))
        data["exchange_id"] = "binance"
        if len(data["data"]) == 0:
            return None
        return data

    def _download_websocket_ohlcv_from_trades(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download OHLCV data from trades data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        :return: exchange data
        """
        raise NotImplementedError(
            "This extractor is for historical data download only. "
            "It can't be used for the real-time data downloading."
        )

    def _subscribe_to_websocket_bid_ask(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to bid-ask data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        """
        raise NotImplementedError("This method is not implemented yet.")

    def _subscribe_to_websocket_ohlcv(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to OHLCV data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        """
        raise NotImplementedError("This method is not implemented yet.")

    def _subscribe_to_websocket_trades(
        self,
        exchange_id: str,
        currency_pair: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to trades data from Binance.

        :param exchange_id: parameter for compatibility with other extractors
          always set to `binance`
        :param currency_pair: currency pair to get data for, e.g. `BTC_USDT`
        :param start_timestamp: start timestamp
        :param end_timestamp: end timestamp
        """
        raise NotImplementedError("This method is not implemented yet.")

    async def _subscribe_to_websocket_bid_ask_multiple_symbols(
        self,
        exchange_id: str,
        currency_pairs: List[str],
        bid_ask_depth: int,
        **kwargs: Any,
    ) -> None:
        """
        #TODO(Juraj): Add docstring.

        :param exchange_id: exchange to download from (not used, kept
            for compatibility with parent class).
        :param currency_pairs: currency pairs, e.g. ["BTC_USDT",
            "ETH_USDT"]
        :param bid_ask_depth: how many levels of order book to download
        """
        self.currency_pairs = currency_pairs
        self.bid_ask_depth = bid_ask_depth
        # Binance only supports depth 5, 10 or 20
        if bid_ask_depth not in [5, 10, 20]:
            _LOG.warning(
                f"Bid/Ask depth {bid_ask_depth} not supported by binance, setting downloader depth to 5"
            )
            bid_ask_depth = 5
        # Binance has a rate limit of 10 incoming messages per secnd
        throttle_counter = 0
        for currency_pair in currency_pairs:
            _LOG.info(f"subscribe: {self.convert_currency_pair(currency_pair)}")
            self._client.partial_book_depth(
                symbol=self.convert_currency_pair(currency_pair),
                level=bid_ask_depth,
                speed=100,
            )
            self._websocket_data_buffer[
                self.convert_currency_pair(currency_pair)
            ] = []
            throttle_counter += 1
            if throttle_counter == 10:
                time.sleep(1)
                throttle_counter = 0

    async def _subscribe_to_websocket_ohlcv_multiple_symbols(
        self,
        exchange_id: str,
        currency_pairs: List[str],
        **kwargs: Any,
    ) -> None:
        """
        #TODO(Juraj): Add docstring.

        :param exchange_id: exchange to download from (not used, kept
            for compatibility with parent class).
        :param currency_pairs: currency pairs, e.g. ["BTC_USDT",
            "ETH_USDT"]
        """
        self.currency_pairs = currency_pairs
        # Binance has a rate limit of 10 incoming messages per secnd
        throttle_counter = 0
        for currency_pair in currency_pairs:
            _LOG.info(f"subscribe: {self.convert_currency_pair(currency_pair)}")
            self._client.kline(
                symbol=self.convert_currency_pair(currency_pair),
                interval="1m",
            )
            self._ohlcv[self.convert_currency_pair(currency_pair)] = {}
            throttle_counter += 1
            if throttle_counter == 10:
                time.sleep(1)
                throttle_counter = 0

    async def _subscribe_to_websocket_trades_multiple_symbols(
        self,
        exchange_id: str,
        currency_pairs: List[str],
        **kwargs: Any,
    ) -> None:
        """
        #TODO(Juraj): Add docstring.

        :param exchange_id: exchange to download from (not used, kept
            for compatibility with parent class).
        :param currency_pairs: currency pairs, e.g. ["BTC_USDT",
            "ETH_USDT"]
        """
        self.currency_pairs = currency_pairs
        # Binance has a rate limit of 10 incoming messages per secnd
        throttle_counter = 0
        for currency_pair in currency_pairs:
            _LOG.info(f"subscribe: {self.convert_currency_pair(currency_pair)}")
            self._client.trade(
                symbol=self.convert_currency_pair(currency_pair),
            )
            self._trades[self.convert_currency_pair(currency_pair)] = []
            throttle_counter += 1
            if throttle_counter == 10:
                time.sleep(1)
                throttle_counter = 0

    def _pad_bids_asks_to_equal_len(
        self, bids: List[List], asks: List[List]
    ) -> Tuple[List[List], List[List]]:
        """
        Pad list of bids and asks to the same length.
        """
        max_len = max(len(bids), len(asks))
        pad_bids_num = max_len - len(bids)
        pad_asks_num = max_len - len(asks)
        bids = bids + [[None, None]] * pad_bids_num
        asks = asks + [[None, None]] * pad_asks_num
        return bids, asks
