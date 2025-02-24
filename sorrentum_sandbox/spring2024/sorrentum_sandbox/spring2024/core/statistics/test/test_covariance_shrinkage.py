import logging
from typing import Tuple

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics.covariance_shrinkage as cstcoshr
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestAnalyticalNonlinearShrinkageEstimator1(hunitest.TestCase):
    def test_high_sample_count(self) -> None:
        dim = 8
        num_samples = 126 * dim
        # q = dim / num_samples = 0.0079...
        cov, scm = _get_cov_and_scm(num_samples, dim)
        # True covariance matrix eigenvalues.
        expected_cov_eigenvalues = np.array(
            [
                0.04334372,
                0.05971632,
                0.10105678,
                0.10493383,
                0.24817698,
                0.35094874,
                1.52008844,
                17.42559941,
            ]
        )
        # Sample covariance matrix eigenvalues.
        expected_scm_eigenvalues = np.array(
            [
                0.04335411,
                0.05921702,
                0.09104625,
                0.10063471,
                0.23806769,
                0.37452067,
                1.44341287,
                17.47003994,
            ]
        )
        # Shrink.
        shrunk_scm = cstcoshr.compute_analytical_nonlinear_shrinkage_estimator(
            scm, num_samples
        )
        # Shrunken sample covariance matrix eigenvalues.
        expected_shrunk_scm_eigenvalues = np.array(
            [
                0.04452743,
                0.06017127,
                0.09266562,
                0.10029585,
                0.24003444,
                0.3748768,
                1.44705564,
                17.49786509,
            ]
        )
        #
        self._assert_eigenvalues_close(
            cov,
            scm,
            shrunk_scm,
            expected_cov_eigenvalues,
            expected_scm_eigenvalues,
            expected_shrunk_scm_eigenvalues,
        )

    def test_moderate_sample_count(self) -> None:
        dim = 8
        num_samples = 4 * dim
        # q = dim / num_samples = 0.25
        cov, scm = _get_cov_and_scm(num_samples, dim)
        # True covariance matrix eigenvalues.
        expected_cov_eigenvalues = np.array(
            [
                0.04334372,
                0.05971632,
                0.10105678,
                0.10493383,
                0.24817698,
                0.35094874,
                1.52008844,
                17.42559941,
            ]
        )
        # Sample covariance matrix eigenvalues.
        expected_scm_eigenvalues = np.array(
            [
                0.02242449,
                0.04255202,
                0.05433005,
                0.07929792,
                0.27019815,
                0.31234004,
                1.25296819,
                22.39853676,
            ]
        )
        # Shrink.
        shrunk_scm = cstcoshr.compute_analytical_nonlinear_shrinkage_estimator(
            scm, num_samples
        )
        # Shrunken sample covariance matrix eigenvalues.
        expected_shrunk_scm_eigenvalues = np.array(
            [
                0.04994592,
                0.07139584,
                0.07397226,
                0.0851278,
                0.33856532,
                0.34947873,
                1.34271109,
                23.45002166,
            ]
        )
        #
        self._assert_eigenvalues_close(
            cov,
            scm,
            shrunk_scm,
            expected_cov_eigenvalues,
            expected_scm_eigenvalues,
            expected_shrunk_scm_eigenvalues,
        )

    @staticmethod
    def _assert_eigenvalues_close(
        cov: pd.DataFrame,
        scm: pd.DataFrame,
        shrunk_scm: pd.DataFrame,
        expected_cov_eigenvalues: np.ndarray,
        expected_scm_eigenvalues: np.ndarray,
        expected_shrunk_scm_eigenvalues: np.ndarray,
    ) -> None:
        rtol = 1e-5
        atol = 1e-5
        #
        actual_cov_eigenvalues = np.linalg.eigh(cov)[0]
        np.testing.assert_allclose(
            actual_cov_eigenvalues, expected_cov_eigenvalues, rtol=rtol, atol=atol
        )
        #
        actual_scm_eigenvalues = np.linalg.eigh(scm)[0]
        np.testing.assert_allclose(
            actual_scm_eigenvalues, expected_scm_eigenvalues, rtol=rtol, atol=atol
        )
        #
        actual_shrunk_scm_eigenvalues = np.linalg.eigh(shrunk_scm)[0]
        np.testing.assert_allclose(
            actual_shrunk_scm_eigenvalues,
            expected_shrunk_scm_eigenvalues,
            rtol=rtol,
            atol=atol,
        )


class TestAnalyticalNonlinearShrinkageEstimator2(hunitest.TestCase):
    def test_high_sample_count(self) -> None:
        dim = 100
        num_samples = 100 * dim
        # q = dim / num_samples = 0.01
        cov, scm = _get_cov_and_scm(num_samples, dim)
        shrunk_scm = cstcoshr.compute_analytical_nonlinear_shrinkage_estimator(
            scm, num_samples
        )
        #
        rtol = 1e-9
        atol = 1e-9
        #
        expected_scm_mv_loss = 0.0002358836954011647
        actual_scm_mv_loss = cstcoshr.compute_mv_loss(scm, cov)
        np.testing.assert_allclose(
            actual_scm_mv_loss, expected_scm_mv_loss, rtol=rtol, atol=atol
        )
        #
        expected_shrunk_scm_mv_loss = 3.110762489289508e-05
        actual_shrunk_scm_mv_loss = cstcoshr.compute_mv_loss(shrunk_scm, cov)
        np.testing.assert_allclose(
            actual_shrunk_scm_mv_loss,
            expected_shrunk_scm_mv_loss,
            rtol=rtol,
            atol=atol,
        )

    def test_moderate_sample_count(self) -> None:
        dim = 100
        num_samples = 2 * dim
        # q = dim / num_samples = 0.5
        cov, scm = _get_cov_and_scm(num_samples, dim)
        shrunk_scm = cstcoshr.compute_analytical_nonlinear_shrinkage_estimator(
            scm, num_samples
        )
        #
        rtol = 1e-9
        atol = 1e-9
        #
        expected_scm_mv_loss = 0.015238000110623557
        actual_scm_mv_loss = cstcoshr.compute_mv_loss(scm, cov)
        np.testing.assert_allclose(
            actual_scm_mv_loss, expected_scm_mv_loss, rtol=rtol, atol=atol
        )
        #
        expected_shrunk_scm_mv_loss = 0.0005422549973756081
        actual_shrunk_scm_mv_loss = cstcoshr.compute_mv_loss(shrunk_scm, cov)
        np.testing.assert_allclose(
            actual_shrunk_scm_mv_loss,
            expected_shrunk_scm_mv_loss,
            rtol=rtol,
            atol=atol,
        )


def _get_cov_and_scm(
    num_samples: int, dim: int, seed: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    mvn = carsigen.MultivariateNormalProcess()
    mvn.set_cov_from_inv_wishart_draw(dim=dim, seed=seed)
    num_samples = num_samples
    mvn_rets = mvn.generate_sample(
        {"start": "2000-01-01", "periods": num_samples, "freq": "B"}, seed=seed
    )
    scm = mvn_rets.cov()
    cov = pd.DataFrame(mvn.cov, index=scm.index, columns=scm.columns)
    return cov, scm
