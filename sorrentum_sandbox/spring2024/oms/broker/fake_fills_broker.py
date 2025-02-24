"""
Import as:

import oms.broker.fake_fills_broker as obfafibr
"""

import logging
from typing import List

import helpers.hdbg as hdbg
import oms.broker.broker as obrobrok
import oms.fill as omfill

_LOG = logging.getLogger(__name__)

# #############################################################################
# FakeFillsBroker
# #############################################################################


# TODO(gp): -> FakeFillsBrokerMixin since it adds certain behaviors
class FakeFillsBroker(obrobrok.Broker):
    """
    Broker that simulates order fills.

    There are scenarios where we do not care about the internal behavior of the
    broker, we simply want to obtain fills "somehow".

    Use cases:
    - Running a simulation where it's assumed that partial fills at TWAP price
      is obtained for each order
    - Replaying an experiment, where logged fills are loaded back and served

    This object doesn't require data or a trading exchange
    """

    def get_fills(self) -> List[omfill.Fill]:
        """
        Implement logic simulating orders being filled.
        """
        # We should always get the "next" orders, for this reason one should use
        # a priority queue.
        wall_clock_timestamp = self._get_wall_clock_time()
        timestamps = self._deadline_timestamp_to_orders.keys()
        _LOG.debug("Timestamps of orders in queue: %s", timestamps)
        if not timestamps:
            return []
        # In our current execution model, we should ask about the orders that are
        # terminating.
        hdbg.dassert_lte(min(timestamps), wall_clock_timestamp)
        orders_to_execute_timestamps = []
        orders_to_execute = []
        for timestamp in timestamps:
            if timestamp <= wall_clock_timestamp:
                orders_to_execute.extend(
                    self._deadline_timestamp_to_orders[timestamp]
                )
                orders_to_execute_timestamps.append(timestamp)
        _LOG.debug("Executing %d orders", len(orders_to_execute))
        # Ensure that no orders are included with `end_timestamp` greater than
        # `wall_clock_timestamp`, e.g., assume that in general orders take their
        # entire allotted window to fill.
        for order in orders_to_execute:
            hdbg.dassert_lte(order.end_timestamp, wall_clock_timestamp)
        # "Execute" the orders.
        # TODO(gp): Here there should be a programmable logic that decides
        #  how many shares are filled and how.
        fills = obrobrok.fill_orders_fully_at_once(
            self.market_data,
            self._timestamp_col,
            self._column_remap,
            orders_to_execute,
        )
        self._fills.extend(fills)
        # Remove the orders that have been executed.
        _LOG.debug(
            "Removing orders from queue with deadline earlier than=`%s`",
            wall_clock_timestamp,
        )
        for timestamp in orders_to_execute_timestamps:
            del self._deadline_timestamp_to_orders[timestamp]
        _LOG.debug("-> Returning fills:\n%s", str(fills))
        return fills
