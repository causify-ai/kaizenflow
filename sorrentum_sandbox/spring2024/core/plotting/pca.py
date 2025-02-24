"""
Import as:

import core.plotting.pca as cplopca
"""

import logging
from typing import Any, List, Optional, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import sklearn.decomposition as sdecom
import sklearn.utils.validation as suvali

import core.plotting.plotting_utils as cplpluti
import core.signal_processing as csigproc
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


_PCA_TYPE = Union[sdecom.PCA, sdecom.IncrementalPCA]


class PCA:
    def __init__(self, mode: str, **kwargs: Any):
        if mode == "standard":
            self.pca = sdecom.PCA(**kwargs)
        elif mode == "incremental":
            self.pca = sdecom.IncrementalPCA(**kwargs)
        else:
            raise ValueError("Invalid mode='%s'" % mode)

    def plot_components(
        self,
        num_components: Optional[int] = None,
        num_cols: int = 4,
        y_scale: Optional[float] = 4,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> None:
        """
        Plot principal components.

        :param num_components: number of top components to plot
        :param y_scale: the height of each plot. If `None`, the size of the whole
            figure equals the default `figsize`
        :param num_cols: number of columns to use in the subplot
        """
        suvali.check_is_fitted(self.pca)
        pcs = pd.DataFrame(self.pca.components_)
        max_pcs = self.pca.components_.shape[0]
        num_components = self._get_num_pcs_to_plot(num_components, max_pcs)
        _LOG.info(
            "Plotting the first {num_components} components out of %s", max_pcs
        )
        if axes is None:
            _, axes = cplpluti.get_multiple_plots(
                num_components,
                num_cols=num_cols,
                y_scale=y_scale,
                sharex=True,
                sharey=True,
            )
            plt.suptitle("Principal components")
        else:
            hdbg.dassert_eq(len(axes), num_components)
        for i in range(num_components):
            pc = pcs.iloc[i, :]
            pc.plot(
                kind="barh", ax=axes[i], title="PC%s" % i, edgecolor="tab:blue"
            )

    def plot_explained_variance(
        self,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> None:
        if ax is None:
            _, ax = plt.subplots()
        suvali.check_is_fitted(self.pca)
        explained_variance_ratio = pd.Series(self.pca.explained_variance_ratio_)
        eigenvals = pd.Series(self.pca.explained_variance_)
        # Plot explained variance.
        explained_variance_ratio.cumsum().plot(
            title="Explained variance ratio", lw=5, ylim=(0, 1), ax=ax
        )
        (eigenvals / eigenvals.max()).plot(color="g", kind="bar", rot=0, ax=ax)

    def fit(self, X: pd.DataFrame, standardize: bool = False) -> _PCA_TYPE:
        if standardize:
            X = (X - X.mean()) / X.std()
        return self.pca.fit(X)

    @staticmethod
    def _get_num_pcs_to_plot(num_pcs_to_plot: Optional[int], max_pcs: int) -> int:
        """
        Get the number of principal components to coplotti.
        """
        if num_pcs_to_plot is None:
            num_pcs_to_plot = max_pcs
            _LOG.warning("Plotting all %s components", num_pcs_to_plot)
        else:
            if num_pcs_to_plot > max_pcs:
                _LOG.warning(
                    "Overall number of components is less than requested"
                )
                num_pcs_to_plot = max_pcs
        hdbg.dassert_lte(1, num_pcs_to_plot)
        return num_pcs_to_plot


def plot_ipca(
    df: pd.DataFrame,
    num_pc: int,
    tau: float,
    num_cols: int = 2,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> None:
    """
    Plot a panel of iPCA calculation results over time.

    Plots include:
        - Eigenvalues estimates
        - Eigenvectors estimates
        - Eigenvector angular distances
    """
    eigenvalues, eigenvectors = csigproc.compute_ipca(df, num_pc=num_pc, tau=tau)
    eigenvalues.plot(title="Eigenvalues")
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(
            num_plots=num_pc,
            num_cols=num_cols,
            sharex=True,
            sharey=True,
        )
    for i in range(num_pc):
        eigenvectors[i].plot(ax=axes[i], title=f"Eigenvectors PC{i}")
    eigenvector_diffs = csigproc.compute_eigenvector_diffs(eigenvectors)
    eigenvector_diffs.plot(title="Eigenvector angular distances")
