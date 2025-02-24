import time
import unittest.mock as umock
from collections import namedtuple
from typing import Any, List

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import im_v2.binance.data.extract.extractor as imvbdexex
import im_v2.binance.websocket.binance_socket_manager as imvbwbsoma


class TestBinanceExtractor1(hunitest.TestCase):
    def test_fetch_trades(self) -> None:
        """
        Tests the fetch trades method.
        """
        # Mock downloading files and extracting data from them.
        imvbdexex.hio = umock.MagicMock()
        contract_type = "futures"
        data_type = "trades"
        try:
            binance_extractor = imvbdexex.BinanceExtractor(
                contract_type, imvbdexex.BinanceNativeTimePeriod.DAILY, data_type
            )
            binance_extractor._download_binance_files = umock.AsyncMock()
            binance_extractor._extract_data_from_binance_files = umock.MagicMock(
                return_value=self._get_mock_trades()
            )
            # Prepare parameters.
            currency_pair = "BTCUSDT"
            start_date = pd.Timestamp("2020-01-01 00:00:00")
            end_date = pd.Timestamp("2020-01-03 23:59:00")
            # Run.
            actual_df = binance_extractor._fetch_trades(
                currency_pair, start_date, end_date
            )
        except Exception as e:
            raise e
        finally:
            binance_extractor.close()
        # Compare results.
        actual = hpandas.df_to_str(
            actual_df.drop(columns=["end_download_timestamp"])
        )
        expected = """timestamp  price  amount  side
            0  1577836800000    100       1   buy
            1  1577923200000    200       2  sell
            2  1578009600000    300       3   buy"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def _get_mock_trades(self) -> pd.DataFrame:
        """
        Returns a mock trades dataframe.
        """
        return pd.DataFrame(
            {
                "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT", "BTCUSDT"],
                "time": [
                    hdateti.convert_timestamp_to_unix_epoch(
                        pd.Timestamp("2020-01-01 00:00:00")
                    ),
                    hdateti.convert_timestamp_to_unix_epoch(
                        pd.Timestamp("2020-01-02 00:00:00")
                    ),
                    hdateti.convert_timestamp_to_unix_epoch(
                        pd.Timestamp("2020-01-03 00:00:00")
                    ),
                    hdateti.convert_timestamp_to_unix_epoch(
                        pd.Timestamp("2020-01-04 10:00:00")
                    ),
                ],
                "price": [100, 200, 300, 400],
                "qty": [1, 2, 3, 4],
                "is_buyer_maker": [True, False, True, False],
                "quote_qty": [100, 400, 900, 300],
                "id": [1, 2, 3, 4],
            }
        )


class TestBinanceExtractor2(hunitest.TestCase):
    """
    Test subscription and reconnection on error.
    """

    def test1(self) -> None:
        """
        Test subscription and WebSocketConnectionClosedException.

        The expected behavior is as follows:
            1. We subscribe to the webSocket with the specified currency pairs and begin receiving data.
            2. WebSocket exception is thrown during data reception, we catch it internally.
            3. Upon catching the exception, we proceed to resubscribe to the same currency pairs.
            4. Once resubscribed, we resume receiving data from the WebSocket.
        """
        # Create dummy data.
        bid_ask = namedtuple("bid_ask", ["data"])
        dummy_data = bid_ask(data="dummy")
        side_effect = [
            ["", dummy_data],
            imvbwbsoma.WebSocketConnectionClosedException,
            ["", dummy_data],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
        ]
        exp = r"""['dummy', 'dummy']"""
        self._test_binance_extractor(side_effect, exp)

    def test2(self) -> None:
        """
        Test max attempts for retry subscription.

        The expected behavior is as follows:
            1. Initially attempts to subscribe to the websocket may fail.
            2. Subscription is retried based on the specified maximum attempts count.
            3. Upon successful subscription, data reception starts.
        """
        # Create dummy data.
        bid_ask = namedtuple("bid_ask", ["data"])
        dummy_data = bid_ask(data="dummy")
        max_attempts = 2
        side_effect = [
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            ["", dummy_data],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
        ]
        exp = r"""['dummy']"""
        self._test_binance_extractor(side_effect, exp, max_attempts=max_attempts)

    def test3(self) -> None:
        """
        Test max attempts for retry subscription.

        The expected behavior is as follows:
            1. Initially attempts to subscribe to the websocket may fail.
            2. Subscription is retried based on the specified maximum attempts count.
            3. Max attempts are exhausted, data reception fails.
        """
        # Create dummy data.
        bid_ask = namedtuple("bid_ask", ["data"])
        dummy_data = bid_ask(data="dummy")
        max_attempts = 2
        side_effect = [
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            ["", dummy_data],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
        ]
        exp = r"""[]"""
        self._test_binance_extractor(side_effect, exp, max_attempts=max_attempts)

    def test4(self) -> None:
        """
        Test max attempts for retry subscription.

        The expected behavior is as follows:
            1. Initial subscription attempts are successful.
            2. An unexpected close connection signal is received.
            3. Subscription is not retried as max attempts only apply to initial subscription.
        """
        # Create dummy data.
        bid_ask = namedtuple("bid_ask", ["data"])
        dummy_data = bid_ask(data="dummy")
        max_attempts = 2
        side_effect = [
            ["", dummy_data],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
            ["", dummy_data],
            [imvbwbsoma.ABNF.OPCODE_CLOSE, {}],
        ]
        exp = r"""['dummy']"""
        self._test_binance_extractor(side_effect, exp, max_attempts=max_attempts)

    def _test_binance_extractor(
        self,
        side_effect: List[Any],
        expected: str,
        *,
        max_attempts: int = 0,
    ) -> None:
        """
        Init `BinanceExtractor` and subscribe.
        """
        self.actual = []
        try:
            with umock.patch.object(
                imvbdexex.BinanceExtractor,
                "_handle_orderbook_message",
                new=self._mock_handle_orderbook_message,
            ), umock.patch.object(
                imvbwbsoma.random, "randint",
                # Mock waiting time for resubscription.
                new=self._mock_randint,
            ), umock.patch.object(
                imvbwbsoma, "create_connection"
            ) as mock_ws_connection:
                # Mock WebSocketConnectionClosed error.
                mock_ws_connection_instance = mock_ws_connection.return_value
                mock_ws_connection_instance.recv_data_frame = umock.MagicMock(
                    side_effect=side_effect
                )
                # Init.
                contract_type = "futures"
                data_type = "bid_ask"
                exchange_id = "binance"
                currency_pairs = ["ETH_USDT"]
                bid_ask_depth = 5
                binance_extractor = imvbdexex.BinanceExtractor(
                    contract_type,
                    imvbdexex.BinanceNativeTimePeriod.DAILY,
                    data_type,
                    max_attempts=max_attempts,
                )
                # Subscribe.
                with hasynci.solipsism_context() as event_loop:
                    coroutine = binance_extractor._subscribe_to_websocket_bid_ask_multiple_symbols(
                        exchange_id,
                        currency_pairs,
                        bid_ask_depth=bid_ask_depth,
                    )
                    hasynci.run(coroutine, event_loop=event_loop)
                time.sleep(1)
                # Assert.
                self.assert_equal(str(self.actual), expected)
        except Exception as e:
            raise e
        finally:
            binance_extractor.close()

    def _mock_handle_orderbook_message(self, _, message: str):
        """
        Mock `_handle_orderbook_message`.
        """
        self.actual.append(message)
    
    def _mock_randint(self, start: int, end: int):
        """
        Mock `random.randint()`
        """
        return 0
