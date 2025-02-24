"""
Import as:

import helpers.hsql_implementation as hsqlimpl
"""

import collections
import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras
import psycopg2.sql as psql

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsecrets as hsecret
import helpers.htimer as htimer

_LOG = logging.getLogger(__name__)

# #############################################################################
# Connection
# #############################################################################

DbConnection = Any

# Invariant: keep the arguments in the interface in the same order as:
# host, dbname, port, user, password.
DbConnectionInfo = collections.namedtuple(
    "DbConnectionInfo", ["host", "dbname", "port", "user", "password"]
)


def get_connection(
    host: str,
    dbname: str,
    port: int,
    user: str,
    password: str,
    autocommit: bool = True,
) -> DbConnection:
    """
    Create a connection and cursor for a SQL database.
    """
    _LOG.debug(hprint.to_str("host dbname port user"))
    connection = psycop.connect(
        host=host, dbname=dbname, port=port, user=user, password=password
    )
    if autocommit:
        connection.autocommit = True
    return connection


def get_connection_from_aws_secret(
    *,
    stage: str = "prod",
) -> DbConnection:
    """
    Create an SQL connection using credentials obtained from AWS
    SecretsManager.

    The function uses `ck` AWS profile on the backend.
    The intended usage is obtaining connection to a DB on RDS instances.

    :param stage: DB stage to connect to. For "prod" stage it is only possible to obtain a read-only connection via this method.
    """
    hdbg.dassert_in(stage, ["prod", "preprod", "test"])
    dbname = f"{stage}.im_data_db"
    if stage == "prod":
        secret_name = f"{dbname}.read_only"
    else:
        secret_name = dbname
    _LOG.info("Fetching secret: %s", secret_name)
    db_creds = hsecret.get_secret(secret_name)
    connection = get_connection(
        host=db_creds["host"],
        dbname=dbname,
        port=db_creds["port"],
        user=db_creds["username"],
        password=db_creds["password"],
    )
    return connection


def get_connection_from_env_vars() -> DbConnection:
    """
    Create a SQL connection with the information from the environment
    variables.
    """
    # Get values from the environment variables.
    host = os.environ["POSTGRES_HOST"]
    dbname = os.environ["POSTGRES_DB"]
    port = int(os.environ["POSTGRES_PORT"])
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    # Build the
    connection = get_connection(
        host=host,
        dbname=dbname,
        port=port,
        user=user,
        password=password,
    )
    return connection


def get_connection_from_string(
    conn_as_str: str,
    autocommit: bool = True,
) -> DbConnection:
    """
    Create a connection from a string.

    E.g., `host=localhost dbname=im_db_local port=5432 user=...
    password=...`
    """
    regex = r"host=\w+ dbname=\w+ port=\d+ user=\w+ password=\w+"
    m = re.match(regex, conn_as_str)
    hdbg.dassert(m, "Invalid connection string: '%s'", conn_as_str)
    connection = psycop.connect(conn_as_str)
    if autocommit:
        connection.autocommit = True
    return connection


def get_connection_info_from_env_file(env_file_path: str) -> DbConnectionInfo:
    """
    Get connection parameters from environment file.

    :param env_file_path: path to an environment file that contains db connection
        parameters
    """
    import dotenv

    db_config = dotenv.dotenv_values(env_file_path)
    params = {
        "host": db_config["POSTGRES_HOST"],
        "dbname": db_config["POSTGRES_DB"],
        "user": db_config["POSTGRES_USER"],
        "password": db_config["POSTGRES_PASSWORD"],
    }
    key = "POSTGRES_PORT"
    if key in db_config:
        params["port"] = int(db_config[key])
    else:
        params["port"] = 5432
    # The parameters' names are fixed and cannot be changed, see
    # `https:://hub.docker.com/_/postgres`.
    connection_parameters = DbConnectionInfo(**params)
    return connection_parameters


def check_db_connection(
    host: str,
    dbname: str,
    port: int,
    user: str,
    password: str,
) -> Tuple[bool, Optional[psycop.OperationalError]]:
    """
    Check whether a connection to a DB exists, in a non-blocking way.
    """
    try:
        get_connection(
            host=host, dbname=dbname, port=port, user=user, password=password
        )
        connection_exist = True
        error = None
    except psycop.OperationalError as e:
        connection_exist = False
        error = e
    return connection_exist, error


def wait_db_connection(
    host: str,
    dbname: str,
    port: int,
    user: str,
    password: str,
    *,
    timeout_in_secs: int = 30,
) -> None:
    """
    Wait until the database is available.

    :param timeout_in_secs: secs before timing out with `RuntimeError`.
    """
    hdbg.dassert_lte(1, timeout_in_secs)
    _LOG.debug("dbname=%s, port=%s, host=%s", dbname, port, host)
    elapsed_secs = 0
    while True:
        _LOG.info("Waiting for PostgreSQL to become available...")
        conn_exists = check_db_connection(host, dbname, port, user, password)
        if conn_exists[0]:
            _LOG.info("PostgreSQL is available (after %s seconds)", elapsed_secs)
            break
        if elapsed_secs > timeout_in_secs:
            raise psycop.OperationalError(
                f"Cannot connect to db host={host} dbname={dbname} port={port} "
                f"due to timeout={timeout_in_secs} seconds"
                f"\n{conn_exists[1]}"
            )
        elapsed_secs += 1
        time.sleep(1)


def db_connection_to_tuple(connection: DbConnection) -> DbConnectionInfo:
    """
    Get database connection details using connection. Connection details
    include:

        - Host
        - Database name
        - Port
        - Username
        - Password

    :param connection: a database connection
    :return: database connection details
    """
    info = connection.info
    ret = DbConnectionInfo(
        host=info.host,
        dbname=info.dbname,
        port=info.port,
        user=info.user,
        password=info.password,
    )
    return ret


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
        query = f"""SELECT * FROM pg_indexes WHERE tablename = '{table}' """
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


def disconnect_all_clients(connection: DbConnection) -> None:
    # From https://stackoverflow.com/questions/36502401
    # Not sure this will work in our case, since it might kill our own connection.
    dbname = connection.info.host
    query = f"""
        SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{dbname}';"""
    connection.cursor().execute(query)


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
    *,
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


def get_tables_size(
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
    query = f"SELECT * FROM {table} LIMIT {limit} "
    df = execute_query_to_df(connection, query)
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


def get_table_columns(connection: DbConnection, table_name: str) -> List[str]:
    """
    Get column names for given table.
    """
    query = f"""
        SELECT column_name
            FROM information_schema.columns
            WHERE TABLE_NAME = '{table_name}'"""
    cursor = connection.cursor()
    cursor.execute(query)
    columns = [x[0] for x in cursor.fetchall()]
    return columns


def find_tables_common_columns(
    connection: DbConnection,
    tables: List[str],
    as_df: bool = False,
) -> Union[None, pd.DataFrame]:
    limit = 5
    df = []
    for i, table in enumerate(tables):
        table = tables[i]
        query = f"SELECT * FROM {table} LIMIT {limit} "
        df1 = execute_query_to_df(connection, query, verbose=False)
        if df1 is None:
            continue
        for j in range(i + 1, len(tables)):
            table = tables[j]
            query = f"SELECT * FROM {table} LIMIT {limit} "
            df2 = execute_query_to_df(connection, query, verbose=False)
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
                print(f"'{tables[i]}' vs '{tables[j]}'")
                print(f"    ({len(common_cols)}): {' '.join(common_cols)}")
    obj = None
    if as_df:
        obj = pd.DataFrame(
            df, columns=["table1", "table2", "num_comm_cols", "common_cols"]
        )
    return obj


def remove_table(
    connection: DbConnection, table_name: str, cascade: bool = False
) -> None:
    """
    Remove a table from a database.

    :param connection: database connection
    :param table_name: table name
    :param cascade: whether to drop the objects dependent on the table
    """
    query = f"DROP TABLE IF EXISTS {table_name}"
    if cascade:
        query = " ".join([query, "CASCADE"])
    connection.cursor().execute(query)


def remove_all_tables(connection: DbConnection, cascade: bool = False) -> None:
    """
    Remove all the tables from a database.

    :param connection: database connection
    :param cascade: whether to drop the objects dependent on the tables
    """
    table_names = get_table_names(connection)
    _LOG.warning("Deleting all the tables: %s", table_names)
    for table_name in table_names:
        _LOG.warning("Deleting %s ...", table_name)
        remove_table(connection, table_name, cascade)


# #############################################################################
# Query
# #############################################################################


# TODO(gp): -> as_df
def execute_query_to_df(
    connection: DbConnection,
    query: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    use_timer: bool = False,
    profile: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Execute a query.
    """
    if False:
        # Ask the user before executing a query.
        print(f"query=\n{query}")
        import helpers.hsystem as hsystem

        hsystem.query_yes_no("Ok to execute?")
    if limit is not None:
        query += f" LIMIT {limit}"
    if offset is not None:
        query += f" OFFSET {offset}"
    if profile:
        query = "EXPLAIN ANALYZE " + query
    if verbose:
        _LOG.info("> %s", query)
    # Compute.
    if use_timer:
        idx = htimer.dtimer_start(0, "Sql time")
    cursor = connection.cursor()
    try:
        df = pd.read_sql_query(query, connection)
    except psycop.OperationalError:
        # Catch error and execute query directly to print error.
        try:
            cursor.execute(query)
        except psycop.Error as e:
            print(e.pgerror)
            raise e
    if use_timer:
        htimer.dtimer_stop(idx)
    if profile:
        _LOG.info("df=%s", df)
    return df


# #############################################################################
# Insert
# #############################################################################


def csv_to_series(csv_as_txt: str, sep: str = ",") -> pd.Series:
    """
    Convert a text with (key, value) separated by `sep` into a `pd.Series`.

    :param csv_as_txt: a string containing csv data
        E.g.,
        ```
        tradedate,2021-11-12
        targetlistid,1
        ```
    :param sep: csv separator, e.g. `,`
    :return: series
    """
    lines = hprint.dedent(csv_as_txt).split("\n")
    tuples = [tuple(line.split(sep)) for line in lines]
    # Remove empty tuples.
    tuples = [t for t in tuples if t[0] != ""]
    # Build series.
    index, data = zip(*tuples)
    # _LOG.debug("index=%s", index)
    # _LOG.debug("data=%s", data)
    srs = pd.Series(data, index=index)
    return srs


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


# TODO(gp): -> table_name, df
def create_insert_query(df: pd.DataFrame, table_name: str) -> str:
    """
    Create an INSERT query to insert data into a DB.

    :param df: data to insert into DB
    :param table_name: name of the table for insertion
    :return: sql query, e.g.,
        ```
        INSERT INTO ccxt_ohlcv_spot(timestamp,open,high,low,close) VALUES %s
        ```
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    columns = ",".join(list(df.columns))
    query = f"INSERT INTO {table_name}({columns}) VALUES %s"
    _LOG.debug("query=%s", query)
    return query


# TODO(gp): -> table_name, df
def create_insert_on_conflict_do_nothing_query(
    df: pd.DataFrame, table_name: str, unique_columns: List[str]
) -> str:
    """
    Create an INSERT query to insert data into a DB. If a unique constraint is
    violated for a provided set of columns, duplicates are not inserted.

    :param df: data to insert into DB
    :param table_name: name of the table for insertion
    :param unique_columns: set of columns which should be unique record-wise.
    :return: sql query, e.g.,
        ```
        INSERT INTO ccxt_bid_ask(timestamp,bid_size,bid_price,ask_size,
        ask_price,exchange_id,currency_pair) VALUES %s
        ON CONFLICT (timestamp, exchange_id, currency_pair) DO NOTHING;
        ```
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Check that the constraint is actually applied to columns
    # of the DataFrame.
    hdbg.dassert_is_subset(unique_columns, list(df.columns))
    columns = ",".join(list(df.columns))
    unique_columns_str = ",".join(unique_columns)
    query = f"INSERT INTO {table_name}({columns}) VALUES %s ON CONFLICT ({unique_columns_str}) \
            DO NOTHING"
    _LOG.debug("query=%s", query)
    return query


# TODO(gp): -> connection, table_name, obj
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
    _LOG.debug("df=\n%s", hpandas.df_to_str(df, use_tabulate=False))
    # Transform dataframe into list of tuples.
    values = [tuple(v) for v in df.to_numpy()]
    # Generate a query for multiple rows.
    query = create_insert_query(df, table_name)
    # Execute query for each provided row.
    cur = connection.cursor()
    extras.execute_values(cur, query, values)
    connection.commit()


# TODO(gp): -> connection, table_name, obj
def execute_insert_on_conflict_do_nothing_query(
    connection: DbConnection,
    obj: Union[pd.DataFrame, pd.Series],
    table_name: str,
    unique_columns: List[str],
) -> None:
    """
    Insert a DB as multiple rows into the database. If a a UNIQUE constraint is
    violated for a provided set of columns, duplicates are not inserted.

    :param connection: connection to the DB
    :param obj: data to insert
    :param table_name: name of the table for insertion
    :param unique_columns: set of columns which should be unique record-wise.
       If unique_columns is an empty list, a regular DB insert is executed
       without the UNIQUE constraint.
    """
    if isinstance(obj, pd.Series):
        df = obj.to_frame().T
    else:
        df = obj
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_in(table_name, get_table_names(connection))
    _LOG.debug("df=\n%s", hpandas.df_to_str(df, use_tabulate=False))
    # Transform dataframe into list of tuples.
    values = [tuple(v) for v in df.to_numpy()]
    # Generate a query for multiple rows.
    if not unique_columns:
        # If unique_columns is an empty list, currently used when saving
        # bid/ask RT data, to experiment with using no uniqueness constraints.
        query = create_insert_query(df, table_name)
    else:
        query = create_insert_on_conflict_do_nothing_query(
            df, table_name, unique_columns
        )
    # Execute query for each provided row.
    cur = connection.cursor()
    try:
        extras.execute_values(cur, query, values)
        connection.commit()
    except Exception as e:
        _LOG.error(
            "Failed to insert data with the '%s'. Query %s. Values: %s",
            str(e),
            query,
            values,
        )
        raise e


def execute_query(connection: DbConnection, query: str) -> List[tuple]:
    """
    Use for generic simple operations.

    :param connection: connection to the DB
    :param query: generic query that can be: insert, update, delete, etc.
    :return: list of tuples with the results of the query
    """
    _LOG.debug(hprint.to_str("query"))
    with connection.cursor() as cursor:
        cursor.execute(query)
        if not connection.autocommit:
            connection.commit()
        try:
            result = cursor.fetchall()
        except psycop.ProgrammingError:
            result = [()]
        return result


# #############################################################################
# Build more complex SQL queries.
# #############################################################################


# Invariants for functions with SQL queries
#
# - Functions creating tables
#   - accept a parameter `incremental that has the same behavior as in
#   `hio.create_dir(..., incremental)`
#   - It controls the behavior of this function if the target table already exists.
#     If `incremental` is True, then skip creating it and reuse it as it is; if
#     False delete it and create it from scratch.
#
# - Function creating / execution SQL queries
#   - We prefer functions that directly perform SQL queries implementing a given
#     functionality (e.g., `get_num_rows()`)
#   - Use `get_..._query()` returning the query text only when we want to freeze
#     the query in a test, e.g., because it is complex


def get_remove_duplicates_query(
    table_name: str, id_col_name: str, column_names: List[str]
) -> str:
    """
    Get a query to remove duplicates from table, keeping last duplicated row.

    :param table_name: name of table
    :param id_col_name: name of unique id column
    :param column_names: names of columns to compare on
    :return: query to execute duplicate removal
    """
    # TODO(*): Add a "limit" parameter if possible, to check only in top N rows.
    remove_statement = []
    remove_statement.append(f"DELETE FROM {table_name} a USING {table_name} b")
    remove_statement.append(f"WHERE a.{id_col_name} < b.{id_col_name}")
    for c in column_names:
        remove_statement.append(f"AND a.{c} = b.{c}")
    remove_statement = " ".join(remove_statement)
    return remove_statement


def get_num_rows(connection: DbConnection, table_name: str) -> int:
    """
    Return the number of rows in a DB table.
    """
    cursor = connection.cursor()
    query = f"SELECT COUNT(*) FROM {table_name}"
    cursor.execute(query)
    vals = cursor.fetchall()
    # The return value is like: vals=[(0,)]
    hdbg.dassert_eq(len(vals), 1)
    return vals[0][0]  # type: ignore[no-any-return]


# #############################################################################
# Polling functions
# #############################################################################


def is_row_with_value_present(
    connection: DbConnection,
    table_name: str,
    field_name: str,
    target_value: str,
    *,
    show_db_state: bool = True,
) -> hasynci.PollOutput:
    """
    Check with a polling function if a row with `field_name` == `target_value`
    is present in the table `table_name` of the DB.

    E.g., this can be used with polling to wait for the target value
    "hello_world.txt" in the "filename" field of the table "table_name" to appear

    :return:
        - success if the value is present
        - result: None
    """
    _LOG.debug(hprint.to_str("connection table_name field_name target_value"))
    # Print the state of the DB, if needed.
    if show_db_state:
        query = f"SELECT * FROM {table_name} ORDER BY filename"
        df = execute_query_to_df(connection, query)
        _LOG.debug("df=\n%s", hpandas.df_to_str(df, use_tabulate=False))
    # Check if the required row is available.
    query = f"SELECT {field_name} FROM {table_name} WHERE {field_name}='{target_value}'"
    df = execute_query_to_df(connection, query)
    _LOG.debug("df=\n%s", hpandas.df_to_str(df, use_tabulate=False))
    # Package results.
    success = df.shape[0] > 0
    result = None
    return success, result


# TODO(gp): Add unit test.
async def wait_for_change_in_number_of_rows(
    get_wall_clock_time: hdateti.GetWallClockTime,
    db_connection: DbConnection,
    table_name: str,
    poll_kwargs: Dict[str, Any],
    *,
    tag: Optional[str] = None,
) -> int:
    """
    Wait until the number of rows in a table changes.

    :param get_wall_clock_time: a function to get current time
    :param db_connection: connection to the target DB
    :param table_name: name of the table to poll
    :param poll_kwargs: a dictionary with the kwargs for `poll()`
    :param tag: name of the caller function
    :return: number of new rows found
    """
    num_rows = get_num_rows(db_connection, table_name)

    def _is_number_of_rows_changed() -> hasynci.PollOutput:
        new_num_rows = get_num_rows(db_connection, table_name)
        _LOG.debug("new_num_rows=%s num_rows=%s", new_num_rows, num_rows)
        success = new_num_rows != num_rows
        diff_num_rows = new_num_rows - num_rows
        return success, diff_num_rows

    # Poll.
    if tag is None:
        # Use name of the caller function.
        tag = hintros.get_function_name(count=0)
    if poll_kwargs is None:
        poll_kwargs = hasynci.get_poll_kwargs(get_wall_clock_time)
    num_iters, diff_num_rows = await hasynci.poll(
        _is_number_of_rows_changed,
        tag=tag,
        **poll_kwargs,
    )
    _ = num_iters
    diff_num_rows = cast(int, diff_num_rows)
    return diff_num_rows
