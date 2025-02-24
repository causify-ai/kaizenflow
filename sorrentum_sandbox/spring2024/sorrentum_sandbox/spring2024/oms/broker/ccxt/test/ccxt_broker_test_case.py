"""
Import as:

import oms.broker.ccxt.test.ccxt_broker_test_case as obccbteca
"""
import abc
import asyncio
import logging
import os
import pprint
import re
import unittest.mock as umock
from typing import Any, Dict, List, Optional, Type

import ccxt
import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu
import market_data as mdata
import oms.broker.broker as obrobrok
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.fill as omfill
import oms.hsecrets.secret_identifier as ohsseide
import oms.limit_price_computer as oliprcom
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# #############################################################################
# Generate Fills and Orders
# #############################################################################


def _get_test_order(order_type: str) -> List[oordorde.Order]:
    """
    Build toy list of 1 order for tests.
    """
    # Prepare test data.
    order_str = f"Order: order_id=0 creation_timestamp=2022-08-05 10:36:44.976104-04:00\
    asset_id=1464553467 type_={order_type} start_timestamp=2022-08-05 10:36:44.976104-04:00\
    end_timestamp=2022-08-05 10:38:44.976104-04:00 curr_num_shares=0.0 diff_num_shares=0.121"
    order_str += " tz=America/New_York extra_params={}"
    # Get orders.
    orders = oordorde.orders_from_string(order_str)
    return orders


def _get_child_order_response():
    """
    Corresponds to `orders[0]` from `get_test_orders`.
    """
    child_order_response = {
        "info": {
            "orderId": "7954906695",
            "symbol": "ETHUSDT",
            "status": "NEW",
            "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
            "price": "1780.0",
            "avgPrice": "1780.70000",
            "origQty": "0.06",
            "executedQty": "0.06",
            "cumQty": "0.06",
            "cumQuote": "48.07890",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "reduceOnly": False,
            "closePosition": False,
            "side": "BUY",
            "positionSide": "BOTH",
            "stopPrice": "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": "LIMIT",
            "updateTime": "1680207361629",
        },
        "id": "7954906695",
        "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
        "timestamp": 1680207361629,
        "datetime": "2023-03-15T16:35:38.582Z",
        "lastTradeTimestamp": None,
        "symbol": "ETH/USDT:USDT",
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "side": "buy",
        "price": 1780.0,
        "stopPrice": None,
        "amount": 0.06,
        "cost": 106.8,
        "average": 1780.7,
        "filled": 0.0,
        "remaining": 0.06,
        "status": "open",
        "fee": None,
        "trades": [],
        "fees": [],
    }
    return child_order_response


def _get_test_order_fills1() -> List[oordorde.Order]:
    """
    Get CCXT order structures for child orders associated with
    `_get_test_order`.
    """
    fills = [
        {
            "info": {
                "orderId": "8389765589152377439",
                "symbol": "ETHUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "price": "1780.0",
                "avgPrice": "1780.70000",
                "origQty": "0.06",
                "executedQty": "0.06",
                "cumQty": "0.06",
                "cumQuote": "48.07890",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": "",
                "closePosition": "",
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": "",
                "origType": "LIMIT",
                "updateTime": "1680207361629",
            },
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT:USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "buy",
            "price": 1780.0,
            "stopPrice": "",
            "amount": 0.06,
            "cost": 106.8,
            "average": 1780.7,
            "filled": 0.06,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
        {
            "info": {
                "orderId": "8389765589152377439",
                "symbol": "ETHUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "price": "1770.10",
                "avgPrice": "1770.70000",
                "origQty": "0.06",
                "executedQty": "0.06",
                "cumQty": "0.06",
                "cumQuote": "48.07890",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": "",
                "closePosition": "",
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": "",
                "origType": "LIMIT",
                "updateTime": "1680207361629",
            },
            "id": "8389765589152377439",
            "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
            "timestamp": "",
            "datetime": "",
            "lastTradeTimestamp": "",
            "symbol": "ETH/USDT:USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": "",
            "reduceOnly": "",
            "side": "buy",
            "price": 1770.0,
            "stopPrice": "",
            "amount": 0.06,
            "cost": 106.2,
            "average": 1770.7,
            "filled": 0.06,
            "remaining": 0.0,
            "status": "closed",
            "fee": "",
            "trades": [],
            "fees": [],
        },
    ]
    return fills


# #############################################################################
# TestCcxtBroker_TestCase
# #############################################################################


class TestCcxtBroker_TestCase(hunitest.TestCase, abc.ABC):
    # Mock calls to external objects (i.e., AWS, CCXT).
    # Since CCXT is imported twice in the abstract class and in
    # child class, it is required to be mocked twice: for uses in abstract
    # class, and for child class uses.
    get_secret_patch = umock.patch.object(obccccut.hsecret, "get_secret")
    abstract_ccxt_patch = umock.patch.object(obccccut, "ccxt", spec=obccccut.ccxt)
    abstract_ccxtpro_patch = umock.patch.object(
        obccccut, "ccxtpro", spec=obccccut.ccxtpro
    )
    mock_timestamp_to_str_patch = umock.patch.object(
        obcccclo.hdateti, "timestamp_to_str", autospec=True, spec_set=True
    )

    # Ensure we can pass class name to the hunitest.TestCase
    # to obtain the correct path to golden outcome, avoid repetitively
    # copying goldens for multiple child classes.
    @staticmethod
    def get_class_name() -> str:
        return "TestCcxtBroker_TestCase"

    @staticmethod
    def reset() -> None:
        omfill.Fill._fill_id = 0
        oordorde.Order._order_id = 0
        obrobrok.Broker._submitted_order_id = 0

    def get_broker_class(self) -> Type[obcaccbr.AbstractCcxtBroker]:
        """
        Return class used to instantiate CCXT Broker.
        """
        return obccccbr.CcxtBroker

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Create new mocks from patch's `start()` method.
        self.get_secret_mock: umock.MagicMock = self.get_secret_patch.start()
        # The order initialization matters here -> since ccxt.pro is included in ccxt
        #  it needs to go first.
        self.abstract_ccxtpro_mock: umock.MagicMock = (
            self.abstract_ccxtpro_patch.start()
        )
        self.abstract_ccxt_mock: umock.MagicMock = (
            self.abstract_ccxt_patch.start()
        )
        self.mock_timestamp_to_str: umock.MagicMock = (
            self.mock_timestamp_to_str_patch.start()
        )
        # Return random timestamp for logging by mocking.
        self.mock_timestamp_to_str.return_value = pd.Timestamp(
            "2022-08-05 09:30:55+00:00"
        )
        # Set dummy credentials for all tests.
        self.get_secret_mock.return_value = {"apiKey": "test", "secret": "test"}
        # Reset static variables on each test run.
        self.reset()

    def tear_down_test(self) -> None:
        self.get_secret_patch.stop()
        self.abstract_ccxtpro_patch.stop()
        self.abstract_ccxt_patch.stop()
        self.mock_timestamp_to_str_patch.stop()
        # Reset static variables on each test run.
        self.reset()

    # //////////////////////////////////////////////////////////////////////////

    def test_initialize_class(self) -> None:
        """
        Smoke test that the class is being initialized correctly.
        """
        # Build broker.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "futures"
        secret_id = 1
        bid_ask_im_client = None
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        # Check broker state and remove dynamic mock ids.
        broker_state_with_mock_ids = pprint.pformat(vars(broker))
        broker_state = re.sub(
            r" id='(.*?)'>", " id='***'>", broker_state_with_mock_ids
        )
        self.check_string(
            broker_state, purify_text=True, test_class_name=self.get_class_name()
        )

    def test_submit_market_order1(self) -> None:
        """
        Verify that order is properly submitted via mocked exchange.
        """
        # Build broker.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 1
        bid_ask_im_client = None
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        # Patch main external source.
        with umock.patch.object(
            broker._async_exchange, "create_order", new_callable=umock.AsyncMock
        ) as create_order_mock:
            create_order_mock.side_effect = [{"id": 0}]
            orders = _get_test_order("market")
            broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
                "2022-08-05 10:37:00-04:00", tz="America/New_York"
            )
            # Run.
            receipt, orders = asyncio.run(
                broker._submit_market_orders(
                    orders,
                    "dummy_timestamp",
                    dry_run=False,
                )
            )
            submitted_orders = broker._previous_parent_orders
        # Check the count of calls.
        self.assertEqual(create_order_mock.call_count, 1)
        # Check the args.
        actual_args = pprint.pformat(tuple(create_order_mock.call_args))
        expected_args = r"""
            ((),
            {'amount': 0.121,
            'params': {'client_oid': 0, 'portfolio_id': 'ccxt_portfolio_mock'},
            'side': 'buy',
            'symbol': 'ETH/USDT',
            'type': 'market'})
        """
        self.assert_equal(actual_args, expected_args, fuzzy_match=True)
        # Check the receipt.
        self.assert_equal(receipt, "order_0")
        # Check the orders.
        act = pprint.pformat(orders)
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 10:36:44.976104-04:00
        asset_id=1464553467
        type_=market
        start_timestamp=2022-08-05 10:36:44.976104-04:00
        end_timestamp=2022-08-05 10:38:44.976104-04:00
        curr_num_shares=0.0
        diff_num_shares=0.121
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}}]
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        submitted_orders = pprint.pformat(submitted_orders)
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 10:36:44.976104-04:00
        asset_id=1464553467
        type_=market
        start_timestamp=2022-08-05 10:36:44.976104-04:00
        end_timestamp=2022-08-05 10:38:44.976104-04:00
        curr_num_shares=0.0
        diff_num_shares=0.121
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)

    def test_submit_market_orders1(
        self,
    ) -> None:
        """
        Verify that orders are properly submitted via mocked exchange.
        """
        # Build broker.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 1
        bid_ask_im_client = self._get_mock_bid_ask_im_client()
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        # Patch the methods to create buy / sell orders and the method that returns limit price
        # for the orders of `limit` type.
        with umock.patch.object(
            broker._async_exchange, "create_order", new_callable=umock.AsyncMock
        ) as create_order_mock, umock.patch.object(
            broker, "load_bid_ask_and_calculate_limit_price", create=True
        ) as limit_price_mock:
            # Define return values for the patched methods.
            create_order_mock.side_effect = [{"id": 0}, {"id": 1}]
            limit_price_mock.side_effect = [60.0, 32.0]
            broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
                "2022-08-05 10:37:00-04:00", tz="America/New_York"
            )
            # Get the orders to submit.
            orders = self._get_test_orders2()
            # Run.
            receipt, orders = asyncio.run(
                broker._submit_market_orders(
                    orders, "dummy_timestamp", dry_run=False
                )
            )
            submitted_orders = broker._previous_parent_orders
        # Check the count of calls.
        self.assertEqual(create_order_mock.call_count, 2)
        # Check the args for buy order.
        _LOG.info(create_order_mock.call_args)
        actual_args = pprint.pformat(create_order_mock.call_args_list)
        expected_args = r"""
        [call(symbol='ETH/USDT', type='limit', side='buy', amount=10.0, price=60.0, params={'portfolio_id': 'ccxt_portfolio_mock', 'client_oid': 0}),
        call(symbol='BTC/USDT', type='limit', side='sell', amount=20.0, price=32.0, params={'portfolio_id': 'ccxt_portfolio_mock', 'client_oid': 1})]
        """
        self.assert_equal(actual_args, expected_args, fuzzy_match=True)
        # Check the receipt.
        self.assert_equal(receipt, "order_0")
        # Check the orders.
        act = pprint.pformat(orders)
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 10:36:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:39:00-04:00
        curr_num_shares=2500.0
        diff_num_shares=10.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}},
        Order:
        order_id=1
        creation_timestamp=2022-08-05 10:36:00-04:00
        asset_id=1467591036
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:39:00-04:00
        curr_num_shares=1000.0
        diff_num_shares=-20.0
        tz=America/New_York
        extra_params={'ccxt_id': [1],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}}]
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        submitted_orders = pprint.pformat(submitted_orders)
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 10:36:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:39:00-04:00
        curr_num_shares=2500.0
        diff_num_shares=10.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}},
        Order:
        order_id=1
        creation_timestamp=2022-08-05 10:36:00-04:00
        asset_id=1467591036
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:39:00-04:00
        curr_num_shares=1000.0
        diff_num_shares=-20.0
        tz=America/New_York
        extra_params={'ccxt_id': [1],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)

    @umock.patch.object(obcaccbr.asyncio, "sleep")
    def test_submit_market_orders_errors2(
        self, sleep_mock: umock.MagicMock
    ) -> None:
        """
        Verify that Binance API error is raised correctly.
        """
        # Build broker.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 1
        bid_ask_im_client = None
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        broker._submitted_order_id = 0
        # Patch main external source.
        with umock.patch.object(
            broker._async_exchange, "create_order", create=True
        ) as create_order_mock:
            create_order_mock.side_effect = [
                ccxt.ExchangeNotAvailable(
                    umock.Mock(), "MockExchangeNotAvailable"
                ),
                Exception("MockException"),
            ]
            orders = _get_test_order("market")
            with umock.patch.object(
                self.abstract_ccxt_mock,
                "ExchangeNotAvailable",
                ccxt.ExchangeNotAvailable,
            ), umock.patch.object(
                self.abstract_ccxt_mock, "NetworkError", ccxt.NetworkError
            ), umock.patch.object(
                self.abstract_ccxt_mock, "BaseError", ccxt.BaseError
            ):
                # Run.
                with self.assertRaises(Exception) as ex:
                    asyncio.run(
                        broker._submit_market_orders(
                            orders,
                            "dummy_timestamp",
                            dry_run=False,
                        )
                    )
        # Check that the exception was raised.
        actual = str(ex.exception)
        self.assertEqual(actual, "MockException")
        # TODO(Juraj): Add test fro _submit_single_order_to_ccxt_with_retry
        #  to test the equivalent of these
        # ccxt_id = order_df["extra_params"][0]["ccxt_id"]
        # self.assertListEqual(ccxt_id, [-1])
        # Check that the error message was logged.
        # extra_params = order_df["extra_params"][0]
        # self.assertIn("error_msg", extra_params)
        # self.assertEqual(extra_params["error_msg"], "MockExchangeNotAvailable")
        # Check the count of calls.
        # self.assertEqual(sleep_mock.call_count, 1)

    def test_submit_market_orders_errors3(self) -> None:
        """
        Verify that the order is not submitted in case of a liquidity error.
        """
        # Define broker parameters.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 1
        bid_ask_im_client = None
        # Initialize class.
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        # Patch main external source.
        with umock.patch.object(
            broker._async_exchange, "create_order", create=True
        ) as create_order_mock:
            # Check that the order is not submitted if the error is connected to liquidity.
            from ccxt.base.errors import OrderNotFillable

            create_order_mock.side_effect = [
                OrderNotFillable(umock.Mock(status=-4131), '"code":-4131,')
            ]
            orders = _get_test_order("market")
            with umock.patch.object(
                self.abstract_ccxt_mock,
                "ExchangeNotAvailable",
                ccxt.ExchangeNotAvailable,
            ), umock.patch.object(
                self.abstract_ccxt_mock, "NetworkError", ccxt.NetworkError
            ), umock.patch.object(
                self.abstract_ccxt_mock, "BaseError", ccxt.BaseError
            ):
                # Run.
                _, orders = asyncio.run(
                    broker._submit_market_orders(
                        orders,
                        "dummy_timestamp",
                        dry_run=False,
                    )
                )
        # Order df should be empty.
        self.assertFalse(orders)

    def test_get_fills1(self) -> None:
        """
        Verify that orders are filled properly via mocked exchange.
        """
        orders = _get_test_order("price@twap")
        # Load fills corresponding to the test orders.
        fills = _get_test_order_fills1()
        # Assign a CCXT order ID corresponding to the order's fill.
        for order, fill in zip(orders, fills):
            order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(
                order, fill["id"]
            )
        expected_fills = "(1) Fill: asset_id=1464553467 fill_id=0 timestamp=2023-03-30 20:16:01.629000+00:00 num_shares=0.12 price=1775.0"
        prev_parent_orders_ts = pd.to_datetime("2023-03-30 20:16:01+00:00")
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    def test_get_fills2(self) -> None:
        """
        Verify that no fills are returned without an order execution timestamp.
        """
        orders = _get_test_order("price@twap")
        # Load fills corresponding to the test orders.
        fills = _get_test_order_fills1()
        # Assign a CCXT order ID corresponding to the order's fill.
        for order, fill in zip(orders, fills):
            order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(
                order, fill["id"]
            )
        expected_fills = hprint.format_list([])
        # Mock missing last order execution time using previous_parent_orders_timestamp=None.
        prev_parent_orders_ts = None
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    def test_get_fills3(self) -> None:
        """
        Verify that if some parent orders have a CCXT ID, and some do not, only
        those with an ID are considered filled.
        """
        self.maxDiff = None
        orders = self._get_test_orders1()
        # Load fills corresponding to the test orders.
        fills = self._get_test_order_fills2()
        # Assign a CCXT order ID corresponding to the order's fill.
        # Don't assign a CCXT ID to the 1st order.
        for order, fill in zip(orders[1:], fills[1:]):
            order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(
                order, fill["id"]
            )
        prev_parent_orders_ts = pd.to_datetime("2023-03-30 20:16:01+00:00")
        # Note: the resulting values were calculated by hand with given test orders.
        expected_fills = "(2) Fill: asset_id=3065029174 fill_id=1 timestamp=2023-03-30 20:16:01.629000+00:00 num_shares=0.18 price=1774.3333333333335 Fill: asset_id=8968126878 fill_id=2 timestamp=2023-03-30 20:16:01.629000+00:00 num_shares=0.18 price=1774.3333333333335"
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    def test_get_fills4(self) -> None:
        """
        Verify that no fills are returned in case when
        `Broker._previous_parent_orders = None`.
        """
        orders = None
        fills = _get_test_order_fills1()
        expected_fills = hprint.format_list([])
        prev_parent_orders_ts = None
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    def test_get_fills5(self) -> None:
        """
        Verify that no fills are returned for an order with no fills.
        """
        orders = _get_test_order("price@twap")
        # Assign a CCXT order ID.
        orders[0] = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(
            orders[0], -1
        )
        fills = []
        expected_fills = hprint.format_list([])
        prev_parent_orders_ts = None
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    def test_get_fills6(self) -> None:
        """
        Verify that orders with multiple child orders are filled correctly.
        """
        orders = _get_test_order("price@twap")
        fills = self._get_test_order_fills3()
        # Assign a CCXT order ID.
        orders[0].extra_params["ccxt_id"] = [
            8389765589152377433,
            8389765589152377488,
        ]
        prev_parent_orders_ts = pd.to_datetime("2023-03-30 20:16:01+00:00")
        # Note: the resulting values were calculated by hand with given test orders.
        expected_fills = "(1) Fill: asset_id=1464553467 fill_id=0 timestamp=2023-03-30 20:16:01.629000+00:00 num_shares=0.15 price=1774.0000000000002"
        self._test_get_fills(orders, fills, expected_fills, prev_parent_orders_ts)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    @umock.patch("oms.broker.ccxt.abstract_ccxt_broker.pd.Timestamp.utcnow")
    def test_get_bid_ask_data_for_last_period(
        self,
        mock_utcnow: umock.MagicMock,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify if the complete dataframe of the bid ask data generated in the
        given last period is correct.
        """
        # Create a broker.
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            1467591036: "BTC/USDT",
            1464553467: "ETH/USDT",
        }
        broker = self._get_local_test_broker(use_mock_data_reader=True)
        mock_utcnow.return_value = pd.Timestamp("2023-09-13 15:30:00", tz="UTC")
        # Test broker is initialized with `60S` bid ask lookback period by default.
        bid_ask_data = broker.get_bid_ask_data_for_last_period()
        # Remove index and timestamps.
        bid_ask_data = bid_ask_data.reset_index(drop=True)
        actual = hpandas.df_to_str(bid_ask_data)
        expected = r"""
        currency_pair exchange_id  bid_size_l1  ask_size_l1  bid_price_l1  ask_price_l1           end_download_timestamp              knowledge_timestamp ccxt_symbols    asset_id
        0      ETH_USDT     binance           22           25            31            10        2023-09-13 15:29:00+00:00        2023-09-13 15:29:00+00:00     ETH/USDT  1464553467
        1      BTC_USDT     binance           13           37            13            17        2023-09-13 15:29:00+00:00        2023-09-13 15:29:00+00:00     BTC/USDT  1467591036
        2      ETH_USDT     binance           22           25            31            10 2023-09-13 15:29:00.500000+00:00 2023-09-13 15:29:00.500000+00:00     ETH/USDT  1464553467
        ...
        239      ETH_USDT     binance           22           25            31            10 2023-09-13 15:29:59.500000+00:00 2023-09-13 15:29:59.500000+00:00     ETH/USDT  1464553467
        240      ETH_USDT     binance           22           25            31            10        2023-09-13 15:30:00+00:00        2023-09-13 15:30:00+00:00     ETH/USDT  1464553467
        241      BTC_USDT     binance           13           37            13            17        2023-09-13 15:30:00+00:00        2023-09-13 15:30:00+00:00     BTC/USDT  1467591036
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_get_ccxt_trades(self) -> None:
        """
        Verify that the ccxt trades we get are correct.
        """
        broker = self._get_local_test_broker()
        orders = self._get_test_order_fills2()
        # Mock method.
        broker._get_ccxt_trades_for_one_symbol = umock.create_autospec(
            broker._get_ccxt_trades_for_one_symbol, return_value=[None]
        )
        # Check that it returns empty list if ccxt_trade is None.
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_ccxt_trades(orders)
            trades = hasynci.run(coroutine, event_loop=event_loop)
        self.assertListEqual(trades, [None] * len(orders))

    # #########################################################################

    def test_get_open_positions1(self) -> None:
        """
        Verify that the open positions we get are correct.

        - Empty dict if no open position.
        """
        broker = self._get_local_test_broker()
        # Mock method for no value.
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        broker._sync_exchange.fetch_positions = umock.MagicMock(return_value=[])
        open_positions = broker.get_open_positions()
        self.assertDictEqual(open_positions, {})

    def test_get_open_positions2(self) -> None:
        """
        Verify that the open positions we get are correct.

        - Dict with correct positionAmt if position is not empty.
        """
        broker = self._get_local_test_broker()
        # Mock method for some dummy value.
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        expected_position = [{"info": {"positionAmt": 10}, "symbol": "BTC"}]
        broker._sync_exchange.fetch_positions = umock.MagicMock(
            return_value=expected_position
        )
        open_positions = broker.get_open_positions()
        expected_str = "{'BTC': 10.0}"
        self.assert_equal(str(open_positions), expected_str)

    def test_get_open_positions3(self) -> None:
        """
        Verify that the open positions are actually cached.

        - Dict with correct positionAmt if position is not empty.
        """
        broker = self._get_local_test_broker()
        # Mock method for some dummy value.
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        expected_position = [{"info": {"positionAmt": 10}, "symbol": "BTC"}]
        broker._sync_exchange.fetch_positions = umock.MagicMock(
            return_value=expected_position
        )
        # Load open positions and access cached value.
        open_positions = broker.get_open_positions()
        expected_str = "{'BTC': 10.0}"
        # Check that the loaded open positions are correct.
        self.assert_equal(str(open_positions), expected_str)
        # Verify that the fetch_positions is called exactly once.
        self.assertEqual(broker._sync_exchange.fetch_positions.call_count, 1)
        # Check that the cache is correctly updated.
        cached_positions = broker._cached_open_positions
        self.assert_equal(str(cached_positions), expected_str)
        # Verify that the fetch_positions is not called again if there is a cached value.
        _ = broker.get_open_positions()
        self.assertEqual(broker._sync_exchange.fetch_positions.call_count, 1)

    def test_get_open_positions4(self) -> None:
        """
        Verify that the cached value is deleted after order submission.

        - `None` value after order is submitted.
        """
        broker = self._get_local_test_broker()
        # Mock method for some dummy value.
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        expected_position = [{"info": {"positionAmt": 10}, "symbol": "BTC"}]
        broker._sync_exchange.fetch_positions = umock.MagicMock(
            return_value=expected_position
        )
        open_positions = broker.get_open_positions()
        # Mock `_submit_order` to override the cached value.
        with umock.patch.object(
            broker._async_exchange, "create_order", new_callable=umock.AsyncMock
        ) as create_order_mock:
            create_order_mock.side_effect = [{"id": 0}]
            orders = _get_test_order("market")
            broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
                "2022-08-05 10:37:00-04:00", tz="America/New_York"
            )
            # Run.
            _ = asyncio.run(
                broker._submit_market_orders(
                    orders,
                    "dummy_timestamp",
                    dry_run=False,
                )
            )
        expected_str = "{'BTC': 10.0}"
        # Check that the loaded open positions are correct.
        self.assert_equal(str(open_positions), expected_str)
        # Verify that the fetch_positions is called exactly once.
        self.assertEqual(broker._sync_exchange.fetch_positions.call_count, 1)
        # Get cached value.
        open_positions = broker._cached_open_positions
        #
        self.assertIsNone(open_positions)
        # Verify that the fetch_positions is called again if there is no cached value.
        _ = broker.get_open_positions()
        self.assertEqual(broker._sync_exchange.fetch_positions.call_count, 2)

    # #########################################################################

    def test_cancel_open_orders(self) -> None:
        """
        Verify that cancel_open_orders() calls cancel_all_orders() just once.
        """
        broker = self._get_local_test_broker()
        with umock.patch.object(
            broker._sync_exchange, "cancel_all_orders"
        ) as mock_cancel_all_orders:
            broker.cancel_open_orders("BTC")
            self.assertEqual(mock_cancel_all_orders.call_count, 1)

    def test_get_total_balance1(self) -> None:
        """
        Verify that get_total_balance() returns expected results when fetch
        balance is empty.
        """
        # Build broker.
        broker = self._get_local_test_broker()
        # Mock method with empty dict.
        expected = {"total": {}}
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        broker._sync_exchange.fetchBalance = umock.MagicMock(
            return_value=expected
        )
        actual = broker.get_total_balance()
        expected_str = str(expected["total"])
        self.assert_equal(str(actual), expected_str)

    def test_get_total_balance2(self) -> None:
        """
        Verify that get_total_balance() returns expected results with some
        dummy balance.
        """
        # Build broker.
        broker = self._get_local_test_broker()
        # Mock method with some dummy values.
        expected = {"total": {"BNB": 0.0, "USDT": 5026.224, "BUSD": 1000.1001}}
        broker._sync_exchange = umock.create_autospec(ccxt.Exchange)
        broker._sync_exchange.fetchBalance = umock.MagicMock(
            return_value=expected
        )
        actual = broker.get_total_balance()
        expected_str = str(expected["total"])
        self.assert_equal(str(actual), expected_str)

    @staticmethod
    def _get_test_orders1() -> List[oordorde.Order]:
        """
        Build a list of toy orders based or real data for tests.
        """
        # pylint: disable=line-too-long
        orders_str = "\n".join(
            [
                "Order: order_id=0 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3303714233 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-16.0 tz=America/New_York extra_params={}",
                "Order: order_id=1 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3065029174 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-6.0 tz=America/New_York extra_params={}",
                "Order: order_id=2 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=8968126878 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=38.0 tz=America/New_York extra_params={}",
            ]
        )
        # pylint: disable=line-too-long
        orders = oordorde.orders_from_string(orders_str)
        return orders

    @staticmethod
    def _get_test_order_fills2() -> List[oordorde.Order]:
        """
        Get CCXT order structures for child orders associated with
        `_get_test_order1`.
        """
        fills = [
            {
                "info": {
                    "orderId": "8389765589152377439",
                    "symbol": "BNBUSDT",
                    "status": "FILLED",
                    "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                    "price": "1780.0",
                    "avgPrice": "1780.70000",
                    "origQty": "0.06",
                    "executedQty": "0.06",
                    "cumQty": "0.06",
                    "cumQuote": "48.07890",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "reduceOnly": "",
                    "closePosition": "",
                    "side": "BUY",
                    "positionSide": "BOTH",
                    "stopPrice": "0",
                    "workingType": "CONTRACT_PRICE",
                    "priceProtect": "",
                    "origType": "LIMIT",
                    "updateTime": "1680207361629",
                },
                "id": "8389765589152377439",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "timestamp": "",
                "datetime": "",
                "lastTradeTimestamp": "",
                "symbol": "BNB/USDT:USDT",
                "type": "limit",
                "timeInForce": "GTC",
                "postOnly": "",
                "reduceOnly": "",
                "side": "buy",
                "price": 1780.0,
                "stopPrice": "",
                "amount": 0.06,
                "cost": 106.8,
                "average": 1780.7,
                "filled": 0.06,
                "remaining": 0.0,
                "status": "closed",
                "fee": "",
                "trades": [],
                "fees": [],
            },
            {
                "info": {
                    "orderId": "8389765589152377439",
                    "symbol": "DOGEUSDT",
                    "status": "FILLED",
                    "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                    "price": "1770.10",
                    "avgPrice": "1770.70000",
                    "origQty": "0.06",
                    "executedQty": "0.06",
                    "cumQty": "0.06",
                    "cumQuote": "48.07890",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "reduceOnly": "",
                    "closePosition": "",
                    "side": "BUY",
                    "positionSide": "BOTH",
                    "stopPrice": "0",
                    "workingType": "CONTRACT_PRICE",
                    "priceProtect": "",
                    "origType": "LIMIT",
                    "updateTime": "1680207361629",
                },
                "id": "8389765589152377439",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "timestamp": "",
                "datetime": "",
                "lastTradeTimestamp": "",
                "symbol": "DOGE/USDT:USDT",
                "type": "limit",
                "timeInForce": "GTC",
                "postOnly": "",
                "reduceOnly": "",
                "side": "buy",
                "price": 1770.0,
                "stopPrice": "",
                "amount": 0.06,
                "cost": 106.2,
                "average": 1770.7,
                "filled": 0.06,
                "remaining": 0.0,
                "status": "closed",
                "fee": "",
                "trades": [],
                "fees": [],
            },
            {
                "info": {
                    "orderId": "8389765589152377439",
                    "symbol": "ADAUSDT",
                    "status": "FILLED",
                    "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                    "price": "1773.0",
                    "avgPrice": "1773.70000",
                    "origQty": "0.06",
                    "executedQty": "0.06",
                    "cumQty": "0.06",
                    "cumQuote": "48.07890",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "reduceOnly": "",
                    "closePosition": "",
                    "side": "BUY",
                    "positionSide": "BOTH",
                    "stopPrice": "0",
                    "workingType": "CONTRACT_PRICE",
                    "priceProtect": "",
                    "origType": "LIMIT",
                    "updateTime": "1680207361629",
                },
                "id": "8389765589152377439",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "timestamp": "",
                "datetime": "",
                "lastTradeTimestamp": "",
                "symbol": "ADA/USDT:USDT",
                "type": "limit",
                "timeInForce": "GTC",
                "postOnly": "",
                "reduceOnly": "",
                "side": "buy",
                "price": 1773.0,
                "stopPrice": "",
                "amount": 0.06,
                "cost": 106.38,
                "average": 1773.7,
                "filled": 0.06,
                "remaining": 0.0,
                "status": "closed",
                "fee": "",
                "trades": [],
                "fees": [],
            },
        ]
        return fills

    @staticmethod
    def _get_test_order_fills3() -> List[oordorde.Order]:
        """
        Get CCXT order structures for child orders associated with
        `_get_test_order`.
        """
        fills = [
            {
                "info": {
                    "orderId": "8389765589152377488",
                    "symbol": "ETHUSDT",
                    "status": "FILLED",
                    "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                    "price": "1770.10",
                    "avgPrice": "1770.70000",
                    "origQty": "0.09",
                    "executedQty": "0.09",
                    "cumQty": "0.09",
                    "cumQuote": "48.07890",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "reduceOnly": "",
                    "closePosition": "",
                    "side": "BUY",
                    "positionSide": "BOTH",
                    "stopPrice": "0",
                    "workingType": "CONTRACT_PRICE",
                    "priceProtect": "",
                    "origType": "LIMIT",
                    "updateTime": "1680207361629",
                },
                "id": "8389765589152377488",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "timestamp": "",
                "datetime": "",
                "lastTradeTimestamp": "",
                "symbol": "ETH/USDT:USDT",
                "type": "limit",
                "timeInForce": "GTC",
                "postOnly": "",
                "reduceOnly": "",
                "side": "buy",
                "price": 1770.0,
                "stopPrice": "",
                "amount": 0.09,
                "cost": 159.3,
                "average": 1770.7,
                "filled": 0.09,
                "remaining": 0.0,
                "status": "closed",
                "fee": "",
                "trades": [],
                "fees": [],
            },
            {
                "info": {
                    "orderId": "8389765589152377433",
                    "symbol": "ETHUSDT",
                    "status": "FILLED",
                    "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                    "price": "1780.10",
                    "avgPrice": "1780.70000",
                    "origQty": "0.06",
                    "executedQty": "0.06",
                    "cumQty": "0.06",
                    "cumQuote": "48.07890",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "reduceOnly": "",
                    "closePosition": "",
                    "side": "BUY",
                    "positionSide": "BOTH",
                    "stopPrice": "0",
                    "workingType": "CONTRACT_PRICE",
                    "priceProtect": "",
                    "origType": "LIMIT",
                    "updateTime": "1680207361629",
                },
                "id": "8389765589152377433",
                "clientOrderId": "x-xcKtGhcu2538b26ad6ffd65a877c16",
                "timestamp": "",
                "datetime": "",
                "lastTradeTimestamp": "",
                "symbol": "ETH/USDT:USDT",
                "type": "limit",
                "timeInForce": "GTC",
                "postOnly": "",
                "reduceOnly": "",
                "side": "buy",
                "price": 1780.0,
                "stopPrice": "",
                "amount": 0.06,
                "cost": 106.8,
                "average": 1780.7,
                "filled": 0.06,
                "remaining": 0.0,
                "status": "closed",
                "fee": "",
                "trades": [],
                "fees": [],
            },
        ]
        return fills

    @staticmethod
    def _get_test_orders2() -> List[oordorde.Order]:
        """
        Build a list of toy orders for unit testing.
        """
        # Prepare test data.
        # pylint: disable=line-too-long
        orders_str = "\n".join(
            [
                "Order: order_id=0 creation_timestamp=2022-08-05 10:36:00-04:00 asset_id=1464553467 type_=limit start_timestamp=2022-08-05 10:36:00-04:00 end_timestamp=2022-08-05 10:39:00-04:00 curr_num_shares=2500.0 diff_num_shares=10 tz=America/New_York extra_params={}",
                "Order: order_id=1 creation_timestamp=2022-08-05 10:36:00-04:00 asset_id=1467591036 type_=limit start_timestamp=2022-08-05 10:36:00-04:00 end_timestamp=2022-08-05 10:39:00-04:00 curr_num_shares=1000.0 diff_num_shares=-20.0 tz=America/New_York extra_params={}",
            ]
        )
        # Get orders.
        orders = oordorde.orders_from_string(orders_str)
        return orders

    @staticmethod
    def _get_test_orders3() -> List[oordorde.Order]:
        """
        Build a list of toy orders based or real data for tests.
        """
        # pylint: disable=line-too-long
        orders_str = "\n".join(
            [
                "Order: order_id=0 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3303714233 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-0.008 tz=America/New_York extra_params={}",
                "Order: order_id=1 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3065029174 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=0.01 tz=America/New_York extra_params={}",
                "Order: order_id=2 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=8968126878 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=38.478 tz=America/New_York extra_params={}",
            ]
        )
        # pylint: disable=line-too-long
        orders = oordorde.orders_from_string(orders_str)
        return orders

    @staticmethod
    def _get_mock_bid_ask_im_client() -> icdc.ImClient:
        """
        Get Mock bid / ask ImClient using synthetical data.
        """
        df = obcttcut.get_test_bid_ask_data()
        # Get universe.
        universe_mode = "trade"
        vendor = "CCXT"
        version = "v7"
        universe = ivcu.get_vendor_universe(
            vendor,
            universe_mode,
            version=version,
            as_full_symbol=True,
        )
        # Build ImClient.
        im_client = icdc.DataFrameImClient(df, universe)
        return im_client

    # //////////////////////////////////////////////////////////////////////////

    def _test_timestamp_helper(
        self,
        timestamp: pd.Timestamp,
    ) -> None:
        actual = obcaccbr.AbstractCcxtBroker.timestamp_to_str(timestamp)
        expected = "20230825-120000"
        self.assert_equal(actual, expected)

    def _get_test_broker(
        self,
        universe_version: str,
        account_type: str,
        contract_type: str,
        secret_id: int,
        bid_ask_im_client: Optional[icdc.ImClient],
        *,
        log_dir: Optional[str] = "mock/log",
        passivity_factor: float = 0.1,
        use_mock_data_reader: Optional[bool] = False,
    ) -> obcaccbr.AbstractCcxtBroker:
        """
        Build the mocked `AbstractCcxtBroker` for unit testing.

        See `AbstractCcxtBroker` for params description.
        """
        exchange_id = "binance"
        stage = "preprod"
        portfolio_id = "ccxt_portfolio_mock"
        secret_id = ohsseide.SecretIdentifier(
            exchange_id, stage, account_type, secret_id
        )
        if use_mock_data_reader:
            mock_data_reader = umock.MagicMock()
            mock_data_reader.load_db_table = (
                obcttcut._generate_raw_data_reader_bid_ask_data
            )
        else:
            mock_data_reader = None
        logger = obcccclo.CcxtLogger(log_dir, mode="write")
        sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
            secret_id, contract_type, exchange_id, account_type
        )
        broker = self.get_broker_class()(
            logger=logger,
            bid_ask_im_client=bid_ask_im_client,
            strategy_id="dummy_strategy_id",
            market_data=umock.create_autospec(
                spec=mdata.MarketData, instance=True
            ),
            universe_version=universe_version,
            stage=stage,
            log_dir=log_dir,
            exchange_id=exchange_id,
            account_type=account_type,
            portfolio_id=portfolio_id,
            contract_type=contract_type,
            secret_identifier=secret_id,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(
                passivity_factor
            ),
            max_order_submit_retries=3,
            bid_ask_raw_data_reader=mock_data_reader,
            sync_exchange=sync_exchange,
            async_exchange=async_exchange,
        )
        return broker

    def _get_local_test_broker(
        self,
        use_mock_data_reader: Optional[bool] = False,
    ) -> obcaccbr.AbstractCcxtBroker:
        """
        Return a CCXT Broker for local testing.
        """
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 1
        bid_ask_im_client = None
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
            use_mock_data_reader=use_mock_data_reader,
        )
        return broker

    # //////////////////////////////////////////////////////////////////////////

    def _test_get_fills(
        self,
        orders: List[oordorde.Order],
        ccxt_fills: List[oordorde.Order],
        expected_fills_as_str: str,
        previous_parent_orders_timestamp: Optional[pd.Timestamp],
    ) -> None:
        # Define broker parameters.
        universe_version = "v5"
        account_type = "trading"
        contract_type = "spot"
        secret_id = 4
        bid_ask_im_client = None
        # Initialize class.
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
        )
        broker._previous_parent_orders = orders
        # Mock last order execution time. Unix time: 1680207361629 ms.
        broker.previous_parent_orders_timestamp = previous_parent_orders_timestamp
        with umock.patch.object(
            broker._async_exchange, "fetch_orders", new_callable=umock.AsyncMock
        ) as fetch_orders_mock:
            fetch_orders_mock.return_value = ccxt_fills
            with hasynci.solipsism_context() as event_loop:
                coroutine = broker.get_fills_async()
                fills = hasynci.run(coroutine, event_loop=event_loop)
        actual_fills = hprint.format_list(fills)
        _LOG.info(actual_fills)
        self.assertEqual(actual_fills, expected_fills_as_str)


# TODO(gp): Add test for _submit_single_ccxt_order.


# #############################################################################
# TestSaveBrokerData1
# #############################################################################


@pytest.mark.skip(
    "Run manually. Cannot be run via GH because Binance is not accessible from North America."
)
class TestSaveBrokerData1(hunitest.TestCase):
    """
    Capture data from a CCXT broker so that it can be reused in other tests and
    code.
    """

    # TODO(gp): @Danya we need to document the `aws cp command`.
    def test_save_market_info1(self) -> None:
        """
        Save market info.

        See `AbstractCcxtBroker._get_market_info()` for details.
        """
        # Get market information from the exchange.
        broker = self._get_test_broker()
        market_info = broker.market_info
        _LOG.debug("asset_market_info dict '%s' ...", market_info)
        self._save_broker_data(market_info)

    # TODO(Sameep): disabled as part of CMTask5310.
    @pytest.mark.skip()
    def test_save_trading_fees_info1(self) -> None:
        """
        Save binance fee info.

        See `AbstractCcxtBroker._get_trading_fee_info()` for details.
        """
        # Get market information from the exchange.
        broker = self._get_test_broker()
        fees_info = broker.fees
        _LOG.debug("asset_fees dict '%s' ...", fees_info)
        self._save_broker_data(fees_info)

    def _get_test_broker(self) -> obcaccbr.AbstractCcxtBroker:
        # Initialize broker.
        # Use v8 universe as it is a super-set of all the universes that we use
        # (e.g., v7.4, v7.5, v8.1, v8.2).
        # TODO(Grisha): Ideally save information about all currently listed
        # names.
        universe_version = "v8"
        exchange = "binance"
        stage = "preprod"
        account_type = "trading"
        secret_id = 4
        secret_identifier = ohsseide.SecretIdentifier(
            exchange, stage, account_type, secret_id
        )
        log_dir = self.get_scratch_space()
        # Use the exchange-only Broker because we only need to fetch Binance
        # limits.
        broker = obccbrin.get_CcxtBroker_exchange_only_instance1(
            universe_version,
            secret_identifier,
            log_dir,
        )
        return broker

    def _save_broker_data(self, data: Dict[Any, Any]) -> None:
        # Build file path.
        dst_dir = self.get_input_dir(use_only_test_class=False)
        file_name = "broker_data.json"
        file_path = os.path.join(dst_dir, file_name)
        # Save data.
        _LOG.info("Saving data in '%s' ...", file_path)
        hio.to_json(file_path, data)
        _LOG.info("Saving in '%s' done", file_path)
