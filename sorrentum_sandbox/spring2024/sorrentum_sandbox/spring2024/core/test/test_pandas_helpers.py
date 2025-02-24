import io
import logging

import numpy as np
import pandas as pd
import pytest

import core.pandas_helpers as cpanhelp
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################


class TestResampleIndex1(hunitest.TestCase):
    def test1(self) -> None:
        index = pd.date_range(start="01-04-2018", periods=200, freq="30T")
        df = pd.DataFrame(np.random.rand(len(index), 3), index=index)
        txt = []
        txt.extend(["df.head()=", df.head()])
        txt.extend(["df.tail()=", df.tail()])
        resampled_index = cpanhelp.resample_index(
            df.index, time=(10, 30), freq="D"
        )
        # Normalize since the format seems to be changing on different machines.
        txt_tmp = str(resampled_index).replace("\n", "").replace(" ", "")
        txt.extend(["resampled_index=", txt_tmp])
        result = df.loc[resampled_index]
        txt.extend(["result=", str(result)])
        txt = "\n".join(map(str, txt))
        self.check_string(txt)


# #############################################################################


class TestDfRollingApply(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test with function returning a pd.Series.
        """
        df_str = hprint.dedent(
            """
        ,A,B
        2018-01-01,0.47,0.01
        2018-01-02,0.83,0.43
        2018-01-04,0.81,0.79
        2018-01-05,0.83,0.93
        2018-01-06,0.66,0.71
        2018-01-08,0.41,0.6
        2018-01-09,0.83,0.82
        2019-01-10,0.69,0.82
        """
        )
        df_str = io.StringIO(df_str)
        df = pd.read_csv(df_str, index_col=0)
        #
        window = 5
        func = lambda x: np.mean(x, axis=0)
        df_act = cpanhelp.df_rolling_apply(df, window, func)
        #
        df_exp = df.rolling(window).apply(func, raw=True)
        # Check.
        exp_val = [0.720, 0.574]
        np.testing.assert_array_almost_equal(
            df.loc["2018-01-01":"2018-01-06"].mean().tolist(),  # type: ignore
            exp_val,
        )
        np.testing.assert_array_almost_equal(
            df_act.loc["2018-01-06"].tolist(), exp_val
        )
        self.assert_equal(df_act.to_string(), df_exp.to_string())
        self.check_string(df_act.to_string())

    @pytest.mark.slow
    def test2(self) -> None:
        """
        Test with function returning a pd.Series.
        """
        df = pd.DataFrame(np.random.rand(100, 2).round(2), columns=["A", "B"])
        #
        window = 5
        func = lambda x: np.mean(x, axis=0)
        df_act = cpanhelp.df_rolling_apply(df, window, func)
        #
        df_exp = df.rolling(window).apply(func, raw=True)
        # Check.
        self.assert_equal(df_act.to_string(), df_exp.to_string())
        self.check_string(df_act.to_string())

    @pytest.mark.slow
    def test3(self) -> None:
        """
        Test with function returning a pd.DataFrame.
        """
        df = pd.DataFrame(np.random.rand(100, 2).round(2), columns=["A", "B"])
        #
        window = 5
        func = lambda x: pd.DataFrame(np.mean(x, axis=0))
        df_act = cpanhelp.df_rolling_apply(df, window, func)
        #
        func = np.mean
        df_exp = df.rolling(window).apply(func, raw=True)
        # Convert to an equivalent format.
        df_exp = pd.DataFrame(df_exp.stack(dropna=False))
        # Check.
        self.assert_equal(df_act.to_string(), df_exp.to_string())
        self.check_string(df_act.to_string())

    @pytest.mark.slow
    def test4(self) -> None:
        """
        Test with function returning a pd.DataFrame with multiple lines.
        """
        df = pd.DataFrame(np.random.rand(100, 2).round(2), columns=["A", "B"])
        #
        window = 5
        func = lambda x: pd.DataFrame([np.mean(x, axis=0), np.sum(x)])
        df_act = cpanhelp.df_rolling_apply(df, window, func)
        # Check.
        self.check_string(df_act.to_string())

    def test5(self) -> None:
        """
        Like test1 but with a down-sampled version of the data.
        """
        dts = pd.date_range(start="2009-01-04", end="2009-01-10", freq="1H")
        df = pd.DataFrame(
            np.random.rand(len(dts), 2).round(2), columns=["A", "B"], index=dts
        )
        #
        resampled_index = cpanhelp.resample_index(
            df.index, time=(9, 0), freq="1D"
        )
        self.assertEqual(len(resampled_index), 6)
        #
        window = 5
        func = lambda x: np.mean(x, axis=0)
        df_act = cpanhelp.df_rolling_apply(
            df, window, func, timestamps=resampled_index
        )
        # Check.
        df_tmp = df.loc["2009-01-04 05:00:00":"2009-01-04 09:00:00"]  # type: ignore
        exp_val = [0.592, 0.746]
        np.testing.assert_array_almost_equal(df_tmp.mean().tolist(), exp_val)
        np.testing.assert_array_almost_equal(
            df_act.loc["2009-01-04 09:00:00"].tolist(), exp_val
        )
        #
        df_tmp = df.loc["2009-01-09 05:00:00":"2009-01-09 09:00:00"]  # type: ignore
        exp_val = [0.608, 0.620]
        np.testing.assert_array_almost_equal(df_tmp.mean().tolist(), exp_val)
        np.testing.assert_array_almost_equal(
            df_act.loc["2009-01-09 09:00:00"].tolist(), exp_val
        )
        #
        self.check_string(df_act.to_string())
