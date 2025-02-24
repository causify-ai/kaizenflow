import io
import logging
from typing import Optional

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.finance.resampling as cfinresa
import core.finance_data_example as cfidaexa
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _get_test_data(
    start_ts_str: str,
    periods: int,
) -> pd.DataFrame:
    """
    Build test DataFrame with minutely timestamp index.
    """
    freq = "1T"
    timestamps = pd.date_range(start_ts_str, periods=periods, freq=freq)
    data = list(range(periods))
    df = pd.DataFrame(data, index=timestamps)
    df.columns = ["price"]
    return df


# #############################################################################
# Resampling.
# #############################################################################


class Test_resample_time_bars1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Resampling with the same frequency of the data should not change
        anything.
        """
        df = self._get_df()
        #
        rule = "1T"
        df_out = self._resample_helper(df, rule)
        # Check output.
        act = self._compute_actual_output(df, df_out)
        exp = r"""
        # df=
                            close      vol     ret_0
        datetime
        2016-01-04 09:30:00  94.70  1867590       NaN
        2016-01-04 09:31:00  94.98   349119  0.002957
        2016-01-04 09:32:00  95.33   419479  0.003685
        2016-01-04 09:33:00  95.03   307383 -0.003147
        2016-01-04 09:34:00  94.89   342218 -0.001473
        2016-01-04 09:35:00  94.97   358280  0.000843
        2016-01-04 09:36:00  95.21   266199  0.002527
        2016-01-04 09:37:00  95.48   293074  0.002836
        2016-01-04 09:38:00  95.95   581584  0.004922
        2016-01-04 09:39:00  96.07   554872  0.001251
        # df_out=
                                ret_0  close      vol
        datetime
        2016-01-04 09:30:00       NaN  94.70  1867590
        2016-01-04 09:31:00  0.002957  94.98   349119
        2016-01-04 09:32:00  0.003685  95.33   419479
        2016-01-04 09:33:00 -0.003147  95.03   307383
        2016-01-04 09:34:00 -0.001473  94.89   342218
        2016-01-04 09:35:00  0.000843  94.97   358280
        2016-01-04 09:36:00  0.002527  95.21   266199
        2016-01-04 09:37:00  0.002836  95.48   293074
        2016-01-04 09:38:00  0.004922  95.95   581584
        2016-01-04 09:39:00  0.001251  96.07   554872
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        """
        Resample data with 1 min resolution with 5 mins intervals.
        """
        df = self._get_df()
        #
        rule = "5T"
        df_out = self._resample_helper(df, rule)
        # Check output.
        act = self._compute_actual_output(df, df_out)
        exp = r"""
        # df=
                            close      vol     ret_0
        datetime
        2016-01-04 09:30:00  94.70  1867590       NaN
        2016-01-04 09:31:00  94.98   349119  0.002957
        2016-01-04 09:32:00  95.33   419479  0.003685
        2016-01-04 09:33:00  95.03   307383 -0.003147
        2016-01-04 09:34:00  94.89   342218 -0.001473
        2016-01-04 09:35:00  94.97   358280  0.000843
        2016-01-04 09:36:00  95.21   266199  0.002527
        2016-01-04 09:37:00  95.48   293074  0.002836
        2016-01-04 09:38:00  95.95   581584  0.004922
        2016-01-04 09:39:00  96.07   554872  0.001251
        # df_out=
                                ret_0    close      vol
        datetime
        2016-01-04 09:30:00       NaN  94.7000  1867590
        2016-01-04 09:35:00  0.002865  95.0400  1776479
        2016-01-04 09:40:00  0.011536  95.6775  1695729
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Check manually certain values for the returns.
        self.assertTrue(np.isnan(df.loc["2016-01-04 09:30:00", "ret_0"]))
        np.testing.assert_almost_equal(
            df.loc["2016-01-04 09:31:00", "ret_0"],
            (94.98 - 94.70) / 94.70,
            decimal=6,
        )
        np.testing.assert_almost_equal(
            df.loc["2016-01-04 09:39:00", "ret_0"],
            (96.07 - 95.95) / 95.95,
            decimal=6,
        )
        # The resampling is (a, b] with the label on b.
        # The first interval corresponds to (9:25, 9:30] and is timestamped with
        # 9:30am. The values are the same as the first row of the input.
        timestamp = "2016-01-04 09:30:00"
        for col in df.columns:
            np.testing.assert_almost_equal(
                df_out.loc[timestamp, col], df.loc[timestamp, col]
            )
        # The second interval corresponds to (9:30, 9:35] and is timestamped with
        # 9:35am.
        timestamp = "2016-01-04 09:35:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "close"],
            np.mean([94.98, 95.33, 95.03, 94.89, 94.97]),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vol"],
            np.sum([349119, 419479, 307383, 342218, 358280]),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "ret_0"],
            np.sum([0.002957, 0.003685, -0.003147, -0.001473, 0.000843]),
        )
        # The last interval corresponds to (9:35, 9:40] and is timestamped with 9:40am.
        # Note that the last timestamp (i.e., 9:40am) is missing so the average is
        # on 4 values and not 1.
        timestamp = "2016-01-04 09:40:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "close"], np.mean([95.21, 95.48, 95.95, 96.07])
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vol"], np.sum([266199, 293074, 581584, 554872])
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "ret_0"],
            np.sum([0.002527, 0.002836, 0.004922, 0.001251]),
        )

    @staticmethod
    def _get_df() -> pd.DataFrame:
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,close,vol,ret_0
2016-01-04 09:30:00,94.7,1867590,NaN
2016-01-04 09:31:00,94.98,349119,0.002957
2016-01-04 09:32:00,95.33,419479,0.003685
2016-01-04 09:33:00,95.03,307383,-0.003147
2016-01-04 09:34:00,94.89,342218,-0.001473
2016-01-04 09:35:00,94.97,358280,0.000843
2016-01-04 09:36:00,95.21,266199,0.002527
2016-01-04 09:37:00,95.48,293074,0.002836
2016-01-04 09:38:00,95.95,581584,0.004922
2016-01-04 09:39:00,96.07,554872,0.001251
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df

    @staticmethod
    def _resample_helper(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        return_cols = ["ret_0"]
        return_agg_func = None
        return_agg_func_kwargs = None
        #
        price_cols = ["close"]
        price_agg_func = None
        price_agg_func_kwargs = None
        #
        volume_cols = ["vol"]
        volume_agg_func = None
        volume_agg_func_kwargs = None
        df_out = cfinresa.resample_time_bars(
            df,
            rule,
            return_cols=return_cols,
            return_agg_func=return_agg_func,
            return_agg_func_kwargs=return_agg_func_kwargs,
            price_cols=price_cols,
            price_agg_func=price_agg_func,
            price_agg_func_kwargs=price_agg_func_kwargs,
            volume_cols=volume_cols,
            volume_agg_func=volume_agg_func,
            volume_agg_func_kwargs=volume_agg_func_kwargs,
        )
        return df_out

    @staticmethod
    def _compute_actual_output(df: pd.DataFrame, df_out: pd.DataFrame) -> str:
        act = []
        act.append(hpandas.df_to_str(df, num_rows=None, tag="df"))
        act.append(hpandas.df_to_str(df_out, num_rows=None, tag="df_out"))
        act = "\n".join(act)
        return act


class Test_resample_ohlcv_bars1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Compute OHLCV bars at the frequency of the data should not change the
        data.
        """
        df = self._get_df()
        rule = "1T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        self.assert_equal(act, act, fuzzy_match=True)

    def test2(self) -> None:
        """
        Compute OHLCV bars at 5 min frequency on 1 min data.
        """
        df = self._get_df()
        rule = "5T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                            open   high    low  close      vol
        datetime
        2016-01-04 09:30:00  95.23  95.23  94.66  94.70  1867590
        2016-01-04 09:35:00  94.72  95.43  94.67  94.97  1776479
        2016-01-04 09:40:00  94.98  96.23  94.95  95.93  2182331
        2016-01-04 09:45:00  95.92  96.13  95.06  95.31  1746253
        2016-01-04 09:50:00  95.31  95.81  95.27  95.61   841564
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # The first interval corresponds to (9:25, 9:30] and is timestamped with
        # 9:30am. The values are the same as the first row of the input.
        timestamp = "2016-01-04 09:30:00"
        for col in df.columns:
            np.testing.assert_almost_equal(
                df_out.loc[timestamp, col], df.loc[timestamp, col]
            )
        # The second interval corresponds to (9:30, 9:30] and is timestamped with
        # 9:30am. The values are the same as the first row of the input.
        timestamp = "2016-01-04 09:35:00"
        np.testing.assert_almost_equal(df_out.loc[timestamp, "open"], 94.72)
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "high"],
            np.max([95.05, 95.43, 95.39, 95.04, 95.21]),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "low"],
            np.min([94.67, 94.95, 95.01, 94.75, 94.88]),
        )
        np.testing.assert_almost_equal(df_out.loc[timestamp, "close"], 94.97)
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vol"],
            np.sum([349119, 419479, 307383, 342218, 358280]),
        )

    def test3(self) -> None:
        """
        Compute OHLCV bars at 1 hr gives first, max, min, last values.
        """
        df = self._get_df()
        rule = "1H"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                            open   high    low  close      vol
        datetime
        2016-01-04 10:00:00  95.23  96.23  94.66  95.61  8414217
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # The only interval corresponds to (9:00, 10:00] and is timestamped with
        # 10:00am.
        timestamp = "2016-01-04 10:00:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "open"], df.loc["2016-01-04 09:30:00", "open"]
        )
        df_values = df.drop("vol", axis="columns").values
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "high"], np.max(np.max(df_values, axis=1))
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "low"], np.min(np.min(df_values, axis=1))
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "close"], df.loc["2016-01-04 09:49:00", "close"]
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vol"], np.sum(df[["vol"]].values)
        )

    @staticmethod
    def _get_df() -> pd.DataFrame:
        """
        Return a df without NaNs.
        """
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,open,high,low,close,vol
2016-01-04 09:30:00,95.23,95.23,94.66,94.7,1867590
2016-01-04 09:31:00,94.72,95.05,94.67,94.98,349119
2016-01-04 09:32:00,94.97,95.43,94.95,95.33,419479
2016-01-04 09:33:00,95.34,95.39,95.01,95.03,307383
2016-01-04 09:34:00,95.01,95.04,94.75,94.89,342218
2016-01-04 09:35:00,94.9,95.21,94.88,94.97,358280
2016-01-04 09:36:00,94.98,95.27,94.95,95.21,266199
2016-01-04 09:37:00,95.21,95.49,95.2,95.48,293074
2016-01-04 09:38:00,95.48,96.04,95.47,95.95,581584
2016-01-04 09:39:00,95.93,96.16,95.82,96.07,554872
2016-01-04 09:40:00,96.08,96.23,95.9,95.93,486602
2016-01-04 09:41:00,95.92,96.13,95.75,95.78,451518
2016-01-04 09:42:00,95.8,95.9,95.59,95.59,315207
2016-01-04 09:43:00,95.61,95.62,95.28,95.29,429025
2016-01-04 09:44:00,95.29,95.41,95.22,95.26,262630
2016-01-04 09:45:00,95.26,95.37,95.06,95.31,287873
2016-01-04 09:46:00,95.31,95.48,95.27,95.41,225975
2016-01-04 09:47:00,95.41,95.71,95.33,95.66,262623
2016-01-04 09:48:00,95.7,95.71,95.5,95.57,179722
2016-01-04 09:49:00,95.56,95.81,95.49,95.61,173244
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df

    @staticmethod
    def _helper(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        df_out = cfinresa.resample_ohlcv_bars(
            df,
            rule,
            open_col="open",
            high_col="high",
            low_col="low",
            close_col="close",
            volume_col="vol",
            add_twap_vwap=False,
        )
        return df_out

    @staticmethod
    def _compute_actual_output(df_out: pd.DataFrame) -> str:
        act = []
        act.append(hpandas.df_to_str(df_out, num_rows=None, tag="df_out"))
        act = "\n".join(act)
        return act


class Test_compute_twap_vwap1(hunitest.TestCase):
    def test_with_no_nans1(self) -> None:
        """
        Compute VWAP/TWAP at the frequency of the data should not change the
        data.
        """
        df = self._get_df_with_no_nans()
        rule = "1T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                            vwap   twap
        datetime
        2016-01-04 09:30:00  94.70  94.70
        2016-01-04 09:31:00  94.98  94.98
        2016-01-04 09:32:00  95.33  95.33
        2016-01-04 09:33:00  95.03  95.03
        2016-01-04 09:34:00  94.89  94.89
        2016-01-04 09:35:00  94.97  94.97
        2016-01-04 09:36:00  95.21  95.21
        2016-01-04 09:37:00  95.48  95.48
        2016-01-04 09:38:00  95.95  95.95
        2016-01-04 09:39:00  96.07  96.07
        2016-01-04 09:40:00  95.93  95.93
        2016-01-04 09:41:00  95.78  95.78
        2016-01-04 09:42:00  95.59  95.59
        2016-01-04 09:43:00  95.29  95.29
        2016-01-04 09:44:00  95.26  95.26
        2016-01-04 09:45:00  95.31  95.31
        2016-01-04 09:46:00  95.41  95.41
        2016-01-04 09:47:00  95.66  95.66
        2016-01-04 09:48:00  95.57  95.57
        2016-01-04 09:49:00  95.61  95.61
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # TWAP is the same as VWAP aggregating on 1 sample.
        np.testing.assert_array_almost_equal(df_out["vwap"], df_out["twap"])
        # TWAP and VWAP are the same value as the original price aggregating on 1
        # sample.
        np.testing.assert_array_almost_equal(df_out["vwap"], df["close"])

    def test_with_no_nans2(self) -> None:
        """
        Compute VWAP/TWAP at 5 min frequency on 1 min data.
        """
        df = self._get_df_with_no_nans()
        rule = "5T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                                vwap     twap
        datetime
        2016-01-04 09:30:00  94.700000  94.7000
        2016-01-04 09:35:00  95.051943  95.0400
        2016-01-04 09:40:00  95.822669  95.7280
        2016-01-04 09:45:00  95.469633  95.4460
        2016-01-04 09:50:00  95.563357  95.5625
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # The first interval is (9:25, 9:30] so VWAP/TWAP matches the original data.
        timestamp = "2016-01-04 09:30:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"], df.loc[timestamp, "close"]
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"], df.loc[timestamp, "close"]
        )
        # The second interval is (9:30, 9:35].
        timestamp = "2016-01-04 09:35:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"],
            (
                94.98 * 349119
                + 95.33 * 419479
                + 95.03 * 307383
                + 94.89 * 342218
                + 94.97 * 358280
            )
            / (349119 + 419479 + 307383 + 342218 + 358280),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"],
            np.mean([94.98, 95.33, 95.03, 94.89, 94.97]),
        )
        # The last interval is (9:45, 9:50].
        timestamp = "2016-01-04 09:50:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"],
            (95.41 * 225975 + 95.66 * 262623 + 95.57 * 179722 + 95.61 * 173244)
            / (225975 + 262623 + 179722 + 173244),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"], np.mean([95.41, 95.66, 95.57, 95.61])
        )

    def test_with_nans1(self) -> None:
        """
        Compute VWAP/TWAP at the frequency of the data.
        """
        df = self._get_df_with_nans()
        rule = "1T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                            vwap   twap
        datetime
        2016-01-04 09:30:00    NaN    NaN
        2016-01-04 09:31:00    NaN  94.98
        2016-01-04 09:32:00  95.33  95.33
        2016-01-04 09:33:00  95.03  95.03
        2016-01-04 09:34:00  94.89  94.89
        2016-01-04 09:35:00  94.97  94.97
        2016-01-04 09:36:00    NaN    NaN
        2016-01-04 09:37:00    NaN  95.48
        2016-01-04 09:38:00  95.95  95.95
        2016-01-04 09:39:00  96.07  96.07
        2016-01-04 09:40:00    NaN    NaN
        2016-01-04 09:41:00    NaN    NaN
        2016-01-04 09:42:00    NaN    NaN
        2016-01-04 09:43:00    NaN    NaN
        2016-01-04 09:44:00    NaN    NaN
        2016-01-04 09:45:00    NaN    NaN
        2016-01-04 09:46:00  95.41  95.41
        2016-01-04 09:47:00  95.66  95.66
        2016-01-04 09:48:00  95.57  95.57
        2016-01-04 09:49:00  95.61  95.61
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_with_nans2(self) -> None:
        """
        Compute VWAP/TWAP at 5 min frequency on 1 min data.
        """
        # TODO(*): Put the relevant data close to the test.
        df = self._get_df_with_nans()
        rule = "5T"
        df_out = self._helper(df, rule)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                                vwap       twap
        datetime
        2016-01-04 09:30:00        NaN        NaN
        2016-01-04 09:35:00  95.069539  95.040000
        2016-01-04 09:40:00  96.008590  95.833333
        2016-01-04 09:45:00        NaN        NaN
        2016-01-04 09:50:00  95.563357  95.562500
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_with_offset(self) -> None:
        """
        Compute VWAP/TWAP at 5 min frequency on 1 min data.
        """
        df = self._get_df_with_no_nans()
        rule = "5T"
        offset = "1T"
        df_out = self._helper(df, rule, offset)
        # Compute output.
        act = self._compute_actual_output(df_out)
        exp = r"""
        # df_out=
                                vwap       twap
        datetime
        2016-01-04 09:31:00  94.744098  94.840000
        2016-01-04 09:36:00  95.091617  95.086000
        2016-01-04 09:41:00  95.883415  95.842000
        2016-01-04 09:46:00  95.368620  95.372000
        2016-01-04 09:51:00  95.619653  95.613333
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # The first interval is (9:26, 9:31].
        timestamp = "2016-01-04 09:31:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"],
            (94.7 * 1867590 + 94.98 * 349119) / (1867590 + 349119),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"],
            np.mean([94.7, 94.98]),
        )
        # The second interval is (9:31, 9:36].
        timestamp = "2016-01-04 09:36:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"],
            (
                95.33 * 419479
                + 95.03 * 307383
                + 94.89 * 342218
                + 94.97 * 358280
                + 95.21 * 266199
            )
            / (419479 + 307383 + 342218 + 358280 + 266199),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"],
            np.mean([95.33, 95.03, 94.89, 94.97, 95.21]),
        )
        # The last interval is (9:46, 9:51].
        timestamp = "2016-01-04 09:51:00"
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "vwap"],
            (95.66 * 262623 + 95.57 * 179722 + 95.61 * 173244)
            / (262623 + 179722 + 173244),
        )
        np.testing.assert_almost_equal(
            df_out.loc[timestamp, "twap"], np.mean([95.66, 95.57, 95.61])
        )

    @staticmethod
    def _get_df_with_no_nans() -> pd.DataFrame:
        """
        Return a df without NaNs.
        """
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,close,vol
2016-01-04 09:30:00,94.7,1867590
2016-01-04 09:31:00,94.98,349119
2016-01-04 09:32:00,95.33,419479
2016-01-04 09:33:00,95.03,307383
2016-01-04 09:34:00,94.89,342218
2016-01-04 09:35:00,94.97,358280
2016-01-04 09:36:00,95.21,266199
2016-01-04 09:37:00,95.48,293074
2016-01-04 09:38:00,95.95,581584
2016-01-04 09:39:00,96.07,554872
2016-01-04 09:40:00,95.93,486602
2016-01-04 09:41:00,95.78,451518
2016-01-04 09:42:00,95.59,315207
2016-01-04 09:43:00,95.29,429025
2016-01-04 09:44:00,95.26,262630
2016-01-04 09:45:00,95.31,287873
2016-01-04 09:46:00,95.41,225975
2016-01-04 09:47:00,95.66,262623
2016-01-04 09:48:00,95.57,179722
2016-01-04 09:49:00,95.61,173244
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df

    @staticmethod
    def _get_df_with_nans() -> pd.DataFrame:
        """
        Compute a df with NaNs.
        """
        # From `s3://*****-data/data/kibot/all_stocks_1min/AAPL.csv.gz`.
        txt = """
datetime,close,vol
2016-01-04 09:30:00,NaN,1867590
2016-01-04 09:31:00,94.98,NaN
2016-01-04 09:32:00,95.33,419479
2016-01-04 09:33:00,95.03,307383
2016-01-04 09:34:00,94.89,342218
2016-01-04 09:35:00,94.97,358280
2016-01-04 09:36:00,NaN,266199
2016-01-04 09:37:00,95.48,NaN
2016-01-04 09:38:00,95.95,581584
2016-01-04 09:39:00,96.07,554872
2016-01-04 09:40:00,NaN,NaN
2016-01-04 09:41:00,NaN,451518
2016-01-04 09:42:00,NaN,315207
2016-01-04 09:43:00,NaN,429025
2016-01-04 09:44:00,NaN,262630
2016-01-04 09:45:00,NaN,287873
2016-01-04 09:46:00,95.41,225975
2016-01-04 09:47:00,95.66,262623
2016-01-04 09:48:00,95.57,179722
2016-01-04 09:49:00,95.61,173244
"""
        df = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        return df

    @staticmethod
    def _helper(
        df: pd.DataFrame, rule: str, offset: Optional[str] = None
    ) -> pd.DataFrame:
        price_col = "close"
        volume_col = "vol"
        df_out = cfinresa.compute_twap_vwap(
            df,
            rule,
            price_col=price_col,
            volume_col=volume_col,
            offset=offset,
        )
        return df_out

    @staticmethod
    def _compute_actual_output(df_out: pd.DataFrame) -> str:
        act = []
        act.append(hpandas.df_to_str(df_out, num_rows=None, tag="df_out"))
        act = "\n".join(act)
        return act


class TestResamplePortfolioBarMetrics1(hunitest.TestCase):
    @staticmethod
    def get_data(
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
        *,
        bar_duration: str = "5T",
        seed: int = 10,
    ) -> pd.DataFrame:
        df = cfidaexa.get_portfolio_bar_metrics_dataframe(
            start_datetime, end_datetime, bar_duration=bar_duration, seed=seed
        )
        return df

    def test_resampling_invariance(self) -> None:
        """
        Preserve data when resampling at the same frequency.
        """
        freq = "5T"
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            bar_duration=freq,
            seed=27,
        )
        precision = 2
        data_str = hpandas.df_to_str(data, num_rows=None, precision=precision)
        resampled_data = cfinresa.resample_portfolio_bar_metrics(
            data,
            freq,
        )
        resampled_data_str = hpandas.df_to_str(
            resampled_data, num_rows=None, precision=precision
        )
        self.assert_equal(data_str, resampled_data_str, fuzzy_match=True)

    def test_resampling_endpoints_intraday(self) -> None:
        """
        Assign data to bar labeled by left point.

        This convention differs from that used for casual signal
        resampling.
        """
        freq = "5T"
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-03 10:00:00", tz="America/New_York"),
            bar_duration=freq,
            seed=27,
        )
        resampling_freq = "10T"
        resampled_data = cfinresa.resample_portfolio_bar_metrics(
            data,
            resampling_freq,
        )
        precision = 2
        actual = hpandas.df_to_str(
            resampled_data, num_rows=None, precision=precision
        )
        expected = r"""
                              pnl  gross_volume  net_volume        gmv     nmv
2022-01-03 09:30:00-05:00  125.44         49863      -31.10  1000000.0     NaN
2022-01-03 09:40:00-05:00  174.18        100215       24.68  1000000.0   12.47
2022-01-03 09:50:00-05:00  -21.52        100041      -90.39  1000000.0  -55.06
2022-01-03 10:00:00-05:00  -16.82         50202       99.19  1000000.0  167.08"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_resampling_endpoints_daily(self) -> None:
        freq = "30T"
        data = self.get_data(
            pd.Timestamp("2022-01-03 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-01-04 16:00:00", tz="America/New_York"),
            bar_duration=freq,
            seed=27,
        )
        resampling_freq = "B"
        resampled_data = cfinresa.resample_portfolio_bar_metrics(
            data,
            resampling_freq,
        )
        precision = 2
        actual = hpandas.df_to_str(
            resampled_data, num_rows=None, precision=precision
        )
        expected = r"""
                              pnl  gross_volume  net_volume        gmv    nmv
2022-01-03 00:00:00-05:00 -167.88        650519      256.55  1000000.0  11.12
2022-01-04 00:00:00-05:00 -271.28        650884       -8.48  1000000.0 -14.92"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_resample_srs(hunitest.TestCase):
    # TODO(gp): Replace `check_string()` with `assert_equal()` to tests that benefit
    #  from seeing / freezing the results, using a command like:
    # ```
    # > invoke find_check_string_output -c Test_resample_srs -m test_day_to_year1
    # ```

    # Converting days to other units.
    def test_day_to_year1(self) -> None:
        """
        Test freq="D", unit="Y".
        """
        series = self._get_series(seed=1, periods=9, freq="D")
        rule = "Y"
        actual_default = (
            cfinresa.resample(series, rule=rule)
            .sum()
            .rename(f"Output in freq='{rule}'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule=rule, closed="left")
            .sum()
            .rename(f"Output in freq='{rule}'")
        )
        act = self._get_output_txt(series, actual_default, actual_closed_left)
        exp = r"""
        Input:
                    Input in freq='D'
        2014-12-26           0.162435
        2014-12-27           0.263693
        2014-12-28           0.149701
        2014-12-29          -0.010413
        2014-12-30          -0.031170
        2014-12-31          -0.174783
        2015-01-01          -0.230455
        2015-01-02          -0.132095
        2015-01-03          -0.176312

        Output with default arguments:
                    Output in freq='Y'
        2014-12-31            0.359463
        2015-12-31           -0.538862

        Output with closed='left':
                    Output in freq='Y'
        2014-12-31            0.534246
        2015-12-31           -0.713644
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_day_to_month1(self) -> None:
        """
        Test freq="D", unit="M".
        """
        series = self._get_series(seed=1, periods=9, freq="D")
        actual_default = (
            cfinresa.resample(series, rule="M").sum().rename("Output in freq='M'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="M", closed="left")
            .sum()
            .rename("Output in freq='M'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_day_to_week1(self) -> None:
        """
        Test freq="D", unit="W".
        """
        series = self._get_series(seed=1, periods=9, freq="D")
        actual_default = (
            cfinresa.resample(series, rule="W").sum().rename("Output in freq='W'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="W", closed="left")
            .sum()
            .rename("Output in freq='W'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_day_to_business_day1(self) -> None:
        """
        Test freq="D", unit="B".
        """
        series = self._get_series(seed=1, periods=9, freq="D")
        actual_default = (
            cfinresa.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="B", closed="left")
            .sum()
            .rename("Output in freq='B'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    # Equal frequency resampling.
    def test_only_day1(self) -> None:
        """
        Test freq="D", unit="D".
        """
        series = self._get_series(seed=1, periods=9, freq="D")
        actual_default = (
            cfinresa.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="D", closed="left")
            .sum()
            .rename("Output in freq='D'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_only_minute1(self) -> None:
        """
        Test freq="T", unit="T".
        """
        series = self._get_series(seed=1, periods=9, freq="T")
        actual_default = (
            cfinresa.resample(series, rule="T").sum().rename("Output in freq='T'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="T", closed="left")
            .sum()
            .rename("Output in freq='T'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_only_business_day1(self) -> None:
        """
        Test freq="B", unit="B".
        """
        series = self._get_series(seed=1, periods=9, freq="B")
        actual_default = (
            cfinresa.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="B", closed="left")
            .sum()
            .rename("Output in freq='B'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    # Upsampling.
    def test_upsample_month_to_day1(self) -> None:
        """
        Test freq="M", unit="D".
        """
        series = self._get_series(seed=1, periods=3, freq="M")
        actual_default = (
            cfinresa.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="D", closed="left")
            .sum()
            .rename("Output in freq='D'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_upsample_business_day_to_day1(self) -> None:
        """
        Test freq="B", unit="D".
        """
        series = self._get_series(seed=1, periods=9, freq="B")
        actual_default = (
            cfinresa.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="D", closed="left")
            .sum()
            .rename("Output in freq='D'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    # Resampling freq-less series.
    def test_no_freq_day_to_business_day1(self) -> None:
        """
        Test for an input without `freq`.
        """
        series = self._get_series(seed=1, periods=9, freq="D").rename(
            "Input with no freq"
        )
        # Remove some observations in order to make `freq` None.
        series = series.drop(series.index[3:7])
        actual_default = (
            cfinresa.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            cfinresa.resample(series, rule="B", closed="left")
            .sum()
            .rename("Output in freq='B'")
        )
        txt = self._get_output_txt(series, actual_default, actual_closed_left)
        self.check_string(txt)

    @staticmethod
    def _get_series(seed: int, periods: int, freq: str) -> pd.Series:
        """
        Periods include:

        26/12/2014 - Friday,    workday,    5th DoW
        27/12/2014 - Saturday,  weekend,    6th DoW
        28/12/2014 - Sunday,    weekend,    7th DoW
        29/12/2014 - Monday,    workday,    1th DoW
        30/12/2014 - Tuesday,   workday,    2th DoW
        31/12/2014 - Wednesday, workday,    3th DoW
        01/12/2014 - Thursday,  workday,    4th DoW
        02/12/2014 - Friday,    workday,    5th DoW
        03/12/2014 - Saturday,  weekend,    6th DoW
        """
        arma_process = carsigen.ArmaProcess([1], [1])
        date_range = {"start": "2014-12-26", "periods": periods, "freq": freq}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename(f"Input in freq='{freq}'")
        return series

    @staticmethod
    def _get_output_txt(
        input_data: pd.Series,
        output_default: pd.Series,
        output_closed_left: pd.Series,
    ) -> str:
        """
        Create string output for tests results.
        """
        input_string = hpandas.df_to_str(input_data, num_rows=None)
        output_default_string = hpandas.df_to_str(output_default, num_rows=None)
        output_closed_left_string = hpandas.df_to_str(
            output_closed_left, num_rows=None
        )
        txt = (
            f"Input:\n{input_string}\n\n"
            f"Output with default arguments:\n{output_default_string}\n\n"
            f"Output with closed='left':\n{output_closed_left_string}\n"
        )
        return txt


class Test_resample_df(hunitest.TestCase):
    # Converting days to other units.
    def test_day_to_year1(self) -> None:
        """
        Test freq="D", unit="Y".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = cfinresa.resample(df, rule="Y").sum()
        actual_default.columns = [
            "1st output in freq='Y'",
            "2nd output in freq='Y'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="Y", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='Y'",
            "2nd output in freq='Y'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_day_to_month1(self) -> None:
        """
        Test freq="D", unit="M".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = cfinresa.resample(df, rule="M").sum()
        actual_default.columns = [
            "1st output in freq='M'",
            "2nd output in freq='M'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="M", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='M'",
            "2nd output in freq='M'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_day_to_week1(self) -> None:
        """
        Test freq="D", unit="W".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = cfinresa.resample(df, rule="W").sum()
        actual_default.columns = [
            "1st output in freq='W'",
            "2nd output in freq='W'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="W", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='W'",
            "2nd output in freq='W'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_day_to_business_day1(self) -> None:
        """
        Test freq="D", unit="B".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = cfinresa.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="B", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    # Equal frequency resampling.
    def test_only_day1(self) -> None:
        """
        Test freq="D", unit="D".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = cfinresa.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="D", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_only_minute1(self) -> None:
        """
        Test freq="T", unit="T".
        """
        df = self._get_df(seed=1, periods=9, freq="T")
        actual_default = cfinresa.resample(df, rule="T").sum()
        actual_default.columns = [
            "1st output in freq='T'",
            "2nd output in freq='T'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="T", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='T'",
            "2nd output in freq='T'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_only_business_day1(self) -> None:
        """
        Test freq="B", unit="B".
        """
        df = self._get_df(seed=1, periods=9, freq="B")
        actual_default = cfinresa.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="B", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    # Upsampling.
    def test_upsample_month_to_day1(self) -> None:
        """
        Test freq="M", unit="D".
        """
        df = self._get_df(seed=1, periods=3, freq="M")
        actual_default = cfinresa.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="D", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    def test_upsample_business_day_to_day1(self) -> None:
        """
        Test freq="B", unit="D".
        """
        df = self._get_df(seed=1, periods=9, freq="B")
        actual_default = cfinresa.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="D", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    # Resampling freq-less series.
    def test_no_freq_day_to_business_day1(self) -> None:
        """
        Test for an input without `freq`.
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        df.columns = ["1st input with no freq", "2nd input with no freq"]
        # Remove some observations in order to make `freq` None.
        df = df.drop(df.index[3:7])
        actual_default = cfinresa.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = cfinresa.resample(df, rule="B", closed="left").sum()
        actual_closed_left.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        txt = self._get_output_txt(df, actual_default, actual_closed_left)
        self.check_string(txt)

    @staticmethod
    def _get_df(seed: int, periods: int, freq: str) -> pd.DataFrame:
        """
        Periods include:

        26/12/2014 - Friday,    workday,    5th DoW
        27/12/2014 - Saturday,  weekend,    6th DoW
        28/12/2014 - Sunday,    weekend,    7th DoW
        29/12/2014 - Monday,    workday,    1th DoW
        30/12/2014 - Tuesday,   workday,    2th DoW
        31/12/2014 - Wednesday, workday,    3th DoW
        01/12/2014 - Thursday,  workday,    4th DoW
        02/12/2014 - Friday,    workday,    5th DoW
        03/12/2014 - Saturday,  weekend,    6th DoW
        """
        arma_process = carsigen.ArmaProcess([1], [1])
        date_range = {"start": "2014-12-26", "periods": periods, "freq": freq}
        srs_1 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename(f"1st input in freq='{freq}'")
        srs_2 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed + 1
        ).rename(f"2nd input in freq='{freq}'")
        df = pd.DataFrame([srs_1, srs_2]).T
        return df

    @staticmethod
    def _get_output_txt(
        input_data: pd.DataFrame,
        output_default: pd.DataFrame,
        output_closed_left: pd.DataFrame,
    ) -> str:
        """
        Create string output for tests results.
        """
        input_string = hpandas.df_to_str(input_data, num_rows=None)
        output_default_string = hpandas.df_to_str(output_default, num_rows=None)
        output_closed_left_string = hpandas.df_to_str(
            output_closed_left, num_rows=None
        )
        txt = (
            f"Input:\n{input_string}\n\n"
            f"Output with default arguments:\n{output_default_string}\n\n"
            f"Output with closed='left':\n{output_closed_left_string}\n"
        )
        return txt


class Test_build_repeating_pattern_srs(hunitest.TestCase):
    def test1(self) -> None:
        # Set inputs.
        start_ts_str = "2023-06-11 09:44:00+00"
        periods = 10
        data = _get_test_data(start_ts_str, periods)
        weights = [1, 2, 3, 4, 5]
        # Test.
        srs = cfinresa.build_repeating_pattern_srs(data, weights)
        actual = hpandas.df_to_str(srs, num_rows=None)
        expected = r"""
                                0
        2023-06-11 09:44:00+00:00  4
        2023-06-11 09:45:00+00:00  5
        2023-06-11 09:46:00+00:00  1
        2023-06-11 09:47:00+00:00  2
        2023-06-11 09:48:00+00:00  3
        2023-06-11 09:49:00+00:00  4
        2023-06-11 09:50:00+00:00  5
        2023-06-11 09:51:00+00:00  1
        2023-06-11 09:52:00+00:00  2
        2023-06-11 09:53:00+00:00  3
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_resample_with_weights(hunitest.TestCase):
    def test1(self) -> None:
        # Set inputs.
        start_ts_str = "2023-06-11 09:44:00+00"
        periods = 20
        data = _get_test_data(start_ts_str, periods)
        #
        rule = "5T"
        col = "price"
        weights = [1, 2, 3, 4, 5]
        # Test.
        resampled_data = cfinresa.resample_with_weights(
            data, rule, col, weights
        )
        actual = hpandas.df_to_str(resampled_data, num_rows=None)
        expected = r"""
                                            price
        2023-06-11 09:45:00+00:00        0.555556
        2023-06-11 09:50:00+00:00        4.666667
        2023-06-11 09:55:00+00:00        9.666667
        2023-06-11 10:00:00+00:00       14.666667
        2023-06-11 10:05:00+00:00       18.333333
        """
        self.assert_equal(actual, expected, fuzzy_match=True)
