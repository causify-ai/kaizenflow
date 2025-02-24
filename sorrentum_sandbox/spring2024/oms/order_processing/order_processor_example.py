"""
Import as:

import oms.order_processing.order_processor_example as oopoprex
"""

import logging
from typing import Coroutine, Optional, Union

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsql as hsql
import oms.order_processing.order_processor as ooprorpr
import oms.portfolio.portfolio as oporport

_LOG = logging.getLogger(__name__)


# TODO(gp): -> `get_OrderProcessor_example()`.
# TODO(gp): Reorg the params to match OrderProcessor interface.
# TODO(gp): duration_in_secs -> start_delay_in_secs
# TODO(gp): Pass the Broker and not the Portfolio.
def get_order_processor_example1(
    db_connection: hsql.DbConnection,
    bar_duration_in_secs: int,
    termination_condition: Optional[Union[pd.Timestamp, int]],
    duration_in_secs: int,
    portfolio: oporport.Portfolio,
    asset_id_name: str,
    max_wait_time_for_order_in_secs: int,
    *,
    delay_to_accept_in_secs: int = 3,
    delay_to_fill_in_secs: int = 10
) -> ooprorpr.OrderProcessor:
    """
    Build an OrderProcessor.

    The params are the same as the OrderProcessor.

    :param duration_in_secs: how many seconds to run after the beginning
        of the replayed clock
    :param max_wait_time_for_order_in_secs: how long to wait for an
        order to be received, once this object starts waiting
    :param delay_to_accept_in_secs: delay after the order is submitted
        to update the accepted orders table
    :param delay_to_fill_in_secs: delay after the order is accepted to
        update the position table with the filled positions
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str(
                "bar_duration_in_secs "
                "termination_condition "
                "duration_in_secs "
                "portfolio "
                "asset_id_name "
                "max_wait_time_for_order_in_secs "
                "delay_to_accept_in_secs "
                "delay_to_fill_in_secs"
            )
        )
    broker = portfolio.broker
    if duration_in_secs:
        # TODO(gp): Maybe this should be compute from the caller and simplify
        #  this interface.
        hdbg.dassert_is(termination_condition, None)
        # Compute the timestamp when the OrderProcessor should shut down.
        get_wall_clock_time = portfolio.broker.market_data.get_wall_clock_time
        initial_replayed_timestamp = get_wall_clock_time()
        hdbg.dassert_isinstance(duration_in_secs, (float, int))
        hdbg.dassert_lt(0, duration_in_secs)
        offset = pd.Timedelta(duration_in_secs, unit="seconds")
        termination_condition = initial_replayed_timestamp + offset
    order_processor = ooprorpr.OrderProcessor(
        db_connection,
        bar_duration_in_secs,
        termination_condition,
        max_wait_time_for_order_in_secs,
        delay_to_accept_in_secs,
        delay_to_fill_in_secs,
        broker,
        asset_id_name,
    )
    return order_processor


# TODO(gp): -> `get_OrderProcessorCoroutine_example()`.
def get_order_processor_coroutine_example1(
    order_processor: ooprorpr.OrderProcessor,
) -> Coroutine:
    """
    Create a coroutine running the OrderProcessor, that lasts for
    duration_in_secs.
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("order_processor"))
    # Build the Coroutine.
    order_processor_coroutine = order_processor.run_loop()
    hdbg.dassert_isinstance(order_processor_coroutine, Coroutine)
    return order_processor_coroutine
