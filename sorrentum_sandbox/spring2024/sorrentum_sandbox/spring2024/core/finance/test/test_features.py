import logging

import numpy as np
import pandas as pd

import core.finance.features as cfinfeat
import core.finance.market_data_example as cfmadaex
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_stochastic(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test that stochastic is computed correctly.
        """
        df = get_data()
        feature = cfinfeat.compute_stochastic(
            df,
            "high",
            "low",
            "close",
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   stochastic
0   -1.000000
1   -0.152000
2    0.333333
3   -1.000000
4   -0.783784
5   -0.392857
6    0.255814
7    0.920000
8   -1.000000
9    0.475410
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test the case when all prices are equal.
        """
        df = pd.DataFrame(
            data={
                "high": 35,
                "low": 35,
                "close": 35,
            },
            index=[0],
        )
        feature = cfinfeat.compute_stochastic(
            df,
            "high",
            "low",
            "close",
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
           stochastic
        0         0.0
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test the case when high=low!=close.
        """
        df = pd.DataFrame(
            data={
                "high": 35,
                "low": 35,
                "close": 12,
            },
            index=[0],
        )
        with self.assertRaises(AssertionError):
            cfinfeat.compute_stochastic(
                df,
                "high",
                "low",
                "close",
            )

    def test4(self) -> None:
        """
        Test the case when any price is np.nan.
        """
        df = pd.DataFrame(
            data={
                "high": np.nan,
                "low": np.nan,
                "close": 12,
            },
            index=[0],
        )
        feature = cfinfeat.compute_stochastic(
            df,
            "high",
            "low",
            "close",
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
        stochastic
        0         NaN
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_log(self) -> None:
        """
        Test that stochastic is computed correctly when the log trasnformation
        is applied.
        """
        df = get_data()
        feature = cfinfeat.compute_stochastic(
            df, "high", "low", "close", apply_log=True
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   stochastic
0   -1.000000
1   -0.151694
2    0.333454
3   -1.000000
4   -0.783676
5   -0.392738
6    0.256016
7    0.920029
8   -1.000000
9    0.475529
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_midrange(hunitest.TestCase):
    def test1(self) -> None:
        df = get_data()
        feature = cfinfeat.compute_midrange(
            df,
            "high",
            "low",
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   midrange
0   999.600
1   998.475
2   998.230
3   997.975
4   996.605
5   995.660
6   995.860
7   996.315
8   995.950
9   994.515
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_log(self) -> None:
        df = get_data()
        feature = cfinfeat.compute_midrange(df, "high", "low", apply_log=True)
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   log_midrange
0      6.907355
1      6.906229
2      6.905984
3      6.905728
4      6.904354
5      6.903406
6      6.903607
7      6.904063
8      6.903697
9      6.902255
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_money_transacted(hunitest.TestCase):
    def test1(self) -> None:
        df = get_data()
        feature = cfinfeat.compute_money_transacted(df, "high", "low", "volume")
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   money_transacted
0        982606.800
1       1002468.900
2        990244.160
3        963045.875
4       1003581.235
5       1067347.520
6        970963.500
7        965429.235
8        983002.650
9       1003465.635
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_normalize_bar(hunitest.TestCase):
    def test1(self) -> None:
        df = get_data()
        feature = cfinfeat.normalize_bar(
            df, "open", "high", "low", "close", "volume"
        )
        actual = hpandas.df_to_str(feature, num_rows=None)
        expected = r"""
   adj_high   adj_low  adj_close
0  0.005103 -0.016585  -0.016585
1  0.001894 -0.037556  -0.020829
2  0.005398 -0.011748  -0.000318
3  0.001288 -0.038307  -0.038307
4  0.000000 -0.034979  -0.031198
5  0.001527 -0.015577  -0.010384
6  0.027542  0.000000   0.017294
7  0.016705 -0.007389   0.015741
8  0.000000 -0.065571  -0.065571
9  0.004407 -0.014796  -0.000630
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


def get_data() -> pd.DataFrame:
    start_datetime = pd.Timestamp("2000-01-03 09:30:00", tz="America/New_York")
    end_datetime = pd.Timestamp("2000-01-03 12:00", tz="America/New_York")
    asset_id = 100
    bar_duration = "15T"
    seed = 10
    df = cfmadaex.generate_random_ohlcv_bars_for_asset(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        seed=seed,
    )
    _LOG.debug("data=%s", df)
    return df
