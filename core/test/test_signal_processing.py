import collections
import datetime
import logging
import os
import pprint
from typing import Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.signal_processing as csipro
import helpers.git as hgit
import helpers.jupyter as hjupyter
import helpers.printing as hprintin
import helpers.unit_test as huntes

_LOG = logging.getLogger(__name__)


class Test__compute_lagged_cumsum(huntes.TestCase):
    def test1(self) -> None:
        input_df = self._get_df()
        output_df = csipro._compute_lagged_cumsum(input_df, 3)
        self.check_string(
            f"{hprintin.frame('input')}\n"
            f"{huntes.convert_df_to_string(input_df, index=True)}\n"
            f"{hprintin.frame('output')}\n"
            f"{huntes.convert_df_to_string(output_df, index=True)}"
        )

    def test2(self) -> None:
        input_df = self._get_df()
        input_df.columns = ["x", "y1", "y2"]
        output_df = csipro._compute_lagged_cumsum(input_df, 3, ["y1", "y2"])
        self.check_string(
            f"{hprintin.frame('input')}\n"
            f"{huntes.convert_df_to_string(input_df, index=True)}\n"
            f"{hprintin.frame('output')}\n"
            f"{huntes.convert_df_to_string(output_df, index=True)}"
        )

    def test_lag_1(self) -> None:
        input_df = self._get_df()
        input_df.columns = ["x", "y1", "y2"]
        output_df = csipro._compute_lagged_cumsum(input_df, 1, ["y1", "y2"])
        self.check_string(
            f"{hprintin.frame('input')}\n"
            f"{huntes.convert_df_to_string(input_df, index=True)}\n"
            f"{hprintin.frame('output')}\n"
            f"{huntes.convert_df_to_string(output_df, index=True)}"
        )

    @staticmethod
    def _get_df() -> pd.DataFrame:
        df = pd.DataFrame([list(range(10))] * 3).T
        df[1] = df[0] + 1
        df[2] = df[0] + 2
        df.index = pd.date_range(start="2010-01-01", periods=10)
        df.rename(columns=lambda x: f"col_{x}", inplace=True)
        return df


class Test_correlate_with_lagged_cumsum(huntes.TestCase):
    def test1(self) -> None:
        input_df = self._get_arma_df()
        output_df = csipro.correlate_with_lagged_cumsum(
            input_df, 3, y_vars=["y1", "y2"]
        )
        self.check_string(
            f"{hprintin.frame('input')}\n"
            f"{huntes.convert_df_to_string(input_df, index=True)}\n"
            f"{hprintin.frame('output')}\n"
            f"{huntes.convert_df_to_string(output_df, index=True)}"
        )

    def test2(self) -> None:
        input_df = self._get_arma_df()
        output_df = csipro.correlate_with_lagged_cumsum(
            input_df, 3, y_vars=["y1"], x_vars=["x"]
        )
        self.check_string(
            f"{hprintin.frame('input')}\n"
            f"{huntes.convert_df_to_string(input_df, index=True)}\n"
            f"{hprintin.frame('output')}\n"
            f"{huntes.convert_df_to_string(output_df, index=True)}"
        )

    @staticmethod
    def _get_arma_df(seed: int = 0) -> pd.DataFrame:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "2010-01-01", "periods": 40, "freq": "M"}
        srs1 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename("x")
        srs2 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed + 1
        ).rename("y1")
        srs3 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed + 2
        ).rename("y2")
        return pd.concat([srs1, srs2, srs3], axis=1)


class Test_get_symmetric_equisized_bins(huntes.TestCase):
    def test_zero_in_bin_interior_false(self) -> None:
        input_ = pd.Series([-1, 3])
        expected = np.array([-3, -2, -1, 0, 1, 2, 3])
        actual = csipro.get_symmetric_equisized_bins(input_, 1)
        np.testing.assert_array_equal(actual, expected)

    def test_zero_in_bin_interior_true(self) -> None:
        input_ = pd.Series([-1, 3])
        expected = np.array([-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5])
        actual = csipro.get_symmetric_equisized_bins(input_, 1, True)
        np.testing.assert_array_equal(actual, expected)

    def test_infs(self) -> None:
        data = pd.Series([-1, np.inf, -np.inf, 3])
        expected = np.array([-4, -2, 0, 2, 4])
        actual = csipro.get_symmetric_equisized_bins(data, 2)
        np.testing.assert_array_equal(actual, expected)


class Test_compute_rolling_zscore1(huntes.TestCase):
    def test_default_values1(self) -> None:
        """
        Test with default parameters on a heaviside series.
        """
        heaviside = carsigen.get_heaviside(-10, 252, 1, 1).rename("input")
        actual = csipro.compute_rolling_zscore(heaviside, tau=40).rename("output")
        output_df = pd.concat([heaviside, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_default_values2(self) -> None:
        """
        Test for tau with default parameters on a heaviside series.
        """
        heaviside = carsigen.get_heaviside(-10, 252, 1, 1).rename("input")
        actual = csipro.compute_rolling_zscore(heaviside, tau=20).rename("output")
        output_df = pd.concat([heaviside, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_clean1(self) -> None:
        """
        Test on a clean arma series.
        """
        series = self._get_arma_series(seed=1)
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = csipro.compute_rolling_zscore(series, tau=2, atol=0.01).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_clean1(self) -> None:
        """
        Test on a clean arma series when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period, `delay=1` and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = csipro.compute_rolling_zscore(
            series, tau=2, delay=1, atol=0.01
        ).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay1_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_clean1(self) -> None:
        """
        Test on a clean arma series when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period, `delay=2` and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = csipro.compute_rolling_zscore(
            series, tau=2, delay=2, atol=0.01
        ).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    def test_delay2_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = csipro.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = huntes.convert_df_to_string(output_df, index=True)
        self.check_string(output_df_string)

    @staticmethod
    def _get_arma_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([1], [1])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename("input")
        return series


class Test_process_outliers1(huntes.TestCase):
    def test_winsorize1(self) -> None:
        srs = self._get_data1()
        mode = "winsorize"
        lower_quantile = 0.01
        # Check.
        self._helper(srs, mode, lower_quantile)

    def test_set_to_nan1(self) -> None:
        srs = self._get_data1()
        mode = "set_to_nan"
        lower_quantile = 0.01
        # Check.
        self._helper(srs, mode, lower_quantile)

    def test_set_to_zero1(self) -> None:
        srs = self._get_data1()
        mode = "set_to_zero"
        lower_quantile = 0.01
        # Check.
        self._helper(srs, mode, lower_quantile)

    def test_winsorize2(self) -> None:
        srs = self._get_data2()
        mode = "winsorize"
        lower_quantile = 0.2
        # Check.
        self._helper(srs, mode, lower_quantile, num_df_rows=len(srs))

    def test_set_to_nan2(self) -> None:
        srs = self._get_data2()
        mode = "set_to_nan"
        lower_quantile = 0.2
        # Check.
        self._helper(srs, mode, lower_quantile, num_df_rows=len(srs))

    def test_set_to_zero2(self) -> None:
        srs = self._get_data2()
        mode = "set_to_zero"
        lower_quantile = 0.2
        upper_quantile = 0.5
        # Check.
        self._helper(
            srs,
            mode,
            lower_quantile,
            num_df_rows=len(srs),
            upper_quantile=upper_quantile,
        )

    def _helper(
        self,
        srs: pd.Series,
        mode: str,
        lower_quantile: float,
        num_df_rows: int = 10,
        window: int = 100,
        min_periods: Optional[int] = 2,
        **kwargs: Any,
    ) -> None:
        info: collections.OrderedDict = collections.OrderedDict()
        srs_out = csipro.process_outliers(
            srs,
            mode,
            lower_quantile,
            window=window,
            min_periods=min_periods,
            info=info,
            **kwargs,
        )
        txt = []
        txt.append("# info")
        txt.append(pprint.pformat(info))
        txt.append("# srs_out")
        txt.append(str(srs_out.head(num_df_rows)))
        self.check_string("\n".join(txt))

    @staticmethod
    def _get_data1() -> pd.Series:
        np.random.seed(100)
        n = 100000
        data = np.random.normal(loc=0.0, scale=1.0, size=n)
        return pd.Series(data)

    @staticmethod
    def _get_data2() -> pd.Series:
        return pd.Series(range(1, 10))


class Test_compute_smooth_derivative1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        scaling = 2
        order = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_smooth_derivative(
            signal, tau, min_periods, scaling, order
        )
        self.check_string(actual.to_string())


class Test_compute_smooth_moving_average1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_smooth_moving_average(
            signal, tau, min_periods, min_depth, max_depth
        )
        self.check_string(actual.to_string())


class Test_extract_smooth_moving_average_weights(huntes.TestCase):
    def test1(self) -> None:
        """
        Perform a typical application.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=1.4,
            index_location=15,
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test2(self) -> None:
        """
        Like `test1()`, but with `tau` varied.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=16,
            index_location=15,
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test3(self) -> None:
        """
        Like `test2()`, but with `min_depth` and `max_depth` increased.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=16,
            min_depth=2,
            max_depth=2,
            index_location=15,
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test4(self) -> None:
        """
        Use a datatime index instead of a range index.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=16,
            index_location=datetime.datetime(2001, 1, 24),
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test5(self) -> None:
        """
        Like `test4()`, but with `tau` varied.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=252,
            index_location=datetime.datetime(2001, 1, 24),
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test6(self) -> None:
        """
        Let `index_location` equal its default of `None`.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=252,
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)

    def test7(self) -> None:
        """
        Set `index_location` past `end`.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = csipro.extract_smooth_moving_average_weights(
            df,
            tau=252,
            index_location=datetime.datetime(2001, 2, 1),
        )
        actual = huntes.convert_df_to_string(
            weights.round(5), index=True, decimals=5
        )
        self.check_string(actual)


class Test_digitize1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        bins = [0, 0.2, 0.4]
        right = False
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.digitize(signal, bins, right)
        self.check_string(actual.to_string())

    def test_heaviside1(self) -> None:
        heaviside = carsigen.get_heaviside(-10, 20, 1, 1)
        bins = [0, 0.2, 0.4]
        right = False
        actual = csipro.digitize(heaviside, bins, right)
        self.check_string(actual.to_string())


class Test_compute_rolling_moment1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_moment(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_norm1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_norm(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_var1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_var(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_std1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_std(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_demean1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_demean(
            signal, tau, min_periods, min_depth, max_depth
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_skew1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau_z = 40
        tau_s = 20
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_skew(
            signal, tau_z, tau_s, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_kurtosis1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau_z = 40
        tau_s = 20
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_kurtosis(
            signal, tau_z, tau_s, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_sharpe_ratio1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = csipro.compute_rolling_sharpe_ratio(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_corr1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        demean = True
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        df = pd.DataFrame(np.random.randn(n, 2))
        signal1 = df[0]
        signal2 = df[1]
        actual = csipro.compute_rolling_corr(
            signal1,
            signal2,
            tau,
            demean,
            min_periods,
            min_depth,
            max_depth,
            p_moment,
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_zcorr1(huntes.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        demean = True
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        df = pd.DataFrame(np.random.randn(n, 2))
        signal1 = df[0]
        signal2 = df[1]
        actual = csipro.compute_rolling_zcorr(
            signal1,
            signal2,
            tau,
            demean,
            min_periods,
            min_depth,
            max_depth,
            p_moment,
        )
        self.check_string(actual.to_string())


class Test_compute_ipca(huntes.TestCase):
    def test1(self) -> None:
        """
        Test for a clean input.
        """
        df = self._get_df(seed=1)
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test2(self) -> None:
        """
        Test for an input with leading NaNs in only a subset of cols.
        """
        df = self._get_df(seed=1)
        df.iloc[0:3, :-3] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test3(self) -> None:
        """
        Test for an input with interspersed NaNs.
        """
        df = self._get_df(seed=1)
        df.iloc[5:8, 3:5] = np.nan
        df.iloc[2:4, 8:] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test4(self) -> None:
        """
        Test for an input with a full-NaN row among the 3 first rows.

        The eigenvalue estimates aren't in sorted order but should be.
        TODO(*): Fix problem with not sorted eigenvalue estimates.
        """
        df = self._get_df(seed=1)
        df.iloc[1:2, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test5(self) -> None:
        """
        Test for an input with 5 leading NaNs in all cols.
        """
        df = self._get_df(seed=1)
        df.iloc[:5, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test6(self) -> None:
        """
        Test for interspersed all-NaNs rows.
        """
        df = self._get_df(seed=1)
        df.iloc[0:1, :] = np.nan
        df.iloc[2:3, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csipro.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        """
        Generate a dataframe via `carsigen.MultivariateNormalProcess()`.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=seed)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=seed
        )
        return df


class Test__compute_ipca_step(huntes.TestCase):
    def test1(self) -> None:
        """
        Test for clean input series.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        alpha = 0.5
        u_next, v_next = csipro._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test2(self) -> None:
        """
        Test for input series with all zeros.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[:] = 0
        v[:] = 0
        alpha = 0.5
        u_next, v_next = csipro._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test3(self) -> None:
        """
        Test that u == u_next for the case when np.linalg.norm(v)=0.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        v[:] = 0
        alpha = 0.5
        u_next, v_next = csipro._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test4(self) -> None:
        """
        Test for input series with all NaNs.

        Output is not intended.
        TODO(Dan): implement a way to deal with NaNs in the input.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[:] = np.nan
        v[:] = np.nan
        alpha = 0.5
        u_next, v_next = csipro._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test5(self) -> None:
        """
        Test for input series with some NaNs.

        Output is not intended.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[3:6] = np.nan
        v[5:8] = np.nan
        alpha = 0.5
        u_next, v_next = csipro._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    @staticmethod
    def _get_output_txt(
        u: pd.Series, v: pd.Series, u_next: pd.Series, v_next: pd.Series
    ) -> str:
        """
        Create string output for tests results.
        """
        u_string = huntes.convert_df_to_string(u, index=True)
        v_string = huntes.convert_df_to_string(v, index=True)
        u_next_string = huntes.convert_df_to_string(u_next, index=True)
        v_next_string = huntes.convert_df_to_string(v_next, index=True)
        txt = (
            f"u:\n{u_string}\n"
            f"v:\n{v_string}\n"
            f"u_next:\n{u_next_string}\n"
            f"v_next:\n{v_next_string}"
        )
        return txt


@pytest.mark.slow
class Test_gallery_signal_processing1(huntes.TestCase):
    def test_notebook1(self) -> None:
        file_name = os.path.join(
            hgit.get_amp_abs_path(),
            "core/notebooks/gallery_signal_processing.ipynb",
        )
        scratch_dir = self.get_scratch_space()
        hjupyter.run_notebook(file_name, scratch_dir)


class TestProcessNonfinite1(huntes.TestCase):
    def test1(self) -> None:
        series = self._get_messy_series(1)
        actual = csipro.process_nonfinite(series)
        actual_string = huntes.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_messy_series(1)
        actual = csipro.process_nonfinite(series, remove_nan=False)
        actual_string = huntes.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_messy_series(1)
        actual = csipro.process_nonfinite(series, remove_inf=False)
        actual_string = huntes.convert_df_to_string(actual, index=True)
        self.check_string(actual_string)

    @staticmethod
    def _get_messy_series(seed: int) -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        series[:5] = 0
        series[-5:] = np.nan
        series[10:13] = np.inf
        series[13:16] = -np.inf
        return series


class Test_compute_rolling_annualized_sharpe_ratio(huntes.TestCase):
    def test1(self) -> None:
        ar_params: List[float] = []
        ma_params: List[float] = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        rolling_sr = csipro.compute_rolling_annualized_sharpe_ratio(
            realization, tau=16, points_per_year=260.875
        )
        self.check_string(huntes.convert_df_to_string(rolling_sr, index=True))


class Test_get_swt(huntes.TestCase):
    def test_clean1(self) -> None:
        """
        Test for default values.
        """
        series = self._get_series(seed=1, periods=40)
        actual = csipro.get_swt(series, wavelet="haar")
        output_str = self._get_tuple_output_txt(actual)
        self.check_string(output_str)

    def test_timing_mode1(self) -> None:
        """
        Test for timing_mode="knowledge_time".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(
            series, wavelet="haar", timing_mode="knowledge_time"
        )
        output_str = self._get_tuple_output_txt(actual)
        self.check_string(output_str)

    def test_timing_mode2(self) -> None:
        """
        Test for timing_mode="zero_phase".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(series, wavelet="haar", timing_mode="zero_phase")
        output_str = self._get_tuple_output_txt(actual)
        self.check_string(output_str)

    def test_timing_mode3(self) -> None:
        """
        Test for timing_mode="raw".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(series, wavelet="haar", timing_mode="raw")
        output_str = self._get_tuple_output_txt(actual)
        self.check_string(output_str)

    def test_output_mode1(self) -> None:
        """
        Test for output_mode="tuple".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(series, wavelet="haar", output_mode="tuple")
        output_str = self._get_tuple_output_txt(actual)
        self.check_string(output_str)

    def test_output_mode2(self) -> None:
        """
        Test for output_mode="smooth".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(series, wavelet="haar", output_mode="smooth")
        actual_str = huntes.convert_df_to_string(actual, index=True)
        output_str = f"smooth_df:\n{actual_str}\n"
        self.check_string(output_str)

    def test_output_mode3(self) -> None:
        """
        Test for output_mode="detail".
        """
        series = self._get_series(seed=1)
        actual = csipro.get_swt(series, wavelet="haar", output_mode="detail")
        actual_str = huntes.convert_df_to_string(actual, index=True)
        output_str = f"detail_df:\n{actual_str}\n"
        self.check_string(output_str)

    def test_depth(self) -> None:
        """
        Test for sufficient input data length given `depth`.
        """
        series = self._get_series(seed=1, periods=10)
        # The test should not raise on this call.
        csipro.get_swt(series, depth=2, output_mode="detail")
        with pytest.raises(ValueError):
            # The raise comes from the `get_swt` implementation.
            csipro.get_swt(series, depth=3, output_mode="detail")
        with pytest.raises(ValueError):
            # This raise comes from `pywt`.
            csipro.get_swt(series, depth=5, output_mode="detail")

    @staticmethod
    def _get_series(seed: int, periods: int = 20) -> pd.Series:
        arma_process = carsigen.ArmaProcess([0], [0])
        date_range = {"start": "1/1/2010", "periods": periods, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        )
        return series

    @staticmethod
    def _get_tuple_output_txt(
        output: Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]
    ) -> str:
        """
        Create string output for a tuple type return.
        """
        smooth_df_string = huntes.convert_df_to_string(output[0], index=True)
        detail_df_string = huntes.convert_df_to_string(output[1], index=True)
        output_str = (
            f"smooth_df:\n{smooth_df_string}\n"
            f"\ndetail_df\n{detail_df_string}\n"
        )
        return output_str


class Test_compute_swt_var(huntes.TestCase):
    def test1(self) -> None:
        srs = self._get_data(seed=0)
        swt_var = csipro.compute_swt_var(srs, depth=6)
        actual = swt_var.count().values[0]
        np.testing.assert_equal(actual, 1179)

    def test2(self) -> None:
        srs = self._get_data(seed=0)
        swt_var = csipro.compute_swt_var(srs, depth=6)
        actual = swt_var.sum()
        np.testing.assert_allclose(actual, [1102.66], atol=0.01)

    def test3(self) -> None:
        srs = self._get_data(seed=0)
        swt_var = csipro.compute_swt_var(srs, depth=6, axis=1)
        actual = swt_var.sum()
        np.testing.assert_allclose(actual, [1102.66], atol=0.01)

    def _get_data(self, seed: int) -> pd.Series:
        process = carsigen.ArmaProcess([], [])
        realization = process.generate_sample(
            {"start": "2000-01-01", "end": "2005-01-01", "freq": "B"}, seed=seed
        )
        return realization


class Test_resample_srs(huntes.TestCase):

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
            csipro.resample(series, rule=rule)
            .sum()
            .rename(f"Output in freq='{rule}'")
        )
        actual_closed_left = (
            csipro.resample(series, rule=rule, closed="left")
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
            csipro.resample(series, rule="M").sum().rename("Output in freq='M'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="M", closed="left")
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
            csipro.resample(series, rule="W").sum().rename("Output in freq='W'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="W", closed="left")
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
            csipro.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="B", closed="left")
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
            csipro.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="D", closed="left")
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
            csipro.resample(series, rule="T").sum().rename("Output in freq='T'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="T", closed="left")
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
            csipro.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="B", closed="left")
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
            csipro.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="D", closed="left")
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
            csipro.resample(series, rule="D").sum().rename("Output in freq='D'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="D", closed="left")
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
            csipro.resample(series, rule="B").sum().rename("Output in freq='B'")
        )
        actual_closed_left = (
            csipro.resample(series, rule="B", closed="left")
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
        input_string = huntes.convert_df_to_string(input_data, index=True)
        output_default_string = huntes.convert_df_to_string(
            output_default, index=True
        )
        output_closed_left_string = huntes.convert_df_to_string(
            output_closed_left, index=True
        )
        txt = (
            f"Input:\n{input_string}\n\n"
            f"Output with default arguments:\n{output_default_string}\n\n"
            f"Output with closed='left':\n{output_closed_left_string}\n"
        )
        return txt


class Test_resample_df(huntes.TestCase):

    # Converting days to other units.
    def test_day_to_year1(self) -> None:
        """
        Test freq="D", unit="Y".
        """
        df = self._get_df(seed=1, periods=9, freq="D")
        actual_default = csipro.resample(df, rule="Y").sum()
        actual_default.columns = [
            "1st output in freq='Y'",
            "2nd output in freq='Y'",
        ]
        actual_closed_left = csipro.resample(df, rule="Y", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="M").sum()
        actual_default.columns = [
            "1st output in freq='M'",
            "2nd output in freq='M'",
        ]
        actual_closed_left = csipro.resample(df, rule="M", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="W").sum()
        actual_default.columns = [
            "1st output in freq='W'",
            "2nd output in freq='W'",
        ]
        actual_closed_left = csipro.resample(df, rule="W", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = csipro.resample(df, rule="B", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = csipro.resample(df, rule="D", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="T").sum()
        actual_default.columns = [
            "1st output in freq='T'",
            "2nd output in freq='T'",
        ]
        actual_closed_left = csipro.resample(df, rule="T", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = csipro.resample(df, rule="B", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = csipro.resample(df, rule="D", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="D").sum()
        actual_default.columns = [
            "1st output in freq='D'",
            "2nd output in freq='D'",
        ]
        actual_closed_left = csipro.resample(df, rule="D", closed="left").sum()
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
        actual_default = csipro.resample(df, rule="B").sum()
        actual_default.columns = [
            "1st output in freq='B'",
            "2nd output in freq='B'",
        ]
        actual_closed_left = csipro.resample(df, rule="B", closed="left").sum()
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
        input_string = huntes.convert_df_to_string(input_data, index=True)
        output_default_string = huntes.convert_df_to_string(
            output_default, index=True
        )
        output_closed_left_string = huntes.convert_df_to_string(
            output_closed_left, index=True
        )
        txt = (
            f"Input:\n{input_string}\n\n"
            f"Output with default arguments:\n{output_default_string}\n\n"
            f"Output with closed='left':\n{output_closed_left_string}\n"
        )
        return txt


# TODO(Paul): Rename test. Do not use file for golden.
class Test_calculate_inverse(huntes.TestCase):
    def test1(self) -> None:
        df = pd.DataFrame([[1, 2], [3, 4]])
        inverse_df = huntes.convert_df_to_string(
            csipro.compute_inverse(df), index=True
        )
        self.check_string(inverse_df)


# TODO(Paul): Rename test. Do not use file for golden.
class Test_calculate_presudoinverse(huntes.TestCase):
    def test1(self) -> None:
        df = pd.DataFrame([[1, 2], [3, 4], [5, 6]])
        inverse_df = huntes.convert_df_to_string(
            csipro.compute_pseudoinverse(df), index=True
        )
        self.check_string(inverse_df)
