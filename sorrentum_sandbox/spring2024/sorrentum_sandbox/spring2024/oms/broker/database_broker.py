"""
Import as:

import oms.broker.database_broker as obrdabro
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hprint as hprint
import helpers.hsql as hsql
import oms.broker.fake_fills_broker as obfafibr
import oms.db.oms_db as odbomdb
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)

# #############################################################################
# DatabaseBroker
# #############################################################################


class DatabaseBroker(obfafibr.FakeFillsBroker):
    """
    An object that represents a broker backed by a DB with asynchronous updates
    to the state by an OMS handling the orders placed and then filled in the
    marketplace.

    The DB contains the following tables:
    - `submitted_orders`: store information about orders placed by strategies
    - `accepted_orders`: store information about orders accepted by the OMS

    This object always requires a `DatabasePortfolio` that accesses the OMS to
    read the current positions in the `current_positions` DB table.
    We require:
    - In a production set-up: an actual OMS system that fills the orders from
      `accepted_orders` and update `current_positions` table.
    - In a simulation set-up: an `OrderProcessor` that simulates the OMS
    """

    def __init__(
        self,
        *args: Any,
        db_connection: hsql.DbConnection,
        submitted_orders_table_name: str,
        accepted_orders_table_name: str,
        # TODO(gp): This doesn't work for some reason.
        # *,
        poll_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        """
        Construct object.

        :param poll_kwargs: polling instruction when waiting for
            acceptance of an order
        """
        _LOG.debug(
            hprint.to_str(
                "db_connection submitted_orders_table_name "
                "accepted_orders_table_name poll_kwargs"
            )
        )
        super().__init__(*args, **kwargs)
        self._db_connection = db_connection
        self._submitted_orders_table_name = submitted_orders_table_name
        self._accepted_orders_table_name = accepted_orders_table_name
        if poll_kwargs is None:
            poll_kwargs = hasynci.get_poll_kwargs(self._get_wall_clock_time)
        self._poll_kwargs = poll_kwargs
        # Store the submitted rows to the DB for internal bookkeeping.
        self._submissions: Dict[
            pd.Timestamp, pd.Series
        ] = collections.OrderedDict()
        #
        _LOG.debug("After initialization:\n%s", repr(self))

    def __str__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_submissions"])
        return super().__str__(attr_names_to_skip=attr_names_to_skip)

    def __repr__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_submissions"])
        return super().__repr__(attr_names_to_skip=attr_names_to_skip)

    async def _submit_market_orders(
        self,
        orders: List[oordorde.Order],
        wall_clock_timestamp: pd.Timestamp,
        *,
        dry_run: bool = False,
    ) -> Tuple[str, pd.DataFrame]:
        """
        Same as abstract method.
        """
        # Add an order in the submitted orders table.
        submitted_order_id = self._get_next_submitted_order_id()
        order_list: List[Tuple[str, Any]] = []
        file_name = f"filename_{submitted_order_id}.txt"
        order_list.append(("filename", file_name))
        timestamp_db = self._get_wall_clock_time()
        order_list.append(("timestamp_db", timestamp_db))
        order_list.append(("orders_as_txt", oordorde.orders_to_string(orders)))
        row = pd.Series(collections.OrderedDict(order_list))
        # Store the order internally.
        self._submissions[timestamp_db] = row
        # Write the row into the DB.
        if dry_run:
            _LOG.warning("Not submitting orders because of dry_run")
        else:
            hsql.execute_insert_query(
                self._db_connection, row, self._submitted_orders_table_name
            )
        # TODO(gp): We save a single entry in the DB for all the orders instead
        #  of one row per order to accommodate some implementation semantic.
        order_df = pd.DataFrame(row)
        return file_name, order_df

    async def _submit_twap_orders(
        self,
        orders: List[oordorde.Order],
        *,
        execution_freq: Optional[str] = "1T",
    ) -> Tuple[str, List[pd.DataFrame]]:
        """
        Same as abstract method.
        """
        # Add an order in the submitted orders table.
        submitted_order_id = self._get_next_submitted_order_id()
        order_list: List[Tuple[str, Any]] = []
        file_name = f"filename_{submitted_order_id}.txt"
        order_list.append(("filename", file_name))
        timestamp_db = self._get_wall_clock_time()
        order_list.append(("timestamp_db", timestamp_db))
        order_list.append(("orders_as_txt", oordorde.orders_to_string(orders)))
        row = pd.Series(collections.OrderedDict(order_list))
        # Store the order internally.
        self._submissions[timestamp_db] = row
        # TODO(gp): We save a single entry in the DB for all the orders instead
        #  of one row per order to accommodate some implementation semantic.
        hsql.execute_insert_query(
            self._db_connection, row, self._submitted_orders_table_name
        )
        return file_name, orders

    async def _wait_for_accepted_orders(
        self,
        order_receipt: str,
    ) -> None:
        """
        Same as abstract method.
        """
        _LOG.debug("Wait for accepted orders ...")
        await odbomdb.wait_for_order_acceptance(
            self._db_connection,
            order_receipt,
            self._poll_kwargs,
            table_name=self._accepted_orders_table_name,
            field_name="filename",
        )
        _LOG.debug("Wait for accepted orders ... done")
