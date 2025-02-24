"""
Import as:

import oms.broker.test.broker_helper as ombtbh
"""

import logging
from typing import List

import helpers.hasyncio as hasynci
import oms.broker.broker as obrobrok
import oms.fill as omfill
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


async def _get_broker_coroutine(
    broker: obrobrok.Broker,
    order: oordorde.Order,
) -> List[omfill.Fill]:
    """
    Submit an order through the Broker and wait for fills.
    """
    # Wait 1 sec.
    get_wall_clock_time = broker.market_data.get_wall_clock_time
    await hasynci.sleep(1, get_wall_clock_time)
    # Submit orders to the broker.
    orders = [order]
    await broker.submit_orders(orders, order.type_)
    # Wait until order fulfillment.
    fulfillment_deadline = order.end_timestamp
    await hasynci.async_wait_until(fulfillment_deadline, get_wall_clock_time)
    # Check fills.
    fills = broker.get_fills()
    return fills
