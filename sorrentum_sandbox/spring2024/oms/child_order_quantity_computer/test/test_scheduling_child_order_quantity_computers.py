import logging
from typing import Dict, List

import pandas as pd

import helpers.hunit_test as hunitest
import oms.child_order_quantity_computer.dynamic_scheduling_child_order_quantity_computer as ocoqcdscoqc
import oms.child_order_quantity_computer.static_scheduling_child_order_quantity_computer as ocoqcsscoqc
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


class TestStaticSchedulingChildOrderQuantityComputer(hunitest.TestCase):
    def test_get_wave_quantities1(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use two waves, test the first.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [7.3, 2.5, 1.2]
        num_waves = 2
        wave_id = 0
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(wave_quantities, {1: 3.0, 2: 1.2, 3: 0.6})

    def test_get_wave_quantities2(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use two waves, test the second.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [7.3, 2.5, 1.2]
        num_waves = 2
        wave_id = 1
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(wave_quantities, {1: 3.0, 2: 1.2, 3: 0.6})

    def test_get_wave_quantities3(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use three waves, test the first.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [4.0, 1.0, 3.0]
        num_waves = 3
        wave_id = 0
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(
            wave_quantities,
            {1: 1.0, 2: 0.3, 3: 1.0},
        )

    def test_get_wave_quantities4(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use three waves, test the third.
        """
        diff_num_shares = [4.0, 1.0, 3.0]
        num_waves = 3
        wave_id = 2
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(
            wave_quantities,
            {1: 1.0, 2: 0.3, 3: 1.0},
        )

    def _get_wave_quantities(
        self, num_waves: int, target_wave_id: int, diff_num_shares: List[float]
    ) -> Dict[int, float]:
        """
        Get next wave quantities.

        :param num_waves: number of waves
        :param target_wave_id: id of the wave to test
        :param diff_num_shares: list of number of shares for each parent order
        """
        # Define parent orders with different number of shares.
        parent_orders = _get_parent_orders(diff_num_shares)
        dummy_market_info = _get_market_info()
        # Initialize the scheduler.
        child_order_quantity_computer = (
            ocoqcsscoqc.StaticSchedulingChildOrderQuantityComputer()
        )
        child_order_quantity_computer.set_instance_params(
            parent_orders,
            num_waves,
            dummy_market_info,
        )
        # We need go through each wave until the target one
        # to get the correct quantities.
        # E.g. if we want to get the quantities for the second wave,
        # we need to go through the first wave, and then get the quantities for the second wave.
        for wave_id in range(target_wave_id + 1):
            wave_quantities = child_order_quantity_computer.get_wave_quantities(
                wave_id,
            )
        return wave_quantities


class TestDynamicSchedulingChildOrderQuantityComputer(hunitest.TestCase):
    def test_get_wave_quantities1(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use two waves, test the first.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [7.3, 2.5, 1.2]
        num_waves = 2
        wave_id = 0
        open_positions = {}
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares, open_positions
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(wave_quantities, {1: 7.0, 2: 2.5, 3: 1.2})

    def test_get_wave_quantities2(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use two waves, test the second.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [7.3, 2.5, 1.2]
        num_waves = 2
        wave_id = 1
        open_positions = {
            "ETH/USDT:USDT": 10,
            "BTC/USDT:USDT": 5,
        }
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares, open_positions
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(wave_quantities, {1: 7.0, 2: 2.5, 3: 1.199})

    def test_get_wave_quantities3(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use three waves, test the first.
        """
        # Define parent orders with different number of shares.
        diff_num_shares = [4.0, 1.0, 3.0]
        num_waves = 3
        wave_id = 0
        open_positions = {}
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares, open_positions
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(
            wave_quantities,
            {1: 4.0, 2: 1.0, 3: 3.0},
        )

    def test_get_wave_quantities4(self) -> None:
        """
        Test that the child order quantities are correctly computed.

        Use three waves, test the third.
        """
        diff_num_shares = [4.0, 1.0, 3.0]
        num_waves = 3
        wave_id = 2
        open_positions = {
            "ETH/USDT:USDT": 10,
            "BTC/USDT:USDT": 5,
        }
        wave_quantities = self._get_wave_quantities(
            num_waves, wave_id, diff_num_shares, open_positions
        )
        # Note that the quantities are rounded to the precision of the asset.
        self.assertDictEqual(
            wave_quantities,
            {1: 4.0, 2: 1.0, 3: 3.0},
        )

    def _get_wave_quantities(
        self,
        num_waves: int,
        target_wave_id: int,
        diff_num_shares: List[float],
        open_positions: Dict[str, float] = {},
    ) -> Dict[int, float]:
        """
        Get next wave quantities.

        :param num_waves: number of waves
        :param wave_id: id of the wave to test
        :param diff_num_shares: list of number of shares for each parent order
        :param open_positions: dict of open positions
        """
        # Define parent orders with different number of shares.
        parent_orders = _get_parent_orders(diff_num_shares)
        dummy_market_info = _get_market_info()
        # Initialize the scheduler.
        child_order_quantity_computer = (
            ocoqcdscoqc.DynamicSchedulingChildOrderQuantityComputer()
        )
        child_order_quantity_computer.set_instance_params(
            parent_orders,
            num_waves,
            dummy_market_info,
        )
        child_order_quantity_computer.update_current_positions(open_positions)
        # We need go through each wave until the target one
        # to get the correct quantities.
        # E.g. if we want to get the quantities for the second wave,
        # we need to go through the first wave, and then get the quantities for the second wave.
        for wave_id in range(target_wave_id + 1):
            wave_quantities = child_order_quantity_computer.get_wave_quantities(
                wave_id,
            )
        return wave_quantities


def _get_parent_orders(diff_num_shares: List[int]) -> List[oordorde.Order]:
    """
    Generate parent orders.

    :param diff_num_shares: list of number of shares for each parent order, e.g.
        `[1, 2, 3]` for 3 parent orders, 1 share for the first, 2 for the second, 3 for the third.
    """
    # Create a parent order with 2 assets and 2 waves.
    creation_timestamp = pd.Timestamp("2022-08-05 09:30:55+00:00")
    start_timestamp = pd.Timestamp("2022-08-05 09:31:00+00:00")
    end_timestamp = pd.Timestamp("2022-08-05 09:32:00+00:00")
    orders_str = "\n".join(
        [
            f"Order: order_id=1 creation_timestamp={creation_timestamp} asset_id=1464553467 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares=0 diff_num_shares={diff_num_shares[0]} tz=UTC extra_params={{'ccxt_symbol': 'ETH/USDT:USDT'}}",
            f"Order: order_id=2 creation_timestamp={creation_timestamp} asset_id=1464553468 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares=0 diff_num_shares={diff_num_shares[1]} tz=UTC extra_params={{'ccxt_symbol': 'BTC/USDT:USDT'}}",
            f"Order: order_id=3 creation_timestamp={creation_timestamp} asset_id=1464553469 type_=limit start_timestamp={start_timestamp} end_timestamp={end_timestamp} curr_num_shares=0 diff_num_shares={diff_num_shares[2]} tz=UTC extra_params={{'ccxt_symbol': 'ETH/USDT:USDT'}}",
        ]
    )
    parent_orders = oordorde.orders_from_string(orders_str)
    return parent_orders


def _get_market_info() -> Dict[int, Dict[str, int]]:
    """
    Generate market info for the parent orders.
    """
    dummy_market_info = {
        1464553467: {
            "amount_precision": 0,
            "price_precision": 3,
            "max_leverage": 1,
        },
        1464553468: {
            "amount_precision": 1,
            "price_precision": 3,
            "max_leverage": 1,
        },
        1464553469: {
            "amount_precision": 3,
            "price_precision": 3,
            "max_leverage": 1,
        },
    }
    return dummy_market_info
