import datetime
import logging

import pandas as pd

import core.finance.accumulation as cfinaccu
import core.finance_data_example as cfidaexa
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def get_df() -> pd.DataFrame:
    """
    Return test dataframe with returns, volatility, and predictions.
    """
    df = cfidaexa.get_forecast_dataframe(
        pd.Timestamp("2020-01-04 09:30:00", tz="America/New_York"),
        pd.Timestamp("2020-01-06 16:00:00", tz="America/New_York"),
        [100],
    )
    df = df.swaplevel(axis=1)[100]
    return df


class Test_accumulate_returns_and_volatility1(hunitest.TestCase):
    def test1(self) -> None:
        df = get_df()
        actual = cfinaccu.accumulate_returns_and_volatility(
            df,
            "returns",
            "volatility",
            datetime.time(13, 30),
            datetime.time(13, 55),
        )
        actual_str = hpandas.df_to_str(
            actual.round(5), num_rows=None, precision=5
        )
        expected_str = r"""
                           returns  volatility
2020-01-04 13:35:00-05:00  0.00061     0.00083
2020-01-04 13:40:00-05:00  0.00047     0.00110
2020-01-04 13:45:00-05:00 -0.00086     0.00142
2020-01-04 13:50:00-05:00 -0.00035     0.00165
2020-01-04 13:55:00-05:00 -0.00069     0.00181
2020-01-05 13:35:00-05:00  0.00105     0.00095
2020-01-05 13:40:00-05:00  0.00017     0.00134
2020-01-05 13:45:00-05:00 -0.00113     0.00169
2020-01-05 13:50:00-05:00 -0.00230     0.00199
2020-01-05 13:55:00-05:00 -0.00398     0.00234
2020-01-06 13:35:00-05:00  0.00046     0.00095
2020-01-06 13:40:00-05:00 -0.00050     0.00135
2020-01-06 13:45:00-05:00 -0.00069     0.00159
2020-01-06 13:50:00-05:00 -0.00016     0.00177
2020-01-06 13:55:00-05:00 -0.00040     0.00191"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)


class Test_reverse_accumulate_returns1(hunitest.TestCase):
    def test1(self) -> None:
        df = get_df()
        actual = cfinaccu.reverse_accumulate_returns(
            df,
            "returns",
            datetime.time(13, 30),
            datetime.time(13, 55),
        )
        actual_str = hpandas.df_to_str(
            actual.round(5), num_rows=None, precision=5
        )
        expected_str = r"""
                                 0        1        2        3        4
2020-01-04 13:55:00-05:00 -0.00034  0.00017 -0.00116 -0.00130 -0.00069
2020-01-05 13:55:00-05:00 -0.00168 -0.00285 -0.00415 -0.00503 -0.00398
2020-01-06 13:55:00-05:00 -0.00024  0.00029  0.00010 -0.00086 -0.00040"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)
