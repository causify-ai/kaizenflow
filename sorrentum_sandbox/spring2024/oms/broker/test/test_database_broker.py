import asyncio
import logging

import pytest

import helpers.hasyncio as hasynci
import oms.broker.broker_example as obrbrexa
import oms.broker.database_broker as obrdabro
import oms.broker.test.broker_helper as ombtbh
import oms.db.oms_db as odbomdb
import oms.order.order as oordorde
import oms.order.order_example as oororexa
import oms.order_processing.order_processor as ooprorpr
import oms.test.oms_db_helper as omtodh

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestDatabaseBroker1
# #############################################################################


class TestDatabaseBroker1(omtodh.TestOmsDbHelper):
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
        # Create OMS tables.
        asset_id_name = "asset_id"
        incremental = False
        odbomdb.create_oms_tables(self.connection, incremental, asset_id_name)

    def tear_down_test(self) -> None:
        # Remove the OMS tables.
        odbomdb.remove_oms_tables(self.connection)

    async def get_order_processor_coroutine(
        self, broker: obrdabro.DatabaseBroker
    ) -> None:
        """
        Create an OrderProcessor and wait for submitted orders.
        """
        bar_duration_in_secs = 300
        # Dummy value.
        termination_condition = 3
        delay_to_accept_in_secs = 2
        delay_to_fill_in_secs = 1
        max_wait_time_for_order_in_secs = 10
        asset_id_name = "asset_id"
        order_processor = ooprorpr.OrderProcessor(
            self.connection,
            bar_duration_in_secs,
            termination_condition,
            max_wait_time_for_order_in_secs,
            delay_to_accept_in_secs,
            delay_to_fill_in_secs,
            broker,
            asset_id_name,
        )
        await order_processor._enqueue_orders()

    def helper(self, order: oordorde.Order, expected_fills: str) -> None:
        with hasynci.solipsism_context() as event_loop:
            # Create the coroutines.
            broker = obrbrexa.get_DatabaseBroker_example1(
                event_loop, self.connection
            )
            order_processor_coroutine = self.get_order_processor_coroutine(broker)
            broker_coroutine = ombtbh._get_broker_coroutine(broker, order)
            coroutines = [order_processor_coroutine, broker_coroutine]
            # Run.
            results = hasynci.run(
                asyncio.gather(*coroutines), event_loop=event_loop
            )
            # Check.
            fills = results[1]
            self.assertEqual(len(fills), 1)
            actual_fills = str(fills[0])
            self.assert_equal(actual_fills, expected_fills, fuzzy_match=True)

    def test1(self) -> None:
        """
        Test submitting orders to a DatabaseBroker.
        """
        order = oororexa.get_order_example1()
        expected_order = """
        Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        self.assert_equal(str(order), expected_order, fuzzy_match=True)
        #
        expected_fills = r"""
        Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:40:00-05:00 num_shares=100.0 price=999.9161531095003
        """
        self.helper(order, expected_fills)
