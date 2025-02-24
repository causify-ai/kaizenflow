# import asyncio
# import datetime
# import logging
# from typing import Any, Dict, Optional
#
# import pandas as pd
# import pytest
#
# import helpers.hasyncio as hasynci
# import helpers.hprint as hprint
# import helpers.hunit_test as hunitest
# import market_data as mdata
# import market_data_lime as mdlime
# import oms
# import oms.broker.ig.ig_broker_example as obiibrex
#
# _LOG = logging.getLogger(__name__)
#
#
# def _get_order(
#    asset_id: int,
#    wall_clock_timestamp: pd.Timestamp,
#    order_type: str,
#    order_duration_in_mins: int,
# ) -> oms.Order:
#    freq = f"{order_duration_in_mins}T"
#    start_timestamp = wall_clock_timestamp.ceil(freq)
#    end_timestamp = start_timestamp + pd.DateOffset(
#        minutes=order_duration_in_mins
#    )
#    curr_num_shares = 0
#    diff_num_shares = 100
#    order = oms.Order(
#        wall_clock_timestamp,
#        asset_id,
#        order_type,
#        start_timestamp,
#        end_timestamp,
#        curr_num_shares,
#        diff_num_shares,
#    )
#    return order
#
#
# class TestIgBroker1(hunitest.TestCase):
#    @staticmethod
#    async def place_order1(
#        event_loop: asyncio.AbstractEventLoop,
#        order_extra_params: Optional[Dict[str, Any]],
#        order_dst_file_name: Optional[str],
#    ) -> str:
#        """
#        Place an order saving the order on disk and capture its signature.
#        """
#        # Build Broker object.
#        asset_id = 17085
#        replayed_delay_in_mins_or_timestamp = 2 * 60
#        market_data = mdlime.get_IgReplayedMarketData_example1(
#            event_loop, replayed_delay_in_mins_or_timestamp=replayed_delay_in_mins_or_timestamp
#        )
#        # Align on 5 mins.
#        order_duration_in_mins = 5
#        broker = obiibrex.get_IgBroker_example1(
#            market_data, order_duration_in_mins, order_extra_params, order_dst_file_name
#        )
#        # Build Order object.
#        wall_clock_timestamp = market_data.get_wall_clock_time()
#        _LOG.debug(hprint.to_str("wall_clock_timestamp"))
#        order_type = "price@end"
#        order = _get_order(
#            asset_id, wall_clock_timestamp, order_type, order_duration_in_mins
#        )
#        _LOG.info("order=\n%s", order)
#        dry_run = False
#        # Use _submit_orders to avoid to wait for order accepted.
#        file_name = await broker._submit_orders(
#            [order], wall_clock_timestamp, dry_run=dry_run
#        )
#        _LOG.info("file_name=%s", file_name)
#        # Compute dir signature.
#        include_file_content = True
#        remove_dir_name = True
#        txt = hunitest.get_dir_signature(
#            order_dst_file_name, include_file_content, remove_dir_name=remove_dir_name
#        )
#        return txt
#
#    @staticmethod
#    async def place_order2() -> None:
#        """
#        Place order to system in dry-run mode.
#        """
#        # TODO(gp): Enable the test with dry_run=True and a check for market open
#        #  so we can interact with the RT DB.
#        asset_id = 15151
#        asset_ids = [asset_id]
#        market_data = mdlime.get_IgRealTimeMarketData_example1(asset_ids)
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        # Build Broker object.
#        stratigy_id = "SAU1"
#        liveness = "CANDIDATE"
#        instance_type = "QA"
#        # Align on 5 mins.
#        order_duration_in_mins = 5
#        order_extra_params = None
#        broker = obiibrex.get_IgBroker_prod_instance1(
#            market_data,
#            strategy_id,
#            liveness,
#            instance_type,
#            order_duration_in_mins,
#            order_extra_params
#        )
#        # Build Order object.
#        wall_clock_timestamp = pd.Timestamp(datetime.datetime.now(), tz="UTC")
#        # TODO(gp): This should be retrieved from the OMS.
#        type_ = "price@twap"
#        order = _get_order(
#            asset_id, wall_clock_timestamp, type_, order_duration_in_mins
#        )
#        _LOG.info("order=\n%s", order)
#        # Do not submit order to broker.
#        dry_run = True
#        file_name = await broker.submit_orders([order], dry_run=dry_run)
#        _LOG.info("file_name=%s", file_name)
#
#    # #########################################################################
#
#    def test_place_order1(self) -> None:
#        """
#        Place an example trade writing on a local file.
#        """
#        order_extra_params = None
#        order_dst_file_name = self.get_scratch_space()
#        with hasynci.solipsism_context() as event_loop:
#            coro = self.place_order1(
#                event_loop, order_extra_params, order_dst_file_name
#            )
#            txt = hasynci.run(coro, event_loop=event_loop)
#            self.check_string(txt)
#
#    def test_place_order2(self) -> None:
#        """
#        Place an example trade writing on a local file using extra params.
#        """
#        order_extra_params = {"PASSIVEONLY": "Reload"}
#        order_dst_file_name = self.get_scratch_space()
#        with hasynci.solipsism_context() as event_loop:
#            coro = self.place_order1(
#                event_loop, order_extra_params, order_dst_file_name
#            )
#            txt = hasynci.run(coro, event_loop=event_loop)
#            self.check_string(txt)
#
#    def test_place_order3(self) -> None:
#        """
#        Place an example trade to the paper-trading system.
#        """
#        coro = self.place_order2()
#        #
#        event_loop = None
#        hasynci.run(coro, event_loop=event_loop)
