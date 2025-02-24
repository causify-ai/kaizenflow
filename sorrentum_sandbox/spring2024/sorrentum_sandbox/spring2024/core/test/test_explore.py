import logging

import numpy as np
import pandas as pd
import pytest

import core.explore as coexplor
import helpers.hdatetime as hdateti
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_explore1(hunitest.TestCase):
    def test_ols_regress_series(self) -> None:
        x = 5 * np.random.randn(100)
        y = x + np.random.randn(*x.shape)
        df = pd.DataFrame()
        df["x"] = x
        df["y"] = y
        coexplor.ols_regress_series(
            df["x"], df["y"], intercept=True, print_model_stats=False
        )

    @pytest.mark.skip(reason="https://github.com/.../.../issues/3676")
    def test_rolling_pca_over_time1(self) -> None:
        np.random.seed(42)
        df = pd.DataFrame(np.random.randn(10, 5))
        df.index = pd.date_range("2017-01-01", periods=10)
        corr_df, eigval_df, eigvec_df = coexplor.rolling_pca_over_time(
            df, 0.5, "fill_with_zero"
        )
        txt = (
            "corr_df=\n%s\n" % corr_df.to_string()
            + "eigval_df=\n%s\n" % eigval_df.to_string()
            + "eigvec_df=\n%s\n" % eigvec_df.to_string()
        )
        self.check_string(txt)


class TestFilterByTime(hunitest.TestCase):
    def test_filter_by_index1(self) -> None:
        """
        Verify that `[lower_bound, upper_bound)` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2017-01-02")
        upper_bound = hdateti.to_datetime("2017-01-04")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="left",
            ts_col_name=None,
        )
        expected = df[1:3]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_index2(self) -> None:
        """
        Verify that `(lower_bound, upper_bound]` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2017-01-02")
        upper_bound = hdateti.to_datetime("2017-01-04")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="right",
            ts_col_name=None,
        )
        expected = df[2:4]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_index3(self) -> None:
        """
        Verify that `[lower_bound, upper_bound]` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2017-01-02")
        upper_bound = hdateti.to_datetime("2017-01-04")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="both",
            ts_col_name=None,
        )
        expected = df[1:4]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_index4(self) -> None:
        """
        Verify that `(lower_bound, upper_bound)` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2017-01-02")
        upper_bound = hdateti.to_datetime("2017-01-04")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="neither",
            ts_col_name=None,
        )
        expected = df[2:3]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_column1(self) -> None:
        """
        Verify that `[lower_bound, upper_bound)` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2018-04-06")
        upper_bound = hdateti.to_datetime("2018-04-08")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="left",
            ts_col_name="col2",
        )
        expected = df[1:3]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_column2(self) -> None:
        """
        Verify that `(lower_bound, upper_bound]` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2018-04-06")
        upper_bound = hdateti.to_datetime("2018-04-08")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="right",
            ts_col_name="col2",
        )
        expected = df[2:4]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_column3(self) -> None:
        """
        Verify that `[lower_bound, upper_bound]` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2018-04-06")
        upper_bound = hdateti.to_datetime("2018-04-08")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="both",
            ts_col_name="col2",
        )
        expected = df[1:4]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_filter_by_column4(self) -> None:
        """
        Verify that `(lower_bound, upper_bound)` works.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2018-04-06")
        upper_bound = hdateti.to_datetime("2018-04-08")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="neither",
            ts_col_name="col2",
        )
        expected = df[2:3]
        self.assert_equal(actual.to_string(), expected.to_string())

    def test_no_intersection(self) -> None:
        """
        Verify that if time interval is not covered by data then empty
        DataFrame is returned.
        """
        df = self._get_test_data()
        lower_bound = hdateti.to_datetime("2021-04-06")
        upper_bound = hdateti.to_datetime("2021-04-08")
        actual = coexplor.filter_by_time(
            df=df,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            inclusive="both",
            ts_col_name=None,
        )
        self.assertEqual(actual.shape[0], 0)

    @staticmethod
    def _get_test_data() -> pd.DataFrame:
        """
        Get data for testing.

        :return: data for testing
        """
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3, 4],
                "col2": [
                    hdateti.to_datetime("2018-04-05"),
                    hdateti.to_datetime("2018-04-06"),
                    hdateti.to_datetime("2018-04-07"),
                    hdateti.to_datetime("2018-04-08"),
                ],
            }
        )
        df.index = pd.date_range("2017-01-01", periods=4)
        return df
