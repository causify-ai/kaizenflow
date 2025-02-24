"""
Implementation of load part of the ETL and QA pipeline.

Import as:
Import google_trends.src.db as sisebidb
"""

from typing import Any, Optional

import common.client as sinsacli
import common.save as sinsasav
import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras


def get_google_trends_create_table_query() -> str:
    """
    Get SQL query to create the google_trends_data table.
    This table contains the data as it is downloaded from the API after it is processed.
    """
    query = """
                    CREATE TABLE IF NOT EXISTS google_trends_data
                    (
                        topic VARCHAR(225),
                        date_stamp varchar(225),
                        frequency NUMERIC
                    );
            """
    return query


def get_google_trends_predictions_create_table_query() -> str:
    query = """
                    CREATE TABLE IF NOT EXISTS google_trends_predictions
                    (
                        topic VARCHAR(225), 
                        date_stamp DATE, 
                        record_type VARCHAR(225),
                        frequency NUMERIC
                    );
            """

    return query


def get_db_connection() -> Any:
    """
    Retrieve connection to the Postgres DB.
    """

    connection = psycop.connect(
        host="postgres_db",
        dbname="google_trends",
        port=5432,
        user="postgres",
        password="postgres",
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

        :param db_connection: DB connection
        """
        self.db_connection = db_connection
        self._create_tables()

    def save(self, data: pd.DataFrame, db_table: str, topic: str) -> None:
        """
        Save a DataFrame to a specified DB table.

        :param data: data to persists into DB
        """

        # Transform dataframe into list of tuples.
        values = [tuple(v) for v in data.to_numpy()]

        cursor = self.db_connection.cursor()

        # delete records code
        query = self._create_delete_query(db_table, topic)
        cursor.execute(query)

        # Generate a query for multiple rows.
        query = self._create_insert_query(db_table)

        # insert values into table
        extras.execute_values(cursor, query, values)
        self.db_connection.commit()

    @staticmethod
    def _create_insert_query(db_table: str) -> str:
        """
        Create an INSERT query to insert data into a DB.

        :param db_table: name of the table for insertion
        :return: SQL query, e.g.,
            ```
            INSERT INTO google_ternds_data VALUES %s
            ```
        """
        query = f"INSERT INTO {db_table} VALUES %s"
        return query

    @staticmethod
    def _create_delete_query(table: str, topic: str) -> str:
        query ="DELETE FROM "+table+" WHERE topic = '" + topic + "'"
        # print(query)
        return query

    def _create_tables(self) -> None:
        """
        Create DB data tables to store data.
        """
        cursor = self.db_connection.cursor()

        query = get_google_trends_create_table_query()
        cursor.execute(query)

        query = get_google_trends_predictions_create_table_query()
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

        :param db_connection: DB connection
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
        topic = kwargs.get("topic")
        select_query = f"SELECT * FROM " + dataset_signature + " where topic = " + "'" + topic + "'"
        # Read data.
        data = pd.read_sql_query(select_query, self.db_conn)
        return data
