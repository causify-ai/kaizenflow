"""
Import as:

import oms.order_processing.order_processor as ooprorpr
"""

import asyncio
import logging
from typing import List, Optional, Union

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import oms.broker.broker as obrobrok
import oms.db.oms_db as odbomdb
import oms.fill as omfill
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# TODO(gp): Add a pointer to a general event logger so that all the objects (DAG,
#  MarketData, OrderProcessor, Broker) can update that. Add a EventLoggerMixin with
#  the common logic.
class OrderProcessor(hobject.PrintableMixin):
    """
    An `OrderProcessor` mocks the behavior of part of a real-world OMS to allow
    the simulation of a `DatabasePortfolio` and `DatabaseBroker` without a real
    OMS.

    In practice, an OMS can consist of a DB storing:
    - submitted and accepted orders (accessed by a `DatabaseBroker`)
    - current position (accessed by a `DatabasePortfolio`)

    This class implements the loop around a `DatabasePortfolio` and `DatabaseBroker`
    by:
    - polling a table of the DB for submitted orders
    - updating the accepted orders DB table
    - updating the current positions DB table which represent the Portfolio state
    """

    def __init__(
        self,
        db_connection: hsql.DbConnection,
        bar_duration_in_secs: int,
        termination_condition: Union[pd.Timestamp, int],
        max_wait_time_for_order_in_secs: float,
        delay_to_accept_in_secs: float,
        delay_to_fill_in_secs: float,
        broker: obrobrok.Broker,
        asset_id_name: str,
        *,
        # TODO(gp): Expose poll_kwargs.
        submitted_orders_table_name: str = odbomdb.SUBMITTED_ORDERS_TABLE_NAME,
        accepted_orders_table_name: str = odbomdb.ACCEPTED_ORDERS_TABLE_NAME,
        current_positions_table_name: str = odbomdb.CURRENT_POSITIONS_TABLE_NAME,
    ) -> None:
        """
        Constructor.

        :param termination_condition: when to terminate polling the table of
            submitted orders
            - pd.timestamp: when this object should stop checking for orders. This
              can create deadlocks if this timestamp is set after the broker stops
              submitting orders.
            - int: number of orders to accept before shut down
        :param max_wait_time_for_order_in_secs: how long to wait for an order to
            be received, once this object starts waiting. This is typically set to
            be the same duration of a bar, even though the order is placed close
            to the beginning of the bar
        :param delay_to_accept_in_secs: delay after the order is submitted for
            this object to update the accepted orders table
        :param delay_to_fill_in_secs: delay after the order is accepted to update
            the position table with the filled positions
        :param broker: broker object connected to the market
        :param asset_id_name: name of the asset IDs column, e.g. "asset_id"
        :param *_orders_table_name: name of the DB tables used to store the
            various information.
            - Typically we use `OrderProcessor` in unit tests, we have control
              over the DB, and we can use names chosen by us, so we use the
              standard table names as defaults
        :param fill_mode: represent how orders are filled
            - `at_once`: all the orders are filled at once after
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "db_connection "
                    "bar_duration_in_secs "
                    "termination_condition "
                    "max_wait_time_for_order_in_secs "
                    "delay_to_accept_in_secs "
                    "delay_to_fill_in_secs "
                    "broker "
                    "asset_id_name "
                    "submitted_orders_table_name "
                    "accepted_orders_table_name "
                    "current_positions_table_name"
                )
            )
        self._db_connection = db_connection
        hdbg.dassert_lte(
            1, hdateti.convert_seconds_to_minutes(bar_duration_in_secs)
        )
        self.bar_duration_in_secs = bar_duration_in_secs
        hdbg.dassert_isinstance(termination_condition, (pd.Timestamp, int))
        if isinstance(termination_condition, int):
            hdbg.dassert_lt(0, termination_condition)
        self.termination_condition = termination_condition
        #
        hdbg.dassert_lte(0, max_wait_time_for_order_in_secs)
        self.max_wait_time_for_order_in_secs = max_wait_time_for_order_in_secs
        #
        hdbg.dassert_lte(0, delay_to_accept_in_secs)
        self._delay_to_accept_in_secs = delay_to_accept_in_secs
        #
        hdbg.dassert_lte(0, delay_to_fill_in_secs)
        self._delay_to_fill_in_secs = delay_to_fill_in_secs
        #
        self._broker = broker
        self._asset_id_name = asset_id_name
        self._submitted_orders_table_name = submitted_orders_table_name
        self._accepted_orders_table_name = accepted_orders_table_name
        self._current_positions_table_name = current_positions_table_name
        #
        self._get_wall_clock_time = broker.market_data.get_wall_clock_time
        # NOTE: In our current execution model we place orders in one time slot,
        #  which are executed (completely or not) within the same slot. In this
        #  scenario at most one order list should be in this queue at any given time.
        #  If we change our execution model, then we may need to resize the queue.
        self._orders = asyncio.Queue(maxsize=1)
        # Record keeping.
        self.start_timestamp = None
        self.end_timestamp = None
        self.num_accepted_target_lists = 0
        self.num_accepted_orders = 0
        self.num_filled_orders = 0
        # List of free-form events to represent the execution of this object.
        self.events = []
        #
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("After initialization:\n%s", repr(self))

    # ///////////////////////////////////////////////////////////////////////////
    # Print.
    # ///////////////////////////////////////////////////////////////////////////

    def __str__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_broker", "_orders", "events"])
        return super().__str__(attr_names_to_skip=attr_names_to_skip)

    def __repr__(
        self,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        if attr_names_to_skip is None:
            attr_names_to_skip = []
        attr_names_to_skip.extend(["_broker", "_orders", "events"])
        return super().__repr__(attr_names_to_skip=attr_names_to_skip)

    def get_execution_signature(self) -> str:
        """
        Return a string representation of the relevant events during the
        execution of this object.
        """
        txt = []
        hdbg.dassert_is_not(
            self.end_timestamp, None, "OrderProcessor didn't terminate yet"
        )
        txt.append(f"start_timestamp={self.start_timestamp}")
        txt.append(f"end_timestamp={self.end_timestamp}")
        txt.append(f"termination_condition={self.termination_condition}")
        txt.append(f"num_accepted_orders={self.num_accepted_orders}")
        txt.append(f"num_filled_orders={self.num_filled_orders}")
        txt.append(f"events={len(self.events)}")
        events_as_str = [f"{ts}: {event}" for (ts, event) in self.events]
        txt.append("\n".join(events_as_str))
        # Assemble in a single string.
        txt = "\n".join(txt)
        return txt

    # ///////////////////////////////////////////////////////////////////////////

    async def run_loop(
        self,
    ) -> None:
        """
        Run the order processing loop.

        - Wait for new orders submitted
        - Fill orders
        """
        self._add_event("start")
        wall_clock_time = self._get_wall_clock_time()
        self.start_timestamp = wall_clock_time
        termination_condition = self.termination_condition
        while True:
            target_list_id = self.num_accepted_target_lists
            wall_clock_time = self._get_wall_clock_time()
            # Check whether we should exit or continue.
            if isinstance(termination_condition, pd.Timestamp):
                bar_duration_in_mins = hdateti.convert_seconds_to_minutes(
                    self.bar_duration_in_secs
                )
                hdbg.dassert_lte(1, bar_duration_in_mins)
                period_as_pd_str = f"{bar_duration_in_mins}T"
                wall_clock_time_tmp = wall_clock_time.round(period_as_pd_str)
                termination_condition_tmp = termination_condition.round(
                    period_as_pd_str
                )
                is_done = wall_clock_time_tmp >= termination_condition_tmp
                msg = hprint.to_str(
                    "wall_clock_time termination_condition -> "
                    "wall_clock_time_tmp termination_condition_tmp "
                    "-> is_done",
                    char_separator="",
                )
                self._add_event(msg)
            elif isinstance(termination_condition, int):
                hdbg.dassert_lt(
                    0,
                    termination_condition,
                    "OrderProcessor needs to wait for at least 1 order",
                )
                is_done = target_list_id >= termination_condition
                msg = hprint.to_str(
                    "target_list_id termination_condition " "-> is_done",
                    char_separator="",
                )
                self._add_event(msg)
            else:
                raise ValueError(
                    "Invalid termination_condition=%s type=%s"
                    % (termination_condition, str(type(termination_condition)))
                )
            # Exit if needed.
            if is_done:
                msg = "Exiting loop: " + hprint.to_str(
                    "target_list_id wall_clock_time termination_condition"
                )
                self._add_event(msg)
                self.end_timestamp = wall_clock_time
                break
            # Process requests.
            await self._enqueue_orders()
            await self._dequeue_orders()

    # /////////////////////////////////////////////////////////////////////////////

    def _add_event(self, txt: str) -> None:
        wall_clock_time = self._get_wall_clock_time()
        self.events.append((wall_clock_time, txt))
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", txt)

    # /////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////////

    # - All the logic for handling the fills is in the Broker, while the
    #   OrderProcessor just executes

    # The synchronization mechanism is:
    # - OrderProcessor waits for orders in submitted_orders_table
    #   - Broker
    #     - writes orders in submitted_orders_table
    #     - waits on accepted_orders_table
    # - OrderProcessor
    #   - finds orders in submitted_orders_table
    #   - processes orders (delay)
    #   - updates accepted_orders_table
    #   - plays back the fills updating current_position_table

    # The current implementation relies on OrderProcessor and Broker both waiting
    # for the end of the execution interval.

    # TODO(gp): -> _accept_orders
    async def _enqueue_orders(self) -> None:
        """
        Poll for submitted orders, accept orders, and enqueue for execution.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("enqueue")
        # 1) Wait for orders to be written in `submitted_orders_table_name`:
        #    ```
        #    filename      timestamp_db        order_as_csv
        #    ...
        #    ```
        # TODO(gp): -> _wait_for_submitted_orders
        msg = "Waiting for orders in table " + hprint.to_str(
            "self._submitted_orders_table_name"
        )
        self._add_event(msg)
        poll_kwargs = hasynci.get_poll_kwargs(
            self._get_wall_clock_time,
            timeout_in_secs=self.max_wait_time_for_order_in_secs,
        )
        diff_num_rows = await hsql.wait_for_change_in_number_of_rows(
            self._get_wall_clock_time,
            self._db_connection,
            self._submitted_orders_table_name,
            poll_kwargs,
        )
        msg = hprint.to_str("diff_num_rows")
        self._add_event(msg)
        # Extract the latest file_name after order submission is complete.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Executing query for submitted orders filename...")
        query = f"""
            SELECT filename, timestamp_db
                FROM {self._submitted_orders_table_name}
                ORDER BY timestamp_db"""
        df = hsql.execute_query_to_df(self._db_connection, query)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        hdbg.dassert_lte(
            diff_num_rows,
            len(df),
            "There are not enough new rows in df=\n%s",
            hpandas.df_to_str(df),
        )
        # TODO(gp): For now we accept only one order list.
        hdbg.dassert_eq(diff_num_rows, 1)
        file_name = df.tail(1).squeeze()["filename"]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("file_name=%s", file_name)
        # 2) Wait to simulate the submission being parsed and accepted.
        # TODO(gp): -> _wait_to_accept_submitted_orders
        msg = (
            "Waiting %s seconds to simulate the delay for accepting the order list "
            "submission" % self._delay_to_accept_in_secs
        )
        self._add_event(msg)
        hdbg.dassert_lt(0, self._delay_to_accept_in_secs)
        await hasynci.sleep(
            self._delay_to_accept_in_secs,
            self._get_wall_clock_time,
            tag="Wait for order submission being accepted",
        )
        # 3) Write row in `accepted_orders_table_name` to acknowledge that the
        #    orders were accepted.
        # TODO(gp): -> _accept_submitted_orders
        wall_clock_time = self._get_wall_clock_time()
        trade_date = wall_clock_time.date()
        success = True
        txt = f"""
        strategyid,SAU1
        targetlistid,{self.num_accepted_target_lists}
        tradedate,{trade_date}
        instanceid,1
        filename,{file_name}
        timestamp_processed,{wall_clock_time}
        timestamp_db,{wall_clock_time}
        target_count,1
        changed_count,0
        unchanged_count,0
        cancel_count,0
        success,{success}
        reason,Foobar
        """
        row = hsql.csv_to_series(txt, sep=",")
        hsql.execute_insert_query(
            self._db_connection, row, self._accepted_orders_table_name
        )
        self.num_accepted_target_lists += 1
        # 4) Add the new orders to the internal queue.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Executing query for unfilled submitted orders...")
        query = f"""
            SELECT filename, timestamp_db, orders_as_txt
                FROM {self._submitted_orders_table_name}
                ORDER BY timestamp_db"""
        df = hsql.execute_query_to_df(self._db_connection, query)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        hdbg.dassert_eq(file_name, df.tail(1).squeeze()["filename"])
        orders_as_txt = df.tail(1).squeeze()["orders_as_txt"]
        orders = oordorde.orders_from_string(orders_as_txt)
        self.num_accepted_orders += len(orders)
        self._orders.put_nowait(orders)

    # TODO(gp): -> _process_fills
    async def _dequeue_orders(self) -> None:
        """
        Dequeue orders and apply fills.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("dequeue")
        orders = await self._orders.get()
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("orders"))
        fulfillment_deadline = max([order.end_timestamp for order in orders])
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Order fulfillment deadline=%s", fulfillment_deadline)
        # Wait until the order fulfillment deadline to return fill.
        # TODO(gp): We should query the Broker for fills and keep updating the table
        #  as we go, instead of updating in one shot.
        self._add_event(
            "Wait until fulfillment deadline=%s" % fulfillment_deadline
        )
        await hasynci.async_wait_until(
            fulfillment_deadline, self._get_wall_clock_time
        )
        # Get the fills from the Broker.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("Getting fills from the Broker")
        fills = self._broker.get_fills()
        self.num_filled_orders += len(fills)
        fills_as_str = "\n".join([str(fill) for fill in fills])
        msg = "Received %s fills:\n%s" % (len(fills), hprint.indent(fills_as_str))
        self._add_event(msg)
        self._apply_fills(fills)

    def _apply_fills(self, fills: List[omfill.Fill]) -> None:
        """
        Update current positions based on fills.
        """
        for fill in fills:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("fill=\n%s", str(fill))
            # Extract the fill info.
            id_ = fill.order.order_id
            trade_date = fill.timestamp.date()
            asset_id = fill.order.asset_id
            num_shares = fill.num_shares
            #
            cost = fill.price * fill.num_shares
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("cost=%f" % cost)
            # 1) Get the current positions for `asset_id`.
            # TODO(gp): All the DB changes should be done in a single atomic
            #  transaction instead of multiple ones.
            query = []
            query.append(f"SELECT * FROM {self._current_positions_table_name}")
            where_clause = (
                f"WHERE account='candidate' AND tradedate='{trade_date}' "
                f"AND {self._asset_id_name}={asset_id}"
            )
            query.append(where_clause)
            query = "\n".join(query)
            positions_df = hsql.execute_query_to_df(self._db_connection, query)
            hdbg.dassert_lte(positions_df.shape[0], 1)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("positions_df=%s", hpandas.df_to_str(positions_df))
            # 2) Delete the row from the positions table.
            query = []
            query.append(f"DELETE FROM {self._current_positions_table_name}")
            query.append(where_clause)
            query = "\n".join(query)
            hsql.execute_query(self._db_connection, query)
            # 3) Update the row and insert into the positions table.
            # TODO(Paul): Need to handle BOD position and price, but not sure if it's
            #  even used / useful.
            wall_clock_time = self._get_wall_clock_time()
            if not positions_df.empty:
                # Update position.
                row = positions_df.squeeze()
                hdbg.dassert_isinstance(row, pd.Series)
                row["id"] = int(id_)
                row["tradedate"] = trade_date
                row["timestamp_db"] = wall_clock_time
                row["current_position"] += num_shares
                # A negative net cost for financing a long position.
                row["net_cost"] -= cost
                row[self._asset_id_name] = int(row[self._asset_id_name])
            else:
                # New position.
                txt = f"""
                strategyid,SAU1
                account,candidate
                id,{id_}
                tradedate,{trade_date}
                timestamp_db,{wall_clock_time}
                {self._asset_id_name},{asset_id}
                target_position,0
                current_position,{num_shares}
                open_quantity,0
                net_cost,{-1 * cost}
                bod_position,0
                bod_price,0
                """
                row = hsql.csv_to_series(txt, sep=",")
            row = row.convert_dtypes()
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Insert row is=\n%s", hpandas.df_to_str(row))
            hsql.execute_insert_query(
                self._db_connection, row, self._current_positions_table_name
            )
