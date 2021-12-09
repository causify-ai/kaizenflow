import asyncio
import logging
from typing import Any, Callable, Coroutine, List

import pandas as pd
import pytest

import helpers.datetime_ as hdateti
import helpers.git as hgit
import helpers.hasyncio as hasynci
import helpers.hsql_test as hsqltest
import helpers.printing as hprint
import helpers.sql as hsql
import oms.oms_db as oomsdb

_LOG = logging.getLogger(__name__)


class TestOmsDbHelper(hsqltest.TestDbHelper):
    @staticmethod
    def _get_compose_file() -> str:
        # TODO(gp): This information should be retrieved from oms_lib_tasks.py.
        #  We can also use the invoke command.
        return "oms/devops/compose/docker-compose.yml"

    # TODO(Dan): Deprecate after #585.
    @staticmethod
    def _get_db_name() -> str:
        return "oms_postgres_db_local"

    @staticmethod
    def _get_service_name() -> str:
        return "oms_postgres_local"


@pytest.mark.skip(reason="Run manually to clean up the DB")
class TestOmsDbRemoveAllTables1(TestOmsDbHelper):
    """
    This is used to reset the state of the DB.
    """

    def test1(self) -> None:
        hsql.remove_all_tables(self.connection)


def _test_create_table_helper(
    self_: Any,
    connection: hsql.DbConnection,
    table_name: str,
    create_table_func: Callable,
) -> None:
    # Verify that the DB is up.
    db_list = hsql.get_db_names(connection)
    _LOG.info("db_list=%s", db_list)
    # Clean up the table.
    hsql.remove_table(connection, table_name)
    # The DB should not have this table.
    db_tables = hsql.get_table_names(connection)
    _LOG.info("get_table_names=%s", db_tables)
    self_.assertNotIn(table_name, db_tables)
    # Create the table.
    _ = create_table_func(connection, incremental=False)
    # The table should be present.
    db_tables = hsql.get_table_names(connection)
    _LOG.info("get_table_names=%s", db_tables)
    self_.assertIn(table_name, db_tables)
    # Delete the table.
    hsql.remove_table(connection, table_name)


@pytest.mark.skipif(
    hgit.is_dev_tools() or hgit.is_lime(), reason="Need dind support"
)
class TestOmsDbSubmittedOrdersTable1(TestOmsDbHelper):
    """
    Test operations on the submitted orders table.
    """

    @pytest.mark.slow("9 seconds.")
    def test_create_table1(self) -> None:
        """
        Test creating the table.
        """
        table_name = oomsdb.SUBMITTED_ORDERS_TABLE_NAME
        create_table_func = oomsdb.create_submitted_orders_table
        _test_create_table_helper(
            self, self.connection, table_name, create_table_func
        )


# #############################################################################


def _to_series(txt: str) -> pd.Series:
    """
    Convert a text with (key, value) separated by `|` into a pd.series.
    """
    # _LOG.debug("txt=\n%s", txt)
    tuples = [tuple(line.split("|")) for line in hprint.dedent(txt).split("\n")]
    # _LOG.debug("tuples=%s", str(tuples))
    # Remove empty tuples.
    tuples = [t for t in tuples if t[0] != ""]
    index, data = zip(*tuples)
    # _LOG.debug("index=%s", index)
    # _LOG.debug("data=%s", data)
    srs = pd.Series(data, index=index)
    return srs


def _get_row1() -> pd.Series:
    row = """
    tradedate|2021-11-12
    targetlistid|1
    instanceid|3504
    filename|hello_world.txt
    strategyid|SAU1
    timestamp_processed|2021-11-12 19:59:23.710677
    timestamp_db|2021-11-12 19:59:23.716732
    target_count|1
    changed_count|0
    unchanged_count|0
    cancel_count|0
    success|False
    reason|"There were a total of 1 malformed requests in the file.
    """
    srs = _to_series(row)
    return srs


def _get_row2() -> pd.Series:
    row = """
    tradedate|2021-11-12
    targetlistid|2
    instanceid|3504
    filename|s3://targets/20211112000000/positions.16.2021-11-12_15:44:04-05:00.csv
    strategyid|SAU1
    timestamp_processed|2021-11-12 20:45:07.463641
    timestamp_db|2021-11-12 20:45:07.469807
    target_count|1
    changed_count|0
    unchanged_count|0
    cancel_count|0
    success|False
    reason|"There were a total of 1 malformed requests in the file."
    """
    srs = _to_series(row)
    return srs


def _get_row3() -> pd.Series:
    row = """
    tradedate|2021-11-12
    targetlistid|5
    instanceid|3504
    filename|s3://targets/20211112000000/positions.3.2021-11-12_16:38:22-05:00.csv
    strategyid|SAU1
    timestamp_processed|2021-11-12 21:38:39.414138
    timestamp_db|2021-11-12 21:38:39.419536
    target_count|1
    changed_count|1
    unchanged_count|0
    cancel_count|0
    success|True
    reason|
    """
    srs = _to_series(row)
    return srs


# #############################################################################


@pytest.mark.skipif(
    hgit.is_dev_tools() or hgit.is_lime(), reason="Need dind support"
)
class TestOmsDbAcceptedOrdersTable1(TestOmsDbHelper):
    """
    Test operations on the accepted orders table.
    """

    @pytest.mark.slow("9 seconds.")
    def test_up1(self) -> None:
        """
        Verify that the DB is up.
        """
        db_list = hsql.get_db_names(self.connection)
        _LOG.info("db_list=%s", db_list)

    @pytest.mark.slow("8 seconds.")
    def test_create_table1(self) -> None:
        """
        Test creating the table.
        """
        # # Clean up the table.
        # table_name = oomsdb.ACCEPTED_ORDERS_TABLE_NAME
        # hsql.remove_table(self.connection, table_name)
        # # The DB should not have that table.
        # db_tables = hsql.get_table_names(self.connection)
        # _LOG.info("get_table_names=%s", db_tables)
        # self.assertNotIn(oomsdb.ACCEPTED_ORDERS_TABLE_NAME, db_tables)
        # # Create the table.
        # _ = oomsdb.create_accepted_orders_table(
        #     self.connection, incremental=False
        # )
        # # The table should be present.
        # db_tables = hsql.get_table_names(self.connection)
        # _LOG.info("get_table_names=%s", db_tables)
        # self.assertIn(oomsdb.ACCEPTED_ORDERS_TABLE_NAME, db_tables)
        # # Delete the table.
        # hsql.remove_table(self.connection, oomsdb.ACCEPTED_ORDERS_TABLE_NAME)
        table_name = oomsdb.ACCEPTED_ORDERS_TABLE_NAME
        create_table_func = oomsdb.create_accepted_orders_table
        _test_create_table_helper(
            self, self.connection, table_name, create_table_func
        )

    @pytest.mark.slow("8 seconds.")
    def test_insert1(self) -> None:
        """
        Test inserting in the table.
        """
        # Create the table.
        table_name = oomsdb.create_accepted_orders_table(
            self.connection, incremental=True
        )
        # Insert a row.
        row = _get_row1()
        hsql.execute_insert_query(self.connection, row, table_name)
        # Insert another row.
        row = _get_row2()
        hsql.execute_insert_query(self.connection, row, table_name)
        # Insert another row.
        row = _get_row3()
        hsql.execute_insert_query(self.connection, row, table_name)
        # Check the content of the table.
        query = f"SELECT * FROM {table_name}"
        df = hsql.execute_query_to_df(self.connection, query)
        act = hprint.dataframe_to_str(df)
        exp = r"""
           targetlistid   tradedate  instanceid                                                                filename strategyid        timestamp_processed               timestamp_db  target_count  changed_count  unchanged_count  cancel_count  success                                                     reason
        0             1  2021-11-12        3504                                                         hello_world.txt       SAU1 2021-11-12 19:59:23.710677 2021-11-12 19:59:23.716732             1              0                0             0    False   "There were a total of 1 malformed requests in the file.
        1             2  2021-11-12        3504  s3://targets/20211112000000/positions.16.2021-11-12_15:44:04-05:00.csv       SAU1 2021-11-12 20:45:07.463641 2021-11-12 20:45:07.469807             1              0                0             0    False  "There were a total of 1 malformed requests in the file."
        2             5  2021-11-12        3504   s3://targets/20211112000000/positions.3.2021-11-12_16:38:22-05:00.csv       SAU1 2021-11-12 21:38:39.414138 2021-11-12 21:38:39.419536             1              1                0             0     True                                                           """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Delete the table.
        hsql.remove_table(self.connection, oomsdb.ACCEPTED_ORDERS_TABLE_NAME)


# TODO(gp): -> gather
# TODO(gp): Move to hasyncio.py
async def gather_coroutines(*coroutines: List[Coroutine]) -> List[Any]:
    result = await asyncio.gather(*coroutines)
    return result


async def gather_coroutines_with_wall_clock(
    event_loop: asyncio.AbstractEventLoop, *coroutines: List[Coroutine]
) -> List[Any]:
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="ET", event_loop=event_loop
    )
    # Construct the coroutines here by passing the `get_wall_clock_time()`
    # function.
    coroutines = [coro(get_wall_clock_time) for coro in coroutines]
    #
    result = await gather_coroutines(*coroutines)
    return result


@pytest.mark.skipif(
    hgit.is_dev_tools() or hgit.is_lime(), reason="Need dind support"
)
class TestOmsDb2(TestOmsDbHelper):
    """
    Test interactions through the DB.
    """

    def wait_for_table_helper(self, coroutines: List[Any]) -> Any:
        """
        Create a clean DB table and run the coroutines.
        """
        oomsdb.create_accepted_orders_table(self.connection, incremental=False)
        with hasynci.solipsism_context() as event_loop:
            # get_wall_clock_time = lambda: hdateti.get_current_time(
            #     tz="ET", event_loop=event_loop
            # )
            # # Construct the coroutines here by passing the `get_wall_clock_time()`
            # # function.
            # coroutines = [coro(get_wall_clock_time) for coro in coroutines]
            # # Run.
            coroutine = gather_coroutines_with_wall_clock(event_loop, *coroutines)
            res = hasynci.run(coroutine, event_loop=event_loop)
            return res
        # Delete the table.
        hsql.remove_table(self.connection, oomsdb.ACCEPTED_ORDERS_TABLE_NAME)

    @pytest.mark.slow("9 seconds.")
    def test_wait_for_table1(self) -> None:
        """
        Show that if the value doesn't show up in the DB there is a timeout.
        """
        # Create only one coroutine waiting for a row in the table that is never
        # written, causing a timeout.
        coroutines = [self._db_poller]
        with self.assertRaises(TimeoutError):
            self.wait_for_table_helper(coroutines)

    @pytest.mark.slow("9 seconds.")
    def test_wait_for_table2(self) -> None:
        """
        Show that waiting on a value on the table works.
        """
        coroutines = []
        # Add a DB poller waiting for a row in the table.
        coroutines.append(self._db_poller)
        # Add a DB writer that will write after 2 seconds, making the DB poller
        # exiting successfully.
        sleep_in_secs = 2
        coroutines.append(lambda gwct: self._db_writer(sleep_in_secs, gwct))
        # Run.
        res = self.wait_for_table_helper(coroutines)
        # Check output.
        act = str(res)
        # The output is (DB poller, DB writer).
        exp = r"""[[(3, None)], None]"""
        self.assert_equal(act, exp)

    @pytest.mark.slow("9 seconds.")
    def test_wait_for_table3(self) -> None:
        """
        The data is written too late triggering a timeout.
        """
        coroutines = []
        # Add a DB poller waiting for a row in the table.
        coroutines.append(self._db_poller)
        # Add a DB writer that will write after 10 seconds, after the DB poller ends
        # after 5 secs.
        sleep_in_secs = 10
        coroutines.append(lambda gwct: self._db_writer(sleep_in_secs, gwct))
        # Run.
        with self.assertRaises(TimeoutError):
            self.wait_for_table_helper(coroutines)

    async def _db_poller(
        self, get_wall_clock_time: hdateti.GetWallClockTime
    ) -> Any:
        """
        Poll a DB for a certain value.
        """
        _LOG.debug("get_wall_clock_time=%s", get_wall_clock_time())
        #
        target_value = "hello_world.txt"
        poll_kwargs = {
            "sleep_in_secs": 1.0,
            "timeout_in_secs": 5.0,
            "get_wall_clock_time": get_wall_clock_time,
        }
        coro = oomsdb.wait_for_order_accepted(
            self.connection, target_value, poll_kwargs
        )
        result = await asyncio.gather(coro)
        _LOG.debug("get_wall_clock_time=%s", get_wall_clock_time())
        return result

    async def _db_writer(
        self, sleep_in_secs: float, get_wall_clock_time: hdateti.GetWallClockTime
    ) -> None:
        """
        Wait some time and then write a row in the DB.
        """
        table_name = oomsdb.ACCEPTED_ORDERS_TABLE_NAME
        # Sleep.
        _LOG.debug("get_wall_clock_time=%s", get_wall_clock_time())
        _LOG.debug("sleep for %s secs", sleep_in_secs)
        await asyncio.sleep(sleep_in_secs)
        # Insert the row.
        _LOG.debug("get_wall_clock_time=%s", get_wall_clock_time())
        _LOG.debug("insert ...")
        row = _get_row1()
        hsql.execute_insert_query(self.connection, row, table_name)
        _LOG.debug("get_wall_clock_time=%s", get_wall_clock_time())
        _LOG.debug("insert ... done")
        # Show the state of the DB.
        query = f"SELECT * FROM {table_name}"
        df = hsql.execute_query_to_df(self.connection, query)
        _LOG.debug("df=\n%s", hprint.dataframe_to_str(df, use_tabulate=False))
