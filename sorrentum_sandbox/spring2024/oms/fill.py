"""
Import as:

import oms.fill as omfill
"""

import collections
import logging
from typing import Any, Dict, List

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)
_TRACE = False


# #############################################################################
# Fill
# #############################################################################


class Fill:
    """
    An order fill represented without reference to a trading exchange.

    - An order can be filled partially or completely.
    - Multiple fills at the same or different price, can correspond to a single
      order.

    The simplest case is for an order to be completely filled (e.g., at the end of
    its VWAP execution window) at a single price. In this case a single `Fill`
    object can represent the execution.
    """

    _fill_id = 0

    def __init__(
        self,
        order: oordorde.Order,
        timestamp: pd.Timestamp,
        num_shares: float,
        price: float,
    ):
        """
        Constructor.

        :param order: the order that this fill corresponds to
        :param timestamp: when the fill happened
        :param num_shares: it's the number of shares that are filled, with
            respect to `diff_num_shares` in `order`
        :param price: the price at which the fill happened
        """
        _LOG.debug(hprint.to_str("order timestamp num_shares price"))
        self._fill_id = self._get_next_fill_id()
        # Pointer to the order.
        self.order = order
        # TODO(gp): An Order should contain a list of pointers to its fills for
        #  accounting purposes.
        #  We can verify the invariant that no more than the desired quantity
        #  was filled.
        # Timestamp of when it was completed.
        self.timestamp = timestamp
        # Number of shares executed. This has the same meaning as in Order, i.e., it
        # can be positive and negative depending on long / short.
        hdbg.dassert_ne(num_shares, 0)
        self.num_shares = num_shares
        # Price executed for the given shares.
        hdbg.dassert_lt(0, price)
        self.price = price

    def __str__(self) -> str:
        # TODO(gp): Add example of output.
        txt: List[str] = []
        txt.append("Fill:")
        dict_ = self.to_dict()
        for k, v in dict_.items():
            txt.append(f"{k}={v}")
        return " ".join(txt)

    def __repr__(self) -> str:
        return self.__str__()

    def to_dict(self) -> Dict[str, Any]:
        dict_: Dict[str, Any] = collections.OrderedDict()
        dict_["asset_id"] = self.order.asset_id
        dict_["fill_id"] = self.order.order_id
        dict_["timestamp"] = self.timestamp
        dict_["num_shares"] = self.num_shares
        dict_["price"] = self.price
        return dict_

    # ///////////////////////////////////////////////////////////////////////////
    # Private interface.
    # ///////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _get_next_fill_id() -> int:
        fill_id = Fill._fill_id
        Fill._fill_id += 1
        return fill_id
