import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.descriptive as cstadesc
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeMoments(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_moments(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_moments(series, prefix="moments_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test3(self) -> None:
        series = pd.Series(dtype="float64")
        cstadesc.compute_moments(series)

    def test4(self) -> None:
        series = self._get_series(seed=1)
        # Place some `NaN` values in the series.
        series[:5] = np.nan
        series[8:10] = np.nan
        actual = cstadesc.compute_moments(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        series = self._get_series(seed=1)
        # Place some `NaN` values in the series.
        series[:5] = np.nan
        series[8:10] = np.nan
        actual = cstadesc.compute_moments(
            series, nan_mode="ffill_and_drop_leading"
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for input of `np.nan`s.
    def test6(self) -> None:
        series = pd.Series([np.nan for i in range(10)])
        cstadesc.compute_moments(series)

    def test7(self) -> None:
        """
        Test series with `inf`.
        """
        series = self._get_series(seed=1)
        # Place some `NaN` values in the series.
        series[4] = np.inf
        actual = cstadesc.compute_moments(
            series, nan_mode="ffill_and_drop_leading"
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series


class TestComputeFracZero(hunitest.TestCase):
    def test1(self) -> None:
        data = [0.466667, 0.2, 0.13333, 0.2, 0.33333]
        index = [0, 1, 2, 3, 4]
        expected = pd.Series(data=data, index=index)
        actual = cstadesc.compute_frac_zero(self._get_df(seed=1))
        pd.testing.assert_series_equal(actual, expected, atol=1e-03)

    def test2(self) -> None:
        data = [
            0.4,
            0.0,
            0.2,
            0.4,
            0.4,
            0.2,
            0.4,
            0.0,
            0.6,
            0.4,
            0.6,
            0.2,
            0.0,
            0.0,
            0.2,
        ]
        index = pd.date_range(start="1-04-2018", periods=15, freq="30T")
        expected = pd.Series(data=data, index=index)
        actual = cstadesc.compute_frac_zero(self._get_df(seed=1), axis=1)
        pd.testing.assert_series_equal(actual, expected, atol=1e-03)

    def test3(self) -> None:
        # Equals 20 / 75 = num_zeros / num_points.
        expected = 0.266666
        actual = cstadesc.compute_frac_zero(self._get_df(seed=1), axis=None)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test4(self) -> None:
        series = self._get_df(seed=1)[0]
        expected = 0.466667
        actual = cstadesc.compute_frac_zero(series)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test5(self) -> None:
        series = self._get_df(seed=1)[0]
        expected = 0.466667
        actual = cstadesc.compute_frac_zero(series, axis=0)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    # Smoke test for empty input.
    def test6(self) -> None:
        series = pd.Series(dtype="float64")
        cstadesc.compute_frac_zero(series)

    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        nrows = 15
        ncols = 5
        num_nans = 15
        num_infs = 5
        num_zeros = 20
        #
        np.random.seed(seed=seed)
        mat = np.random.randn(nrows, ncols)
        mat.ravel()[np.random.choice(mat.size, num_nans, replace=False)] = np.nan
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = np.inf
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = -np.inf
        mat.ravel()[np.random.choice(mat.size, num_zeros, replace=False)] = 0
        #
        index = pd.date_range(start="01-04-2018", periods=nrows, freq="30T")
        df = pd.DataFrame(data=mat, index=index)
        return df


class TestComputeFracNan(hunitest.TestCase):
    def test1(self) -> None:
        data = [0.4, 0.133333, 0.133333, 0.133333, 0.2]
        index = [0, 1, 2, 3, 4]
        expected = pd.Series(data=data, index=index)
        actual = cstadesc.compute_frac_nan(self._get_df(seed=1))
        pd.testing.assert_series_equal(actual, expected, atol=1e-03)

    def test2(self) -> None:
        data = [
            0.4,
            0.0,
            0.2,
            0.4,
            0.2,
            0.2,
            0.2,
            0.0,
            0.4,
            0.2,
            0.6,
            0.0,
            0.0,
            0.0,
            0.2,
        ]
        index = pd.date_range(start="1-04-2018", periods=15, freq="30T")
        expected = pd.Series(data=data, index=index)
        actual = cstadesc.compute_frac_nan(self._get_df(seed=1), axis=1)
        pd.testing.assert_series_equal(actual, expected, atol=1e-03)

    def test3(self) -> None:
        # Equals 15 / 75 = num_nans / num_points.
        expected = 0.2
        actual = cstadesc.compute_frac_nan(self._get_df(seed=1), axis=None)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test4(self) -> None:
        series = self._get_df(seed=1)[0]
        expected = 0.4
        actual = cstadesc.compute_frac_nan(series)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test5(self) -> None:
        series = self._get_df(seed=1)[0]
        expected = 0.4
        actual = cstadesc.compute_frac_nan(series, axis=0)
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    # Smoke test for empty input.
    def test6(self) -> None:
        series = pd.Series(dtype="float64")
        cstadesc.compute_frac_nan(series)

    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        nrows = 15
        ncols = 5
        num_nans = 15
        num_infs = 5
        num_zeros = 20
        #
        np.random.seed(seed=seed)
        mat = np.random.randn(nrows, ncols)
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = np.inf
        mat.ravel()[np.random.choice(mat.size, num_infs, replace=False)] = -np.inf
        mat.ravel()[np.random.choice(mat.size, num_zeros, replace=False)] = 0
        mat.ravel()[np.random.choice(mat.size, num_nans, replace=False)] = np.nan
        #
        index = pd.date_range(start="01-04-2018", periods=nrows, freq="30T")
        df = pd.DataFrame(data=mat, index=index)
        return df


class TestComputeNumFiniteSamples(hunitest.TestCase):
    @staticmethod
    # Smoke test for empty input.
    def test1() -> None:
        series = pd.Series(dtype="float64")
        cstadesc.count_num_finite_samples(series)


class TestComputeNumUniqueValues(hunitest.TestCase):
    @staticmethod
    # Smoke test for empty input.
    def test1() -> None:
        series = pd.Series(dtype="float64")
        cstadesc.count_num_unique_values(series)


class TestComputeDenominatorAndPackage(hunitest.TestCase):
    @staticmethod
    # Smoke test for empty input.
    def test1() -> None:
        series = pd.Series(dtype="float64")
        cstadesc._compute_denominator_and_package(reduction=1, data=series)


class TestComputeSpecialValueStats(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for default arguments.
        """
        series = self._get_messy_series(seed=1)
        actual = cstadesc.compute_special_value_stats(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test for prefix.
        """
        series = self._get_messy_series(seed=1)
        actual = cstadesc.compute_special_value_stats(series, prefix="data_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test3(self) -> None:
        series = pd.Series(dtype="float64")
        cstadesc.compute_special_value_stats(series)

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


class Test_compute_jensen_ratio(hunitest.TestCase):
    def test1(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstadesc.compute_jensen_ratio(
            signal,
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstadesc.compute_jensen_ratio(
            signal,
            p_norm=3,
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        signal = self._get_signal(seed=1)
        signal[5:8] = np.inf
        actual = cstadesc.compute_jensen_ratio(
            signal,
            inf_mode="drop",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstadesc.compute_jensen_ratio(
            signal,
            nan_mode="ffill",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstadesc.compute_jensen_ratio(
            signal,
            prefix="commodity_",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test6(self) -> None:
        signal = pd.Series(dtype="float64")
        cstadesc.compute_jensen_ratio(signal)

    @staticmethod
    def _get_signal(seed: int) -> pd.Series:
        np.random.seed(seed)
        n = 1000
        signal = pd.Series(np.random.randn(n))
        signal[30:50] = np.nan
        return signal


class Test_compute_t_distribution_j_2(hunitest.TestCase):
    def test_almost_normal(self) -> None:
        actual = cstadesc.compute_t_distribution_j_2(200)
        np.testing.assert_allclose(actual, np.sqrt(2 / np.pi), atol=1e-2)

    def test_4dof(self) -> None:
        actual = cstadesc.compute_t_distribution_j_2(4)
        np.testing.assert_allclose(actual, 0.707107, atol=1e-5)

    def test_2dof(self) -> None:
        actual = cstadesc.compute_t_distribution_j_2(2)
        np.testing.assert_allclose(actual, 0)


class TestComputeZeroDiffProportion(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_zero_diff_proportion(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_zero_diff_proportion(series, atol=1)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_zero_diff_proportion(series, rtol=0.3)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_zero_diff_proportion(
            series, nan_mode="fill_with_zero"
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test6(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadesc.compute_zero_diff_proportion(series, prefix="prefix_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test7(self) -> None:
        series = pd.Series(dtype="float64")
        cstadesc.compute_zero_diff_proportion(series)

    def test8(self) -> None:
        """
        Test constant series with `NaN`s in between, default `nan_mode`.
        """
        series = pd.Series(
            [1, np.nan, 1, np.nan],
            index=pd.date_range(start="2010-01-01", periods=4),
        )
        actual = cstadesc.compute_zero_diff_proportion(series)
        output_str = (
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test9(self) -> None:
        """
        Test constant series with `NaN`s in between, "drop".
        """
        series = pd.Series(
            [1, np.nan, 1, np.nan],
            index=pd.date_range(start="2010-01-01", periods=4),
        )
        nan_mode = "drop"
        actual = cstadesc.compute_zero_diff_proportion(series, nan_mode=nan_mode)
        output_str = (
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame(f'output, `nan_mode`=`{nan_mode}`')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test10(self) -> None:
        """
        Test constant series with `NaN`s in between for "ffill".
        """
        series = pd.Series(
            [1, np.nan, np.nan, 1, np.nan],
            index=pd.date_range(start="2010-01-01", periods=5),
        )
        nan_mode = "ffill"
        actual = cstadesc.compute_zero_diff_proportion(series, nan_mode=nan_mode)
        output_str = (
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame(f'output, `nan_mode`=`{nan_mode}`')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test11(self) -> None:
        """
        Test series with consecutive `NaN`s.
        """
        series = pd.Series(
            [1, np.nan, np.nan, 2],
            index=pd.date_range(start="2010-01-01", periods=4),
        )
        nan_mode = "leave_unchanged"
        actual = cstadesc.compute_zero_diff_proportion(series, nan_mode=nan_mode)
        output_str = (
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame(f'output, `nan_mode`=`{nan_mode}`')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test12(self) -> None:
        """
        Test series with consecutive `NaN`s, "ffill".
        """
        series = pd.Series(
            [1, np.nan, np.nan, 2],
            index=pd.date_range(start="2010-01-01", periods=4),
        )
        nan_mode = "ffill"
        actual = cstadesc.compute_zero_diff_proportion(series, nan_mode=nan_mode)
        output_str = (
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame(f'output, `nan_mode`=`{nan_mode}`')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        np.random.seed(seed=seed)
        n_elements = 100
        index = pd.date_range(start="1-04-2018", periods=n_elements, freq="D")
        data = list(np.random.randint(10, size=n_elements))
        series = pd.Series(data=data, index=index, name="test")
        series[45:47] = np.nan
        series[47:50] = np.inf
        return series


class Test_summarize_time_index_info(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for the case when index freq is not None.
        """
        series = self._get_series(seed=1)
        actual = cstadesc.summarize_time_index_info(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test for the case when index freq is None.
        """
        series = self._get_series(seed=1)
        series = series.drop(series.index[1:3])
        actual = cstadesc.summarize_time_index_info(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test for default nan_mode.
        """
        series = self._get_series(seed=1)
        series[0] = np.nan
        series[-1] = np.nan
        series[5:25] = np.nan
        actual = cstadesc.summarize_time_index_info(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test4(self) -> None:
        """
        Test for specified nan_mode.
        """
        series = self._get_series(seed=1)
        series[0] = np.nan
        series[-1] = np.nan
        series[5:25] = np.nan
        actual = cstadesc.summarize_time_index_info(
            series, nan_mode="fill_with_zero"
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test5(self) -> None:
        """
        Test for prefix.
        """
        series = self._get_series(seed=1)
        actual = cstadesc.summarize_time_index_info(series, prefix="test_")
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test6(self) -> None:
        """
        Test `NaN` series.
        """
        date_range_kwargs = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = pd.Series(np.nan, index=pd.date_range(**date_range_kwargs))
        actual = cstadesc.summarize_time_index_info(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    def test7(self) -> None:
        """
        Test empty series.
        """
        series = pd.Series(index=pd.DatetimeIndex([]))
        actual = cstadesc.summarize_time_index_info(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None, precision=3)
        self.check_string(actual_string, fuzzy_match=True)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = hpandas.get_random_df(
            num_cols=1,
            seed=seed,
            date_range_kwargs=date_range,
        )[0]
        return series
