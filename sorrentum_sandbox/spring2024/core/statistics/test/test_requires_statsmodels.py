import logging

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.signal_processing as csigproc
import core.statistics.requires_statsmodels as cstresta
import core.statistics.returns_and_volatility as csreanvo
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeKratio(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for an clean input series.
        """
        series = self._get_series(seed=1)
        actual = cstresta.compute_kratio(series)
        expected = -0.84551
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test2(self) -> None:
        """
        Test for an input with NaN values.
        """
        series = self._get_series(seed=1)
        series[:3] = np.nan
        series[7:10] = np.nan
        actual = cstresta.compute_kratio(series)
        expected = -0.85089
        np.testing.assert_almost_equal(actual, expected, decimal=3)

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


class TestMultipleTests(hunitest.TestCase):

    # Smoke test for empty input.
    def test1(self) -> None:
        series = pd.Series(dtype="float64")
        cstresta.multipletests(series)

    # Test if error is raised with default arguments when input contains NaNs.
    @pytest.mark.xfail()
    def test2(self) -> None:
        series_with_nans = self._get_series(seed=1)
        series_with_nans[0:5] = np.nan
        actual = cstresta.multipletests(series_with_nans)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series_with_nans = self._get_series(seed=1)
        series_with_nans[0:5] = np.nan
        actual = cstresta.multipletests(series_with_nans, nan_mode="drop")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = hpandas.get_random_df(
            num_cols=1,
            seed=seed,
            date_range_kwargs=date_range,
        )[0]
        return series


class TestMultiTTest(hunitest.TestCase):

    # Smoke test for empty input.
    def test1(self) -> None:
        df = pd.DataFrame(columns=["series_name"])
        cstresta.multi_ttest(df)

    def test2(self) -> None:
        df = self._get_df_of_series(seed=1)
        actual = cstresta.multi_ttest(df)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        df = self._get_df_of_series(seed=1)
        actual = cstresta.multi_ttest(df, prefix="multi_ttest_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        df = self._get_df_of_series(seed=1)
        actual = cstresta.multi_ttest(df, popmean=1)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        df = self._get_df_of_series(seed=1)
        actual = cstresta.multi_ttest(df, nan_mode="fill_with_zero")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test6(self) -> None:
        df = self._get_df_of_series(seed=1)
        actual = cstresta.multi_ttest(df, method="sidak")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @pytest.mark.xfail()
    def test7(self) -> None:
        df = self._get_df_of_series(seed=1)
        df.iloc[:, 0] = np.nan
        actual = cstresta.multi_ttest(df)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @staticmethod
    def _get_df_of_series(seed: int) -> pd.DataFrame:
        n_series = 7
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        # Generating a dataframe from different series.
        df = pd.DataFrame(
            [
                arma_process.generate_sample(
                    date_range_kwargs=date_range, seed=seed + i
                )
                for i in range(n_series)
            ],
            index=["series_" + str(i) for i in range(n_series)],
        ).T
        return df


class TestApplyAdfTest(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_adf_test(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_adf_test(series, regression="ctt")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_adf_test(series, maxlag=5)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_adf_test(series, autolag="t-stat")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_adf_test(series, prefix="adf_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test6(self) -> None:
        series = pd.Series(dtype="float64")
        cstresta.apply_adf_test(series)

    def test7(self) -> None:
        series = self._get_series(seed=1)
        series[3:5] = np.nan
        actual = cstresta.apply_adf_test(series, nan_mode="fill_with_zero")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for input of `np.nan`s.
    def test8(self) -> None:
        series = pd.Series([np.nan for i in range(10)])
        cstresta.apply_adf_test(series)

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


class TestApplyKpssTest(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_kpss_test(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_kpss_test(series, regression="ct")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_kpss_test(series, nlags="auto")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_kpss_test(series, nlags=5)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_kpss_test(series, prefix="kpss_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test6(self) -> None:
        series = pd.Series(dtype="float64")
        cstresta.apply_kpss_test(series)

    def test7(self) -> None:
        series = self._get_series(seed=1)
        series[3:5] = np.nan
        actual = cstresta.apply_kpss_test(series, nan_mode="fill_with_zero")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for input of `np.nan`s.
    def test8(self) -> None:
        series = pd.Series([np.nan for i in range(10)])
        cstresta.apply_kpss_test(series)

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


class TestApplyLjungBoxTest(hunitest.TestCase):
    @pytest.mark.skip(reason="cmamp #654.")
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series, lags=3)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @pytest.mark.skip(reason="cmamp #654.")
    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series, model_df=3)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series, period=5)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @pytest.mark.skip(reason="cmamp #654.")
    def test5(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series, prefix="lb_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @pytest.mark.skip(reason="cmamp #654.")
    def test6(self) -> None:
        series = self._get_series(seed=1)
        actual = cstresta.apply_ljung_box_test(series, return_df=False)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test7(self) -> None:
        series = pd.Series(dtype="float64")
        cstresta.apply_ljung_box_test(series)

    @pytest.mark.skip(reason="cmamp #654.")
    def test8(self) -> None:
        series = self._get_series(seed=1)
        series[3:5] = np.nan
        actual = cstresta.apply_ljung_box_test(series, nan_mode="fill_with_zero")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for input of `np.nan`s.
    def test9(self) -> None:
        series = pd.Series([np.nan for i in range(10)])
        cstresta.apply_ljung_box_test(series)

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


class TestCalculateHitRate(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for default parameters.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_97.50%CI_lower_bound_(%)  25.4094
        hit_rate_97.50%CI_upper_bound_(%)  82.7032
        """
        series = self._get_test_series()
        actual = cstresta.calculate_hit_rate(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test for the case when NaNs compose the half of the input.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_97.50%CI_lower_bound_(%)  25.4094
        hit_rate_97.50%CI_upper_bound_(%)  82.7032
        """
        series = self._get_test_series()
        nan_series = pd.Series([np.nan for i in range(len(series))])
        series = pd.concat([series, nan_series])
        actual = cstresta.calculate_hit_rate(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        """
        Test for the case when np.inf compose the half of the input.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_97.50%CI_lower_bound_(%)  25.4094
        hit_rate_97.50%CI_upper_bound_(%)  82.7032
        """
        series = self._get_test_series()
        inf_series = pd.Series([np.inf for i in range(len(series))])
        inf_series[:5] = -np.inf
        series = pd.concat([series, inf_series])
        actual = cstresta.calculate_hit_rate(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        """
        Test for the case when 0 compose the half of the input.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_97.50%CI_lower_bound_(%)  25.4094
        hit_rate_97.50%CI_upper_bound_(%)  82.7032
        """
        series = self._get_test_series()
        zero_series = pd.Series([0 for i in range(len(series))])
        series = pd.concat([series, zero_series])
        actual = cstresta.calculate_hit_rate(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test5(self) -> None:
        """
        Test threshold.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             57.1429
        hit_rate_97.50%CI_lower_bound_(%)  23.4501
        hit_rate_97.50%CI_upper_bound_(%)  86.1136
        """
        series = self._get_test_series()
        actual = cstresta.calculate_hit_rate(series, threshold=10e-3)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test6(self) -> None:
        """
        Test alpha.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_95.00%CI_lower_bound_(%)  29.6768
        hit_rate_95.00%CI_upper_bound_(%)  79.1316
        """
        series = self._get_test_series()
        actual = cstresta.calculate_hit_rate(series, alpha=0.1)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test7(self) -> None:
        """
        Test prefix.

        Expected outcome:                                              0
        hit_hit_rate_point_est_(%)             55.5556
        hit_hit_rate_97.50%CI_lower_bound_(%)  25.4094
        hit_hit_rate_97.50%CI_upper_bound_(%)  82.7032
        """
        series = self._get_test_series()
        actual = cstresta.calculate_hit_rate(series, prefix="hit_")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test8(self) -> None:
        """
        Test method.

        Expected outcome:                                          0
        hit_rate_point_est_(%)             55.5556
        hit_rate_97.50%CI_lower_bound_(%)  26.6651
        hit_rate_97.50%CI_upper_bound_(%)  81.1221
        """
        series = self._get_test_series()
        actual = cstresta.calculate_hit_rate(series, method="wilson")
        self.check_string(hpandas.df_to_str(actual, num_rows=None))

    # Smoke test for empty input.
    def test_smoke(self) -> None:
        series = pd.Series(dtype="float64")
        cstresta.calculate_hit_rate(series)

    # Smoke test for input of `np.nan`s.
    def test_nan(self) -> None:
        series = pd.Series([np.nan] * 10)
        cstresta.calculate_hit_rate(series)

    @staticmethod
    def _get_test_series() -> pd.Series:
        series = pd.Series([0, -0.001, 0.001, -0.01, 0.01, -0.1, 0.1, -1, 1, 10])
        return series


class Test_compute_bet_stats(hunitest.TestCase):
    def test1(self) -> None:
        log_rets = Test_compute_bet_stats._get_series(42)
        positions = csigproc.compute_smooth_moving_average(log_rets, 4)
        actual = cstresta.compute_bet_stats(positions, log_rets)
        bet_rets = csreanvo.compute_returns_per_bet(positions, log_rets)
        rets_pos_bet_rets = pd.concat(
            {"pos": positions, "rets": log_rets, "bet_rets": bet_rets}, axis=1
        )
        self._check_results(rets_pos_bet_rets, actual)

    def test2(self) -> None:
        log_rets = Test_compute_bet_stats._get_series(42)
        positions = csigproc.compute_smooth_moving_average(log_rets, 4)
        log_rets.iloc[:10] = np.nan
        actual = cstresta.compute_bet_stats(positions, log_rets)
        bet_rets = csreanvo.compute_returns_per_bet(positions, log_rets)
        rets_pos_bet_rets = pd.concat(
            {"pos": positions, "rets": log_rets, "bet_rets": bet_rets}, axis=1
        )
        self._check_results(rets_pos_bet_rets, actual)

    def test3(self) -> None:
        idx = pd.date_range("2010-12-29", freq="D", periods=8)
        log_rets = pd.Series([1, 2, 3, 5, 7, 11, -13, -5], index=idx)
        positions = pd.Series([1, 2, 0, 1, -3, -2, 0, -1], index=idx)
        actual = cstresta.compute_bet_stats(positions, log_rets)
        bet_rets = csreanvo.compute_returns_per_bet(positions, log_rets)
        rets_pos_bet_rets = pd.concat(
            {"pos": positions, "rets": log_rets, "bet_rets": bet_rets}, axis=1
        )
        self._check_results(rets_pos_bet_rets, actual)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed, scale=0.1
        )
        return series

    def _check_results(
        self, rets_pos_bet_rets: pd.DataFrame, actual: pd.Series
    ) -> None:
        act = []
        act.append(hprint.frame("rets_pos"))
        act.append(
            hpandas.df_to_str(
                rets_pos_bet_rets, num_rows=None, precision=3
            )
        )
        act.append(hprint.frame("stats"))
        act.append(hpandas.df_to_str(actual, num_rows=None, precision=3))
        act = "\n".join(act)
        self.check_string(act, fuzzy_match=True)
