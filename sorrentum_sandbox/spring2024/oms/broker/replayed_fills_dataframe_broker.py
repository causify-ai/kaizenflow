"""
Import as:

import oms.broker.replayed_fills_dataframe_broker as obrfdabr
"""

import logging
from typing import Any, List

import oms.broker.dataframe_broker as obdabro
import oms.fill as omfill

_LOG = logging.getLogger(__name__)


# TODO(gp): -> ReplayedDataFrameBroker?
class ReplayedFillsDataFrameBroker(obdabro.DataFrameBroker):
    """
    Broker taking a `oms.Fills` and returning them in correct order.

    # TODO(gp): What is the flow to generate these fills?
    """

    # TODO(gp): add a constructor accepting a file path and load the fills inside
    # the class since it is a common operation.
    def __init__(self, *args: Any, fills: List[List[omfill.Fill]], **kwargs: Any):
        """
        :param fills: list of lists of OMS fills. E.g.,
            ```
            [
                [
                    Fill: asset_id=1464553467 fill_id=0 timestamp=2023-10-03 22:59:02.638000+00:00 num_shares=-0.025 price=1653.3319999999999,
                    Fill: asset_id=1467591036 fill_id=1 timestamp=2023-10-03 22:59:02.640000+00:00 num_shares=-92.0 price=0.30077499999999996,
                ],
                [
                    Fill: asset_id=1464553467 fill_id=25 timestamp=2023-10-03 23:04:01.648000+00:00 num_shares=0.025 price=1657.638,
                    Fill: asset_id=1467591036 fill_id=26 timestamp=2023-10-03 23:04:59.923000+00:00 num_shares=92.0 price=0.3015,
                ]
            ]
            ```
        """
        super().__init__(*args, **kwargs)
        self._fills = iter(fills)

    def get_fills(self) -> List[omfill.Fill]:
        """
        Return the list of oms.Fills with every call.
        """
        return next(self._fills)
