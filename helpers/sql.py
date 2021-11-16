"""
Import as:

import helpers.sql as hsql
"""

import collections
import io
import logging
import os
import time
from typing import List, NamedTuple, Optional, Tuple, Union

import pandas as pd
import psycopg2 as psycop
import psycopg2.sql as psql
from psycopg2 import extras

import helpers.dbg as hdbg
import helpers.printing as hprint
import helpers.system_interaction as hsysinte
import helpers.timer as htimer

_LOG = logging.getLogger(__name__)

# #############################################################################
# Connection
# #############################################################################

# Invariant: keep the arguments in the interface in the same order as: host,
#  dbname, port, user, password

# TODO(gp): mypy doesn't like this. Understand why and / or inline.
DbConnection = psycop.extensions.connection


# TODO(gp): host, dbname, ...
DbConnectionInfo = collections.namedtuple(
    "DbConnectionInfo", ["dbname", "host", "port", "user", "password"]
)


# TODO(gp): Return only the connection (CmampTask441).
# TODO(gp): Reorg params -> host, dbname, user, port
def get_connection(
    dbname: str,
    host: str,
    user: str,
    port: int,
    password: str,
    autocommit: bool = True,
) -> Tuple[DbConnection, psycop.extensions.cursor]:
    """
    Create a connection and cursor for a SQL database.
    """
    _LOG.debug(hprint.to_str("host dbname port user"))
    connection = psycop.connect(
        host=host, dbname=dbname, port=port, user=user, password=password
    )
    cursor = connection.cursor()
    if autocommit:
        connection.autocommit = True
    return connection, cursor


# TODO(gp): Return only the connection (CmampTask441).
def get_connection_from_env_vars() -> Tuple[
    DbConnection, psycop.extensions.cursor
]:
    """
    Create a SQL connection with the information from the environment
    variables.
    """
    # Get values from the environment variables.
    # TODO(gp): -> POSTGRES_DBNAME
    host = os.environ["POSTGRES_HOST"]
    dbname = os.environ["POSTGRES_DB"]
    user = os.environ["POSTGRES_USER"]
    port = int(os.environ["POSTGRES_PORT"])
    password = os.environ["POSTGRES_PASSWORD"]
    # Build the
    connection, cursor = get_connection(
        dbname=dbname,
        host=host,
        port=port,
        user=user,
        password=password,
    )
    return connection, cursor


def get_connection_from_string(
    conn_as_str: str,
    autocommit: bool = True,
) -> Tuple[DbConnection, psycop.extensions.cursor]:
    """
    Create a connection from a string.

    TODO(gp): E.g., add example
    """
    connection = psycop.connect(conn_as_str)
    cursor = connection.cursor()
    if autocommit:
        connection.autocommit = True
    return connection, cursor


def check_db_connection(
    host: str,
    dbname: str,
    port: int,
) -> bool:
    """
    Check whether a connection to a DB exists, in a non-blocking way.
    """
    cmd = f"pg_isready -d {dbname} -p {port} -h {host}"
    rc = hsysinte.system(cmd, abort_on_error=False)
    conn_exists = rc == 0
    return conn_exists


# TODO(gp): Rearrange as host, dbname (instead of db_name), port.
def wait_db_connection(
    db_name: str, port: int, host: str, timeout_in_secs: int = 10
) -> None:
    """
    Wait until the database is available.

    :param timeout_in_secs: secs before timing out with `RuntimeError`.
    """
    hdbg.dassert_lte(1, timeout_in_secs)
    _LOG.debug("db_name=%s, port=%s, host=%s", db_name, port, host)
    elapsed_secs = 0
    while True:
        _LOG.info("Waiting for PostgreSQL to become available...")
        conn_exists = check_db_connection(host, db_name, port)
        if conn_exists:
            _LOG.info("PostgreSQL is available (after %s seconds)", elapsed_secs)
            break
        if elapsed_secs > timeout_in_secs:
            raise RuntimeError(
                f"Cannot connect to db host={host} db_name={db_name} port={port}"
            )
        elapsed_secs += 1
        time.sleep(1)


def db_connection_to_tuple(connection: DbConnection) -> NamedTuple:
    """
    Get database connection details using connection. Connection details
    include:

        - Database name
        - Host
        - Port
        - Username
        - Password

    :param connection: a database connection
    :return: database connection details
    """
    info = connection.info
    det = DbConnectionInfo(
        dbname=info.dbname,
        host=info.host,
        port=info.port,
        user=info.user,
        password=info.password,
    )
    return det


# #############################################################################
# State of the whole DB
# #############################################################################


def get_engine_version(connection: DbConnection) -> str:
    """
    Report information on the SQL engine.

    E.g., ``` PostgreSQL 11.5 on x86_64-pc-linux-gnu compiled by gcc
    (GCC) 4.8.3 20140911 (Red Hat 4.8.3-9), 64-bit ```
    """
    query = "SELECT version();"
    df = pd.read_sql_query(query, connection)
    # pylint: disable=no-member
    info: str = df.iloc[0, 0]
    return info


# TODO(gp): Test / fix this.
def get_indexes(connection: DbConnection) -> pd.DataFrame:
    res = []
    tables = get_table_names(connection)
    cursor = connection.cursor()
    for table in tables:
        query = (
            """SELECT * FROM pg_indexes WHERE tablename = '{table}' """.format(
                table=table
            )
        )
        cursor.execute(query)
        z = cursor.fetchall()
        res.append(pd.DataFrame(z))
    tmp: pd.DataFrame = pd.concat(res)
    tmp["index_type"] = tmp[4].apply(
        lambda w: w.split("USING")[1].lstrip().split(" ")[0]
    )
    tmp.columns = [
        "type: public/private",
        "table_name",
        "key_name",
        "None",
        "Statement",
        "index_type",
    ]
    tmp["columns"] = tmp["Statement"].apply(lambda w: w.split("(")[1][:-1])

    return tmp


# #############################################################################
# Database
# #############################################################################


def get_db_names(connection: DbConnection) -> List[str]:
    """
    Return the names of the available DBs.

    E.g., ['postgres', 'rdsadmin', 'template0', 'template1']
    """
    query = "SELECT datname FROM pg_database;"
    cursor = connection.cursor()
    cursor.execute(query)
    dbs = list(zip(*cursor.fetchall()))[0]
    dbs = sorted(dbs)
    return dbs


def create_database(
    connection: DbConnection,
    dbname: str,
    overwrite: Optional[bool] = None,
) -> None:
    """
    Create empty database.

    :param connection: database connection
    :param dbname: database to create
    :param overwrite: overwrite existing database
    """
    _LOG.debug("connection=%s", connection)
    with connection.cursor() as cursor:
        if overwrite:
            cursor.execute(
                psql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE);").format(
                    psql.Identifier(dbname)
                )
            )
        else:
            if dbname in get_table_names(connection):
                raise ValueError(f"Database {dbname} already exists")
        cursor.execute(
            psql.SQL("CREATE DATABASE {};").format(psql.Identifier(dbname))
        )


def remove_database(connection: DbConnection, dbname: str) -> None:
    """
    Remove database in current environment.

    :param connection: a database connection
    :param dbname: database name to drop, e.g. `im_db_local`
    """
    # Drop database.
    # From https://stackoverflow.com/questions/36502401
    connection.cursor().execute(
        psql.SQL("DROP DATABASE {} WITH (FORCE);").format(psql.Identifier(dbname))
    )


# #############################################################################
# Tables
# #############################################################################


def get_table_names(connection: DbConnection) -> List[str]:
    """
    Report the name of the tables.

    E.g., tables=['entities', 'events', 'stories', 'taxonomy']
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        AND table_schema = 'public'
    """
    cursor = connection.cursor()
    cursor.execute(query)
    tables = [x[0] for x in cursor.fetchall()]
    return tables


# TODO(gp): -> get_tables_size
def get_table_size(
    connection: DbConnection,
    only_public: bool = True,
    summary: bool = True,
) -> pd.DataFrame:
    """
    Report the size of each table.

    E.g.,

      table_name  row_estimate   total    index      toast  table
    0     events           0.0   26 GB  0 bytes  192 bytes  26 GB
    1    stories           0.0   15 GB    43 GB  192 bytes  12 GB
    2   entities    10823400.0   76 MB  0 bytes  192 bytes  76 MB
    3   taxonomy       20691.0  690 kB  0 bytes  192 bytes 652 kB
    """
    q = """SELECT *, pg_size_pretty(total_bytes) AS total
        , pg_size_pretty(index_bytes) AS INDEX
        , pg_size_pretty(toast_bytes) AS toast
        , pg_size_pretty(table_bytes) AS TABLE
      FROM (
      SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
          SELECT c.oid,nspname AS table_schema, relname AS TABLE_NAME
                  , c.reltuples AS row_estimate
                  , pg_total_relation_size(c.oid) AS total_bytes
                  , pg_indexes_size(c.oid) AS index_bytes
                  , pg_total_relation_size(reltoastrelid) AS toast_bytes
              FROM pg_class c
              LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE relkind = 'r'
      ) a
    ) a
    ORDER by total_bytes DESC"""
    df = pd.read_sql_query(q, connection)
    if only_public:
        df = df[df["table_schema"] == "public"]
    if summary:
        cols = "table_name row_estimate total index toast table".split()
        df = df[cols]
    return df


def head_table(
    connection: DbConnection,
    table: str,
    limit: int = 5,
) -> str:
    """
    Report the head of the table as str.
    """
    txt = []
    query = "SELECT * FROM %s LIMIT %s " % (table, limit)
    df = execute_query(connection, query)
    # pd.options.display.max_columns = 1000
    # pd.options.display.width = 130
    txt.append(str(df))
    txt = "\n".join(txt)
    return txt


def head_tables(
    connection: DbConnection,
    tables: Optional[List[str]] = None,
    limit: int = 5,
) -> str:
    txt = []
    if tables is None:
        tables = get_table_names(connection)
    for table in tables:
        txt.append("\n" + "#" * 80 + "\n" + table + "\n" + "#" * 80)
        txt_tmp = head_table(connection, table, limit=limit)
        txt.append(txt_tmp)
    txt = "\n".join(txt)
    return txt


# TODO(gp): -> get_table_columns
def get_columns(connection: DbConnection, table_name: str) -> list:
    """
    Get column names for given table.
    """
    query = (
        """SELECT column_name
                FROM information_schema.columns
                WHERE TABLE_NAME = '%s' """
        % table_name
    )
    cursor = connection.cursor()
    cursor.execute(query)
    columns = [x[0] for x in cursor.fetchall()]
    return columns


# TODO(gp): -> find_tables_common_columns
def find_common_columns(
    connection: DbConnection,
    tables: List[str],
    as_df: bool = False,
) -> Union[None, pd.DataFrame]:
    limit = 5
    df = []
    for i, table in enumerate(tables):
        table = tables[i]
        query = "SELECT * FROM %s LIMIT %s " % (table, limit)
        df1 = execute_query(connection, query, verbose=False)
        if df1 is None:
            continue
        for j in range(i + 1, len(tables)):
            table = tables[j]
            query = "SELECT * FROM %s LIMIT %s " % (table, limit)
            df2 = execute_query(connection, query, verbose=False)
            if df2 is None:
                continue
            common_cols = [c for c in df1 if c in df2]
            if as_df:
                df.append(
                    (
                        tables[i],
                        tables[j],
                        len(common_cols),
                        " ".join(common_cols),
                    )
                )
            else:
                print(("'%s' vs '%s'" % (tables[i], tables[j])))
                print(
                    ("    (%s): %s" % (len(common_cols), " ".join(common_cols)))
                )
    obj = None
    if as_df:
        obj = pd.DataFrame(
            df, columns=["table1", "table2", "num_comm_cols", "common_cols"]
        )
    return obj


# #############################################################################
# Query
# #############################################################################


# TODO(gp): -> execute_query_to_df
def execute_query(
    connection: DbConnection,
    query: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    use_timer: bool = False,
    profile: bool = False,
    verbose: bool = False,
) -> Union[None, pd.DataFrame]:
    """
    Execute a query.
    """
    if limit is not None:
        query += " LIMIT %s" % limit
    if offset is not None:
        query += " OFFSET %s" % offset
    if profile:
        query = "EXPLAIN ANALYZE " + query
    if verbose:
        print(("> " + query))
    # Compute.
    if use_timer:
        idx = htimer.dtimer_start(0, "Sql time")
    df = None
    cursor = connection.cursor()
    try:
        df = pd.read_sql_query(query, connection)
    except psycop.OperationalError:
        # Catch error and execute query directly to print error.
        try:
            cursor.execute(query)
        except psycop.Error as e:
            print(e.pgerror)
            raise psycop.Error
    if use_timer:
        htimer.dtimer_stop(idx)
    if profile:
        print(df)
        return None
    return df


# #############################################################################
# Insert
# #############################################################################


def copy_rows_with_copy_from(
    connection: DbConnection, df: pd.DataFrame, table_name: str
) -> None:
    """
    Copy dataframe contents into DB directly from buffer.

    This function works much faster for large dataframes (>10000 rows).

    :param connection: DB connection
    :param df: data to insert
    :param table_name: name of the table for insertion
    """
    # The target table needs to exist.
    hdbg.dassert_in(table_name, get_table_names(connection))
    # Read the data.
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    # Copy the data to the DB.
    cur = connection.cursor()
    cur.copy_from(buffer, table_name, sep=",")
    # TODO(gp): CmampTask413, is this still needed because the autocommit.
    connection.commit()


def _create_insert_query(df: pd.DataFrame, table_name: str) -> str:
    """
    Create an INSERT query to insert data into a DB.

    :param df: data to insert into DB
    :param table_name: name of the table for insertion
    :return: sql query, e.g.,
        ```
        INSERT INTO ccxt_ohlcv(timestamp,open,high,low,close) VALUES %s
        ```
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    columns = ",".join(list(df.columns))
    query = f"INSERT INTO {table_name}({columns}) VALUES %s"
    _LOG.debug("query=%s", query)
    return query


def execute_insert_query(
    connection: DbConnection, obj: Union[pd.DataFrame, pd.Series], table_name: str
) -> None:
    """
    Insert a DB as multiple rows into the database.

    :param connection: connection to the DB
    :param obj: data to insert
    :param table_name: name of the table for insertion
    """
    if isinstance(obj, pd.Series):
        df = obj.to_frame().T
    else:
        df = obj
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_in(table_name, get_table_names(connection))
    _LOG.debug("df=\n%s", hprint.dataframe_to_str(df))
    # Transform dataframe into list of tuples.
    values = [tuple(v) for v in df.to_numpy()]
    # Generate a query for multiple rows.
    query = _create_insert_query(df, table_name)
    # Execute query for each provided row.
    cur = connection.cursor()
    extras.execute_values(cur, query, values)
    connection.commit()
