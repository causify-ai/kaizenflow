import logging
import os
import pprint
import unittest.mock as umock
from typing import List, Optional

import numpy as np
import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import helpers.hsql as hsql
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.db.db_utils as imvcddbut

_LOG = logging.getLogger(__name__)

_AWS_PROFILE = "ck"


class TestImRawDataClient(hunitest.TestCase):
    """
    Testing build path functionality for parquet and CSV file.
    """

    def test_build_s3_pq_file_path1(self) -> None:
        """
        Test CC bid-ask futures S3 path.
        """
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        s3_path = self._build_s3_pq_file_path_test(signature)
        self.assert_equal(
            s3_path,
            "s3://cryptokaizen-data/v3/bulk/airflow/resampled_1min/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0",
        )

    def test_build_s3_pq_file_path2(self) -> None:
        """
        Test CC bid-ask spot S3 path.
        """
        signature = "bulk.airflow.downloaded_1sec.parquet.bid_ask.spot.v3.crypto_chassis.binance.v1_0_0"
        s3_path = self._build_s3_pq_file_path_test(signature)
        self.assert_equal(
            s3_path,
            "s3://cryptokaizen-data/v3/bulk/airflow/downloaded_1sec/parquet/bid_ask/spot/v3/crypto_chassis/binance/v1_0_0",
        )

    def test_build_s3_pq_file_path3(self) -> None:
        """
        Test CCXT OHLCV futures S3 path.
        """
        signature = "bulk.airflow.downloaded_1min.parquet.ohlcv.futures.v7.ccxt.binance.v1_0_0"
        s3_path = self._build_s3_pq_file_path_test(signature)
        self.assert_equal(
            s3_path,
            "s3://cryptokaizen-data/v3/bulk/airflow/downloaded_1min/parquet/ohlcv/futures/v7/ccxt/binance/v1_0_0",
        )

    def test_build_s3_csv_file_path1(self) -> None:
        """
        Test CCXT bid-ask futures S3 path building.
        """
        signature = "realtime.airflow.downloaded_200ms.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        s3_path = self._build_s3_csv_file_path_test(signature)
        self.assert_equal(
            s3_path,
            "s3://cryptokaizen-data/v3/realtime/airflow/downloaded_200ms/parquet/bid_ask/futures/v7/ccxt/binance/v1_0_0/mock.csv.gz",
        )

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def _build_s3_pq_file_path_test(
        self,
        signature: str,
        mock_get_partition_mode: umock.MagicMock,
    ) -> str:
        """
        Helper function to test bid-ask s3 parquet path.
        """
        mock_get_partition_mode.return_value = None
        reader = imvcdcimrdc.RawDataReader(signature)
        s3_path = reader._build_s3_pq_file_path()
        return s3_path

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def _build_s3_csv_file_path_test(
        self,
        signature: str,
        mock_get_partition_mode: umock.MagicMock,
    ) -> str:
        """
        Helper function to test building bid/ask S3 CSV path.
        """
        mock_get_partition_mode.return_value = None
        reader = imvcdcimrdc.RawDataReader(signature)
        currency_pair = "mock"
        s3_path = reader._build_s3_csv_file_path(currency_pair)
        return s3_path


@pytest.mark.slow("~9 seconds.")
class TestImRawDataClient2(imvcddbut.TestImDbHelper):
    """
    Testing functionality of `RawDataReader` to load data from DB table.
    """

    @staticmethod
    def get_class_name() -> str:
        return "TestImRawDataClient2"

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        instance = cls()
        instance._prepare_test_ccxt_bid_ask_futures_db_data()

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_initialize_class(self, mock_get_connection: umock.MagicMock) -> None:
        """
        Smoke test that the class is being initialized correctly.
        """
        # Build RawDataReader.
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        # Check broker state and remove dynamic mock ids.
        actual = pprint.pformat(vars(reader))
        self.check_string(
            actual, test_class_name=self.get_class_name(), purify_text=True
        )

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table_head(
        self, mock_get_connection: umock.MagicMock
    ) -> None:
        """
        Simple test that the data are fetched from the DB head correctly.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table_head()
        actual = pprint.pformat(actual)
        expected = r"""
                        timestamp  bid_size  bid_price  ask_size  ask_price currency_pair  \
                    0  1659710207000      10.0       31.0      41.0       51.0      ETH_USDT
                    1  1659710207000      15.0       12.0      22.0       32.0      BTC_USDT
                    2  1659710146000      10.0       30.0      40.0       50.0      ETH_USDT
                    3  1659710146000      15.0       10.0      20.0       30.0      BTC_USDT

                    exchange_id  level    end_download_timestamp       knowledge_timestamp
                    0     binance      2 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                    1     binance      1 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                    2     binance      1 2022-08-05 14:35:46+00:00 2022-08-05 14:35:46+00:00
                    3     binance      2 2022-08-05 14:35:46+00:00 2022-08-05 14:35:46+00:00
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_read_data_head1(self, mock_get_connection: umock.MagicMock) -> None:
        """
        Simple test that the data are fetched from the DB head correctly.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.read_data_head()
        actual = pprint.pformat(actual)
        expected = r"""
                        timestamp  bid_size  bid_price  ask_size  ask_price currency_pair  \
                    0  1659710207000      10.0       31.0      41.0       51.0      ETH_USDT
                    1  1659710207000      15.0       12.0      22.0       32.0      BTC_USDT
                    2  1659710146000      10.0       30.0      40.0       50.0      ETH_USDT
                    3  1659710146000      15.0       10.0      20.0       30.0      BTC_USDT

                    exchange_id  level    end_download_timestamp       knowledge_timestamp
                    0     binance      2 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                    1     binance      1 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                    2     binance      1 2022-08-05 14:35:46+00:00 2022-08-05 14:35:46+00:00
                    3     binance      2 2022-08-05 14:35:46+00:00 2022-08-05 14:35:46+00:00
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table1(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            pd.Timestamp("2022-08-05 10:36:00-04:00", tz="America/New_York"),
            pd.Timestamp("2022-08-05 10:38:46-04:00", tz="America/New_York"),
            bid_ask_format="long",
        )
        actual = pprint.pformat(actual)
        expected = r"""
                    id      timestamp  bid_size  bid_price  ask_size  ask_price currency_pair  \
                    0   2  1659710207000      10.0       31.0      41.0       51.0      ETH_USDT
                    1   4  1659710207000      15.0       12.0      22.0       32.0      BTC_USDT

                    exchange_id  level    end_download_timestamp       knowledge_timestamp
                    0     binance      2 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                    1     binance      1 2022-08-05 14:35:47+00:00 2022-08-05 14:35:47+00:00
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table2(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
            None,
            currency_pairs=["ETH_USDT", "BTC_USDT"],
            bid_ask_levels=[2],
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710146000      BTC_USDT     binance 2022-08-05 14:35:46+00:00
                    1659710207000      ETH_USDT     binance 2022-08-05 14:35:47+00:00

                                        knowledge_timestamp  bid_size_l2  bid_price_l2  \
                    timestamp
                    1659710146000 2022-08-05 14:35:46+00:00         15.0          10.0
                    1659710207000 2022-08-05 14:35:47+00:00         10.0          31.0

                                ask_size_l2  ask_price_l2
                    timestamp
                    1659710146000         20.0          30.0
                    1659710207000         41.0          51.0
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table3(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            None,
            pd.Timestamp("2022-08-05 10:38:46-04:00", tz="America/New_York"),
            currency_pairs=["ETH_USDT"],
            bid_ask_levels=[1, 2],
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710146000      ETH_USDT     binance 2022-08-05 14:35:46+00:00
                    1659710207000      ETH_USDT     binance 2022-08-05 14:35:47+00:00

                                        knowledge_timestamp  bid_size_l1  bid_size_l2  \
                    timestamp
                    1659710146000 2022-08-05 14:35:46+00:00         10.0          NaN
                    1659710207000 2022-08-05 14:35:47+00:00          NaN         10.0

                                bid_price_l1  bid_price_l2  ask_size_l1  ask_size_l2  \
                    timestamp
                    1659710146000          30.0           NaN         40.0          NaN
                    1659710207000           NaN          31.0          NaN         41.0

                                ask_price_l1  ask_price_l2
                    timestamp
                    1659710146000          50.0           NaN
                    1659710207000           NaN          51.0
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table4(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.okx.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            None,
            None,
            currency_pairs=["ETH_USDT"],
            bid_ask_levels=[2],
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710207000      ETH_USDT         okx 2022-08-05 14:35:47+00:00

                                        knowledge_timestamp  bid_size_l2  bid_price_l2  \
                    timestamp
                    1659710207000 2022-08-05 14:35:47+00:00         10.0          31.0

                                ask_size_l2  ask_price_l2
                    timestamp
                    1659710207000         41.0          51.0
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table5(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.okx.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            None,
            None,
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710146000      BTC_USDT         okx 2022-08-05 14:35:46+00:00
                    1659710146000      ETH_USDT         okx 2022-08-05 14:35:46+00:00
                    1659710207000      BTC_USDT         okx 2022-08-05 14:35:47+00:00
                    1659710207000      ETH_USDT         okx 2022-08-05 14:35:47+00:00

                                        knowledge_timestamp  bid_size_l1  bid_size_l2  \
                    timestamp
                    1659710146000 2022-08-05 14:35:46+00:00          NaN         15.0
                    1659710146000 2022-08-05 14:35:46+00:00         10.0          NaN
                    1659710207000 2022-08-05 14:35:47+00:00         15.0          NaN
                    1659710207000 2022-08-05 14:35:47+00:00          NaN         10.0

                                bid_price_l1  bid_price_l2  ask_size_l1  ask_size_l2  \
                    timestamp
                    1659710146000           NaN          10.0          NaN         20.0
                    1659710146000          30.0           NaN         40.0          NaN
                    1659710207000          12.0           NaN         22.0          NaN
                    1659710207000           NaN          31.0          NaN         41.0

                                ask_price_l1  ask_price_l2
                    timestamp
                    1659710146000           NaN          30.0
                    1659710146000          50.0           NaN
                    1659710207000          32.0           NaN
                    1659710207000           NaN          51.0
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_load_db_table6(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.okx.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.load_db_table(
            pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
            pd.Timestamp("2022-08-05 10:36:46-04:00", tz="America/New_York"),
            currency_pairs=["ETH_USDT", "BTC_USDT"],
            bid_ask_levels=[1, 2],
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710146000      BTC_USDT         okx 2022-08-05 14:35:46+00:00
                    1659710146000      ETH_USDT         okx 2022-08-05 14:35:46+00:00

                                        knowledge_timestamp  bid_size_l1  bid_size_l2  \
                    timestamp
                    1659710146000 2022-08-05 14:35:46+00:00          NaN         15.0
                    1659710146000 2022-08-05 14:35:46+00:00         10.0          NaN

                                bid_price_l1  bid_price_l2  ask_size_l1  ask_size_l2  \
                    timestamp
                    1659710146000           NaN          10.0          NaN         20.0
                    1659710146000          30.0           NaN         40.0          NaN

                                ask_price_l1  ask_price_l2
                    timestamp
                    1659710146000           NaN          30.0
                    1659710146000          50.0           NaN
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(
        imvcdcimrdc.imvcddbut.DbConnectionManager, "get_connection"
    )
    def test_read_data1(
        self,
        mock_get_connection: umock.MagicMock,
    ) -> None:
        """
        Verify that the data fetched from the DB with filters is correct.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # Mock connection for RawDataReader.
        mock_get_connection.return_value = self.connection
        reader = imvcdcimrdc.RawDataReader(signature)
        actual = reader.read_data(
            pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
            None,
            currency_pairs=["ETH_USDT", "BTC_USDT"],
            bid_ask_levels=[2],
        )
        actual = pprint.pformat(actual)
        expected = r"""
                                currency_pair exchange_id    end_download_timestamp  \
                    timestamp
                    1659710146000      BTC_USDT     binance 2022-08-05 14:35:46+00:00
                    1659710207000      ETH_USDT     binance 2022-08-05 14:35:47+00:00

                                        knowledge_timestamp  bid_size_l2  bid_price_l2  \
                    timestamp
                    1659710146000 2022-08-05 14:35:46+00:00         15.0          10.0
                    1659710207000 2022-08-05 14:35:47+00:00         10.0          31.0

                                ask_size_l2  ask_price_l2
                    timestamp
                    1659710146000         20.0          30.0
                    1659710207000         41.0          51.0
                """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def _prepare_test_ccxt_bid_ask_futures_db_data(self) -> None:
        """
        Create and insert test data in mock DB.
        """
        # Create database table.
        query = imvccdbut.get_ccxt_create_bid_ask_futures_raw_table_query()
        cursor = self.connection.cursor()
        cursor.execute(query)
        # Generate test dataset.
        test_data = self._get_bid_ask_data()
        # Insert data to database.
        hsql.execute_insert_query(
            connection=self.connection,
            obj=test_data,
            table_name="ccxt_bid_ask_futures_raw",
        )

    def _get_bid_ask_data(self) -> pd.DataFrame:
        """
        Fetch OHLCV data for testing.

        Helper method for fetching data used in unit tests.
        """
        columns = [
            "timestamp",
            "bid_size",
            "bid_price",
            "ask_size",
            "ask_price",
            "currency_pair",
            "exchange_id",
            "level",
            "end_download_timestamp",
            "knowledge_timestamp",
        ]
        data = [
            [
                hdateti.convert_timestamp_to_unix_epoch(
                    pd.Timestamp(
                        "2022-08-05 10:35:46-04:00", tz="America/New_York"
                    )
                ),
                10,
                30,
                40,
                50,
                "ETH_USDT",
                "binance",
                1,
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
            ],
            [
                hdateti.convert_timestamp_to_unix_epoch(
                    pd.Timestamp(
                        "2022-08-05 10:36:47-04:00", tz="America/New_York"
                    )
                ),
                10,
                31,
                41,
                51,
                "ETH_USDT",
                "binance",
                2,
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
            ],
            [
                hdateti.convert_timestamp_to_unix_epoch(
                    pd.Timestamp(
                        "2022-08-05 10:35:46-04:00", tz="America/New_York"
                    )
                ),
                15,
                10,
                20,
                30,
                "BTC_USDT",
                "binance",
                2,
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:46-04:00", tz="America/New_York"),
            ],
            [
                hdateti.convert_timestamp_to_unix_epoch(
                    pd.Timestamp(
                        "2022-08-05 10:36:47-04:00", tz="America/New_York"
                    )
                ),
                15,
                12,
                22,
                32,
                "BTC_USDT",
                "binance",
                1,
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
                pd.Timestamp("2022-08-05 10:35:47-04:00", tz="America/New_York"),
            ],
        ]
        binance_data = pd.DataFrame(data, columns=columns)
        okx_data = binance_data.copy()
        okx_data["exchange_id"] = "okx"
        return pd.concat([binance_data, okx_data], ignore_index=True)


class TestImRawDataClient3(hunitest.TestCase):
    """
    Testing functionality of `RawDataReader` to load data from DB table.
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
        self.start_timestamp = pd.Timestamp("2023-09-15 14:30:00+00:00")
        self.end_timestamp = pd.Timestamp("2023-09-15 14:33:00+00:00")
        # Creating mock function for `load_db_data` to return mock dataframe
        self.mock_load_db_data = umock.patch.object(
            imvcdcimrdc.imvcddbut, "load_db_data", autospec=True, spec_set=True
        ).start()
        self.mock_load_db_data.return_value = self.get_test_dataframe()
        # Creating mock function for `_setup_db_table_access` to pass db_connection
        self.mock_setup_db = umock.patch.object(
            imvcdcimrdc.RawDataReader,
            "_setup_db_table_access",
            autospec=True,
            spec_set=True,
        ).start()
        self.mock_setup_db.return_value = None

    def tear_down_test(self) -> None:
        # Clean up the mock after each test
        umock.patch.stopall()

    def get_test_dataframe(self) -> pd.DataFrame:
        """
        Helper function to create dataframe with duplicate entries for the
        test.
        """
        test_data = {
            "id": np.arange(23625518955, 23625518961),
            "currency_pair": ["WAVES_USDT"] * 6,
            "bid_size": [50, 60, 50, 60, 70, 80],
            "level": [1, 2, 1, 2, 1, 2],
            "bid_price": [100, 200, 100, 200, 300, 400],
            "end_download_timestamp": [
                self.end_timestamp,
                self.end_timestamp,
                self.end_timestamp + pd.Timedelta(seconds=10),
                self.end_timestamp + pd.Timedelta(seconds=10),
                self.end_timestamp + pd.Timedelta(seconds=20),
                self.end_timestamp + pd.Timedelta(seconds=20),
            ],
        }
        test_df = pd.DataFrame(test_data)
        test_df["timestamp"] = int(self.start_timestamp.timestamp())
        return test_df

    def test_load_db_table1(self) -> None:
        """
        Test load_db_table when deduplicate is not passed.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        obj = imvcdcimrdc.RawDataReader(signature)
        obj.db_connection = None
        obj.table_name = None
        actual_df = obj.load_db_table(self.start_timestamp, self.end_timestamp)
        actual = hpandas.df_to_str(actual_df)
        expected = r"""
                currency_pair    end_download_timestamp  bid_size_l1  bid_size_l2  bid_price_l1  bid_price_l2
        timestamp
        1694788200    WAVES_USDT 2023-09-15 14:33:00+00:00           50           60           100           200
        1694788200    WAVES_USDT 2023-09-15 14:33:10+00:00           50           60           100           200
        1694788200    WAVES_USDT 2023-09-15 14:33:20+00:00           70           80           300           400
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_load_db_table2(self) -> None:
        """
        Test load_db_table when deduplicate and subset is passed.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        obj = imvcdcimrdc.RawDataReader(signature)
        obj.db_connection = None
        obj.table_name = None
        deduplicate = True
        subset = ["currency_pair", "bid_price", "bid_size"]
        actual_df = obj.load_db_table(
            self.start_timestamp,
            self.end_timestamp,
            deduplicate=deduplicate,
            subset=subset,
        )
        actual = hpandas.df_to_str(actual_df)
        expected = r"""
                currency_pair    end_download_timestamp  bid_size_l1  bid_size_l2  bid_price_l1  bid_price_l2
        timestamp
        1694788200    WAVES_USDT 2023-09-15 14:33:00+00:00           50           60           100           200
        1694788200    WAVES_USDT 2023-09-15 14:33:20+00:00           70           80           300           400
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_load_db_table3(self) -> None:
        """
        Test load_db_table when deduplicate passed and subset is not passed.
        """
        signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        obj = imvcdcimrdc.RawDataReader(signature)
        obj.db_connection = None
        obj.table_name = None
        with self.assertRaises(AssertionError) as fail:
            deduplicate = True
            obj.load_db_table(
                self.start_timestamp, self.end_timestamp, deduplicate=deduplicate
            )
        actual_error = str(fail.exception)
        expected_error = r"""
        ################################################################################
        * Failed assertion *
        'None' is not 'None'
        subset kwarg must be provided when deduplicate=True
        ################################################################################
        """
        self.assert_equal(actual_error, expected_error, fuzzy_match=True)


class TestImRawDataClient4(hunitest.TestCase):
    """
    Testing functionality of `RawDataReader` to load data from CSV file.
    """

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_csv_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_load_csv1(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_csv_file_path: umock.MagicMock,
    ) -> None:
        """
        Test load_csv function with all the parameters.
        """
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        mock_get_partition_mode.return_value = None
        mock_build_s3_csv_file_path.return_value = self._get_test_data()
        obj = imvcdcimrdc.RawDataReader(signature)
        currency_pair = "mock"
        start_timestamp = pd.Timestamp(1698151790126, unit="ms")
        end_timestamp = pd.Timestamp(1698151797365, unit="ms")
        actual = obj.load_csv(
            currency_pair,
            start_timestamp,
            end_timestamp,
        )
        actual = pprint.pformat(actual[1:10])
        expected = r"""
            timestamp currency_pair exchange_id            end_download_timestamp  \
        1  1698151790129      APE_USDT     binance  2023-10-24 12:49:50.400686+00:00
        2  1698151790133     BAKE_USDT     binance  2023-10-24 12:49:50.403131+00:00
        3  1698151790138    WAVES_USDT     binance  2023-10-24 12:49:50.403689+00:00
        4  1698151790157      OGN_USDT     binance  2023-10-24 12:49:50.404010+00:00
        5  1698151790162      DOT_USDT     binance  2023-10-24 12:49:50.401412+00:00
        6  1698151790180      XRP_USDT     binance  2023-10-24 12:49:50.402714+00:00
        7  1698151790183     LINK_USDT     binance  2023-10-24 12:49:50.402484+00:00
        8  1698151790192      CTK_USDT     binance  2023-10-24 12:49:50.405256+00:00
        9  1698151790198    STORJ_USDT     binance  2023-10-24 12:49:50.399588+00:00

                        knowledge_timestamp  bid_size_l1  bid_price_l1  ask_size_l1  \
        1  2023-10-24 12:49:50.869850+00:00     17747.00        1.2690     19704.00
        2  2023-10-24 12:49:50.869850+00:00     55212.00        0.1352     46666.00
        3  2023-10-24 12:49:50.869850+00:00       167.00        1.8435       800.00
        4  2023-10-24 12:49:50.869850+00:00     48570.00        0.1217     11946.00
        5  2023-10-24 12:49:50.869850+00:00      3133.80        4.3580      9142.70
        6  2023-10-24 12:49:50.869850+00:00     86754.30        0.5825     35686.80
        7  2023-10-24 12:49:50.869850+00:00       550.83       10.4400       369.27
        8  2023-10-24 12:49:50.869850+00:00      1085.00        0.4729       420.00
        9  2023-10-24 12:49:50.869850+00:00      2695.00        0.4112      5040.00

        ask_price_l1
        1        1.2700
        2        0.1353
        3        1.8436
        4        0.1218
        5        4.3590
        6        0.5826
        7       10.4410
        8        0.4730
        9        0.4113
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_csv_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_load_csv2(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_csv_file_path: umock.MagicMock,
    ) -> None:
        """
        Test load_csv function with all the parameters.
        """
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        mock_get_partition_mode.return_value = None
        mock_build_s3_csv_file_path.return_value = self._get_test_data()
        obj = imvcdcimrdc.RawDataReader(signature)
        currency_pair = "mock"
        start_timestamp = None
        end_timestamp = pd.Timestamp(1698151790129, unit="ms")
        actual = obj.load_csv(currency_pair, start_timestamp, end_timestamp)
        actual = pprint.pformat(actual)
        expected = r"""
            timestamp currency_pair exchange_id            end_download_timestamp  \
        0  1698151790126      CRV_USDT     binance  2023-10-24 12:49:50.402848+00:00
        1  1698151790129      APE_USDT     binance  2023-10-24 12:49:50.400686+00:00

                        knowledge_timestamp  bid_size_l1  bid_price_l1  ask_size_l1  \
        0  2023-10-24 12:49:50.869850+00:00     420863.5         0.487     209572.4
        1  2023-10-24 12:49:50.869850+00:00      17747.0         1.269      19704.0

        ask_price_l1
        0         0.488
        1         1.270
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_csv_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_load_csv3(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_csv_file_path: umock.MagicMock,
    ) -> None:
        """
        Test load_csv function with all the parameters.
        """
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        mock_get_partition_mode.return_value = None
        mock_build_s3_csv_file_path.return_value = self._get_test_data()
        obj = imvcdcimrdc.RawDataReader(signature)
        currency_pair = "mock"
        start_timestamp = pd.Timestamp(1698151797361, unit="ms")
        end_timestamp = None
        actual = obj.load_csv(currency_pair, start_timestamp, end_timestamp)
        actual = pprint.pformat(actual)
        expected = r"""
                timestamp currency_pair exchange_id  \
        744  1698151797361     DOGE_USDT     binance
        745  1698151797365    WAVES_USDT     binance

                    end_download_timestamp               knowledge_timestamp  \
        744  2023-10-24 12:49:57.515051+00:00  2023-10-24 12:49:57.564413+00:00
        745  2023-10-24 12:49:57.514338+00:00  2023-10-24 12:49:57.564413+00:00

            bid_size_l1  bid_price_l1  ask_size_l1  ask_price_l1
        744      43182.0       0.06971     202159.0       0.06972
        745         27.1       1.84170        761.4       1.84180
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow("9 seconds.")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    def test_get_partition_mode1(
        self,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> None:
        """
        Test to verify the behavior of the `_get_partition_mode` function.
        """
        # The test data has file layout in the following format which is
        # used to test partition mode
        # /currency_pair=ADA_USDT/year=2023/month=1/
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient4.test_get_partition_mode1/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        obj = imvcdcimrdc.RawDataReader(signature)
        actual = str(obj.partition_mode)
        expected = r"""None"""
        self.assert_equal(actual, expected)

    @pytest.mark.slow("9 seconds.")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    def test_get_partition_mode2(
        self,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> None:
        """
        Test to verify the behavior of the `_get_partition_mode` function.
        """
        # The test data has file layout in the following format which is
        # used to test partition mode
        # /currency_pair=APE_USDT/year=2023/month=10/day=1
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient4.test_get_partition_mode2/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        signature = "bulk.airflow.resampled_1min.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        obj = imvcdcimrdc.RawDataReader(signature)
        actual = str(obj.partition_mode)
        expected = "by_year_month_day"
        self.assert_equal(actual, expected)

    @staticmethod
    def _get_test_data() -> str:
        """
        Download test data from S3 and return the local path.
        """
        dir_name = "test_data/"
        # The path has a CSV file which contains bid ask data recorded for a
        # min used to verify above test cases.
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient4/",
        )
        print(file_path)
        hio.create_enclosing_dir(dir_name, incremental=True)
        cmd = f"aws s3 sync {file_path} {dir_name} --profile {_AWS_PROFILE}"
        hsystem.system(cmd)
        pattern = "*.csv"
        only_files = True
        use_relative_paths = False
        path = hio.listdir(dir_name, pattern, only_files, use_relative_paths)[0]
        return path


class TestImRawDataClient5(hunitest.TestCase):
    """
    Testing functionality of `RawDataReader` to load data from parquet file.
    """

    def test_load_parquet1(
        self,
    ) -> None:
        """
        Verify that the data fetched from the parquet with filters is correct.
        """
        start_timestamp = pd.Timestamp("2023-10-01 04:00+00:00")
        end_timestamp = pd.Timestamp("2023-10-01 05:00+00:00")
        currency_pairs = None
        bid_ask_levels = None
        actual = self._test_load_parquet_helper(
            start_timestamp, end_timestamp, currency_pairs, bid_ask_levels
        )
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    def test_load_parquet2(
        self,
    ) -> None:
        """
        Verify that the data fetched from the parquet with filters is correct.
        """
        start_timestamp = pd.Timestamp("2023-10-01 05:55+00:00")
        end_timestamp = None
        currency_pairs = None
        bid_ask_levels = None
        actual = self._test_load_parquet_helper(
            start_timestamp, end_timestamp, currency_pairs, bid_ask_levels
        )
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    def test_load_parquet3(
        self,
    ) -> None:
        """
        Verify that the data fetched from the parquet with filters is correct.
        """
        start_timestamp = None
        end_timestamp = pd.Timestamp("2023-10-01 04:10+00:00")
        currency_pairs = None
        bid_ask_levels = None
        actual = self._test_load_parquet_helper(
            start_timestamp, end_timestamp, currency_pairs, bid_ask_levels
        )
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    def test_load_parquet4(
        self,
    ) -> None:
        """
        Verify that the data fetched from the parquet with filters is correct.
        """
        start_timestamp = pd.Timestamp("2023-10-01 04:00+00:00")
        end_timestamp = pd.Timestamp("2023-10-01 05:00+00:00")
        currency_pairs = None
        bid_ask_levels = [1, 2]
        actual = self._test_load_parquet_helper(
            start_timestamp, end_timestamp, currency_pairs, bid_ask_levels
        )
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    @pytest.mark.slow()
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    def test_load_parquet5(
        self,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> pd.DataFrame:
        """
        Helper function to test proper loading of resampled parquet data in
        wide format.
        """
        signature = "periodic_daily.airflow.resampled_1min.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        # The path has a parquet file which contains resampled bid ask data
        # recorded from "2023-05-05 04:00+00:00" to "2023-05-05 05:00+00:00".
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient5/test_load_parquet5/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        obj = imvcdcimrdc.RawDataReader(signature)
        start_timestamp = pd.Timestamp("2023-05-05 04:00+00:00")
        end_timestamp = pd.Timestamp("2023-05-05 04:10+00:00")
        currency_pairs = ["APE_USDT", "XRP_USDT"]
        bid_ask_levels = [1]
        actual = obj.load_parquet(
            start_timestamp,
            end_timestamp,
            currency_pairs=currency_pairs,
            bid_ask_levels=bid_ask_levels,
        )
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_load_parquet_head(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> None:
        """
        Simple test that the data are fetched from the parquet head correctly.
        """
        signature = "bulk.airflow.downloaded_200ms.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        # The path has a parquet file which contains bid ask data recorded from
        # "2023-10-01 04:00+00:00" to "2023-10-01 06:00+00:00".
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient5/currency_pair=APE_USDT/year=2023/month=10/day=1/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        mock_get_partition_mode.return_value = None
        obj = imvcdcimrdc.RawDataReader(signature)
        actual = obj.load_parquet_head()
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_read_data_head1(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> None:
        """
        Simple test that the data are fetched from the parquet head correctly.
        """
        signature = "bulk.airflow.downloaded_200ms.parquet.bid_ask.futures.v3.crypto_chassis.binance.v1_0_0"
        # The path has a parquet file which contains bid ask data recorded from
        # "2023-10-01 04:00+00:00" to "2023-10-01 06:00+00:00".
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient5/currency_pair=APE_USDT/year=2023/month=10/day=1/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        mock_get_partition_mode.return_value = None
        obj = imvcdcimrdc.RawDataReader(signature)
        actual = obj.read_data_head()
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def test_read_data1(
        self,
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> None:
        """
        Simple test that the data are fetched from the parquet head correctly.
        """
        signature = "bulk.airflow.downloaded_200ms.parquet.bid_ask.futures.v3.ccxt.binance.v1_0_0"
        # The path has a parquet file which contains bid ask data recorded from
        # "2023-10-01 04:00+00:00" to "2023-10-01 06:00+00:00".
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient5/currency_pair=APE_USDT/year=2023/month=10/day=1/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        mock_get_partition_mode.return_value = None
        obj = imvcdcimrdc.RawDataReader(signature)
        start_timestamp = pd.Timestamp("2023-10-01 04:00+00:00")
        end_timestamp = pd.Timestamp("2023-10-01 05:00+00:00")
        actual = obj.read_data(start_timestamp, end_timestamp)
        actual = pprint.pformat(actual)
        self.check_string(
            actual,
            test_class_name="TestImRawDataClient5",
        )

    @umock.patch.object(imvcdcimrdc.RawDataReader, "_build_s3_pq_file_path")
    @umock.patch.object(imvcdcimrdc.RawDataReader, "_get_partition_mode")
    def _test_load_parquet_helper(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        currency_pairs: Optional[List[str]],
        bid_ask_levels: Optional[List[str]],
        mock_get_partition_mode: umock.MagicMock,
        mock_build_s3_pq_file_path: umock.MagicMock,
    ) -> pd.DataFrame:
        """
        Helper function to test proper loading of parquet data.
        """
        signature = "bulk.airflow.downloaded_200ms.parquet.bid_ask.futures.v3.ccxt.binance.v1_0_0"
        # The path has a parquet file which contains bid ask data recorded from
        # "2023-10-01 04:00+00:00" to "2023-10-01 06:00+00:00".
        file_path = os.path.join(
            hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE),
            "unit_test/outcomes/TestImRawDataClient5/currency_pair=APE_USDT/year=2023/month=10/day=1/",
        )
        mock_build_s3_pq_file_path.return_value = file_path
        mock_get_partition_mode.return_value = None
        obj = imvcdcimrdc.RawDataReader(signature)
        data = obj.load_parquet(
            start_timestamp,
            end_timestamp,
            currency_pairs=currency_pairs,
            bid_ask_levels=bid_ask_levels,
        )
        return data
