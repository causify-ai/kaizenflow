"""
Import as:

import oms.broker.dataframe_broker as obdabro
"""

import logging
from typing import List, Optional, Tuple

import pandas as pd

import oms.broker.fake_fills_broker as obfafibr
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# #############################################################################
# DataFrameBroker
# #############################################################################


class DataFrameBroker(obfafibr.FakeFillsBroker):
    """
    Represent a broker to which we place orders and receive fills back:

    - completely, no incremental fills
    - as soon as their deadline comes
    - at the price from the Market

    There is no interaction with an OMS (e.g., no need to waiting for acceptance
    and execution).
    """

    async def _submit_market_orders(
        self,
        orders: List[oordorde.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool,
    ) -> Tuple[str, pd.DataFrame]:
        """
        Same as abstract method.
        """
        # All the simulated behavior is already in the abstract class so there
        # is nothing to do here.
        _ = orders, wall_clock_timestamp
        if dry_run:
            _LOG.warning("Not submitting orders to OMS because of dry_run")
        order_df = pd.DataFrame(None)
        receipt = "dummy_order_receipt"
        return receipt, order_df

    async def _submit_twap_orders(
        self,
        orders: List[oordorde.Order],
        *,
        execution_freq: Optional[str] = "1T",
    ) -> Tuple[str, List[pd.DataFrame]]:
        """
        Same as abstract method.
        """
        # All the simulated behavior is already in the abstract class so there
        # is nothing to do here.
        receipt = "dummy_order_receipt"
        return receipt, orders

    async def _wait_for_accepted_orders(
        self,
        order_receipt: str,
    ) -> None:
        """
        Same as abstract method.
        """
        # Orders are always immediately accepted in simulation, so there is
        # nothing to do here.
        _ = order_receipt
