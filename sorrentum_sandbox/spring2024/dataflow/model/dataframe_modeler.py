"""
Import as:

import dataflow.model.dataframe_modeler as dtfmodamod
"""

from __future__ import annotations

import collections
import datetime
import json
import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import core.config as cconfig
import core.finance as cofinanc
import core.plotting as coplotti
import core.signal_processing as csigproc
import core.timeseries_study as ctimstud
import dataflow.core as cdataf
import dataflow.model.stats_computer as dtfmostcom
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class DataFrameModeler:
    """
    Wrap common dataframe modeling and exploratory analysis functionality.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        oos_start: Optional[Union[str, pd.Timestamp, datetime.datetime]] = None,
        info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize by supplying a dataframe of time series.

        :param df: time series dataframe
        :param oos_start: Optional end of in-sample/start of out-of-sample.
            For methods supporting "fit"/"predict", "fit" applies to
            in-sample only, and "predict" requires `oos_start`.
        """
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert(pd.DataFrame)
        self._df = df
        if oos_start is not None:
            oos_start = pd.Timestamp(oos_start)
        self.oos_start = oos_start or None
        self.info = info or None
        self.stats_computer = dtfmostcom.StatsComputer()

    @property
    def ins_df(self) -> pd.DataFrame:
        return self._df[: self.oos_start].copy()

    @property
    def oos_df(self) -> pd.DataFrame:
        hdbg.dassert(self.oos_start, msg="`oos_start` must be set")
        return self._df[self.oos_start :].copy()

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()

    def dump_json(self) -> str:
        """
        Dump `DataFrameModeler` instance to json.

        Implementation details:
          - `self._df` index is converted to `str`. This way it can be easily
            restored
          - if `self.oos_start` is `None`, it is saved as is. Otherwise, it is
            converted to `str`
          - if `self.info` is `None`, it is saved as is. Otherwise, it is saved
            as `cconfig.Config.to_python()`

        :return: json with "df", "oos_start" and "info" fields
        """
        # Convert dataframe to json while preserving its index.
        df = self._df.copy()
        df.index = df.index.astype(str)
        df = df.to_json()
        # Convert OOS start to string.
        oos_start = self.oos_start
        if oos_start is not None:
            oos_start = str(oos_start)
        # Convert info to string.
        if self.info is not None:
            try:
                info = cconfig.Config.from_dict(self.info)
                info = info.to_python()
            except ValueError:
                _LOG.warning("Failed to serialize `info`.")
                info = None
        else:
            info = None
        #
        json_config = {"df": df, "oos_start": oos_start, "info": info}
        json_str = json.dumps(json_config, indent=4)
        return json_str

    @classmethod
    def load_json(cls, json_str: str) -> DataFrameModeler:
        """
        Load `DataFrameModeler` instance from json.

        :param json_str: the output of `DataFrameModeler.dump_json`
        :return: `DataFrameModeler` instance
        """
        json_str = json.loads(json_str)
        # Load dataframe.
        df = json.loads(json_str["df"])
        df = pd.DataFrame.from_dict(df)
        df.index = pd.to_datetime(df.index)
        if df.shape[0] > 2:
            df.index.freq = pd.infer_freq(df.index)
        # Load OOS start.
        oos_start = json_str["oos_start"]
        if oos_start is not None:
            oos_start = pd.Timestamp(oos_start)
        # Load info.
        info = json_str["info"]
        if info is not None:
            info = cconfig.Config.from_python(info).to_dict()
        #
        modeler = cls(df=df, oos_start=oos_start, info=info)
        return modeler

    def apply_node(
        self,
        node_class: cdataf.FitPredictNode,
        node_kwargs: Dict[str, Any],
        method: cdataf.Method = "fit",
    ) -> DataFrameModeler:
        """
        Apply dataflow node to dataframe.

        :param node_class: a dataflow `FitPredictNode`
        :param node_kwargs: kwargs for node initialization
        :param method: "fit" or "predict"
        :return: a `DataFrameModeler` object whose dataframe is given by the
            output of the `FitPredictNode`
        """
        node = node_class(
            nid=node_class.__name__,
            **node_kwargs,
        )
        return self._run_node(node, method)

    def apply_column_transformer(
        self,
        transformer_func: Callable[..., pd.DataFrame],
        transformer_kwargs: Optional[Dict[str, Any]] = None,
        # TODO(Paul): May need to assume `List` instead.
        cols: Optional[Iterable[str]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
        method: cdataf.Method = "fit",
    ) -> DataFrameModeler:
        """
        Apply a function to a select of columns.
        """
        node_class = cdataf.ColumnTransformer
        node_kwargs = {
            "transformer_func": transformer_func,
            "transformer_kwargs": transformer_kwargs,
            "cols": cols,
            "col_rename_func": col_rename_func,
            "col_mode": col_mode,
            "nan_mode": nan_mode,
        }
        return self.apply_node(node_class, node_kwargs, method)

    def apply_residualizer(
        self,
        model_func: Callable[..., Any],
        x_vars: Union[List[str], Callable[[], List[str]]],
        model_kwargs: Optional[Any] = None,
        nan_mode: Optional[str] = "drop",
        method: cdataf.Method = "fit",
    ) -> DataFrameModeler:
        """
        Apply an unsupervised model and residualize.
        """
        node_class = cdataf.Residualizer
        node_kwargs = {
            "model_func": model_func,
            "x_vars": x_vars,
            "model_kwargs": model_kwargs,
            "nan_mode": nan_mode,
        }
        return self.apply_node(node_class, node_kwargs, method)

    # #########################################################################
    # Convenience methods
    # #########################################################################

    def compute_ret_0(
        self,
        rets_mode: str = "log_rets",
        cols: Optional[Iterable[str]] = None,
        col_rename_func: Optional[Callable[[Any], Any]] = None,
        col_mode: Optional[str] = None,
        nan_mode: Optional[str] = None,
        method: cdataf.Method = "fit",
    ) -> DataFrameModeler:
        """
        Calculate returns (realized at timestamp).
        """
        col_rename_func = col_rename_func or (lambda x: str(x) + "_ret_0")
        col_mode = col_mode or "replace_all"
        model = cdataf.ColumnTransformer(
            nid="compute_ret_0",
            transformer_func=cofinanc.compute_ret_0,
            transformer_kwargs={"mode": rets_mode},
            cols=cols,
            col_rename_func=col_rename_func,
            col_mode=col_mode,
            nan_mode=nan_mode,
        )
        return self._run_node(model, method)

    def set_non_ath_to_nan(
        self,
        start_time: Optional[datetime.time] = None,
        end_time: Optional[datetime.time] = None,
        method: cdataf.Method = "fit",
    ) -> DataFrameModeler:
        """
        Replace values at non active trading hours with NaNs.
        """
        model = cdataf.ColumnTransformer(
            nid="set_non_ath_to_nan",
            transformer_func=cofinanc.set_non_ath_to_nan,
            col_mode="replace_all",
            transformer_kwargs={"start_time": start_time, "end_time": end_time},
        )
        return self._run_node(model, method)

    def set_weekends_to_nan(
        self, method: cdataf.Method = "fit"
    ) -> DataFrameModeler:
        """
        Replace values over weekends with NaNs.
        """
        model = cdataf.ColumnTransformer(
            nid="set_weekends_to_nan",
            transformer_func=cofinanc.set_weekends_to_nan,
            col_mode="replace_all",
        )
        return self._run_node(model, method)

    def merge(
        self,
        dfm: DataFrameModeler,
        merge_kwargs: Optional[Dict[str, Any]] = None,
    ) -> DataFrameModeler:
        """
        Merge `DataFrameModeler` with another `DataFrameModeler` object.

        Returns a new `DataFrameModeler` with merged underlying
        dataframes. If `oos_start` dates are different, set it to the
        first one and raise a warning.
        """
        hdbg.dassert_isinstance(dfm, DataFrameModeler)
        merge_kwargs = merge_kwargs or {}
        df_merged = self._df.merge(
            dfm.df,
            left_index=True,
            right_index=True,
            **merge_kwargs,
        )
        if self.oos_start != dfm.oos_start:
            _LOG.warning(
                "`oos_start` dates are different.\n"
                + "`oos_start` for merged `DataFrameModelers` was set to %s",
                self.oos_start,
            )
        info = collections.OrderedDict(
            {"info": cdataf.get_df_info_as_string(df_merged)}
        )
        return DataFrameModeler(df_merged, oos_start=self.oos_start, info=info)

    # #########################################################################
    # Dataframe plotting
    # #########################################################################

    def compute_time_series_stats(
        self,
        cols: Optional[List[Any]] = None,
        progress_bar: bool = True,
        mode: str = "ins",
    ) -> pd.DataFrame:
        """
        Calculate stats for selected columns.
        """
        df = self._get_df(cols=cols, mode=mode)
        # Calculate stats.
        stats_dict = {}
        for col in tqdm(
            df.columns, disable=not progress_bar, desc="Calculating stats"
        ):
            stats_val = self.stats_computer.compute_time_series_stats(df[col])
            stats_dict[col] = stats_val
        stats_df = pd.concat(stats_dict, axis=1)
        return stats_df

    def plot_time_series(
        self,
        cols: Optional[List[Any]] = None,
        num_plots: Optional[int] = None,
        num_cols: int = 2,
        y_scale: Optional[float] = 4,
        sharex: bool = True,
        sharey: bool = False,
        separator: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        mode: str = "ins",
    ) -> None:
        """
        :param y_scale: the height of each plot. If `None`, the size of the whole
            figure equals the default `figsize`
        :param separator: if not `None`, split the column names by it and
            display only the last part as the plot title
        """
        df = self._get_df(cols=cols, mode=mode)
        num_plots = num_plots or df.shape[1]
        num_plots = min(num_plots, df.shape[1])
        if num_plots == 1:
            num_cols = 1
        if axes is None:
            # Create figure to accommodate plots.
            _, axes = coplotti.get_multiple_plots(
                num_plots=num_plots,
                num_cols=num_cols,
                y_scale=y_scale,
                sharex=sharex,
                sharey=sharey,
            )
        # Select first `num_plots` series in the dict and plot them.
        cols_to_draw = df.columns[:num_plots]
        for i, col_name in enumerate(cols_to_draw):
            srs = df[col_name]
            if separator is not None:
                title = col_name.rsplit(separator, 1)[-1]
            else:
                title = col_name
            srs.plot(title=title, ax=axes[i])

    def plot_projection(
        self,
        cols: Optional[List[Any]] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_projection_kwargs: Optional[Dict[str, Any]] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        plot_projection_kwargs = plot_projection_kwargs or {}
        coplotti.plot_projection(df, ax=ax, **plot_projection_kwargs)

    def plot_cumulative_returns(
        self,
        cols: Optional[List[Any]] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_cumulative_returns_kwargs: Optional[Dict[str, Any]] = None,
        mode_rets: str = "log",
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        plot_cumulative_returns_kwargs = plot_cumulative_returns_kwargs or {}
        cum_rets = df.cumsum()
        coplotti.plot_cumulative_returns(
            cum_rets,
            mode=mode_rets,
            ax=ax,
            **plot_cumulative_returns_kwargs,
        )

    def plot_correlation_with_lag(
        self,
        lag: Union[int, List[int]],
        cols: Optional[List[Any]] = None,
        ax: Optional[mpl.axes.Axes] = None,
        mode: str = "ins",
    ) -> pd.DataFrame:
        """
        Calculate correlation of `cols` with lags of `cols`.
        """
        df = self._get_df(cols=cols, mode=mode)
        # Calculate correlation.
        corr_df = csigproc.correlate_with_lag(df, lag=lag)
        coplotti.plot_heatmap(corr_df, ax=ax)
        return corr_df

    def plot_correlation_with_lagged_cumsum(
        self,
        lag: int,
        y_vars: List[str],
        cols: Optional[List[Any]] = None,
        nan_mode: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
        mode: str = "ins",
    ) -> pd.DataFrame:
        """
        Calculate correlation of `cols` with lagged cumulative sum of `y_vars`.
        """
        df = self._get_df(cols=cols, mode=mode)
        # Calculate correlation.
        corr_df = csigproc.correlate_with_lagged_cumsum(
            df, lag=lag, y_vars=y_vars, nan_mode=nan_mode
        )
        coplotti.plot_heatmap(corr_df, ax=ax)
        return corr_df

    def plot_autocorrelation(
        self,
        cols: Optional[List[Any]] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_auto_correlation_kwargs: Optional[dict] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        plot_auto_correlation_kwargs = plot_auto_correlation_kwargs or {}
        coplotti.plot_autocorrelation(
            df, axes=axes, **plot_auto_correlation_kwargs
        )

    def plot_sequence_and_density(
        self,
        cols: Optional[List[Any]] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_cols_kwargs: Optional[dict] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        plot_cols_kwargs = plot_cols_kwargs or {}
        coplotti.plot_cols(df, axes=axes, **plot_cols_kwargs)

    def plot_spectrum(
        self,
        cols: Optional[List[Any]] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_spectrum_kwargs: Optional[dict] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        plot_spectrum_kwargs = plot_spectrum_kwargs or {}
        coplotti.plot_spectrum(df, axes=axes, **plot_spectrum_kwargs)

    def plot_correlation_matrix(
        self,
        cols: Optional[List[Any]] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_correlation_matrix_kwargs: Optional[dict] = None,
        mode: str = "ins",
    ) -> pd.DataFrame:
        df = self._get_df(cols=cols, mode=mode)
        plot_correlation_matrix_kwargs = plot_correlation_matrix_kwargs or {}
        return coplotti.plot_correlation_matrix(
            df, ax=ax, **plot_correlation_matrix_kwargs
        )

    def plot_dendrogram(
        self,
        cols: Optional[List[Any]] = None,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_dendrogram_kwargs: Optional[Dict[str, Any]] = None,
        mode: str = "ins",
    ) -> None:
        plot_dendrogram_kwargs = plot_dendrogram_kwargs or {}
        #
        df = self._get_df(cols=cols, mode=mode)
        coplotti.plot_dendrogram(
            df, figsize=figsize, ax=ax, **plot_dendrogram_kwargs
        )

    def plot_pca_components(
        self,
        cols: Optional[List[Any]] = None,
        num_components: Optional[int] = None,
        num_cols: int = 2,
        y_scale: Optional[float] = 4,
        axes: Optional[List[mpl.axes.Axes]] = None,
        mode: str = "ins",
    ) -> None:
        """
        :param y_scale: the height of each plot. If `None`, the size of the whole
            figure equals the default `figsize`
        """
        df = self._get_df(cols=cols, mode=mode)
        pca = coplotti.PCA(mode="standard")
        pca.fit(df.replace([np.inf, -np.inf], np.nan).fillna(0))
        pca.plot_components(
            num_components, num_cols=num_cols, y_scale=y_scale, axes=axes
        )

    def plot_explained_variance(
        self,
        cols: Optional[List[Any]] = None,
        num_components: Optional[int] = None,
        ax: Optional[mpl.axes.Axes] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=cols, mode=mode)
        pca = coplotti.PCA(mode="standard", n_components=num_components)
        pca.fit(df.replace([np.inf, -np.inf], np.nan).fillna(0))
        pca.plot_explained_variance(ax=ax)

    def plot_qq(
        self,
        col: Any,
        dist: Optional[str] = None,
        nan_mode: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
        mode: str = "ins",
    ) -> None:
        srs = self._get_df(cols=[col], mode=mode).squeeze()
        coplotti.plot_qq(srs, ax=ax, dist=dist, nan_mode=nan_mode)

    def plot_rolling_correlation(
        self,
        col1: Any,
        col2: Any,
        tau: float,
        ax: Optional[mpl.axes.Axes] = None,
        plot_rolling_correlation_kwargs: Optional[dict] = None,
        mode: str = "ins",
    ) -> None:
        df = self._get_df(cols=[col1, col2], mode=mode)
        plot_rolling_correlation_kwargs = plot_rolling_correlation_kwargs or {}
        coplotti.plot_rolling_correlation(
            df[col1],
            df[col2],
            tau=tau,
            ax=ax,
            **plot_rolling_correlation_kwargs,
        )

    def plot_time_series_study(
        self,
        cols: Optional[List[Any]] = None,
        num_plots: Optional[int] = None,
        mode: str = "ins",
        last_n_years: Optional[int] = None,
        axes: Optional[
            List[Union[mpl.axes.Axes, List[mpl.axes.Axes], None]]
        ] = None,
    ) -> List[List[Optional[mpl.figure.Figure]]]:
        """
        :param num_plots: number of cols to plot the study for
        :param axes: flat list of `ax`/`axes` parameters for each column for
            each `ctimstud.TimeSeriesDailyStudy`method. If the method is skipped,
            should be `None`
        """
        df = self._get_df(cols=cols, mode=mode)
        num_plots = num_plots or df.shape[1]
        cols_to_draw = df.columns[:num_plots]
        if axes is None:
            axes_for_cols = [None] * num_plots
        else:
            axes_for_cols = np.array(axes).reshape(num_plots, -1)
        figs = []
        for col_name, axes_for_col in zip(cols_to_draw, axes_for_cols):
            tsds = ctimstud.TimeSeriesDailyStudy(df[col_name])
            figs.append(
                tsds.execute(last_n_years=last_n_years, axes=axes_for_col)
            )
            if axes is None:
                plt.show()
        return figs

    def plot_seasonal_decomposition(
        self,
        cols: Optional[List[Any]] = None,
        nan_mode: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_seasonal_decomposition_kwargs: Optional[Dict[str, Any]] = None,
        mode: str = "ins",
    ) -> None:
        """
        :param axes: flat list of `axes` parameters for each column
        """
        nan_mode = nan_mode or "drop"
        plot_seasonal_decomposition_kwargs = (
            plot_seasonal_decomposition_kwargs or {}
        )
        df = self._get_df(cols=cols, mode=mode)
        if axes is None:
            axes_for_cols = [None] * df.shape[1]
        else:
            axes_for_cols = np.array(axes).reshape(df.shape[1], -1)
        for i, axes_for_col in zip(df.columns.values, axes_for_cols):
            coplotti.plot_seasonal_decomposition(
                df[i],
                nan_mode=nan_mode,
                axes=axes_for_col,
                **plot_seasonal_decomposition_kwargs,
            )

    def plot_histograms_and_lagged_scatterplot(
        self,
        lag: int,
        mode: str = "ins",
        nan_mode: Optional[str] = None,
        cols: Optional[List[Any]] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        hist_kwargs: Optional[Any] = None,
        scatter_kwargs: Optional[Any] = None,
    ) -> None:
        """
        :param axes: flat list of `axes` parameters for each column
        """
        df = self._get_df(cols=cols, mode=mode)
        if mode == "all_available":
            oos_start = self.oos_start
        else:
            oos_start = None
        if axes is None:
            axes_for_cols = [None] * df.shape[1]
        else:
            axes_for_cols = np.array(axes).reshape(df.shape[1], -1)
        for col_name, axes_for_col in zip(df.columns, axes_for_cols):
            coplotti.plot_histograms_and_lagged_scatterplot(
                df[col_name],
                lag=lag,
                oos_start=oos_start,
                nan_mode=nan_mode,
                title=col_name,
                axes=axes_for_col,
                hist_kwargs=hist_kwargs,
                scatter_kwargs=scatter_kwargs,
                figsize=(20, 10),
            )
            if axes is None:
                plt.show()

    # #########################################################################
    # Private helpers
    # #########################################################################

    def _get_df(self, cols: Optional[List[Any]], mode: str) -> pd.DataFrame:
        cols = cols or self._df.columns
        hdbg.dassert_is_subset(cols, self._df.columns)
        if mode == "ins":
            return self.ins_df[cols]
        if mode == "oos":
            return self.oos_df[cols]
        if mode == "all_available":
            return self.df[cols]
        raise ValueError(f"Unrecognized mode `{mode}`")

    def _run_node(
        self, model: cdataf.FitPredictNode, method: cdataf.Method
    ) -> DataFrameModeler:
        info = collections.OrderedDict()
        if method == "fit":
            df_out = model.fit(self._df[: self.oos_start])["df_out"]
            info["fit"] = model.get_info("fit")
            oos_start = None
        elif method == "predict":
            hdbg.dassert(
                self.oos_start, msg="Must set `oos_start` to run `predict()`"
            )
            model.fit(self._df[: self.oos_start])
            info["fit"] = model.get_info("fit")
            df_out = model.predict(self._df)["df_out"]
            info["predict"] = model.get_info("predict")
            oos_start = self.oos_start
        else:
            raise ValueError(f"Unrecognized method `{method}`.")
        dfm = DataFrameModeler(df_out, oos_start, info)
        return dfm
