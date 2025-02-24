"""
Import as:

import oms.child_order_quantity_computer.child_order_quantity_computer as ocoqccoqc
"""
import abc
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


class AbstractChildOrderQuantityComputer(abc.ABC):
    """
    Represent the strategy to decide the quantity of child orders.

    As a rule, we assume that a parent order needs to be executed within
    a bar (e.g., of 5 minutes) and the execution is split into children
    orders, in a given number of waves (e.g., 1 wave every 30 seconds,
    corresponding to 10 waves in 5 mins).
    """

    def __init__(self) -> None:
        self._num_waves: Optional[int] = None
        self._market_info: Optional[Dict[str, Any]] = None
        self._parent_orders: Optional[List[oordorde.Order]] = None
        # Init a value to track the size of the child order corresponding to
        # a parent order, to be sent in the next wave.
        # It has the form of a `parent_order_id` -> `child_order_size` mapping.
        self._wave_quantities: Dict[int, float] = {}
        # Init a value to track current open positions.
        self._current_open_positions: Dict[int, float] = {}

    def set_instance_params(
        self,
        parent_orders: Optional[List[oordorde.Order]] = None,
        num_waves: Optional[int] = None,
        market_info: Optional[Dict[int, Any]] = None,
    ) -> None:
        """
        Initialize with info necessary to compute the size of a child order.

        :param parent_orders: OMS orders for which child order quantity
            should be computed
        :param num_waves: total number of child order waves expected
        :param market_info: a market info object containing information
            on assets relevant for order generation, e.g. the rounding
            precision
        """
        #
        if num_waves is not None:
            hdbg.dassert_lte(1, num_waves)
            self._num_waves = num_waves
        #
        if market_info is not None:
            self._market_info = market_info
        #
        if parent_orders is not None:
            hdbg.dassert_lte(1, len(parent_orders))
            self._parent_orders = parent_orders
            # Cache the total number of shares expected from each parent order.
            self.parent_order_id_to_target_shares = (
                self._get_parent_order_id_to_target_shares()
            )
        if self._market_info is not None and self._parent_orders is not None:
            # Cache the amount rounding precision for each parent order.
            self.parent_order_id_to_amount_precision = (
                self._get_parent_order_id_to_amount_precision(market_info)
            )
            # Verify that all parent order IDs are consistent.
            hdbg.dassert_set_eq(
                self.parent_order_id_to_target_shares,
                self.parent_order_id_to_amount_precision,
            )

    def get_wave_quantities(self, wave_id: int) -> Dict[int, float]:
        """
        Return the quantity for the `wave_id`.
        """
        hdbg.dassert_lt(wave_id, self._num_waves)
        # Calculate wave quantities.
        wave_quantities = self._get_wave_quantities(wave_id)
        # Verify that parent order IDs in cached values correspond to provided parent orders.
        parent_order_ids = [
            parent_order.order_id for parent_order in self._parent_orders
        ]
        hdbg.dassert_set_eq(wave_quantities, parent_order_ids)
        # Cache the quantities for the wave.
        self._wave_quantities = wave_quantities
        return wave_quantities

    def get_range_filter(
        self,
        bar_duration: str,
        exec_freq: str,
    ) -> List[int]:
        """
        Get the range of expected number of child orders.

        :param bar_duration: bar duration as a string, e.g, `5T`
        :param exec_freq: execution frequency as a string, e.g, `1T`
        :return: range of expected number of child orders, e.g, `[0, 1, 2]` for dynamic or
            `[0, 2]` for static
        """
        bar_duration_timedelta = pd.Timedelta(bar_duration)
        exec_freq_timedelta = pd.Timedelta(exec_freq)
        expected_num_child_orders = int(
            bar_duration_timedelta / exec_freq_timedelta
        )
        range_filter = self._get_range_filter(expected_num_child_orders)
        return range_filter

    def update_current_positions(
        self, current_positions: Dict[str, float]
    ) -> None:
        """
        Update the current positions using data from the Broker. The current
        positions are saved as a {`ccxt_symbol`: `current_position`}, e.g.

        {'BTC/USDT': 10, 'ETH/USDT': 20}.
        """
        self._current_positions = current_positions

    def to_dict(self) -> Dict[str, str]:
        """
        Get the name of the quantity computer class as string.
        """
        obj_dict = {}
        obj_dict["object_type"] = self.__class__.__name__
        return obj_dict

    @abc.abstractmethod
    def _get_wave_quantities(self, wave_id: int) -> Dict[int, float]:
        """
        Specific implementation of `get_wave_quantities`.
        """

    @abc.abstractmethod
    def _get_range_filter(
        self,
        bar_duration: str,
        exec_freq: str,
    ) -> List[int]:
        """
        Specific implementation of `_get_range_filter`.
        """

    def _get_parent_order_id_to_target_shares(self) -> Dict[int, float]:
        """
        Get a diсtionary of expected total shares to be filled for each parent
        order.
        """
        parent_order_id_to_target_shares: Dict[int, float] = {}
        #
        for parent_order in self._parent_orders:
            order_id = parent_order.order_id
            target_shares = parent_order.diff_num_shares
            parent_order_id_to_target_shares[order_id] = target_shares
        return parent_order_id_to_target_shares

    def _get_parent_order_id_to_amount_precision(
        self, market_info: Dict[int, Any]
    ) -> Dict[int, int]:
        """
        Get the precision for amount of order shares expected by the exchange.

        Each asset has a different max number of digits after period.
        Information on that is provided by the exchange and stored in
        `market_info`.
        """
        parent_order_ids_to_amount_precision: Dict[int, int] = {}
        #
        for parent_order in self._parent_orders:
            order_id = parent_order.order_id
            asset_id = parent_order.asset_id
            hdbg.dassert_in(asset_id, market_info)
            amount_precision = market_info[asset_id]["amount_precision"]
            parent_order_ids_to_amount_precision[order_id] = amount_precision
        return parent_order_ids_to_amount_precision
