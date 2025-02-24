"""
Import as:

import core.plotting.correlation as cplocorr
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import matplotlib as mpl
import matplotlib.cm as mcm
import matplotlib.colors as mcolor
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as schier
import seaborn as sns
import sklearn.metrics as smetri

import core.explore as coexplor
import core.plotting.plotting_utils as cplpluti
import core.signal_processing as csigproc
import core.statistics as costatis
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


FIG_SIZE = (20, 5)


# #############################################################################
# Correlation-type plots
# #############################################################################


def plot_heatmap(
    corr_df: pd.core.frame.DataFrame,
    mode: Optional[str] = None,
    annot: Union[bool, str] = "auto",
    figsize: Optional[Tuple[int, int]] = None,
    title: Optional[str] = None,
    vmin: float = -1.0,
    vmax: float = 1.0,
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot a heatmap for a corr / cov df.

    :param corr_df: df to plot a heatmap
    :param mode: "heatmap_semitriangle", "heatmap" or "clustermap"
    :param annot: determines whether to use annotations
    :param figsize: if nothing specified, basic (20,5) used
    :param title: title for the plot
    :param vmin: minimum value to anchor the colormap
    :param vmax: maximum value to anchor the colormap
    :param ax: axes in which to draw the plot
    """
    figsize = figsize or FIG_SIZE
    # Sanity check.
    if corr_df.empty:
        _LOG.warning("Can't plot heatmap for empty `corr_df`")
        return
    if corr_df.shape[0] > 20:
        _LOG.warning("The corr_df.shape[0]='%s' > 20", corr_df.shape[0])
        figsize = (figsize[0], figsize[0])
    if np.all(np.isnan(corr_df)):
        _LOG.warning(
            "Can't plot heatmap with only nans:\n%s", corr_df.to_string()
        )
        return
    #
    if annot == "auto":
        annot = corr_df.shape[0] < 10
    # Generate a custom diverging colormap.
    cmap = _get_heatmap_colormap()
    mode = mode or "heatmap"
    if mode in ("heatmap", "heatmap_semitriangle"):
        # Set up the matplotlib figure.
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)
        mask = _get_heatmap_mask(corr_df, mode)
        sns.heatmap(
            corr_df,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            # Use correct aspect ratio.
            square=True,
            annot=annot,
            fmt=".2f",
            cbar_kws={
                "shrink": 0.5,
                "location": "left",
                "use_gridspec": False,
                "pad": 0.03,
            },
            mask=mask,
            ax=ax,
        )
        ax.set_title(title)
    elif mode == "clustermap":
        hdbg.dassert_is(ax, None)
        g = sns.clustermap(
            corr_df,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            square=True,
            annot=annot,
            figsize=figsize,
        )
        g.ax_heatmap.set_title(title)
        return
    else:
        raise RuntimeError("Invalid mode='%s'" % mode)
    ax.tick_params(axis="y", labelright=True, labelleft=False, labelrotation=0)


# TODO(gp): Add an option to mask out the correlation with low pvalues
# http://stackoverflow.com/questions/24432101/correlation-coefficients-and-p-values-for-all-pairs-of-rows-of-a-matrix
def plot_correlation_matrix(
    df: pd.core.frame.DataFrame,
    mode: Optional[str] = None,
    annot: Union[bool, str] = False,
    figsize: Optional[Tuple[int, int]] = None,
    title: Optional[str] = None,
    method: Optional[str] = None,
    min_periods: Optional[int] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> pd.core.frame.DataFrame:
    """
    Compute correlation matrix and plot its heatmap.

    :param df: Df to compute correlation matrix and plot a heatmap
    :param mode: "heatmap_semitriangle", "heatmap" or "clustermap"
    :param annot: determines whether to use annotations
    :param figsize: if nothing specified, basic (20,5) used
    :param title: title for the plot
    :param method: "pearson", "kendall", "spearman" or callable method of correlation
    :param min_periods: minimum number of observations required per pair of columns to have
        a valid result; currently only available for Pearson and Spearman correlation
    """
    if df.empty:
        _LOG.warning("Skipping correlation matrix since `df` is empty")
        return None
    # Compute the correlation matrix.
    method = method or "pearson"
    corr_df = df.corr(method=method, min_periods=min_periods)
    # Plot heatmap.
    plot_heatmap(
        corr_df,
        mode=mode,
        annot=annot,
        figsize=figsize,
        title=title,
        vmin=-1.0,
        vmax=1.0,
        ax=ax,
    )
    return corr_df


def display_corr_df(df: pd.core.frame.DataFrame) -> None:
    """
    Display a correlation df with values with 2 decimal places.
    """
    if df is not None:
        df_tmp = df.applymap(lambda x: "%.2f" % x)
        coexplor.display_df(df_tmp)
    else:
        _LOG.warning("Can't display correlation df since it is None")


def plot_effective_correlation_rank(
    df: pd.DataFrame,
    q_values: Optional[List[float]] = None,
    figsize: Optional[Tuple[int, int]] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> List[float]:
    """
    Compute effective rank of data correlation based on singular values.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    # Defaults include the endpoints and a value in-between.
    # - q = 1 corresponds to entropy and yields the largest expected rank
    # - q = np.inf corresponds to "stable rank" and yields the smallest expected
    #   rank
    q_values = q_values or [1, 2, np.inf]
    hdbg.dassert_isinstance(q_values, list)
    # Calculate (sample) correlation matrix.
    corr = df.corr()
    # Calculate eigenvalues of sample correlation matrix (i.e., squared
    # singular values of `df`).
    sv = np.linalg.svd(corr.values, hermitian=True)[1]
    singular_values = pd.Series(index=range(1, len(sv) + 1), data=sv)
    # Calculate effective rank over q_values.
    effective_ranks = []
    for q in q_values:
        effective_rank = costatis.compute_hill_number(singular_values, q)
        effective_ranks.append(effective_rank)
    # Plot singular values.
    singular_values.plot(
        title="Singular values and effective rank",
        ylim=(0, None),
        label="Correlation matrix eigenvalues",
    )
    # Plot effective rank bars.
    colors = mcm.get_cmap("Set1")(np.linspace(0, 1, len(effective_ranks)))
    for idx, effective_rank in enumerate(effective_ranks):
        q = q_values[idx]
        color = colors[idx]
        ax.axvline(
            effective_rank,
            label=f"q={q} effective rank={effective_rank:.2f}",
            color=color,
            linestyle="--",
        )
    ax.legend()
    return effective_ranks


def plot_corr_over_time(
    corr_df: pd.core.frame.DataFrame,
    mode: Optional[str] = None,
    annot: bool = False,
    num_cols: int = 4,
) -> None:
    """
    Plot correlation over time.
    """
    mode = mode or "heatmap"
    timestamps = corr_df.index.get_level_values(0).unique()
    if len(timestamps) > 20:
        _LOG.warning("The first level of index length='%s' > 20", len(timestamps))
    # Get the axes.
    fig, axes = cplpluti.get_multiple_plots(
        len(timestamps), num_cols=num_cols, y_scale=4, sharex=True, sharey=True
    )
    # Add color map bar on the side.
    cbar_ax = fig.add_axes([0.91, 0.3, 0.03, 0.4])
    cmap = _get_heatmap_colormap()
    for i, dt in enumerate(timestamps):
        corr_tmp = corr_df.loc[dt]
        # Generate a mask for the upper triangle.
        mask = _get_heatmap_mask(corr_tmp, mode)
        axis = axes[i]  # type: ignore
        # Plot.
        sns.heatmap(
            corr_tmp,
            cmap=cmap,
            cbar=i == 0,
            cbar_ax=None if i else cbar_ax,
            vmin=-1,
            vmax=1,
            square=True,
            annot=annot,
            fmt=".2f",
            linewidths=0.5,
            mask=mask,
            # cbar_kws={"shrink": .5},
            ax=axis,
        )
        axis.set_title(timestamps[i])


# #############################################################################
# Eval metrics plots
# #############################################################################


def plot_confusion_heatmap(
    y_true: Union[List[Union[float, int]], np.array],
    y_pred: Union[List[Union[float, int]], np.array],
    return_results: bool = False,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> Any:
    """
    Construct and plot a heatmap for a confusion matrix of fact and prediction.

    :param y_true: true values
    :param y_pred: predictions
    :param return_results: determines whether to return result dataframes
    """
    confusion = smetri.confusion_matrix(y_true, y_pred)
    labels = set(list(y_true))
    df_out = pd.DataFrame(confusion, index=labels, columns=labels)
    df_out_percentage = df_out.apply(lambda x: x / x.sum(), axis=1)
    if axes is None:
        _, axes = plt.subplots(figsize=(FIG_SIZE), ncols=2)
    # TODO(Paul): Reconsider whether we should use `plot_heatmap()` here:
    #  either we should change the semantics of `plot_heatmap()`, or else
    #  we should not rely on a correlation plotting function.
    plot_heatmap(
        df_out,
        mode="heatmap",
        vmin=df_out.min().min(),
        vmax=df_out.max().max(),
        ax=axes[0],
    )
    plot_heatmap(
        df_out_percentage,
        mode="heatmap",
        vmin=df_out_percentage.min().min(),
        vmax=df_out_percentage.max().max(),
        ax=axes[1],
    )
    if return_results:
        return df_out, df_out_percentage
    return None


def select_series_to_keep(df_corr: pd.DataFrame, threshold: float) -> List[str]:
    """
    Select correlate series to keep.

    Iterate through the correlation dataframe by picking the time series that has
    the largest number of coefficients above the correlation threshold. If there
    are multiple such time series, pick the first one i.e. with the min index.
    Next, take all the time series that have correlation above the threshold
    with the selected one and drop them from the correlation matrix.
    Continue the process on the remaining subset matrix until all of the time series
    in the remaining matrix have a correlation below the threshold. At this point,
    stop the process and return the list of time series in the remaining matrix.

    :param df_corr: dataframe with time series correlations
    :param threshold: correlation threshold to remove time series
    :returns: list of series to remove
    """
    corr = df_corr.copy()
    # Fill diag with 0 to ensure that the correlations of time series with themselves
    # (i.e. 1.0) are not selected when coefficients compared to the threshold.
    np.fill_diagonal(corr.values, 0)
    while True:
        subset_corr = corr[abs(corr) > threshold]
        if subset_corr.isnull().values.all():
            return list(subset_corr.columns.values)
        column_to_keep = (
            subset_corr[abs(subset_corr) > threshold].notnull().sum().idxmax()
        )
        columns_to_remove = subset_corr[
            subset_corr[column_to_keep].notnull()
        ].index
        corr = subset_corr.drop(columns_to_remove).drop(columns_to_remove, axis=1)


def cluster_and_select(
    df: pd.DataFrame,
    num_clust: int,
    corr_thr: float = 0.8,
    show_corr_plots: bool = True,
    show_dendogram: bool = True,
    method: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """
    Select a subset of time series, using clustering and correlation approach.

    Cluster time series using hierarchical clustering algorithm defined by
    the linkage matrix. We use compute_linkage() function to compute linkage
    matrix with the default 'average' method (or the method specified in the input).
    Once the clusters are formed and each time series is assigned to a
    specific cluster, the correlations amongst time series produced
    for every such cluster. The correlation matrix is then passed to
    select_series_to_remove() method, which returns the list of highly
    correlated time series within the cluster (above the threshold specified)
    that are removed from the total list of time series to consider.
    Once the function iterated over every cluster and removed from the
    original list of time series, it returns the reduced list of time series
    with the equivalent amount of information that can be used to consider
    for further analysis. The function also produces dendogram of clustered
    time series along with correlation plots at different stages of execution.

    :param df: input dataframe with columns as time series
    :param num_clust: number of clusters to compute
    :param corr_thr: correlation threshold
    :param show_corr_plots: bool whether to show correlation plots or not
    :param show_dendogram: bool whether to show original clustering dendogram
    :param method: distance calculation method
    :returns: list of names of series to keep
    """
    method = method or "average"
    df = df.drop(df.columns[df.nunique() == 1], axis=1)
    if df.shape[1] < 2:
        _LOG.warning("Skipping correlation matrix since df is %s", str(df.shape))
        return None
    # Cluster the time series.
    z_linkage = compute_linkage(df, method=method)
    clusters = schier.fcluster(z_linkage, num_clust, criterion="maxclust")
    series_to_keep: List[str] = []
    dict_series_to_keep = {}
    df_name_clust = pd.DataFrame(
        {"name": list(df.columns.values), "cluster": clusters}
    )
    # Plot the dendogram of clustered series.
    if show_dendogram:
        plot_dendrogram(df, method=method)
    # Plot the correlation heatmap for each cluster and drop highly correlated ts.
    for cluster_name, cluster_series in df_name_clust.groupby("cluster"):
        names = list(cluster_series["name"])
        cluster_subset = df[names]
        cluster_corr = cluster_subset.corr()
        if show_corr_plots:
            plot_heatmap(cluster_corr)
            plt.show()
        original = set(names.copy())
        # Remove series that have correlation above the threshold specified.
        remaining_series = select_series_to_keep(cluster_corr, corr_thr)
        series_to_keep = series_to_keep + remaining_series
        dict_series_to_keep[cluster_name] = remaining_series
        plt.show()
        _LOG.info("Current cluster is %s", cluster_name)
        _LOG.info("Original series in cluster is %s", list(original))
        _LOG.info("Series to keep in cluster is %s", remaining_series)
    # Print the final list of series to keep.
    _LOG.info("Final number of selected time series is %s", len(series_to_keep))
    _LOG.info("Series to keep are: %s", series_to_keep)
    return dict_series_to_keep


def compute_linkage(df: pd.DataFrame, method: Optional[str] = None) -> np.ndarray:
    """
    Perform hierarchical clustering.

    Linkage methods available in the official documentation:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html

    :param df: input dataframe with columns as series
    :method: distance calculation method
    :returns: hierarchical clustering encoded as a linkage matrix
    """
    method = method or "average"
    corr = df.corr()
    linkage = schier.linkage(corr, method=method)
    linkage = cast(np.ndarray, linkage)
    return linkage


def plot_dendrogram(
    df: pd.core.frame.DataFrame,
    method: Optional[str] = None,
    figsize: Optional[Tuple[int, int]] = None,
    ax: Optional[mpl.axes.Axes] = None,
    **kwargs: Any,
) -> None:
    """
    Plot a dendrogram.

    A dendrogram is a diagram representing a tree.

    :param df: df to plot a heatmap
    :param method: string distance calculation method
    :param figsize: if nothing specified, basic (20,5) used
    :param kwargs: kwargs for `sp.cluster.hierarchy.dendrogram`
    """
    # Look at:
    # ~/.conda/envs/root_longman_20150820/lib/python2.7/site-packages/seaborn/matrix.py
    # https://joernhees.de/blog/2015/08/26/scipy-hierarchical-clustering-and-dendrogram-tutorial/
    # Drop constant columns.
    method = method or "average"
    df = df.replace([None], np.nan)
    constant_cols = df.columns[(df.diff().iloc[1:] == 0).all()]
    if not constant_cols.empty:
        _LOG.warning("Excluding constant columns: %s", constant_cols.tolist())
        df = df.drop(columns=constant_cols)
    if df.shape[1] < 2:
        _LOG.warning("Skipping correlation matrix since df is %s", str(df.shape))
        return
    z_linkage = compute_linkage(df, method=method)
    if not {"leaf_rotation", "orientation"}.intersection(kwargs):
        kwargs["leaf_rotation"] = 90
    ax = ax or plt.gca()
    schier.dendrogram(
        z_linkage,
        labels=df.columns.tolist(),
        ax=ax,
        **kwargs,
    )
    figsize = figsize or FIG_SIZE
    ax.get_figure().set_size_inches(figsize)
    ax.set_title("Hierarchical Clustering Dendrogram")
    ax.set_ylabel("Distance")


def plot_rolling_correlation(
    srs1: pd.Series,
    srs2: pd.Series,
    tau: float,
    demean: bool = True,
    min_periods: int = 0,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
    mode: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
    plot_zero_line: bool = True,
    ylim: Optional[str] = None,
) -> None:
    """
    Return rolling correlation between 2 series and plot rolling correlation.

    :param srs1: first series
    :param srs2: second series
    :param tau: tau correlation coefficient
    :param demean: bool demean
    :param min_periods: min periods
    :param min_depth: min depth
    :param max_depth: max depth
    :param p_moment: p moment
    :param mode: corr or zcorr
    :param ax: axis
    :param events: list of tuples with dates and labels to point out on the plot
    :param ylim: either "fixed" or "scalable" (if None). If ylim is set to "fixed",
        the y-axis limits are (-1, 1).
    """
    mode = mode or "corr"
    # Calculate and plot rolling correlation.
    ax = ax or plt.gca()
    # Calculate rolling correlation.
    if mode == "zcorr":
        roll_correlation = csigproc.compute_rolling_zcorr
        title = "Z Correlation of 2 time series"
        label = "Rolling z correlation"
    elif mode == "corr":
        roll_correlation = csigproc.compute_rolling_corr
        title = "Correlation of 2 time series"
        label = "Rolling correlation"
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    # Calculate rolling correlation with the given mode.
    roll_corr = roll_correlation(
        srs1,
        srs2,
        tau=tau,
        demean=demean,
        min_periods=min_periods,
        min_depth=min_depth,
        max_depth=max_depth,
        p_moment=p_moment,
    )
    # Plot rolling correlation.
    roll_corr.plot(ax=ax, title=title, label=label)
    ylim = ylim or "scalable"
    if ylim == "fixed":
        ax.set_ylim(-1, 1)
    elif ylim == "scalable":
        pass
    else:
        raise ValueError("Invalid `ylim`='%s'" % ylim)
    # Calculate correlation whole period.
    whole_period = srs1.corr(srs2)
    # Plot correlation whole period.
    ax.axhline(
        whole_period,
        linewidth=0.8,
        ls="--",
        c="darkviolet",
        label="Whole-period correlation",
    )
    if plot_zero_line:
        ax.axhline(0, linewidth=0.8, color="k")
    ax.set_xlabel("period")
    ax.set_ylabel("correlation")
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.legend()


def _get_heatmap_mask(corr: pd.DataFrame, mode: str) -> Optional[np.ndarray]:
    if mode == "heatmap_semitriangle":
        # Generate a mask for the upper triangle.
        mask = np.zeros_like(corr, dtype=np.bool_)
        mask[np.triu_indices_from(mask)] = True
    elif mode == "heatmap":
        mask = None
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    return mask


def _get_heatmap_colormap() -> mcolor.LinearSegmentedColormap:
    """
    Generate a custom diverging colormap useful for heatmaps.
    """
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    return cmap
