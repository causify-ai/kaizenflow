"""
Import as:

import oms.oms_db as oomsdb
"""

import asyncio
import logging
import math
from typing import Any, Dict, Callable, Tuple

import pandas as pd

import helpers.datetime_ as hdateti
import helpers.dbg as hdbg
import helpers.printing as hprint
import helpers.sql as hsql

_LOG = logging.getLogger(__name__)

# TODO(gp): Instead of returning the query just perform it. We should return the
#  query only when we want to freeze the query in a test.
def create_target_files_table(
    connection: hsql.DbConnection, incremental: bool
) -> str:
    """
    Create a table for `target_files`

    :param incremental: if it already exists and `incremental` is:
        - True: skip creating it
        - False: delete and create it from scratch
    """
    # targetlistid                                              1
    #   = just an internal ID.
    # tradedate                                        2021-11-12
    # instanceid                                             3504
    #   = refers to a number that determines a unique "run" of the continuous
    #     trading system service that polls S3 for targets and inserts them
    #     into the DB.
    #   - If we restarted the service intra-day, one would see an updated
    #     `instanceid`. This is just for internal book keeping.
    # filename             s3://${bucket}/files/.../cand/targe...
    #   = the filename we read. In this context, this is the full S3 key that
    #     you uploaded the file to.
    # strategyid                                          {strat}
    # timestamp_processed              2021-11-12 19:59:23.710677
    # timestamp_db                     2021-11-12 19:59:23.716732
    # target_count                                              1
    #   = number of targets in file
    # changed_count                                             0
    #   = number of targets in the file which are different from the last
    #     requested target for the corresponding (account, symbol)
    #   - Targets are considered the "same" if the target position + algo +
    #     algo params are the same. If the target is the same, it is treated as a
    #     no-op and nothing is done, since we're already working to fill that
    #     target.
    #   - One can see zeroes for the changed/unchanged count fields is because
    #     the one target you're passing in is considered "malformed", so it's
    #     neither changed or nor unchanged.
    # unchanged_count                                           0
    #   = number of targets in the file which are the same from the last
    #     requested target for the corresponding (account, symbol)
    # cancel_count                                              0
    # success                                               False
    # reason                              There were a total of..
    table_name = "target_files_processed_candidate_view"
    query = []
    if not incremental:
        query.append(f"DROP TABLE IF EXISTS {table_name}")
    query.append(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            targetlistid SERIAL PRIMARY KEY,
            tradedate DATE NOT NULL,
            instanceid INT,
            filename VARCHAR(255) NOT NULL,
            strategyid VARCHAR(64),
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
    _LOG.debug("query=%s", query)
    connection.cursor().execute(query)
    return table_name


# TODO(gp): This can go in hasyncio.

# A function used to poll. It can accept any inputs and needs to return a bool
# indicating success and a result.
PollOutput = Tuple[bool, Any]
PollingFunction = Callable[[Any], PollOutput]


async def poll(
    func: PollingFunction,
    sleep_in_secs: float,
    timeout_in_secs: float,
    get_wall_clock_time: hdateti.GetWallClockTime,
) -> PollOutput:
    """
    Call `func` every `sleep_in_secs` until a success or timeout.

    :param func: function returning a tuple (success, value)
    :return:
        - number of iterations before a successful call to `func`
        - result from `func`
    :raises: TimeoutError in case of timeout
    """
    _LOG.debug(hprint.to_str("func sleep_in_secs timeout_in_secs"))
    hdbg.dassert_lt(0, sleep_in_secs)
    hdbg.dassert_lt(0, timeout_in_secs)
    max_num_iter = math.ceil(timeout_in_secs / sleep_in_secs)
    hdbg.dassert_lte(1, max_num_iter)
    num_iter = 1
    while True:
        _LOG.debug(
            "\n%s",
            hprint.frame(
                "# Iter %s/%s: wall clock time=%s"
                % (num_iter, max_num_iter, get_wall_clock_time()),
                char1="<",
            ),
        )
        # Poll.
        success, value = func()
        _LOG.debug("success=%s, value=%s", success, value)
        # If success, then exit.
        if success:
            # The function returned.
            _LOG.debug(
                "poll done: wall clock time=%s",
                get_wall_clock_time(),
            )
            return num_iter, value
        # Otherwise update state.
        num_iter += 1
        if num_iter > max_num_iter:
            msg = "Timeout for " + hprint.to_str(
                "func sleep_in_secs timeout_in_secs"
            )
            _LOG.error(msg)
            raise TimeoutError(msg)
        _LOG.debug("sleep for %s secs", sleep_in_secs)
        await asyncio.sleep(sleep_in_secs)


# TODO(gp): This can be general enough to go in hsql.
def _is_target_row_present(
    connection: hsql.DbConnection,
    table_name: str,
    field_name: str,
    target_value: str,
    *,
    show_db_state: bool = False,
) -> PollOutput:
    """
    Check if a row with field_name == target_value is in the given table of the DB.

    E.g., look for the target value "hello_world.txt" in the "filename" field of
    the table "table_name".
    """
    _LOG.debug(hprint.to_str("connection table_name field_name target_value"))
    # Print the state of the DB, if needed.
    if show_db_state:
        query = f"SELECT * FROM {table_name}"
        df = hsql.execute_query(connection, query)
        _LOG.debug("df=\n%s", hprint.dataframe_to_str(df, use_tabulate=False))
    # Check if the required row is available.
    query = f"SELECT {field_name} FROM {table_name} WHERE {field_name}='{target_value}'"
    df = hsql.execute_query(connection, query)
    _LOG.debug("df=\n%s", hprint.dataframe_to_str(df, use_tabulate=False))
    success = df.shape[0] > 0
    result = None
    return success, result


async def wait_for_target_ack(
    connection: hsql.DbConnection, target_value: str, poll_kwargs: Dict[str, Any]
) -> PollOutput:
    """
    Wait until the target is acknowledged by the DB.

    :param poll_kwargs: a dictionary with the kwargs for `poll()`.
    """
    table_name = "target_files_processed_candidate_view"
    field_name = "filename"
    # Create the polling function.
    func = lambda: _is_target_row_present(
        connection, table_name, field_name, target_value
    )
    # Poll.
    rc, result = await poll(func, **poll_kwargs)
    return rc, result
