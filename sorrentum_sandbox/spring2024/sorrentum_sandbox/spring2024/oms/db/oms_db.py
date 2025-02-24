"""
Implement the DB interface of a broker accepting orders.

Import as:

import oms.db.oms_db as odbomdb
"""

import logging
from typing import Any, Dict

import helpers.hasyncio as hasynci
import helpers.hprint as hprint
import helpers.hsql as hsql

_LOG = logging.getLogger(__name__)


# #############################################################################
# Submitted orders
# #############################################################################


SUBMITTED_ORDERS_TABLE_NAME = "submitted_orders"


def create_submitted_orders_table(
    db_connection: hsql.DbConnection, incremental: bool, table_name: str
) -> str:
    """
    Create a table storing the orders submitted to the system.
    """
    # - filename (e.g., s3://${bucket}/files/.../cand/targe...)
    #     = the filename we read. In this context, this is the full S3 key that
    #       you uploaded the file to.
    # - timestamp_db (e.g., 2021-11-12 19:59:23.716732)
    # - order_as_csv
    #     = target order in CSV format
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("db_connection incremental table_name"))
    query = []
    if not incremental:
        query.append(f"DROP TABLE IF EXISTS {table_name}")
    query.append(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            filename VARCHAR(255) NOT NULL,
            timestamp_db TIMESTAMP NOT NULL,
            orders_as_txt VARCHAR(16384)
            )
            """
    )
    query = "; ".join(query)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("query=%s", query)
    db_connection.cursor().execute(query)
    return table_name


# #############################################################################
# Accepted orders
# #############################################################################


# This corresponds to the table "target_files_processed_candidate_view" of an
# implemented system.
ACCEPTED_ORDERS_TABLE_NAME = "accepted_orders"


def create_accepted_orders_table(
    db_connection: hsql.DbConnection, incremental: bool, table_name: str
) -> str:
    """
    Create a table for acknowledging that orders have been accepted.
    """
    # - strategyid (e.g., "strat")
    # - targetlistid (e.g., 1)
    #     = just an internal ID
    # - tradedate (e.g., 2021-11-12)
    # - instanceid (e.g., 3504)
    #     = refers to a number that determines a unique "run" of the continuous
    #       trading system service that polls S3 for targets and inserts them
    #       into the DB.
    #     - If we restarted the service intra-day, one would see an updated
    #       `instanceid`. This is just for internal book keeping.
    # - filename (e.g., s3://${bucket}/files/.../cand/targe...)
    #     = the filename we read. In this context, this is the full S3 key that
    #       you uploaded the file to.
    # - timestamp_processed (e..g, 2021-11-12 19:59:23.710677)
    # - timestamp_db (e.g., 2021-11-12 19:59:23.716732)
    # - target_count (e.g., 1)
    #     = number of targets in file
    # - changed_count (e.g., 0)
    #     = number of targets in the file which are different from the last
    #       requested target for the corresponding (account, symbol)
    #     - Targets are considered the "same" if the target position + algo +
    #       algo params are the same. If the target is the same, it is treated as a
    #       no-op and nothing is done, since we're already working to fill that
    #       target.
    #     - One can see zeroes for the changed/unchanged count fields is because
    #       the one target you're passing in is considered "malformed", so it's
    #       neither changed or nor unchanged.
    # - unchanged_count (e.g., 0)
    #     = number of targets in the file which are the same from the last
    #       requested target for the corresponding (account, symbol)
    # - cancel_count (e.g., 0)
    # - success (e.g., False)
    # - reason (e.g., There were a total of..)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("db_connection incremental table_name"))
    query = []
    if not incremental:
        query.append(f"DROP TABLE IF EXISTS {table_name}")
    query.append(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            strategyid VARCHAR(64),
            targetlistid SERIAL PRIMARY KEY,
            tradedate DATE NOT NULL,
            instanceid INT,
            filename VARCHAR(255) NOT NULL,
            timestamp_processed TIMESTAMP NOT NULL,
            timestamp_db TIMESTAMP NOT NULL,
            target_count INT,
            changed_count INT,
            unchanged_count INT,
            cancel_count INT,
            success BOOL,
            reason VARCHAR(255)
            )
            """
    )
    query = "; ".join(query)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("query=%s", query)
    db_connection.cursor().execute(query)
    return table_name


# #############################################################################
# Current positions
# #############################################################################


# This corresponds to the table "current_positions_candidate_view" of an
# implemented system.
CURRENT_POSITIONS_TABLE_NAME = "current_positions"


def create_current_positions_table(
    db_connection: hsql.DbConnection,
    incremental: bool,
    asset_id_name: str,
    table_name: str,
) -> str:
    """
    Create a table holding the current positions.

    :param db_connection: connection to DB containing order data
    :param incremental: if True, append to existing table
    :param asset_id_name: name of the asset id to be used in the DB (e.g., `asset_id`)
    :param table_name: name of the current positions table
    :return: name of created table
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str("db_connection incremental asset_id_name table_name")
        )
    query = []
    if not incremental:
        query.append(f"DROP TABLE IF EXISTS {table_name}")
    # The current positions table has the following fields:
    # - strategyid (e.g., SAU1)
    # - account (e.g., SAU1_CAND)
    # - id (e.g., 10005)
    # - tradedate (e.g., 2021-10-28)
    # - published_dt (e.g., 2021-10-28 12:01:49.41)
    # - target_position (e.g., 300)
    #   = the fully realized portfolio position
    #   - E.g., the value is 300 if we own 100 AAPL and we want get 200 more so
    #     we send an order for 200
    # - current_position (e.g., 100)
    #   = what we own (e.g., 100 AAPL)
    # - open_quantity (e.g., 200)
    #   = how many shares we have orders open in the market. In other words,
    #     open quantity reflects how much is out getting executed in the market
    #   - Note that it's not always
    #     `open_quantity = target_position - current_position`
    #     since orders might have been cancelled. If `open_quantity = 0` it
    #     means that there are no order in the market
    #   - E.g., if we send orders for 200 AAPL, then current_position = 200, but
    #     if we cancel the orders, current_position = 0, even if target_position
    #     reports what we were targeting 200 shares
    # - net_cost (e.g., 0.0)
    #   = fill-quantity * signed fill_price with respect to the BOD price
    #   - In practice it is the average price paid
    # - bod_position (e.g., 0)
    #   - = number of shares at BOD
    # - bod_price (e.g., 0.0)
    #   - = price of a share at BOD
    query.append(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            strategyid VARCHAR(64),
            account VARCHAR(64),
            id INT,
            tradedate DATE NOT NULL,
            timestamp_db TIMESTAMP NOT NULL,
            {asset_id_name} INT,
            target_position FLOAT,
            current_position FLOAT,
            open_quantity FLOAT,
            net_cost FLOAT,
            bod_position FLOAT,
            bod_price FLOAT
            );
            """
    )
    query = "; ".join(query)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("query=%s", query)
    db_connection.cursor().execute(query)
    return table_name


# #############################################################################
# Restrictions
# #############################################################################


# This corresponds to the table "restrictions_candidate_view" of an
# implemented system.
RESTRICTIONS_TABLE_NAME = "restrictions"


def create_restrictions_table(
    db_connection: hsql.DbConnection,
    incremental: bool,
    asset_id_name: str,
    table_name: str,
) -> str:
    """
    Create a table holding restrictions.

    :param db_connection: connection to DB containing order data
    :param incremental: if True, append to existing table
    :param asset_id_name: name of the asset id to be used in the DB (e.g., `asset_id`)
    :param table_name: name of the restrictions table
    :return: name of created table
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(
            hprint.to_str("db_connection incremental asset_id_name table_name")
        )
    query = []
    if not incremental:
        query.append(f"DROP TABLE IF EXISTS {table_name}")
    query.append(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            strategyid VARCHAR(64),
            account VARCHAR(64),
            id INT,
            tradedate DATE NOT NULL,
            timestamp_db TIMESTAMP NOT NULL,
            {asset_id_name} INT,
            is_restricted BOOL,
            is_buy_restricted BOOL,
            is_buy_cover_restricted BOOL,
            is_sell_short_restricted BOOL,
            is_sell_long_restricted BOOL
            );
            """
    )
    query = "; ".join(query)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("query=%s", query)
    db_connection.cursor().execute(query)
    return table_name


# #############################################################################
# API
# #############################################################################

# We can only create / remove tables in a DB controlled by us, so we can hard-wire
# the table names to the ones we use. When the DB is external, then the caller
# needs to specify the names of the tables.


def create_oms_tables(
    db_connection: hsql.DbConnection, incremental: bool, asset_id_name: str
) -> None:
    create_accepted_orders_table(
        db_connection, incremental, ACCEPTED_ORDERS_TABLE_NAME
    )
    create_submitted_orders_table(
        db_connection, incremental, SUBMITTED_ORDERS_TABLE_NAME
    )
    create_current_positions_table(
        db_connection, incremental, asset_id_name, CURRENT_POSITIONS_TABLE_NAME
    )
    create_restrictions_table(
        db_connection, incremental, asset_id_name, RESTRICTIONS_TABLE_NAME
    )


def remove_oms_tables(db_connection: hsql.DbConnection) -> None:
    for table_name in [
        SUBMITTED_ORDERS_TABLE_NAME,
        ACCEPTED_ORDERS_TABLE_NAME,
        CURRENT_POSITIONS_TABLE_NAME,
        RESTRICTIONS_TABLE_NAME,
    ]:
        hsql.remove_table(db_connection, table_name)


# TODO(gp): This might be part of DatabaseBroker. It is also used in some tests.
async def wait_for_order_acceptance(
    db_connection: hsql.DbConnection,
    target_value: str,
    poll_kwargs: Dict[str, Any],
    *,
    table_name: str = ACCEPTED_ORDERS_TABLE_NAME,
    field_name: str = "filename",
) -> hasynci.PollOutput:
    """
    Wait until the desired order is accepted by the OMS.

    The order is accepted when there is a value `target_value` in the column
    `file_name` of the expected table.

    :param poll_kwargs: a dictionary with the kwargs for `poll()`.
    """
    # Create a polling function that checks whether `target_value` is present
    # in the `field_name` column of the table `table_name`.
    # TODO(Paul): Expose `show_db_state`.
    polling_func = lambda: hsql.is_row_with_value_present(
        db_connection,
        table_name,
        field_name,
        target_value,
        show_db_state=False,
    )
    tag = "wait_for_order_acceptance"
    # Poll.
    rc, result = await hasynci.poll(polling_func, tag=tag, **poll_kwargs)
    return rc, result
