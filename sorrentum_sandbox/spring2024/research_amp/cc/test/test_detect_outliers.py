import numpy as np
import pandas as pd

import helpers.hunit_test as hunitest
import research_amp.cc.detect_outliers as raccdeou


class TestDetectOutliers(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for one 0 in data.
        """
        # Get test series and set outliers.
        test_srs = self._helper()
        test_srs.iloc[200] = 0
        # Compute actual outcome and compare to expected.
        actual = raccdeou.detect_outliers(test_srs, 100, 3)
        expected = np.array([False] * 200 + [True] + [False] * 799)
        self.assert_equal(str(actual), str(expected))

    def test2(self) -> None:
        """
        Test for two consecutive 0 in data.
        """
        # Get test series and set outliers.
        test_srs = self._helper()
        test_srs.iloc[200:202] = 0
        # Compute actual outcome and compare to expected.
        actual = raccdeou.detect_outliers(test_srs, 100, 3)
        expected = np.array([False] * 200 + [True] * 2 + [False] * 798)
        self.assert_equal(str(actual), str(expected))

    def test3(self) -> None:
        """
        Test for three consecutive 0 in data.
        """
        # Get test series and set outliers.
        test_srs = self._helper()
        test_srs.iloc[200:203] = 0
        # Compute actual outcome and compare to expected.
        actual = raccdeou.detect_outliers(test_srs, 100, 3)
        expected = np.array([False] * 200 + [True] * 3 + [False] * 797)
        self.assert_equal(str(actual), str(expected))

    def test4(self) -> None:
        """
        Test for consecutive 0 and 1000 in data.
        """
        # Get test series and set outliers.
        test_srs = self._helper()
        test_srs.iloc[200] = 0
        test_srs.iloc[201] = 1000
        # Compute actual outcome and compare to expected.
        actual = raccdeou.detect_outliers(test_srs, 100, 3)
        expected = np.array([False] * 200 + [True] * 2 + [False] * 798)
        self.assert_equal(str(actual), str(expected))

    @staticmethod
    def _helper() -> pd.Series:
        """
        Get series for test.
        """
        data = np.random.uniform(0, 1, 1000).cumsum()
        index = (
            pd.date_range(end=pd.Timestamp("2021-11-11"), freq="D", periods=1000)
            .to_pydatetime()
            .tolist()
        )
        #
        np.random.seed(42)
        srs = pd.Series(data=data, index=index)
        return srs
