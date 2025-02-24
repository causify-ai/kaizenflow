import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing as csigproc
import core.statistics.returns_and_volatility as csreanvo
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_annualized_return_and_volatility(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for default parameters.
        """
        series = self._get_series(seed=1)
        actual = csreanvo.compute_annualized_return_and_volatility(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test prefix.
        """
        series = self._get_series(seed=1)
        actual = csreanvo.compute_annualized_return_and_volatility(
            series, prefix="test_"
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input
    def test3(self) -> None:
        series = pd.Series(dtype="float64")
        csreanvo.compute_annualized_return_and_volatility(series)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([0], [0])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        )
        return series


class Test_compute_returns_per_bet(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for clean input series.
        """
        log_rets = self._get_series(42)
        positions = csigproc.compute_smooth_moving_average(log_rets, 4)
        actual = csreanvo.compute_returns_per_bet(positions, log_rets)
        rets_pos = pd.concat({"pos": positions, "rets": log_rets}, axis=1)
        output_str = (
            f"{hprint.frame('rets_pos')}\n"
            f"{hpandas.df_to_str(rets_pos, num_rows=None)}\n"
            f"{hprint.frame('rets_per_bet')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test2(self) -> None:
        """
        Test for input series with NaNs and zeros.
        """
        log_rets = self._get_series(42)
        log_rets.iloc[6:12] = np.nan
        positions = csigproc.compute_smooth_moving_average(log_rets, 4)
        positions.iloc[:4] = 0
        positions.iloc[10:15] = np.nan
        positions.iloc[-4:] = 0
        actual = csreanvo.compute_returns_per_bet(positions, log_rets)
        rets_pos = pd.concat({"pos": positions, "rets": log_rets}, axis=1)
        output_str = (
            f"{hprint.frame('rets_pos')}\n"
            f"{hpandas.df_to_str(rets_pos, num_rows=None)}\n"
            f"{hprint.frame('rets_per_bet')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test3(self) -> None:
        """
        Test for short input series.
        """
        idx = pd.to_datetime(
            [
                "2010-01-01",
                "2010-01-03",
                "2010-01-05",
                "2010-01-06",
                "2010-01-10",
                "2010-01-12",
            ]
        )
        log_rets = pd.Series([1.0, 2.0, 3.0, 5.0, 7.0, 11.0], index=idx)
        positions = pd.Series([1.0, 2.0, 0.0, 1.0, -3.0, -2.0], index=idx)
        actual = csreanvo.compute_returns_per_bet(positions, log_rets)
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-03"): 5.0,
                pd.Timestamp("2010-01-06"): 5.0,
                pd.Timestamp("2010-01-12"): -43.0,
            }
        )
        pd.testing.assert_series_equal(actual, expected)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "M"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series
