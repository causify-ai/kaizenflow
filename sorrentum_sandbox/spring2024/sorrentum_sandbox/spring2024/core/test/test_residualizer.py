import io
import logging
from typing import Any, Callable, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy

import core.explore as coexplor
import core.pandas_helpers as cpanhelp
import core.residualizer as coresidu
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestPcaFactorComputer1(hunitest.TestCase):
    @staticmethod
    def get_ex1() -> Tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
    ]:
        df_str = hprint.dedent(
            """
        ,0,1,2
        0,0.68637724274453,0.34344509725064354,0.6410395820984168
        1,-0.7208890365507423,0.205021903910637,0.6620309780499695
        2,-0.09594413803541411,0.916521404055221,-0.3883081743735094"""
        )
        df_str = io.StringIO(df_str)
        prev_eigvec_df = pd.read_csv(df_str, index_col=0)
        prev_eigvec_df.index = prev_eigvec_df.index.map(int)
        prev_eigvec_df.columns = prev_eigvec_df.columns.map(int)
        #
        prev_eigval_df = pd.DataFrame([[1.0, 0.5, 0.3]], columns=[0, 1, 2])
        # Shuffle eigenvalues / eigenvectors.
        eigvec_df = prev_eigvec_df.copy()
        shuffle = [1, 2, 0]
        eigvec_df = eigvec_df.reindex(columns=shuffle)
        eigvec_df.columns = list(range(eigvec_df.shape[1]))
        eigvec_df.iloc[:, 1] *= -1
        #
        eigval_df = prev_eigval_df.reindex(columns=shuffle)
        eigval_df.columns = list(range(eigval_df.shape[1]))
        for obj in (prev_eigval_df, eigval_df, prev_eigvec_df, eigvec_df):
            hpandas.dassert_strictly_increasing_index(obj)
        return prev_eigval_df, eigval_df, prev_eigvec_df, eigvec_df

    def test_stabilize_eigenvec1(self) -> None:
        data_func = self.get_ex1
        eval_func = coresidu.PcaFactorComputer._build_stable_eig_map
        self._test_stabilize_eigenvec_helper(data_func, eval_func)

    def test_stabilize_eigenvec2(self) -> None:
        data_func = self.get_ex1
        eval_func = coresidu.PcaFactorComputer._build_stable_eig_map2
        self._test_stabilize_eigenvec_helper(data_func, eval_func)

    # #########################################################################

    def test_linearize_eigval_eigvec(self) -> None:
        # Get data.
        eigval_df, _, eigvec_df, _ = self.get_ex1()
        # Evaluate.
        out = coresidu.PcaFactorComputer.linearize_eigval_eigvec(
            eigval_df, eigvec_df
        )
        _LOG.debug("out=\n%s", out)
        # Check.
        txt = (
            "eigval_df=\n%s\n" % eigval_df
            + "eigvec_df=\n%s\n" % eigvec_df
            + "out=\n%s" % out
        )
        self.check_string(txt)

    def test_sort_eigval1(self) -> None:
        eigval = np.array([1.30610138, 0.99251131, 0.70138731])
        eigvec = np.array(
            [
                [-0.55546523, 0.62034663, 0.55374041],
                [0.70270302, -0.00586218, 0.71145914],
                [-0.4445974, -0.78430587, 0.43266321],
            ]
        )
        are_eigval_sorted_exp = True
        self._test_sort_eigval_helper(eigval, eigvec, are_eigval_sorted_exp)

    def test_sort_eigval2(self) -> None:
        eigval = np.array([0.99251131, 0.70138731, 1.30610138])
        eigvec = np.array(
            [
                [-0.55546523, 0.62034663, 0.55374041],
                [0.70270302, -0.00586218, 0.71145914],
                [-0.4445974, -0.78430587, 0.43266321],
            ]
        )
        are_eigval_sorted_exp = False
        self._test_sort_eigval_helper(eigval, eigvec, are_eigval_sorted_exp)

    def _test_stabilize_eigenvec_helper(
        self, data_func: Callable, eval_func: Callable
    ) -> None:
        # Get data.
        prev_eigval_df, eigval_df, prev_eigvec_df, eigvec_df = data_func()
        # Check if they are stable.
        num_fails = coresidu.PcaFactorComputer.are_eigenvectors_stable(
            prev_eigvec_df, eigvec_df
        )
        self.assertEqual(num_fails, 3)
        # Transform.
        col_map, _ = eval_func(prev_eigvec_df, eigvec_df)
        #
        obj = coresidu.PcaFactorComputer.shuffle_eigval_eigvec(
            eigval_df, eigvec_df, col_map
        )
        shuffled_eigval_df, shuffled_eigvec_df = obj
        # Check.
        txt = (
            "prev_eigval_df=\n%s\n" % prev_eigval_df
            + "prev_eigvec_df=\n%s\n" % prev_eigvec_df
            + "eigval_df=\n%s\n" % eigval_df
            + "eigvec_df=\n%s\n" % eigvec_df
            + "shuffled_eigval_df=\n%s\n" % shuffled_eigval_df
            + "shuffled_eigvec_df=\n%s\n" % shuffled_eigvec_df
        )
        self.check_string(txt)
        # Check stability.
        num_fails = coresidu.PcaFactorComputer.are_eigenvectors_stable(
            prev_eigvec_df, shuffled_eigvec_df
        )
        self.assertEqual(num_fails, 0)
        self.assertTrue(
            coresidu.PcaFactorComputer.are_eigenvalues_stable(
                prev_eigval_df, shuffled_eigval_df
            )
        )

    # #########################################################################

    def _test_sort_eigval_helper(
        self, eigval: np.ndarray, eigvec: np.ndarray, are_eigval_sorted_exp: bool
    ) -> None:
        # pylint: disable=possibly-unused-variable
        obj = coresidu.PcaFactorComputer.sort_eigval(eigval, eigvec)
        are_eigval_sorted, eigval_tmp, eigvec_tmp = obj
        self.assertEqual(are_eigval_sorted, are_eigval_sorted_exp)
        self.assertSequenceEqual(
            eigval_tmp.tolist(), sorted(eigval_tmp, reverse=True)
        )
        vars_as_str = [
            "eigval",
            "eigvec",
            "are_eigval_sorted",
            "eigval_tmp",
            "eigvec_tmp",
        ]
        txt = hprint.vars_to_debug_string(vars_as_str, locals())
        self.check_string(txt)


# #############################################################################


class TestPcaFactorComputer2(hunitest.TestCase):
    def test1(self) -> None:
        num_samples = 100
        report_stats = False
        stabilize_eig = False
        window = 50
        comp, df_res = self._helper(
            num_samples, report_stats, stabilize_eig, window
        )
        self._check(comp, df_res)

    def test2(self) -> None:
        num_samples = 100
        report_stats = False
        stabilize_eig = True
        window = 50
        comp, df_res = self._helper(
            num_samples, report_stats, stabilize_eig, window
        )
        self._check(comp, df_res)

    @staticmethod
    def _get_data(num_samples: int, report_stats: bool) -> Dict[str, Any]:
        # The desired covariance matrix.
        # r = np.array([
        #         [  3.40, -2.75, -2.00],
        #         [ -2.75,  5.50,  1.50],
        #         [ -2.00,  1.50,  1.25]
        #     ])
        cov = np.array([[1.0, 0.5, 0], [0.5, 1, 0], [0, 0, 1]])
        if report_stats:
            _LOG.info("cov=\n%s", cov)
            coexplor.plot_heatmap(cov, mode="heatmap", title="cov")
            plt.show()
        # Generate samples from three independent normally distributed random
        # variables with mean 0 and std dev 1.
        x = scipy.stats.norm.rvs(size=(3, num_samples))
        if report_stats:
            _LOG.info("x=\n%s", x[:2, :])
        # We need a matrix `c` for which `c*c^T = r`.
        # We can use # the Cholesky decomposition, or the we can construct `c`
        # from the eigenvectors and eigenvalues.
        # Compute the eigenvalues and eigenvectors.
        evals, evecs = np.linalg.eigh(cov)
        if report_stats:
            _LOG.info("evals=\n%s", evals)
            _LOG.info("evecs=\n%s", evecs)
            coexplor.plot_heatmap(evecs, mode="heatmap", title="evecs")
            plt.show()
        # Construct c, so c*c^T = r.
        transform = np.dot(evecs, np.diag(np.sqrt(evals)))
        if report_stats:
            _LOG.info("transform=\n%s", transform)
        # print(c.T * c)
        # print(c * c.T)
        # Convert the data to correlated random variables.
        y = np.dot(transform, x)
        y_cov = np.corrcoef(y)
        if report_stats:
            _LOG.info("cov(y)=\n%s", y_cov)
            coexplor.plot_heatmap(y_cov, mode="heatmap", title="y_cov")
            plt.show()
        #
        y = pd.DataFrame(y).T
        _LOG.debug("y=\n%s", y.head(5))
        result = {
            "y": y,
            "cov": cov,
            "evals": evals,
            "evecs": evecs,
            "transform": transform,
        }
        return result

    def _helper(
        self,
        num_samples: int,
        report_stats: bool,
        stabilize_eig: bool,
        window: int,
    ) -> Tuple[coresidu.PcaFactorComputer, pd.DataFrame]:
        result = self._get_data(num_samples, report_stats)
        _LOG.debug("result=%s", result.keys())
        #
        nan_mode_in_data = "drop"
        nan_mode_in_corr = "fill_with_zero"
        sort_eigvals = True
        comp = coresidu.PcaFactorComputer(
            nan_mode_in_data, nan_mode_in_corr, sort_eigvals, stabilize_eig
        )
        df_res = cpanhelp.df_rolling_apply(
            result["y"], window, comp, progress_bar=True
        )
        if report_stats:
            comp.plot_over_time(df_res, num_pcs_to_plot=-1)
        return comp, df_res

    def _check(
        self, comp: coresidu.PcaFactorComputer, df_res: pd.DataFrame
    ) -> None:
        txt = []
        txt.append("comp.get_eigval_names()=\n%s" % comp.get_eigval_names())
        txt.append("df_res.mean()=\n%s" % df_res.mean())
        txt.append("df_res.std()=\n%s" % df_res.std())
        txt = "\n".join(txt)
        self.check_string(txt)
