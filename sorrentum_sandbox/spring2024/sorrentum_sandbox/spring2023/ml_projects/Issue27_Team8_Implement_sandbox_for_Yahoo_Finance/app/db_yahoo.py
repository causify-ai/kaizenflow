from typing import Any, Optional

import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import common.client as sinsacli
import common.download as sinsadow
import common.save as sinsasav


def get_yfinance_spot_downloaded_1min_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_1min(


            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_5min_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_5min(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_2min_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_2min(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_15min_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_15min(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_30min_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_30min(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_1hr_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_1hr(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_yfinance_spot_downloaded_1d_create_table_query() -> str:
    """
    Get SQL query to create yahoo yfinance table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS yahoo_yfinance_spot_downloaded_1d(
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            adj_close NUMERIC,
            volume NUMERIC,
            timestamp TIMESTAMP WITH TIME ZONE,
            currency_pair VARCHAR(255) NOT NULL,
            exchangeTimezoneName VARCHAR(255) NOT NULL,
            timezone VARCHAR(255) NOT NULL
            )
            """
    return query


def get_dask_db() -> str:
    """
    Get SQL query to create db for features computed using dask.
    """
    query = """
    CREATE TABLE IF NOT EXISTS dask_dataframe_1min_average_300sec_check3(
            currency_pair VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE,
            average_last_300_seconds_open NUMERIC
            )
            """
    return query

def get_db_connection() -> Any:
    """
    Retrieve connection based on hardcoded values.

    The parameters must match the parameters used for setting up Postgres container
    """
    connection = psycop.connect(
        host="host.docker.internal",
        dbname="postgres",
        port=5432,
        user="postgres",
        password="docker",
    )
    connection.autocommit = True
    return connection


# #############################################################################
# PostgresDataFrameSaver
# #############################################################################


class PostgresDataFrameSaver(sinsasav.DataSaver):
    """
    Save Pandas DataFrame to a PostgreSQL using a provided DB connection.
    """

    def __init__(self, db_connection: str) -> None:
        """
        Constructor.

        :param db_conn: DB connection
        """
        self.db_conn = db_connection
        self._create_tables()

    def save(
        self, data: sinsadow.RawData, db_table: str, *args: Any, **kwargs: Any
    ) -> None:
        """
        Save RawData storing a DataFrame to a specified DB table.

        :param data: data to persists into DB
        :param db_table: table to save data to
        """
        hdbg.dassert_isinstance(
            data.get_data(), pd.DataFrame, "Only DataFrame is supported."
        )
        # Transform dataframe into list of tuples.
        df = data.get_data()
        values = [tuple(v) for v in df.to_numpy()]
        # Generate a query for multiple rows.
        query = self._create_insert_query(df, db_table)
        # Execute query for each provided row.
        cursor = self.db_conn.cursor()
        extras.execute_values(cursor, query, values)
        self.db_conn.commit()

    @staticmethod
    def _create_insert_query(df: pd.DataFrame, db_table: str) -> str:
        """
        Create an INSERT query to insert data into a DB.

        :param df: data to insert into DB
        :param table_name: name of the table for insertion
        :return: SQL query, e.g.
        """

        columns = ",".join(list(df.columns))
        query = f"INSERT INTO {db_table}({columns}) VALUES %s"
        return query

    def _create_tables(self) -> None:
        """
        Create DB data tables to store data.

        Note that typically table creation would not be handled in the same place
        as downloading the data, but as an example this suffices.
        """
        cursor = self.db_conn.cursor()
        #
        query = get_yfinance_spot_downloaded_1min_create_table_query()
        cursor.execute(query)
        #
        query = get_yfinance_spot_downloaded_5min_create_table_query()
        cursor.execute(query)

        query = get_yfinance_spot_downloaded_2min_create_table_query()
        cursor.execute(query)

        query = get_yfinance_spot_downloaded_15min_create_table_query()
        cursor.execute(query)

        query = get_yfinance_spot_downloaded_30min_create_table_query()
        cursor.execute(query)

        query = get_yfinance_spot_downloaded_1hr_create_table_query()
        cursor.execute(query)

        query = get_yfinance_spot_downloaded_1d_create_table_query()
        cursor.execute(query)

        query = get_dask_db()
        cursor.execute(query)

# #############################################################################
# PostgresClient
# #############################################################################


class PostgresClient(sinsacli.DataClient):
    """
    Load PostgreSQL data.
    """

    def __init__(self, db_connection: str) -> None:
        """
        Constructor.

        :param db_conn: DB connection
        """
        self.db_conn = db_connection

    def load(
        self,
        dataset_signature: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Load CSV data specified by a unique signature from a desired source
        directory for a specified time period.

        The method assumes data having a `timestamp` column.
        """
        select_query = f"SELECT * FROM {dataset_signature}"
        # Filter data.
        if start_timestamp:
            hdateti.dassert_has_tz(start_timestamp)
            start_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
                start_timestamp
            )
            select_query += f" WHERE timestamp >= {start_timestamp_as_unix}"
        if end_timestamp:
            hdateti.dassert_has_tz(end_timestamp)
            end_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
                end_timestamp
            )
            if start_timestamp:
                select_query += " AND "
            else:
                select_query += " WHERE "
            select_query += f" timestamp < {end_timestamp_as_unix}"
        # Read data.
        data = pd.read_sql_query(select_query, self.db_conn)
        return data


print(1)
