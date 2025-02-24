import logging

import pytest

import helpers.hunit_test as hunitest
import oms.broker.ib_api as obribapi

_LOG = logging.getLogger(__name__)


def _get_contract1():
    symbol = "ES"
    sec_type = "FUT"
    contract = obribapi.Contract(symbol, sec_type)
    return contract


class Test_Contract1(hunitest.TestCase):
    def test1(self):
        contract = _get_contract1()
        #
        act = str(contract)
        exp = "Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None"
        self.assert_equal(act, exp)

    def test_cmp1(self):
        contract1 = _get_contract1()
        contract2 = _get_contract1()
        #
        self.assertEqual(contract1, contract2)

    def test_cmp2(self):
        contract1 = _get_contract1()
        contract2 = _get_contract1()
        contract2.symbol = "ES2"
        #
        self.assertNotEqual(contract1, contract2)


# TODO(*): Add type hints, docstrings.
def _get_order1():
    order_id = 0
    action = "BUY"
    total_quantity = 100.0
    order_type = "MKT"
    order = obribapi.Order(order_id, action, total_quantity, order_type)
    return order


class Test_Order1(hunitest.TestCase):
    def test1(self):
        order = _get_order1()
        #
        act = str(order)
        exp = "Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None"
        self.assert_equal(act, exp)


def _get_order_status1():
    order_id = 0
    status = "filled"
    filled = 75.0
    remaining = 25.0
    avg_fill_price = 100.0
    order_status = obribapi.OrderStatus(
        order_id, status, filled, remaining, avg_fill_price
    )
    return order_status


class Test_OrderStatus1(hunitest.TestCase):
    def test1(self):
        order_status = _get_order_status1()
        #
        act = str(order_status)
        exp = "OrderStatus: order_id=0, status=filled, filled=75.0, remaining=25.0 avg_fill_price=100.0"
        self.assert_equal(act, exp)


class Test_Trade1(hunitest.TestCase):
    def test1(self):
        contract = _get_contract1()
        order = _get_order1()
        order_status = _get_order_status1()
        trade = obribapi.Trade(contract, order, order_status)
        #
        act = str(trade)
        exp = """Trade:
  contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
  order=Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
  order_status=OrderStatus: order_id=0, status=filled, filled=75.0, remaining=25.0 avg_fill_price=100.0
  timestamp=None"""
        self.assert_equal(act, exp)


def _get_position1():
    contract = _get_contract1()
    position = 1000
    position = obribapi.Position(contract, position)
    return position


# TODO(*): Test public functions, not private ones.
class Test_Position1(hunitest.TestCase):
    def test1(self):
        position = _get_position1()
        #
        act = str(position)
        exp = """Position:
  contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
  position=1000"""
        self.assert_equal(act, exp)

    def test_cmp1(self):
        position1 = _get_position1()
        position2 = _get_position1()
        #
        self.assertEqual(position1, position2)

    def test_cmp2(self):
        position1 = _get_position1()
        position2 = _get_position1()
        position2.position = 999
        #
        self.assertNotEqual(position1, position2)

    def test_diff1(self):
        position = self._update_position_helper(1000, -250)
        #
        act = str(position)
        exp = """Position:
  contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
  position=750"""
        self.assert_equal(act, exp)

    def test_diff2(self):
        position = self._update_position_helper(1000, -1250)
        #
        act = str(position)
        exp = """Position:
  contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
  position=-250"""
        self.assert_equal(act, exp)

    def test_diff3(self):
        position = self._update_position_helper(-1000, 1000)
        #
        act = str(position)
        exp = "None"
        self.assert_equal(act, exp)

    def _update_position_helper(self, amount1: int, amount2: int):
        contract = _get_contract1()
        position1 = obribapi.Position(contract, amount1)
        position2 = obribapi.Position(contract, amount2)
        #
        position = obribapi.Position.update(position1, position2)
        return position


class Test_OMS1(hunitest.TestCase):
    @pytest.mark.skip
    def test1(self):
        contract = _get_contract1()
        order = _get_order1()
        timestamp = None
        oms = obribapi.OMS()
        #
        act = str(oms)
        exp = """OMS:
  trades=0
  orders=0
  positions=0"""
        self.assert_equal(act, exp)
        # Place an order.
        oms.place_order(contract, order, timestamp)
        act = str(oms)
        exp = """OMS:
  trades=1
    Trade:
      contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
      order=Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
      order_status=OrderStatus: order_id=0, status=filled, filled=100.0, remaining=0.0 avg_fill_price=1000.0
      timestamp=None
  orders=1
    Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
  positions=1
    None"""
        self.assert_equal(act, exp)

    @pytest.mark.skip
    def test2(self):
        contract = _get_contract1()
        _get_order1()
        timestamp = None
        oms = obribapi.OMS()
        # Place an order.
        oms.place_order(contract, order, timestamp)
        act = str(oms)
        exp = """OMS:
  trades=1
    Trade:
      contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
      order=Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
      order_status=OrderStatus: order_id=0, status=filled, filled=100.0, remaining=0.0 avg_fill_price=1000.0
      timestamp=None
  orders=1
    Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
  positions=1
    None"""
        self.assert_equal(act, exp)
        # Place another opposite order.
        contract2 = copy.deepcopy(contract1)
        contract2.action = "SELL"
        oms.place_order(contract, order, timestamp)
        act = str(oms)
        exp = """OMS:
  trades=1
    Trade:
      contract=Contract: symbol=ES, sec_type=FUT, currency=None, exchange=None
      order=Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
      order_status=OrderStatus: order_id=0, status=filled, filled=100.0, remaining=0.0 avg_fill_price=1000.0
      timestamp=None
  orders=1
    Order: order_id=0, action=BUY, total_quantity=100.0, order_type=MKT timestamp=None
  positions=1
    None"""
        self.assert_equal(act, exp)
