import logging

import pandas as pd
import pytest

import helpers.hasyncio as hasynci
import helpers.hunit_test as hunitest
import market_data as mdata
import oms.fill as omfill
import oms.order.order as oordorde
import oms.order_processing.target_position_and_order_generator as ooptpaoge
import oms.order_processing.target_position_and_order_generator_example as otpaogeex

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestTargetPositionAndOrderGenerator1
# #############################################################################


class TestTargetPositionAndOrderGenerator1(hunitest.TestCase):
    """
    Exercise target positions generation with the POMO optimizer.
    """

    @staticmethod
    def reset() -> None:
        omfill.Fill._fill_id = 0
        oordorde.Order._order_id = 0

    def get_target_position_and_order_generator1(
        self,
    ) -> ooptpaoge.TargetPositionAndOrderGenerator:
        self.reset()
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            target_position_and_order_generator = (
                otpaogeex.get_TargetPositionAndOrderGenerator_example1(
                    event_loop, market_data
                )
            )
        return target_position_and_order_generator

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

    def test_compute(self) -> None:
        expected = r"""
        <oms.order_processing.target_position_and_order_generator.TargetPositionAndOrderGenerator at 0x>
        # last target positions=
                holdings_shares        price  holdings_notional wall_clock_timestamp  prediction  volatility  spread  target_holdings_notional  target_trades_notional  target_trades_shares  target_holdings_shares
        asset_id
        101                     0  1000.311925                  0                  0.0           1      0.0001    0.01             100031.192549           100031.192549                 100.0                   100.0
        # last orders=
        Order: order_id=0 creation_timestamp=2000-01-01 09:35:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}
        """
        target_position_and_order_generator = (
            self.get_target_position_and_order_generator1()
        )
        predictions = pd.Series([1], [101], name="prediction")
        volatility = pd.Series([0.0001], [101], name="volatility")
        spread = pd.Series([0.01], [101], name="spread")
        liquidate_holdings = False
        orders = target_position_and_order_generator.compute_target_positions_and_generate_orders(
            predictions,
            volatility,
            spread,
            liquidate_holdings,
        )
        _ = orders
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "target_position_and_order_generator=%s",
                target_position_and_order_generator,
            )
        self.assert_equal(
            str(target_position_and_order_generator),
            expected,
            purify_text=True,
            fuzzy_match=True,
        )


# #############################################################################
# TestTargetPositionAndOrderGenerator2
# #############################################################################


class TestTargetPositionAndOrderGenerator2(hunitest.TestCase):
    """
    Exercise target positions generation with the `SinglePeriodOptimizer`.
    """

    @staticmethod
    def reset() -> None:
        omfill.Fill._fill_id = 0
        oordorde.Order._order_id = 0

    def get_target_position_and_order_generator2(
        self,
    ) -> ooptpaoge.TargetPositionAndOrderGenerator:
        self.reset()
        with hasynci.solipsism_context() as event_loop:
            (
                market_data,
                _,
            ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
            target_position_and_order_generator = (
                otpaogeex.get_TargetPositionAndOrderGenerator_example2(
                    event_loop, market_data
                )
            )
        return target_position_and_order_generator

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

    def test_compute(self) -> None:
        expected = r"""
        <oms.order_processing.target_position_and_order_generator.TargetPositionAndOrderGenerator at 0x>
        # last target positions=
                holdings_shares        price  holdings_notional wall_clock_timestamp  prediction  volatility  spread  target_holdings_shares  target_holdings_notional  target_trades_shares  target_trades_notional
        asset_id
        101                     0  1000.311925                  0                  0.0           1      0.0001    0.01                    50.0              50015.596275                  50.0            50015.596275
        202                     0  1000.311925                  0                  0.0          -1     0.00005    0.02                   -50.0             -50015.596275                 -50.0           -50015.596275
        # last orders=
        Order: order_id=0 creation_timestamp=2000-01-01 09:35:00-05:00 asset_id=101 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=50.0 tz=America/New_York extra_params={}
        Order: order_id=1 creation_timestamp=2000-01-01 09:35:00-05:00 asset_id=202 type_=price@twap start_timestamp=2000-01-01 09:35:00-05:00 end_timestamp=2000-01-01 09:40:00-05:00 curr_num_shares=0.0 diff_num_shares=-50.0 tz=America/New_York extra_params={}
        """
        target_position_and_order_generator = (
            self.get_target_position_and_order_generator2()
        )
        asset_ids = [101, 202]
        predictions = pd.Series([1, -1], asset_ids, name="prediction")
        volatility = pd.Series([0.0001, 0.00005], asset_ids, name="volatility")
        spread = pd.Series([0.01, 0.02], asset_ids, name="spread")
        liquidate_holdings = False
        orders = target_position_and_order_generator.compute_target_positions_and_generate_orders(
            predictions,
            volatility,
            spread,
            liquidate_holdings,
        )
        _ = orders
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "target_position_and_order_generator=%s",
                target_position_and_order_generator,
            )
        self.assert_equal(
            str(target_position_and_order_generator),
            expected,
            purify_text=True,
            fuzzy_match=True,
        )
