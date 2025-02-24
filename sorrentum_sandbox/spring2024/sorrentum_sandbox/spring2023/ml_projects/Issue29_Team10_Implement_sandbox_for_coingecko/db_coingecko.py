"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue29_Team10_Implement_sandbox_for_coingecko.db_coingecko as ssempitisfcdc
"""

import json
from typing import Any, Optional
import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras
import requests
from pycoingecko import CoinGeckoAPI

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import sorrentum_sandbox.common.client as ssacocli
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.save as ssacosav

def get_db_connection() -> Any:
    """
    Retrieve connection to the Postgres DB inside the Sorrentum data node.
    The parameters must match the parameters set up in the Sorrentum
    data node docker-compose.
    """
    
    db_connection = psycop.connect(
        host="host.docker.internal",
        dbname="airflow",
        port=5532,
        user="postgres",
        password="postgres",
    )
    db_connection.autocommit = True

    return db_connection

def get_coingecko_historic_table_query() -> str:
    """
    Get SQL query to create coingecko table.
    """

    query = """
                CREATE TABLE IF NOT EXISTS coingecko_historic
                (
                    id VARCHAR,
                    timestamp BIGINT,
                    price NUMERIC,
                    market_cap NUMERIC,
                    total_volume NUMERIC
                );
            """
    return query

def get_coingecko_realtime_table_query() -> str:
    """
    Get SQL query to create coingecko table.
    """

    query = """
                CREATE TABLE IF NOT EXISTS coingecko_rt
                (
                    timestamp BIGINT,
                    price NUMERIC,
                    market_cap NUMERIC,
                    total_volume NUMERIC
                );
            """
    return query

def get_coingecko_drop_query() -> str:
    """
    Get SQL query to drop coingecko table.
    """
    query = "drop table coingecko_data"

    return query


# def get_coingecko_table_fetch_query(id) -> str:

#     query = ""
#     query = query + "SELECT * FROM coingecko_data WHERE id = %s"

#     return query


class PostgresDataFrameSaver(ssacosav.DataSaver):
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
        self, data: ssacodow.RawData, db_table: str, *args: Any, **kwargs: Any
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
        :return: SQL query, e.g.,
            ```
            INSERT INTO coingecko_data (timestamp, price, market_cap, total_volume) VALUES %s
            ```
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
        query = get_coingecko_historic_table_query()
        cursor.execute(query)
        #
        query = get_coingecko_realtime_table_query()
        cursor.execute(query)

# # #############################################################################
# # PostgresClient
# # #############################################################################


class PostgresClient(ssacocli.DataClient):
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
        from_timestamp: Optional[pd.Timestamp] = None,
        to_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Load CSV data specified by a unique signature from a desired source
        directory for a specified time period.
        """
        select_query = f"SELECT id, timestamp, price, market_cap, total_volume FROM {dataset_signature}"
        # Filter data.
        if from_timestamp:
            hdateti.dassert_has_tz(from_timestamp)
            select_query += f" WHERE timestamp >= {from_timestamp}"
        if to_timestamp:
            hdateti.dassert_has_tz(to_timestamp)
            if from_timestamp:
                select_query += " AND "
            else:
                select_query += " WHERE "
            select_query += f" timestamp < {to_timestamp}"
        # Read data.
        data = pd.read_sql_query(select_query, self.db_conn)
        return data
