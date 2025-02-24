import logging

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.signed_runs as cstsirun
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_bet_starts(hunitest.TestCase):
    def test1(self) -> None:
        positions = Test_compute_bet_starts._get_series(42)
        actual = cstsirun.compute_signed_run_starts(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test2(self) -> None:
        positions = Test_compute_bet_starts._get_series(42)
        positions.iloc[:4] = np.nan
        positions.iloc[10:15] = np.nan
        positions.iloc[-4:] = np.nan
        actual = cstsirun.compute_signed_run_starts(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test3(self) -> None:
        """
        Test zeros.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): 0,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): 0,
                pd.Timestamp("2010-01-04"): -1,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            },
            dtype=float,
        )
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test4(self) -> None:
        """
        Test `NaN`s.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            },
            dtype=float,
        )
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test5(self) -> None:
        """
        Test consecutive zeroes.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): 0,
                pd.Timestamp("2010-01-02"): 0,
                pd.Timestamp("2010-01-03"): 0,
                pd.Timestamp("2010-01-04"): -1,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): np.nan,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            },
            dtype=float,
        )
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

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


class Test_compute_run_ends(hunitest.TestCase):
    def test1(self) -> None:
        positions = Test_compute_run_ends._get_series(42)
        actual = cstsirun.compute_signed_run_ends(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('run_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test2(self) -> None:
        positions = Test_compute_run_ends._get_series(42)
        positions.iloc[:4] = np.nan
        positions.iloc[10:15] = np.nan
        positions.iloc[-4:] = np.nan
        actual = cstsirun.compute_signed_run_ends(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('run_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test3(self) -> None:
        """
        Test zeros.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): 0,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): 0,
                pd.Timestamp("2010-01-04"): -1,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            },
            dtype=float,
        )
        # TODO(*): This is testing the wrong function!
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test4(self) -> None:
        """
        Test `NaN`s.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): np.nan,
                pd.Timestamp("2010-01-02"): 1,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): -1,
            },
            dtype=float,
        )
        # TODO(*): This is testing the wrong function!
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test5(self) -> None:
        """
        Test consecutive zeroes.
        """
        positions = pd.Series(
            {
                pd.Timestamp("2010-01-01"): -1,
                pd.Timestamp("2010-01-02"): 0,
                pd.Timestamp("2010-01-03"): 0,
                pd.Timestamp("2010-01-04"): 0,
            }
        )
        expected = pd.Series(
            {
                pd.Timestamp("2010-01-01"): -1,
                pd.Timestamp("2010-01-02"): np.nan,
                pd.Timestamp("2010-01-03"): np.nan,
                pd.Timestamp("2010-01-04"): np.nan,
            },
            dtype=float,
        )
        # TODO(*): This is testing the wrong function!
        actual = cstsirun.compute_signed_run_starts(positions)
        pd.testing.assert_series_equal(actual, expected)

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


class Test_compute_signed_run_lengths(hunitest.TestCase):
    def test1(self) -> None:
        positions = Test_compute_signed_run_lengths._get_series(42)
        actual = cstsirun.compute_signed_run_lengths(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test2(self) -> None:
        positions = Test_compute_signed_run_lengths._get_series(42)
        positions.iloc[:4] = np.nan
        positions.iloc[10:15] = np.nan
        positions.iloc[-4:] = np.nan
        actual = cstsirun.compute_signed_run_lengths(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test3(self) -> None:
        positions = pd.Series(
            [1, 1, 1, 2, -1, -4, -0.5, 0, 0, -1, 0, 1],
            index=pd.date_range(start="2010-01-01", periods=12, freq="D"),
        )
        expected_bet_ends = pd.to_datetime(
            ["2010-01-04", "2010-01-07", "2010-01-10", "2010-01-12"]
        )
        expected = pd.Series([4, -3, -1, 1], index=expected_bet_ends, dtype=float)
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test4(self) -> None:
        """
        Test a single value.
        """
        positions = pd.Series(
            [1], index=[pd.Timestamp("2010-01-01")], dtype=float
        )
        expected = pd.Series([1], index=[pd.Timestamp("2010-01-01")], dtype=float)
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test5(self) -> None:
        """
        Test NaNs.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02"])
        positions = pd.Series([np.nan, np.nan], index=idx)
        expected = pd.Series(index=idx).dropna()
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test6(self) -> None:
        """
        Test NaNs.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02", "2010-01-03"])
        positions = pd.Series([1, np.nan, 0], index=idx)
        expected = pd.Series(
            [1], index=pd.to_datetime(["2010-01-01"]), dtype=float
        )
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test7(self) -> None:
        """
        Test NaNs.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02", "2010-01-03"])
        positions = pd.Series([1, np.nan, np.nan], index=idx)
        expected = pd.Series(
            [1], index=pd.to_datetime(["2010-01-01"]), dtype=float
        )
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test8(self) -> None:
        """
        Test zeroes.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02"])
        positions = pd.Series([0, 0], index=idx)
        expected = pd.Series(index=idx).dropna()
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test9(self) -> None:
        """
        Test zeroes.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02", "2010-01-03"])
        positions = pd.Series([0, 1, 0], index=idx)
        expected = pd.Series([1.0], index=[pd.Timestamp("2010-01-02")])
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test10(self) -> None:
        """
        Test zeroes.
        """
        idx = pd.to_datetime(["2010-01-01", "2010-01-02", "2010-01-03"])
        positions = pd.Series([1, 0, 0], index=idx)
        expected = pd.Series([1.0], index=[pd.Timestamp("2010-01-01")])
        actual = cstsirun.compute_signed_run_lengths(positions)
        pd.testing.assert_series_equal(actual, expected)

    def test11(self) -> None:
        positions = Test_compute_signed_run_lengths._get_series(42)
        positions.iloc[:4] = 0
        positions.iloc[10:15] = 0
        positions.iloc[-4:] = 0
        actual = cstsirun.compute_signed_run_lengths(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

    def test12(self) -> None:
        positions = Test_compute_signed_run_lengths._get_series(42)
        positions.iloc[:4] = 0
        positions.iloc[10:15] = 0
        positions.iloc[-4:] = 0
        actual = cstsirun.compute_signed_run_lengths(positions)
        output_str = (
            f"{hprint.frame('positions')}\n"
            f"{hpandas.df_to_str(positions, num_rows=None)}\n"
            f"{hprint.frame('bet_lengths')}\n"
            f"{hpandas.df_to_str(actual, num_rows=None)}"
        )
        self.check_string(output_str)

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
