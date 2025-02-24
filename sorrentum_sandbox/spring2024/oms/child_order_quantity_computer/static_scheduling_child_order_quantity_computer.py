"""
Import as:

import oms.child_order_quantity_computer.static_scheduling_child_order_quantity_computer as ocoqcsscoqc
"""
import logging
from typing import Dict, List

import helpers.hdbg as hdbg
import helpers.hnumpy as hnumpy
import helpers.hprint as hprint
import oms.child_order_quantity_computer.child_order_quantity_computer as ocoqccoqc

_LOG = logging.getLogger(__name__)


class StaticSchedulingChildOrderQuantityComputer(
    ocoqccoqc.AbstractChildOrderQuantityComputer
):
    """
    Return a TWAP-like schedule.

    Given a certain amount like `(BTC, 10), (ETH, 5)` and num_waves=5,
    return (BTC, 2), (ETH, 1) for every wave. This does not use the
    current quantity held passed through update.
    """

    def __init__(self):
        super().__init__()

    def _calculate_static_child_order_quantities(self) -> Dict[int, float]:
        """
        Calculate child order quantities for each provided parent order.

        The quantity is static, so it is calculated only once.
        """
        next_wave_quantities: Dict[int, float] = {}
        for parent_order in self._parent_orders:
            parent_order_id = parent_order.order_id
            # Verify that the target parent order IDs are present
            # in the cached values.
            hdbg.dassert_in(
                parent_order_id, self.parent_order_id_to_target_shares
            )
            hdbg.dassert_in(
                parent_order_id,
                self.parent_order_id_to_amount_precision,
            )
            # Get the max amount of digits for the given asset's quantity.
            amount_precision = self.parent_order_id_to_amount_precision[
                parent_order_id
            ]
            diff_signed_num_shares = parent_order.diff_num_shares
            hdbg.dassert_ne(0, diff_signed_num_shares)
            # Get size of a single child order based on number of parent orders.
            child_order_diff_signed_num_shares = (
                diff_signed_num_shares / self._num_waves
            )
            hdbg.dassert_ne(0, child_order_diff_signed_num_shares)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(hprint.to_str("child_order_diff_signed_num_shares"))
            # Round to the allowable asset precision.
            child_order_diff_signed_num_shares_before_floor = (
                child_order_diff_signed_num_shares
            )
            child_order_diff_signed_num_shares = hnumpy.floor_with_precision(
                child_order_diff_signed_num_shares, amount_precision
            )
            # Check if the rounding changed the originally
            # calculated child order amount.
            if (
                child_order_diff_signed_num_shares_before_floor
                != child_order_diff_signed_num_shares
            ):
                _LOG.warning(
                    "Share amount changed due to precision limit: "
                    + hprint.to_str(
                        "child_order_diff_signed_num_shares_before_floor \
                        child_order_diff_signed_num_shares amount_precision"
                    )
                )
            next_wave_quantities[
                parent_order_id
            ] = child_order_diff_signed_num_shares
        return next_wave_quantities

    def _get_wave_quantities(self, wave_id: int) -> Dict[int, float]:
        """
        Return the quantity for the wave.

        Since the scheduling is static, the same value is returned from
        the state each time.
        """
        if wave_id == 0:
            self._next_wave_quantities = (
                self._calculate_static_child_order_quantities()
            )
        _ = wave_id
        return self._next_wave_quantities

    def _get_range_filter(self, expected_num_child_orders: int) -> List[int]:
        """
        Get the range of expected number of child orders.
        """
        return [0, expected_num_child_orders]
