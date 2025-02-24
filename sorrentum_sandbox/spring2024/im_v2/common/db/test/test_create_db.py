import logging

import pytest

import helpers.hsql as hsql
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)


class TestCreateDb1(imvcddbut.TestImDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    @pytest.mark.slow("11 seconds.")
    def test_up1(self) -> None:
        """
        Verify that the DB is up.
        """
        db_list = hsql.get_db_names(self.connection)
        _LOG.info("db_list=%s", db_list)

    @pytest.mark.slow("9 seconds.")
    def test_create_all_tables1(self) -> None:
        """
        Verify that all necessary tables are created inside the DB.
        """
        imvcddbut.create_all_tables(self.connection)
        expected = sorted(
            [
                "ccxt_bid_ask_futures_raw",
                "ccxt_bid_ask_resampled_1min",
                "ccxt_bid_ask_spot_raw",
                "ccxt_bid_ask_futures_resampled_1min",
                "ccxt_ohlcv_spot",
                "ccxt_ohlcv_futures",
                "currency_pair",
                "exchange",
                "exchange_name",
                "ib_daily_data",
                "ib_minute_data",
                "ib_tick_bid_ask_data",
                "ib_tick_data",
                "kibot_daily_data",
                "kibot_minute_data",
                "kibot_tick_bid_ask_data",
                "kibot_tick_data",
                "symbol",
                "trade_symbol",
            ]
        )
        actual = sorted(hsql.get_table_names(self.connection))
        self.assertEqual(actual, expected)
        # Delete all the tables.
        hsql.remove_all_tables(connection=self.connection, cascade=True)

    @pytest.mark.slow("18 seconds.")
    def test_create_im_database(self) -> None:
        imvcddbut.create_im_database(
            db_connection=self.connection, new_db="test_db"
        )
        db_list = hsql.get_db_names(self.connection)
        self.assertIn("test_db", db_list)
        # Delete the database.
        hsql.remove_database(self.connection, "test_db")
