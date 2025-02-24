import pandas as pd
import pytest

import helpers.hpandas as hpandas
import im.common.data.types as imcodatyp
import im.common.test.utils as ictuti
import im.ib.sql_writer as imibsqwri


@pytest.mark.skip(reason="CmTask666")
class TestIbSqlWriterBackend1(ictuti.SqlWriterBackendTestCase):
    """
    Test writing operation to PostgreSQL IM db.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test2()
        yield

    def set_up_test2(self) -> None:
        self.set_up_test()
        # Initialize writer class to test.
        self._writer = imibsqwri.IbSqlWriter(
            dbname=self._dbname,
            user=self._user,
            password=self._password,
            host=self._host,
            port=self._port,
        )

    def test_ensure_symbol_exist1(self) -> None:
        """
        Test adding a new symbol to Symbol table.
        """
        self._writer.ensure_symbol_exists(
            symbol=self._get_test_string(),
            asset_class=imcodatyp.AssetClass.Futures,
        )
        self._check_saved_data(table="Symbol")

    def test_get_remaining_data_to_load(self) -> None:
        """
        Slicing Pandas Dataframe to load.

        This test, mock the situation, when loading process interrupted
        somehow. Then, we need to load remaining data from the Pandas
        Dataframe.
        """
        # Load the daily data.
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        df = pd.DataFrame(
            {
                "trade_symbol_id": [self._trade_symbol_id] * 3,
                "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
                "open": [10.0] * 3,
                "high": [15] * 3,
                "low": [9] * 3,
                "close": [12.5] * 3,
                "volume": [1000] * 3,
                "average": [12.0] * 3,
                "barCount": [10] * 3,
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        self._writer.insert_bulk_daily_data(df=df)
        # Mock the situation, when loading process interrupted somehow.
        # Literally delete the tail of the data.
        with self._writer.conn as conn:
            with conn.cursor() as curs:
                curs.execute("DELETE FROM IbDailyData WHERE date > '2021-01-01'")
        # Get remaining part of the pandas Dataframe to load.
        df = self._writer.get_remaining_data_to_load(
            df,
            trade_symbol_id=self._trade_symbol_id,
            frequency=imcodatyp.Frequency.Daily,
        )
        # Convert dataframe to string.
        txt = hpandas.df_to_str(df, num_rows=None)
        # Check the output against the golden.
        self.check_string(txt, fuzzy_match=True)

    def test_ensure_exchange_exist1(self) -> None:
        """
        Test adding a new exchange to Exchange table.
        """
        self._writer.ensure_exchange_exists(exchange=self._get_test_string())
        self._check_saved_data(table="Exchange")

    def test_ensure_trade_symbol_exist1(self) -> None:
        """
        Test adding a new symbol to TradeSymbol table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=False
        )
        self._writer.ensure_trade_symbol_exists(
            symbol_id=self._symbol_id, exchange_id=self._exchange_id
        )
        self._check_saved_data(table="TradeSymbol")

    def test_insert_bulk_daily_data1(self) -> None:
        """
        Test adding a dataframe to IbDailyData table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        df = pd.DataFrame(
            {
                "trade_symbol_id": [self._trade_symbol_id] * 3,
                "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
                "open": [10.0] * 3,
                "high": [15] * 3,
                "low": [9] * 3,
                "close": [12.5] * 3,
                "volume": [1000] * 3,
                "average": [12.0] * 3,
                "barCount": [10] * 3,
            }
        )
        self._writer.insert_bulk_daily_data(df=df)
        self._check_saved_data(table="IbDailyData")

    def test_insert_bulk_daily_data_with_holes(self) -> None:
        """
        Test adding a dataframe to IbDailyData table if some data is missing.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        df = pd.DataFrame(
            {
                "trade_symbol_id": [self._trade_symbol_id] * 3,
                "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
                "open": [10.0] * 3,
                "high": [15] * 3,
                "low": [9] * 3,
                "close": [12.5] * 3,
                "volume": [1000] * 3,
                "average": [12.0] * 3,
                "barCount": [10] * 3,
            }
        )
        self._writer.insert_bulk_daily_data(df=df)
        with self._writer.conn as conn:
            with conn.cursor() as curs:
                curs.execute("delete from IbDailyData where date = '2021-01-02'")
        self._writer.insert_bulk_daily_data(df=df)
        self._check_saved_data(table="IbDailyData")

    def test_insert_daily_data1(self) -> None:
        """
        Test adding a one bar data to IbDailyData table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        self._writer.insert_daily_data(
            trade_symbol_id=self._trade_symbol_id,
            date="2021-01-01",
            open_val=10.0,
            high_val=15,
            low_val=9,
            close_val=12.5,
            volume_val=1000,
            average_val=12.0,
            bar_count_val=10,
        )
        self._check_saved_data(table="IbDailyData")

    def test_insert_bulk_minute_data1(self) -> None:
        """
        Test adding a dataframe to IbMinuteData table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        df = pd.DataFrame(
            {
                "trade_symbol_id": [self._trade_symbol_id] * 3,
                "datetime": [
                    "2021-02-10T13:50:00Z",
                    "2021-02-10T13:51:00Z",
                    "2021-02-10T13:52:00Z",
                ],
                "open": [10.0] * 3,
                "high": [15] * 3,
                "low": [9] * 3,
                "close": [12.5] * 3,
                "volume": [1000] * 3,
                "average": [12.0] * 3,
                "barCount": [10] * 3,
            }
        )
        self._writer.insert_bulk_minute_data(df=df)
        self._check_saved_data(table="IbMinuteData")

    def test_insert_bulk_minute_data_with_holes(self) -> None:
        """
        Test adding a dataframe to IbMinuteData table if some data is missing.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        df = pd.DataFrame(
            {
                "trade_symbol_id": [self._trade_symbol_id] * 3,
                "datetime": [
                    "2021-02-10T13:50:00Z",
                    "2021-02-10T13:51:00Z",
                    "2021-02-10T13:52:00Z",
                ],
                "open": [10.0] * 3,
                "high": [15] * 3,
                "low": [9] * 3,
                "close": [12.5] * 3,
                "volume": [1000] * 3,
                "average": [12.0] * 3,
                "barCount": [10] * 3,
            }
        )
        with self._writer.conn as conn:
            with conn.cursor() as curs:
                curs.execute(
                    "DELETE FROM IbMinuteData "
                    "WHERE datetime = '2021-02-10T13:51:00Z'"
                )
        self._writer.insert_bulk_minute_data(df=df)
        self._check_saved_data(table="IbMinuteData")

    def test_insert_minute_data1(self) -> None:
        """
        Test adding a one bar data to IbMinuteData table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        self._writer.insert_minute_data(
            trade_symbol_id=self._trade_symbol_id,
            date_time="2021-02-10T13:50:00Z",
            open_val=10.0,
            high_val=15,
            low_val=9,
            close_val=12.5,
            volume_val=1000,
            average_val=12.0,
            bar_count_val=10,
        )
        self._check_saved_data(table="IbMinuteData")

    def test_insert_tick_data1(self) -> None:
        """
        Test adding a one tick data to IbTickData table.
        """
        self._prepare_tables(
            insert_symbol=True, insert_exchange=True, insert_trade_symbol=True
        )
        self._writer.insert_tick_data(
            trade_symbol_id=self._trade_symbol_id,
            date_time="2021-02-10T13:50:00Z",
            price_val=10.0,
            size_val=15,
        )
        self._check_saved_data(table="IbTickData")
