import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.t_test as cstttes
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestTTest1samp(hunitest.TestCase):

    # Smoke test for empty input.
    def test1(self) -> None:
        series = pd.Series(dtype="float64")
        cstttes.ttest_1samp(series)

    def test2(self) -> None:
        series = self._get_series(seed=1)
        # Place some `NaN` values in the series.
        series[:5] = np.nan
        series[8:10] = np.nan
        actual = cstttes.ttest_1samp(series)
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        series = self._get_series(seed=1)
        # Place some `NaN` values in the series.
        series[:5] = np.nan
        series[8:10] = np.nan
        actual = cstttes.ttest_1samp(series, nan_mode="ffill_and_drop_leading")
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for input of `np.nan`s.
    def test4(self) -> None:
        series = pd.Series([np.nan for i in range(10)])
        cstttes.ttest_1samp(series)

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
