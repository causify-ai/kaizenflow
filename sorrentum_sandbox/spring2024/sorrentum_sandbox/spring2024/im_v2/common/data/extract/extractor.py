"""
Implement abstract extractor class.

Import as:

import im_v2.common.data.extract.extractor as ivcdexex
"""

import abc
from typing import Any, Dict, List

import pandas as pd

import helpers.hdbg as hdbg


# TODO(gp): -> MarketDataExtractor and descends from Data
class Extractor(abc.ABC):
    """
    Abstract class for downloading raw data from vendors.
    """

    def __init__(self) -> None:
        super().__init__()

    # TODO(Juraj): rename `download_data_rest` to clarify after addition of
    #  websocket based download in #CmTask2912.
    def download_data(
        self, data_type: str, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> pd.DataFrame:
        """
        Download exchange data using REST API based download.

        :param data_type: the type of data, e.g. `ohlcv`, `bid_ask`, `trades`
            This is used to dispatch the call to abstract methods from the other
            derived classes.
        :param exchange_id: exchange to get data from, e.g. `binance`
        :param currency_pair: currency_pair to get data about, e.g. `ETH_USDT`
        :param kwargs: passed to the downloading method
        :return: exchange data as dataframe
        """
        if data_type == "ohlcv":
            data = self._download_ohlcv(
                exchange_id,
                currency_pair,
                **kwargs,
            )
        elif data_type == "bid_ask":
            data = self._download_bid_ask(exchange_id, currency_pair, **kwargs)
        elif data_type == "trades":
            data = self._download_trades(exchange_id, currency_pair, **kwargs)
        else:
            hdbg.dfatal(f"Unknown data type {data_type}.")
        return data

    # #########################################################################

    def download_websocket_data(
        self, data_type: str, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        """
        Download exchange data using websocket.

        This assumes that the websocket corresponding to the particular
        `exchange_id` and `currency_pair` has been subscribed to via
        `subscribe_to_websocket_data()`.

        Same parameters as `download_data()`.
        """
        if data_type == "ohlcv":
            data = self._download_websocket_ohlcv(
                exchange_id,
                currency_pair,
                **kwargs,
            )
        elif data_type == "bid_ask":
            data = self._download_websocket_bid_ask(
                exchange_id, currency_pair, **kwargs
            )
        elif data_type == "trades":
            data = self._download_websocket_trades(
                exchange_id, currency_pair, **kwargs
            )
        elif data_type == "ohlcv_from_trades":
            data = self._download_websocket_ohlcv_from_trades(
                exchange_id, currency_pair, **kwargs
            )
        else:
            hdbg.dfatal(f"Unknown data type {data_type}")
        return data

    async def subscribe_to_websocket_data(
        self, data_type: str, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> None:
        """
        Subscribe to websocket based data stream for a particular exchange
        `exchange_id` and `currency_pair`.

        Same parameters as `download_websocket_data()`.
        """
        if data_type == "ohlcv":
            await self._subscribe_to_websocket_ohlcv(
                exchange_id,
                currency_pair,
                **kwargs,
            )
        elif data_type == "bid_ask":
            await self._subscribe_to_websocket_bid_ask(
                exchange_id, currency_pair, **kwargs
            )
        elif data_type == "trades":
            await self._subscribe_to_websocket_trades(
                exchange_id, currency_pair, **kwargs
            )
        elif data_type == "ohlcv_from_trades":
            await self._subscribe_to_websocket_trades(
                exchange_id, currency_pair, **kwargs
            )
        else:
            hdbg.dfatal(f"Unknown data type {data_type}")

    async def subscribe_to_websocket_data_multiple_symbols(
        self,
        data_type: str,
        exchange_id: str,
        currency_pairs: List[str],
        **kwargs: Any,
    ):
        """
        Subscribe to websocket based data stream for a particular exchange
        `exchange_id` and multiple currency_pairs.

        Same parameters as `download_websocket_data()`.
        """
        if data_type == "ohlcv":
            await self._subscribe_to_websocket_ohlcv_multiple_symbols(
                exchange_id,
                currency_pairs,
                **kwargs,
            )
        elif data_type == "bid_ask":
            await self._subscribe_to_websocket_bid_ask_multiple_symbols(
                exchange_id, currency_pairs, **kwargs
            )
        elif data_type == "trades":
            await self._subscribe_to_websocket_trades_multiple_symbols(
                exchange_id, currency_pairs, **kwargs
            )
        else:
            hdbg.dfatal(f"Unknown data type {data_type}")

    # #########################################################################
    # Private methods.
    # #########################################################################

    @abc.abstractmethod
    def _download_ohlcv(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def _download_bid_ask(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def _download_trades(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def _download_websocket_ohlcv(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _download_websocket_ohlcv_from_trades(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _download_websocket_bid_ask(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _download_websocket_trades(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _subscribe_to_websocket_ohlcv(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _subscribe_to_websocket_bid_ask(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _subscribe_to_websocket_bid_ask_multiple_symbols(
        self, exchange_id: str, currency_pair: List[str], **kwargs: Any
    ) -> Dict:
        ...

    @abc.abstractmethod
    def _subscribe_to_websocket_trades(
        self, exchange_id: str, currency_pair: str, **kwargs: Any
    ) -> Dict:
        ...
