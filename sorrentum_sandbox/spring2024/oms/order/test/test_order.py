import logging

import pandas as pd

import helpers.hunit_test as hunitest
import oms.order.order as oordorde
import oms.order.order_example as oororexa

_LOG = logging.getLogger(__name__)


class TestOrder1(hunitest.TestCase):
    def helper(self, order: oordorde.Order, expected_order_as_str: str) -> None:
        """
        Test building and serializing an Order.
        """
        # Check.
        order_as_str = str(order)
        expected_order_as_str = expected_order_as_str.replace("\n", " ")
        self.assert_equal(order_as_str, expected_order_as_str, fuzzy_match=True)
        # Deserialize from string.
        order_from_string = oordorde.Order.from_string(order_as_str)
        # Check.
        order_from_string = str(order_from_string)
        self.assert_equal(
            order_from_string, expected_order_as_str, fuzzy_match=True
        )

    def test1(self) -> None:
        """
        Supplied extra parameters.
        """
        # Build `Order` object.
        extra_params = {"ccxt_id": 0}
        order = oororexa.get_order_example1(order_extra_params=extra_params)
        expected_order_as_str = r"""Order: order_id=0
        creation_timestamp=2000-01-01 09:30:00-05:00
        asset_id=101
        type_=price@twap
        start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        curr_num_shares=0.0
        diff_num_shares=100.0
        tz=America/New_York
        extra_params={'ccxt_id': 0}"""
        # Check.
        self.helper(order, expected_order_as_str)

    def test2(self) -> None:
        """
        Extra parameters are not supplied.
        """
        # Build `Order` object.
        extra_params = None
        order = oororexa.get_order_example1(order_extra_params=extra_params)
        expected_order_as_str = r"""Order: order_id=0
        creation_timestamp=2000-01-01 09:30:00-05:00
        asset_id=101
        type_=price@twap
        start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        curr_num_shares=0.0
        diff_num_shares=100.0
        tz=America/New_York
        extra_params={}"""
        # Check.
        self.helper(order, expected_order_as_str)

    def test_3(self) -> None:
        """
        Check order representation.
        """
        # Build `Order` object.
        extra_params = {
            "stats": {
                "_submit_twap_child_order::child_order.created.0": pd.Timestamp(
                    "2023-07-07 14:03:05.932433-0400", tz="America/New_York"
                ),
                "_submit_twap_child_order::child_order.limit_price_calculated.0": pd.Timestamp(
                    "2023-07-07 14:03:05.937598-0400", tz="America/New_York"
                ),
            "ccxt_id": [0],
            }
        }
        order = oororexa.get_order_example1(order_extra_params=extra_params)
        expected_order_repr = r"""
        Order:
        order_id=0
        creation_timestamp=2000-01-01 09:30:00-05:00
        asset_id=101
        type_=price@twap
        start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        curr_num_shares=0.0
        diff_num_shares=100.0
        tz=America/New_York
        extra_params={'stats': {'_submit_twap_child_order::child_order.created.0': Timestamp('2023-07-07 14:03:05.932433-0400', tz='America/New_York'),
                '_submit_twap_child_order::child_order.limit_price_calculated.0': Timestamp('2023-07-07 14:03:05.937598-0400', tz='America/New_York'),
                'ccxt_id': [0]}}
        """
        # Check.
        order_repr = repr(order)
        self.assert_equal(order_repr, expected_order_repr, fuzzy_match=True)


class TestMultipleOrders1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test building and serializing a list of Orders.
        """
        # Build `Order` objects.
        extra_params1 = {"ccxt_id": 0}
        extra_params2 = None
        orders = [
            oororexa.get_order_example1(order_extra_params=extra_params1),
            oororexa.get_order_example1(order_extra_params=extra_params2),
        ]
        act = oordorde.orders_to_string(orders)
        exp = r"""
Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={'ccxt_id': 0}
Order: order_id=0 creation_timestamp=2000-01-01 09:30:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
"""
        self.assert_equal(act, exp, fuzzy_match=True)
        # Deserialize from string.
        orders2 = oordorde.orders_from_string(act)
        # Check.
        act = oordorde.orders_to_string(orders2)
        self.assert_equal(act, exp, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test how the list of Orders is represented.
        """
        # Build `Order` objects.
        extra_params1 = {
            "stats": {
                "_submit_twap_child_order::child_order.created.0": pd.Timestamp(
                    "2023-07-07 14:03:05.932433-0400", tz="America/New_York"
                ),
                "_submit_twap_child_order::child_order.limit_price_calculated.0": pd.Timestamp(
                    "2023-07-07 14:03:05.937598-0400", tz="America/New_York"
                ),
            "ccxt_id": [0],
            }
        }
        extra_params2 = None
        orders = [
            oororexa.get_order_example1(order_extra_params=extra_params1),
            oororexa.get_order_example1(order_extra_params=extra_params2),
        ]
        exp = r"""
        Order:
        order_id=0
        creation_timestamp=2000-01-01 09:30:00-05:00
        asset_id=101
        type_=price@twap
        start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        curr_num_shares=0.0
        diff_num_shares=100.0
        tz=America/New_York
        extra_params={'stats': {'_submit_twap_child_order::child_order.created.0': Timestamp('2023-07-07 14:03:05.932433-0400', tz='America/New_York'),
                '_submit_twap_child_order::child_order.limit_price_calculated.0': Timestamp('2023-07-07 14:03:05.937598-0400', tz='America/New_York'),
                'ccxt_id': [0]}}
        Order:
        order_id=0
        creation_timestamp=2000-01-01 09:30:00-05:00
        asset_id=101
        type_=price@twap
        start_timestamp=2000-01-01 09:35:00-05:00
        end_timestamp=2000-01-01 09:40:00-05:00
        curr_num_shares=0.0
        diff_num_shares=100.0
        tz=America/New_York
        extra_params={}
        """
        # Check.
        actual = oordorde.orders_to_string(orders, mode="repr")
        self.assert_equal(actual, exp, fuzzy_match=True)
