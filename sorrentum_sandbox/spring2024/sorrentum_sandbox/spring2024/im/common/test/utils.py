import logging

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hsql as hsql
import helpers.hunit_test as hunitest
import im.common.sql_writer as imcosqwri

_LOG = logging.getLogger(__name__)


class SqlWriterBackendTestCase(hunitest.TestCase):
    """
    Helper class to test writing data to IM PostgreSQL DB.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Get PostgreSQL connection.
        self._connection = hsql.get_connection_from_env_vars()
        self._new_db = self._get_test_string()
        # Create database for each test.
        imcdbcrdb.create_im_database(
            connection=self._connection,
            new_db=self._new_db,
            overwrite=True,
        )
        # Define constant IDs for records across the test.
        self._symbol_id = 10
        self._exchange_id = 20
        self._trade_symbol_id = 30
        # Create a placeholder for self._writer.
        self._writer: imcosqwri.AbstractSqlWriter

    def tear_down_test(self) -> None:
        # Close connection.
        self._writer.close()
        # Remove created database.
        hsql.remove_database(
            connection=self._connection,
            dbname=self._new_db,
        )

    def _prepare_tables(
        self,
        insert_symbol: bool,
        insert_exchange: bool,
        insert_trade_symbol: bool,
    ) -> None:
        """
        Insert Symbol, Exchange and TradeSymbol entries to make test work.

        See `common/db/sql` for more info.
        """
        with self._writer.conn:
            with self._writer.conn.cursor() as curs:
                # Fill Symbol table.
                if insert_symbol:
                    curs.execute(
                        "INSERT INTO Symbol (id, code, asset_class) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        [
                            self._symbol_id,
                            "ZS1M",
                            "Futures",
                        ],
                    )
                # Fill Exchange table.
                if insert_exchange:
                    curs.execute(
                        "INSERT INTO Exchange (id, name) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [
                            self._exchange_id,
                            "CME",
                        ],
                    )
                # Fill TradeSymbol table.
                if insert_trade_symbol:
                    curs.execute(
                        "INSERT INTO TradeSymbol (id, exchange_id, symbol_id) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        [
                            self._trade_symbol_id,
                            self._exchange_id,
                            self._symbol_id,
                        ],
                    )
            _LOG.debug("tables=%s", hsql.head_tables(self._writer.conn))

    def _get_test_string(self) -> str:
        string: str = self._get_test_name().replace("/", "").replace(".", "")
        return string

    def _check_saved_data(self, table: str) -> None:
        """
        Check data saved in PostgreSQL by test.

        :param table: table name
        """
        # Construct query to retrieve the data.
        query = "SELECT * FROM %s;" % table
        # Get data in pandas format based on query.
        res = pd.read_sql(query, self._writer.conn)
        # Exclude changeable columns.
        columns_to_check = list(res.columns)
        for column_to_remove in ["id", "start_date"]:
            if column_to_remove in columns_to_check:
                columns_to_check.remove(column_to_remove)
        # Convert dataframe to string.
        txt = hpandas.df_to_str(res[columns_to_check], num_rows=None)
        # Check the output against the golden.
        self.check_string(txt, fuzzy_match=True)
