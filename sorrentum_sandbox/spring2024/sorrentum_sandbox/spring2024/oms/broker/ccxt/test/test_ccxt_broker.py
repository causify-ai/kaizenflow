import asyncio
import logging
import pprint
import unittest.mock as umock
from typing import List, Optional, Tuple

import ccxt
import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.htimer as htimer
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.mock_ccxt_exchange as obcmccex
import oms.broker.ccxt.test.ccxt_broker_test_case as obccbteca
import oms.broker.ccxt.test.mock_exchange_test_case as obcctmetc
import oms.broker.ccxt.test.test_ccxt_utils as obcttcut
import oms.child_order_quantity_computer as ochorquco
import oms.limit_price_computer as oliprcom
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestCcxtBroker
# #############################################################################


class TestCcxtBroker(obccbteca.TestCcxtBroker_TestCase):
    def test_get_ccxt_order_structure1(self) -> None:
        """
        Test that `_get_ccxt_order_structure()` raises AssertionError if
        ccxt_id is not in order.
        """
        # Prepare inputs.
        broker, order = self._get_mock_broker_and_order()
        # Run test.
        with self.assertRaises(AssertionError) as e:
            self._test_get_ccxt_order_structure_helper(broker, order)
        # Check results.
        excepted_msg = "* Failed assertion *\n'ccxt_id' in '{}'"
        actual_msg = str(e.exception)
        self.assert_equal(excepted_msg, actual_msg, fuzzy_match=True)

    def test_get_ccxt_order_structure2(self) -> None:
        """
        Verify expected results for `ccxt_order` if `ccxt_id` is not -1.
        """
        # Prepare inputs.
        broker, order = self._get_mock_broker_and_order()
        expected_order = "unbelievable order"
        broker._async_exchange.fetch_order = umock.AsyncMock(
            return_value=expected_order
        )
        # Run test.
        order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(order, 1)
        result = self._test_get_ccxt_order_structure_helper(broker, order)
        # Check results.
        self.assert_equal(expected_order, result)

    def test_get_ccxt_order_structure3(self) -> None:
        """
        Verify expected results for `ccxt_order` if `ccxt_id` is -1 without an
        error message.
        """
        # Prepare inputs.
        broker, order = self._get_mock_broker_and_order()
        order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(order, -1)
        # Run test.
        with self.assertRaises(AssertionError) as e:
            self._test_get_ccxt_order_structure_helper(broker, order)
        # Check results.
        excepted_msg = (
            f"* Failed assertion *\n'error_msg' in '{str(order.extra_params)}'"
        )
        actual_msg = str(e.exception)
        self.assert_equal(excepted_msg, actual_msg, fuzzy_match=True)

    def test_get_ccxt_order_structure4(self) -> None:
        """
        Check that it returns None if ccxt_id is -1 with error message.
        """
        broker, order = self._get_mock_broker_and_order()
        order.extra_params["ccxt_id"] = [-1]
        order.extra_params["error_msg"] = "Some error message"
        result = self._test_get_ccxt_order_structure_helper(broker, order)
        self.assertIsNone(result)

    def test_get_ccxt_fills1(self) -> None:
        """
        Test that get_ccxt_fills() returns empty list if ccxt_order is None.

        - List with ccxt_order if ccxt_order is not None.
        """
        # Build broker.
        broker = self._get_local_test_broker()
        # Mock method.
        broker._get_ccxt_order_structure = umock.create_autospec(
            broker._get_ccxt_order_structure, return_value=None
        )
        # Check that it returns empty list if ccxt_order is None.
        order = obccbteca._get_test_order("market")
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_ccxt_fills(order)
            result = hasynci.run(coroutine, event_loop=event_loop)
        self.assertListEqual(result, [])

    def test_get_ccxt_fills2(self) -> None:
        """
        Test that get_ccxt_fills() returns list with ccxt_order if ccxt_order
        is not None.
        """
        # Build broker.
        broker = self._get_local_test_broker()
        # Mock method.
        expected_order = "dummy_order"
        broker._get_ccxt_order_structure = umock.create_autospec(
            broker._get_ccxt_order_structure, return_value=expected_order
        )
        order = obccbteca._get_test_order("market")
        # Check normal case.
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker.get_ccxt_fills(order)
            result = hasynci.run(coroutine, event_loop=event_loop)
        self.assertListEqual(result, [expected_order])

    def test_update_stats_for_order(self) -> None:
        """
        Test that _update_stats_for_order() updates
        order.extra_params["stats"].
        """
        # Build broker.
        broker = self._get_local_test_broker()
        order = obccbteca._get_test_order("market")[0]
        order.id = "123"
        function_name = "test_update_stats_for_order"
        tag = "ccxt_order"
        value = "value"
        # Check that order was updated.
        broker._update_stats_for_order(order, tag, value)
        self.assertDictEqual(
            {function_name + "::" + tag: value}, order.extra_params["stats"]
        )

    def test_submit_orders_empty(self) -> None:
        """
        Test it possible to passing empty list of orders to submit.
        """
        broker = self._get_local_test_broker()
        with hasynci.solipsism_context() as event_loop:
            receipt, orders = hasynci.run(
                broker._submit_twap_orders([]), event_loop=event_loop
            )
        self.assert_equal(receipt, "")
        self.assert_equal(str(orders), "[]")

    def test_skip_first_wave1(self) -> None:
        """
        Test that the method returns True when there is not enough time left to
        complete the first wave of orders.
        """
        # Prepare inputs.
        execution_start_timestamp = pd.Timestamp("2024-04-29 09:30:00+00:00")
        execution_freq = pd.Timedelta("10S")
        wave_start_time = pd.Timestamp("2024-04-29 09:30:07+00:00")
        wave_id = 0
        # Build broker.
        broker = self._get_local_test_broker()
        broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
            "2024-04-29 09:30:07+00:00"
        )
        with htimer.TimedScope(logging.INFO, "async_retry_loop") as ts:
            actual = asyncio.run(
                broker._skip_first_wave(
                    execution_start_timestamp,
                    execution_freq,
                    wave_start_time,
                    wave_id,
                )
            )
        # Check that the waiting time was correct.
        self.assertEqual(round(ts.elapsed_time, 1), 3.0)
        self.assertEqual(actual, True)

    def test_skip_first_wave2(self) -> None:
        """
        Test that the method returns False when there is enough time left to
        complete the first wave of orders.
        """
        # Prepare inputs.
        execution_start_timestamp = pd.Timestamp("2024-04-29 09:30:00+00:00")
        execution_freq = pd.Timedelta("10S")
        wave_start_time = pd.Timestamp("2024-04-29 09:30:06+00:00")
        wave_id = 0
        # Build broker.
        broker = self._get_local_test_broker()
        broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
            "2024-04-29 09:30:06+00:00"
        )
        actual = asyncio.run(
            broker._skip_first_wave(
                execution_start_timestamp,
                execution_freq,
                wave_start_time,
                wave_id,
            )
        )
        self.assertEqual(actual, False)

    def test_skip_first_wave3(self) -> None:
        """
        Test that the method returns False when `wave_id` is not 0.
        """
        # Prepare inputs.
        execution_start_timestamp = pd.Timestamp("2024-04-29 09:30:00+00:00")
        execution_freq = pd.Timedelta("10S")
        wave_start_time = pd.Timestamp("2024-04-29 09:30:01+00:00")
        wave_id = 1
        # Build broker.
        broker = self._get_local_test_broker()
        broker.market_data.get_wall_clock_time.return_value = pd.Timestamp(
            "2024-04-29 09:30:01+00:00"
        )
        actual = asyncio.run(
            broker._skip_first_wave(
                execution_start_timestamp,
                execution_freq,
                wave_start_time,
                wave_id,
            )
        )
        self.assertEqual(actual, False)

    # //////////////////////////////////////////////////////////////////////////

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
        passivity_factor = 0.5
        broker = self._get_test_broker(
            universe_version,
            account_type,
            contract_type,
            secret_id,
            bid_ask_im_client,
            passivity_factor=passivity_factor,
            use_mock_data_reader=use_mock_data_reader,
        )
        return broker

    def _get_mock_broker_and_order(
        self,
    ) -> Tuple[obcaccbr.AbstractCcxtBroker, oordorde.Order]:
        """
        Create mock broker and order for test.
        """
        broker = self._get_local_test_broker()
        broker._async_exchange = umock.create_autospec(ccxt.Exchange)
        broker.asset_id_to_ccxt_symbol_mapping = umock.MagicMock()
        order = obccbteca._get_test_order("market")[0]
        return broker, order

    # //////////////////////////////////////////////////////////////////////////

    # TODO(gp): Make it staticmethod.
    def _test_get_ccxt_order_structure_helper(
        self,
        broker: obcaccbr.AbstractCcxtBroker,
        order: oordorde.Order,
    ) -> Optional[obcaccbr.CcxtData]:
        """
        Test `_get_ccxt_order_structure()` with async.
        """
        with hasynci.solipsism_context() as event_loop:
            coroutine = broker._get_ccxt_order_structure(order)
            result = hasynci.run(coroutine, event_loop=event_loop)
        return result


# #############################################################################
# TestCcxtBroker_V2_UsingFakeExchange
# #############################################################################


class TestCcxtBroker_V2_UsingFakeExchange(obcctmetc.MockExchangeTestCase):
    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_orders1(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Test submitting non-twap orders.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:30:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:31:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:32:00+00:00")
        curr_num_shares = 0
        passivity_factor = 0.5
        orders = self._get_test_orders(
            creation_timestamp, start_timestamp, end_timestamp
        )
        starting_positions = [
            {"info": {"positionAmt": curr_num_shares}, "symbol": "ETH/USDT"},
        ]
        # Define fills percents for each order.
        fills_percents = [1.0, 0.9]
        orders, broker = self._test_submit_orders(
            orders,
            "limit",
            starting_positions,
            fills_percents,
            oliprcom.LimitPriceComputerUsingSpread(passivity_factor),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )
        submitted_orders = broker._previous_parent_orders
        exp = r"""
        order_id        creation_timestamp    asset_id  type_  \
        0         0 2022-08-05 05:30:55-04:00  1464553467  limit
        1         1 2022-08-05 05:30:55-04:00  1467591036  limit

                    start_timestamp             end_timestamp  curr_num_shares  \
        0 2022-08-05 05:31:00-04:00 2022-08-05 05:32:00-04:00           2500.0
        1 2022-08-05 05:31:00-04:00 2022-08-05 05:32:00-04:00           1000.0

        diff_num_shares                tz  \
        0             10.0  America/New_York
        1            -20.0  America/New_York

                                                extra_params
        0  {'stats': {'_submit_single_order_to_ccxt::star...
        1  {'stats': {'_submit_single_order_to_ccxt::star...
        """
        actual_orders = pprint.pformat(orders)
        self.assert_equal(actual_orders, exp, fuzzy_match=True)
        submitted_orders = pprint.pformat(submitted_orders)
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:30:55-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=2500.0
        diff_num_shares=10.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:30:57-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}},
        Order:
        order_id=1
        creation_timestamp=2022-08-05 05:30:55-04:00
        asset_id=1467591036
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=1000.0
        diff_num_shares=-20.0
        tz=America/New_York
        extra_params={'ccxt_id': [1],
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:30:59-0400', tz='America/New_York'),
                '_submit_single_order_to_ccxt::attempt_num': 1,
                '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:30:57-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=0 timestamp=2022-08-05 09:30:57+00:00 num_shares=10.0 price=20.5,
        Fill: asset_id=1467591036 fill_id=1 timestamp=2022-08-05 09:30:59+00:00 num_shares=-18.0 price=15.0]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_orders2(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Submit custom_twap type of orders.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        curr_num_shares = 0
        passivity_factor = 0.5
        orders_str = "\n".join(
            [
                "Order: order_id=0 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1464553467 type_=price@custom_twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-0.008 tz=America/New_York extra_params={}",
                "Order: order_id=1 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=6051632686 type_=price@custom_twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=0.01 tz=America/New_York extra_params={}",
            ]
        )
        # pylint: disable=line-too-long
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {"info": {"positionAmt": curr_num_shares}, "symbol": "ETH/USDT"},
        ]
        # We expect to have 5 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [1.0, 0.8, 0.6, 0.4, 0.2]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        orders, broker = self._test_submit_orders(
            orders,
            "price@custom_twap",
            starting_positions,
            fills_per_order,
            oliprcom.LimitPriceComputerUsingSpread(passivity_factor),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )
        exp = r"""
        order_id creation_timestamp asset_id type_ \
        0 0 2023-02-21 02:55:44.508525-05:00 1464553467 limit
        1 1 2023-02-21 02:55:44.508525-05:00 6051632686 limit
        2 2 2023-02-21 02:56:00-05:00 1464553467 limit
        3 3 2023-02-21 02:56:00-05:00 6051632686 limit
        4 4 2023-02-21 02:57:00-05:00 1464553467 limit
        5 5 2023-02-21 02:57:00-05:00 6051632686 limit
        6 6 2023-02-21 02:58:00-05:00 1464553467 limit
        7 7 2023-02-21 02:58:00-05:00 6051632686 limit
        8 8 2023-02-21 02:59:00-05:00 1464553467 limit
        9 9 2023-02-21 02:59:00-05:00 6051632686 limit
        start_timestamp end_timestamp curr_num_shares \
        0 2023-02-21 02:55:44.508525-05:00 2023-02-21 02:56:00-05:00 0.0
        1 2023-02-21 02:55:44.508525-05:00 2023-02-21 02:56:00-05:00 0.0
        2 2023-02-21 02:56:00-05:00 2023-02-21 02:57:00-05:00 0.0
        3 2023-02-21 02:56:00-05:00 2023-02-21 02:57:00-05:00 0.0
        4 2023-02-21 02:57:00-05:00 2023-02-21 02:58:00-05:00 0.0
        5 2023-02-21 02:57:00-05:00 2023-02-21 02:58:00-05:00 0.0
        6 2023-02-21 02:58:00-05:00 2023-02-21 02:59:00-05:00 0.0
        7 2023-02-21 02:58:00-05:00 2023-02-21 02:59:00-05:00 0.0
        8 2023-02-21 02:59:00-05:00 2023-02-21 03:00:00-05:00 0.0
        9 2023-02-21 02:59:00-05:00 2023-02-21 03:00:00-05:00 0.0
        diff_num_shares tz \
        0 -0.001 America/New_York
        1 0.002 America/New_York
        2 -0.001 America/New_York
        3 0.002 America/New_York
        4 -0.001 America/New_York
        5 0.002 America/New_York
        6 -0.001 America/New_York
        7 0.002 America/New_York
        8 -0.001 America/New_York
        9 0.002 America/New_York
        extra_params
        0 {'stats': {'_submit_twap_child_order::wave_id'...
        1 {'stats': {'_submit_twap_child_order::wave_id'...
        2 {'stats': {'_submit_twap_child_order::wave_id'...
        3 {'stats': {'_submit_twap_child_order::wave_id'...
        4 {'stats': {'_submit_twap_child_order::wave_id'...
        5 {'stats': {'_submit_twap_child_order::wave_id'...
        6 {'stats': {'_submit_twap_child_order::wave_id'...
        7 {'stats': {'_submit_twap_child_order::wave_id'...
        8 {'stats': {'_submit_twap_child_order::wave_id'...
        9 {'stats': {'_submit_twap_child_order::wave_id'...
        """
        actual_orders = pprint.pformat(orders)
        self.assert_equal(actual_orders, exp, fuzzy_match=True)
        submitted_orders = broker._previous_parent_orders
        submitted_orders = pprint.pformat(submitted_orders)
        self.check_string(submitted_orders)
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=0 timestamp=2023-02-21 07:59:02+00:00 num_shares=-0.003 price=20.5,
         Fill: asset_id=6051632686 fill_id=1 timestamp=2023-02-21 07:59:02+00:00 num_shares=0.006 price=29.500000000000004]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders1(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP buy order is submitted correctly over a
        single iteration.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        #
        creation_timestamp = pd.Timestamp("2022-08-05 09:30:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:31:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:32:00+00:00")
        curr_num_shares = 0
        # TODO(gp): Split in multiple lines or use an helper function or just
        # create the object directly. Using a string is more complicated at this
        # point than using the `Order` ctor.
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id=1464553467 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=1.0 tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {"info": {"positionAmt": curr_num_shares}, "symbol": "ETH/USDT"},
        ]
        # We want to fully fill all orders.
        fills_rate = 1.0
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_rate,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )
        # TODO(gp): Use the check orders, check submitted orders, check fills
        # everywhere.
        # 1) Check orders.
        # TODO(gp): Use `check_string` instead of `assert_equal` and check the
        # important properties of the results (e.g., there is a single order).
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 1,
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        actual_orders = pprint.pformat(orders)
        self.assert_equal(actual_orders, exp, fuzzy_match=True)
        # 2) Check submitted_orders.
        submitted_orders = broker._previous_parent_orders
        submitted_orders = pprint.pformat(submitted_orders)
        exp = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [0],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # 3) Check fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:31:02+00:00 num_shares=1.0 price=20.5]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders2(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        #
        creation_timestamp = pd.Timestamp("2022-08-05 09:29:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:30:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:33:00+00:00")
        curr_num_shares = 12
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=-{curr_num_shares} tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # We expect to have 3 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [1.0, 0.7, 0.5]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_per_order,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )
        submitted_orders = broker._previous_parent_orders
        # 1) Check orders.
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        # 2) Check submitted orders.
        submitted_orders = pprint.pformat(submitted_orders)
        exp = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:29:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:30:00+00:00
        end_timestamp=2022-08-05 09:33:00+00:00
        curr_num_shares=12.0
        diff_num_shares=-12.0
        tz=UTC
        extra_params={'ccxt_id': [0, 1, 2],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:30:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.1': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.2': Timestamp('2022-08-05 05:32:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:32:02+00:00 num_shares=-8.8 price=20.5]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders3(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that 2 TWAP orders (1 buy, 1 sell) are submitted correctly.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        start_timestamp = pd.Timestamp("2022-08-05 10:36:00-04:00")
        end_timestamp = pd.Timestamp("2022-08-05 10:38:00-04:00")
        starting_positions = [
            {"info": {"positionAmt": 2500}, "symbol": "ETH/USDT:USDT"},
            {"info": {"positionAmt": 1000}, "symbol": "BTC/USDT:USDT"},
        ]
        orders = self._get_test_orders(
            creation_timestamp, start_timestamp, end_timestamp
        )
        # We expect to have 2 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [1.0, 0.7]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_per_order,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )
        submitted_orders = broker._previous_parent_orders
        # Check the order Dataframe.
        # TODO(Juraj): since this is correlated with the generated input,
        # it should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        # TODO(Juraj, Danya): check if the expected string is correct.
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Grisha): convert to a df and freeze instead of using string.
        # TODO(Juraj): since this is almost the same as the generated input,
        # it should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        exp = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 10:35:55-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:38:00-04:00
        curr_num_shares=2500.0
        diff_num_shares=10.0
        tz=America/New_York
        extra_params={'ccxt_id': [0, 2],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 10:36:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.1': Timestamp('2022-08-05 10:37:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 10:35:55-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_orders::start': Timestamp('2022-08-05 10:35:55-0400', tz='America/New_York')}},
        Order:
        order_id=1
        creation_timestamp=2022-08-05 10:35:55-04:00
        asset_id=1467591036
        type_=limit
        start_timestamp=2022-08-05 10:36:00-04:00
        end_timestamp=2022-08-05 10:38:00-04:00
        curr_num_shares=1000.0
        diff_num_shares=-20.0
        tz=America/New_York
        extra_params={'ccxt_id': [1, 3],
        'ccxt_symbol': 'BTC/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 10:36:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.1': Timestamp('2022-08-05 10:37:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 10:35:55-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 10:36:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.1': Timestamp('2022-08-05 10:37:00-0400', tz='America/New_York'),
        '_submit_twap_orders::start': Timestamp('2022-08-05 10:35:55-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=0 timestamp=2022-08-05 14:37:02+00:00 num_shares=8.5 price=20.5,
        Fill: asset_id=1467591036 fill_id=1 timestamp=2022-08-05 14:37:02+00:00 num_shares=-17.0 price=15.0]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_price_assertion(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that the fill corresponding to the order has the correct limit
        price.

        This test case uses engineered bid/ask data instead of randomly
        generated ones in order to be able to assert the average price
        calculated in the fill. The test assumes that the obtained price
        is exactly the limit price and each order is fully filled.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        start_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        end_timestamp = pd.Timestamp("2022-08-05 10:37:00-04:00")
        curr_num_shares = 0
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=1.0 tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # We expect to have 2 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [1.0, 0.7]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        # Run TWAP submission.
        bid_ask_df = obcttcut.get_test_bid_ask_data()
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_per_order,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
            bid_ask_df=bid_ask_df,
        )
        # Assert fills.
        # The timestamp is taken as last update time of all child orders.
        # The price corresponds to using passivity factor = 0.5.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 14:36:02+00:00 num_shares=0.85 price=20.5]
        """
        self._test_get_fills(broker, exp)

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_partial_fill(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations with partial fill.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:29:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:30:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:33:00+00:00")
        curr_num_shares = 12
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=-{curr_num_shares} tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # We expect to have 3 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [0.8, 0.7, 0.6]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_per_order,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
            num_trades_per_order=2,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Juraj): since this is correlated with the generated input,
        # it should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        exp = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:29:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:30:00+00:00
        end_timestamp=2022-08-05 09:33:00+00:00
        curr_num_shares=12.0
        diff_num_shares=-12.0
        tz=UTC
        extra_params={'ccxt_id': [0, 1, 2],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:30:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.1': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.2': Timestamp('2022-08-05 05:32:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:32:02+00:00 num_shares=-8.4 price=20.499999999999996]
        """
        self._test_get_fills(broker, exp)
        ccxt_fills = self._test_ccxt_fills(broker, orders, "test_ccxt_fills")
        self._test_ccxt_trades(broker, ccxt_fills, "test_ccxt_trades")

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_no_fill(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations with no fill.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:29:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:30:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:33:00+00:00")
        curr_num_shares = 12
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=-{curr_num_shares} tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # Use 0 fill rate for each order.
        fills_rate = 0.0
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fills_rate,
            oliprcom.LimitPriceComputerUsingSpread(0.5),
            ochorquco.StaticSchedulingChildOrderQuantityComputer(),
            num_trades_per_order=0,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Grisha): convert to a df and freeze instead of using string.
        # TODO(Juraj): since this is correlated with the generated input,
        # it should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        exp = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:29:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:30:00+00:00
        end_timestamp=2022-08-05 09:33:00+00:00
        curr_num_shares=12.0
        diff_num_shares=-12.0
        tz=UTC
        extra_params={'ccxt_id': [0, 1, 2],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:30:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.1': Timestamp('2022-08-05 05:31:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.id_added_to_parent_order.2': Timestamp('2022-08-05 05:32:02-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::bid_ask_market_data.start.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_orders::order_coroutines_created.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:30:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.1': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_orders::get_open_positions.done.2': Timestamp('2022-08-05 05:32:00-0400', tz='America/New_York'),
        '_submit_twap_orders::start': Timestamp('2022-08-05 05:29:55-0400', tz='America/New_York')}}]
        """
        self.assert_equal(submitted_orders, exp, fuzzy_match=True)
        # Assert fills.
        exp = "[]"
        self._test_get_fills(broker, exp)
        # Assert ccxt fills.
        ccxt_fills = self._test_ccxt_fills(broker, orders, "test_ccxt_fills")
        # Assert ccxt trades.
        self._test_ccxt_trades(broker, ccxt_fills, "test_ccxt_trades")


# #############################################################################
# TestCcxtBroker_V2_UsingFakeExchangeWithErrors
# #############################################################################


class TestCcxtBroker_V2_UsingFakeExchangeWithErrors(
    obcctmetc.MockExchangeTestCase
):
    # Mock CCXT Exchange for exceptions.
    abstract_ccxt_patch = umock.patch.object(obcaccbr, "ccxt", spec=obcaccbr.ccxt)

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test2()
        yield
        # Run after each test.
        self.tear_down_test2()

    def set_up_test2(self) -> None:
        self.set_up_test()
        self.abstract_ccxt_mock: umock.MagicMock = (
            self.abstract_ccxt_patch.start()
        )
        for e in obcmccex._EXCEPTIONS:
            setattr(self.abstract_ccxt_mock, e.__name__, e)

    def tear_down_test2(self) -> None:
        self.abstract_ccxt_patch.stop()
        self.tear_down_test()

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_orders1(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Test non-TWAP orders submission with errors.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:30:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:31:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:32:00+00:00")
        orders = self._get_test_orders(
            creation_timestamp, start_timestamp, end_timestamp
        )
        num_exceptions = 1
        actual_expected_orders = r"""
        order_id        creation_timestamp    asset_id  type_  \
        0         0 2022-08-05 05:30:55-04:00  1464553467  limit
        1         1 2022-08-05 05:30:55-04:00  1467591036  limit

                    start_timestamp             end_timestamp  curr_num_shares  \
        0 2022-08-05 05:31:00-04:00 2022-08-05 05:32:00-04:00           2500.0
        1 2022-08-05 05:31:00-04:00 2022-08-05 05:32:00-04:00           1000.0

        diff_num_shares                tz  \
        0             10.0  America/New_York
        1            -20.0  America/New_York

                                                extra_params
        0  {'stats': {'_submit_single_order_to_ccxt::star...
        1  {'stats': {'_submit_single_order_to_ccxt::star...
        """
        expected_fills = r"""
        [Fill: asset_id=1464553467 fill_id=0 timestamp=2022-08-05 09:30:59.500000+00:00 num_shares=10.0 price=20.5,
        Fill: asset_id=1467591036 fill_id=1 timestamp=2022-08-05 09:31:01.500000+00:00 num_shares=-18.0 price=15.0]
        """
        # Define the expected fills percents for each order.
        fills_percents = [1.0, 0.9]
        self._test_submit_orders_with_errors(
            orders,
            "limit",
            num_exceptions,
            actual_expected_orders,
            expected_fills,
            fills_percents,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_orders2(
        self, mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock
    ) -> None:
        """
        Test TWAP order submission with errors.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        orders_str = "\n".join(
            [
                "Order: order_id=0 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1464553467 type_=price@custom_twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-0.008 tz=America/New_York extra_params={}",
                "Order: order_id=1 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=6051632686 type_=price@custom_twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=0.01 tz=America/New_York extra_params={}",
            ]
        )
        # pylint: disable=line-too-long
        orders = oordorde.orders_from_string(orders_str)
        num_exceptions = 1
        actual_expected_orders = r"""
        order_id creation_timestamp asset_id type_ \
        0 0 2023-02-21 02:55:44.508525-05:00 1464553467 limit
        1 1 2023-02-21 02:55:44.508525-05:00 6051632686 limit
        2 2 2023-02-21 02:56:00-05:00 1464553467 limit
        3 3 2023-02-21 02:56:00-05:00 6051632686 limit
        4 4 2023-02-21 02:57:00-05:00 1464553467 limit
        5 5 2023-02-21 02:57:00-05:00 6051632686 limit
        6 6 2023-02-21 02:58:00-05:00 1464553467 limit
        7 7 2023-02-21 02:58:00-05:00 6051632686 limit
        8 8 2023-02-21 02:59:00-05:00 1464553467 limit
        9 9 2023-02-21 02:59:00-05:00 6051632686 limit
        start_timestamp end_timestamp curr_num_shares \
        0 2023-02-21 02:55:44.508525-05:00 2023-02-21 02:56:00-05:00 0.0
        1 2023-02-21 02:55:44.508525-05:00 2023-02-21 02:56:00-05:00 0.0
        2 2023-02-21 02:56:00-05:00 2023-02-21 02:57:00-05:00 0.0
        3 2023-02-21 02:56:00-05:00 2023-02-21 02:57:00-05:00 0.0
        4 2023-02-21 02:57:00-05:00 2023-02-21 02:58:00-05:00 0.0
        5 2023-02-21 02:57:00-05:00 2023-02-21 02:58:00-05:00 0.0
        6 2023-02-21 02:58:00-05:00 2023-02-21 02:59:00-05:00 0.0
        7 2023-02-21 02:58:00-05:00 2023-02-21 02:59:00-05:00 0.0
        8 2023-02-21 02:59:00-05:00 2023-02-21 03:00:00-05:00 0.0
        9 2023-02-21 02:59:00-05:00 2023-02-21 03:00:00-05:00 0.0
        diff_num_shares tz \
        0 -0.001 America/New_York
        1 0.002 America/New_York
        2 -0.001 America/New_York
        3 0.002 America/New_York
        4 -0.001 America/New_York
        5 0.002 America/New_York
        6 -0.001 America/New_York
        7 0.002 America/New_York
        8 -0.001 America/New_York
        9 0.002 America/New_York
        extra_params
        0 {'stats': {'_submit_twap_child_order::wave_id'...
        1 {'stats': {'_submit_twap_child_order::wave_id'...
        2 {'stats': {'_submit_twap_child_order::wave_id'...
        3 {'stats': {'_submit_twap_child_order::wave_id'...
        4 {'stats': {'_submit_twap_child_order::wave_id'...
        5 {'stats': {'_submit_twap_child_order::wave_id'...
        6 {'stats': {'_submit_twap_child_order::wave_id'...
        7 {'stats': {'_submit_twap_child_order::wave_id'...
        8 {'stats': {'_submit_twap_child_order::wave_id'...
        9 {'stats': {'_submit_twap_child_order::wave_id'...
        """
        expected_fills = r"""
        [Fill: asset_id=1464553467 fill_id=0 timestamp=2023-02-21 07:59:02+00:00 num_shares=-0.0036 price=20.499999999999996,
        Fill: asset_id=6051632686 fill_id=1 timestamp=2023-02-21 07:59:02+00:00 num_shares=0.0072 price=29.499999999999996]
        """
        # We expect to have 5 waves of orders submission.
        # Elements of the list reflect the fills percentage for each wave.
        fills_per_wave = [1.0, 0.8, 0.7, 0.6, 0.5]
        fills_per_order = self._get_fills_percents(len(orders), fills_per_wave)
        self._test_submit_orders_with_errors(
            orders,
            "price@custom_twap",
            num_exceptions,
            actual_expected_orders,
            expected_fills,
            fills_per_order,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders1(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        num_exceptions = 1
        actual_expected_orders = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'error_msg': 'Some error message',
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:04.500000-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 2,
        '_submit_single_order_to_ccxt::exception_on_retry.1': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:04.500000-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:04.500000-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        submitted_expected_orders = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [0],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:04.500000-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        expected_fills = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:31:04.500000+00:00 num_shares=1.0 price=20.5]
        """
        # We expect to have 1 wave of orders submission for 1 order.
        fill_percents = [1.0]
        self._test_submit_twap_orders_with_errors(
            num_exceptions,
            actual_expected_orders,
            submitted_expected_orders,
            expected_fills,
            fill_percents,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders2(
        self, mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock
    ) -> None:
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        num_exceptions = 2
        actual_expected_orders = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'error_msg': 'Some error message',
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 3,
        '_submit_single_order_to_ccxt::exception_on_retry.1': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::exception_on_retry.2': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        submitted_expected_orders = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [0],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        expected_fills = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:31:07+00:00 num_shares=1.0 price=20.5]
        """
        # We expect to have 1 wave of orders submission for 1 order.
        fill_percents = [1.0]
        self._test_submit_twap_orders_with_errors(
            num_exceptions,
            actual_expected_orders,
            submitted_expected_orders,
            expected_fills,
            fill_percents,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders3(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        num_exceptions = 3
        actual_expected_orders = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [-1],
        'error_msg': 'Some error message',
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:07.500000-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 3,
        '_submit_single_order_to_ccxt::exception_on_retry.1': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::exception_on_retry.2': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::exception_on_retry.3': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:07.500000-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:07.500000-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        submitted_expected_orders = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:07.500000-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        expected_fills = "[]"
        # We expect to have 1 wave for 1 orders submission.
        fill_percents = [1.0]
        self._test_submit_twap_orders_with_errors(
            num_exceptions,
            actual_expected_orders,
            submitted_expected_orders,
            expected_fills,
            fill_percents,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_partial_fill(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations with partial fill.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        num_exceptions = 2
        actual_expected_orders = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'error_msg': 'Some error message',
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 3,
        '_submit_single_order_to_ccxt::exception_on_retry.1': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::exception_on_retry.2': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        submitted_expected_orders = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [0],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        expected_fills = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:31:07+00:00 num_shares=0.5 price=20.5]
        """
        # We expect to have 1 wave for 1 orders submission.
        fill_percents = [0.5]
        self._test_submit_twap_orders_with_errors(
            num_exceptions,
            actual_expected_orders,
            submitted_expected_orders,
            expected_fills,
            fill_percents,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_no_fill(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations with no fill.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        num_exceptions = 2
        actual_expected_orders = r"""
        [Order:
        order_id=0
        creation_timestamp=2022-08-05 05:31:00-04:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 05:31:00-04:00
        end_timestamp=2022-08-05 05:32:00-04:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=America/New_York
        extra_params={'ccxt_id': [0],
        'error_msg': 'Some error message',
        'oms_parent_order_id': 1,
        'stats': {'_submit_single_order_to_ccxt::all_attempts_end.timestamp': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_single_order_to_ccxt::attempt_num': 3,
        '_submit_single_order_to_ccxt::exception_on_retry.1': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::exception_on_retry.2': 'Some error '
        'message',
        '_submit_single_order_to_ccxt::start.timestamp': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::bid_ask_market_data.start': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.created': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.limit_price_calculated': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.logged': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submission_started': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::child_order.submitted': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
        '_submit_twap_child_order::get_open_positions.done': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
        '_submit_twap_child_order::wave_id': 0,
        '_submit_twap_orders::aligned_with_next_wave.end': Timestamp('2022-08-05 05:31:55-0400', tz='America/New_York')}}]
        """
        submitted_expected_orders = r"""
        [Order:
        order_id=1
        creation_timestamp=2022-08-05 09:30:55+00:00
        asset_id=1464553467
        type_=limit
        start_timestamp=2022-08-05 09:31:00+00:00
        end_timestamp=2022-08-05 09:32:00+00:00
        curr_num_shares=0.0
        diff_num_shares=1.0
        tz=UTC
        extra_params={'ccxt_id': [0],
        'ccxt_symbol': 'ETH/USDT:USDT',
        'stats': {'_submit_twap_child_order::child_order.id_added_to_parent_order.0': Timestamp('2022-08-05 05:31:07-0400', tz='America/New_York'),
                '_submit_twap_child_order::start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::bid_ask_market_data.start.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_child_orders::order_coroutines_created.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.end': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::align_with_parent_order.start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York'),
                '_submit_twap_orders::get_open_positions.done.0': Timestamp('2022-08-05 05:31:00-0400', tz='America/New_York'),
                '_submit_twap_orders::start': Timestamp('2022-08-05 05:30:55-0400', tz='America/New_York')}}]
        """
        expected_fills = "[]"
        # We expect to have 1 wave for 1 orders submission.
        fill_percents = [0]
        self._test_submit_twap_orders_with_errors(
            num_exceptions,
            actual_expected_orders,
            submitted_expected_orders,
            expected_fills,
            fill_percents,
            num_trades_per_order=0,
            limit_price_computer=oliprcom.LimitPriceComputerUsingSpread(0.5),
            child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
        )

    def _test_submit_orders_with_errors(
        self,
        orders: List[oordorde.Order],
        orders_type: str,
        num_exceptions: int,
        actual_expected_orders: str,
        expected_fills: str,
        fill_percents: List[float],
        limit_price_computer=oliprcom.AbstractLimitPriceComputer,
        child_order_quantity_computer=ochorquco.AbstractChildOrderQuantityComputer,
        *,
        num_trades_per_order: int = 1,
    ) -> None:
        """
        Test non-twap type of orders.
        """
        # Get orders and postions.
        starting_positions = [
            {"info": {"positionAmt": 0}, "symbol": "ETH/USDT"},
        ]
        # Run TWAP submission.
        orders, broker = self._test_submit_orders(
            orders,
            orders_type,
            starting_positions,
            limit_price_computer=limit_price_computer,
            child_order_quantity_computer=child_order_quantity_computer,
            num_exceptions=num_exceptions,
            fill_percents=fill_percents,
            num_trades_per_order=num_trades_per_order,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.assert_equal(actual_orders, actual_expected_orders, fuzzy_match=True)
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Grisha): convert to a df and freeze instead of using string.
        # TODO(Juraj): since this is almost the same as the generated input, it should not be hardcoded,
        # instead it should be made programmatically possible to generate the expected output.
        self.check_string(submitted_orders)
        # TODO(Juraj): Assert final positions.
        # Assert fills.
        self._test_get_fills(broker, expected_fills)

    def _test_submit_twap_orders_with_errors(
        self,
        num_exceptions: int,
        actual_expected_orders: str,
        submitted_expected_orders: str,
        expected_fills: str,
        fill_percent: List[float],
        limit_price_computer=oliprcom.AbstractLimitPriceComputer,
        child_order_quantity_computer=ochorquco.AbstractChildOrderQuantityComputer,
        *,
        num_trades_per_order: int = 1,
    ) -> None:
        """
        Verify that a single TWAP buy order is submitted correctly over a
        single time interval.
        """
        creation_timestamp = pd.Timestamp("2022-08-05 09:30:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:31:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:32:00+00:00")
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} "
                + "asset_id=1464553467 "
                + f"type_=limit start_timestamp={start_timestamp} "
                + f"end_timestamp={end_timestamp} curr_num_shares=0.0 "
                + f"diff_num_shares=1.0 tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {"info": {"positionAmt": 0}, "symbol": "ETH/USDT"},
        ]
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fill_percent,
            num_exceptions=num_exceptions,
            num_trades_per_order=num_trades_per_order,
            limit_price_computer=limit_price_computer,
            child_order_quantity_computer=child_order_quantity_computer,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.assert_equal(actual_orders, actual_expected_orders, fuzzy_match=True)
        #
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Grisha): convert to a df and freeze instead of using string.
        # TODO(Juraj): since this is almost the same as the generated input, it
        # should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        self.assert_equal(
            submitted_orders, submitted_expected_orders, fuzzy_match=True
        )
        # TODO(Juraj): Assert final positions.
        # Assert fills.
        self._test_get_fills(broker, expected_fills)


# #############################################################################
# TestCcxtBroker_UsingFakeExchangeWithDynamicScheduler
# #############################################################################


class TestCcxtBroker_UsingFakeExchangeWithDynamicScheduler(
    obcctmetc.MockExchangeTestCase
):
    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_with_partial_fill(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Verify that a single TWAP sell order is submitted correctly over
        multiple iterations with partial fill.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:29:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:30:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:33:00+00:00")
        curr_num_shares = 12
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=-{curr_num_shares} tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # We expect to have 3 wave of orders submission for 1 order.
        fill_percents = [0.6, 0.5, 0.4]
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fill_percents,
            oliprcom.LimitPriceComputerUsingVolatility(0.5),
            ochorquco.DynamicSchedulingChildOrderQuantityComputer(),
            num_trades_per_order=2,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        submitted_orders = pprint.pformat(submitted_orders)
        # TODO(Juraj): since this is correlated with the generated input,
        # it should not be hardcoded, instead it should be made programmatically
        # possible to generate the expected output.
        self.check_string(
            submitted_orders, tag="test_submitted_orders", fuzzy_match=True
        )
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:32:02+00:00 num_shares=-10.559999999999999 price=31.0]
        """
        self._test_get_fills(broker, exp)
        # Assert ccxt fills.
        ccxt_fills = self._test_ccxt_fills(broker, orders, "test_ccxt_fills")
        # Assert ccxt trades.
        self._test_ccxt_trades(broker, ccxt_fills, "test_ccxt_trades")

    # Mocking the wave completion time threshold to be greater than the
    # execution frequency inorder to skip the first wave.
    @umock.patch(
        "oms.broker.ccxt.ccxt_broker._WAVE_COMPLETION_TIME_THRESHOLD", new=61
    )
    @umock.patch.object(
        obcaccbr.AbstractCcxtBroker, "_build_asset_id_to_ccxt_symbol_mapping"
    )
    def test_submit_twap_orders_skipping_first_wave(
        self,
        mock_build_asset_id_to_ccxt_symbol_mapping: umock.MagicMock,
    ) -> None:
        """
        Test case for submitting TWAP orders while skipping the first wave.
        """
        mock_build_asset_id_to_ccxt_symbol_mapping.return_value = {
            6051632686: "APE/USDT:USDT",
            1467591036: "BTC/USDT:USDT",
            1464553467: "ETH/USDT:USDT",
        }
        creation_timestamp = pd.Timestamp("2022-08-05 09:29:55+00:00")
        start_timestamp = pd.Timestamp("2022-08-05 09:30:00+00:00")
        end_timestamp = pd.Timestamp("2022-08-05 09:33:00+00:00")
        curr_num_shares = 12
        asset_id = 1464553467
        orders_str = "\n".join(
            [
                f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id={asset_id} type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares={curr_num_shares} diff_num_shares=-{curr_num_shares} tz=UTC extra_params={{}}",
            ]
        )
        # Get orders and positions.
        orders = oordorde.orders_from_string(orders_str)
        starting_positions = [
            {
                "info": {"positionAmt": curr_num_shares},
                "symbol": "ETH/USDT:USDT",
            },
        ]
        # We expect to have 3 wave of orders submission for 1 order.
        fill_percents = [0, 0.5, 0.5]
        # Run TWAP submission.
        orders, broker = self._test_submit_twap_orders(
            orders,
            starting_positions,
            fill_percents,
            oliprcom.LimitPriceComputerUsingVolatility(0.5),
            ochorquco.DynamicSchedulingChildOrderQuantityComputer(),
            num_trades_per_order=2,
        )
        submitted_orders = broker._previous_parent_orders
        actual_orders = pprint.pformat(orders)
        self.check_string(actual_orders)
        submitted_orders = pprint.pformat(submitted_orders)
        self.check_string(
            submitted_orders, tag="test_submitted_orders", fuzzy_match=True
        )
        # Assert fills.
        exp = r"""
        [Fill: asset_id=1464553467 fill_id=1 timestamp=2022-08-05 09:32:02+00:00 num_shares=-6.0 price=31.0]
        """
        self._test_get_fills(broker, exp)
        # Assert ccxt fills.
        ccxt_fills = self._test_ccxt_fills(broker, orders, "test_ccxt_fills")
        # Assert ccxt trades.
        self._test_ccxt_trades(broker, ccxt_fills, "test_ccxt_trades")
