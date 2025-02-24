import asyncio
import json
import logging
import os
import pprint
import unittest.mock as umock
from typing import Dict, List, Union

import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import market_data.market_data_example as mdmadaex
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.broker.ccxt.mock_ccxt_exchange as obcmccex
import oms.broker.ccxt.replayed_ccxt_exchange as obcrccex
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.broker.replayed_data_reader as obredare

_LOG = logging.getLogger(__name__)

_DUMMY_MARKET_INFO = {
    1464553467: {"amount_precision": 3, "max_leverage": 1},
    1467591036: {"amount_precision": 3, "max_leverage": 1},
    6051632686: {"amount_precision": 3, "max_leverage": 1},
    4516629366: {"amount_precision": 3, "max_leverage": 1},
}


class TestReplayedCcxtExchange1(hunitest.TestCase):
    """
    Test suite for the `ReplayedCcxtExchange` class functions.
    """

    def get_ccxt_orders(self) -> List[obcmccex.CcxtOrderStructure]:
        ccxt_orders = []
        # The following path consists of CCXT child order
        # JSON file logged during a simple experiment:
        # > oms/broker/ccxt/scripts/run_ccxt_broker.py \
        # > --log_dir tmp_log_dir \
        # > --max_parent_order_notional 10 \
        # > --randomize_orders \
        # > --parent_order_duration_in_min 1 \
        # > --num_bars 1 \
        # > --num_parent_orders_per_bar 1 \
        # > --secret_id 3 \
        # > --clean_up_before_run \
        # > --clean_up_after_run \
        # > --passivity_factor 0.55 \
        # > --child_order_execution_freq 1T \
        # > -v DEBUG
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        file_name = os.path.join(
            s3_input_dir, "1467591036_20230918_155000.20230918-115003.json"
        )
        aws_profile = "ck"
        s3fs = hs3.get_s3fs(aws_profile)
        with s3fs.open(file_name) as json_file:
            ccxt_orders.append(json.load(json_file))
        return ccxt_orders

    def create_order_helper(
        self,
        ccxt_orders: List[obcmccex.CcxtOrderStructure],
        symbol: str,
        type: str,
        amount: float,
        price: float,
        side: str,
        expected: str,
        fill_percents: Union[float, List[float]],
    ) -> None:
        """
        Build `ReplayedCcxtExchange` and call create_order function.
        """
        # Build `ReplayedCcxtExchange`.
        ccxt_fill_list = []
        ccxt_trades_list = []
        exchange_markets = None
        leverage_info = None
        reduce_only_ccxt_orders = []
        positions = None
        balances = None
        delay_in_secs = 0
        event_loop = None
        get_wall_clock_time = None
        replayed_ccxt_exchange = obcrccex.ReplayedCcxtExchange(
            ccxt_orders,
            ccxt_fill_list,
            ccxt_trades_list,
            exchange_markets,
            leverage_info,
            reduce_only_ccxt_orders,
            positions,
            balances,
            delay_in_secs,
            event_loop,
            get_wall_clock_time,
            fill_percents,
        )
        # Run `create_order()`.
        with self.assertRaises(AssertionError) as fail:
            asyncio.run(
                replayed_ccxt_exchange.create_order(
                    symbol,
                    type,
                    amount,
                    price,
                    side,
                )
            )
        # Check result.
        actual_error = str(fail.exception)
        self.assert_equal(actual_error, expected, fuzzy_match=True)

    def test_create_order1(self) -> None:
        """
        Check proper return of Orders.
        """
        # Build `ReplayedCcxtExchange`.
        ccxt_orders = self.get_ccxt_orders()
        ccxt_fill_list = []
        ccxt_trades_list = []
        exchange_markets = None
        leverage_info = None
        reduce_only_ccxt_orders = []
        positions = None
        balances = None
        delay_in_secs = 0
        event_loop = None
        get_wall_clock_time = None
        fill_percents = [1.0]
        replayed_ccxt_exchange = obcrccex.ReplayedCcxtExchange(
            ccxt_orders,
            ccxt_fill_list,
            ccxt_trades_list,
            exchange_markets,
            leverage_info,
            reduce_only_ccxt_orders,
            positions,
            balances,
            delay_in_secs,
            event_loop,
            get_wall_clock_time,
            fill_percents,
        )
        # Run `create_order()`.
        symbol = "BTC/USDT:USDT"
        type = "limit"
        amount = 0.008
        price = 27269.3
        side = "sell"
        actual = asyncio.run(
            replayed_ccxt_exchange.create_order(
                symbol,
                type,
                amount,
                price,
                side,
            )
        )
        # Check result.
        actual_string = pprint.pformat(actual)
        expected = r"""
        {'amount': 0.008,
        'average': 27272.4,
        'clientOrderId': 'x-xcKtGhcu5f42d11066594a19a432cd',
        'cost': 218.1792,
        'datetime': '2023-09-18T15:50:03.808Z',
        'fee': {'cost': None, 'currency': None, 'rate': None},
        'fees': [{'py/id': 2}],
        'filled': 0.008,
        'id': '190884912635',
        'info': {'avgPrice': '27272.40000',
                'clientOrderId': 'x-xcKtGhcu5f42d11066594a19a432cd',
                'closePosition': False,
                'cumQty': '0.008',
                'cumQuote': '218.17920',
                'executedQty': '0.008',
                'goodTillDate': '0',
                'orderId': '190884912635',
                'origQty': '0.008',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '27269.30',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'SELL',
                'status': 'FILLED',
                'stopPrice': '0.00',
                'symbol': 'BTCUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1695052203808',
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': 1695052203808,
        'lastUpdateTimestamp': 1695052203808,
        'postOnly': False,
        'price': 27269.3,
        'reduceOnly': False,
        'remaining': 0.0,
        'side': 'sell',
        'status': 'closed',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'BTC/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1695052203808,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'}
        """
        self.assert_equal(actual_string, expected, fuzzy_match=True)

    def test_create_order2(self) -> None:
        """
        Check that error is raised when empty order log is passed.
        """
        expected = r"""
        ################################################################################
        * Failed assertion *
        '0'
        !=
        '0'
        Log order data is empty
        ################################################################################
        """
        ccxt_orders = []
        symbol = "BTC/USDT:USDT"
        order_type = "limit"
        amount = 0.008
        price = 27269.3
        side = "sell"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )

    def test_create_order3(self) -> None:
        """
        Check that error is raised when arguments that does not match data are
        passed.
        """
        # Check for wrong symbol.
        expected = r"""
        symbol: mock not present in log data
        """
        ccxt_orders = self.get_ccxt_orders()
        symbol = "mock"
        order_type = "limit"
        amount = 0.008
        price = 27269.3
        side = "sell"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )

    def test_create_order4(self) -> None:
        """
        Check that error is raised when arguments that does not match data are
        passed.
        """
        # Check for wrong amount.
        expected = r"""
        The following arguments do not match with log data: ['amount']
        """
        ccxt_orders = self.get_ccxt_orders()
        symbol = "BTC/USDT:USDT"
        order_type = "limit"
        amount = 100
        price = 27269.3
        side = "sell"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )

    def test_create_order5(self) -> None:
        """
        Check that error is raised when arguments that does not match data are
        passed.
        """
        # Check for wrong price.
        expected = r"""
        The following arguments do not match with log data: ['price']
        """
        ccxt_orders = self.get_ccxt_orders()
        symbol = "BTC/USDT:USDT"
        order_type = "limit"
        amount = 0.008
        price = 100
        side = "sell"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )

    def test_create_order6(self) -> None:
        """
        Check that error is raised when arguments that does not match data are
        passed.
        """
        # Check for wrong side.
        expected = r"""
        The following arguments do not match with log data: ['side']
        """
        ccxt_orders = self.get_ccxt_orders()
        symbol = "BTC/USDT:USDT"
        order_type = "limit"
        amount = 0.008
        price = 27269.3
        side = "mock_buy"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )

    def test_create_order7(self) -> None:
        """
        Check that error is raised when arguments that does not match data are
        passed.
        """
        # Check for multiple wrong arguments.
        expected = r"""
        The following arguments do not match with log data: ['amount', 'price', 'side']
        """
        ccxt_orders = self.get_ccxt_orders()
        symbol = "BTC/USDT:USDT"
        order_type = "limit"
        amount = 100
        price = 100
        side = "mock_buy"
        fill_percents = [1.0]
        self.create_order_helper(
            ccxt_orders,
            symbol,
            order_type,
            amount,
            price,
            side,
            expected,
            fill_percents,
        )


class TestReplayedCcxtExchange2(hunitest.TestCase):
    """
    Test suite for the `ReplayedCcxtExchange` class functions to handle
    multiple CCXT orders.
    """

    def get_replayed_ccxt_exchange(self) -> obcrccex.ReplayedCcxtExchange:
        """
        Read all the JSON files and add them to the ccxt_orders list and create
        object for class `ReplayedCcxtExchange`.
        """
        orders = []
        # TODO(Sameep): Come up with schema on how to create subdirectories.
        # Download test data from s3 to local system. The following path
        # consists of CCXT child order responses JSON files logged during a
        # simple experiment:
        # > oms/broker/ccxt/scripts/run_ccxt_broker.py \
        # > --log_dir tmp_log_dir \
        # > --max_parent_order_notional 10 \
        # > --randomize_orders \
        # > --parent_order_duration_in_min 1 \
        # > --num_bars 1 \
        # > --num_parent_orders_per_bar 1 \
        # > --secret_id 3 \
        # > --clean_up_before_run \
        # > --clean_up_after_run \
        # > --passivity_factor 0.55 \
        # > --child_order_execution_freq 1T \
        # > -v DEBUG
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        aws_profile = "ck"
        file_list = hs3.listdir(
            s3_input_dir,
            "*.json",
            only_files=False,
            use_relative_paths=True,
            aws_profile=aws_profile,
        )
        json_file_list = sorted(file_list)
        s3fs = hs3.get_s3fs(aws_profile)
        for file in json_file_list:
            file_name = os.path.join(s3_input_dir, file)
            json_file, _ = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
            order = json.load(json_file)
            orders.append(order)
        # Build `ReplayedCcxtExchange`.
        ccxt_orders = orders
        ccxt_fill_list = []
        ccxt_trades_list = []
        exchange_markets = None
        leverage_info = None
        reduce_only_ccxt_orders = []
        positions = None
        balances = None
        delay_in_secs = 0
        event_loop = None
        get_wall_clock_time = None
        fill_percents = [1.0]
        replayed_ccxt_exchange = obcrccex.ReplayedCcxtExchange(
            ccxt_orders,
            ccxt_fill_list,
            ccxt_trades_list,
            exchange_markets,
            leverage_info,
            reduce_only_ccxt_orders,
            positions,
            balances,
            delay_in_secs,
            event_loop,
            get_wall_clock_time,
            fill_percents,
        )
        return replayed_ccxt_exchange

    def test_create_order1(self) -> None:
        """
        Check proper return of Orders in the desired sequence.
        """
        replayed_ccxt_exchange = self.get_replayed_ccxt_exchange()
        symbol = "ETH/USDT:USDT"
        type = "limit"
        amount = 0.005
        price = 1591.74
        side = "buy"
        actual = asyncio.run(
            replayed_ccxt_exchange.create_order(
                symbol,
                type,
                amount,
                price,
                side,
            )
        )
        actual_string = pprint.pformat(actual)
        expected = r"""
        {'amount': 0.005,
        'average': None,
        'clientOrderId': 'x-xcKtGhcu9c0d90dec7aaa96477c2da',
        'cost': 0.0,
        'datetime': '2023-09-25T18:25:04.467Z',
        'fee': {'cost': None, 'currency': None, 'rate': None},
        'fees': [{'py/id': 2}],
        'filled': 0.0,
        'id': '8389765618591816891',
        'info': {'avgPrice': '0.00',
                'clientOrderId': 'x-xcKtGhcu9c0d90dec7aaa96477c2da',
                'closePosition': False,
                'cumQty': '0.000',
                'cumQuote': '0.00000',
                'executedQty': '0.000',
                'goodTillDate': '0',
                'orderId': '8389765618591816891',
                'origQty': '0.005',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '1591.74',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0.00',
                'symbol': 'ETHUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1695666304467',
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'lastUpdateTimestamp': 1695666304467,
        'postOnly': False,
        'price': 1591.74,
        'reduceOnly': False,
        'remaining': 0.005,
        'side': 'buy',
        'status': 'open',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'ETH/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1695666304467,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'}
        """
        self.assert_equal(actual_string, expected, fuzzy_match=True)
        symbol = "ETH/USDT:USDT"
        type = "limit"
        amount = 0.005
        price = 1591.21
        side = "buy"
        actual = asyncio.run(
            replayed_ccxt_exchange.create_order(
                symbol,
                type,
                amount,
                price,
                side,
            )
        )
        actual_string = pprint.pformat(actual)
        expected = r"""
        {'amount': 0.005,
        'average': 1591.21,
        'clientOrderId': 'x-xcKtGhcu4349fe380e4851b0c5f5d0',
        'cost': 7.95605,
        'datetime': '2023-09-25T18:26:01.888Z',
        'fee': {'cost': None, 'currency': None, 'rate': None},
        'fees': [{'py/id': 2}],
        'filled': 0.005,
        'id': '8389765618591889529',
        'info': {'avgPrice': '1591.21000',
                'clientOrderId': 'x-xcKtGhcu4349fe380e4851b0c5f5d0',
                'closePosition': False,
                'cumQty': '0.005',
                'cumQuote': '7.95605',
                'executedQty': '0.005',
                'goodTillDate': '0',
                'orderId': '8389765618591889529',
                'origQty': '0.005',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '1591.21',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'BUY',
                'status': 'FILLED',
                'stopPrice': '0.00',
                'symbol': 'ETHUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1695666361888',
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': 1695666361888,
        'lastUpdateTimestamp': 1695666361888,
        'postOnly': False,
        'price': 1591.21,
        'reduceOnly': False,
        'remaining': 0.0,
        'side': 'buy',
        'status': 'closed',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'ETH/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1695666361888,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'}
        """
        self.assert_equal(actual_string, expected, fuzzy_match=True)
        symbol = "SAND/USDT:USDT"
        type = "limit"
        amount = 21.0
        price = 0.2999
        side = "buy"
        actual = asyncio.run(
            replayed_ccxt_exchange.create_order(
                symbol,
                type,
                amount,
                price,
                side,
            )
        )
        actual_string = pprint.pformat(actual)
        expected = r"""
        {'amount': 21.0,
        'average': None,
        'clientOrderId': 'x-xcKtGhcu2b84d78cee60fcb533c17f',
        'cost': 0.0,
        'datetime': '2023-09-25T18:25:05.198Z',
        'fee': {'cost': None, 'currency': None, 'rate': None},
        'fees': [{'py/id': 2}],
        'filled': 0.0,
        'id': '14193283670',
        'info': {'avgPrice': '0.00',
                'clientOrderId': 'x-xcKtGhcu2b84d78cee60fcb533c17f',
                'closePosition': False,
                'cumQty': '0',
                'cumQuote': '0.00000',
                'executedQty': '0',
                'goodTillDate': '0',
                'orderId': '14193283670',
                'origQty': '21',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '0.29990',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0.00000',
                'symbol': 'SANDUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1695666305198',
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'lastUpdateTimestamp': 1695666305198,
        'postOnly': False,
        'price': 0.2999,
        'reduceOnly': False,
        'remaining': 21.0,
        'side': 'buy',
        'status': 'open',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'SAND/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1695666305198,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'}
        """
        self.assert_equal(actual_string, expected, fuzzy_match=True)

    def test_create_order2(self) -> None:
        """
        Check proper return of Orders in case wrong symbol is provided.
        """
        replayed_ccxt_exchange = self.get_replayed_ccxt_exchange()
        with self.assertRaises(AssertionError) as fail:
            symbol = "BTC/USDT:USDT"
            type = "limit"
            amount = 0.01
            price = 1591.74
            side = "buy"
            asyncio.run(
                replayed_ccxt_exchange.create_order(
                    symbol,
                    type,
                    amount,
                    price,
                    side,
                )
            )
        actual_error = str(fail.exception)
        expected = r"""
        symbol: BTC/USDT:USDT not present in log data
        """
        self.assert_equal(actual_error, expected, fuzzy_match=True)

    def test_create_order3(self) -> None:
        """
        Check proper return of Orders in case the wrong sequence of order is
        invoked.
        """
        replayed_ccxt_exchange = self.get_replayed_ccxt_exchange()
        symbol = "ETH/USDT:USDT"
        type = "limit"
        amount = 0.005
        price = 1591.74
        side = "buy"
        actual = asyncio.run(
            replayed_ccxt_exchange.create_order(
                symbol,
                type,
                amount,
                price,
                side,
            )
        )
        actual_string = pprint.pformat(actual)
        expected = r"""
        {'amount': 0.005,
        'average': None,
        'clientOrderId': 'x-xcKtGhcu9c0d90dec7aaa96477c2da',
        'cost': 0.0,
        'datetime': '2023-09-25T18:25:04.467Z',
        'fee': {'cost': None, 'currency': None, 'rate': None},
        'fees': [{'py/id': 2}],
        'filled': 0.0,
        'id': '8389765618591816891',
        'info': {'avgPrice': '0.00',
                'clientOrderId': 'x-xcKtGhcu9c0d90dec7aaa96477c2da',
                'closePosition': False,
                'cumQty': '0.000',
                'cumQuote': '0.00000',
                'executedQty': '0.000',
                'goodTillDate': '0',
                'orderId': '8389765618591816891',
                'origQty': '0.005',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '1591.74',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0.00',
                'symbol': 'ETHUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1695666304467',
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'lastUpdateTimestamp': 1695666304467,
        'postOnly': False,
        'price': 1591.74,
        'reduceOnly': False,
        'remaining': 0.005,
        'side': 'buy',
        'status': 'open',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'ETH/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1695666304467,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'}
        """
        self.assert_equal(actual_string, expected, fuzzy_match=True)
        with self.assertRaises(AssertionError) as fail:
            symbol = "ETH/USDT:USDT"
            type = "limit"
            amount = 0.01
            price = 1591.21
            side = "buy"
            asyncio.run(
                replayed_ccxt_exchange.create_order(
                    symbol,
                    type,
                    amount,
                    price,
                    side,
                )
            )
        actual_error = str(fail.exception)
        expected = r"""
        The following arguments do not match with log data: ['amount']
        """
        self.assert_equal(actual_error, expected, fuzzy_match=True)


class TestReplayedCcxtExchange3(hunitest.TestCase):
    """
    Test suite for the `ReplayedCcxtExchange` class functions to handle
    `submit_twap_orders` with `ReplayedDataReader`.
    """

    def get_test_data(self) -> Dict:
        """
        Load test data using helper functions from `CcxtLogger`.
        """
        # Download test data from s3 to local system. The following path
        # consists of all the log files logged during an experiment.
        # Following are the parameters used while running  and logging the
        # experiment:
        # > oms/broker/ccxt/scripts/run_ccxt_broker.py \
        # > --log_dir /shared_data/sameep/log_test/log \
        # > --max_parent_order_notional 10 \
        # > --randomize_orders \
        # > --parent_order_duration_in_min 5 \
        # > --num_bars 2 \
        # > --num_parent_orders_per_bar 2 \
        # > --secret_id 3 \
        # > --clean_up_before_run \
        # > --clean_up_after_run \
        # > --passivity_factor 0.55 \
        # > --child_order_execution_freq 1T \
        # > -v DEBUG
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        s3_log_dir = os.path.join(s3_input_dir, "logs")
        scratch_dir = self.get_scratch_space()
        aws_profile = "ck"
        hs3.copy_data_from_s3_to_local_dir(s3_log_dir, scratch_dir, aws_profile)
        # Load test data using `Ccxtlogger` load functions.
        log_reader = obcccclo.CcxtLogger(scratch_dir)
        log_data = log_reader.load_all_data(
            convert_to_dataframe=False, abort_on_missing_data=False
        )
        return log_data

    @pytest.mark.slow("8 seconds.")
    @umock.patch.object(
        obccbrin.icdcl,
        "get_CcxtSqlRealTimeImClient_example1",
        autospec=True,
        spec_set=True,
    )
    @umock.patch.object(
        obccbrin.obccccut, "create_ccxt_exchanges", autospec=True, spec_set=True
    )
    @umock.patch.object(
        obccbrin.imvcdcimrdc,
        "get_bid_ask_realtime_raw_data_reader",
        autospec=True,
        spec_set=True,
    )
    @umock.patch.object(
        obccbrin.dtfamsysc,
        "get_Cx_RealTimeMarketData_prod_instance2",
        autospec=True,
        spec_set=True,
    )
    def test_submit_twap_orders1(
        self,
        mock_market_data: umock.MagicMock,
        mock_get_bid_ask_realtime_raw_data_reader: umock.MagicMock,
        mock_create_ccxt_exchanges: umock.MagicMock,
        mock_im_client: umock.MagicMock,
    ) -> None:
        """
        Check compatibility with broker using `submit_twap_orders` with
        `ReplayedDataReader`.
        """
        log_data = self.get_test_data()
        parent_orders = obccccut.create_parent_orders_from_json(
            log_data["oms_parent_orders"], 2, update_time=False
        )
        secret_id = 3
        scratch_dir = self.get_scratch_space()
        log_dir = os.path.join(scratch_dir, "mock", "log")
        universe = "v7.4"
        creation_timestamp = parent_orders[0].creation_timestamp
        with hasynci.solipsism_context() as event_loop:
            num_minutes = 5
            # The second element in the returned tuple is a callable.
            (
                market_data,
                get_wall_clock_time,
            ) = mdmadaex.get_ReplayedTimeMarketData_example2(
                event_loop,
                # For solipsism to work correctly it is important to set the correct time interval.
                creation_timestamp,
                creation_timestamp + pd.Timedelta(minutes=num_minutes),
                0,
                list(obcttcut._ASSET_ID_SYMBOL_MAPPING.keys()),
            )
            # Build `ReplayedCcxtExchange`.
            replayed_ccxt_exchange = obcrccex.ReplayedCcxtExchange(
                ccxt_orders=log_data["ccxt_order_responses"],
                ccxt_fill_list=log_data["ccxt_fills"],
                ccxt_trades_list=log_data["ccxt_trades"],
                exchange_markets=log_data["exchange_markets"],
                leverage_info=log_data["leverage_info"],
                reduce_only_ccxt_orders=log_data["reduce_only_order_responses"],
                positions=log_data["positions"],
                balances=log_data["balances"],
                delay_in_secs=1,
                event_loop=event_loop,
                get_wall_clock_time=get_wall_clock_time,
                fill_percents=[1.0],
            )
            # Initializing mock data.
            mock_create_ccxt_exchanges.return_value = (
                replayed_ccxt_exchange,
                replayed_ccxt_exchange,
            )
            mock_get_bid_ask_realtime_raw_data_reader.return_value = (
                obredare.ReplayDataReader(
                    log_data["bid_ask_files"],
                )
            )
            mock_market_data.return_value = market_data
            mock_im_client.return_value = None
            broker_config = {
                "limit_price_computer_type": "LimitPriceComputerUsingVolatility",
                "limit_price_computer_kwargs": {
                    "volatility_multiple": [0.75, 0.7, 0.6, 0.8, 1.0]
                },
            }
            broker = obccbrin.get_CcxtBroker(
                secret_id,
                log_dir,
                universe,
                broker_config,
            )
            coroutine = broker._submit_twap_orders(
                # Selecting the first two twap parent orders
                parent_orders[:2],
                execution_freq="1T",
            )
            orders = hasynci.run(coroutine, event_loop=event_loop)
