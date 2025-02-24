import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.turnover as cstaturn
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_turnover(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for default arguments.
        """
        series = self._get_series(seed=1)
        series[5:10] = np.nan
        actual = cstaturn.compute_turnover(series).rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test2(self) -> None:
        """
        Test for only positive input.
        """
        positive_series = self._get_series(seed=1).abs()
        actual = cstaturn.compute_turnover(positive_series).rename("output")
        output_df = pd.concat([positive_series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test3(self) -> None:
        """
        Test for nan_mode.
        """
        series = self._get_series(seed=1)
        series[5:10] = np.nan
        actual = cstaturn.compute_turnover(series, nan_mode="ffill").rename(
            "output"
        )
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    def test4(self) -> None:
        """
        Test for unit.
        """
        series = self._get_series(seed=1)
        series[5:10] = np.nan
        actual = cstaturn.compute_turnover(series, unit="B").rename("output")
        output_df = pd.concat([series, actual], axis=1)
        output_df_string = hpandas.df_to_str(output_df, num_rows=None)
        self.check_string(output_df_string)

    @staticmethod
    def _get_series(seed: int) -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "D"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        ).rename("input")
        return series


class Test_compute_average_holding_period(hunitest.TestCase):
    def test1(self) -> None:
        series = self._get_series_in_unit(seed=1)
        series[5:10] = np.nan
        actual = cstaturn.compute_average_holding_period(series)
        expected = 1.08458
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test2(self) -> None:
        positive_series = self._get_series_in_unit(seed=1).abs()
        actual = cstaturn.compute_average_holding_period(positive_series)
        expected = 1.23620
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    def test3(self) -> None:
        series = self._get_series_in_unit(seed=1)
        actual = cstaturn.compute_average_holding_period(series, unit="M")
        expected = 0.05001
        np.testing.assert_almost_equal(actual, expected, decimal=3)

    @staticmethod
    def _get_series_in_unit(seed: int, freq: str = "D") -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": freq}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series


class Test_compute_avg_turnover_and_holding_period(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for default parameters.
        """
        pos = self._get_pos(seed=1)
        actual = cstaturn.compute_avg_turnover_and_holding_period(pos)
        actual_string = hpandas.df_to_str(
            actual, num_rows=None, precision=3
        )
        self.check_string(actual_string)

    def test2(self) -> None:
        """
        Test for unit.
        """
        pos = self._get_pos(seed=1)
        actual = cstaturn.compute_avg_turnover_and_holding_period(pos, unit="M")
        actual_string = hpandas.df_to_str(
            actual, num_rows=None, precision=3
        )
        self.check_string(actual_string, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test for nan_mode.
        """
        pos = self._get_pos(seed=1)
        pos[5:10] = np.nan
        actual = cstaturn.compute_avg_turnover_and_holding_period(
            pos, nan_mode="fill_with_zero"
        )
        actual_string = hpandas.df_to_str(
            actual, num_rows=None, precision=3
        )
        self.check_string(actual_string, fuzzy_match=True)

    def test4(self) -> None:
        """
        Test for prefix.
        """
        pos = self._get_pos(seed=1)
        actual = cstaturn.compute_avg_turnover_and_holding_period(
            pos, prefix="test_"
        )
        actual_string = hpandas.df_to_str(
            actual, num_rows=None, precision=3
        )
        self.check_string(actual_string, fuzzy_match=True)

    @staticmethod
    def _get_pos(seed: int) -> pd.Series:
        arparams = np.array([0.75, -0.25])
        maparams = np.array([0.65, 0.35])
        arma_process = carsigen.ArmaProcess(arparams, maparams)
        date_range = {"start": "1/1/2010", "periods": 40, "freq": "D"}
        series = arma_process.generate_sample(
            date_range_kwargs=date_range, seed=seed
        )
        return series


class TestComputeTurn1(hunitest.TestCase):
    def test1(self) -> None:
        df = _get_turn_df()
        turn = cstaturn.compute_turn(df)
        np.testing.assert_almost_equal(turn, 1.33146, decimal=3)


class TestMaximizeWeightEntropy1(hunitest.TestCase):
    def test1(self) -> None:
        df = _get_turn_df()
        weights = cstaturn.maximize_weight_entropy(df, 1.33146)
        actual = hpandas.df_to_str(weights, num_rows=7, precision=3)
        expected = r"""
    weight
1   0.142
2   0.146
3   0.140
4   0.140
5   0.144
6   0.144
7   0.142"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class TestFindNearestAffinePoint1(hunitest.TestCase):
    def test1(self) -> None:
        df = _get_turn_df()
        weights = cstaturn.find_nearest_affine_point(df, 1.33146)
        actual = hpandas.df_to_str(weights, num_rows=7, precision=6)
        expected = r"""
     weight
1  0.142855
2  0.142857
3  0.142858
4  0.142858
5  0.142858
6  0.142857
7  0.142857"""
        self.assert_equal(actual, expected, fuzzy_match=True)


def _get_turn_df() -> pd.DataFrame:
    df = pd.DataFrame(
        [
            [0.035800, 1.7276, -1],
            [0.019700, 1.2265, -1],
            [0.011828, 0.8651, -1],
            [0.007924, 0.5893, -1],
            [0.005678, 0.4399, -1],
            [0.002616, 0.3795, -1],
            [0.000883, 0.3581, -1],
        ],
        [1, 2, 3, 4, 5, 6, 7],
        ["var", "turn", "weight"],
    )
    return df
