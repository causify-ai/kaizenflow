import argparse
import datetime
import itertools
import unittest.mock as umock

import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hsql as hsql
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.data.extract.backfill_bid_ask_db_data as imvcdebbadd
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.db.db_utils as imvcddbut


def _get_test_data_row_from_s3(
    start_timestamp: pd.Timestamp, minute: int
) -> dict:
    """
    Build test bid_ask 1 minute row.

    :param start_timestamp: start date and time
    :param minute: number of minute to generate
    :return: generated data for the minute
    """
    number_levels_of_order_book = 10
    names_generator = itertools.product(
        ["bid", "ask"],
        ["size", "price"],
        range(1, number_levels_of_order_book + 1),
    )
    names = [
        f"{bid_ask}_{size_price}_l{level}"
        for bid_ask, size_price, level in names_generator
    ]
    # Iterate trough: bid_price_l1, bid_size_l1, ask_size_l1 .. ask_price_l10
    # and assign a mock values.
    bid_ask_values = {name: 0.245553 for name in names}
    timestamp = hdateti.convert_timestamp_to_unix_epoch(
        start_timestamp + pd.Timedelta(minutes=minute)
    )
    knowledge_timestamp = hdateti.convert_timestamp_to_unix_epoch(
        pd.Timestamp("2023-01-01")
    )
    return dict(
        timestamp=timestamp,
        currency_pair="ADA_USDT",
        year=2023,
        month=1,
        exchange_id="binance",
        knowledge_timestamp=knowledge_timestamp,
        **bid_ask_values,
    )


def _get_test_data_from_s3(
    start_timestamp: pd.Timestamp, number_of_minutes: int
) -> pd.DataFrame:
    """
    Build test bid_ask 1 minute data.

    :param start_timestamp: start date and time
    :param number_of_minutes: number of minutes to generate
    :return: dataframe with the mocked data
    """
    return pd.DataFrame(
        [
            _get_test_data_row_from_s3(start_timestamp, minute)
            for minute in range(number_of_minutes)
        ]
    )


def _get_test_data_row_for_db(
    start_timestamp: pd.Timestamp, minute: int, level: int
) -> dict:
    """
    Build test bid_ask 1 minute row for DB format.

    :param start_timestamp: start date and time
    :param minute: number of minute to generate
    :param level: level of the orderbook
    :return: generated data
    """
    timestamp = hdateti.convert_timestamp_to_unix_epoch(
        start_timestamp + pd.Timedelta(minutes=minute)
    )
    knowledge_timestamp = hdateti.convert_timestamp_to_unix_epoch(
        pd.Timestamp("2023-01-01")
    )
    return dict(
        level=level,
        timestamp=timestamp,
        currency_pair="ADA_USDT",
        exchange_id="binance",
        knowledge_timestamp=knowledge_timestamp,
        bid_size=0.245553,
        ask_size=0.245553,
        bid_price=0.245553,
        ask_price=0.245553,
    )


def _get_test_data_for_db(
    start_timestamp: pd.Timestamp, number_of_minutes: int
) -> pd.DataFrame:
    """
    Make mock bid_ask 1 minute data for DB.

    :param start_timestamp: start date and time
    :param number_of_minutes: number of minutes to generate
    :return: dataframe with the mocked data
    """
    return pd.DataFrame(
        [
            _get_test_data_row_for_db(start_timestamp, minute, level)
            for minute in range(number_of_minutes)
            for level in range(1, 11)
        ]
    )


@pytest.mark.slow("Setup test DB ~ 5 seconds.")
@pytest.mark.skip(
    "Skip because the flow is not working because CryptoChassis deprecation0"
    "It might be re-enabled once binance order book history is available"
)
class TestBackfillBidAskDbData(imvcddbut.TestImDbHelper, hmoto.S3Mock_TestCase):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    @umock.patch.object(imvcdebbadd.imvcdcimrdc, "RawDataReader", autospec=True)
    @umock.patch.object(
        imvcdebbadd.imvcdqqach, "GapsInTimeIntervalBySymbolsCheck", autospec=True
    )
    def test__load_data_from_s3(
        self, mock_check_class, mock_raw_data_reader_class
    ) -> None:
        """
        Couple of checks of the loading data from S3:

        - check if qa_check is failed then raise a RunTime exception
        - check for calling qa_checker
        """
        # Mock reader and qa_check.
        mock_class_instance = mock_check_class.return_value
        mock_class_instance.check.return_value = False
        mock_class_instance._status = "FAILED"
        mock_raw_data_reader_instance = mock_raw_data_reader_class.return_value
        mock_raw_data_reader_instance.read_data.return_value = pd.DataFrame(
            [{"timestamp": datetime.datetime.now().timestamp()}]
        )
        # Check for raising exception if qa_check is failed.
        with self.assertRaises(RuntimeError):
            stage = "dev"
            start_timestamp = pd.Timestamp(
                datetime.datetime.now() - datetime.timedelta(hours=5)
            )
            end_timestamp = pd.Timestamp(datetime.datetime.now())
            imvcdebbadd._load_data_from_s3(
                stage, "some_dataset_signature", start_timestamp, end_timestamp
            )
        # Make sure that all method were called.
        mock_raw_data_reader_instance.read_data.assert_called()
        mock_class_instance.check.assert_called()

    def test_transform_s3_to_db_format(self) -> None:
        """
        Check that transformation does its job:

        compare the outcome with the golden outcome.
        """
        expected = r"""      timestamp exchange_id currency_pair  knowledge_timestamp  level  bid_size  ask_size  bid_price  ask_price
            0  1672531200000     binance      ADA_USDT         1672531200000      1  0.245553  0.245553   0.245553   0.245553
            1  1672531200000     binance      ADA_USDT         1672531200000      2  0.245553  0.245553   0.245553   0.245553
            2  1672531200000     binance      ADA_USDT         1672531200000      3  0.245553  0.245553   0.245553   0.245553
            3  1672531200000     binance      ADA_USDT         1672531200000      4  0.245553  0.245553   0.245553   0.245553
            4  1672531200000     binance      ADA_USDT         1672531200000      5  0.245553  0.245553   0.245553   0.245553
            5  1672531200000     binance      ADA_USDT         1672531200000      6  0.245553  0.245553   0.245553   0.245553
            6  1672531200000     binance      ADA_USDT         1672531200000      7  0.245553  0.245553   0.245553   0.245553
            7  1672531200000     binance      ADA_USDT         1672531200000      8  0.245553  0.245553   0.245553   0.245553
            8  1672531200000     binance      ADA_USDT         1672531200000      9  0.245553  0.245553   0.245553   0.245553
            9  1672531200000     binance      ADA_USDT         1672531200000     10  0.245553  0.245553   0.245553   0.245553"""
        start_timestamp = pd.Timestamp("2023-01-01")
        number_of_minutes = 1
        s3_data_df = _get_test_data_from_s3(start_timestamp, number_of_minutes)
        actual_df = imvcdttrut.transform_s3_to_db_format(s3_data_df)
        actual = hpandas.df_to_str(actual_df, num_rows=5000, max_colwidth=15000)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_qa_check(self) -> None:
        """
        Check that qa_check works when assert_missing_data=true:
        """
        # Prepare data.
        run_args = {
            "start_timestamp": "2023-01-01 00:00:00+00:00",
            "end_timestamp": "2023-01-01 00:10:00+00:00",
            "stage": "dev",
            "assert_missing_data": "true",
            "db_table": "ccxt_bid_ask_futures_resampled_1min",
            "log_level": "INFO",
            "s3_dataset_signature": (
                "periodic_daily.airflow.resampled_1min.parquet.bid_ask"
                ".futures.v3.crypto_chassis.binance.v1_0_0"
            ),
        }
        namespace = argparse.Namespace(**run_args)
        # Run and check that qa_check works.
        with self.assertRaises(RuntimeError):
            with umock.patch.object(
                imvcdebbadd, "_check_gaps_by_interval_in_db", return_value=False
            ):
                imvcdebbadd._run(namespace)

    def test_main(self) -> None:
        """
        Check saving transforming data to DB.
        """
        # Prepare data.
        test_data_from_s3 = _get_test_data_from_s3(
            start_timestamp=pd.Timestamp("2023-01-01"),
            number_of_minutes=10,
        )
        mock__load_data_from_s3 = umock.Mock(return_value=test_data_from_s3)
        imvcdebbadd._load_data_from_s3 = mock__load_data_from_s3
        run_args = {
            "start_timestamp": "2023-01-01 00:00:00+00:00",
            "end_timestamp": "2023-01-01 00:10:00+00:00",
            "aws_profile": "ck",
            "stage": "dev",
            "assert_missing_data": "false",
            "db_table": "ccxt_bid_ask_futures_resampled_1min",
            "log_level": "INFO",
            "s3_dataset_signature": (
                "periodic_daily.airflow.resampled_1min.parquet.bid_ask"
                ".futures.v3.crypto_chassis.binance.v1_0_0"
            ),
        }
        namespace = argparse.Namespace(**run_args)
        start_timestamp = pd.Timestamp("2023-01-01")
        number_of_minutes = 10
        test_data_for_db = _get_test_data_for_db(
            start_timestamp, number_of_minutes
        )
        self._prepare_test_ccxt_bid_ask_db_data(data=test_data_for_db)
        # Run.
        with umock.patch.object(
            imvcdebbadd.imvcddbut.DbConnectionManager,
            "get_connection",
            return_value=self.connection,
        ):
            imvcdebbadd._run(namespace)
        number_levels_of_order_book = 10
        self.assertEqual(
            # Explanation:
            # - initially there are 10 minutes generated
            # - after backfilling 10 more items added
            # - each minute will generate as many records as defined
            # in the number_levels_of_order_book constant (10)
            (10 + 10) * number_levels_of_order_book,
            hsql.get_num_rows(
                self.connection, "ccxt_bid_ask_futures_resampled_1min"
            ),
        )

    def _prepare_test_ccxt_bid_ask_db_data(self, data: pd.DataFrame) -> None:
        """
        Populate test ccxt bid_ask DB data.

        :param data: data to populate
        """
        query = (
            imvccdbut.get_ccxt_create_bid_ask_futures_resampled_1min_table_query()
        )
        cursor = self.connection.cursor()
        cursor.execute(query)
        data_type = "bid_ask"
        db_table = "ccxt_bid_ask_futures_resampled_1min"
        time_zone = "UTC"
        imvcddbut.save_data_to_db(
            data, data_type, self.connection, db_table, time_zone
        )
