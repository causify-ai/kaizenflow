import logging

import numpy as np
import pandas as pd

import helpers.hpandas as hpandas
import core.statistics.forecastability as cstafore
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_forecastability(hunitest.TestCase):
    def test1(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstafore.compute_forecastability(
            signal,
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test2(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstafore.compute_forecastability(
            signal,
            mode="periodogram",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test3(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstafore.compute_forecastability(
            signal,
            nan_mode="ffill_and_drop_leading",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    def test4(self) -> None:
        signal = self._get_signal(seed=1)
        actual = cstafore.compute_forecastability(
            signal,
            prefix="commodity_",
        )
        actual_string = hpandas.df_to_str(actual, num_rows=None)
        self.check_string(actual_string)

    # Smoke test for empty input.
    def test5(self) -> None:
        signal = self._get_signal(seed=1)
        cstafore.compute_forecastability(signal)

    @staticmethod
    def _get_signal(seed: int) -> pd.Series:
        np.random.seed(seed)
        n = 1000
        signal = pd.Series(np.random.randn(n))
        signal[30:50] = np.nan
        return signal
