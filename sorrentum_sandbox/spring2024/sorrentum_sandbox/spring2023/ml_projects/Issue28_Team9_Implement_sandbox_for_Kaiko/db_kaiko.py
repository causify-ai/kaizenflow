"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue28_Team9_Implement_sandbox_for_Kaiko.db_kaiko as ssempitisfkdk
"""

from typing import Any, Optional

import common.client as sinsacli
import common.download as sinsadow
import common.save as sinsasav
import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg


def get_ohlcv_spot_downloaded_1min_create_table_query() -> str:
    """
    Get SQL query to create Binance OHLCV table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS binance_ohlcv_spot_downloaded_1min(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE default CURRENT_TIMESTAMP,
            UNIQUE(timestamp, currency_pair)
            )
            """
    return query


def get_ohlcv_spot_resampled_5min_create_table_query() -> str:
    """
    Get SQL query to create Binance OHLCV resampled model table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS binance_ohlcv_spot_resampled_5min(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE default CURRENT_TIMESTAMP,
            UNIQUE(timestamp, currency_pair)
            )
            """
    return query


def get_db_connection() -> Any:

    try:
        connection = psycop.connect(
            host="host.docker.internal",
            dbname="kaiko",
            port=5432,

            user="postgres",
            password="postgres",
        )
    except Exception:
        connection = psycop.connect(
            host="localhost",

            dbname="kaiko",
            port=5432,
            user="postgres",
            password="postgres",
        )

    connection.autocommit = True
    return connection


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

        columns = ",".join(list(df.columns))
        query = f"INSERT INTO {db_table}({columns}) VALUES %s"
        return query

    def _create_tables(self) -> None:

        cursor = self.db_conn.cursor()
        #
        query = get_ohlcv_spot_downloaded_1min_create_table_query()
        cursor.execute(query)
        #
        query = get_ohlcv_spot_resampled_5min_create_table_query()
        cursor.execute(query)


class PostgresClient(sinsacli.DataClient):
    def __init__(self, db_connection: str) -> None:

        self.db_conn = db_connection

    def load(
        self,
        dataset_signature: str,
        *,
        start_timestamp: Optional[pd.Timestamp] = None,
        end_timestamp: Optional[pd.Timestamp] = None,
        **kwargs: Any,
    ) -> Any:

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
