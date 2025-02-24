import asyncio
import logging

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.broker.broker_example as obrbrexa
import oms.broker.test.broker_helper as ombtbh
import oms.order.order as oordorde
import oms.order.order_example as oororexa

_LOG = logging.getLogger(__name__)

# #############################################################################
# TestDataFrameBroker1
# #############################################################################


class TestDataFrameBroker1(hunitest.TestCase):
    async def get_broker_coroutine(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Submit orders to a DataFrameBroker.
        """
        # Build a DataFrameBroker.
        broker = obrbrexa.get_DataFrameBroker_example1(event_loop)
        # Submit an order.
        order = oororexa.get_order_example2()
        orders = [order]
        await broker.submit_orders(orders, order.type_)
        # Check fills.
        fills = broker.get_fills()
        self.assertEqual(len(fills), 1)
        actual_fills = str(fills[0])
        expected_fills = r"""Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=1000.3449750508295
        """
        self.assert_equal(actual_fills, expected_fills, fuzzy_match=True)

    def test_submit_and_fill1(self) -> None:
        event_loop = None
        coro = self.get_broker_coroutine(event_loop)
        hasynci.run(coro, event_loop=event_loop)

    def test_submit_market_orders(self) -> None:
        """
        Test `_submit_market_orders()` when an empty order list is passed.
        """
        event_loop = None
        # Build a DataFrameBroker.
        broker = obrbrexa.get_DataFrameBroker_example1(event_loop)
        # Initialize test variables.
        order = []
        wall_clock_timestamp = pd.Timestamp("2024-02-28T12:00:00+00:00")
        dry_run = True
        # Check.
        actual = str(
            hasynci.run(
                broker._submit_market_orders(
                    order, wall_clock_timestamp, dry_run=dry_run
                ),
                event_loop,
            )
        )
        expected = r"""
        ('dummy_order_receipt', Empty DataFrame
        Columns: []
        Index: [])
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_submit_twap_orders(self) -> None:
        """
        Test `_submit_twap_orders()` when an empty order list is passed.
        """
        event_loop = None
        # Build a DataFrameBroker.
        broker = obrbrexa.get_DataFrameBroker_example1(event_loop)
        # Initialize test variables.
        order = []
        # Check.
        actual = str(hasynci.run(broker._submit_twap_orders(order), event_loop))
        expected = r"""
        ('dummy_order_receipt', [])
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################
# TestDataFrameBroker2
# #############################################################################


class TestDataFrameBroker2(hunitest.TestCase):
    def helper(self, order: oordorde.Order, expected_fills: str) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Build a coroutine with the Broker.
            start_datetime = pd.Timestamp(
                "2000-01-01 09:30:00-05:00", tz="America/New_York"
            )
            end_datetime = pd.Timestamp(
                "2000-01-01 09:50:00-05:00", tz="America/New_York"
            )
            asset_ids = [101]
            market_data, _ = mdata.get_ReplayedTimeMarketData_example5(
                event_loop,
                start_datetime,
                end_datetime,
                asset_ids,
            )
            broker = obrbrexa.get_DataFrameBroker_example1(
                event_loop, market_data=market_data
            )
            broker_coroutine = ombtbh._get_broker_coroutine(broker, order)
            # Run.
            coroutines = [broker_coroutine]
            results = hasynci.run(
                asyncio.gather(*coroutines), event_loop=event_loop
            )
            # Check.
            fills = results[0]
            self.assertEqual(len(fills), 1)
            actual = str(fills[0])
            self.assert_equal(actual, expected_fills, fuzzy_match=True)

    def test_collect_spread_buy(self) -> None:
        order = oororexa.get_order_example3(0.0)
        expected_order = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.0@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=998.03
        """
        self.helper(order, expected_fills)

    def test_collect_spread_sell(self) -> None:
        order = oororexa.get_order_example3(0.0, -100)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.0@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=-100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=-100.0 price=998.0575
        """
        self.helper(order, expected_fills)

    def test_cross_spread_buy(self) -> None:
        order = oororexa.get_order_example3(1.0)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_1.0@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=998.0575
        """
        self.helper(order, expected_fills)

    def test_cross_spread_sell(self) -> None:
        order = oororexa.get_order_example3(1.0, -100)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_1.0@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=-100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=-100.0 price=998.03
        """
        self.helper(order, expected_fills)

    def test_midpoint_buy(self) -> None:
        order = oororexa.get_order_example3(0.5)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.5@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=998.04375
        """
        self.helper(order, expected_fills)

    def test_midpoint_sell(self) -> None:
        order = oororexa.get_order_example3(0.5, -100)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.5@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=-100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=-100.0 price=998.04375
        """
        self.helper(order, expected_fills)

    def test_quarter_spread_buy(self) -> None:
        order = oororexa.get_order_example3(0.75)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.75@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=998.0506250000001
        """
        self.helper(order, expected_fills)

    def test_quarter_spread_sell(self) -> None:
        order = oororexa.get_order_example3(0.75, -100)
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:29:00-05:00 asset_id=101 type_=partial_spread_0.75@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=-100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=-100.0 price=998.036875
        """
        self.helper(order, expected_fills)
