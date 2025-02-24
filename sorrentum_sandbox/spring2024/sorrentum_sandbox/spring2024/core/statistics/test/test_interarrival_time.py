import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.interarrival_time as cstintim
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestGetInterarrivalTime(hunitest.TestCase):

    # Smoke test for empty input.
    def test1(self) -> None:
        series = pd.Series(dtype="float64")
        cstintim.get_interarrival_time(series)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstintim.get_interarrival_time(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstintim.get_interarrival_time(series, nan_mode="fill_with_zero")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        n = 100
        start = pd.to_datetime("2015-01-01")
        end = pd.to_datetime("2018-01-01")
        start_u = start.value // 10**9
        end_u = end.value // 10**9
        np.random.seed(seed=seed)
        dates = pd.to_datetime(np.random.randint(start_u, end_u, n), unit="s")
        sorted_dates = dates.sort_values()
        data = list(np.random.randint(10, size=n))
        series = pd.Series(data=data, index=sorted_dates, name="test")
        series[45:50] = np.nan
        return series


class TestComputeInterarrivalTimeStats(hunitest.TestCase):

    # Smoke test for empty input.
    def test1(self) -> None:
        series = pd.Series(dtype="float64")
        cstintim.compute_interarrival_time_stats(series)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        actual = cstintim.compute_interarrival_time_stats(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        actual = cstintim.compute_interarrival_time_stats(
            series, nan_mode="ffill"
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
        series.drop(series.index[15:20], inplace=True)
        series[5:10] = np.nan
        return series
