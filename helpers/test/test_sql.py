import logging
import pprint

import pandas as pd
import psycopg2.errors as perrors
import pytest

import helpers.hpandas as hpandas
import helpers.hsql as hsql

# TODO(gp): This is a problematic dependency, since helpers should not depende
#  from im_v2. For tests we could be more forgiving, but it would be better to
#  avoid. We should have and use a `TestDbHelper` that doesn't depend on IM
#  in helpers.
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)


# TODO(gp): helpers can't depend from im.
class TestSql1(imvcddbut.TestImDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    @pytest.mark.slow("10 seconds.")
    def test_db_connection_to_tuple(self) -> None:
        """
        Verify that connection string is correct.
        """
        actual_details = hsql.db_connection_to_tuple(self.connection)
        expected = {
            # "host": "localhost",
            "dbname": "im_postgres_db_local",
            "user": "aljsdalsd",
            "password": "alsdkqoen",
        }
        # Drop the `port` key since it is assigned a dynamic value.
        actual_details_dict = actual_details._asdict()
        del actual_details_dict["host"]
        del actual_details_dict["port"]
        #
        self.assert_equal(
            pprint.pformat(actual_details_dict), pprint.pformat(expected)
        )

    @pytest.mark.slow("17 seconds.")
    def test_create_database(self) -> None:
        """
        Verify that db is creating.
        """
        hsql.create_database(self.connection, dbname="test_db")
        self.assertIn("test_db", hsql.get_db_names(self.connection))
        # Delete the database.
        hsql.remove_database(self.connection, "test_db")

    @pytest.mark.slow("10 seconds.")
    def test_create_insert_query(self) -> None:
        """
        Verify that query is correct.
        """
        self._create_test_table()
        test_data = self._get_test_data()
        actual_query = hsql.create_insert_query(test_data, "test_table")
        self.check_string(actual_query)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    @pytest.mark.slow("11 seconds.")
    def test_remove_database1(self) -> None:
        """
        Create database 'test_db_to_remove' and remove it.
        """
        hsql.create_database(
            self.connection,
            dbname="test_db_to_remove",
        )
        hsql.remove_database(self.connection, "test_db_to_remove")
        db_list = hsql.get_db_names(self.connection)
        self.assertNotIn("test_db_to_remove", db_list)

    @pytest.mark.slow("8 seconds.")
    def test_remove_database_invalid(self) -> None:
        """
        Test failed assertion for passing db name that does not exist.
        """
        with self.assertRaises(perrors.InvalidCatalogName):
            hsql.remove_database(self.connection, "db does not exist")

    @pytest.mark.slow("16 seconds.")
    def test_execute_insert_query1(self) -> None:
        """
        Verify that dataframe insertion is correct.
        """
        self._create_test_table()
        test_data = self._get_test_data()
        # Try uploading test data.
        hsql.execute_insert_query(self.connection, test_data, "test_table")
        # Load data.
        df = hsql.execute_query_to_df(self.connection, "SELECT * FROM test_table")
        actual = hpandas.convert_df_to_json_string(df, n_tail=None)
        self.check_string(actual)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    @pytest.mark.slow("16 seconds.")
    def test_copy_rows_with_copy_from1(self) -> None:
        """
        Verify that dataframe insertion via buffer is correct.
        """
        self._create_test_table()
        test_data = self._get_test_data()
        # Try uploading test data.
        hsql.copy_rows_with_copy_from(self.connection, test_data, "test_table")
        # Load data.
        df = hsql.execute_query_to_df(self.connection, "SELECT * FROM test_table")
        actual = hpandas.convert_df_to_json_string(df, n_tail=None)
        self.check_string(actual)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    @pytest.mark.slow("9 seconds.")
    def test_duplicate_removal1(self) -> None:
        """
        Verify that duplicate entries are removed correctly.
        """
        self._create_test_table()
        test_data = self._get_duplicated_data()
        # Try uploading test data.
        hsql.execute_insert_query(self.connection, test_data, "test_table")
        # Create a query to remove duplicates.
        dup_query = hsql.get_remove_duplicates_query(
            "test_table", "id", ["column_1", "column_2"]
        )
        self.connection.cursor().execute(dup_query)
        df = hsql.execute_query_to_df(self.connection, "SELECT * FROM test_table")
        actual = hpandas.convert_df_to_json_string(df, n_tail=None)
        self.check_string(actual)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    @pytest.mark.slow("9 seconds.")
    def test_duplicate_removal2(self) -> None:
        """
        Verify that no rows are removed as duplicates.
        """
        self._create_test_table()
        test_data = self._get_test_data()
        # Try uploading test data.
        hsql.execute_insert_query(self.connection, test_data, "test_table")
        # Create a query to remove duplicates.
        dup_query = hsql.get_remove_duplicates_query(
            "test_table", "id", ["column_1", "column_2"]
        )
        self.connection.cursor().execute(dup_query)
        df = hsql.execute_query_to_df(self.connection, "SELECT * FROM test_table")
        actual = hpandas.convert_df_to_json_string(df, n_tail=None)
        self.check_string(actual)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    @staticmethod
    def _get_test_data() -> pd.DataFrame:
        """
        Get test data.
        """
        test_data = pd.DataFrame(
            columns=["id", "column_1", "column_2"],
            data=[
                [
                    1,
                    1000,
                    "test_string_1",
                ],
                [
                    2,
                    1001,
                    "test_string_2",
                ],
                [
                    3,
                    1002,
                    "test_string_3",
                ],
                [
                    4,
                    1003,
                    "test_string_4",
                ],
                [
                    5,
                    1004,
                    "test_string_5",
                ],
            ],
        )
        return test_data

    @staticmethod
    def _get_duplicated_data() -> pd.DataFrame:
        """
        Get test data with duplicates.
        """
        test_data = pd.DataFrame(
            columns=["id", "column_1", "column_2"],
            data=[
                [
                    1,
                    1000,
                    "test_string_1",
                ],
                [
                    2,
                    1001,
                    "test_string_2",
                ],
                [
                    3,
                    1002,
                    "test_string_3",
                ],
                [
                    4,
                    1002,
                    "test_string_3",
                ],
                [
                    5,
                    1001,
                    "test_string_2",
                ],
            ],
        )
        return test_data

    def _create_test_table(self) -> None:
        """
        Create a test table.
        """
        query = """CREATE TABLE IF NOT EXISTS test_table(
                    id SERIAL PRIMARY KEY,
                    column_1 NUMERIC,
                    column_2 VARCHAR(255)
                    )
                    """
        self.connection.cursor().execute(query)


class TestSql2(imvcddbut.TestImDbHelper):
    """
    Test case for writing and reading postgres database with mixed timestamp
    formats.
    """

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test1(self) -> None:
        """
        Write two DataFrames with different timestamp formats to a postgres
        database and read it back.
        """
        # Create the table.
        self._create_test_table()
        # Insert data in the table with timestamp in string format.
        initial_df = self._get_test_df()
        hsql.execute_insert_query(
            self.connection, initial_df.reset_index(), "test_table"
        )
        # Append data in the table with timestamp in pd.Timestamp format.
        second_df = initial_df.copy()
        second_df["end_download_timestamp"] = pd.to_datetime(
            second_df["end_download_timestamp"]
        )
        hsql.execute_insert_query(
            self.connection, second_df.reset_index(), "test_table"
        )
        # Read it back and verify the output.
        actual_table = hsql.execute_query_to_df(
            self.connection, "SELECT * FROM test_table"
        )
        actual = str(actual_table)
        expected = r"""
          bids  asks    symbol                        ts  \
        0   200   150  BTC_USDT 2024-05-20 00:00:00+00:00
        1   123   120  BTC_USDT 2024-05-20 00:00:00+00:00
        2   263   240  BTC_USDT 2024-05-20 00:00:00+00:00
        3   167   150  BTC_USDT 2024-05-20 00:00:00+00:00
        4   200   150  BTC_USDT 2024-05-20 00:00:00+00:00
        5   123   120  BTC_USDT 2024-05-20 00:00:00+00:00
        6   263   240  BTC_USDT 2024-05-20 00:00:00+00:00
        7   167   150  BTC_USDT 2024-05-20 00:00:00+00:00

            end_download_timestamp
        0 2024-06-04 20:38:43.467599+00:00
        1 2024-06-04 20:38:43.467599+00:00
        2 2024-06-04 20:38:43.467599+00:00
        3 2024-06-04 20:38:43.467599+00:00
        4 2024-06-04 20:38:43.467599+00:00
        5 2024-06-04 20:38:43.467599+00:00
        6 2024-06-04 20:38:43.467599+00:00
        7 2024-06-04 20:38:43.467599+00:00
        """
        self.assert_equal(actual, expected, fuzzy_match=True)
        # Delete the table.
        hsql.remove_table(self.connection, "test_table")

    def _get_test_df(self) -> pd.DataFrame:
        """
        Create a Test DataFrame with timestamps.
        """
        timestamp = pd.Timestamp("2024-05-20 00:00:00", tz="UTC")
        index = [timestamp for _ in range(4)]
        df = pd.DataFrame(
            {
                "bids": [200, 123, 263, 167],
                "asks": [150, 120, 240, 150],
                "symbol": ["BTC_USDT" for _ in range(4)],
            },
            index=index,
        )
        df.index.name = "ts"
        end_download_timestamp = "2024-06-04 20:38:43.467599+00:00"
        df["end_download_timestamp"] = end_download_timestamp
        return df

    def _create_test_table(self) -> None:
        """
        Create the test table.
        """
        query = """CREATE TABLE IF NOT EXISTS test_table(
            bids INT,
            asks INT,
            symbol TEXT,
            ts TIMESTAMP WITH TIME ZONE,
            end_download_timestamp TIMESTAMP WITH TIME ZONE
        )
        """
        self.connection.cursor().execute(query)
