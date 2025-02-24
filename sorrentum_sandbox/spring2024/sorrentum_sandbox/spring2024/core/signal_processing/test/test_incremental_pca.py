import logging

import numpy as np
import pandas as pd
import pytest

import core.artificial_signal_generators as carsigen
import core.signal_processing.incremental_pca as csprinpc
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


@pytest.mark.skip("See CmTask5898.")
class Test_compute_ipca(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for a clean input.
        """
        df = self._get_df(seed=1)
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test2(self) -> None:
        """
        Test for an input with leading NaNs in only a subset of cols.
        """
        df = self._get_df(seed=1)
        df.iloc[0:3, :-3] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test3(self) -> None:
        """
        Test for an input with interspersed NaNs.
        """
        df = self._get_df(seed=1)
        df.iloc[5:8, 3:5] = np.nan
        df.iloc[2:4, 8:] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test4(self) -> None:
        """
        Test for an input with a full-NaN row among the 3 first rows.

        The eigenvalue estimates aren't in sorted order but should be.
        TODO(*): Fix problem with not sorted eigenvalue estimates.
        """
        df = self._get_df(seed=1)
        df.iloc[1:2, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test5(self) -> None:
        """
        Test for an input with 5 leading NaNs in all cols.
        """
        df = self._get_df(seed=1)
        df.iloc[:5, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    def test6(self) -> None:
        """
        Test for interspersed all-NaNs rows.
        """
        df = self._get_df(seed=1)
        df.iloc[0:1, :] = np.nan
        df.iloc[2:3, :] = np.nan
        num_pc = 3
        tau = 16
        lambda_df, unit_eigenvec_dfs = csprinpc.compute_ipca(df, num_pc, tau)
        unit_eigenvec_dfs_txt = "\n".join(
            [f"{i}:\n{df.to_string()}" for i, df in enumerate(unit_eigenvec_dfs)]
        )
        txt = (
            f"lambda_df:\n{lambda_df.to_string()}\n, "
            f"unit_eigenvecs_dfs:\n{unit_eigenvec_dfs_txt}"
        )
        self.check_string(txt)

    @staticmethod
    def _get_df(seed: int) -> pd.DataFrame:
        """
        Generate a dataframe via `carsigen.MultivariateNormalProcess()`.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=seed)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 40, "freq": "B"}, seed=seed
        )
        return df


@pytest.mark.skip("See CmTask5898.")
class Test__compute_ipca_step(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for clean input series.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        alpha = 0.5
        u_next, v_next = csprinpc._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test2(self) -> None:
        """
        Test for input series with all zeros.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[:] = 0
        v[:] = 0
        alpha = 0.5
        u_next, v_next = csprinpc._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test3(self) -> None:
        """
        Test that u == u_next for the case when np.linalg.norm(v)=0.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        v[:] = 0
        alpha = 0.5
        u_next, v_next = csprinpc._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test4(self) -> None:
        """
        Test for input series with all NaNs.

        Output is not intended.
        TODO(Dan): implement a way to deal with NaNs in the input.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[:] = np.nan
        v[:] = np.nan
        alpha = 0.5
        u_next, v_next = csprinpc._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    def test5(self) -> None:
        """
        Test for input series with some NaNs.

        Output is not intended.
        """
        mn_process = carsigen.MultivariateNormalProcess()
        mn_process.set_cov_from_inv_wishart_draw(dim=10, seed=1)
        df = mn_process.generate_sample(
            {"start": "2000-01-01", "periods": 10, "freq": "B"}, seed=1
        )
        u = df.iloc[1]
        v = df.iloc[2]
        u[3:6] = np.nan
        v[5:8] = np.nan
        alpha = 0.5
        u_next, v_next = csprinpc._compute_ipca_step(u, v, alpha)
        txt = self._get_output_txt(u, v, u_next, v_next)
        self.check_string(txt)

    @staticmethod
    def _get_output_txt(
        u: pd.Series, v: pd.Series, u_next: pd.Series, v_next: pd.Series
    ) -> str:
        """
        Create string output for tests results.
        """
        u_string = hpandas.df_to_str(u, num_rows=None)
        v_string = hpandas.df_to_str(v, num_rows=None)
        u_next_string = hpandas.df_to_str(u_next, num_rows=None)
        v_next_string = hpandas.df_to_str(v_next, num_rows=None)
        txt = (
            f"u:\n{u_string}\n"
            f"v:\n{v_string}\n"
            f"u_next:\n{u_next_string}\n"
            f"v_next:\n{v_next_string}"
        )
        return txt
