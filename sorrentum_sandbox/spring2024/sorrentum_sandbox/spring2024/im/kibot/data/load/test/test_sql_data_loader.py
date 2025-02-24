import datetime

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hsql as hsql
import helpers.hunit_test as hunitest
import im.common.data.types as imcodatyp
import im.kibot.data.load.kibot_sql_data_loader as imkdlksdlo
import im.kibot.sql_writer as imkisqwri
import im_v2.common.db.db_utils as imvcddbut


@pytest.mark.skip(reason="CmTask666")
class TestSqlDataLoader1(hunitest.TestCase):
    """
    Test writing operation to PostgreSQL Kibot DB.
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
        # Get PostgreSQL connection parameters.
        self._connection = hsql.get_connection_from_env_vars()
        self._new_db = self._get_test_name().replace("/", "").replace(".", "")
        # Create database for test.
        imvcddbut.create_im_database(
            connection=self._connection,
            new_db=self._new_db,
            overwrite=True,
        )
        # Initialize writer class to test.
        writer = imkisqwri.KibotSqlWriter(
            self._new_db, self._user, self._password, self._host, self._port
        )
        # Add data to database.
        self._prepare_tables(writer)
        writer.close()
        # Create loader.
        self._loader = imkdlksdlo.KibotSqlDataLoader(
            self._new_db, self._user, self._password, self._host, self._port
        )

    def tear_down_test(self) -> None:
        # Close connection.
        self._loader.conn.close()
        # Remove created database.
        hsql.remove_database(connection=self._connection, dbname=self._new_db)

    def test_get_symbol_id1(self) -> None:
        """
        Test correct mapping from symbol name to internal id.
        """
        actual = self._loader.get_symbol_id("ABC0")
        expected = 10
        self.assertEqual(actual, expected)

    def test_get_symbol_id2(self) -> None:
        """
        Test incorrect symbol.
        """
        with self.assertRaises(AssertionError):
            self._loader.get_symbol_id("_")

    def test_get_exchange_id1(self) -> None:
        """
        Test correct mapping from exchange name to internal id.
        """
        actual = self._loader.get_exchange_id("CME")
        expected = 10
        self.assertEqual(actual, expected)

    def test_get_exchange_id2(self) -> None:
        """
        Test incorrect exchange.
        """
        with self.assertRaises(AssertionError):
            self._loader.get_exchange_id("_")

    def test_get_trade_symbol_id1(self) -> None:
        """
        Test correct mapping from symbol/exchange pair to internal trade symbol
        id.
        """
        actual = self._loader.get_trade_symbol_id(11, 11)
        expected = 12
        self.assertEqual(actual, expected)

    def test_get_trade_symbol_id2(self) -> None:
        """
        Test incorrect trade symbol.
        """
        with self.assertRaises(AssertionError):
            self._loader.get_trade_symbol_id(9, 9)

    def test_read_data1(self) -> None:
        """
        Test correct minute data reading for ZYX9 on CME.
        """
        # Get data.
        actual = self._loader._read_data(
            "CME", "ZYX9", imcodatyp.Frequency.Minutely
        )
        # Convert to string.
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        # Compare with golden.
        self.check_string(actual_string, fuzzy_match=True)

    def test_read_data2(self) -> None:
        """
        Test correct daily data reading for ETF0 on LSE.
        """
        # Get data.
        actual = self._loader._read_data("LSE", "ZYX9", imcodatyp.Frequency.Daily)
        # Convert to string.
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        # Compare with golden.
        self.check_string(actual_string, fuzzy_match=True)

    def test_read_data3(self) -> None:
        """
        Test failed assertion for invalid exchange.
        """
        # Get data.
        with self.assertRaises(AssertionError):
            self._loader._read_data("", "ZYX9", imcodatyp.Frequency.Daily)

    def test_read_data4(self) -> None:
        """
        Test failed assertion for invalid ticker.
        """
        # Get data.
        with self.assertRaises(AssertionError):
            self._loader._read_data("CME", "", imcodatyp.Frequency.Minutely)

    @staticmethod
    def _generate_test_data(seed: int) -> pd.DataFrame:
        """
        Generate dataframe with some data based on symbol.
        """
        nrows = 5
        df = pd.DataFrame(
            {
                "trade_symbol_id": [seed] * nrows,
                "date": [
                    datetime.date(2021, 1, i + 1).isoformat()
                    for i in range(nrows)
                ],
                "datetime": [
                    datetime.datetime(2021, 1, 1, 1, i + 1, 0).isoformat()
                    for i in range(nrows)
                ],
                "open": [seed + i for i in range(nrows)],
                "high": [seed + 2 * i for i in range(nrows)],
                "low": [seed - i for i in range(nrows)],
                "close": [seed] * nrows,
                "volume": [seed * 100] * nrows,
            }
        )
        return df

    @classmethod
    def _prepare_tables(cls, writer: imkisqwri.KibotSqlWriter) -> None:
        """
        Insert Symbol, Exchange and TradeSymbol entries to make test work.

        See `common/db/sql/` for more info.
        """
        with writer.conn as conn:
            with conn.cursor() as curs:
                # Fill Symbol table.
                for symbol_id, name, asset_class in [
                    (10, "ABC0", "Futures"),
                    (11, "ZYX9", "Futures"),
                    (12, "ETF0", "etfs"),
                ]:
                    curs.execute(
                        "INSERT INTO Symbol (id, code, asset_class) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        [
                            symbol_id,
                            name,
                            asset_class,
                        ],
                    )
                # Fill Exchange table.
                for exchange_id, name in [
                    (10, "CME"),
                    (11, "LSE"),
                ]:
                    curs.execute(
                        "INSERT INTO Exchange (id, name) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [
                            exchange_id,
                            name,
                        ],
                    )
                # Fill TradeSymbol table.
                for trade_symbol_id, exchange_id, symbol_id in [
                    (10, 10, 10),
                    (11, 10, 11),
                    (12, 11, 11),
                    (13, 11, 12),
                ]:
                    curs.execute(
                        "INSERT INTO TradeSymbol (id, exchange_id, symbol_id) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        [
                            trade_symbol_id,
                            exchange_id,
                            symbol_id,
                        ],
                    )
                # Fill minute and daily data.
                for trade_symbol_id in [10, 11, 12, 13]:
                    generated_data = cls._generate_test_data(trade_symbol_id)
                    writer.insert_bulk_daily_data(
                        generated_data.drop(columns=["datetime"])
                    )
                    writer.insert_bulk_minute_data(
                        generated_data.drop(columns=["date"])
                    )
