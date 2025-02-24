"""
Import as:

import oms.child_order_quantity_computer.dynamic_scheduling_child_order_quantity_computer as ocoqcdscoqc
"""
import logging
from typing import Dict, List

import helpers.hnumpy as hnumpy
import helpers.hprint as hprint
import oms.child_order_quantity_computer.child_order_quantity_computer as ocoqccoqc

_LOG = logging.getLogger(__name__)


class DynamicSchedulingChildOrderQuantityComputer(
    ocoqccoqc.AbstractChildOrderQuantityComputer
):
    """
    Place each child order wave with the remaining amount to fill.

    Given a certain amount like `(BTC, 10)` and num_waves=5, the first
    wave is placed for (BTC, 10); if during the first wave the order has
    been filled for 8 BTC, the second wave is placed for (BTC, 2). If
    during the second wave the order has been filled completely, no new
    orders are placed for the rest of the execution.
    """

    def __init__(self):
        super().__init__()
        self._target_positions = {}

    def _get_wave_quantities(self, wave_id: int) -> Dict[int, float]:
        """
        Return the child order quantity to be placed during `wave_id`.

        During the first wave, compute the target positions for parent orders
        and get the first child order quantity as equal to the parent order
        quantity.
        For the following waves, the child order quantities are computed as
        `target_position` - `open_position`. This is done for two reasons:
        - Extra API calls required to check the fill rate are expensive, and
        it is cheaper to calculate the fill rate from the open positions
        - We cannot rely only on open positions, since the bar can start with
        an unflattened account, and parent orders do not update information
        on current holdings in live fashion.
        """
        next_wave_quantities: Dict[int, float] = {}
        if wave_id == 0:
            # Compute the target positions based on current positions.
            # We need the `target_positions` variable to track the fill rate
            # for the parent order without conducting additional API calls.
            for parent_order in self._parent_orders:
                parent_order_id = parent_order.order_id
                diff_num_shares = parent_order.diff_num_shares
                #
                ccxt_symbol = parent_order.extra_params["ccxt_symbol"]
                current_position = self._current_positions.get(ccxt_symbol, 0)
                # Get the target position for the current parent order,
                # as a sum of current position and `diff_num_shares`.
                self._target_positions[parent_order_id] = (
                    current_position + diff_num_shares
                )
                # Round to the number allowable by the exchange.
                amount_precision = self.parent_order_id_to_amount_precision[
                    parent_order_id
                ]
                diff_num_shares_before_floor = diff_num_shares
                diff_num_shares = hnumpy.floor_with_precision(
                    diff_num_shares, amount_precision
                )
                if diff_num_shares_before_floor != diff_num_shares:
                    _LOG.warning(
                        "Share amount changed due to precision limit: "
                        + hprint.to_str(
                            "diff_num_shares_before_floor \
                            diff_num_shares amount_precision"
                        )
                    )
                next_wave_quantities[parent_order_id] = diff_num_shares
        else:
            # Calculate the order size based on current holdings.
            # Given the open positions, the next wave quantity
            # is computed as target_position - current_position.
            for parent_order in self._parent_orders:
                parent_order_id = parent_order.order_id
                ccxt_symbol = parent_order.extra_params["ccxt_symbol"]
                # Get the current amount of holdings.
                # If there is no held amount of an asset, it is not included
                # in the `open_positions`, so we default to 0.
                current_position = self._current_positions.get(ccxt_symbol, 0)
                #
                target_position = self._target_positions[parent_order_id]
                # Calculate the child order size based on missing amount for a full fill.
                child_order_diff_signed_num_shares = (
                    target_position - current_position
                )
                # Round to the number allowable by the exchange.
                amount_precision = self.parent_order_id_to_amount_precision[
                    parent_order_id
                ]
                child_order_diff_signed_num_shares_before_floor = (
                    child_order_diff_signed_num_shares
                )
                child_order_diff_signed_num_shares = hnumpy.floor_with_precision(
                    child_order_diff_signed_num_shares, amount_precision
                )
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
                # Assign to the output.
                next_wave_quantities[
                    parent_order_id
                ] = child_order_diff_signed_num_shares
        return next_wave_quantities

    def _get_range_filter(self, expected_num_child_orders: int) -> List[int]:
        """
        Get the range of expected number of child orders.
        """
        return list(range(expected_num_child_orders + 1))
