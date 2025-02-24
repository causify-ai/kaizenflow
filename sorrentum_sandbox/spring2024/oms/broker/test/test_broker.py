import logging
from typing import List

import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.broker.broker as obrobrok
import oms.fill as omfill
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# #############################################################################
# Test_fill_orders1
# #############################################################################


# TODO(gp): Add more testing based on the coverage.
class Test_fill_orders1(hunitest.TestCase):
    @staticmethod
    def get_order_example(
        type_: str, start_timestamp: pd.Timestamp
    ) -> oordorde.Order:
        creation_timestamp = start_timestamp
        asset_id = 101
        end_timestamp = pd.Timestamp(
            "2000-01-01 09:35:00-05:00", tz="America/New_York"
        )
        curr_num_shares = 0
        diff_num_shares = 100
        order_id = 0
        # Build Order.
        order = oordorde.Order(
            creation_timestamp,
            asset_id,
            type_,
            start_timestamp,
            end_timestamp,
            curr_num_shares,
            diff_num_shares,
            order_id=order_id,
        )
        return order

    @staticmethod
    def reset() -> None:
        omfill.Fill._fill_id = 0
        oordorde.Order._order_id = 0

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        self.reset()

    def tear_down_test(self) -> None:
        self.reset()

    def helper(
        self, asset_ids: List[int], order: oordorde.Order, mode: str, exp: str
    ) -> List[omfill.Fill]:
        # We need to reset the counter to get Fills and Orders independent on
        # the previous runs.
        self.reset()
        with hasynci.solipsism_context() as event_loop:
            start_datetime = pd.Timestamp("2000-01-01 09:29:00-05:00")
            end_datetime = pd.Timestamp("2000-01-02 09:30:00-05:00")
            if asset_ids == [101]:
                exp_data = """
                                                     start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
                end_datetime
                2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00  998.90  998.96   998.930     994       101  998.930
                2000-01-01 09:32:00-05:00 2000-01-01 09:31:00-05:00 2000-01-01 09:32:01-05:00  998.17  998.19   998.180    1015       101  998.180
                2000-01-01 09:33:00-05:00 2000-01-01 09:32:00-05:00 2000-01-01 09:33:01-05:00  997.39  997.44   997.415     956       101  997.415
                2000-01-01 09:34:00-05:00 2000-01-01 09:33:00-05:00 2000-01-01 09:34:01-05:00  997.66  997.74   997.700    1015       101  997.700
                2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44   997.425     978       101  997.425
                2000-01-01 09:36:00-05:00 2000-01-01 09:35:00-05:00 2000-01-01 09:36:01-05:00  997.54  997.55   997.545     996       101  997.545
                2000-01-01 09:37:00-05:00 2000-01-01 09:36:00-05:00 2000-01-01 09:37:01-05:00  998.38  998.42   998.400    1043       101  998.400
                2000-01-01 09:38:00-05:00 2000-01-01 09:37:00-05:00 2000-01-01 09:38:01-05:00  999.24  999.38   999.310    1025       101  999.310
                2000-01-01 09:39:00-05:00 2000-01-01 09:38:00-05:00 2000-01-01 09:39:01-05:00  999.71  999.72   999.715    1009       101  999.715
                """
            elif asset_ids == [101, 102]:
                exp_data = r"""
                                                     start_datetime              timestamp_db      bid      ask  midpoint  volume  asset_id     price
                end_datetime
                2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00   998.90   998.96   998.930     994       101   998.930
                2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00  1000.03  1000.12  1000.075     996       102  1000.075
                2000-01-01 09:32:00-05:00 2000-01-01 09:31:00-05:00 2000-01-01 09:32:01-05:00   998.17   998.19   998.180    1015       101   998.180
                2000-01-01 09:32:00-05:00 2000-01-01 09:31:00-05:00 2000-01-01 09:32:01-05:00  1001.39  1001.41  1001.400    1069       102  1001.400
                2000-01-01 09:33:00-05:00 2000-01-01 09:32:00-05:00 2000-01-01 09:33:01-05:00   997.39   997.44   997.415     956       101   997.415
                2000-01-01 09:33:00-05:00 2000-01-01 09:32:00-05:00 2000-01-01 09:33:01-05:00  1002.62  1002.64  1002.630    1010       102  1002.630
                2000-01-01 09:34:00-05:00 2000-01-01 09:33:00-05:00 2000-01-01 09:34:01-05:00   997.66   997.74   997.700    1015       101   997.700
                2000-01-01 09:34:00-05:00 2000-01-01 09:33:00-05:00 2000-01-01 09:34:01-05:00  1002.11  1002.13  1002.120    1009       102  1002.120
                2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00   997.41   997.44   997.425     978       101   997.425
                2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  1001.81  1001.83  1001.820     983       102  1001.820
                2000-01-01 09:36:00-05:00 2000-01-01 09:35:00-05:00 2000-01-01 09:36:01-05:00   997.54   997.55   997.545     996       101   997.545
                2000-01-01 09:36:00-05:00 2000-01-01 09:35:00-05:00 2000-01-01 09:36:01-05:00  1001.28  1001.29  1001.285    1008       102  1001.285
                2000-01-01 09:37:00-05:00 2000-01-01 09:36:00-05:00 2000-01-01 09:37:01-05:00   998.38   998.42   998.400    1043       101   998.400
                2000-01-01 09:37:00-05:00 2000-01-01 09:36:00-05:00 2000-01-01 09:37:01-05:00  1001.85  1001.91  1001.880    1018       102  1001.880
                2000-01-01 09:38:00-05:00 2000-01-01 09:37:00-05:00 2000-01-01 09:38:01-05:00   999.24   999.38   999.310    1025       101   999.310
                2000-01-01 09:38:00-05:00 2000-01-01 09:37:00-05:00 2000-01-01 09:38:01-05:00  1001.80  1001.81  1001.805     949       102  1001.805
                2000-01-01 09:39:00-05:00 2000-01-01 09:38:00-05:00 2000-01-01 09:39:01-05:00   999.71   999.72   999.715    1009       101   999.715
                2000-01-01 09:39:00-05:00 2000-01-01 09:38:00-05:00 2000-01-01 09:39:01-05:00  1002.55  1002.57  1002.560     984       102  1002.560
                """
            else:
                raise ValueError(f"Invalid asset_ids={asset_ids}")
            replayed_delay_in_mins_or_timestamp = pd.Timestamp(
                "2000-01-01 09:40:00-05:00"
            )
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example5(
                event_loop,
                start_datetime,
                end_datetime,
                asset_ids,
                replayed_delay_in_mins_or_timestamp=replayed_delay_in_mins_or_timestamp,
                use_midpoint_as_price=True,
            )
            wall_clock_time = market_data.get_wall_clock_time()
            _LOG.debug(hprint.to_str("wall_clock_time"))
            self.assert_equal(str(wall_clock_time), "2000-01-01 09:40:00-05:00")
            # Use the index.
            timestamp_col = "end_datetime"
            data = market_data.get_data_for_interval(
                pd.Timestamp("2000-01-01 09:30:00-05:00"),
                pd.Timestamp("2000-01-01 09:40:00-05:00"),
                timestamp_col,
                asset_ids,
            )
            act_data = hpandas.df_to_str(data, num_rows=None)
            _LOG.debug("data=\n" + act_data)
            self.assert_equal(act_data, exp_data, fuzzy_match=True)
            # Run
            _LOG.debug(hprint.to_str("order"))
            orders = [order]
            timestamp_col = "end_datetime"
            column_remap = None
            if mode == "fill_orders_fully_at_once":
                fills = obrobrok.fill_orders_fully_at_once(
                    market_data, timestamp_col, column_remap, orders
                )
            elif mode == "fill_orders_fully_twap":
                freq_as_pd_string = "1T"
                fills = obrobrok.fill_orders_fully_twap(
                    market_data,
                    timestamp_col,
                    column_remap,
                    orders,
                    freq_as_pd_string=freq_as_pd_string,
                )
            else:
                raise ValueError(f"Invalid mode='{mode}'")
            for fill in fills:
                fill.price = fill.price.round(3)
            # Check.
            act = "\n".join([str(order), str(fills)])
            self.assert_equal(act, exp, fuzzy_match=True, ignore_line_breaks=True)
        return fills

    # /////////////////////////////////////////////////////////////////////////

    def test_fill_orders_fully_at_once1(self) -> None:
        """
        Test:
        - type_ = "price@twap"
        - mode = "fill_orders_fully_at_once"
        """
        type_ = "price@twap"
        start_timestamp = pd.Timestamp(
            "2000-01-01 09:30:00-05:00", tz="America/New_York"
        )
        order = self.get_order_example(type_, start_timestamp)
        #
        exp = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        [Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=997.93]
        """
        asset_ids = [101]
        mode = "fill_orders_fully_at_once"
        fills = self.helper(asset_ids, order, mode, exp)
        #                                      start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
        # end_datetime
        # 2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00  998.90  998.96   998.930     994       101  998.930
        # 2000-01-01 09:32:00-05:00 2000-01-01 09:31:00-05:00 2000-01-01 09:32:01-05:00  998.17  998.19   998.180    1015       101  998.180
        # 2000-01-01 09:33:00-05:00 2000-01-01 09:32:00-05:00 2000-01-01 09:33:01-05:00  997.39  997.44   997.415     956       101  997.415
        # 2000-01-01 09:34:00-05:00 2000-01-01 09:33:00-05:00 2000-01-01 09:34:01-05:00  997.66  997.74   997.700    1015       101  997.700
        # 2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44   997.425     978       101  997.425
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(
            (998.930 + 998.180 + 997.415 + 997.700 + 997.425) / 5.0,
            fills[0].price,
        )
        # There should be no difference.
        asset_ids = [101, 102]
        self.helper(asset_ids, order, mode, exp)

    def test_fill_orders_fully_at_once2(self) -> None:
        """
        Test:
        - type_ = "price@end"
        - mode = "fill_orders_fully_at_once"
        """
        type_ = "price@end"
        start_timestamp = pd.Timestamp(
            "2000-01-01 09:30:00-05:00", tz="America/New_York"
        )
        order = self.get_order_example(type_, start_timestamp)
        #
        exp = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101 type_=price@end start_timestamp=2000-01-01 09:30:00-05:00 end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        [Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=997.425]
        """
        asset_ids = [101]
        mode = "fill_orders_fully_at_once"
        fills = self.helper(asset_ids, order, mode, exp)
        #                                      start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
        # end_datetime
        # 2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44   997.425     978       101  997.425
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(fills[0].price, 997.425)
        # There should be no difference.
        asset_ids = [101, 102]
        self.helper(asset_ids, order, mode, exp)

    def test_fill_orders_fully_at_once3(self) -> None:
        """
        Test:
        - type_ = "midpoint@end"
        - mode = "fill_orders_fully_at_once"
        """
        type_ = "midpoint@end"
        start_timestamp = pd.Timestamp(
            "2000-01-01 09:30:00-05:00", tz="America/New_York"
        )
        order = self.get_order_example(type_, start_timestamp)
        #
        exp = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101
            type_=midpoint@end start_timestamp=2000-01-01 09:30:00-05:00
            end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0
            diff_num_shares=100.0 tz=America/New_York extra_params={}
        [Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=997.425]
        """
        asset_ids = [101]
        mode = "fill_orders_fully_at_once"
        fills = self.helper(asset_ids, order, mode, exp)
        #                                      start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
        # end_datetime
        # 2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44   997.425     978       101  997.425
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(fills[0].price, 997.425)
        # There should be no difference.
        asset_ids = [101, 102]
        self.helper(asset_ids, order, mode, exp)

    def test_fill_orders_fully_at_once4(self) -> None:
        """
        Test that `Order` is filled when timestamp is not aligned to 1-minute
        frequency, e.g., "2000-01-01 09:31:10-05:00".

        - `type_ = "price@start"`
        - `mode = "fill_orders_fully_at_once"`
        """
        type_ = "price@start"
        start_timestamp = pd.Timestamp(
            "2000-01-01 09:31:10-05:00", tz="America/New_York"
        )
        order = self.get_order_example(type_, start_timestamp)
        #
        exp = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:31:10-05:00 asset_id=101
            type_=price@start start_timestamp=2000-01-01 09:31:10-05:00
            end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0
            diff_num_shares=100.0 tz=America/New_York extra_params={}
        [Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:35:00-05:00 num_shares=100.0 price=998.93]
        """
        mode = "fill_orders_fully_at_once"
        asset_ids = [101]
        fills = self.helper(asset_ids, order, mode, exp)
        #                                      start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
        # end_datetime
        # 2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00  998.90  998.96   998.930     994       101  998.930
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(fills[0].price, 998.93)
        # There should be no difference.
        asset_ids = [101, 102]
        self.helper(asset_ids, order, mode, exp)

    # /////////////////////////////////////////////////////////////////////////

    def test_fill_orders_fully_twap1(self) -> None:
        """
        Test:
        - type_ = "price@twap"
        - mode = "fill_orders_fully_twap"
        """
        type_ = "price@twap"
        start_timestamp = pd.Timestamp(
            "2000-01-01 09:30:00-05:00", tz="America/New_York"
        )
        order = self.get_order_example(type_, start_timestamp)
        #
        exp = r"""
        Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00
            asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:30:00-05:00
            end_timestamp=2000-01-01 09:35:00-05:00 curr_num_shares=0.0
            diff_num_shares=100.0 tz=America/New_York extra_params={}
        [Fill: asset_id=101 fill_id=0 timestamp=2000-01-01 09:31:00-05:00
        num_shares=20.0 price=998.93,
        Fill: asset_id=101 fill_id=1 timestamp=2000-01-01 09:32:00-05:00
        num_shares=20.0 price=998.18,
        Fill: asset_id=101 fill_id=2 timestamp=2000-01-01 09:33:00-05:00
        num_shares=20.0 price=997.415,
        Fill: asset_id=101 fill_id=3 timestamp=2000-01-01 09:34:00-05:00
        num_shares=20.0 price=997.7,
        Fill: asset_id=101 fill_id=4 timestamp=2000-01-01 09:35:00-05:00
        num_shares=20.0 price=997.425]
        """
        asset_ids = [101]
        mode = "fill_orders_fully_twap"
        fills = self.helper(asset_ids, order, mode, exp)
        #                                      start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id    price
        # end_datetime
        # 2000-01-01 09:31:00-05:00 2000-01-01 09:30:00-05:00 2000-01-01 09:31:01-05:00  998.90  998.96   998.930     994       101  998.930
        # ...
        # 2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44   997.425     978       101  997.425
        self.assertEqual(len(fills), 5)
        self.assertAlmostEqual(fills[0].price, 998.930)
        self.assertAlmostEqual(fills[4].price, 997.425)
        # There should be no difference.
        asset_ids = [101, 102]
        self.helper(asset_ids, order, mode, exp)
