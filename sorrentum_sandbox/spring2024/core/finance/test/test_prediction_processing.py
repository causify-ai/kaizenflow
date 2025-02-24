import datetime
import io
import logging

import pandas as pd

import core.finance.prediction_processing as cfiprpro
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestStackPredictionDf(hunitest.TestCase):
    def test1(self) -> None:
        df = self._get_data()
        actual = cfiprpro.stack_prediction_df(
            df,
            id_col="amid",
            close_price_col="close",
            vwap_col="vwap",
            ret_col="ret",
            prediction_col="pred",
            ath_start=datetime.time(9, 30),
            ath_end=datetime.time(16, 0),
        )
        expected_txt = """
,amid,eob_close,eob_vwap,eob_ret,eopb_close,alpha,minute_index,start_bar_et_ts
0,MN0,100.0,100.0,,,,24198330,2016-01-04T09:30:00
1,MN1,73.25,73.25,,,,24198330,2016-01-04T09:30:00
2,MN0,100.05,100.04,0.0005,100.0,,24198331,2016-01-04T09:31:00
3,MN1,73.22,73.24,-0.00041,73.25,,24198331,2016-01-04T09:31:00
4,MN0,100.07,100.05,0.0002,100.05,1e-05,24198332,2016-01-04T09:32:00
5,MN1,73.22,73.23,0.0,73.22,-3e-05,24198332,2016-01-04T09:32:00
"""
        expected = pd.read_csv(
            io.StringIO(expected_txt),
            index_col=0,
        )
        # NOTE: If the test fails, converting to json strings may make
        #       debugging easier.
        # import helpers.hpandas as hpandas
        # actual_str = hpandas.convert_df_to_json_string(actual)
        # expected_str = hpandas.convert_df_to_json_string(expected)
        # self.assert_equal(actual_str, expected_str)
        hunitest.compare_df(actual, expected)

    @staticmethod
    def _get_data() -> pd.DataFrame:
        txt = """
,close,close,vwap,vwap,ret,ret,pred,pred
datetime,MN0,MN1,MN0,MN1,MN0,MN1,MN0,MN1
2016-01-04 09:31:00,100.0,73.25,100.0,73.25,NaN,NaN,NaN,NaN
2016-01-04 09:32:00,100.05,73.22,100.04,73.24,0.0005,-0.00041,0.00001,-0.00003
2016-01-04 09:33:00,100.07,73.22,100.05,73.23,0.0002,0.0,0.00001,0.00001
"""
        df = pd.read_csv(
            io.StringIO(txt), index_col=0, parse_dates=True, header=[0, 1]
        )
        df.index.freq = "T"
        return df


# #############################################################################


class TestComputeEpoch(hunitest.TestCase):
    """
    Test the computation of epoch time series with different units.
    """

    def helper(self) -> pd.Series:
        """
        Fetch input data for test.
        """
        timestamp_index = pd.date_range("2024-01-01", periods=10, freq="T")
        close = list(range(200, 210))
        data = {"close": close}
        srs = pd.Series(data=data, index=timestamp_index)
        return srs

    def test1(self) -> None:
        """
        Check that epoch is computed correctly for minute unit.
        """
        unit = "minute"
        srs = self.helper()
        result = cfiprpro.compute_epoch(srs, unit=unit)
        # Define expected values.
        expected_length = 10
        expected_column_value = None
        expected_signature = r"""
                              minute
        2024-01-01 00:00:00    28401120
        2024-01-01 00:01:00    28401121
        2024-01-01 00:02:00    28401122
        2024-01-01 00:03:00    28401123
        2024-01-01 00:04:00    28401124
        2024-01-01 00:05:00    28401125
        2024-01-01 00:06:00    28401126
        2024-01-01 00:07:00    28401127
        2024-01-01 00:08:00    28401128
        2024-01-01 00:09:00    28401129
        """
        # Check signature.
        self.check_srs_output(
            result, expected_length, expected_column_value, expected_signature
        )

    def test2(self) -> None:
        """
        Check that epoch is computed correctly for second unit.
        """
        unit = "second"
        srs = self.helper()
        result = cfiprpro.compute_epoch(srs, unit=unit)
        # Define expected values.
        expected_length = 10
        expected_column_value = None
        expected_signature = r"""
                                second
        2024-01-01 00:00:00    1704067200
        2024-01-01 00:01:00    1704067260
        2024-01-01 00:02:00    1704067320
        2024-01-01 00:03:00    1704067380
        2024-01-01 00:04:00    1704067440
        2024-01-01 00:05:00    1704067500
        2024-01-01 00:06:00    1704067560
        2024-01-01 00:07:00    1704067620
        2024-01-01 00:08:00    1704067680
        2024-01-01 00:09:00    1704067740
        """
        # Check signature.
        self.check_srs_output(
            result, expected_length, expected_column_value, expected_signature
        )

    def test3(self) -> None:
        """
        Check that epoch is computed correctly for nanosecond unit.
        """
        unit = "nanosecond"
        srs = self.helper()
        result = cfiprpro.compute_epoch(srs, unit=unit)
        # Define expected values.
        expected_length = 10
        expected_column_value = None
        expected_signature = r"""
                                     nanosecond
        2024-01-01 00:00:00    1704067200000000000
        2024-01-01 00:01:00    1704067260000000000
        2024-01-01 00:02:00    1704067320000000000
        2024-01-01 00:03:00    1704067380000000000
        2024-01-01 00:04:00    1704067440000000000
        2024-01-01 00:05:00    1704067500000000000
        2024-01-01 00:06:00    1704067560000000000
        2024-01-01 00:07:00    1704067620000000000
        2024-01-01 00:08:00    1704067680000000000
        2024-01-01 00:09:00    1704067740000000000
        """
        # Check signature.
        self.check_srs_output(
            result, expected_length, expected_column_value, expected_signature
        )

    def test4(self) -> None:
        """
        Check that epoch is computed correctly for dataframe input.
        """
        srs = self.helper()
        df = srs.to_frame()
        result = cfiprpro.compute_epoch(df)
        # Define expected values.
        expected_length = 10
        expected_column_value = None
        expected_signature = r"""
        # df=
        index=[2024-01-01 00:00:00, 2024-01-01 00:09:00]
        columns=minute
        shape=(10, 1)
                                minute
        2024-01-01 00:00:00        28401120
        2024-01-01 00:01:00        28401121
        2024-01-01 00:02:00        28401122
                                 ...
        2024-01-01 00:07:00        28401127
        2024-01-01 00:08:00        28401128
        2024-01-01 00:09:00        28401129
        """
        # Check signature.
        self.check_df_output(
            result,
            expected_length,
            expected_column_value,
            expected_column_value,
            expected_signature,
        )
