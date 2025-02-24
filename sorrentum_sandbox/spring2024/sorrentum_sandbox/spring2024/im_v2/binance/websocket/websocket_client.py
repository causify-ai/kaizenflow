"""
Import as:

import im_v2.binance.websocket.websocket_client as imvbwwecl
"""

import json
import logging
from typing import Optional

import im_v2.binance.websocket.binance_socket_manager as imvbwbsoma
import im_v2.binance.websocket.utils as imvbiweut


class BinanceWebsocketClient:
    ACTION_SUBSCRIBE = "SUBSCRIBE"
    ACTION_UNSUBSCRIBE = "UNSUBSCRIBE"

    def __init__(
        self,
        stream_url,
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        on_disconnect=None,
        logger=None,
        proxies: Optional[dict] = None,
        max_attempts=0,
    ):
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.socket_manager = self._initialize_socket(
            stream_url,
            on_message,
            on_open,
            on_close,
            on_error,
            on_ping,
            on_pong,
            on_disconnect,
            logger,
            proxies,
            max_attempts,
        )

        # start the thread
        self.socket_manager.start()
        self.logger.debug("Binance WebSocket Client started.")

    def send(self, message: dict):
        self.socket_manager.send_message(json.dumps(message))

    def send_message_to_server(self, message, action=None, id=None):
        if not id:
            id = imvbiweut.get_timestamp()

        if action != self.ACTION_UNSUBSCRIBE:
            return self.subscribe(message, id=id)
        return self.unsubscribe(message, id=id)

    def subscribe(self, stream, id=None):
        if not id:
            id = imvbiweut.get_timestamp()
        if self._single_stream(stream):
            stream = [stream]
        json_msg = json.dumps({"method": "SUBSCRIBE", "params": stream, "id": id})
        self.socket_manager.send_message(json_msg)

    def unsubscribe(self, stream, id=None):
        if not id:
            id = imvbiweut.get_timestamp()
        if self._single_stream(stream):
            stream = [stream]
        json_msg = json.dumps(
            {"method": "UNSUBSCRIBE", "params": stream, "id": id}
        )
        self.socket_manager.send_message(json_msg)

    def ping(self):
        self.logger.debug("Sending ping to Binance WebSocket Server")
        self.socket_manager.ping()

    def stop(self, id=None):
        self.socket_manager.close()
        self.socket_manager.join()

    def list_subscribe(self, id=None):
        """
        Sending the list subscription message, e.g.

        {"method": "LIST_SUBSCRIPTIONS","id": 100}
        """

        if not id:
            id = imvbiweut.get_timestamp()
        self.socket_manager.send_message(
            json.dumps({"method": "LIST_SUBSCRIPTIONS", "id": id})
        )

    def _initialize_socket(
        self,
        stream_url,
        on_message,
        on_open,
        on_close,
        on_error,
        on_ping,
        on_pong,
        on_disconnect,
        logger,
        proxies,
        max_attempts,
    ):
        return imvbwbsoma.BinanceSocketManager(
            stream_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
            on_disconnect=on_disconnect,
            logger=logger,
            proxies=proxies,
            max_attempts=max_attempts,
        )

    def _single_stream(self, stream):
        if isinstance(stream, str):
            return True
        elif isinstance(stream, list):
            return False
        else:
            raise ValueError("Invalid stream name, expect string or array")


class UMFuturesWebsocketClient(BinanceWebsocketClient):
    def __init__(
        self,
        stream_url="wss://fstream.binance.com",
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        on_disconnect=None,
        is_combined=False,
        proxies: Optional[dict] = None,
        max_attempts=0,
    ):
        if is_combined:
            stream_url = stream_url + "/stream"
        else:
            stream_url = stream_url + "/ws"
        super().__init__(
            stream_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_ping=on_ping,
            on_pong=on_pong,
            on_disconnect=on_disconnect,
            proxies=proxies,
            max_attempts=max_attempts,
        )

    def agg_trade(self, symbol: str, id=None, action=None, **kwargs):
        """
        Aggregate Trade Streams.

        The Aggregate Trade Streams push market trade information that is aggregated for a single taker order every 100 milliseconds.
        Only market trades will be aggregated, which means the insurance fund trades and ADL trades won't be aggregated.

        Stream Name: <symbol>@aggTrade

        https://binance-docs.github.io/apidocs/futures/en/#aggregate-trade-streams

        Update Speed: 100ms
        """
        stream_name = "{}@aggTrade".format(symbol.lower())

        self.send_message_to_server(stream_name, action=action, id=id)

    def trade(self, symbol, id=None, action=None, **kwargs):
        """
        Individual Trade Streams.

        # TODO(Sonaal) : Add docstring.

        Stream Name: <symbol>@trade

        Update Speed: 100ms
        """
        stream_name = "{}@trade".format(symbol.lower())
        self.send_message_to_server(stream_name, action=action, id=id)

    def mark_price(self, symbol: str, speed: int, id=None, action=None, **kwargs):
        """
        Mark Price Streams.

        Mark price and funding rate for all symbols pushed every 3 seconds or every second.

        Stream Name: <symbol>@markPrice or <symbol>@markPrice@1s

        https://binance-docs.github.io/apidocs/futures/en/#mark-price-stream

        Update Speed: 3000ms or 1000ms
        """
        stream_name = "{}@markPrice@{}s".format(symbol.lower(), speed)

        self.send_message_to_server(stream_name, action=action, id=id)

    def kline(self, symbol: str, interval: str, id=None, action=None, **kwargs):
        """
        Kline/Candlestick Streams.

        The Kline/Candlestick Stream push updates to the current klines/candlestick every 250 milliseconds (if existing)

        Stream Name: <symbol>@kline_<interval>

        https://binance-docs.github.io/apidocs/futures/en/#kline-candlestick-streams

        interval:
        m -> minutes; h -> hours; d -> days; w -> weeks; M -> months

        - 1m
        - 3m
        - 5m
        - 15m
        - 30m
        - 1h
        - 2h
        - 4h
        - 6h
        - 8h
        - 12h
        - 1d
        - 3d
        - 1w
        - 1M

        Update Speed: 250ms
        """
        stream_name = "{}@kline_{}".format(symbol.lower(), interval)

        self.send_message_to_server(stream_name, action=action, id=id)

    def continuous_kline(
        self,
        pair: str,
        contractType: str,
        interval: str,
        id=None,
        action=None,
        **kwargs
    ):
        """
        Continuous Kline/Candlestick Streams.

        The Kline/Candlestick Stream push updates to Kline/candlestick bars for a specific contract type. every 250 milliseconds

        Stream Name: <pair>_<contractType>@continuousKline_<interval>

        https://binance-docs.github.io/apidocs/futures/en/#continuous-contract-kline-candlestick-streams

        interval:
        m -> minutes; h -> hours; d -> days; w -> weeks; M -> months

        - 1m
        - 3m
        - 5m
        - 15m
        - 30m
        - 1h
        - 2h
        - 4h
        - 6h
        - 8h
        - 12h
        - 1d
        - 3d
        - 1w
        - 1M

        Update Speed: 250ms
        """
        stream_name = "{}_{}@continuousKline_{}".format(
            pair.lower(), contractType, interval
        )

        self.send_message_to_server(stream_name, action=action, id=id)

    def mini_ticker(self, symbol=None, id=None, action=None, **kwargs):
        """
        Individual symbol or all symbols mini ticker.

        24hr rolling window mini-ticker statistics.
        These are NOT the statistics of the UTC day, but a 24hr rolling window for the previous 24hrs

        Stream Name: <symbol>@miniTicker or
        Stream Name: !miniTicker@arr

        https://binance-docs.github.io/apidocs/futures/en/#individual-symbol-mini-ticker-stream
        https://binance-docs.github.io/apidocs/futures/en/#individual-symbol-ticker-streams

        Update Speed: 500ms for individual symbol, 1000ms for all market symbols
        """

        if symbol is None:
            stream_name = "!miniTicker@arr"
        else:
            stream_name = "{}@miniTicker".format(symbol.lower())

        self.send_message_to_server(stream_name, action=action, id=id)

    def ticker(self, symbol=None, id=None, action=None, **kwargs):
        """
        Individual symbol or all symbols ticker.

        24hr rolling window ticker statistics for a single symbol.
        These are NOT the statistics of the UTC day, but a 24hr rolling window from requestTime to 24hrs before.

        Stream Name: <symbol>@ticker or
        Stream Name: !ticker@arr

        https://binance-docs.github.io/apidocs/futures/en/#individual-symbol-ticker-streams
        https://binance-docs.github.io/apidocs/futures/en/#all-market-tickers-streams

        Update Speed: 500ms for individual symbol, 1000ms for all market symbols
        """

        if symbol is None:
            stream_name = "!ticker@arr"
        else:
            stream_name = "{}@ticker".format(symbol.lower())
        self.send_message_to_server(stream_name, action=action, id=id)

    def book_ticker(self, symbol, id=None, action=None, **kwargs):
        """
        Individual symbol or all book ticker.

        Pushes any update to the best bid or ask's price or quantity in real-time for a specified symbol.

        Stream Name: <symbol>@bookTicker or
        Stream Name: !bookTicker

        https://binance-docs.github.io/apidocs/futures/en/#individual-symbol-book-ticker-streams
        https://binance-docs.github.io/apidocs/futures/en/#all-book-tickers-stream

        Update Speed: Real-time
        """
        if symbol is None:
            stream_name = "!bookTicker"
        else:
            stream_name = "{}@bookTicker".format(symbol.lower())
        self.send_message_to_server(stream_name, action=action, id=id)

    def diff_book_depth(
        self, symbol: str, speed=100, id=None, action=None, **kwargs
    ):
        """
        Diff. Depth Stream Order book price and quantity depth updates used to
        locally manage an order book.

        Stream Name: <symbol>@depth OR <symbol>@depth@500ms OR<symbol>@depth@100ms

        https://binance-docs.github.io/apidocs/futures/en/#diff-book-depth-streams

        Update Speed: 250ms, 500ms or 100ms
        """

        self.send_message_to_server(
            "{}@depth@{}ms".format(symbol.lower(), speed), action=action, id=id
        )

    def partial_book_depth(
        self, symbol: str, level=5, speed=500, id=None, action=None, **kwargs
    ):
        """
        Partial Book Depth Streams.

        Top bids and asks, Valid are 5, 10, or 20.

        Stream Names: <symbol>@depth<levels> OR <symbol>@depth<levels>@500ms OR <symbol>@depth<levels>@100ms

        https://binance-docs.github.io/apidocs/futures/en/#partial-book-depth-streams

        Update Speed: 250ms, 500ms or 100ms
        """
        self.send_message_to_server(
            "{}@depth{}@{}ms".format(symbol.lower(), level, speed),
            id=id,
            action=action,
        )

    def liquidation_order(self, symbol: str, id=None, action=None, **kwargs):
        """
        The Liquidation Order Snapshot Streams push force liquidation order
        information for specific symbol. The All Liquidation Order Snapshot
        Streams push force liquidation order information for all symbols in the
        market.

        For each symbol，only the latest one liquidation order within 1000ms will be pushed as the snapshot. If no liquidation happens in the interval of 1000ms, no stream will be pushed.

        Stream Name: <symbol>@forceOrder or
        Stream Name: !forceOrder@arr

        https://binance-docs.github.io/apidocs/futures/en/#liquidation-order-streams
        https://binance-docs.github.io/apidocs/futures/en/#all-market-liquidation-order-streams

        Update Speed: 1000ms
        """
        if symbol is None:
            stream_name = "!forceOrder@arr"
        else:
            stream_name = "{}@forceOrder".format(symbol.lower())
        self.send_message_to_server(stream_name, id=id, action=action)

    def composite_index(self, symbol: str, id=None, action=None, **kwargs):
        """
        Composite Index Info Stream Composite index information for index
        symbols pushed every second.

        Stream Name: <symbol>@compositeIndex

        https://binance-docs.github.io/apidocs/futures/en/#composite-index-symbol-information-streams

        Update Speed: 1000ms
        """

        self.send_message_to_server(
            "{}@compositeIndex".format(symbol.lower()), id=id, action=action
        )

    def user_data(self, listen_key: str, id=None, action=None, **kwargs):
        """
        Listen to user data by using the provided listen_key.
        """
        self.send_message_to_server(listen_key, action=action, id=id)
