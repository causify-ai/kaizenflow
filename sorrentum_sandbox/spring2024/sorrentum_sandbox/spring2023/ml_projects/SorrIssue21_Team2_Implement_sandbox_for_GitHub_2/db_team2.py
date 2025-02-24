#!/usr/bin/env python3
"""
Implementation of load part of the ETL and QA pipeline.

Import as:

import sorrentum_sandbox.projects.Issue21_Team2_Implement_sandbox_for_github.db as sisebidb
"""

from typing import Any, Optional

import pandas as pd
import psycopg2 as psycop
import psycopg2.extras as extras

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import sorrentum_sandbox.common.client as ssacocli
import sorrentum_sandbox.common.download as ssacodow
import sorrentum_sandbox.common.save as ssacosav

# create three tables that we want to save in database
def get_github_create_main_table_query() -> str:
    """
    Get SQL query to create github_main table.

    This table contains the data as it is downloaded.
    """
    query = """
    CREATE TABLE IF NOT EXISTS github_main(
             id NUMERIC,
             created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP,
            pushed_at TIMESTAMP,
            size NUMERIC,
            stargazers_count NUMERIC,
            watchers_count NUMERIC,
            forks_count NUMERIC,
            open_issues_count NUMERIC,
            watchers  NUMERIC,
            network_count NUMERIC,
            subscribers_count NUMERIC,
            owner_id NUMERIC,
            organization_id NUMERIC,
            Crypto VARCHAR(255) NOT NULL,
            inserted_at TIMESTAMP
            )
            """
    return query


def get_github_create_issues_table_query() -> str:
    """
    Get SQL query to create github_issues table.

    This table contains the data as it is downloaded.
    """
    query = """
         CREATE TABLE IF NOT EXISTS github_issues(
            id SERIAL PRIMARY KEY,
            number NUMERIC,
            title VARCHAR(500) NOT NULL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            closed_at TIMESTAMP,
            author_association VARCHAR(255),
            comments NUMERIC,
            body VARCHAR(50000) ,
            user_login VARCHAR(255) NOT NULL,
            user_id NUMERIC,
            Crypto_Name VARCHAR(255) NOT NULL,
            Extension VARCHAR(255) NOT NULL
            )

            """
    return query


def get_github_create_commits_table_query() -> str:
    """
    Get SQL query to create github_commits table.

    This table contains the data as it is downloaded.
    """
    query = """
    CREATE TABLE IF NOT EXISTS  github_commits(
          total NUMERIC,
          week NUMERIC,
          days VARCHAR(255) NOT NULL,
          Crypto_Name VARCHAR(255) NOT NULL,
          Extension VARCHAR(255) NOT NULL,
          Sun NUMERIC,
          Mon NUMERIC,
          Tue NUMERIC,
          Wed NUMERIC,
          Thur NUMERIC,
          Fri NUMERIC,
          Sat NUMERIC
            )
            """
    return query

 
def get_github_create_analysis_table_query() -> str:
    """
    Get SQL query to create github_commits table. 
       
    This table contains the data as it is downloaded.
    """
    query = """CREATE TABLE IF NOT EXISTS  github_analysis(
    Crypto VARCHAR(255) NOT NULL,
    Datatable VARCHAR(255) NOT NULL,
    Column_Type VARCHAR(255) NOT NULL,
    Column_Name VARCHAR(255) NOT NULL,
          total_count NUMERIC,
          unique_count NUMERIC,
          null_count NUMERIC,
          null_Percent NUMERIC, 
          levels VARCHAR(255) NOT NULL,
          value_count NUMERIC,
          counts_Percent NUMERIC,
          mean NUMERIC,
          std NUMERIC,
          min NUMERIC,
          max NUMERIC,
          Analysed_On TIMESTAMP
          )
            """
    return query




def get_db_connection() -> Any:
    """
    Retrieve connection to the Postgres DB inside the Sorrentum data node.

    The parameters must match the parameters set up in the Sorrentum
    data node docker-compose.
    """
    connection = psycop.connect(
        host="host.docker.internal",
        dbname="airflow",
        port=5532,
        user="postgres",
        password="postgres",
    )
    connection.autocommit = True
    return connection


# #############################################################################
# PostgresDataFrameSaver
# #############################################################################


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
        :return: SQL query
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

        query = get_github_create_main_table_query()
        cursor.execute(query)

        query = get_github_create_issues_table_query()
        cursor.execute(query)

        query = get_github_create_commits_table_query()
        cursor.execute(query)
        
        query = get_github_create_analysis_table_query()
        cursor.execute(query)
# #############################################################################
# PostgresClient
# #############################################################################


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
            select_query += f" WHERE timestamp >= {start_timestamp}"
        if end_timestamp:
            hdateti.dassert_has_tz(end_timestamp)
            if start_timestamp:
                select_query += " AND "
            else:
                select_query += " WHERE "
            select_query += f" timestamp < {end_timestamp}"
        # Read data.
        data = pd.read_sql_query(select_query, self.db_conn)
        return data