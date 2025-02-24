import io
import logging

import numpy as np
import pandas as pd

import core.signal_processing.cross_sectional as csprcrse
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_gaussian_rank1(hunitest.TestCase):
    @staticmethod
    def get_data(num_cols: int, seed: int) -> pd.DataFrame:
        date_range = pd.date_range(
            start=pd.Timestamp("2022-01-04 09:30", tz="America/New_York"),
            end=pd.Timestamp("2022-01-04 11:30", tz="America/New_York"),
            freq="15T",
        )
        rng = np.random.default_rng(seed=seed)
        vals = rng.uniform(size=(len(date_range), num_cols))
        df = pd.DataFrame(vals, date_range)
        return df

    def test_gaussian_rank(self) -> None:
        df = self.get_data(num_cols=5, seed=1)
        _LOG.debug("df=\n%s", df)
        actual = csprcrse.gaussian_rank(df)
        precision = 2
        actual_str = hpandas.df_to_str(
            actual.round(precision), num_rows=None, precision=precision
        )
        expected_str = r"""
                              0    1     2     3     4
2022-01-04 09:30:00-05:00  0.00  5.2 -5.20  0.67 -0.67
2022-01-04 09:45:00-05:00  0.00  5.2 -0.67  0.67 -5.20
2022-01-04 10:00:00-05:00  0.67  0.0 -0.67  5.20 -5.20
2022-01-04 10:15:00-05:00  5.20 -5.2  0.67 -0.67  0.00
2022-01-04 10:30:00-05:00  0.00 -5.2 -0.67  5.20  0.67
2022-01-04 10:45:00-05:00  0.67  0.0 -0.67 -5.20  5.20
2022-01-04 11:00:00-05:00 -0.67 -5.2  0.67  5.20  0.00
2022-01-04 11:15:00-05:00  5.20 -5.2  0.67  0.00 -0.67
2022-01-04 11:30:00-05:00  0.00  5.2 -0.67 -5.20  0.67"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)

    def test_gaussian_rank_3_quantiles(self) -> None:
        df = self.get_data(num_cols=10, seed=1)
        _LOG.debug("df=\n%s", df)
        actual = csprcrse.gaussian_rank(df, n_quantiles=3)
        precision = 2
        actual_str = hpandas.df_to_str(
            actual.round(precision), num_rows=None, precision=precision
        )
        expected_str = r"""
                              0     1     2     3     4     5     6     7     8     9
2022-01-04 09:30:00-05:00  0.12  5.20 -1.11  2.90 -0.46 -0.13  1.14 -0.17  0.21 -5.20
2022-01-04 09:45:00-05:00  1.74  0.53 -0.20  5.20 -0.35  0.26 -5.20  0.11 -1.04 -0.59
2022-01-04 10:00:00-05:00  0.44 -1.14 -0.40  5.20  1.92  0.34 -0.25 -1.16 -5.20  2.16
2022-01-04 10:15:00-05:00 -0.02 -1.41  0.33  0.92  0.29  5.20 -5.20  0.02 -0.16 -1.99
2022-01-04 10:30:00-05:00  0.13  5.20 -0.06 -1.18  1.93 -0.29 -0.29  0.80 -5.20  1.48
2022-01-04 10:45:00-05:00 -0.10  0.48 -1.38  0.64 -1.38 -5.20  1.44  1.61  5.20 -0.53
2022-01-04 11:00:00-05:00 -0.81 -5.20  0.01  0.31  0.84 -0.79 -0.98 -0.01  0.68  5.20
2022-01-04 11:15:00-05:00 -1.26 -0.31  1.72 -0.45 -0.09 -5.20  0.18  5.20  0.99  1.57
2022-01-04 11:30:00-05:00  0.93 -0.46  1.52 -0.63  5.20 -5.20  2.51 -0.92  0.08 -0.13"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)

    def test_gaussian_rank_3_quantiles_middle_removed(self) -> None:
        df = self.get_data(num_cols=10, seed=1)
        _LOG.debug("df=\n%s", df)
        actual = csprcrse.gaussian_rank(
            df, bulk_frac_to_remove=0.5, n_quantiles=3
        )
        precision = 2
        actual_str = hpandas.df_to_str(
            actual.round(precision), num_rows=None, precision=precision
        )
        expected_str = r"""
                              0     1     2     3     4     5     6     7     8     9
2022-01-04 09:30:00-05:00   NaN  5.20 -1.11  2.90   NaN   NaN  1.14   NaN   NaN -5.20
2022-01-04 09:45:00-05:00  1.74   NaN   NaN  5.20   NaN   NaN -5.20   NaN -1.04   NaN
2022-01-04 10:00:00-05:00   NaN -1.14   NaN  5.20  1.92   NaN   NaN -1.16 -5.20  2.16
2022-01-04 10:15:00-05:00   NaN -1.41   NaN  0.92   NaN  5.20 -5.20   NaN   NaN -1.99
2022-01-04 10:30:00-05:00   NaN  5.20   NaN -1.18  1.93   NaN   NaN  0.80 -5.20  1.48
2022-01-04 10:45:00-05:00   NaN   NaN -1.38   NaN -1.38 -5.20  1.44  1.61  5.20   NaN
2022-01-04 11:00:00-05:00 -0.81 -5.20   NaN   NaN  0.84 -0.79 -0.98   NaN  0.68  5.20
2022-01-04 11:15:00-05:00 -1.26   NaN  1.72   NaN   NaN -5.20   NaN  5.20  0.99  1.57
2022-01-04 11:30:00-05:00  0.93   NaN  1.52   NaN  5.20 -5.20  2.51 -0.92   NaN   NaN"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)


class Test_gaussian_rank2(hunitest.TestCase):
    @staticmethod
    def get_data() -> pd.DataFrame:
        df_str = """
,100,200,300,400
2016-01-04 16:00:00,3,5,32,-3
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,NaN,2,-4,8
2016-01-05 09:31:00,2,NaN,-4,8
2016-01-05 09:32:00,1,2,3,4
"""
        df = pd.read_csv(
            io.StringIO(df_str),
            index_col=0,
            parse_dates=True,
        )
        return df

    def helper(
        self,
        expected_str: str,
        bulk_frac_to_remove: float,
        bulk_fill_method: str,
    ) -> None:
        df = self.get_data()
        actual = csprcrse.gaussian_rank(
            df,
            bulk_frac_to_remove=bulk_frac_to_remove,
            bulk_fill_method=bulk_fill_method,
            n_quantiles=3,
        )
        precision = 2
        actual_str = hpandas.df_to_str(
            actual.round(precision), num_rows=None, precision=precision
        )
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)

    def test_default(self) -> None:
        expected_str = r"""
                      100   200   300  400
2016-01-04 16:00:00 -0.18  0.04  5.20 -5.2
2016-01-04 16:01:00   NaN   NaN   NaN  NaN
2016-01-05 09:29:00   NaN   NaN   NaN  NaN
2016-01-05 09:30:00   NaN  0.00 -5.20  5.2
2016-01-05 09:31:00  0.00   NaN -5.20  5.2
2016-01-05 09:32:00 -5.20 -0.43  0.43  5.2"""
        self.helper(expected_str, 0.0, "nan")

    def test_nan(self) -> None:
        expected_str = r"""
                     100  200  300  400
2016-01-04 16:00:00  NaN  NaN  5.2 -5.2
2016-01-04 16:01:00  NaN  NaN  NaN  NaN
2016-01-05 09:29:00  NaN  NaN  NaN  NaN
2016-01-05 09:30:00  NaN  NaN -5.2  5.2
2016-01-05 09:31:00  NaN  NaN -5.2  5.2
2016-01-05 09:32:00 -5.2  NaN  NaN  5.2"""
        self.helper(expected_str, 0.5, "nan")

    def test_zero(self) -> None:
        expected_str = r"""
                     100  200  300  400
2016-01-04 16:00:00  0.0  0.0  5.2 -5.2
2016-01-04 16:01:00  NaN  NaN  NaN  NaN
2016-01-05 09:29:00  NaN  NaN  NaN  NaN
2016-01-05 09:30:00  NaN  0.0 -5.2  5.2
2016-01-05 09:31:00  0.0  NaN -5.2  5.2
2016-01-05 09:32:00 -5.2  0.0  0.0  5.2"""
        self.helper(expected_str, 0.5, "zero")

    def test_ffill(self) -> None:
        expected_str = r"""
                     100  200  300  400
2016-01-04 16:00:00  NaN  NaN  5.2 -5.2
2016-01-04 16:01:00  NaN  NaN  NaN  NaN
2016-01-05 09:29:00  NaN  NaN  NaN  NaN
2016-01-05 09:30:00  NaN  NaN -5.2  5.2
2016-01-05 09:31:00  NaN  NaN -5.2  5.2
2016-01-05 09:32:00 -5.2  NaN -5.2  5.2"""
        self.helper(expected_str, 0.5, "ffill")


class Test_uniform_rank1(hunitest.TestCase):
    @staticmethod
    def get_data() -> pd.DataFrame:
        df_str = """
,100,200,300,400
2016-01-04 16:00:00,3,5,32,-3
2016-01-04 16:01:00,NaN,NaN,NaN,NaN
2016-01-05 09:29:00,NaN,NaN,NaN,NaN
2016-01-05 09:30:00,NaN,2,-4,8
2016-01-05 09:31:00,2,NaN,-4,8
2016-01-05 09:32:00,1,2,3,4
"""
        df = pd.read_csv(
            io.StringIO(df_str),
            index_col=0,
            parse_dates=True,
        )
        return df

    def test1(self) -> None:
        df = self.get_data()
        actual = csprcrse.uniform_rank(df)
        precision = 2
        actual_str = hpandas.df_to_str(
            actual.round(precision), num_rows=None, precision=precision
        )
        expected_str = r"""
                      100   200   300  400
2016-01-04 16:00:00 -0.33  0.33  1.00 -1.0
2016-01-04 16:01:00   NaN   NaN   NaN  NaN
2016-01-05 09:29:00   NaN   NaN   NaN  NaN
2016-01-05 09:30:00   NaN  0.00 -1.00  1.0
2016-01-05 09:31:00  0.00   NaN -1.00  1.0
2016-01-05 09:32:00 -1.00 -0.33  0.33  1.0
"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)
