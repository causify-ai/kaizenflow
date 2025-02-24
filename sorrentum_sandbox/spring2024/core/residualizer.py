"""
Implement a residualizer pipeline that, given data (e.g., returns or features),
computes:
1) factors
2) loadings
3) residuals

Each of the 3 components:
- has an interface and multiple implementations
- supports both stateful and stateless operations
- supports a functional style, composable with pandas and following some pandas
  conventions
- can be used in sklearn Pipeline objects

Import as:

import core.residualizer as coresidu
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.spatial.distance import cosine  # type: ignore

import core.explore as coexplor
import core.plotting as coplotti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): This is probably general and should be moved somewhere else.
# TODO(gp): -> stack_df or better name.
def linearize_df(df: pd.DataFrame, prefix: str) -> pd.Series:
    """
    Transform a pd.DataFrame like:

    0         1         2
        0  0.691443 -0.088121  0.717036
        1  0.656170 -0.338633 -0.674366
        2  0.302238  0.936783 -0.176323
    into a pd.Series like:
        f0_0    0.691443
        f0_1    0.656170
        f0_2    0.302238
        f1_0   -0.088121
        f1_1   -0.338633
        f1_2    0.936783
        f2_0    0.717036
        f2_1   -0.674366
        f2_2   -0.176323
    """
    df = df.copy()
    df.columns = ["%s%s" % (prefix, i) for i in range(df.shape[1])]
    df.index = df.index.map(str)
    #
    srs = df.unstack()
    hdbg.dassert_isinstance(srs, pd.Series)
    srs.index = srs.index.map("_".join)
    return srs


# #############################################################################


# TODO(gp): Make sure it's sklearn complaint
# TODO(gp): Use abstract classes (see https://docs.python.org/3/library/abc.html).
class FactorComputer:
    def __init__(self) -> None:
        pass

    def __call__(self, obj: pd.DataFrame, *args: Any, **kwargs: Any) -> pd.Series:
        if isinstance(obj, pd.Series):
            df = pd.DataFrame(obj)
        else:
            df = obj
        hdbg.dassert_isinstance(df, pd.DataFrame)
        return self._execute(obj, *args, **kwargs)

    def fit(self) -> None:
        # TODO(gp): Implement sklearn complaint method.
        raise NotImplementedError

    def transform(self) -> None:
        # TODO(gp): Implement sklearn complaint method.
        raise NotImplementedError

    def get_factors(self) -> None:
        raise NotImplementedError

    def _execute(self, df: pd.DataFrame, ts: int) -> pd.Series:
        raise NotImplementedError


# #############################################################################


# TODO(gp): eigval_df -> eigval since it's a Series?
# eigvec_df -> eigvec
class PcaFactorComputer(FactorComputer):
    """
    Compute factors using a rolling PCA decomposition.
    """

    def __init__(
        self,
        nan_mode_in_data: str,
        nan_mode_in_corr: str,
        do_sort_eigvals: bool,
        do_stabilize_eig: bool,
    ) -> None:
        """

        :param nan_mode_in_data: how to handle NAs in data passed for processing
            (see `handle_nans()`)
        :param nan_mode_in_corr: how to handle NAs in correlation matrix
        :param do_sort_eigvals: force sorting of the eigenvalues
        :param do_stabilize_eig: stabilize eigenvalues / eigenvectors by
            reordering them and changing sign
        """
        super().__init__()
        self.nan_mode_in_data = nan_mode_in_data
        self.nan_mode_in_corr = nan_mode_in_corr
        self.do_sort_eigvals = do_sort_eigvals
        self.do_stabilize_eig = do_stabilize_eig
        # Map from timestamps to eigval / eigvec.
        self._ts: List[int] = []
        self._eigval_df: collections.OrderedDict = collections.OrderedDict()
        self._eigvec_df: collections.OrderedDict = collections.OrderedDict()
        #
        self._eig_num = None
        self._eig_comp_num = None

    # TODO(gp): -> private
    @staticmethod
    def linearize_eigval_eigvec(
        eigval_df: pd.DataFrame, eigvec_df: pd.DataFrame
    ) -> pd.Series:
        res = linearize_df(eigvec_df, "eigvec")
        #
        hdbg.dassert_isinstance(eigval_df, pd.DataFrame)
        eigval_df = eigval_df.T.copy()
        eigval_df.index = ["eigval%s" % i for i in range(eigval_df.shape[0])]
        hdbg.dassert_eq(eigval_df.shape[1], 1)
        res = pd.concat([res, eigval_df.iloc[:, 0]])
        return res

    @staticmethod
    def sort_eigval(
        eigval: np.array, eigvec: np.array
    ) -> Tuple[np.bool_, np.array, np.array]:
        are_eigval_sorted = (np.diff(eigval) <= 0).all()
        if not are_eigval_sorted:
            _LOG.debug(
                "eigvals not sorted:\neigval=\n%s\neigvec=\n%s", eigval, eigvec
            )
            # Sort eigvals in descending order.
            idx = eigval.argsort()[::-1]
            eigval = eigval[idx]
            eigvec = eigvec[:, idx]
            # Make sure it's sorted in descending order.
            hdbg.dassert_eq_all(eigval, np.sort(eigval)[::-1])
        return are_eigval_sorted, eigval, eigvec

    # TODO(gp): -> eig_distance
    @staticmethod
    def eigvec_distance(v1: pd.Series, v2: pd.Series) -> np.float64:
        # TODO(gp): Maybe the max of the diff of the component is a better
        # metric.
        diff = np.linalg.norm(v1 - v2)
        # _LOG.debug("v1=%s\nv2=%s\ndiff=%s", v1, v2, diff)
        return diff

    @staticmethod
    def check_stabilized_eigvec(
        col_map: Union[
            Dict[int, Tuple[int, int]], Dict[int, Tuple[int, np.int64]]
        ],
        n: int,
    ) -> bool:
        # Check that col_map contains a permutation of the index.
        col_map_src = col_map.keys()
        col_map_dst = [x[1] for x in col_map.values()]
        exp_idxs = list(range(n))
        hdbg.dassert_eq_all(sorted(col_map_src), exp_idxs)
        hdbg.dassert_eq_all(sorted(col_map_dst), exp_idxs)
        return True

    @staticmethod
    def shuffle_eigval_eigvec(
        eigval_df: pd.DataFrame,
        eigvec_df: pd.DataFrame,
        col_map: Union[
            Dict[int, Tuple[int, int]], Dict[int, Tuple[int, np.int64]]
        ],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Transform the eigenvalues / eigenvectors according to a col_map
        returned by `_build_stable_eig_map()`.

        :return: updated eigvalues and eigenvectors
        """
        hdbg.dassert_isinstance(eigval_df, pd.DataFrame)
        hdbg.dassert_isinstance(eigvec_df, pd.DataFrame)
        _LOG.debug("col_map=%s", col_map)
        # Apply the permutation to the eigenvalues / eigenvectors.
        permutation = [col_map[i][1] for i in sorted(col_map.keys())]
        _LOG.debug("permutation=%s", permutation)
        shuffled_eigvec_df = eigvec_df.reindex(columns=permutation)
        shuffled_eigvec_df.columns = range(shuffled_eigvec_df.shape[1])
        shuffled_eigval_df = eigval_df.reindex(columns=permutation)
        shuffled_eigval_df.columns = range(shuffled_eigval_df.shape[1])
        # Change the sign of the eigenvectors. We don't need to change the
        # sign of the eigenvalues.
        coeffs = pd.Series([col_map[i][0] for i in sorted(col_map.keys())])
        _LOG.debug("coeffs=%s", coeffs)
        shuffled_eigvec_df *= coeffs
        return shuffled_eigval_df, shuffled_eigvec_df

    @staticmethod
    def are_eigenvectors_stable(
        prev_eigvec_df: pd.DataFrame, eigvec_df: pd.DataFrame, thr: float = 0.1
    ) -> int:
        """
        Return whether eigvec_df are "stable" in the sense that the change of
        corresponding of each eigenvec is smaller than a certain threshold.
        """
        hdbg.dassert_eq(
            prev_eigvec_df.shape,
            eigvec_df.shape,
            "prev_eigvec_df=\n%s\neigvec_df=\n%s",
            prev_eigvec_df,
            eigvec_df,
        )
        num_fails = 0
        for i in range(eigvec_df.shape[1]):
            v1 = prev_eigvec_df.iloc[:, i]
            v2 = eigvec_df.iloc[:, i]
            _LOG.debug("v1=%s\nv2=%s", v1, v2)
            diff = PcaFactorComputer.eigvec_distance(v1, v2)
            if diff > thr:
                _LOG.debug(
                    "diff=%s > thr=%s -> num_fails=%d", diff, thr, num_fails
                )
                num_fails += 1
        return num_fails

    @staticmethod
    def are_eigenvalues_stable(
        prev_eigval_df: pd.DataFrame, eigval_df: pd.DataFrame, thr: float = 1e-3
    ) -> bool:
        _LOG.debug(
            "prev_eigval_df=\n%s\neigval_df=\n%s\n", prev_eigval_df, eigval_df
        )
        hdbg.dassert_eq(prev_eigval_df.shape, eigval_df.shape)
        are_stable = True
        diff = PcaFactorComputer.eigvec_distance(prev_eigval_df, eigval_df)
        _LOG.debug("diff=%s", diff)
        if diff > thr:
            _LOG.debug("diff=%s > thr=%s", diff, thr)
            are_stable = False
        return are_stable

    @property
    def eig_num(self) -> Optional[int]:
        """
        Return number of eigenvalue / vectors.
        """
        return self._eig_num

    @property
    def eig_comp_num(self) -> Optional[int]:
        """
        Return number of components for each eigenvector.
        """
        return self._eig_comp_num

    def get_eigval_names(self) -> List[str]:
        """
        Return the names of the eigenvalues column in the result df.
        """
        return ["eigval%s" % i for i in range(self.eig_num)]

    def get_eigvec_names(self, i: int) -> List[str]:
        """
        Return the names of the i-th eigenvector in the result df.
        """
        hdbg.dassert_lte(0, i)
        hdbg.dassert_lt(i, self.eig_num)
        return ["eigvec%s_%s" % (i, j) for j in range(self.eig_comp_num)]

    def plot_over_time(
        self, res_df: pd.DataFrame, num_pcs_to_plot: int = 0, num_cols: int = 2
    ) -> None:
        """
        Similar to plot_pca_analysis() but over time.
        """
        # Plot eigenvalues.
        cols = [c for c in res_df.columns if c.startswith("eigval")]
        eigval_df = res_df[cols]
        hdbg.dassert_lte(1, eigval_df.shape[1])
        eigval_df.plot(title="Eigenvalues over time", ylim=(0, 1))
        # Plot cumulative variance.
        eigval_df.cumsum(axis=1).plot(
            title="Fraction of variance explained by top PCs over time",
            ylim=(0, 1),
        )
        # Plot eigenvectors.
        cols = [c for c in res_df.columns if c.startswith("eigvec")]
        eigvec_df = res_df[cols]
        hdbg.dassert_lte(1, eigvec_df.shape[1])
        # TODO(gp): Fix this.
        # max_pcs = len([c for c in res_df.columns if c.startswith("eigvec_")])
        max_pcs = 3
        num_pcs_to_plot = self._get_num_pcs_to_plot(num_pcs_to_plot, max_pcs)
        _LOG.info("num_pcs_to_plot=%s", num_pcs_to_plot)
        if num_pcs_to_plot > 0:
            _, axes = coplotti.get_multiple_plots(
                num_pcs_to_plot,
                num_cols=num_cols,
                y_scale=4,
                sharex=True,
                sharey=True,
            )
            for i in range(num_pcs_to_plot):
                col_names = [
                    c for c in eigvec_df.columns if c.startswith("eigvec%s" % i)
                ]
                hdbg.dassert_lte(1, len(col_names))
                eigvec_df[col_names].plot(
                    ax=axes[i], ylim=(-1, 1), title="PC%s" % i
                )

    @staticmethod
    def _get_num_pcs_to_plot(num_pcs_to_plot: int, max_pcs: int) -> int:
        """
        Get the number of principal components to coplotti.
        """
        if num_pcs_to_plot == -1:
            num_pcs_to_plot = max_pcs
        hdbg.dassert_lte(0, num_pcs_to_plot)
        hdbg.dassert_lte(num_pcs_to_plot, max_pcs)
        return num_pcs_to_plot

    @staticmethod
    def _build_stable_eig_map(
        prev_eigvec_df: pd.DataFrame, eigvec_df: pd.DataFrame
    ) -> Tuple[Dict[int, Tuple[int, np.int64]], np.array]:
        """
        Try to find a permutation and sign changes of the columns in
        `prev_eigvec_df` to ensure continuity with `eigvec_df`.

        :return: map column index of original eigvec to (sign, column index
            of transformed eigvec)
        """

        def dist(v1: pd.Series, v2: pd.Series) -> np.float64:
            # return res.PcaFactorComputer.eigvec_distance(v1, v2)
            return 1 - cosine(v1, v2)

        # Build a matrix with the distances between corresponding vectors.
        num_cols = prev_eigvec_df.shape[1]
        distances = np.zeros((num_cols, num_cols)) * np.nan
        for i in range(num_cols):
            for j in range(num_cols):
                distances[i, j] = dist(
                    prev_eigvec_df.iloc[:, i], eigvec_df.iloc[:, j]
                )
        _LOG.debug("distances=\n%s", distances)
        # Find the row with the max abs value for each column.
        max_abs_cos = np.argmax(np.abs(distances), axis=1)
        _LOG.debug("max_abs_cos=%s", max_abs_cos)
        signs = np.sign(distances[range(0, num_cols), max_abs_cos])
        signs = list(map(int, signs))
        _LOG.debug("signs=%s", signs)
        # Package the results into col_map.
        col_map = {k: (signs[k], max_abs_cos[k]) for k in range(0, num_cols)}
        _LOG.debug("col_map=%s", col_map)
        #
        PcaFactorComputer.check_stabilized_eigvec(col_map, num_cols)
        return col_map, distances

    @staticmethod
    def _build_stable_eig_map2(
        prev_eigvec_df: pd.DataFrame, eigvec_df: pd.DataFrame
    ) -> Tuple[Dict[int, Tuple[Optional[int], int]], None]:
        """
        Different implementation of `_build_stable_eig_map()`.
        """

        def eigvec_coeff(
            v1: pd.Series, v2: pd.Series, thr: float = 1e-3
        ) -> Optional[int]:
            for sign in (-1, 1):
                diff = PcaFactorComputer.eigvec_distance(v1, sign * v2)
                _LOG.debug("v1=\n%s\nv2=\n%s\n-> diff=%s", v1, sign * v2, diff)
                if diff < thr:
                    return sign
            return None

        hpandas.dassert_strictly_increasing_index(prev_eigvec_df)
        hpandas.dassert_strictly_increasing_index(eigvec_df)
        # TODO(gp): This code can be sped up by:
        # 1) keeping a running list of the v2 columns already mapped so that
        #    we don't have to check over and over.
        # 2) once we find a match between columns, move to the next one v1
        # For now we just care about functionality.
        num_cols = eigvec_df.shape[1]
        col_map: Dict[int, Tuple[Optional[int], int]] = {}
        for i in range(num_cols):
            for j in range(num_cols):
                coeff = eigvec_coeff(
                    prev_eigvec_df.iloc[:, i], eigvec_df.iloc[:, j]
                )
                _LOG.debug("i=%s, j=%s, coeff=%s", i, j, coeff)
                if coeff:
                    _LOG.debug("i=%s -> j=%s", i, j)
                    hdbg.dassert_not_in(
                        i, col_map, msg="i=%s col_map=%s" % (i, col_map)
                    )
                    col_map[i] = (coeff, j)
        # Sanity check.
        PcaFactorComputer.check_stabilized_eigvec(col_map, num_cols)
        # Add dummy var to keep the same interface of _build_stable_eig_map.
        dummy = None
        return col_map, dummy

    def _execute(self, df: pd.DataFrame, ts: int) -> pd.Series:
        _LOG.debug("ts=%s", ts)
        hpandas.dassert_strictly_increasing_index(df)
        # Compute correlation.
        df = coexplor.handle_nans(df, self.nan_mode_in_data)
        corr_df = df.corr()
        corr_df = coexplor.handle_nans(corr_df, self.nan_mode_in_corr)
        _LOG.debug("corr_df=%s", corr_df)
        # Use the last datetime as timestamp.
        dt = df.index.max()
        _LOG.debug("ts=%s", dt)
        # Compute eigenvalues and eigenvectors.
        eigval, eigvec = np.linalg.eigh(corr_df)
        # Sort eigenvalues, if needed.
        if self.do_sort_eigvals:
            _, eigval, eigvec = self.sort_eigval(eigval, eigvec)
        _LOG.debug("eigval=\n%s\neigvec=\n%s", eigval, eigvec)
        # Package eigenvalues.
        eigval_df = pd.DataFrame([eigval], index=[dt])
        eigval_df = eigval_df.multiply(1 / eigval_df.sum(axis=1), axis="index")
        # Package eigenvectors.
        if np.isnan(eigval_df).all().all():
            eigvec = np.nan * eigvec
        # TODO(gp): Make sure eigenvec are normalized.
        eigvec_df = pd.DataFrame(eigvec, index=corr_df.columns)
        _LOG.debug("eigvec_df=%s", eigvec_df)
        if self.do_stabilize_eig:
            eigval_df, eigvec_df = self._stabilize_eig(eigval_df, eigvec_df)
        # Store results.
        self._ts.append(ts)
        #
        _LOG.debug("eigval_df=%s", eigval_df)
        self._eigval_df[ts] = eigval_df
        #
        _LOG.debug("eigvec_df=\n%s", eigvec_df)
        self._eigvec_df[ts] = eigvec_df
        if self._eig_num is None:
            self._eig_num = eigvec_df.shape[1]
            self._eig_comp_num = eigvec_df.shape[0]
        # Turn results into a pd.Series.
        res = self.linearize_eigval_eigvec(eigval_df, eigvec_df)
        hdbg.dassert_isinstance(res, pd.Series)
        return res

    def _stabilize_eig(
        self, eigval_df: pd.DataFrame, eigvec_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if not self._ts:
            return eigval_df, eigvec_df
        # Get previous ts.
        prev_ts = self._ts[-1]
        prev_eigvec_df = self._eigvec_df[prev_ts]
        # Check if they are stable.
        num_fails = self.are_eigenvectors_stable(prev_eigvec_df, eigvec_df)
        if num_fails > 0:
            _LOG.debug(
                "Eigenvalues not stable: prev_ts=%s"
                "\nprev_eigvec_df=\n%s"
                "\neigvec_df=\n%s"
                "\nnum_fails=%s",
                prev_ts,
                prev_eigvec_df,
                eigvec_df,
                num_fails,
            )
            col_map, _ = self._build_stable_eig_map(prev_eigvec_df, eigvec_df)
            shuffled_eigval_df, shuffled_eigvec_df = self.shuffle_eigval_eigvec(
                eigval_df, eigvec_df, col_map
            )
            # Check.
            # TODO(gp): Use Frobenius norm compared to identity.
            if False:
                num_fails = self.are_eigenvectors_stable(
                    prev_eigvec_df, shuffled_eigvec_df
                )
                hdbg.dassert_eq(
                    num_fails,
                    0,
                    "prev_eigvec_df=\n%s\n" "shuffled_eigvec_df=\n%s",
                    prev_eigvec_df,
                    shuffled_eigvec_df,
                )
            eigval_df = shuffled_eigval_df
            eigvec_df = shuffled_eigvec_df
        return eigval_df, eigvec_df


# #############################################################################


# TODO(gp): Factor out interface once this code is stable.
class FactorLoadingStatsmodelComputer:
    """
    Compute factor loading from target df (e.g., returns) and factor df.

    Timing assumption:
    - All timing info are in terms of timestamps (date times and not dates)
      with timezone (unless the timezones are common to all data and can be removed)
    - Each value is available at the corresponding timestamp
    """

    def __init__(self) -> None:
        super().__init__()
        self._residuals: List = []

    def transform(self, target_df: pd.DataFrame, factor_df: pd.DataFrame) -> None:
        """
        Express each row of target_df in terms of previous rows of factor_df.
        """
