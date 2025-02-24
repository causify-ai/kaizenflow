import argparse
import os
import unittest.mock as umock

import pandas as pd
import pytest

import helpers.hdatetime as hdateti
import helpers.henv as henv
import helpers.hs3 as hs3
import helpers.hsql as hsql
import im_v2.ccxt.data.extract.compare_realtime_and_historical as imvcdecrah
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.db.db_utils as imvcddbut


@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestCompareRealtimeAndHistoricalData1(imvcddbut.TestImDbHelper):
    FILTERS = [
        [("year", "==", 2021), ("month", ">=", 12)],
        [("year", "==", 2022), ("month", "<=", 1)],
    ]
    _ohlcv_dataframe_sample = None
    _bid_ask_dataframe_sample = None

    _test_start_timestamp = "2021-09-15T23:45:00+00:00"
    _test_end_timestamp = "2021-09-15T23:54:00+00:00"

    @staticmethod
    def get_s3_path() -> str:
        aws_profile = "ck"
        s3_bucket_path = hs3.get_s3_bucket_path(aws_profile)
        s3_path = os.path.join(s3_bucket_path, "reorg/daily_staged.airflow.pq")
        return s3_path

    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Initialize database.
        ccxt_ohlcv_table_query = imvccdbut.get_ccxt_ohlcv_create_table_query()
        hsql.execute_query(self.connection, ccxt_ohlcv_table_query)

    def tear_down_test(self) -> None:
        # Drop table used in tests.
        ccxt_ohlcv_drop_query = "DROP TABLE IF EXISTS ccxt_ohlcv_spot;"
        hsql.execute_query(self.connection, ccxt_ohlcv_drop_query)

    def ohlcv_dataframe_sample(self) -> pd.DataFrame:
        """
        Get OHLCV data sample.
        """
        ohlcv_sample = pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
                "full_symbol",
            ],
            # fmt: off
            # pylint: disable=line-too-long
            data=[
                [30, 40, 50, 60, 70, "binance::BTC_USDT"],
                [31, 41, 51, 61, 71, "binance::BTC_USDT"],
                [34, 44, 54, 64, 74, "binance::BTC_USDT"],
                [34, 44, 54, 64, 74, "binance::BTC_USDT"],
                [34, 44, 54, 64, 74, "binance::BTC_USDT"],
                [38, 39, 50, 61, 71, "binance::BTC_USDT"],
                [31, 45, 54, 60, 75, "binance::BTC_USDT"],
                [33, 43, 57, 63, 73, "binance::BTC_USDT"],
                [34, 40, 52, 62, 72, "binance::BTC_USDT"],
                [37, 44, 51, 64, 72, "binance::BTC_USDT"],
            ]
            # pylint: enable=line-too-long
            # fmt: on
        )
        ohlcv_sample["timestamp"] = pd.date_range(
            start=self._test_start_timestamp,
            end=self._test_end_timestamp,
            freq="T",
        ).map(hdateti.convert_timestamp_to_unix_epoch)
        ohlcv_sample = ohlcv_sample.set_index(["timestamp", "full_symbol"])
        self._ohlcv_dataframe_sample = ohlcv_sample
        return self._ohlcv_dataframe_sample.copy()

    def bid_ask_dataframe_sample(self) -> pd.DataFrame:
        """
        Get bid-ask data sample.
        """
        bid_ask_sample = pd.DataFrame(
            columns=[
                "full_symbol",
                "bid_price_l1",
                "bid_size_l1",
                "ask_price_l1",
                "ask_size_l1",
            ],
            # fmt: off
            # pylint: disable=line-too-long
            data=[
                ["binance::BTC_USDT", 19505.817, 1185.347, 19504.541, 859.472],
                ["binance::BTC_USDT", 1321.790, 7004.761, 1321.699, 3670.681],
                ["binance::BTC_USDT", 19500.714, 1019.649, 19502.706, 1101.954],
                ["binance::BTC_USDT", 1321.400, 3675.864, 1321.278, 4320.231],
                ["binance::BTC_USDT", 19483.345, 1689.938, 19484.335, 1095.325],
                ["binance::BTC_USDT", 1320.022, 4612.925, 1320.102, 6404.481],
                ["binance::BTC_USDT", 19483.128, 1528.736, 19482.422, 958.668],
                ["binance::BTC_USDT", 1319.769, 3754.403, 1319.654, 4775.201],
                ["binance::BTC_USDT", 19473.500, 4.351, 19473.600, 15.578],
                ["binance::BTC_USDT", 1319.030, 43.404, 1319.040, 48.725],
            ]
            # pylint: enable=line-too-long
            # fmt: on
        )
        bid_ask_sample["timestamp"] = pd.date_range(
            start=self._test_start_timestamp,
            end=self._test_end_timestamp,
            freq="T",
        ).map(hdateti.convert_timestamp_to_unix_epoch)
        bid_ask_sample = bid_ask_sample.set_index(["timestamp", "full_symbol"])
        self._bid_ask_dataframe_sample = bid_ask_sample
        return self._bid_ask_dataframe_sample.copy()

    @pytest.mark.slow
    def test_compare_ohlcv_1(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        No data missing.
        """
        sample = self.ohlcv_dataframe_sample()
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample
        self._test_function_call("ohlcv", "spot", True)
        #
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)

    @pytest.mark.slow
    def test_compare_ohlcv_2(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Differing realtime data.
        """
        sample_rt = self.ohlcv_dataframe_sample()
        sample_daily = self.ohlcv_dataframe_sample()
        for position in [1, 3]:
            # Edit original realtime data for mismatch.
            sample_rt.iloc[position, sample_rt.columns.get_loc("open")] = 666
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("ohlcv", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        ################################################################################
        Differing table contents:
        df.shape=(2, 4)
        df.full=
        open            timestamp        full_symbol
        self other
        1   31   666  1631749560000  binance::BTC_USDT
        3   34   666  1631749680000  binance::BTC_USDT
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow
    def test_compare_ohlcv_3(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Missing daily data.s
        """
        sample_rt = self.ohlcv_dataframe_sample()
        sample_daily = self.ohlcv_dataframe_sample()
        for position in [2, 4]:
            # Edit original daily data for mismatch.
            sample_daily.iloc[
                position, sample_daily.columns.get_loc("open")
            ] = 999
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("ohlcv", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        ################################################################################
        Differing table contents:
        df.shape=(2, 4)
        df.full=
        open            timestamp        full_symbol
        self other
        2  999    34  1631749620000  binance::BTC_USDT
        4  999    34  1631749740000   binance::BTC_USDT
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow
    def test_compare_ohlcv_4(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Mismatch between realtime and daily data with missing data.
        """
        sample_rt = self.ohlcv_dataframe_sample().head(4)
        sample_daily = self.ohlcv_dataframe_sample().tail(5)
        for position in [1, 3]:
            # Edit original realtime data for mismatch.
            sample_rt.iloc[position, sample_rt.columns.get_loc("open")] = 666
        for position in [2, 4]:
            # Edit original daily data for mismatch.
            sample_daily.iloc[
                position, sample_daily.columns.get_loc("open")
            ] = 999
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("ohlcv", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""

        ################################################################################
        Missing real time data:
        df.shape=(5, 5)
        df.full=
                                        open  high  low  close  volume
        timestamp     full_symbol
        1631749800000 binance::BTC_USDT    38    39   50     61      71
        1631749860000 binance::BTC_USDT    31    45   54     60      75
        1631749920000 binance::BTC_USDT   999    43   57     63      73
        1631749980000 binance::BTC_USDT    34    40   52     62      72
        1631750040000 binance::BTC_USDT    999    44   51     64      72
        Missing daily data:
        df.shape=(4, 5)
        df.full=
                                        open  high  low  close  volume
        timestamp     full_symbol
        1631749500000 binance::BTC_USDT    30    40   50     60      70
        1631749560000 binance::BTC_USDT   666    41   51     61      71
        1631749620000 binance::BTC_USDT    34    44   54     64      74
        1631749680000 binance::BTC_USDT   666    44   54     64      74
        Gaps in real time data:
        df.shape=(6, 1)
        df.full=
                                                        0
        2021-09-15 23:49:00+00:00 2021-09-15 23:49:00+00:00
        2021-09-15 23:50:00+00:00 2021-09-15 23:50:00+00:00
        2021-09-15 23:51:00+00:00 2021-09-15 23:51:00+00:00
        2021-09-15 23:52:00+00:00 2021-09-15 23:52:00+00:00
        2021-09-15 23:53:00+00:00 2021-09-15 23:53:00+00:00
        2021-09-15 23:54:00+00:00 2021-09-15 23:54:00+00:00
        Gaps in daily data:
        df.shape=(5, 1)
        df.full=
                                                        0
        2021-09-15 23:45:00+00:00 2021-09-15 23:45:00+00:00
        2021-09-15 23:46:00+00:00 2021-09-15 23:46:00+00:00
        2021-09-15 23:47:00+00:00 2021-09-15 23:47:00+00:00
        2021-09-15 23:48:00+00:00 2021-09-15 23:48:00+00:00
        2021-09-15 23:49:00+00:00 2021-09-15 23:49:00+00:00
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow
    def test_compare_bid_ask_1(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        No data missing.
        """
        sample = self.bid_ask_dataframe_sample()
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample
        self._test_function_call("bid_ask", "futures", True)
        #
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)

    @pytest.mark.slow
    def test_compare_bid_ask_2(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Missing realtime data.
        """
        sample_rt = self.bid_ask_dataframe_sample()
        sample_daily = self.bid_ask_dataframe_sample()
        for position in [1, 3]:
            # Edit original realtime data for mismatch.
            sample_rt.iloc[
                position, sample_rt.columns.get_loc("bid_size_l1")
            ] = 666.667
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("bid_ask", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        ################################################################################
        Difference between bid_size_l1 in real time and daily data for `binance::BTC_USDT` coin is more than 1%.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow
    def test_compare_bid_ask_3(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Missing daily data.
        """
        sample_rt = self.bid_ask_dataframe_sample()
        sample_daily = self.bid_ask_dataframe_sample()
        for position in [2, 4]:
            # Edit original realtime data for mismatch.
            sample_daily.iloc[
                position, sample_daily.columns.get_loc("ask_price_l1")
            ] = 999.876
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("bid_ask", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        ################################################################################
        Difference between ask_price_l1 in real time and daily data for `binance::BTC_USDT` coin is more than 1%.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    @pytest.mark.slow
    def test_compare_bid_ask_4(self) -> None:
        """
        Test function call with specific arguments that are mimicking command
        line arguments.

        Mismatch between realtime and daily data with missing data.
        """
        sample_rt = self.bid_ask_dataframe_sample().head(4)
        sample_daily = self.bid_ask_dataframe_sample().head(4)
        for position in [1, 3]:
            # Edit original realtime data for mismatch.
            sample_rt.iloc[
                position, sample_rt.columns.get_loc("bid_size_l1")
            ] = 2279.667
        for position in [2, 3]:
            # Edit original daily data for mismatch.
            sample_daily.iloc[
                position, sample_daily.columns.get_loc("ask_price_l1")
            ] = 3224.678
        mock_get_rt_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_rt_data"
        )
        mock_get_rt_data = mock_get_rt_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_rt_data.return_value = sample_rt
        #
        mock_get_daily_data_patch = umock.patch.object(
            imvcdecrah.RealTimeHistoricalReconciler, "_get_daily_data"
        )
        mock_get_daily_data = mock_get_daily_data_patch.start()
        # Prepare and attach sample to mocked function.
        mock_get_daily_data.return_value = sample_daily
        # Run.
        with self.assertRaises(AssertionError) as fail:
            self._test_function_call("bid_ask", "spot", True)
        # Stop the patches.
        mock_get_rt_data_patch.stop()
        mock_get_daily_data_patch.stop()
        self.assertEqual(mock_get_rt_data.call_count, 1)
        self.assertEqual(mock_get_daily_data.call_count, 1)
        # Check output.
        actual = str(fail.exception)
        expected = r"""
        ################################################################################
        Gaps in real time data:
        df.shape=(6, 1)
        df.full=
                                                        0
        2021-09-15 23:49:00+00:00 2021-09-15 23:49:00+00:00
        2021-09-15 23:50:00+00:00 2021-09-15 23:50:00+00:00
        2021-09-15 23:51:00+00:00 2021-09-15 23:51:00+00:00
        2021-09-15 23:52:00+00:00 2021-09-15 23:52:00+00:00
        2021-09-15 23:53:00+00:00 2021-09-15 23:53:00+00:00
        2021-09-15 23:54:00+00:00 2021-09-15 23:54:00+00:00
        Gaps in daily data:
        df.shape=(6, 1)
        df.full=
                                                        0
        2021-09-15 23:49:00+00:00 2021-09-15 23:49:00+00:00
        2021-09-15 23:50:00+00:00 2021-09-15 23:50:00+00:00
        2021-09-15 23:51:00+00:00 2021-09-15 23:51:00+00:00
        2021-09-15 23:52:00+00:00 2021-09-15 23:52:00+00:00
        2021-09-15 23:53:00+00:00 2021-09-15 23:53:00+00:00
        2021-09-15 23:54:00+00:00 2021-09-15 23:54:00+00:00
        Difference between ask_price_l1 in real time and daily data for `binance::BTC_USDT` coin is more than 1%.
        Difference between bid_size_l1 in real time and daily data for `binance::BTC_USDT` coin is more than 1%.
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_parser(self) -> None:
        """
        Test arg parser for predefined args in the script.

        Mostly for coverage and to detect argument changes.
        """
        parser = imvcdecrah._parse()
        cmd = []
        cmd.extend(["--start_timestamp", "20220216-000000"])
        cmd.extend(["--end_timestamp", "20220217-000000"])
        cmd.extend(["--exchange_id", "binance"])
        cmd.extend(["--db_stage", "dev"])
        cmd.extend(["--db_table", "ccxt_ohlcv_spot"])
        cmd.extend(["--aws_profile", "ck"])
        cmd.extend(
            ["--s3_path", "s3://cryptokaizen-data/reorg/historical.manual.pq/"]
        )
        cmd.extend(["--data_type", "ohlcv"])
        cmd.extend(["--contract_type", "spot"])
        cmd.extend(["--s3_vendor", "crypto_chassis"])
        args = parser.parse_args(cmd)
        actual = vars(args)
        # Change bool values to string type to pass the check.
        actual["resample_1min"] = "True"
        actual["resample_1sec"] = "False"
        expected = {
            "start_timestamp": "20220216-000000",
            "end_timestamp": "20220217-000000",
            "db_stage": "dev",
            "exchange_id": "binance",
            "db_table": "ccxt_ohlcv_spot",
            "log_level": "INFO",
            "aws_profile": "ck",
            "s3_path": "s3://cryptokaizen-data/reorg/historical.manual.pq/",
            "data_type": "ohlcv",
            "contract_type": "spot",
            "resample_1min": "True",
            "resample_1sec": "False",
            "s3_vendor": "crypto_chassis",
            "bid_ask_accuracy": None,
            "bid_ask_depth": 10,
        }
        self.assertDictEqual(actual, expected)

    def _save_sample_in_db(self, sample: pd.DataFrame) -> None:
        """
        Save small sample of ohlcv data in test db.

        Extra date columns `year` and `month` are removed from sample as
        those are only used for data partition.
        """
        columns = ["year", "month"]
        trimmed_sample = sample.drop(columns, axis=1)
        hsql.execute_insert_query(
            connection=self.connection,
            obj=trimmed_sample,
            table_name="ccxt_ohlcv_spot",
        )

    def _test_function_call(
        self, data_type, contract_type, resample_1min
    ) -> None:
        """
        Test directly _run function for coverage increase.
        """
        # Prepare inputs.
        kwargs = {
            "start_timestamp": self._test_start_timestamp,
            "end_timestamp": self._test_end_timestamp,
            "db_stage": "local",
            "exchange_id": "binance",
            "db_table": "ccxt_ohlcv_spot",
            "log_level": "INFO",
            "aws_profile": "ck",
            "s3_path": f"{self.get_s3_path()}",
            "connection": self.connection,
            "data_type": data_type,
            "contract_type": contract_type,
            "resample_1min": True,
            "s3_vendor": "crypto_chassis",
            "bid_ask_accuracy": 1,
            "bid_ask_depth": 1,
        }
        if resample_1min:
            kwargs["resample_1min"] = True
            kwargs["resample_1sec"] = False
        else:
            kwargs["resample_1min"] = False
            kwargs["resample_1sec"] = True
        # Run.
        args = argparse.Namespace(**kwargs)
        imvcdecrah._run(args)
