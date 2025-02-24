"""
Import as:

import core.plotting.pnl as cplopnl
"""

import calendar
import logging
from typing import Dict, Optional, Tuple, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import core.finance as cofinanc
import core.plotting.plotting_utils as cplpluti
import core.statistics as costatis
import helpers.hdataframe as hdatafr

_LOG = logging.getLogger(__name__)

_COLORMAP = cplpluti.COLORMAP


def plot_yearly_barplot(
    log_rets: pd.Series,
    unit: str = "ratio",
    unicolor: bool = False,
    orientation: str = "vertical",
    figsize: Optional[Tuple[int, int]] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot a barplot of log returns statistics by year.

    :param log_rets: input series of log returns
    :param unit: "ratio", "%" or "bps" scaling coefficient
    :param unicolor: if True, plot all bars in neutral blue color
    :param orientation: vertical or horizontal bars
    :param figsize: size of plot
    :param ax: axes
    """
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    yearly_log_returns = log_rets.resample("Y").sum()
    yearly_pct_returns = cofinanc.convert_log_rets_to_pct_rets(yearly_log_returns)
    yearly_returns = yearly_pct_returns * scale_coeff
    yearly_returns.index = yearly_returns.index.year
    ax = ax or plt.gca()
    cplpluti.plot_barplot(
        yearly_returns,
        annotation_mode="value",
        orientation=orientation,
        title=f"Annual returns ({unit})",
        unicolor=unicolor,
        ax=ax,
        figsize=figsize,
    )
    if orientation == "vertical":
        xlabel = "year"
        ylabel = unit
    elif orientation == "horizontal":
        xlabel = unit
        ylabel = "year"
    else:
        raise ValueError("Invalid orientation='%s'" % orientation)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def plot_monthly_heatmap(
    log_rets: pd.Series, unit: str = "ratio", ax: Optional[mpl.axes.Axes] = None
) -> None:
    """
    Plot a heatmap of log returns statistics by year and month.

    :param log_rets: input series of log returns
    :param unit: "ratio", `%` or "bps" scaling coefficient
    :param ax: axes
    """
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    ax = ax or plt.gca()
    monthly_pct_spread = _calculate_year_to_month_spread(log_rets)
    monthly_spread = monthly_pct_spread * scale_coeff
    cmap = sns.diverging_palette(10, 133, as_cmap=True)
    sns.heatmap(monthly_spread, center=0, cmap=cmap, annot=True, fmt=".2f", ax=ax)
    ax.set_title(f"Monthly returns ({unit})")
    ax.tick_params(axis="y", rotation=0)


def plot_pnl(
    pnls: Dict[int, pd.Series],
    title: Optional[str] = None,
    colormap: Optional[_COLORMAP] = None,
    figsize: Optional[Tuple[int]] = None,
    start_date: Optional[Union[str, pd.Timestamp]] = None,
    end_date: Optional[Union[str, pd.Timestamp]] = None,
    nan_mode: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot pnls for dict of pnl time series.

    :param pnls: dict of pnl time series
    :param title: plot title
    :param colormap: matplotlib colormap name
    :param figsize: size of plot
    :param start_date: left limit value of the X axis
    :param end_date: right limit value of the X axis
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param xlabel: label of the X axis
    :param ylabel: label of the Y axis
    :param ax: axes
    """
    title = title or ""
    colormap = colormap or "rainbow"
    nan_mode = nan_mode or "drop"
    xlabel = xlabel or None
    ylabel = ylabel or None
    fstr = "{col} (SR={sr})"
    ax = ax or plt.gca()
    #
    pnls_notna = {}
    empty_srs = []
    for key, srs in pnls.items():
        srs = hdatafr.apply_nan_mode(srs, mode=nan_mode)
        if srs.dropna().empty:
            empty_srs.append(key)
        else:
            pnls_notna[key] = srs
    if empty_srs:
        _LOG.warning(
            "Empty input series were dropped: '%s'",
            ", ".join([str(x) for x in empty_srs]),
        )
    df_plot = pd.concat(pnls_notna, axis=1)
    # Compute sharpe ratio for every time series.
    sharpe_ratio = {
        key: costatis.compute_annualized_sharpe_ratio(srs)
        for key, srs in pnls.items()
    }
    sharpe_ratio = pd.Series(sharpe_ratio)
    sharpe_cols = [
        [round(sr, 1), df_plot.columns[i]] for i, sr in enumerate(sharpe_ratio)
    ]
    # Change column names and order to column names with sharpe ratio.
    df_plot.columns = [
        fstr.format(col=str(item[1]), sr=str(item[0])) for item in sharpe_cols
    ]
    sharpe_cols = sorted(sharpe_cols, key=lambda x: x[0], reverse=True)
    sorted_names = [
        fstr.format(col=str(item[1]), sr=str(item[0])) for item in sharpe_cols
    ]
    df_plot = df_plot.reindex(sorted_names, axis=1)
    # Plotting the dataframe without dropping `NaN`s in each column results in
    # a missing line for some of the pnls. To avoid it, plot by column.
    cmap = mpl.cm.get_cmap(colormap)
    colors = np.linspace(0, 1, df_plot.shape[1])
    colors = [cmap(c) for c in colors]
    for color, col in zip(colors, df_plot.columns):
        df_plot[col].cumsum().dropna().plot(ax=ax, color=color, figsize=figsize)
    # Setting fixed borders of x-axis.
    left_lim = start_date or min(df_plot.index)
    right_lim = end_date or max(df_plot.index)
    ax.set_xlim([left_lim, right_lim])
    # Formatting.
    ax.set_title(title, fontsize=20)
    ax.set_ylabel(ylabel, fontsize=20)
    ax.set_xlabel(xlabel, fontsize=20)
    ax.legend(prop=dict(size=13), loc="upper left")


def _calculate_year_to_month_spread(log_rets: pd.Series) -> pd.DataFrame:
    """
    Calculate log returns statistics by year and month.

    :param log_rets: input series of log returns
    :return: dataframe of log returns with years on y-axis and
        months on x-axis
    """
    srs_name = log_rets.name or 0
    log_rets_df = pd.DataFrame(log_rets)
    log_rets_df["year"] = log_rets_df.index.year
    log_rets_df["month"] = log_rets_df.index.month
    log_rets_df.reset_index(inplace=True)
    monthly_log_returns = log_rets_df.groupby(["year", "month"])[srs_name].sum()
    monthly_pct_returns = cofinanc.convert_log_rets_to_pct_rets(
        monthly_log_returns
    )
    monthly_pct_spread = monthly_pct_returns.unstack()
    monthly_pct_spread.columns = monthly_pct_spread.columns.map(
        lambda x: calendar.month_abbr[x]
    )
    return monthly_pct_spread
