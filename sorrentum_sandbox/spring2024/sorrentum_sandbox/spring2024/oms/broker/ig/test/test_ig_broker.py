# import asyncio
# import datetime
# import logging
# from typing import Optional
#
# import pandas as pd
# import pytest
#
# import helpers.hasyncio as hasynci
# import helpers.hunit_test as hunitest
# import market_data as mdata
# import market_data_lime as mdlime
# import oms
# import oms.broker.ig.ig_broker_example as obiibrex
#
# _LOG = logging.getLogger(__name__)
#
#
# class TestIgBroker1(hunitest.TestCase):
#     @staticmethod
#     async def place_order1(
#         event_loop: Optional[asyncio.AbstractEventLoop],
#     ) -> None:
#         # TODO(gp): Enable the test with dry_run=True and a check for market open
#         #  so we can interact with the RT DB.
#         # Build Broker object.
#         asset_id = 15151
#         asset_ids = [asset_id]
#         market_data = mdlime.get_IgRealTimeMarketData_example1(asset_ids)
#         if mdata.skip_test_since_not_online(market_data):
#             pytest.skip("Market not on-line")
#         # Real-time.
#         broker = obiibrex.get_ig_broker_example1(event_loop, market_data)
#         # Build Order object.
#         wall_clock_timestamp = pd.Timestamp(datetime.datetime.now(), tz="UTC")
#         type_ = "price@twap"
#         start_timestamp = wall_clock_timestamp
#         order_duration_in_mins = 5
#         freq = f"{order_duration_in_mins}T"
#         # end_timestamp = start_timestamp + pd.DateOffset(minutes=5)
#         # Align on 5 mins.
#         end_timestamp = start_timestamp.ceil(freq)
#         # TODO(gp): This should be retrieved from the OMS.
#         curr_num_shares = 0
#         diff_num_shares = 100
#         order = oms.Order(
#             wall_clock_timestamp,
#             asset_id,
#             type_,
#             start_timestamp,
#             end_timestamp,
#             curr_num_shares,
#             diff_num_shares,
#         )
#         _LOG.info("order=\n%s", order)
#         # Do not submit order to IG broker.
#         dry_run = True
#         file_name = await broker.submit_orders([order], dry_run=dry_run)
#         _LOG.info("file_name=%s", file_name)
#
#     def test_place_order1(self) -> None:
#         """
#         Place an example trade to the paper-trading system.
#         """
#         event_loop = None
#         hasynci.run(self.place_order1(event_loop), event_loop=event_loop)
