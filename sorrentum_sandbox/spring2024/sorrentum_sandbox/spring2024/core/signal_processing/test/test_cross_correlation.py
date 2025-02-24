import logging

import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing.cross_correlation as csprcrco
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test__compute_lagged_cumsum(hunitest.TestCase):
    def test1(self) -> None:
        input_df = self._get_df()
        output_df = csprcrco._compute_lagged_cumsum(input_df, 3)
        self.check_string(
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(input_df, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(output_df, num_rows=None)}"
        )

    def test2(self) -> None:
        input_df = self._get_df()
        input_df.columns = ["x", "y1", "y2"]
        output_df = csprcrco._compute_lagged_cumsum(input_df, 3, ["y1", "y2"])
        self.check_string(
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(input_df, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(output_df, num_rows=None)}"
        )

    def test_lag_1(self) -> None:
        input_df = self._get_df()
        input_df.columns = ["x", "y1", "y2"]
        output_df = csprcrco._compute_lagged_cumsum(input_df, 1, ["y1", "y2"])
        self.check_string(
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(input_df, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(output_df, num_rows=None)}"
        )

    @staticmethod
    def _get_df() -> pd.DataFrame:
        df = pd.DataFrame([list(range(10))] * 3).T
        df[1] = df[0] + 1
        df[2] = df[0] + 2
        df.index = pd.date_range(start="2010-01-01", periods=10)
        df.rename(columns=lambda x: f"col_{x}", inplace=True)
        return df


class Test_correlate_with_lagged_cumsum(hunitest.TestCase):
    def test1(self) -> None:
        input_df = self._get_arma_df()
        output_df = csprcrco.correlate_with_lagged_cumsum(
            input_df, 3, y_vars=["y1", "y2"]
        )
        self.check_string(
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(input_df, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(output_df, num_rows=None)}"
        )

    def test2(self) -> None:
        input_df = self._get_arma_df()
        output_df = csprcrco.correlate_with_lagged_cumsum(
            input_df, 3, y_vars=["y1"], x_vars=["x"]
        )
        self.check_string(
            f"{hprint.frame('input')}\n"
            f"{hpandas.df_to_str(input_df, num_rows=None)}\n"
            f"{hprint.frame('output')}\n"
            f"{hpandas.df_to_str(output_df, num_rows=None)}"
        )

    @staticmethod
    def _get_arma_df(seed: int = 0) -> pd.DataFrame:
        arma_process = carsigen.ArmaProcess([], [])
        date_range = {"start": "2010-01-01", "periods": 40, "freq": "M"}
        srs1 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed
        ).rename("x")
        srs2 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed + 1
        ).rename("y1")
        srs3 = arma_process.generate_sample(
            date_range_kwargs=date_range, scale=0.1, seed=seed + 2
        ).rename("y2")
        return pd.concat([srs1, srs2, srs3], axis=1)


# TODO(Paul): Rename test. Do not use file for golden.
class Test_calculate_inverse(hunitest.TestCase):
    def test1(self) -> None:
        df = pd.DataFrame([[1, 2], [3, 4]])
        inverse_df = hpandas.df_to_str(
            csprcrco.compute_inverse(df)
        )
        self.check_string(inverse_df)


# TODO(Paul): Rename test. Do not use file for golden.
class Test_calculate_presudoinverse(hunitest.TestCase):
    def test1(self) -> None:
        df = pd.DataFrame([[1, 2], [3, 4], [5, 6]])
        inverse_df = hpandas.df_to_str(
            csprcrco.compute_pseudoinverse(df)
        )
        self.check_string(inverse_df)
