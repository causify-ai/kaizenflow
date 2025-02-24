"""
Import as:

import im_v2.binance.websocket.binance_socket_manager as imvbwbsoma
"""

import logging
import random
import threading
import time
from typing import Optional

from websocket import (
    ABNF,
    WebSocketConnectionClosedException,
    WebSocketException,
    create_connection,
)

import im_v2.binance.websocket.utils as imvbiweut


class BinanceSocketManager(threading.Thread):
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
        threading.Thread.__init__(self)
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.stream_url = stream_url
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_error = on_error
        self.on_disconnect = on_disconnect
        self.proxies = proxies

        self._proxy_params = imvbiweut.parse_proxies(proxies) if proxies else {}

        self.create_ws_connection()
        # Max attempts for retry subscription.
        self.max_attempts = max_attempts

    def create_ws_connection(self):
        self.logger.debug(
            f"Creating connection with WebSocket Server: {self.stream_url}, proxies: {self.proxies}",
        )
        self.ws = create_connection(self.stream_url, **self._proxy_params)
        self.logger.debug(
            f"WebSocket connection has been established: {self.stream_url}, proxies: {self.proxies}",
        )
        self._callback(self.on_open)

    def run(self):
        self.read_data()

    def send_message(self, message):
        self.logger.debug(
            "Sending message to Binance WebSocket Server: %s", message
        )
        self.ws.send(message)

    def ping(self):
        self.ws.ping()

    def read_data(self):
        data = ""
        while True:
            try:
                op_code, frame = self.ws.recv_data_frame(True)
            except WebSocketException as e:
                if isinstance(e, WebSocketConnectionClosedException):
                    self.logger.error("Lost websocket connection")
                    self._callback(self.on_disconnect)
                    continue
                else:
                    self.logger.error("Websocket exception: {}".format(e))
                    raise e
            except Exception as e:
                self.logger.error("Exception in read_data: {}".format(e))
                raise e

            if op_code == ABNF.OPCODE_CLOSE and self.max_attempts:
                # Handle cases where the connection closes unexpectedly during initial subscription attempts.
                # Decrease the max attempts counter to manage reconnection attempts.
                self.max_attempts = self.max_attempts - 1
                self.logger.warning(
                    "Subscribing Again, Attempts left %s", self.max_attempts
                )
                # Sleep for some random time to cool things down.
                sleep_secs = random.randint(2,5)
                time.sleep(sleep_secs)
                self._callback(self.on_disconnect)
                continue
            elif op_code == ABNF.OPCODE_CLOSE:
                self.logger.warning(
                    "CLOSE frame received, closing websocket connection"
                )
                self._callback(self.on_close)
                break
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
                self.ws.pong("")
                self.logger.debug("Received Ping; PONG frame sent back")
            elif op_code == ABNF.OPCODE_PONG:
                self.logger.debug("Received PONG frame")
                self._callback(self.on_pong)
            else:
                data = frame.data
                # If the subscription was successful, set max_attempts to 0 to avoid redundant resubscriptions.
                self.max_attempts = 0
                if op_code == ABNF.OPCODE_TEXT:
                    data = data.decode("utf-8")
                self._callback(self.on_message, data)

    def close(self):
        if not self.ws.connected:
            self.logger.warn("Websocket already closed")
        else:
            self.ws.send_close()
        return

    def _callback(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception as e:
                self.logger.error(
                    "Error from callback {}: {}".format(callback, e)
                )
                if self.on_error:
                    self.on_error(self, e)
