import io
import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.drawdown as cstadraw
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeDrawdownCdf(hunitest.TestCase):
    def test1(self) -> None:
        sharpe_ratio = 1
        volatility = 0.15
        drawdown = 0.05
        time = 1
        probability = cstadraw.compute_drawdown_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            drawdown=drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probability, 0.52500, decimal=3)

    def test2(self) -> None:
        sharpe_ratio = 3
        volatility = 0.15
        drawdown = 0.05
        time = 1
        probalility = cstadraw.compute_drawdown_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            drawdown=drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.86475, decimal=3)

    def test3(self) -> None:
        sharpe_ratio = 3
        volatility = 0.15
        drawdown = 0.05
        time = 10
        probalility = cstadraw.compute_drawdown_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            drawdown=drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.86466, decimal=3)


class TestComputeNormalizedDrawdownCdf(hunitest.TestCase):
    def test1(self) -> None:
        sharpe_ratio = 1
        normalized_drawdown = 0.5
        time = 1
        probalility = cstadraw.compute_normalized_drawdown_cdf(
            sharpe_ratio=sharpe_ratio,
            normalized_drawdown=normalized_drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.67881, decimal=3)

    def test2(self) -> None:
        sharpe_ratio = 3
        normalized_drawdown = 1
        time = 1
        probalility = cstadraw.compute_normalized_drawdown_cdf(
            sharpe_ratio=sharpe_ratio,
            normalized_drawdown=normalized_drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.99754, decimal=3)


class TestComputeMaxDrawdownApproximateCdf(hunitest.TestCase):
    def test1(self) -> None:
        sharpe_ratio = 1
        volatility = 0.15
        max_drawdown = 0.05
        time = 1
        probalility = cstadraw.compute_max_drawdown_approximate_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            max_drawdown=max_drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.59844, decimal=3)

    def test2(self) -> None:
        sharpe_ratio = 3
        volatility = 0.15
        max_drawdown = 0.05
        time = 1
        probalility = cstadraw.compute_max_drawdown_approximate_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            max_drawdown=max_drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.87342, decimal=3)

    def test3(self) -> None:
        sharpe_ratio = 3
        volatility = 0.15
        max_drawdown = 0.05
        time = 10
        probalility = cstadraw.compute_max_drawdown_approximate_cdf(
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            max_drawdown=max_drawdown,
            time=time,
        )
        np.testing.assert_almost_equal(probalility, 0.25837, decimal=3)


class TestComputeMaxDrawdown(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadraw.compute_max_drawdown(series)
        expected_txt = """
,\"arma(1,1)\"
max_drawdown,0.784453
"""
        expected = pd.read_csv(io.StringIO(expected_txt), index_col=0)
        self.assert_dfs_close(actual.to_frame(), expected, rtol=1e-5, atol=1e-5)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstadraw.compute_max_drawdown(series, prefix="new_")
        expected_txt = """
,\"arma(1,1)\"
new_max_drawdown,0.784453
"""
        expected = pd.read_csv(io.StringIO(expected_txt), index_col=0)
        self.assert_dfs_close(actual.to_frame(), expected, rtol=1e-5, atol=1e-5)

    def test3(self) -> None:
        """
        Smoke test for empty input.
        """
        series = pd.Series(dtype="float64")
        cstadraw.compute_max_drawdown(series)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([0], [0])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        )
        return series


class Test_compute_drawdown(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series(1)
        actual = cstadraw.compute_drawdown(series)
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


class Test_compute_time_under_water(hunitest.TestCase):
    def test1(self) -> None:
        series = Test_compute_time_under_water._get_series(42)
        drawdown = cstadraw.compute_drawdown(series).rename("drawdown")
        time_under_water = cstadraw.compute_time_under_water(series).rename(
            "time_under_water"
        )
        output = pd.concat([series, drawdown, time_under_water], axis=1)
        self.check_string(hpandas.df_to_str(output, num_rows=None))

    def test2(self) -> None:
        series = Test_compute_time_under_water._get_series(42)
        series.iloc[:4] = np.nan
        series.iloc[10:15] = np.nan
        series.iloc[-4:] = np.nan
        drawdown = cstadraw.compute_drawdown(series).rename("drawdown")
        time_under_water = cstadraw.compute_time_under_water(series).rename(
            "time_under_water"
        )
        output = pd.concat([series, drawdown, time_under_water], axis=1)
        self.check_string(hpandas.df_to_str(output, num_rows=None))

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series
