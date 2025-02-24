import asyncio
from typing import Union

import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import oms.broker.broker as obrobrok
import oms.broker.broker_example as obrbrexa
import oms.db.oms_db as odbomdb
import oms.order.order_example as oororexa
import oms.order_processing.order_processor as ooprorpr
import oms.test.oms_db_helper as omtodh


class TestOrderProcessor1(omtodh.TestOmsDbHelper):
    @staticmethod
    async def broker_coroutine(
        broker: obrobrok.Broker,
        get_wall_clock_time: hdateti.GetWallClockTime,
    ) -> None:
        # We need to wait 1 sec to make sure that the OrderProcessor comes up first
        # and starts polling, avoiding a deadlock.
        await hasynci.sleep(1, get_wall_clock_time)
        # Create an order.
        order = oororexa.get_order_example1()
        order_type = order.type_
        # Submit the order to the broker.
        await broker.submit_orders([order], order_type)

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
        incremental = False
        self._asset_id_name = "asset_id"
        odbomdb.create_oms_tables(
            self.connection, incremental, self._asset_id_name
        )

    def tear_down_test(self) -> None:
        # Remove the OMS tables.
        odbomdb.remove_oms_tables(self.connection)

    def helper(
        self, termination_condition: Union[int, pd.Timestamp], exp: str
    ) -> None:
        """
        Create two coroutines, one with a `DatabaseBroker`, the other with an
        `OrderProcessor`.
        """
        #
        with hasynci.solipsism_context() as event_loop:
            # Build a DatabaseBroker.
            broker = obrbrexa.get_DatabaseBroker_example1(
                event_loop, self.connection
            )
            get_wall_clock_time = broker.market_data.get_wall_clock_time
            # Create a coroutine executing the Broker.
            broker_coroutine = self.broker_coroutine(broker, get_wall_clock_time)
            # Build an OrderProcessor.
            bar_duration_in_secs = 300
            delay_to_accept_in_secs = 3
            delay_to_fill_in_secs = 10
            max_wait_time_for_order_in_secs = 10
            order_processor = ooprorpr.OrderProcessor(
                self.connection,
                bar_duration_in_secs,
                termination_condition,
                max_wait_time_for_order_in_secs,
                delay_to_accept_in_secs,
                delay_to_fill_in_secs,
                broker,
                self._asset_id_name,
            )
            order_processor_coroutine = order_processor.run_loop()
            # Run.
            coroutines = [order_processor_coroutine, broker_coroutine]
            hasynci.run(asyncio.gather(*coroutines), event_loop=event_loop)
        #
        act = order_processor.get_execution_signature()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_submit_order1(self) -> None:
        """
        Submit one order and have the OrderProcessor accept that.
        """
        # Shut down after one order is received.
        termination_condition = 1
        exp = r"""start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        termination_condition=1
        num_accepted_orders=1
        num_filled_orders=1
        events=9
        2000-01-01 09:35:00-05:00: start
        2000-01-01 09:35:00-05:00: target_list_id=0 termination_condition=1 -> is_done=False
        2000-01-01 09:35:00-05:00: Waiting for orders in table self._submitted_orders_table_name='submitted_orders'
        2000-01-01 09:35:02-05:00: diff_num_rows=1
        2000-01-01 09:35:02-05:00: Waiting 3 seconds to simulate the delay for accepting the order list submission
        2000-01-01 09:35:05-05:00: Wait until fulfillment deadline=2000-01-01 09:40:00-05:00
        2000-01-01 09:40:00-05:00: Received 1 fills:
          Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:40:00-05:00 num_shares=100.0 price=999.9161531095003
        2000-01-01 09:40:00-05:00: target_list_id=1 termination_condition=1 -> is_done=True
        2000-01-01 09:40:00-05:00: Exiting loop: target_list_id=1, wall_clock_time=Timestamp('2000-01-01 09:40:00-0500', tz='America/New_York'), termination_condition=1
        """
        self.helper(termination_condition, exp)

    def test_submit_order2(self) -> None:
        """
        Submit one order and have the OrderProcessor accept that.
        """
        # Shut down at a certain time.
        termination_condition = pd.Timestamp("2000-01-01 09:40:15-05:00")
        exp = r"""start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        termination_condition=2000-01-01 09:40:15-05:00
        num_accepted_orders=1
        num_filled_orders=1
        events=9
        2000-01-01 09:35:00-05:00: start
        2000-01-01 09:35:00-05:00: wall_clock_time=Timestamp('2000-01-01 09:35:00-0500', tz='America/New_York') termination_condition=Timestamp('2000-01-01 09:40:15-0500', tz='UTC-05:00') -> wall_clock_time_tmp=Timestamp('2000-01-01 09:35:00-0500', tz='America/New_York') termination_condition_tmp=Timestamp('2000-01-01 09:40:00-0500', tz='UTC-05:00') -> is_done=False
        2000-01-01 09:35:00-05:00: Waiting for orders in table self._submitted_orders_table_name='submitted_orders'
        2000-01-01 09:35:02-05:00: diff_num_rows=1
        2000-01-01 09:35:02-05:00: Waiting 3 seconds to simulate the delay for accepting the order list submission
        2000-01-01 09:35:05-05:00: Wait until fulfillment deadline=2000-01-01 09:40:00-05:00
        2000-01-01 09:40:00-05:00: Received 1 fills:
          Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:40:00-05:00 num_shares=100.0 price=999.9161531095003
        2000-01-01 09:40:00-05:00: wall_clock_time=Timestamp('2000-01-01 09:40:00-0500', tz='America/New_York') termination_condition=Timestamp('2000-01-01 09:40:15-0500', tz='UTC-05:00') -> wall_clock_time_tmp=Timestamp('2000-01-01 09:40:00-0500', tz='America/New_York') termination_condition_tmp=Timestamp('2000-01-01 09:40:00-0500', tz='UTC-05:00') -> is_done=True
        2000-01-01 09:40:00-05:00: Exiting loop: target_list_id=1, wall_clock_time=Timestamp('2000-01-01 09:40:00-0500', tz='America/New_York'), termination_condition=Timestamp('2000-01-01 09:40:15-0500', tz='UTC-05:00')
        """
        self.helper(termination_condition, exp)

    def test_submit_order_and_timeout1(self) -> None:
        """
        Test OrderProcessor timing out.
        """
        # Shut down after two orders are received, but the DatabaseBroker sends only
        # one, so the OrderProcessor times out.
        termination_condition = 2
        exp = "Dummy"
        with self.assertRaises(TimeoutError):
            self.helper(termination_condition, exp)

    def test_submit_order_and_timeout2(self) -> None:
        """
        Test OrderProcessor timing out.
        """
        # Shut down the OrderProcessor after 1 hour, but the DatabaseBroker sends
        # only one order at 9:35, so the OrderProcessor times out.
        termination_condition = pd.Timestamp("2000-01-01 10:30:00-05:00")
        exp = "Dummy"
        with self.assertRaises(TimeoutError):
            self.helper(termination_condition, exp)
