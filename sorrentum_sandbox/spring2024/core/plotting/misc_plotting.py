"""
Import as:

import core.plotting.misc_plotting as cplmiplo
"""

# TODO(Paul): Move functions out of here into appropriate files.
# TODO(gp): Test with a gallery notebook and/or with unit tests.

import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy as sp
import seaborn as sns
import statsmodels as statsm
import statsmodels.api as sm
import statsmodels.regression.rolling as srroll

import core.plotting.plotting_utils as cplpluti
import core.signal_processing as csigproc
import core.statistics as costatis
import helpers.hdataframe as hdatafr
import helpers.hdbg as hdbg
import helpers.hlist as hlist
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)

FIG_SIZE = (20, 5)

_DATETIME_TYPES = [
    "year",
    "month",
    "quarter",
    "weekofyear",
    "dayofweek",
    "hour",
    "minute",
    "second",
]

_COLORMAP = cplpluti.COLORMAP


# #############################################################################
# General plotting helpers
# #############################################################################


def plot_non_na_cols(
    df: pd.core.frame.DataFrame,
    sort: bool = False,
    ascending: bool = True,
    max_num: Optional[int] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> Any:
    """
    Plot a diagram describing the non-nans intervals for the columns of df.

    :param df: usual df indexed with times
    :param sort: sort the columns by number of non-nans
    :param ascending:
    :param max_num: max number of columns to plot
    """
    # Check that there are no repeated columns.
    # TODO(gp): dassert_no_duplicates
    hdbg.dassert_eq(len(hlist.find_duplicates(df.columns.tolist())), 0)
    # Note that the plot assumes that the first column is at the bottom of the
    # Assign 1.0 to all the non-nan value.
    df = df.where(df.isnull(), 1)
    # Sort.
    if sort:
        cnt = df.sum().sort_values(ascending=not ascending)
        df = df.reindex(cnt.index.tolist(), axis=1)
    _LOG.debug("Columns=%d %s", len(df.columns), ", ".join(df.columns))
    # Limit the number of elements.
    if max_num is not None:
        _LOG.warning(
            "Plotting only %d columns instead of all %d columns",
            max_num,
            df.shape[1],
        )
        hdbg.dassert_lte(1, max_num)
        if max_num > df.shape[1]:
            _LOG.warning(
                "Too many columns requested: %d > %d", max_num, df.shape[1]
            )
        df = df.iloc[:, :max_num]
    _LOG.debug("Columns=%d %s", len(df.columns), ", ".join(df.columns))
    _LOG.debug("To plot=\n%s", df.head())
    # Associate each column to a number between 1 and num_cols + 1.
    scale = pd.Series({col: idx + 1 for idx, col in enumerate(df.columns)})
    df *= scale
    num_cols = df.shape[1]
    # Heuristics to find the value of ysize.
    ysize = num_cols * 0.3
    figsize = (20, ysize)
    ax = df.plot(figsize=figsize, legend=False, ax=ax)
    # Force all the yticks to be equal to the column names and to be visible.
    ax.set_yticks(np.arange(num_cols, 0, -1))
    ax.set_yticklabels(reversed(df.columns.tolist()))
    return ax


def plot_categories_count(
    df: pd.core.frame.DataFrame,
    category_column: str,
    figsize: Optional[Tuple[int, int]] = None,
    title: Optional[str] = None,
    label: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
) -> None:
    """
    Plot countplot of a given `category_column`.

    :param df: df to plot
    :param category_column: categorical column to subset plots by
    :param figsize: if nothing specified, basic (20,5) used
    :param title: title for the plot
    """
    if not figsize:
        figsize = FIG_SIZE
    if not label:
        label = category_column
    num_categories = df[category_column].nunique()
    if num_categories > 10:
        ylen = math.ceil(num_categories / 26) * 5
        ax = sns.countplot(
            y=df[category_column],
            order=df[category_column].value_counts().index,
            ax=ax,
        )
        ax.set(xlabel=f"Number of {label}s")
        ax.set(ylabel=category_column.lower())
        figsize = (figsize[0], ylen)
        ax.get_figure().set_size_inches(figsize)
        for p in ax.patches:
            ax.text(
                p.get_width() + 0.1,
                p.get_y() + 0.5,
                str(round((p.get_width()), 2)),
            )
    else:
        ax = sns.countplot(
            x=df[category_column],
            order=df[category_column].value_counts().index,
            ax=ax,
        )
        ax.set(xlabel=category_column.lower())
        ax.set(ylabel=f"Number of {label}s")
        ax.get_figure().set_size_inches(figsize)
        for p in ax.patches:
            ax.annotate(p.get_height(), (p.get_x() + 0.35, p.get_height() + 1))
    title = title or f"Distribution by {category_column}"
    ax.set_title(title)


def plot_projection(
    df: pd.DataFrame,
    special_values: Optional[List[Any]] = None,
    mode: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    colormap: Optional[_COLORMAP] = None,
) -> None:
    """
    Plot lines where each column is not in special values.

    :param df: dataframe
    :param special_values: values to omit from plot. If `None`, omit `NaN`s
    :param mode: "scatter" or "no-scatter"; whether to add a scatter plot
    :param ax: axis on which to plot. If `None`, create an axis and plot there
    :param colormap: matplotlib colormap or colormap name
    """
    special_values = special_values or [None]
    mode = mode or "no-scatter"
    ax = ax or plt.gca()
    ax.set_yticklabels([])
    hpandas.dassert_strictly_increasing_index(df)
    hdbg.dassert_no_duplicates(df.columns.tolist())
    df = df.copy()
    # Get a mask for special values.
    special_val_mask = pd.DataFrame(
        np.full(df.shape, False), columns=df.columns, index=df.index
    )
    for curr_val in special_values:
        if pd.isna(curr_val):
            curr_mask = df.isna()
        elif np.isinf(curr_val):
            curr_mask = df.applymap(np.isinf)
        else:
            curr_mask = df.eq(curr_val)
        special_val_mask |= curr_mask
    # Replace non-special values with column numbers and special values with
    # `NaN`s.
    range_df = df.copy()
    for i in range(df.shape[1]):
        range_df.isetitem(i,i)
    df_to_plot = range_df.mask(special_val_mask, np.nan)
    # Plot.
    df_to_plot.plot(ax=ax, legend="reverse", colormap=colormap)
    if mode == "scatter":
        sns.scatterplot(
            data=df_to_plot,
            markers=["o"] * df.shape[1],
            ax=ax,
            legend=False,
            color=colormap,
        )
    elif mode == "no-scatter":
        pass
    else:
        raise ValueError("Invalid `mode`='%s'" % mode)


# #############################################################################
# Time series plotting
# #############################################################################


def plot_time_series_by_period(
    srs: pd.Series,
    period: str,
) -> None:
    """
    Average series values according to a datetime period.

    TODO(Paul): Consider adding support for other aggregations.

    srs: numerical series
    period: a period, such as "year", "month", "day", "hour", etc. This must
        be a `pd.DatetimeIndex` attribute:
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DatetimeIndex.html
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_isinstance(srs.index, pd.DatetimeIndex)
    hdbg.dassert_isinstance(period, str)
    hdbg.dassert(
        hasattr(srs.index, period),
        msg="Not an attribute of `pd.DatetimeIndex`, whose attributes are %s"
        % pd.core.arrays.DatetimeArray._datetimelike_ops,
    )
    if not srs.name:
        srs = srs.copy()
        srs.name = "values"
    df = srs.to_frame()
    periods = getattr(df.index, period)
    # Handle special cases that return np.arrays of datetime-type objects.
    if period in ["date", "time"]:
        periods = [x.isoformat() for x in periods]
        periods = pd.Index(periods)
    hdbg.dassert_isinstance(
        periods, pd.Index, msg="period=%s is not supported" % period
    )
    periods.name = period
    hdbg.dassert_lt(
        1,
        len(periods.unique()),
        msg="The unique period value found is `%s`. Multiple values expected."
        % periods[0],
    )
    sns.relplot(x=periods, y=srs.name, data=df, kind="line")


def plot_timeseries_distribution(
    srs: pd.Series,
    datetime_types: Optional[List[str]] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> None:
    """
    Plot timeseries distribution by.

    - "year",
    - "month",
    - "quarter",
    - "weekofyear",
    - "dayofweek",
    - "hour",
    - "second"
    unless otherwise provided by `datetime_types`.

    :param srs: timeseries pd.Series to plot
    :param datetime_types: types of pd.datetime, e.g. "month", "quarter"
    """
    hdbg.dassert_isinstance(srs, pd.Series)
    hdbg.dassert_isinstance(srs.index, pd.DatetimeIndex)
    if datetime_types is None:
        datetime_types = _DATETIME_TYPES
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(
            num_plots=len(datetime_types), num_cols=1
        )
    else:
        hdbg.dassert_eq(len(datetime_types), len(axes))
    srs = hdatafr.apply_nan_mode(srs, mode="drop")
    index_series = pd.Series(srs.index)
    for datetime_type, ax in zip(datetime_types, axes):
        sns.countplot(
            data=index_series.to_frame(),
            x=getattr(index_series.dt, datetime_type),
            ax=ax,
        )
        ax.set_title(f"Distribution by {datetime_type}")
        ax.set_xlabel(datetime_type, fontsize=12)
        ax.set_ylabel(f"Quantity of {srs.name}", fontsize=12)
        ax.get_figure().set_size_inches(FIG_SIZE)


def plot_timeseries_per_category(
    df: pd.core.frame.DataFrame,
    datetime_types: Optional[List["str"]],
    column: str,
    ts_column: str,
    category_column: str,
    categories: Optional[List[str]] = None,
    top_n: Optional[int] = None,
    figsize: Optional[Tuple[int, int]] = None,
) -> None:
    """
    Plot distribution (where `datetime_types` has the same meaning as in
    plot_headlines) for a given list of categories.

    If `categories` param is not specified, `top_n` must be specified and plots
    will show the `top_n` most popular categories.
    :param df: df to plot
    :param datetime_types: types of pd.datetime, e.g. "month", "quarter"
    :param column: distribution of which variable to represent
    :param ts_column: timeseries column
    :param category_column: categorical column to subset plots by
    :param categories: categories to represent
    :param top_n: number of top categories to use, if categories are not specified
    """
    if not figsize:
        figsize = FIG_SIZE
    use_index = False
    unique_rows = hpandas.drop_duplicates(df, use_index, subset=[column])
    if top_n:
        categories = (
            df[category_column].value_counts().iloc[:top_n].index.to_list()
        )
    hdbg.dassert(categories, "No categories found.")
    if not datetime_types:
        datetime_types = _DATETIME_TYPES
    for datetime_type in datetime_types:
        categories = cast(List[str], categories)
        rows = math.ceil(len(categories) / 3)
        fig, ax = plt.subplots(
            figsize=(FIG_SIZE[0], rows * 4.5),
            ncols=3,
            nrows=rows,
            constrained_layout=True,
        )
        ax = ax.flatten()
        a = iter(ax)
        for category in categories:
            j = next(a)
            # Prepare a subset of data for the current category only.
            rows_by_category = unique_rows.loc[
                unique_rows[categories] == category, :
            ]
            sns.countplot(
                getattr(rows_by_category[ts_column].dt, datetime_type), ax=j
            )
            j.set_ylabel(f"Quantity of {column}")
            j.set_xlabel(datetime_type)
            j.set_xticklabels(j.get_xticklabels(), rotation=45)
            j.set_title(category)
        fig.suptitle(f"Distribution by {datetime_type}")


# TODO(*): Rename. Maybe `plot_sequence_and_density()`.
def plot_cols(
    data: Union[pd.Series, pd.DataFrame],
    colormap: _COLORMAP = "rainbow",
    mode: Optional[str] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
    figsize: Optional[Tuple[float, float]] = (20, 10),
) -> None:
    """
    Plot lineplot and density plot for the given dataframe.

    :param data: data to plot
    :param colormap: preferred colors
    :param mode: "renormalize" or "default"
    :param axes: pair of axes for plot over time and density plot
    :param figsize: matplotlib figsize. Default is `(20, 10)`. If `None`, uses
        notebook default parameters
    """
    if isinstance(data, pd.Series):
        data = data.to_frame()
    if axes is None:
        _, axes = plt.subplots(2, ncols=1, figsize=figsize)
    if mode is None or mode == "default":
        pass
    elif mode == "renormalize":
        data = data.copy()
        data /= data.std()
    else:
        raise ValueError(f"Unsupported mode `{mode}`")
    data.replace([np.inf, -np.inf], np.nan).plot(
        kind="density", colormap=colormap, ax=axes[0]
    )
    data.plot(colormap=colormap, ax=axes[1])


# TODO(*): Check that data index size exceeds lags.
def plot_autocorrelation(
    signal: Union[pd.Series, pd.DataFrame],
    lags: int = 40,
    zero: bool = False,
    nan_mode: str = "conservative",
    fft: bool = True,
    title_prefix: Optional[str] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
    **kwargs: Any,
) -> None:
    """
    Plot ACF and PACF of columns.

    https://www.statsmodels.org/stable/_modules/statsmodels/graphics/tsaplots.html#plot_acf
    https://www.statsmodels.org/stable/_modules/statsmodels/tsa/stattools.html#acf

    :param axes: flat list of axes or `None`
    """
    if isinstance(signal, pd.Series):
        signal = signal.to_frame()
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(
            signal.shape[1] * 2, num_cols=2, y_scale=5
        )
    axis_pairs = zip(axes[::2], axes[1::2])
    title_prefix = title_prefix or ""
    # Replacing inf with nan to ensure non-empty plots generated.
    signal = costatis.replace_infs_with_nans(signal)
    for col, axis_pair in zip(signal.columns, axis_pairs):
        if nan_mode == "conservative":
            data = signal[col].fillna(0).dropna()
        else:
            raise ValueError(f"Unsupported nan_mode `{nan_mode}`")
        ax1 = axis_pair[0]
        # Partial correlation can be computed for lags up to 50% of the sample
        # size.
        lags_curr = min(lags, data.size // 2 - 1)
        # Exclude lag zero so that the y-axis does not get squashed.
        acf_title = title_prefix + f"{col} autocorrelation"
        _ = sm.graphics.tsa.plot_acf(
            data,
            lags=lags_curr,
            fft=fft,
            ax=ax1,
            zero=zero,
            title=acf_title,
            **kwargs,
        )
        ax2 = axis_pair[1]
        pacf_title = title_prefix + f"{col} partial autocorrelation"
        _ = sm.graphics.tsa.plot_pacf(
            data,
            lags=lags_curr,
            ax=ax2,
            zero=zero,
            title=pacf_title,
            **kwargs,
        )


def plot_seasonal_decomposition(
    srs: Union[pd.Series, pd.DataFrame],
    nan_mode: Optional[str] = None,
    figsize: Optional[Tuple[int, int]] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
    kwargs: Optional[dict] = None,
) -> None:
    """
    Plot seasonal trend decomposition using LOESS.

    https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html

    :param srs: input time series
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param kwargs: kwargs for statsm.tsa.seasonal.STL
    """
    nan_mode = nan_mode or "drop"
    kwargs = kwargs or {}
    figsize = figsize or (20, 16)
    if isinstance(srs, pd.DataFrame) and srs.shape[1] > 1:
        raise ValueError("Input df should be 1 dim, not %s'" % srs.shape[1])
    srs = srs.squeeze()
    srs = hdatafr.apply_nan_mode(srs, mode=nan_mode)
    stl = statsm.tsa.seasonal.STL(srs, **kwargs).fit()
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(4, 1, y_scale=figsize[1] / 4)
    stl.observed.plot(ylabel="Observed", ax=axes[0])
    stl.trend.plot(ylabel="Trend", ax=axes[1])
    stl.seasonal.plot(ylabel="Season", ax=axes[2])
    stl.resid.plot(marker="o", linestyle="none", ylabel="Resid", ax=axes[3])
    axes[3].axhline(0, color="#000000", zorder=-3)


def plot_spectrum(
    signal: Union[pd.Series, pd.DataFrame],
    nan_mode: str = "conservative",
    title_prefix: Optional[str] = None,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> None:
    """
    Plot power spectral density and spectrogram of columns.

    PSD:
      - Estimate the power spectral density using Welch's method.
      - Related to autocorrelation via the Fourier transform (Wiener-Khinchin).
    Spectrogram:
      - From the scipy documentation of spectrogram:
        "Spectrograms can be used as a way of visualizing the change of a
         nonstationary signal's frequency content over time."

    :param axes: flat list of axes or `None`
    """
    if isinstance(signal, pd.Series):
        signal = signal.to_frame()
    if title_prefix is None:
        title_prefix = ""
    # Replacing inf with nan to ensure non-empty plots generated.
    signal = costatis.replace_infs_with_nans(signal)
    if axes is None:
        _, axes = cplpluti.get_multiple_plots(
            signal.shape[1] * 2, num_cols=2, y_scale=5
        )
    axis_pairs = zip(axes[::2], axes[1::2])
    for col, axis_pair in zip(signal.columns, axis_pairs):
        if nan_mode == "conservative":
            data = signal[col].fillna(0).dropna()
        else:
            raise ValueError(f"Unsupported nan_mode `{nan_mode}`")
        axes = cast(List, axes)
        ax1 = axis_pair[0]
        f_pxx, Pxx = sp.signal.welch(data)
        ax1.semilogy(f_pxx, Pxx)
        ax1.set_title(title_prefix + f"{col} power spectral density")
        # TODO(*): Maybe put labels on a shared axis.
        # ax1.set_xlabel("Frequency")
        # ax1.set_ylabel("Power")
        ax2 = axis_pair[1]
        f_sxx, t, Sxx = sp.signal.spectrogram(data)
        ax2.pcolormesh(t, f_sxx, Sxx)
        ax2.set_title(title_prefix + f"{col} spectrogram")
        # ax2.set_ylabel("Frequency band")
        # ax2.set_xlabel("Time window")


def plot_time_series_dict(
    dict_: Dict[str, pd.Series],
    num_plots: Optional[int] = None,
    num_cols: Optional[int] = None,
    y_scale: Optional[float] = 4,
    sharex: bool = True,
    sharey: bool = False,
    exclude_empty: bool = True,
    axes: Optional[List[mpl.axes.Axes]] = None,
) -> None:
    """
    Plot series from a dict of series.

    :param dict_: dict of series
    :param num_plots: number of plots
    :param num_cols: number of columns to use in the subplot
    :param y_scale: the height of each plot. If `None`, the size of the whole
        figure equals the default `figsize`
    :param sharex: unify x-axis if True
    :param sharey: unify y-axis if True
    :param exclude_empty: whether to exclude plots of empty series
    """
    if exclude_empty:
        non_empty_dict_ = {
            key: val for key, val in dict_.items() if not val.empty
        }
        if len(non_empty_dict_) < len(dict_):
            excluded_series = set(dict_).difference(non_empty_dict_)
            _LOG.warning("Excluded empty series: %s", excluded_series)
        dict_ = non_empty_dict_
    num_plots = num_plots or len(dict_)
    if axes is None:
        # Create figure to accommodate plots.
        num_cols = num_cols or 2
        _, axes = cplpluti.get_multiple_plots(
            num_plots=num_plots,
            num_cols=num_cols,
            y_scale=y_scale,
            sharex=sharex,
            sharey=sharey,
        )
    else:
        hdbg.dassert_eq(len(axes), num_plots)
    # Select first `num_plots` series in the dict and plot them.
    keys_to_draw = list(dict_.keys())[:num_plots]
    for i, key in enumerate(keys_to_draw):
        srs = dict_[key]
        srs.to_frame().plot(title=key, ax=axes[i])


# #############################################################################
# Model evaluation
# #############################################################################


def plot_cumulative_returns(
    cumulative_rets: pd.Series,
    mode: str,
    unit: str = "ratio",
    benchmark_series: Optional[pd.Series] = None,
    title_suffix: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    plot_zero_line: bool = True,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot cumulative returns.

    :param cumulative_rets: log or pct cumulative returns
    :param mode: log or pct, used to choose plot title
    :param unit: "ratio", "%" or "bps", both input series are rescaled
        appropriately
    :param benchmark_series: additional series to plot
    :param title_suffix: suffix added to the title
    :param ax: axes
    :param plot_zero_line: whether to plot horizontal line at 0
    :param events: list of tuples with dates and labels to point out on the plot
    """
    title_suffix = title_suffix or ""
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    cumulative_rets = cumulative_rets * scale_coeff
    #
    if mode == "log":
        title = "Cumulative log returns"
    elif mode == "pct":
        title = "Cumulative returns"
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    label = str(cumulative_rets.name) or "returns"
    #
    ax = cumulative_rets.plot(
        ax=ax, title=f"{title}{title_suffix}", label=label, linewidth=3.0
    )
    if benchmark_series is not None:
        benchmark_series = benchmark_series.loc[
            cumulative_rets.index[0] : cumulative_rets.index[-1]
        ]
        benchmark_series = benchmark_series * scale_coeff
        bs_label = benchmark_series.name or "benchmark_series"
        benchmark_series.plot(ax=ax, label=bs_label, color="grey")
    if plot_zero_line:
        ax.axhline(0, linestyle="--", linewidth=0.8, color="black")
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.set_ylabel(unit)
    ax.legend()
    ax.autoscale()


def plot_rolling_annualized_volatility(
    srs: pd.Series,
    tau: float,
    min_periods: Optional[int] = None,
    min_depth: int = 1,
    max_depth: int = 1,
    p_moment: float = 2,
    unit: str = "ratio",
    trim_index: Optional[bool] = False,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot rolling annualized volatility.

    :param srs: input series
    :param tau: argument as for csigproc.compute_rolling_std
    :param min_periods: argument as for csigproc.compute_rolling_std
    :param min_depth: argument as for csigproc.compute_rolling_std
    :param max_depth: argument as for csigproc.compute_rolling_std
    :param p_moment: argument as for csigproc.compute_rolling_std
    :param unit: "ratio", "%" or "bps" scaling coefficient
        "Exchange:Kibot_symbol"
        "Exchange:Exchange_symbol"
    :param trim_index: start plot at original index if True
    :param ax: axes
    :param events: list of tuples with dates and labels to point out on the plot
    """
    min_periods = min_periods or tau
    srs = hdatafr.apply_nan_mode(srs, mode="fill_with_zero")
    # Calculate rolling volatility.
    rolling_volatility = csigproc.compute_rolling_std(
        srs, tau, min_periods, min_depth, max_depth, p_moment
    )
    # Annualize rolling volatility.
    ppy = hdatafr.infer_sampling_points_per_year(srs)
    annualized_rolling_volatility = np.sqrt(ppy) * rolling_volatility
    # Remove leading `NaNs`.
    first_valid_index = annualized_rolling_volatility.first_valid_index()
    annualized_rolling_volatility = annualized_rolling_volatility.loc[
        first_valid_index:
    ]
    # Rescale according to desired output units.
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    annualized_rolling_volatility *= scale_coeff
    # Calculate whole-period target volatility.
    annualized_volatility = costatis.compute_annualized_volatility(srs)
    annualized_volatility *= scale_coeff
    # Plot.
    ax = ax or plt.gca()
    ax.plot(
        annualized_rolling_volatility,
        label="annualized rolling volatility",
    )
    ax.axhline(
        annualized_volatility,
        linestyle="--",
        linewidth=2,
        color="green",
        label="average annualized volatility",
    )
    ax.axhline(0, linewidth=0.8, color="black")
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.set_title(f"Annualized rolling volatility ({unit})")
    # Start plot from original index if specified.
    if not trim_index:
        ax.set_xlim([min(srs.index), max(srs.index)])
    else:
        ax.set_xlim(
            annualized_rolling_volatility.index[0],
            annualized_rolling_volatility.index[-1],
        )
    ax.set_ylabel(unit)
    ax.set_xlabel("period")
    ax.legend()


def plot_holdings(
    holdings: pd.Series,
    unit: str = "ratio",
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot holdings, average holdings and average holdings by month.

    :param holdings: pnl series to plot
    :param unit: "ratio", "%" or "bps" scaling coefficient
    :param ax: axes in which to draw the plot
    :param events: list of tuples with dates and labels to point out on the plot
    """
    ax = ax or plt.gca()
    scale_coeff = cplpluti.choose_scaling_coefficient(unit)
    holdings = scale_coeff * holdings
    holdings.plot(linewidth=1, ax=ax, label="holdings")
    holdings.resample("M").mean().plot(
        linewidth=2.5, ax=ax, label="average holdings by month"
    )
    ax.axhline(
        holdings.mean(),
        linestyle="--",
        color="green",
        label="average holdings, overall",
    )
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.set_ylabel(unit)
    ax.legend()
    ax.set_title(f"Total holdings ({unit})")


def plot_allocation(
    position_df: pd.DataFrame,
    config: Dict[str, Any],
    figsize: Optional[Tuple[int, int]] = None,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> None:
    """
    Plot position allocations over time.

    :param position_df: dataframe with position time series
    :param config: information about time series
    :param figsize: size of plot
    :param ax: axes
    :param events: list of tuples with dates and labels to point out on the plot
    """
    ax = ax or plt.gca()
    figsize = figsize or (20, 5)
    fstr = "{key} [{tag}]"
    labels = [
        fstr.format(key=str(key), tag=config[key]["tag"]) for key in config.keys()
    ]
    position_df_plot = position_df.copy()
    position_df_plot.columns = labels
    position_df_plot.plot(ax=ax, figsize=figsize)
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.set_title(
        f"Portfolio allocation over time; {position_df.shape[1]} positions"
    )
    ax.set_xlabel("period")
    ax.legend()


def plot_rolling_beta(
    rets: pd.Series,
    benchmark_rets: pd.Series,
    window: int,
    nan_mode: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    events: Optional[List[Tuple[str, Optional[str]]]] = None,
    **kwargs: Any,
) -> None:
    """
    Regress returns against benchmark series and plot rolling beta.

    :param rets: returns
    :param benchmark_rets: benchmark returns
    :param window: length of the rolling window
    :param nan_mode: argument for hdatafr.apply_nan_mode()
    :param ax: axis
    :param events: list of tuples with dates and labels to point out on the plot
    :param kwargs: kwargs for statsmodels.regression.rolling.RollingOLS
    """
    hpandas.dassert_strictly_increasing_index(rets)
    hpandas.dassert_strictly_increasing_index(benchmark_rets)
    hdbg.dassert_eq(rets.index.freq, benchmark_rets.index.freq)
    # Assert that the 'rets' index is a subset of the 'benchmark_rets' index.
    hdbg.dassert(rets.index.isin(benchmark_rets.index).all())
    hdbg.dassert_lte(
        window,
        min(len(rets), len(benchmark_rets)),
        "`window` should not be larger than inputs' lengths.",
    )
    rets_name = rets.name
    benchmark_name = benchmark_rets.name
    hdbg.dassert_ne(
        rets_name, benchmark_name, "Inputs should have different names."
    )
    nan_mode = nan_mode or "drop"
    # Combine rets and benchmark_rets in one dataframe over the intersection
    #    of their indices.
    all_rets_df = pd.concat([rets, benchmark_rets], axis=1, join="inner")
    all_rets_df.columns = [rets_name, benchmark_name]
    # Extract common index in order to keep NaN periods on the X-axis.
    common_index = all_rets_df.index
    # Apply `.dropna()` after `hdatafr.apply_nan_mode` in oder to drop remaining
    #     rows with NaNs and calculate rolling beta without NaN gaps in input.
    clean_rets_df = all_rets_df.apply(
        hdatafr.apply_nan_mode, mode=nan_mode
    ).dropna()
    # Get copies of rets and benchmark_rets with unified indices and no NaNs.
    rets = clean_rets_df[rets_name]
    benchmark_rets = clean_rets_df[benchmark_name]
    # Calculate and plot rolling beta.
    ax = ax or plt.gca()
    benchmark_rets = sm.add_constant(benchmark_rets)
    # Calculate and plot rolling beta.
    model_rolling = srroll.RollingOLS(
        rets, benchmark_rets, window=window, **kwargs
    )
    res_rolling = model_rolling.fit()
    beta_rolling = res_rolling.params[
        benchmark_name
    ]  # pylint: disable=unsubscriptable-object
    # Return NaN periods to the rolling beta series for the plot.
    beta_rolling = beta_rolling.reindex(common_index)
    beta_rolling.plot(
        ax=ax,
        title=f"Beta with respect to {benchmark_name}",
        label="Rolling beta",
    )
    # Calculate and plot beta for the whole period.
    model_whole_period = sm.OLS(rets, benchmark_rets)
    res_whole_period = model_whole_period.fit()
    beta_whole_period = res_whole_period.params[benchmark_name]
    ax.axhline(beta_whole_period, ls="--", c="k", label="Whole-period beta")
    ax.set_xlabel("period")
    ax.set_ylabel("beta")
    cplpluti.maybe_add_events(ax=ax, events=events)
    ax.legend()
