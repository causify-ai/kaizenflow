import argparse
import asyncio
import datetime
import unittest.mock as umock
from typing import Any, Dict

import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hsql as hsql
import helpers.hunit_test as hunitest
import im_v2.ccxt.data.extract.download_exchange_data_to_db_periodically as imvcdededtdp
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.db.db_utils as imvcddbut


class TestDownloadRealtimeForOneExchangePeriodically1(
    imvcddbut.TestImDbHelper, hunitest.TestCase
):
    # Mock calls to external provider.
    ccxtpro_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcdexex,
        "ccxtpro",
        spec=imvcdededtdp.imvcdeexut.imvcdexex.ccxtpro,
    )
    ccxt_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcdexex,
        "ccxt",
        spec=imvcdededtdp.imvcdeexut.imvcdexex.ccxt,
    )
    get_current_time_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcdexex.hdateti,
        "get_current_time",
        return_value=pd.Timestamp("2023-09-26 16:04:10+00:00"),
    )
    db_connection_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcddbut.DbConnectionManager, "get_connection"
    )

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Add an isolated events loop.
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Activate mock for `ccxt.pro`.
        self.ccxtpro_mock: umock.MagicMock = self.ccxtpro_patch.start()
        # Activate mock for `ccxt`.
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        # Mock the binance ccxt to return load market keys, they don't need to be real.
        self.ccxt_mock.binance.return_value.load_markets.return_value.keys.return_value = [
            "MOCKBTC/MOCKUSD"
        ]
        # Mock the binance class inside ccxtpro (ccxt.pro).
        self.mock_binance_class = self.ccxtpro_mock.binance = umock.MagicMock()
        # Mock the `get_current_time` function.
        self.get_current_time_mock = self.get_current_time_patch.start()
        # Mock the `get_connection` function.
        self.mock_get_connection = self.db_connection_patch.start()
        self.mock_get_connection.return_value = self.connection

    def tear_down_test(self) -> None:
        self.ccxt_patch.stop()
        self.ccxtpro_patch.stop()
        self.get_current_time_patch.stop()
        self.db_connection_patch.stop()

    @pytest.mark.slow("~10 seconds.")
    def test_download_websocket_ohlcv_spot(
        self,
    ) -> None:
        """
        Test Python script call for OHLCV spot data type.
        """
        # Get query to create the `ccxt_ohlcv_spot` database.
        query = imvccdbut.get_ccxt_ohlcv_create_table_query()
        # Get downloaded data.
        data = self._test_websocket_data_download(
            "ohlcv",
            "spot",
            "ccxt_ohlcv_spot",
            query,
        )
        # Check downloaded data.
        actual = hpandas.df_to_str(data, num_rows=None)
        self.check_string(actual, fuzzy_match=True)

    @pytest.mark.slow("~10 seconds.")
    def test_download_websocket_ohlcv_futures(
        self,
    ) -> None:
        """
        Test Python script call for OHLCV futures data type.
        """
        # Get query to create the `ccxt_ohlcv_futures` database.
        query = imvccdbut.get_ccxt_ohlcv_futures_create_table_query()
        # Get downloaded data.
        data = self._test_websocket_data_download(
            "ohlcv",
            "futures",
            "ccxt_ohlcv_futures",
            query,
        )
        # Check downloaded data.
        actual = hpandas.df_to_str(data, num_rows=None)
        self.check_string(actual, fuzzy_match=True)

    @pytest.mark.slow("~10 seconds.")
    def test_download_websocket_bid_ask_spot(
        self,
    ) -> None:
        """
        Test Python script call for Bid-Ask spot data type.
        """
        # Get query to create the `ccxt_bid_ask_raw` database.
        query = imvccdbut.get_ccxt_create_bid_ask_raw_table_query()
        # Get downloaded data.
        data = self._test_websocket_data_download(
            "bid_ask",
            "spot",
            "ccxt_bid_ask_spot_raw",
            query,
        )
        # Check downloaded data.
        actual = hpandas.df_to_str(data, num_rows=None)
        self.check_string(actual, fuzzy_match=True)

    @pytest.mark.slow("~10 seconds.")
    def test_download_websocket_bid_ask_futures(
        self,
    ) -> None:
        """
        Test Python script call for Bid-Ask futures data type.
        """
        # Get query to create the `ccxt_bid_ask_futures_raw` database.
        query = imvccdbut.get_ccxt_create_bid_ask_futures_raw_table_query()
        # Get downloaded data.
        data = self._test_websocket_data_download(
            "bid_ask",
            "futures",
            "ccxt_bid_ask_futures_raw",
            query,
        )
        # Check downloaded data.
        actual = hpandas.df_to_str(data, num_rows=None)
        self.check_string(actual, fuzzy_match=True)

    @staticmethod
    def _get_argument_parser(
        data_type: str, contract_type: str, db_table: str
    ) -> argparse.ArgumentParser:
        """
        Prepare inputs for the script call.
        """
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Amount of downloads depends on the start time and stop time.
        current_time = datetime.datetime.now()
        start_time = current_time + datetime.timedelta(minutes=0, seconds=6)
        stop_time = current_time + datetime.timedelta(minutes=0, seconds=10)
        kwargs = {
            "data_type": data_type,
            "exchange_id": "binance",
            "universe": "v7.3",
            "db_stage": "test",
            "contract_type": contract_type,
            "vendor": "ccxt",
            "db_table": db_table,
            "aws_profile": "ck",
            "start_time": f"{start_time}",
            "stop_time": f"{stop_time}",
            "method": "websocket",
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_200ms",
            "data_format": "postgres",
            "log_level": "INFO",
            "websocket_data_buffer_size": None,
            "db_saving_mode": "on_buffer_full",
            "bid_ask_depth": 10,
            "ohlcv_download_method": "from_exchange",
        }
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        return mock_argument_parser

    @staticmethod
    def _get_ohlcvs_periodical_data(
        contract_type: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get mock data for the OHLCV method.

        Currency pairs of `spot` and `futures` data have different formatting:
          - spot: "ETH/USDT"
          - futures: "ETH/USDT:USDT"

        :param data_type: "spot" or "futures"
        :return: mock data
        """
        hdbg.dassert_in(
            contract_type,
            ["futures", "spot"],
            msg="Supported contract types: spot, futures",
        )
        # Add a postfix to the currency pair if it is not spot data.
        if contract_type == "spot":
            postfix = ""
        else:
            postfix = ":USDT"
        data = {
            f"ETH/USDT": {
                "1m": [
                    [1695120600000, 1645.08, 1645.23, 1643.83, 1643.97, 1584.649]
                ]
            },
            f"BTC/USDT": {
                "1m": [
                    [1695120600000, 27142.4, 27145.8, 27107.2, 27116.7, 641.342]
                ]
            },
            f"SAND/USDT": {
                "1m": [
                    [1695120600000, 0.303, 0.3031, 0.3028, 0.3028, 142502.0],
                ]
            },
            f"STORJ/USDT": {
                "1m": [[1695120600000, 0.4224, 0.4228, 0.4212, 0.4213, 928841.0]]
            },
            f"GMT/USDT": {
                "1m": [[1695120600000, 0.1566, 0.1566, 0.1564, 0.1564, 127564.0]]
            },
            f"AVAX/USDT": {
                "1m": [[1695120600000, 9.226, 9.227, 9.219, 9.219, 2601.0]]
            },
            f"BNB/USDT": {
                "1m": [[1695120600000, 218.35, 218.37, 218.12, 218.15, 494.27]]
            },
            f"APE/USDT": {
                "1m": [[1695120600000, 1.159, 1.159, 1.157, 1.158, 127432.0]]
            },
            f"MATIC/USDT": {
                "1m": [[1695120600000, 0.5365, 0.5365, 0.5359, 0.5361, 266908.0]]
            },
            f"DYDX/USDT": {
                "1m": [[1695120600000, 1.97, 1.97, 1.968, 1.968, 5387.8]]
            },
            f"DOT/USDT": {
                "1m": [[1695120660000, 4.126, 4.127, 4.123, 4.125, 26169.3]]
            },
            f"UNFI/USDT": {
                "1m": [[1695120660000, 7.748, 7.75, 7.745, 7.749, 1715.3]]
            },
            f"LINK/USDT": {
                "1m": [[1695120660000, 6.714, 6.717, 6.711, 6.716, 18893.91]]
            },
            f"XRP/USDT": {
                "1m": [[1695120660000, 0.5077, 0.5079, 0.5075, 0.5077, 838320.1]]
            },
            f"CRV/USDT": {
                "1m": [[1695120660000, 0.448, 0.448, 0.447, 0.447, 201250.0]]
            },
            f"RUNE/USDT": {
                "1m": [[1695120660000, 1.92, 1.921, 1.919, 1.919, 56577.0]]
            },
            f"BAKE/USDT": {
                "1m": [[1695120660000, 0.1266, 0.1268, 0.1266, 0.1267, 277760.0]]
            },
            f"NEAR/USDT": {
                "1m": [[1695120660000, 1.117, 1.118, 1.117, 1.117, 20889.0]]
            },
            f"FTM/USDT": {
                "1m": [[1695120660000, 0.1933, 0.1934, 0.1933, 0.1934, 128310.0]]
            },
            f"WAVES/USDT": {
                "1m": [[1695120660000, 1.5621, 1.5626, 1.561, 1.5616, 9133.3]]
            },
            f"AXS/USDT": {
                "1m": [[1695120660000, 4.592, 4.593, 4.59, 4.591, 4488.0]]
            },
            f"OGN/USDT": {
                "1m": [[1695120660000, 0.0957, 0.0957, 0.0956, 0.0956, 973721.0]]
            },
            f"DOGE/USDT": {
                "1m": [
                    [1695120660000, 0.06256, 0.06256, 0.06252, 0.06255, 5306066.0]
                ]
            },
            f"SOL/USDT": {
                "1m": [[1695120660000, 20.146, 20.151, 20.136, 20.145, 26187.0]]
            },
            f"CTK/USDT": {
                "1m": [[1695120660000, 0.462, 0.462, 0.4617, 0.4619, 1372.0]]
            },
        }
        processed_data = {
            f"{symbol}{postfix}": values for symbol, values in data.items()
        }
        return processed_data

    @staticmethod
    def _get_bidask_periodical_data() -> Dict[str, Any]:
        """
        Mock data for the Bid-Ask method.

        :return: mock data
        """
        mocked_orderbooks_data = {
            "NEAR/USDT": {
                "bids": [
                    [1.096, 2541.6],
                    [1.095, 60756.0],
                ],
                "asks": [
                    [1.097, 10433.9],
                    [1.098, 13874.2],
                ],
                "timestamp": 1695817653495,
                "datetime": "2023-09-27T12:27:33.495Z",
                "nonce": 3826684538,
                "symbol": "NEAR/USDT",
            },
            "FTM/USDT": {
                "bids": [
                    [0.1902, 102755.0],
                    [0.1901, 62012.0],
                ],
                "asks": [
                    [0.1903, 50233.0],
                    [0.1904, 34190.0],
                ],
                "timestamp": 1695817653395,
                "datetime": "2023-09-27T12:27:33.395Z",
                "nonce": 4877550809,
                "symbol": "FTM/USDT",
            },
            "WAVES/USDT": {
                "bids": [
                    [1.535, 6385.39],
                    [1.534, 9803.58],
                ],
                "asks": [
                    [1.536, 3745.47],
                    [1.537, 5674.78],
                ],
                "timestamp": 1695817653495,
                "datetime": "2023-09-27T12:27:33.495Z",
                "nonce": 2628989232,
                "symbol": "WAVES/USDT",
            },
        }
        # Create a dictionary with the same structure but with each entry being a Mock object
        # with a `limit()` method returning the corresponding original entry.
        # We need this because the ccxtpro library uses the `limit()` method to get the data.
        mocked_orderbooks = {}
        for pair, data in mocked_orderbooks_data.items():
            mock_orderbook = umock.Mock(
                limit=umock.Mock(return_value=data), **data
            )
            mocked_orderbooks[pair] = mock_orderbook
        return mocked_orderbooks

    def _test_websocket_data_download(
        self,
        data_type: str,
        contract_type: str,
        db_name: str,
        create_db_query: str,
    ) -> pd.DataFrame:
        """
        Test data download.

        :param data_type: "ohlcv" or "bid_ask"
        :param contract_type: "spot" or "futures"
        :param db_name: name of the database
        :param create_db_query: query to create the database
        :param mock_get_connection: mock for the `get_connection` function
        :return: downloaded data
        """
        # Tests use special connection params, so we mock the module function.
        # mock_get_connection.return_value = self.connection
        # Set a side effects. for the instantiation of the binance class.
        mock_instance = umock.AsyncMock()
        mock_instance.describe = umock.MagicMock(return_value={"has": {}})
        mock_instance.sleep = lambda *args, **kwargs: asyncio.sleep(1)
        if data_type == "ohlcv":
            mock_instance.watchOHLCV = umock.AsyncMock(return_value=None)
            data = self._get_ohlcvs_periodical_data(contract_type=contract_type)
            # Test `_is_fresh_data_point()`.
            for curr_pair, ohlcv in data.items():
                # data_point = [timestamp, o, h, l, c, v]
                data_point = data[curr_pair]["1m"][0]
                # Add data with same timestamp.
                data[curr_pair]["1m"].append(data_point)
                # Add data with new timestamp.
                new_data_point = data_point.copy()
                # Random timestamp.
                new_data_point[0] += 1000
                data[curr_pair]["1m"].append(new_data_point)
            mock_instance.ohlcvs = data
        else:
            mock_instance.watchOrderBook = umock.AsyncMock(return_value=None)
            mock_instance.orderbooks = self._get_bidask_periodical_data()
        self.mock_binance_class.return_value = mock_instance
        # Create the database.
        cursor = self.connection.cursor()
        cursor.execute(create_db_query)
        # Prepare inputs.
        mock_argument_parser = self._get_argument_parser(
            data_type, contract_type, db_name
        )
        # Run the sctipt.
        imvcdededtdp._main(mock_argument_parser)
        # Get downloaded data.
        get_data_query = f"SELECT * FROM {db_name};"
        data = hsql.execute_query_to_df(self.connection, get_data_query)
        return data


class TestDownloadRealtimeForOneExchangePeriodically2(hunitest.TestCase):
    """
    Test if argument `websocket_data_buffer_size` overrides the global variable
    `WEBSOCKET_CONFIG[data_type]["max_buffer_size"]` correctly.
    """

    def test1(self) -> None:
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Amount of downloads depends on the start time and stop time.
        current_time = datetime.datetime.now()
        start_time = current_time + datetime.timedelta(minutes=0, seconds=6)
        stop_time = current_time + datetime.timedelta(minutes=0, seconds=8)
        expected_buffer_size = 30
        kwargs = {
            "data_type": "ohlcv",
            "exchange_id": "binance",
            "universe": "v7.3",
            "db_stage": "test",
            "contract_type": "futures",
            "vendor": "ccxt",
            "db_table": "ccxt_ohlcv_futures",
            "aws_profile": "ck",
            "start_time": f"{start_time}",
            "stop_time": f"{stop_time}",
            "method": "websocket",
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_200ms",
            "data_format": "postgres",
            "log_level": "INFO",
            "websocket_data_buffer_size": expected_buffer_size,
            "db_saving_mode": "on_buffer_full",
            "ohlcv_download_method": "from_exchange",
        }
        # Run.
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace

        with umock.patch.object(
            imvcdededtdp.imvcdeexut,
            "download_realtime_for_one_exchange_periodically",
            return_value=[],
        ):
            with umock.patch.object(
                imvcdededtdp.imvcdeexut.imvcdexex, "CcxtExtractor"
            ) as mock_ccxt_extractor:
                # Mock the `close()` method of CcxtExtractor
                mock_ccxt_extractor_instance = mock_ccxt_extractor.return_value
                mock_ccxt_extractor_instance.close = umock.MagicMock()
                # Run.
                imvcdededtdp._main(mock_argument_parser)
                actual_buffer_size = imvcdededtdp.imvcdeexut.WEBSOCKET_CONFIG[
                    "ohlcv"
                ]["max_buffer_size"]
        # Check output.
        self.assertEqual(actual_buffer_size, expected_buffer_size)


class TestDownloadRealtimeForOneExchangePeriodically3(
    imvcddbut.TestImDbHelper, hunitest.TestCase
):
    """
    Test to verify unfinished data in OHLCV is handled correctly by
    `_is_fresh_data_point()`.
    """

    # Mock calls to external provider.
    ccxt_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcdexex,
        "ccxt",
        spec=imvcdededtdp.imvcdeexut.imvcdexex.ccxt,
    )
    get_current_time_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcdexex.hdateti,
        "get_current_time",
        return_value=pd.Timestamp("2023-09-26 16:04:10+00:00"),
    )
    db_connection_patch = umock.patch.object(
        imvcdededtdp.imvcdeexut.imvcddbut.DbConnectionManager, "get_connection"
    )

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Add an isolated events loop.
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Activate mock for `ccxt`.
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        # Mock the binance ccxt to return load market keys, they don't need to be real.
        self.ccxt_mock.binance.return_value.load_markets.return_value.keys.return_value = [
            "MOCKBTC/MOCKUSD"
        ]
        self.get_current_time_mock = self.get_current_time_patch.start()
        self.mock_get_connection = self.db_connection_patch.start()
        self.mock_get_connection.return_value = self.connection

    def tear_down_test(self) -> None:
        self.ccxt_patch.stop()
        self.get_current_time_patch.stop()
        self.db_connection_patch.stop()
        self.loop.close()

    @pytest.mark.slow("~10 seconds.")
    def test1(self) -> None:
        # Prepare inputs.
        mock_argument_parser = umock.create_autospec(
            argparse.ArgumentParser, spec_set=True
        )
        # Amount of downloads depends on the start time and stop time.
        current_time = datetime.datetime.now()
        start_time = current_time + datetime.timedelta(minutes=0, seconds=8)
        stop_time = current_time + datetime.timedelta(minutes=0, seconds=10)
        kwargs = {
            "data_type": "ohlcv",
            "exchange_id": "binance",
            "universe": "v7.3",
            "db_stage": "test",
            "contract_type": "futures",
            "vendor": "ccxt",
            "db_table": "ccxt_ohlcv_futures",
            "aws_profile": "ck",
            "start_time": f"{start_time}",
            "stop_time": f"{stop_time}",
            "method": "websocket",
            "download_mode": "realtime",
            "downloading_entity": "manual",
            "action_tag": "downloaded_200ms",
            "data_format": "postgres",
            "log_level": "INFO",
            "websocket_data_buffer_size": 0,
            "db_saving_mode": "on_buffer_full",
            "ohlcv_download_method": "from_exchange",
        }
        # Create argparser.
        namespace = argparse.Namespace(**kwargs)
        mock_argument_parser.parse_args.return_value = namespace
        # Create input data.
        timestamp = 1695120600000
        data = [
            {
                "1m": [[timestamp, 1645.08, 1645.23, 1643.83, 1643.97, 1584.649]],
                "ohlcv": [
                    [timestamp, 1645.08, 1645.23, 1643.83, 1643.97, 1584.649]
                ],
                "currency_pair": "ETH/USDT:USDT",
                # This data point is unfinished as end download timestamp
                # < timestamp + 1T (60000ms).
                "end_download_timestamp": hdateti.convert_unix_epoch_to_timestamp(
                    timestamp + 1000
                ),
            },
            {
                "1m": [[timestamp, 1645.08, 1645.23, 1643.83, 1643.97, 1584.649]],
                "ohlcv": [
                    [timestamp, 1645.08, 1645.23, 1643.83, 1643.97, 1584.649]
                ],
                "currency_pair": "ETH/USDT:USDT",
                # This data point is complete as end download timestamp
                # >= timestamp + 1T (60000ms).
                "end_download_timestamp": hdateti.convert_unix_epoch_to_timestamp(
                    timestamp + 60000
                ),
            },
        ]
        create_db_query = imvccdbut.get_ccxt_ohlcv_futures_create_table_query()
        # Create the database.
        cursor = self.connection.cursor()
        cursor.execute(create_db_query)
        # Run.
        with umock.patch.object(
            imvcdededtdp.imvcdeexut.imvcdexex.CcxtExtractor,
            "download_websocket_data",
            return_value=[],
            side_effect=data,
        ):
            with umock.patch.object(
                imvcdededtdp.imvcdeexut.ivcu,
                "get_vendor_universe",
                return_value={"binance": ["ETH_USDT"]},
            ):
                with umock.patch.object(
                    imvcdededtdp.imvcdeexut.imvcdexex.CcxtExtractor,
                    "subscribe_to_websocket_data",
                    new_callable=umock.AsyncMock,
                ):
                    # Mock waiting time to speed up test.
                    imvcdededtdp.imvcdeexut.WEBSOCKET_CONFIG["ohlcv"][
                        "sleep_between_iter_in_ms"
                    ] = 1000
                    imvcdededtdp._main(mock_argument_parser)
                    # Get downloaded data.
                    get_data_query = f"SELECT * FROM ccxt_ohlcv_futures;"
                    data = hsql.execute_query_to_df(
                        self.connection, get_data_query
                    )
        # Check output.
        expected = r"""
                       id      timestamp     open     high      low    close    volume  currency_pair exchange_id    end_download_timestamp        knowledge_timestamp
                    0   1  1695120600000  1645.08  1645.23  1643.83  1643.97  1584.649  ETH_USDT:USDT     binance 2023-09-19 10:51:00+00:00  2023-09-26 16:04:10+00:00
                """
        actual = hpandas.df_to_str(data, num_rows=None)
        self.assert_equal(actual, expected, fuzzy_match=True)
