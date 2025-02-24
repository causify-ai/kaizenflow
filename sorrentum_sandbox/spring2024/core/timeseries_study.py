"""
Import as:

import core.timeseries_study as ctimstud
"""

import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from tqdm.auto import tqdm

import core.plotting as coplotti
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): Obsolete or clean up / reuse.


class _TimeSeriesAnalyzer:
    """
    Perform basic study of time series, such as:

    - analysis at different time frequencies by resampling
    - plot time series for column
        - by year
        - by month
        - by day of week
        - by hour
    """

    def __init__(
        self,
        time_series: pd.Series,
        freq_name: str,
        data_name: Optional[str] = None,
        sharey: Optional[bool] = False,
        disabled_methods: Optional[Iterable[str]] = None,
    ):
        """
        :param time_series: pd.Series for which the study needs to be
            conducted
        :param freq_name: the name of the data frequency to add to plot titles
            e.g., 'daily'
        :param data_name: the name of the data to add to plot titles, e.g.,
            `symbol`
        :param sharey: a parameter passed into plt.subplots in `plot_by_year`
            method
        :param disabled_methods: methods that need to be skipped
        """
        hdbg.dassert_isinstance(time_series, pd.Series)
        hdbg.dassert_isinstance(time_series.index, pd.DatetimeIndex)
        hpandas.dassert_strictly_increasing_index(time_series.index)
        self._time_series = time_series
        self._ts_name = time_series.name
        self._data_name = data_name
        self._freq_name = freq_name
        self._sharey = sharey
        self._disabled_methods = disabled_methods or []

    def plot_time_series(
        self,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> Optional[mpl.figure.Figure]:
        """
        Plot timeseries on its original time scale.
        """
        func_name = hintros.get_function_name()
        _LOG.debug(func_name)
        if func_name in self._disabled_methods:
            _LOG.debug("Skipping '%s' as per user request", func_name)
            return None
        #
        ax = self._time_series.plot(ax=ax)
        ax.set_title(
            f"{self._freq_name.capitalize()} {self._ts_name}"
            f"{self._title_suffix}"
        )
        xticklabels = self._time_series.resample("YS").sum().index
        ax.set_xticks(xticklabels)
        ax.set_xticklabels(
            xticklabels,
            ha="right",
            rotation=30,
            rotation_mode="anchor",
        )
        return ax.get_figure()

    def plot_by_year(
        self,
        last_n_years: Optional[int] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> Optional[mpl.figure.Figure]:
        """
        Resample yearly and then plot each year on a different coplotti.
        """
        func_name = hintros.get_function_name()
        if self._need_to_skip(func_name):
            return None
        # Split by year.
        time_series = self._time_series.dropna()
        yearly_resample = time_series.resample("y")
        # Include only the years with enough data to coplotti.
        yearly_resample_count = yearly_resample.count()
        years_to_plot_data_mask = yearly_resample_count > 1
        # Limit to top n years, if set.
        if last_n_years:
            years_to_plot_data_mask[: -last_n_years - 1] = False
        num_plots = years_to_plot_data_mask.sum()
        if num_plots == 0:
            _LOG.warning("Not enough data to plot year-by-year.")
            return None
        if axes is None:
            # Create as many subplots as years.
            _, axes = coplotti.get_multiple_plots(
                num_plots,
                num_cols=1,
                y_scale=5,
                sharey=self._sharey,
            )
            plt.suptitle(
                f"{self._freq_name.capitalize()} {self._ts_name} by year"
                f"{self._title_suffix}",
                # Set suptitle at the top of the plots.
                y=1.005,
            )
        # Plot each year in a subplot.
        if (~years_to_plot_data_mask).sum() > 0:
            years_with_not_enough_data = years_to_plot_data_mask[
                ~years_to_plot_data_mask
            ].index.year.tolist()
            _LOG.info(
                "Skipping years %s: not enough data to plot",
                years_with_not_enough_data,
            )
        years_with_enough_data = yearly_resample_count[
            years_to_plot_data_mask
        ].index
        for ax, group_by_timestamp in zip(axes, years_with_enough_data):
            ts = yearly_resample.get_group(group_by_timestamp)
            ts.plot(ax=ax, title=group_by_timestamp.year)
        return axes[-1].get_figure()

    # TODO(gp): Think if it makes sense to generalize this by passing a lambda
    #  that define the timescale, e.g.,
    #   groupby_func = lambda ts: ts.index.day
    #  to sample on many frequencies (e.g., monthly, hourly, minutely, ...)
    #  The goal is to look for seasonality at many frequencies.
    # TODO(gp): It would be nice to plot the timeseries broken down by
    #  different timescales instead of doing the mean in each step
    #  (see https://en.wikipedia.org/wiki/Seasonality#Detecting_seasonality)
    def boxplot_day_of_month(
        self, ax: Optional[mpl.axes.Axes] = None
    ) -> Optional[mpl.figure.Figure]:
        """
        Plot the mean value of the timeseries for each day.
        """
        func_name = hintros.get_function_name()
        if self._need_to_skip(func_name):
            return None
        #
        self._boxplot(self._time_series, self._time_series.index.day, ax=ax)
        ax = ax or plt.gca()
        ax.set_xlabel("day of month")
        ax.set_title(
            f"{self._freq_name} {self._ts_name} on different days of "
            f"month{self._title_suffix}"
        )
        return ax.get_figure()

    def boxplot_day_of_week(
        self, ax: Optional[mpl.axes.Axes] = None
    ) -> Optional[mpl.figure.Figure]:
        """
        Plot the mean value of the timeseries for year.
        """
        func_name = hintros.get_function_name()
        if self._need_to_skip(func_name):
            return None
        #
        self._boxplot(self._time_series, self._time_series.index.dayofweek, ax=ax)
        ax = ax or plt.gca()
        ax.set_xlabel("day of week")
        ax.set_title(
            f"{self._freq_name} {self._ts_name} on different days of "
            f"week{self._title_suffix}"
        )
        return ax.get_figure()

    def execute(
        self,
        last_n_years: Optional[int] = None,
        axes: Optional[
            List[Union[mpl.axes.Axes, List[mpl.axes.Axes], None]]
        ] = None,
    ) -> List[Optional[mpl.figure.Figure]]:
        """
        :param axes: list of `ax`/`axes` parameters for each method. If the
            method is skipped, should be `None`
        """
        axes = axes or [None] * 4
        figs = []
        figs.append(self.plot_time_series(ax=axes[0]))
        figs.append(self.plot_by_year(last_n_years=last_n_years, axes=axes[1]))
        figs.append(self.boxplot_day_of_month(ax=axes[2]))
        figs.append(self.boxplot_day_of_week(ax=axes[3]))
        return figs

    @staticmethod
    def _boxplot(
        ts: pd.Series, groupby: str, ax: Optional[mpl.axes.Axes] = None
    ) -> None:
        ts_df = pd.DataFrame(ts)
        ts_df["groupby"] = groupby
        ts_df.boxplot(by="groupby", column=ts.name, ax=ax)
        plt.suptitle("")

    def _need_to_skip(self, func_name: str) -> bool:
        _LOG.debug(func_name)
        if func_name in self._disabled_methods:
            _LOG.debug("Skipping '%s' as per user request", func_name)
            return True
        return False

    @property
    def _title_suffix(self) -> str:
        if self._data_name is not None:
            ret = f" for {self._data_name}"
        else:
            ret = ""
        return ret


class TimeSeriesDailyStudy(_TimeSeriesAnalyzer):
    def __init__(
        self,
        time_series: pd.Series,
        data_name: Optional[str] = None,
        sharey: Optional[bool] = False,
        disabled_methods: Optional[Iterable[str]] = None,
    ):
        freq_name = "daily"
        super().__init__(
            time_series, freq_name, data_name, sharey, disabled_methods
        )


class TimeSeriesMinutelyStudy(_TimeSeriesAnalyzer):
    def boxplot_minutely_hour(
        self, ax: Optional[mpl.axes.Axes] = None
    ) -> Optional[mpl.figure.Figure]:
        func_name = hintros.get_function_name()
        if self._need_to_skip(func_name):
            return None
        #
        self._boxplot(self._time_series, self._time_series.index.hour, ax=ax)
        ax = ax or plt.gca()
        ax.set_title(
            f"{self._ts_name} during different hours {self._title_suffix}"
        )
        ax.set_xlabel("hour")
        return ax.get_figure()

    def execute(
        self,
        last_n_years: Optional[int] = None,
        axes: Optional[
            List[Union[mpl.axes.Axes, List[mpl.axes.Axes], None]]
        ] = None,
    ) -> List[Optional[mpl.figure.Figure]]:
        axes = axes or [None] * 5
        figs = super().execute(last_n_years=last_n_years, axes=axes[:-1])
        figs.append(self.boxplot_minutely_hour(ax=axes[-1]))
        return figs


# Functions for processing dict of time series to generate a df with statistics
# of these series.


def map_dict_to_dataframe(
    dict_: Dict[Any, pd.Series],
    functions: Dict[str, Callable],
    add_prefix: bool = True,
    progress_bar: bool = True,
) -> pd.DataFrame:
    """
    Apply and combine results of specified functions on a dict of series.

    :param dict_: dict of series to apply functions to.
    :param functions: dict with functions prefixes in keys and functions
        returns in values. Each function should receive a series as input
        and return a series or 1-column dataframe.
    :param add_prefix: bool value. If True, add specified prefixes to
        the functions outcomes and do not add if False.
    :param progress_bar: bool value. If True, show progress bar of applying
        the function to the series in the input and do not show if False.
    :return: dataframe with dict of series keys as column names and
         prefix + functions metrics' names as index.
    """
    all_func_outs = []
    dict_items = dict_.items()
    if progress_bar:
        dict_items = tqdm(dict_.items(), desc="map_dict_to_df")
    for key, series in dict_items:
        # Apply all functions in `functions` to `series`.
        key_func_outs = []
        for prefix, func in functions.items():
            if not add_prefix:
                prefix = ""
            func_out = func(series, prefix=prefix)
            if isinstance(func_out, pd.DataFrame):
                func_out = func_out.squeeze("columns")
            hdbg.dassert_isinstance(func_out, pd.Series)
            key_func_outs.append(func_out)
        # Create a single series from individual function series.
        key_func_out_srs = pd.concat(key_func_outs)
        key_func_out_srs.name = key
        all_func_outs.append(key_func_out_srs)
    # Concatenate each output series.
    df = pd.concat(all_func_outs, axis=1)
    return df
