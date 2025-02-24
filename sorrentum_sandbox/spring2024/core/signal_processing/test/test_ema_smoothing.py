import datetime
import logging
from typing import List

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing.ema_smoothing as cspremsm
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_smooth_derivative1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        scaling = 2
        order = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_smooth_derivative(
            signal, tau, min_periods, scaling, order
        )
        self.check_string(actual.to_string())


class Test_compute_smooth_moving_average1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_smooth_moving_average(
            signal, tau, min_periods, min_depth, max_depth
        )
        self.check_string(actual.to_string())


class Test_extract_smooth_moving_average_weights(hunitest.TestCase):
    def test1(self) -> None:
        """
        Perform a typical application.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=1.4,
            index_location=15,
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test2(self) -> None:
        """
        Like `test1()`, but with `tau` varied.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=16,
            index_location=15,
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test3(self) -> None:
        """
        Like `test2()`, but with `min_depth` and `max_depth` increased.
        """
        df = pd.DataFrame(index=range(0, 20))
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=16,
            min_depth=2,
            max_depth=2,
            index_location=15,
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test4(self) -> None:
        """
        Use a datatime index instead of a range index.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=16,
            index_location=datetime.datetime(2001, 1, 24),
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test5(self) -> None:
        """
        Like `test4()`, but with `tau` varied.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=252,
            index_location=datetime.datetime(2001, 1, 24),
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test6(self) -> None:
        """
        Let `index_location` equal its default of `None`.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=252,
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)

    def test7(self) -> None:
        """
        Set `index_location` past `end`.
        """
        df = pd.DataFrame(
            index=pd.date_range(start="2001-01-04", end="2001-01-31", freq="B")
        )
        weights = cspremsm.extract_smooth_moving_average_weights(
            df,
            tau=252,
            index_location=datetime.datetime(2001, 2, 1),
        )
        actual = hpandas.df_to_str(
            weights.round(5), num_rows=None, precision=5
        )
        self.check_string(actual)


class Test_compute_rolling_moment1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_moment(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_norm1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_norm(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_var1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_var(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_std1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_std(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_demean1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_demean(
            signal, tau, min_periods, min_depth, max_depth
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_skew1(hunitest.TestCase):
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
        actual = cspremsm.compute_rolling_skew(
            signal, tau_z, tau_s, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_kurtosis1(hunitest.TestCase):
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
        actual = cspremsm.compute_rolling_kurtosis(
            signal, tau_z, tau_s, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_sharpe_ratio1(hunitest.TestCase):
    def test1(self) -> None:
        np.random.seed(42)
        tau = 40
        min_periods = 20
        min_depth = 1
        max_depth = 5
        p_moment = 2
        n = 1000
        signal = pd.Series(np.random.randn(n))
        actual = cspremsm.compute_rolling_sharpe_ratio(
            signal, tau, min_periods, min_depth, max_depth, p_moment
        )
        self.check_string(actual.to_string())


class Test_compute_rolling_corr1(hunitest.TestCase):
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
        actual = cspremsm.compute_rolling_corr(
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


class Test_compute_rolling_zcorr1(hunitest.TestCase):
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
        actual = cspremsm.compute_rolling_zcorr(
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


class Test_compute_rolling_zscore1(hunitest.TestCase):
    def test_default_values1(self) -> None:
        """
        Test with default parameters on a heaviside series.
        """
        heaviside = carsigen.get_heaviside(-10, 252, 1, 1).rename("input")
        actual = cspremsm.compute_rolling_zscore(heaviside, tau=40).rename(
            "output"
        )
        output_df = pd.concat([heaviside, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_default_values2(self) -> None:
        """
        Test for tau with default parameters on a heaviside series.
        """
        heaviside = carsigen.get_heaviside(-10, 252, 1, 1).rename("input")
        actual = cspremsm.compute_rolling_zscore(heaviside, tau=20).rename(
            "output"
        )
        output_df = pd.concat([heaviside, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_clean1(self) -> None:
        """
        Test on a clean arma series.
        """
        series = self._get_arma_series(seed=1)
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=2, atol=0.01).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_clean1(self) -> None:
        """
        Test on a clean arma series when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period, `delay=1` and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = cspremsm.compute_rolling_zscore(
            series, tau=2, delay=1, atol=0.01
        ).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay1_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs when `delay=1`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=1).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_clean1(self) -> None:
        """
        Test on a clean arma series when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_nan1(self) -> None:
        """
        Test on an arma series with leading NaNs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_nan2(self) -> None:
        """
        Test on an arma series with interspersed NaNs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.nan
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_zero1(self) -> None:
        """
        Test on an arma series with leading zeros when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_zero2(self) -> None:
        """
        Test on an arma series with interspersed zeros when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = 0
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_atol1(self) -> None:
        """
        Test on an arma series with all-zeros period, `delay=2` and `atol>0`.
        """
        series = self._get_arma_series(seed=1)
        series[10:25] = 0
        actual = cspremsm.compute_rolling_zscore(
            series, tau=2, delay=2, atol=0.01
        ).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_inf1(self) -> None:
        """
        Test on an arma series with leading infs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[:5] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test_delay2_arma_inf2(self) -> None:
        """
        Test on an arma series with interspersed infs when `delay=2`.
        """
        series = self._get_arma_series(seed=1)
        series[5:10] = np.inf
        actual = cspremsm.compute_rolling_zscore(series, tau=20, delay=2).rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    @staticmethod
    def _get_arma_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([1], [1])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename("input")
        return series


class Test_compute_rolling_annualized_sharpe_ratio(hunitest.TestCase):
    def test1(self) -> None:
        ar_params: List[float] = []
        ma_params: List[float] = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        rolling_sr = cspremsm.compute_rolling_annualized_sharpe_ratio(
            realization, tau=16, points_per_year=260.875
        )
        self.check_string(hpandas.df_to_str(rolling_sr, num_rows=None))
