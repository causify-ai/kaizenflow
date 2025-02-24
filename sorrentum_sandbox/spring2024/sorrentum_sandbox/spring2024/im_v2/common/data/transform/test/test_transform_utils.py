import os
import unittest.mock as umock

import pandas as pd
import pytest

import data_schema.dataset_schema_utils as dsdascut
import helpers.hdbg as hdbg
import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import im_v2.common.data.extract.extract_utils as imvcdeexut
import im_v2.common.data.transform.resample_daily_bid_ask_data as imvcdtrdbad
import im_v2.common.data.transform.transform_utils as imvcdttrut


class TestGetVendorEpochUnit(hunitest.TestCase):
    POSSIBLE_UNITS = ["ms", "s", "ns"]

    def test_get_vendor_epoch_unit(self) -> None:
        """
        Verify that the correct epoch unit is returned.
        """
        actual = imvcdttrut.get_vendor_epoch_unit("crypto_chassis", "bid_ask")
        self.assertIn(actual, self.POSSIBLE_UNITS)

    def test_get_vendor_epoch_unit_invalid_vendor(self) -> None:
        """
        Verify that ValueError is raised when invalid vendor is passed.
        """
        with self.assertRaises(AssertionError):
            vendor = "invalid_vendor"
            data_type = "bid_ask"
            imvcdttrut.get_vendor_epoch_unit(vendor, data_type)

    def test_get_vendor_epoch_unit_invalid_data_type(self) -> None:
        """
        Verify that ValueError is raised when invalid data type is passed.
        """
        with self.assertRaises(AssertionError):
            imvcdttrut.get_vendor_epoch_unit("ccxt", "invalid_data_type")


class TestConvertTimestampColumn(hunitest.TestCase):
    def test_integer_datetime(self) -> None:
        """
        Verify that integer datetime is converted correctly.
        """
        # Prepare inputs.
        test_data = pd.Series([1638756800000, 1639656800000, 1648656800000])
        # Run.
        actual = imvcdttrut.convert_timestamp_column(test_data)
        # Check output.
        actual = str(actual)
        expected = """
        0   2021-12-06 02:13:20+00:00
        1   2021-12-16 12:13:20+00:00
        2   2022-03-30 16:13:20+00:00
        dtype: datetime64[ns, UTC]
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_string_datetime(self) -> None:
        """
        Verify that string datetime is converted correctly.
        """
        # Prepare inputs.
        test_data = pd.Series(["2021-01-12", "2021-02-14", "2010-12-11"])
        # Run.
        actual = imvcdttrut.convert_timestamp_column(test_data)
        # Check output.
        actual = str(actual)
        expected = """
        0   2021-01-12
        1   2021-02-14
        2   2010-12-11
        dtype: datetime64[ns]
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_incorrect_datetime(self) -> None:
        """
        Assert that incorrect types are not converted.
        """
        test_data = pd.Series([37.9, 88.11, 14.0])
        with self.assertRaises(ValueError) as fail:
            imvcdttrut.convert_timestamp_column(test_data)
        actual = str(fail.exception)
        expected = (
            "Incorrect data format. Datetime column should be of int or str dtype"
        )
        self.assert_equal(actual, expected)


# #############################################################################


class TestReindexOnDatetime(hunitest.TestCase):
    def get_dummy_df_with_timestamp(self, unit: str = "ms") -> pd.DataFrame:
        datetime_column_name = "dummy_timestamp"
        test_data = {
            "dummy_value": [1, 2, 3],
            datetime_column_name: [1638646800000, 1638646860000, 1638646960000],
        }
        if unit == "s":
            test_data[datetime_column_name] = [
                timestamp // 1000 for timestamp in test_data[datetime_column_name]
            ]
        return pd.DataFrame(data=test_data)

    def test_reindex_on_datetime_milliseconds(self) -> None:
        """
        Verify datetime index creation when timestamp is in milliseconds.
        """
        # Prepare inputs.
        dummy_df = self.get_dummy_df_with_timestamp()
        # Run.
        reindexed_dummy_df = imvcdttrut.reindex_on_datetime(
            dummy_df, "dummy_timestamp"
        )
        # Check output.
        actual = str(reindexed_dummy_df)
        expected = (
            "                           dummy_value  dummy_timestamp\n"
            "dummy_timestamp                                        \n"
            "2021-12-04 19:40:00+00:00            1    1638646800000\n"
            "2021-12-04 19:41:00+00:00            2    1638646860000\n"
            "2021-12-04 19:42:40+00:00            3    1638646960000"
        )
        self.assert_equal(actual, expected)

    def test_reindex_on_datetime_seconds(self) -> None:
        """
        Verify datetime index creation when timestamp is in seconds.
        """
        # Prepare inputs.
        dummy_df = self.get_dummy_df_with_timestamp(unit="s")
        # Run.
        reindexed_dummy_df = imvcdttrut.reindex_on_datetime(
            dummy_df, "dummy_timestamp", unit="s"
        )
        actual = str(reindexed_dummy_df)
        expected = (
            "                           dummy_value  dummy_timestamp\n"
            "dummy_timestamp                                        \n"
            "2021-12-04 19:40:00+00:00            1       1638646800\n"
            "2021-12-04 19:41:00+00:00            2       1638646860\n"
            "2021-12-04 19:42:40+00:00            3       1638646960"
        )
        self.assert_equal(actual, expected)

    def test_reindex_on_datetime_wrong_column(self) -> None:
        """
        Assert that wrong column is detected before reindexing.
        """
        dummy_df = self.get_dummy_df_with_timestamp()
        with self.assertRaises(AssertionError) as fail:
            imvcdttrut.reindex_on_datetime(dummy_df, "void_column")
        actual = str(fail.exception)
        expected = """
        * Failed assertion *
        'void_column' in 'Index(['dummy_value', 'dummy_timestamp'], dtype='object')'
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_reindex_on_datetime_index_already_present(self) -> None:
        """
        Assert that reindexing is not done on already reindexed dataframe.
        """
        dummy_df = self.get_dummy_df_with_timestamp()
        reindexed_dummy_df = imvcdttrut.reindex_on_datetime(
            dummy_df, "dummy_timestamp"
        )
        with self.assertRaises(AssertionError) as fail:
            imvcdttrut.reindex_on_datetime(reindexed_dummy_df, "dummy")
        actual = str(fail.exception)
        expected = """
        * Failed assertion *
        'dummy' in 'Index(['dummy_value', 'dummy_timestamp'], dtype='object')'
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestReindexOnCustomColumns(hunitest.TestCase):
    def get_test_data(self) -> pd.DataFrame:
        test_data = {
            "dummy_value_1": [1, 3, 2],
            "dummy_value_2": ["A", "C", "B"],
            "dummy_value_3": [0, 0, 0],
        }
        df = pd.DataFrame(data=test_data)
        df.index.name = "test"
        return df

    def test_reindex_on_custom_columns(self) -> None:
        """
        Verify that dataframe is re-indexed correctly with specified columns.
        """
        # Prepare inputs.
        test_data = self.get_test_data()
        expected_columns = test_data.columns.values.tolist()
        # Run.
        actual = imvcdttrut.reindex_on_custom_columns(
            test_data, expected_columns[:2], expected_columns
        )
        # Check output.
        actual = str(actual)
        expected = r"""                             dummy_value_3
        dummy_value_1 dummy_value_2
        1             A                          0
        2             B                          0
        3             C                          0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_reindex_on_custom_columns_invalid_columns(self) -> None:
        """
        Verify that dataframe is re-indexed correctly with specified columns.
        """
        # Prepare inputs.
        test_data = self.get_test_data()
        expected_columns = ["mock1", "mock2", "mock3"]
        # Run.
        with self.assertRaises(AssertionError) as fail:
            imvcdttrut.reindex_on_custom_columns(
                test_data, expected_columns[:2], expected_columns
            )
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        * Failed assertion *
        val1=['mock1', 'mock2', 'mock3']
        issubset
        val2=['dummy_value_1', 'dummy_value_2', 'dummy_value_3']
        val1 - val2=['mock1', 'mock2', 'mock3']
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class TestTransformRawWebsocketData(hunitest.TestCase):
    def test_transform_raw_websocket_ohlcv_data(self) -> None:
        """
        Verify that raw OHLCV dict data received from websocket is transformed
        to DataFrame of specified format.
        """
        test_exchange = "binance"
        test_timestamp = pd.Timestamp("2022-10-05 15:06:00.019422+00:00")
        test_data = [
            {
                "ohlcv": [
                    [1664982180000, 1324.17, 1324.79, 1324.0, 1324.01, 2081.017],
                    [1664982240000, 1324.17, 1324.79, 1324.0, 1324.01, 2081.017],
                ],
                "currency_pair": "ETH/USDT",
                "end_download_timestamp": test_timestamp,
            },
            {
                "ohlcv": [
                    [1664982180000, 19900.0, 19913.2, 19900.0, 19905.1, 376.639],
                    [1664982240000, 19900.0, 19913.2, 19900.0, 19905.1, 376.639],
                ],
                "currency_pair": "BTC/USDT",
                "end_download_timestamp": test_timestamp,
            },
        ]
        expected_data = [
            [
                "ETH_USDT",
                1664982180000,
                1324.17,
                1324.79,
                1324.0,
                1324.01,
                2081.017,
                test_timestamp,
                test_exchange,
            ],
            [
                "ETH_USDT",
                1664982240000,
                1324.17,
                1324.79,
                1324.0,
                1324.01,
                2081.017,
                test_timestamp,
                test_exchange,
            ],
            [
                "BTC_USDT",
                1664982180000,
                19900.0,
                19913.2,
                19900.0,
                19905.1,
                376.639,
                test_timestamp,
                test_exchange,
            ],
            [
                "BTC_USDT",
                1664982240000,
                19900.0,
                19913.2,
                19900.0,
                19905.1,
                376.639,
                test_timestamp,
                test_exchange,
            ],
        ]
        expected_columns = [
            "currency_pair",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "end_download_timestamp",
            "exchange_id",
        ]
        expected_df = pd.DataFrame(expected_data, columns=expected_columns)
        actual_df = imvcdttrut.transform_raw_websocket_data(
            test_data, "ohlcv", test_exchange
        ).reset_index(drop=True)
        self.assert_equal(
            hpandas.df_to_str(expected_df), hpandas.df_to_str(actual_df)
        )

    def test_transform_raw_websocket_bid_ask_data(self) -> None:
        """
        Verify that raw bid/ask dict data received from websocket is
        transformed to DataFrame of specified format.
        """
        test_exchange = "binance"
        test_timestamp = pd.Timestamp("2022-10-05 15:06:00.019422+00:00")
        test_data = [
            {
                "bids": [[1336.7, 60.789], [1336.69, 3.145]],
                "asks": [[1336.71, 129.483], [1336.72, 20.892]],
                "timestamp": 1664987681005,
                "datetime": "2022-10-05T16:34:41.005Z",
                "nonce": 2000450235897,
                "symbol": "ETH/USDT",
                "end_download_timestamp": test_timestamp,
            },
            {
                "bids": [[20066.5, 39.455], [20066.3, 1.346]],
                "asks": [[20066.6, 0.698], [20066.7, 0.008]],
                "timestamp": 1664987681001,
                "datetime": "2022-10-05T16:34:41.001Z",
                "nonce": 2000450235917,
                "symbol": "BTC/USDT",
                "end_download_timestamp": test_timestamp,
            },
        ]

        expected_data = [
            [
                "ETH_USDT",
                1664987681005,
                1336.7,
                60.789,
                1336.71,
                129.483,
                test_timestamp,
                1,
                test_exchange,
            ],
            [
                "ETH_USDT",
                1664987681005,
                1336.69,
                3.145,
                1336.72,
                20.892,
                test_timestamp,
                2,
                test_exchange,
            ],
            [
                "BTC_USDT",
                1664987681001,
                20066.5,
                39.455,
                20066.6,
                0.698,
                test_timestamp,
                1,
                test_exchange,
            ],
            [
                "BTC_USDT",
                1664987681001,
                20066.3,
                1.346,
                20066.7,
                0.008,
                test_timestamp,
                2,
                test_exchange,
            ],
        ]
        expected_columns = [
            "currency_pair",
            "timestamp",
            "bid_price",
            "bid_size",
            "ask_price",
            "ask_size",
            "end_download_timestamp",
            "level",
            "exchange_id",
        ]
        expected_df = pd.DataFrame(expected_data, columns=expected_columns)
        actual_df = imvcdttrut.transform_raw_websocket_data(
            test_data, "bid_ask", test_exchange
        ).reset_index(drop=True)
        self.assert_equal(
            hpandas.df_to_str(expected_df), hpandas.df_to_str(actual_df)
        )

    def test_transform_raw_websocket_trades_data(self) -> None:
        """
        Verify that raw trades dict data received from websocket is transformed
        to DataFrame of specified format.
        """
        # Build test data.
        test_exchange = "binance"
        test_timestamp = pd.Timestamp("2022-10-05 15:06:00.019422+00:00")

        def get_nested_test_data(timestamp: int, id: int) -> dict:
            """
            Return a nested dict with test data.

            :param timestamp: timestamp of the test data
            :param int: trade id of the test data
            :return: nested dict with test data
            """
            return {
                "info": {"some": "info"},
                "timestamp": timestamp,
                "datetime": "2023-03-10T09:27:55.951Z",
                "symbol": "ETH/USDT",
                "id": id,
                "order": None,
                "type": None,
                "side": "buy",
                "takerOrMaker": "taker",
                "price": 1405.2,
                "amount": 0.242,
                "cost": 340.0584,
                "fee": None,
                "fees": [],
            }

        def get_test_record(data: list) -> dict:
            """
            Return a dict with test record.

            :param data: list of nested dicts with test data
            :return: dict with test record
            """
            return {
                "data": data,
                "currency_pair": "ETH/USDT",
                "end_download_timestamp": test_timestamp,
            }

        test_data = [
            get_test_record(
                [
                    get_nested_test_data(1678440475951, 1),
                    get_nested_test_data(1678440475952, 2),
                ]
            ),
            get_test_record(
                [
                    get_nested_test_data(1678440475953, 3),
                    get_nested_test_data(1678440475954, 4),
                ]
            ),
        ]
        # Run transformation.
        actual_df = imvcdttrut.transform_raw_websocket_data(
            test_data, "trades", test_exchange
        ).reset_index(drop=True)
        # Verify results.
        expected = r"""
            id      timestamp side   price  amount currency_pair           end_download_timestamp exchange_id
        0   1  1678440475951  buy  1405.2   0.242      ETH/USDT 2022-10-05 15:06:00.019422+00:00     binance
        1   2  1678440475952  buy  1405.2   0.242      ETH/USDT 2022-10-05 15:06:00.019422+00:00     binance
        2   3  1678440475953  buy  1405.2   0.242      ETH/USDT 2022-10-05 15:06:00.019422+00:00     binance
        3   4  1678440475954  buy  1405.2   0.242      ETH/USDT 2022-10-05 15:06:00.019422+00:00     binance
        """
        actual = hpandas.df_to_str(actual_df)
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


@pytest.mark.slow
class TestResampleBidAskData(hmoto.S3Mock_TestCase):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test2()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test2(self) -> None:
        self.src_signature = (
            "periodic_daily.airflow.archived_200ms"
            ".parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        )
        self.dst_signature = (
            "periodic_daily.airflow.resampled_1min"
            ".parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        )
        self.base_s3_path = f"s3://{self.bucket_name}/"
        src_dir = imvcdtrdbad._get_s3_path_from_signature(
            self.src_signature,
            self.base_s3_path,
        )
        self.start_timestamp = "2023-04-01T00:00:00+00:00"
        self.end_timestamp = "2023-04-01T00:00:01.999999+00:00"
        self.bid_ask_levels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        data = self.read_data_from_s3(self.start_timestamp, self.end_timestamp)
        self.set_up_test()
        #
        imvcdeexut.save_parquet(
            data,
            src_dir,
            "ms",
            self.mock_aws_profile,
            "bid_ask",
            # The `id` column is most likely not needed once the data is in S3.
            drop_columns=["id"],
            mode="append",
            partition_mode="by_year_month_day",
        )
        self.s3fs_ = hs3.get_s3fs(self.mock_aws_profile)

    def test_resample_daily_bid_ask_data(self) -> None:
        parser = imvcdtrdbad._parse()
        args = parser.parse_args(
            [
                "--start_timestamp",
                f"{self.start_timestamp}",
                "--end_timestamp",
                f"{self.end_timestamp}",
                "--src_signature",
                f"{self.src_signature}",
                "--src_s3_path",
                f"{self.base_s3_path}",
                "--dst_signature",
                f"{self.dst_signature}",
                "--dst_s3_path",
                f"{self.base_s3_path}",
                "--assert_all_resampled",
                "--bid_ask_levels",
                "10",
            ]
        )
        imvcdtrdbad._run(args, aws_profile=self.s3fs_)
        dst_dir = imvcdtrdbad._get_s3_path_from_signature(
            self.dst_signature,
            self.base_s3_path,
        )
        actual_df = hparque.from_parquet(dst_dir, aws_profile=self.s3fs_)
        actual_df = actual_df.reset_index(drop=True)
        actual_df = actual_df.drop(["knowledge_timestamp"], axis=1)
        actual = hpandas.df_to_str(actual_df, num_rows=5000, max_colwidth=15000)
        self.check_string(actual)

    def read_data_from_s3(
        self, start_timestamp: str, end_timestamp: str
    ) -> pd.DataFrame:
        """
        Dump test data to S3 mock bucket.
        """
        # Get signature arguments mapping for source and destination data.
        dataset_schema = dsdascut.get_dataset_schema()
        scr_signature_args = dsdascut.parse_dataset_signature_to_args(
            self.src_signature, dataset_schema
        )
        dst_signature_args = dsdascut.parse_dataset_signature_to_args(
            self.dst_signature, dataset_schema
        )
        # Define the unit of the timestamp column.
        data_type = "bid_ask"
        epoch_unit = imvcdttrut.get_vendor_epoch_unit(
            scr_signature_args["vendor"], data_type
        )
        # Check that the source and destination data format are parquet.
        hdbg.dassert_eq(scr_signature_args["data_format"], "parquet")
        hdbg.dassert_eq(dst_signature_args["data_format"], "parquet")
        # Define filters for data period.
        # Note: it's better from Airflow execution perspective
        # to keep the interval closed: [start, end].
        # In other words the client takes care of providing the correct interval.
        filters = imvcdtrdbad._build_parquet_filters(
            scr_signature_args["action_tag"],
            start_timestamp,
            end_timestamp,
            epoch_unit,
            self.bid_ask_levels,
        )
        filters += [("currency_pair", "in", ["BTC_USDT", "ETH_USDT"])]
        aws_profile = "ck"
        s3_bucket = hs3.get_s3_bucket_path_unit_test(aws_profile)
        src_s3_path = imvcdtrdbad._get_s3_path_from_signature(
            self.src_signature, s3_bucket
        )
        data = hparque.from_parquet(
            src_s3_path, filters=filters, aws_profile=aws_profile
        )
        data = data.reset_index(drop=True)
        return data


@pytest.mark.slow
class TestResampleBidAskData2(hunitest.TestCase):
    def setUp(self):
        super().setUp()
        self._get_test_data()

    def test_resample_bid_ask_data_to_1min(self) -> None:
        """
        Verify that raw data 200ms is correctly resampled to 1min.
        """
        scratch_dir = self.get_scratch_space()
        # Prepare inputs.
        # SampleBidAskDataLong.csv contains short sample of top 2
        # orderbook levels for BTC_USDT and ETH_USDT.
        file_name = os.path.join(scratch_dir, "SampleBidAskDataLong.csv")
        data = pd.read_csv(file_name)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data = data.set_index("timestamp")
        # Choose only one level as the function expects.
        data = data[data["level"] == 1]
        # Check results.
        bid_ask_cols = ["bid_size", "bid_price", "ask_size", "ask_price"]
        actual_df = data.groupby("currency_pair")[bid_ask_cols].apply(
            imvcdttrut.resample_bid_ask_data_to_1min
        )

        expected = r"""
        bid_price.open bid_size.open ask_price.open ask_size.open bid_ask_midpoint.open half_spread.open log_size_imbalance.open bid_price.close bid_size.close ask_price.close ask_size.close bid_ask_midpoint.close half_spread.close log_size_imbalance.close bid_price.high bid_size.max ask_price.high ask_size.max bid_ask_midpoint.max half_spread.max log_size_imbalance.max bid_price.low bid_size.min ask_price.low ask_size.min bid_ask_midpoint.min half_spread.min log_size_imbalance.min bid_price.mean bid_size.mean ask_price.mean ask_size.mean bid_ask_midpoint.mean half_spread.mean log_size_imbalance.mean bid_ask_midpoint_var.100ms bid_ask_midpoint_autocovar.100ms log_size_imbalance_var.100ms log_size_imbalance_autocovar.100ms
        currency_pair timestamp
        BTC_USDT 2023-05-05 14:01:00+00:00 29163.70 8.581 29163.80 1.762 29163.75 0.05 1.583101 29168.00 18.547 29168.1 1.650 29168.050 0.050 2.419533 29168.00 30.071 29168.1 2.276 29168.050 0.10 8.677610 29163.70 5.552 29163.80 0.002 29163.75 0.050 0.891739 29166.250000 14.608643 29166.364286 1.026071 29166.307143 0.057143 3.66105 4.535000 0.0 270.096097 225.892178
        ETH_USDT 2023-05-05 14:01:00+00:00 1931.65 1.482 1931.67 0.016 1931.66 0.01 4.528559 1932.99 2.884 1933.0 223.777 1932.995 0.005 -4.351472 1932.99 72.749 1933.0 223.777 1932.995 0.01 6.476819 1931.65 1.482 1931.67 0.010 1931.66 0.005 -4.351472 1932.253077 24.094615 1932.264615 30.164231 1932.258846 0.005769 1.71967 0.472225 0.0 156.028250 44.467921
        """
        actual = hpandas.df_to_str(actual_df)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_resample_bid_ask_data_to_1min2(self) -> None:
        """
        Verify that ffill() inside resample_bid_ask_data_to_1min() behaves as
        expected.
        """
        scratch_dir = self.get_scratch_space()
        # Prepare inputs.
        file_name = os.path.join(scratch_dir, "SampleBidAskDataLong.csv")
        data = pd.read_csv(file_name)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data = data.set_index("timestamp")
        # Choose only one level as the function expects.
        data = data[data["level"] == 1]
        # Choose only single symbol to simplify test.
        data = data[data["currency_pair"] == "BTC_USDT"]

        with umock.patch.object(
            imvcdttrut.cfinresa, "resample_bars"
        ) as resample_bars:
            bid_ask_cols = ["bid_size", "bid_price", "ask_size", "ask_price"]
            imvcdttrut.resample_bid_ask_data_to_1min(data[bid_ask_cols])
            self.assertEqual(resample_bars.call_count, 1)
            # Get the dataset passed to resampler.
            # call_args_list has the following structure:
            # [call((pd.DataFrame(...),), ...), call(...)]
            # That's why triple indexing is needed to fetch the DF itself.
            ffilled_data = resample_bars.call_args_list[0][0][0]

            # Confirm that the data was forward filled to the expected length
            # AKA the input to cnfiresa.resample_bars is what we expect.
            actual = hpandas.df_to_str(ffilled_data)
            self.check_string(actual)

    def test_resample_bid_ask_data_to_1min3(self) -> None:
        """
        Verify that assertion fails if we pass incorrectly formatted data.

        The function expects single level of data, if multiple levels
        are passed the assertion should fail.
        """
        scratch_dir = self.get_scratch_space()
        # Prepare inputs.
        file_name = os.path.join(scratch_dir, "SampleBidAskDataLong.csv")
        data = pd.read_csv(file_name)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data = data.set_index("timestamp")
        # Check assertion.
        with self.assertRaises(AssertionError) as ae:
            data.groupby("currency_pair").apply(
                imvcdttrut.resample_bid_ask_data_to_1min
            )
        exp = r"""
        ################################################################################
        * Failed assertion *
        val1 - val2=[]
        val2 - val1=['currency_pair', 'level']
        val1=['ask_price', 'ask_size', 'bid_price', 'bid_size']
        set eq
        val2=['ask_price', 'ask_size', 'bid_price', 'bid_size', 'currency_pair', 'level']
        ################################################################################
        """
        act = str(ae.exception)
        self.assert_equal(exp, act, fuzzy_match=True)

    def test_resample_multilevel_bid_ask_data_to_1min(self) -> None:
        """
        Verify that multilevel raw data 200ms is correctly resampled to 1min.
        """
        scratch_dir = self.get_scratch_space()
        file_name = os.path.join(scratch_dir, "SampleBidAskDataWide.csv")
        # Data has 2 levels in wide format.
        data = pd.read_csv(file_name)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data = data.set_index("timestamp")
        # Run Resampling
        actual_df = data.groupby("currency_pair").apply(
            lambda group: imvcdttrut.resample_multilevel_bid_ask_data_to_1min(
                group, number_levels_of_order_book=2
            )
        )
        actual = hpandas.df_to_str(actual_df)
        self.check_string(actual)

    def test_resample_multisymbol_multilevel_bid_ask_data_to_1min(self) -> None:
        """
        Verify that multisymbol multilevel raw data 200ms is correctly
        resampled to 1min.
        """
        scratch_dir = self.get_scratch_space()
        file_name = os.path.join(scratch_dir, "SampleBidAskDataWide.csv")
        # Data has 2 levels in wide format.
        data = pd.read_csv(file_name)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data.set_index("timestamp", inplace=True)
        # Run Resampling.
        actual_df = (
            imvcdttrut.resample_multisymbol_multilevel_bid_ask_data_to_1min(
                data, number_levels_of_order_book=2
            )
        )
        actual = hpandas.df_to_str(actual_df)
        self.check_string(actual)

    def _get_test_data(self) -> None:
        """
        Copy bid-ask data from S3 to a scratch dir.
        """
        s3_input_dir = self.get_s3_input_dir(use_only_test_class=True)
        scratch_dir = self.get_scratch_space()
        aws_profile = "ck"
        hs3.copy_data_from_s3_to_local_dir(s3_input_dir, scratch_dir, aws_profile)
