import datetime

import numpy as np
import pandas as pd

import helpers.hunit_test as hunitest
import im_v2.common.data.qa.qa_check as imvcdqqach


class QAChecksTestCase(hunitest.TestCase):
    @staticmethod
    def _get_data(start_timestamp: pd.Timestamp, minutes: int) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timestamp": start_timestamp
                    + datetime.timedelta(minutes=minutes_delta),
                    "open": 0.4055,
                    "high": 0.4056,
                    "low": 0.4049,
                    "close": 0.4049,
                    "volume": 65023.8,
                    "currency_pair": "BTC_USDT",
                }
                for minutes_delta in range(minutes + 1)
            ]
        )


class TestGapsInTimeIntervalCheck(QAChecksTestCase):
    def test_main(self):
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        end_timestamp = start_timestamp + datetime.timedelta(minutes=minutes)
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Check.
        check_instance = imvcdqqach.GapsInTimeIntervalCheck(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            data_frequency="T",
        )
        check_result = check_instance.check(datasets=[data])
        self.assertTrue(check_result)

    def test_corner_case(self):
        """
        Test that check of a dataset with a gap (missing rows) in timestamp
        values will be failed.
        """
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        end_timestamp = start_timestamp + datetime.timedelta(minutes=minutes)
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Remove random elements to create a gap.
        np.random.seed(10)
        drop_indices = np.random.choice(data.index, 3, replace=False)
        data_with_timestamp_gaps = data.drop(drop_indices)
        # Check.
        check_instance = imvcdqqach.GapsInTimeIntervalCheck(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            data_frequency="T",
        )
        check_result = check_instance.check(datasets=[data_with_timestamp_gaps])
        self.assertFalse(check_result)


class TestGapsInTimeIntervalBySymbolsCheck(QAChecksTestCase):
    def test_main(self):
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        end_timestamp = start_timestamp + datetime.timedelta(minutes=minutes)
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Check.
        check_instance = imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            data_frequency="T",
        )
        check_result = check_instance.check(datasets=[data])
        self.assertTrue(check_result)

    def test_corner_case(self):
        """
        Test that check of a dataset with a gap (missing rows by symbols in
        timestamp values will be failed.
        """
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        end_timestamp = start_timestamp + datetime.timedelta(minutes=minutes)
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Remove random elements to create a gap.
        np.random.seed(10)
        drop_indices = np.random.choice(data.index, 3, replace=False)
        data_with_timestamp_gaps = data.drop(drop_indices)
        # Check.
        check_instance = imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            data_frequency="T",
        )
        check_result = check_instance.check(datasets=[data_with_timestamp_gaps])
        self.assertFalse(check_result)
        self.assertIn("BTC_USDT", check_instance.get_status())


class TestNaNChecks(QAChecksTestCase):
    def test_main(self):
        # Get the data.
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=120)
        # Check.
        check_result = imvcdqqach.NaNChecks(
            fields=["open", "high", "low", "close", "volume"]
        ).check(datasets=[data])
        self.assertTrue(check_result)

    def test_corner_case(self):
        """
        Test that check of a dataset with NaN values will be failed.
        """
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Assign random fields values to NaN.
        np.random.seed(10)
        data.loc[
            np.random.randint(low=1, high=minutes, size=10),
            ["open", "high", "low", "close", "volume"],
        ] = np.NaN
        # Check.
        check_result = imvcdqqach.NaNChecks(
            fields=["open", "high", "low", "close", "volume"]
        ).check(datasets=[data])
        self.assertFalse(check_result)


class TestOhlcvLogicalValuesCheck(QAChecksTestCase):
    def test_main(self):
        # Get the data.
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=120)
        # Check.
        check_result = imvcdqqach.OhlcvLogicalValuesCheck().check(datasets=[data])
        self.assertTrue(check_result)

    def test_corner_case(self):
        """
        Test that check of a dataset with a couple logical mistakes, will be
        failed.
        """
        # Get the data.
        minutes = 120
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=minutes)
        # Assign random valumes to 0.
        # TODO(Juraj): this test is temporarily disabled since it's turned off.
        # data_with_0_volume = data.copy()
        # data_with_0_volume.loc[
        #    np.random.randint(low=1, high=minutes, size=10), ["volume"]
        # ] = 0
        ## Check.
        # check_result = imvcdqqach.OhlcvLogicalValuesCheck().check(
        #    datasets=[data_with_0_volume]
        # )
        # self.assertFalse(check_result)
        # Assign random high values to wrong small values.
        high_lt_low = data.copy()
        high_lt_low.loc[
            np.random.randint(low=1, high=minutes, size=10), ["high"]
        ] = 0.001
        # Check.
        check_result = imvcdqqach.OhlcvLogicalValuesCheck().check(
            datasets=[high_lt_low]
        )
        self.assertFalse(check_result)


class TestFullUniversePresentCheck(QAChecksTestCase):
    def test_main(self):
        # Get the data.
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=2)
        universe = ["BTC_USDT"]
        # Check.
        check_result = imvcdqqach.FullUniversePresentCheck(universe).check([data])
        self.assertTrue(check_result)

    def test_corner_case(self):
        """
        Test that dataset with a missing symbol in a universe will fail.
        """
        # Get the data.
        start_timestamp = pd.Timestamp(datetime.datetime(2000, 1, 1))
        data = self._get_data(start_timestamp=start_timestamp, minutes=2)
        universe = ["BTC_USDT", "ETH_USDT"]
        # Check.
        check_result = imvcdqqach.FullUniversePresentCheck(universe).check([data])
        self.assertFalse(check_result)


class TestIdenticalDataFramesCheck(QAChecksTestCase):
    def test_identical_datasets(self):
        """
        Assert that IdenticalDataFramesCheck correctly identifies two
        DataFrames with no differences as identical.
        """
        # Prepare data.
        start_timestamp = pd.Timestamp("2023-01-15T00:00:00+00:00")
        dataset = self._get_data(start_timestamp, 5)
        # Check result.
        check_instance = imvcdqqach.IdenticalDataFramesCheck()
        check_result = check_instance.check([dataset, dataset])
        self.assertTrue(check_result)
        self.assertIn("PASSED", check_instance.get_status())

    def test_different_datasets(self):
        """
        Assert that IdenticalDataFramesCheck correctly identifies two
        DataFrames with differences as not identical.
        """
        # Prepare data.
        start_timestamp = pd.Timestamp("2023-01-15T00:00:00+00:00")
        dataset1 = self._get_data(start_timestamp, 5)
        dataset2 = self._get_data2(start_timestamp, 5)
        # Check result.
        check_instance = imvcdqqach.IdenticalDataFramesCheck()
        check_result = check_instance.check([dataset1, dataset2])
        self.assertFalse(check_result)
        self.assertIn("FAILED", check_instance.get_status())

    @staticmethod
    def _get_data2(start_timestamp: pd.Timestamp, minutes: int) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timestamp": start_timestamp
                    + datetime.timedelta(minutes=minutes_delta),
                    "open": 0.4655,
                    "high": 0.3956,
                    "low": 0.3749,
                    "close": 0.4049,
                    "volume": 65023.8,
                    "currency_pair": "BTC_USDT",
                }
                for minutes_delta in range(minutes + 1)
            ]
        )


class TestDuplicateDifferingOhlcvCheck(QAChecksTestCase):
    def test_duplicates_with_same_ohlcv(self) -> None:
        """
        Test case to check for records with identical ohlcv values
        along with identical `timestamp` and `currecny_pair`.
        """
        # Prepare data.
        start_timestamp = pd.Timestamp("2023-01-15T00:00:00+00:00")
        data_len = 5
        dataset = self._get_data(start_timestamp, data_len)
        dataset = pd.concat([dataset, dataset])
        # Execute.
        check_instance = imvcdqqach.DuplicateDifferingOhlcvCheck()
        check_result = check_instance.check([dataset])
        # Check results.
        self.assertTrue(check_result)
        self.assertIn("PASSED", check_instance.get_status())

    def test_no_duplicates(self) -> None:
        """
        Test case to assert that no duplicates are present.
        """
        # Prepare data.
        start_timestamp = pd.Timestamp("2023-01-15T00:00:00+00:00")
        data_len = 5
        dataset = self._get_data(start_timestamp, data_len)
        # Execute.
        check_instance = imvcdqqach.DuplicateDifferingOhlcvCheck()
        check_result = check_instance.check([dataset])
        # Check results.
        self.assertTrue(check_result)
        self.assertIn("PASSED", check_instance.get_status())
    
    def test_duplicates_with_different_ohlcv(self) -> None:
        """
        Test case to check for records with the same 'timestamp' 
        and 'currency_pair' values, but differing OHLCV data.
        """
        # Prepare data.
        start_timestamp = pd.Timestamp("2023-01-15T00:00:00+00:00")
        data_len = 5
        dataset = self._get_data(start_timestamp, data_len)
        dataset_copy = dataset.copy()
        dataset = pd.concat([dataset, dataset_copy], ignore_index=True)
        # Change one value in a row.
        row_num = 5
        dataset.loc[row_num, "volume"] = 100
        # Execute.
        check_instance = imvcdqqach.DuplicateDifferingOhlcvCheck()
        check_result = check_instance.check([dataset])
        # Check results.
        self.assertFalse(check_result)
        self.assertIn("FAILED", check_instance.get_status())
