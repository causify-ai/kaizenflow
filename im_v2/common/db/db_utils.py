"""
Manage (e.g., create, destroy, query) IM Postgres DB.

Import as:

import im_v2.common.db.db_utils as imvcddbut
"""
import abc
import argparse
import logging
import os
from typing import Optional

import psycopg2 as psycop

import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hsql as hsql
import helpers.hsql_test as hsqltest
import im.ib.sql_writer as imibsqwri
import im.kibot.sql_writer as imkisqwri
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.im_lib_tasks as imvimlita

_LOG = logging.getLogger(__name__)


def add_db_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for db table and stage.
    """
    parser.add_argument(
        "--db_stage",
        action="store",
        required=True,
        type=str,
        help="DB stage to use",
    )
    parser.add_argument(
        "--db_table",
        action="store",
        required=True,
        type=str,
        help="DB table to use",
    )
    return parser


def get_common_create_table_query() -> str:
    """
    Get SQL query that is used to create tables for common usage.
    """
    sql_query = """
    CREATE TABLE IF NOT EXISTS Exchange (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        name text UNIQUE
    );

    CREATE TABLE IF NOT EXISTS Symbol (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        code text UNIQUE,
        description text,
        asset_class AssetClass,
        start_date date DEFAULT CURRENT_DATE,
        symbol_base text
    );

    CREATE TABLE IF NOT EXISTS TRADE_SYMBOL (
        id integer PRIMARY KEY DEFAULT nextval('serial'),
        exchange_id integer REFERENCES Exchange,
        symbol_id integer REFERENCES Symbol,
        UNIQUE (exchange_id, symbol_id)
    );
    """
    return sql_query


def get_data_types_query() -> str:
    """
    Define custom data types inside a database.
    """
    # Define data types.
    query = """
    CREATE TYPE AssetClass AS ENUM ('futures', 'etfs', 'forex', 'stocks', 'sp_500');
    CREATE TYPE Frequency AS ENUM ('minute', 'daily', 'tick');
    CREATE TYPE ContractType AS ENUM ('continuous', 'expiry');
    CREATE SEQUENCE serial START 1;
    """
    return query


def create_all_tables(db_connection: hsql.DbConnection) -> None:
    """
    Create all the tables inside an IM database.

    :param db_connection: a database connection
    """
    queries = [
        get_data_types_query(),
        get_common_create_table_query(),
        imibsqwri.get_create_table_query(),
        imkisqwri.get_create_table_query(),
        imvccdbut.get_ccxt_ohlcv_create_table_query(),
        imvccdbut.get_exchange_name_create_table_query(),
        imvccdbut.get_currency_pair_create_table_query(),
    ]
    # Create tables.
    for query in queries:
        _LOG.debug("Executing query %s", query)
        try:
            cursor = db_connection.cursor()
            cursor.execute(query)
        except psycop.errors.DuplicateObject:
            _LOG.warning("Duplicate table created, skipping.")


def create_im_database(
    db_connection: hsql.DbConnection,
    new_db: str,
    *,
    overwrite: Optional[bool] = None,
) -> None:
    """
    Create database and SQL schema inside it.

    :param db_connection: a database connection
    :param new_db: name of database to connect to, e.g. `im_db_local`
    :param overwrite: overwrite existing database
    """
    _LOG.debug("connection=%s", db_connection)
    # Create a DB.
    hsql.create_database(db_connection, dbname=new_db, overwrite=overwrite)
    conn_details = hsql.db_connection_to_tuple(db_connection)
    new_db_connection = hsql.get_connection(
        host=conn_details.host,
        dbname=new_db,
        port=conn_details.port,
        user=conn_details.user,
        password=conn_details.password,
    )
    # Create table.
    create_all_tables(new_db_connection)
    new_db_connection.close()


# #############################################################################
# TestImDbHelper
# #############################################################################


# TODO(gp): Move to db_test_utils.py


class TestImDbHelper(hsqltest.TestImOmsDbHelper, abc.ABC):
    """
    Configure the helper to build an IM test DB.
    """

    # TODO(gp): For some reason without having this function defined, the
    #  derived classes can't be instantiated because of get_id().
    @classmethod
    @abc.abstractmethod
    def get_id(cls) -> int:
        raise NotImplementedError

    @classmethod
    def _get_compose_file(cls) -> str:
        idx = cls.get_id()
        dir_name = hgit.get_amp_abs_path()
        docker_compose_path = os.path.join(
            dir_name, "im_v2/devops/compose/docker-compose.yml"
        )
        docker_compose_path_idx: str = hio.add_suffix_to_filename(
            docker_compose_path, idx
        )
        return docker_compose_path_idx

    @classmethod
    def _get_service_name(cls) -> str:
        idx = cls.get_id()
        return "im_postgres" + str(idx)

    # TODO(gp): Use file or path consistently.
    @classmethod
    def _get_db_env_path(cls) -> str:
        """
        See `_get_db_env_path()` in the parent class.
        """
        # Use the `local` stage for testing.
        idx = cls.get_id()
        env_file_path = imvimlita.get_db_env_path("local", idx=idx)
        return env_file_path  # type: ignore[no-any-return]

    @classmethod
    def _get_postgres_db(cls) -> str:
        return "im_postgres_db_local"

