import logging
from typing import List

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.finance as cofinanc
import core.statistics.sharpe_ratio as cstshrat
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeSharpeRatio(hunitest.TestCase):
    def test1(self) -> None:
        ar_params: List[float] = []
        ma_params: List[float] = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        sr = cstshrat.compute_sharpe_ratio(realization)
        np.testing.assert_almost_equal(sr, 0.057670899)


class TestComputeSharpeRatioStandardError(hunitest.TestCase):
    def test1(self) -> None:
        ar_params: List[float] = []
        ma_params: List[float] = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        sr_se = cstshrat.compute_sharpe_ratio_standard_error(realization)
        np.testing.assert_almost_equal(sr_se, 0.160261242)


class TestComputeAnnualizedSharpeRatio(hunitest.TestCase):
    def test1(self) -> None:
        """
        Demonstrate the approximate invariance of the annualized SR (at least
        for iid returns) under resampling.
        """
        srs = self._generate_minutely_series(n_days=100, seed=10)
        # Calculate SR from minutely time series.
        srs_sr = cstshrat.compute_annualized_sharpe_ratio(srs)
        np.testing.assert_almost_equal(srs_sr, -2.6182, decimal=3)
        # Resample to hourly and calculate SR.
        hourly_srs = srs.resample(rule="60T", label="right", closed="right").sum()
        hourly_sr = cstshrat.compute_annualized_sharpe_ratio(hourly_srs)
        np.testing.assert_almost_equal(hourly_sr, -2.6483, decimal=3)
        # Resample to daily and calculate SR.
        daily_srs = srs.resample(rule="D", label="right", closed="right").sum()
        daily_srs_sr = cstshrat.compute_annualized_sharpe_ratio(daily_srs)
        np.testing.assert_almost_equal(daily_srs_sr, -2.4890, decimal=3)
        # Resample to weekly and calculate SR.
        weekly_srs = srs.resample(rule="W", label="right", closed="right").sum()
        weekly_srs_sr = cstshrat.compute_annualized_sharpe_ratio(weekly_srs)
        np.testing.assert_almost_equal(weekly_srs_sr, -2.7717, decimal=3)

    def test2(self) -> None:
        """
        Demonstrate the approximate invariance of the annualized SR in moving
        from a "uniform" ATH-only time grid to a truly uniform time grid.
        """
        srs = self._generate_minutely_series(n_days=100, seed=10)
        # Filter out non-trading time points.
        filtered_srs = cofinanc.set_non_ath_to_nan(srs)
        filtered_srs = cofinanc.set_weekends_to_nan(filtered_srs)
        filtered_srs = filtered_srs.dropna()
        # Treat srs as an intraday trading day-only series, e.g.,
        # approximately 252 trading days per year, ATH only.
        n_samples = filtered_srs.size
        points_per_year = 2.52 * n_samples
        filtered_srs_sr = cstshrat.compute_sharpe_ratio(
            filtered_srs, time_scaling=points_per_year
        )
        np.testing.assert_almost_equal(filtered_srs_sr, -2.7203, decimal=3)
        # Compare to SR annualized using `freq`.
        srs_sr = cstshrat.compute_annualized_sharpe_ratio(srs)
        np.testing.assert_almost_equal(srs_sr, -2.6182, decimal=3)

    def test3(self) -> None:
        """
        Test for pd.DataFrame input with NaN values.
        """
        srs = self._generate_minutely_series(n_days=1, seed=1)[:40]
        srs[5:10] = np.nan
        df = pd.DataFrame([srs, srs.shift()]).T
        df.columns = ["Series 1", "Series 2"]
        actual = cstshrat.compute_annualized_sharpe_ratio(df)
        df_string = hpandas.df_to_str(df, num_rows=None)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        txt = f"Input:\n{df_string}\n\n" f"Output:\n{actual_string}\n"
        self.check_string(txt)

    def _generate_minutely_series(self, n_days: float, seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": n_days * 24 * 60, "freq": "T"},
            scale=1,
            seed=seed,
        )
        return realization


class TestComputeAnnualizedSharpeRatioStandardError(hunitest.TestCase):
    def test1(self) -> None:
        srs = self._generate_minutely_series(n_days=100, seed=10)
        # Calculate SR from minutely time series.
        srs_sr_se = cstshrat.compute_annualized_sharpe_ratio_standard_error(srs)
        np.testing.assert_almost_equal(srs_sr_se, 1.9108, decimal=3)
        # Resample to hourly and calculate SR.
        hourly_srs = srs.resample(rule="60T", label="right", closed="right").sum()
        hourly_sr_se = cstshrat.compute_annualized_sharpe_ratio_standard_error(
            hourly_srs
        )
        np.testing.assert_almost_equal(hourly_sr_se, 1.9116, decimal=3)
        # Resample to daily and calculate SR.
        daily_srs = srs.resample(rule="D", label="right", closed="right").sum()
        daily_sr_se_sr = cstshrat.compute_annualized_sharpe_ratio_standard_error(
            daily_srs
        )
        np.testing.assert_almost_equal(daily_sr_se_sr, 1.9192, decimal=3)
        # Resample to weekly and calculate SR.
        weekly_srs = srs.resample(rule="W", label="right", closed="right").sum()
        weekly_sr_se_sr = cstshrat.compute_annualized_sharpe_ratio_standard_error(
            weekly_srs
        )
        np.testing.assert_almost_equal(weekly_sr_se_sr, 2.0016, decimal=3)

    def test2(self) -> None:
        srs = self._generate_minutely_series(n_days=100, seed=10)
        # Filter out non-trading time points.
        filtered_srs = cofinanc.set_non_ath_to_nan(srs)
        filtered_srs = cofinanc.set_weekends_to_nan(filtered_srs)
        filtered_srs = filtered_srs.dropna()
        # Treat srs as an intraday trading day-only series, e.g.,
        # approximately 252 trading days per year, ATH only.
        n_samples = filtered_srs.size
        points_per_year = 2.52 * n_samples
        filtered_srs_se = cstshrat.compute_sharpe_ratio_standard_error(
            filtered_srs, time_scaling=points_per_year
        )
        np.testing.assert_almost_equal(filtered_srs_se, 1.5875, decimal=3)
        # Compare to SR annualized using `freq`.
        srs_sr_se = cstshrat.compute_annualized_sharpe_ratio_standard_error(srs)
        np.testing.assert_almost_equal(srs_sr_se, 1.9108, decimal=3)

    def _generate_minutely_series(self, n_days: float, seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": n_days * 24 * 60, "freq": "T"},
            scale=1,
            seed=seed,
        )
        return realization


class Test_summarize_sharpe_ratio(hunitest.TestCase):
    def test1(self) -> None:
        ar_params: List[float] = []
        ma_params: List[float] = []
        arma_process = carsigen.ArmaProcess(ar_params, ma_params)
        realization = arma_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"},
            scale=1,
            burnin=5,
        )
        res = cstshrat.summarize_sharpe_ratio(realization)
        self.check_string(hpandas.df_to_str(res, num_rows=None))


class Test_zscore_oos_sharpe_ratio(hunitest.TestCase):
    def test1(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        oos_start = "2010-02-25"
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test2(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        oos_start = "2010-04-10"
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test3(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        oos_start = "2010-02-25"
        series.loc[oos_start:] = series.loc[oos_start:].apply(  # type: ignore
            lambda x: 0.1 * x if x > 0 else x
        )
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test4(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        oos_start = "2010-02-25"
        series.loc[oos_start:] = series.loc[oos_start:].apply(  # type: ignore
            lambda x: 0.1 * x if x < 0 else x
        )
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test_nans1(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        series.iloc[:10] = np.nan
        series.iloc[40:50] = np.nan
        oos_start = "2010-02-25"
        series.loc[oos_start:"2010-03-03"] = np.nan  # type: ignore
        series.loc["2010-04-01":"2010-04-30"] = np.nan  # type: ignore
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test_zeros1(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        series.iloc[:10] = 0
        series.iloc[40:50] = 0
        oos_start = "2010-02-25"
        series.loc[oos_start:"2010-03-03"] = np.nan  # type: ignore
        series.loc["2010-04-01":"2010-04-30"] = np.nan  # type: ignore
        sr_stats = cstshrat.zscore_oos_sharpe_ratio(series, oos_start)
        output_str = (
            f"OOS start: {oos_start}\n"
            f"{hprint.frame('input series')}\n"
            f"{hpandas.df_to_str(series, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(sr_stats, num_rows=None)}"
        )
        self.check_string(output_str)

    def test_oos_not_from_interval1(self) -> None:
        series = Test_zscore_oos_sharpe_ratio._get_series(42)
        with self.assertRaises(AssertionError):
            _ = cstshrat.zscore_oos_sharpe_ratio(series, "2012-01-01")

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "2010-01-01", "periods": 100, "freq": "B"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed, scale=0.1
        )
        return series


class TestSharpeRatioCorrelationConversion(hunitest.TestCase):
    def test1(self) -> None:
        actual = cstshrat.apply_sharpe_ratio_correlation_conversion(
            points_per_year=252 * 78, sharpe_ratio=3
        )
        np.testing.assert_allclose(actual, 0.0214, atol=0.0001)

    def test2(self) -> None:
        actual = cstshrat.apply_sharpe_ratio_correlation_conversion(
            points_per_year=252 * 78, correlation=0.0214
        )
        np.testing.assert_allclose(actual, 3, atol=0.01)


class Test_compute_hit_rate_implied_by_correlation(hunitest.TestCase):
    def zero_corr(self) -> None:
        actual = cstshrat.compute_hit_rate_implied_by_correlation(0)
        np.testing.assert_allclose(actual, 0.5)

    def one_percent_corr(self) -> None:
        actual = cstshrat.compute_hit_rate_implied_by_correlation(0.01)
        np.testing.assert_allclose(actual, 0.5049999)

    def heavy_tails(self) -> None:
        actual = cstshrat.compute_hit_rate_implied_by_correlation(0.01, 0.6)
        np.testing.assert_allclose(actual, 0.5066487)


class Test_compute_correlation_implied_by_hit_rate(hunitest.TestCase):
    def zero_hit_rate(self) -> None:
        actual = cstshrat.compute_correlation_implied_by_hit_rate(0)
        np.testing.assert_allclose(actual, 0)

    def small_edge_to_one_percent_corr(self) -> None:
        actual = cstshrat.compute_correlation_implied_by_hit_rate(0.5049999)
        np.testing.assert_allclose(actual, 0.0100001)

    def heavy_tails(self) -> None:
        actual = cstshrat.compute_correlation_implied_by_hit_rate(0.5049999, 0.6)
        np.testing.assert_allclose(actual, 0.0075120)

    def fifty_one_percent(self) -> None:
        actual = cstshrat.compute_correlation_implied_by_hit_rate(0.51)
        np.testing.assert_allclose(actual, 0.0200002)
