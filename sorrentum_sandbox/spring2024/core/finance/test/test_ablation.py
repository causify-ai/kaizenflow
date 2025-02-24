import datetime
import io
import logging

import pandas as pd

import core.artificial_signal_generators as carsigen
import core.finance.ablation as cfinabla
import helpers.hunit_test as hunitest
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


class Test_set_non_ath_to_nan1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for active trading hours in [9:30, 16:00].
        """
        df = self._get_df()
        start_time = datetime.time(9, 30)
        end_time = datetime.time(16, 0)
        act = cfinabla.set_non_ath_to_nan(df, start_time=start_time, end_time=end_time)
        exp = """
                              open   high    low  close        vol
        datetime
        2016-01-05 09:28:00    NaN    NaN    NaN    NaN        NaN
        2016-01-05 09:29:00    NaN    NaN    NaN    NaN        NaN
        2016-01-05 09:30:00    NaN    NaN    NaN    NaN        NaN
        2016-01-05 09:31:00  98.01  98.19  98.00  98.00   172584.0
        2016-01-05 09:32:00  97.99  98.04  97.77  97.77   189058.0
        2016-01-05 15:58:00  95.31  95.32  95.22  95.27   456235.0
        2016-01-05 15:59:00  95.28  95.36  95.22  95.32   729315.0
        2016-01-05 16:00:00  95.32  95.40  95.32  95.40  3255752.0
        2016-01-05 16:01:00    NaN    NaN    NaN    NaN        NaN
        2016-01-05 16:02:00    NaN    NaN    NaN    NaN        NaN
        """
        self.assert_equal(str(act), exp, fuzzy_match=True)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,open,high,low,close,vol
2016-01-05 09:28:00,98.0,98.05,97.99,98.05,2241
2016-01-05 09:29:00,98.04,98.13,97.97,98.13,14174
2016-01-05 09:30:00,98.14,98.24,97.79,98.01,751857
2016-01-05 09:31:00,98.01,98.19,98.0,98.0,172584
2016-01-05 09:32:00,97.99,98.04,97.77,97.77,189058
2016-01-05 15:58:00,95.31,95.32,95.22,95.27,456235
2016-01-05 15:59:00,95.28,95.36,95.22,95.32,729315
2016-01-05 16:00:00,95.32,95.4,95.32,95.4,3255752
2016-01-05 16:01:00,95.4,95.42,95.4,95.42,4635
2016-01-05 16:02:00,95.41,95.41,95.37,95.4,3926
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df


class Test_remove_times_outside_window(hunitest.TestCase):
    def test_remove(self) -> None:
        df = self._get_df()
        start_time = datetime.time(9, 29)
        end_time = datetime.time(16, 0)
        actual = cfinabla.remove_times_outside_window(df, start_time, end_time)
        expected_txt = """
datetime,open,high,low,close,vol
2016-01-05 09:30:00,98.14,98.24,97.79,98.01,751857
2016-01-05 09:31:00,98.01,98.19,98.0,98.0,172584
2016-01-05 09:32:00,97.99,98.04,97.77,97.77,189058
2016-01-05 15:58:00,95.31,95.32,95.22,95.27,456235
2016-01-05 15:59:00,95.28,95.36,95.22,95.32,729315
2016-01-05 16:00:00,95.32,95.4,95.32,95.4,3255752
        """
        expected = pd.read_csv(
            io.StringIO(expected_txt), index_col=0, parse_dates=True
        )
        self.assert_dfs_close(actual, expected)

    def test_bypass(self) -> None:
        df = self._get_df()
        start_time = datetime.time(9, 29)
        end_time = datetime.time(16, 0)
        actual = cfinabla.remove_times_outside_window(
            df, start_time, end_time, bypass=True
        )
        self.assert_dfs_close(actual, df)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,open,high,low,close,vol
2016-01-05 09:28:00,98.0,98.05,97.99,98.05,2241
2016-01-05 09:29:00,98.04,98.13,97.97,98.13,14174
2016-01-05 09:30:00,98.14,98.24,97.79,98.01,751857
2016-01-05 09:31:00,98.01,98.19,98.0,98.0,172584
2016-01-05 09:32:00,97.99,98.04,97.77,97.77,189058
2016-01-05 15:58:00,95.31,95.32,95.22,95.27,456235
2016-01-05 15:59:00,95.28,95.36,95.22,95.32,729315
2016-01-05 16:00:00,95.32,95.4,95.32,95.4,3255752
2016-01-05 16:01:00,95.4,95.42,95.4,95.42,4635
2016-01-05 16:02:00,95.41,95.41,95.37,95.4,3926
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df


class Test_set_weekends_to_nan(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for a daily frequency input.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=2, seed=1)
        df = mn_process.generate_sample(
            {"start": "2020-01-01", "periods": 40, "freq": "D"}, seed=1
        )
        actual = cfinabla.set_weekends_to_nan(df)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test for a minutely frequency input.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=2, seed=1)
        df = mn_process.generate_sample(
            {"start": "2020-01-05 23:00:00", "periods": 100, "freq": "T"}, seed=1
        )
        actual = cfinabla.set_weekends_to_nan(df)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)


class Test_remove_weekends(hunitest.TestCase):
    def test_remove(self) -> None:
        df = self._get_df()
        actual = cfinabla.remove_weekends(df)
        expected_txt = """
datetime,close,volume
2016-01-01,NaN,NaN
2016-01-04,100.00,100000
2016-01-05,100.00,100000
2016-01-06,100.00,100000
2016-01-07,100.00,100000
2016-01-08,100.00,100000
2016-01-11,100.00,100000
2016-01-12,100.00,100000
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt), index_col=0, parse_dates=True
        )
        self.assert_dfs_close(actual, expected)

    def test_bypass(self) -> None:
        df = self._get_df()
        actual = cfinabla.remove_weekends(df, bypass=True)
        self.assert_dfs_close(actual, df)

    @staticmethod
    def _get_df() -> pd.DataFrame:
        txt = """
datetime,close,volume
2016-01-01,NaN,NaN
2016-01-02,NaN,NaN
2016-01-03,NaN,NaN
2016-01-04,100.00,100000
2016-01-05,100.00,100000
2016-01-06,100.00,100000
2016-01-07,100.00,100000
2016-01-08,100.00,100000
2016-01-09,100.00,100000
2016-01-10,100.00,100000
2016-01-11,100.00,100000
2016-01-12,100.00,100000
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df
