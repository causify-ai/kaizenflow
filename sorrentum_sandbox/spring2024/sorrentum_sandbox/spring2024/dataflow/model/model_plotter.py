"""
Import as:

import dataflow.model.model_plotter as dtfmomoplo
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import core.finance as cofinanc
import core.plotting as coplotti
import core.statistics as costatis
import dataflow.model.model_evaluator as dtfmomoeva
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# TODO(gp): Sometimes it is useful to have a more compact DataFrame view of the
# results, besides plotting, so each function can return DataFrame. We can use
# this output in the unit tests.


class ModelPlotter:
    """
    Wrap a `ModelEvaluator` with plotting functionality.

    The meaning of parameters is the same as in `ModelEvaluator`, unless
    stated otherwise.
    """

    def __init__(
        self,
        model_evaluator: dtfmomoeva.ModelEvaluator,
    ) -> None:
        """
        Initialize by supplying an initialized `ModelEvaluator`.

        :param model_evaluator: initialized `ModelEvaluator`
        """
        hdbg.dassert_isinstance(model_evaluator, dtfmomoeva.ModelEvaluator)
        self.model_evaluator = model_evaluator

    def plot_rets_signal_analysis(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        target_volatility: Optional[float] = None,
        resample_rule: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> None:
        """
        Plot a panel of signal analyses for (log) returns.

        Plots include:
        - Q-Q plot
        - histogram
        - time evolution
        - cumulative sum
        - ACF and PACF
        - spectral density and spectrogram

        :param keys: use all available if `None`
        :param weights: average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param target_volatility: Rescale portfolio to achieve
            `target_volatility` on in-sample region
        :param resample_rule: resampling frequency to apply before plotting
        :param axes: a flat list of axes to plot on
        """
        # Compute the returns.
        rets, _, _ = self.model_evaluator.aggregate_models(
            keys=keys,
            weights=weights,
            mode=mode,
            target_volatility=target_volatility,
        )
        # Resample, if needed.
        if resample_rule is not None:
            rets = rets.resample(rule=resample_rule).sum(min_count=1)
        # Plot.
        num_rows = 6
        if axes is None:
            fig = plt.figure(constrained_layout=True, figsize=(20, 5 * num_rows))
            gs = mpl.gridspec.GridSpec(num_rows, 2, figure=fig)
            # Generate a flat list of axis.
            axes = [
                fig.add_subplot(gs[0, :]),
                #
                fig.add_subplot(gs[1, :]),
                fig.add_subplot(gs[2, :]),
                #
                fig.add_subplot(gs[3, :]),
                #
                fig.add_subplot(gs[4, 0]),
                fig.add_subplot(gs[4, -1]),
                #
                fig.add_subplot(gs[5, 0]),
                fig.add_subplot(gs[5, -1]),
            ]
        # qq-plot against normal.
        coplotti.plot_qq(rets, ax=axes[0])
        # Plot line and density coplotti.
        coplotti.plot_cols(rets, axes=axes[1:3])
        # Plot pnl.
        coplotti.plot_pnl({"rets pnl": rets}, ax=axes[3])
        # Plot ACF and PACF.
        coplotti.plot_autocorrelation(
            rets,
            axes=axes[4:6],
            fft=True,
        )
        # Plot power spectral density and spectrogram.
        coplotti.plot_spectrum(rets, axes=axes[6:])

    def plot_performance(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        target_volatility: Optional[float] = None,
        resample_rule: Optional[str] = None,
        benchmark: Optional[pd.Series] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_cumulative_returns_kwargs: Optional[dict] = None,
        plot_rolling_beta_kwargs: Optional[dict] = None,
        plot_rolling_annualized_sharpe_ratio_kwargs: Optional[dict] = None,
        plot_drawdown_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Plot model/strategy performance.

        Plots include:
        - Cumulative returns
        - Rolling Sharpe Ratio
        - Drawdown

        If a benchmark is provided, then also display:
        - Cumulative returns against benchmark
        - Rolling beta against benchmark

        :param keys: use all available if `None`
        :param weights: average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param target_volatility: rescale portfolio to achieve `target_volatility`
            on in-sample region
        :param resample_rule: resampling frequency to apply before plotting
        :param benchmark: benchmark returns to compare against
        :param axes: a flat list of axes to plot on
        """
        # Obtain (log) returns.
        rets, _, _ = self.model_evaluator.aggregate_models(
            keys=keys,
            weights=weights,
            mode=mode,
            target_volatility=target_volatility,
        )
        if resample_rule is not None:
            rets = rets.resample(rule=resample_rule).sum(min_count=1)
        # Set kwargs.
        plot_cumulative_returns_kwargs = plot_cumulative_returns_kwargs or {
            "mode": "log",
            "unit": "%",
        }
        plot_rolling_beta_kwargs = plot_rolling_beta_kwargs or {"window": 52}
        plot_rolling_annualized_sharpe_ratio_kwargs = (
            plot_rolling_annualized_sharpe_ratio_kwargs
            or {"tau": 52, "max_depth": 1, "ci": 0.5}
        )
        # Set OOS start if applicable.
        events = None
        if mode == "all_available" and self.model_evaluator.oos_start is not None:
            events = [(self.model_evaluator.oos_start, "OOS start")]
        # Create the plots.
        if axes is None:
            # Set number of plots.
            if benchmark is not None:
                num_plots = 4
            else:
                num_plots = 3
            _, axes = coplotti.get_multiple_plots(
                num_plots, 1, y_scale=5, constrained_layout=True
            )
        cumrets = rets.cumsum()
        cumrets_mode = plot_cumulative_returns_kwargs["mode"]
        if cumrets_mode == "log":
            pass
        elif cumrets_mode == "pct":
            cumrets = cofinanc.convert_log_rets_to_pct_rets(cumrets)
        else:
            raise ValueError("Invalid cumulative returns mode `{cumrets_mode}`")
        coplotti.plot_cumulative_returns(
            cumrets,
            benchmark_series=benchmark,
            ax=axes[0],
            events=events,
            **plot_cumulative_returns_kwargs,
        )
        if benchmark is not None:
            coplotti.plot_rolling_beta(
                rets,
                benchmark,
                ax=axes[1],
                events=events,
                **plot_rolling_beta_kwargs,
            )
        coplotti.plot_rolling_annualized_sharpe_ratio(
            rets,
            ax=axes[-2],
            events=events,
            **plot_rolling_annualized_sharpe_ratio_kwargs,
        )
        plot_drawdown_kwargs = plot_drawdown_kwargs or {}
        coplotti.plot_drawdown(
            rets, ax=axes[-1], events=events, **plot_drawdown_kwargs
        )

    def plot_rets_and_vol(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        target_volatility: Optional[float] = None,
        resample_rule: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_yearly_barplot_kwargs: Optional[dict] = None,
        plot_monthly_heatmap_kwargs: Optional[dict] = None,
        plot_rolling_annualized_volatility_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Plot returns by year and month, plot rolling volatility.

        :param keys: Use all available if `None`
        :param weights: Average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param target_volatility: Rescale portfolio to achieve
            `target_volatility` on in-sample region
        :param resample_rule: Resampling frequency to apply before plotting
        :param axes: a flat list of axes to plot on
        """
        plot_yearly_barplot_kwargs = plot_yearly_barplot_kwargs or {"unit": "%"}
        plot_monthly_heatmap_kwargs = plot_monthly_heatmap_kwargs or {"unit": "%"}
        plot_rolling_annualized_volatility_kwargs = (
            plot_rolling_annualized_volatility_kwargs
            or {"tau": 52, "max_depth": 1, "unit": "%"}
        )
        rets, _, _ = self.model_evaluator.aggregate_models(
            keys=keys,
            weights=weights,
            mode=mode,
            target_volatility=target_volatility,
        )
        if resample_rule is not None:
            rets = rets.resample(rule=resample_rule).sum(min_count=1)
        num_plots = 3
        if axes is None:
            _, axes = coplotti.get_multiple_plots(
                num_plots, 1, y_scale=5, constrained_layout=True
            )
        # Plot yearly returns.
        coplotti.plot_yearly_barplot(
            rets,
            ax=axes[0],
            figsize=(20, 5 * num_plots),
            **plot_yearly_barplot_kwargs,
        )
        # Plot monthly returns.
        coplotti.plot_monthly_heatmap(
            rets, ax=axes[1], **plot_monthly_heatmap_kwargs
        )
        # Set OOS start if applicable.
        events = None
        if mode == "all_available" and self.model_evaluator.oos_start is not None:
            events = [(self.model_evaluator.oos_start, "OOS start")]
        # Plot volatility.
        coplotti.plot_rolling_annualized_volatility(
            rets,
            ax=axes[2],
            events=events,
            **plot_rolling_annualized_volatility_kwargs,
        )

    def plot_positions(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        target_volatility: Optional[float] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> None:
        """
        Plot holdings and turnover.

        :param keys: Use all available if `None`
        :param weights: Average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param target_volatility: Rescale portfolio to achieve
            `target_volatility` on in-sample region
        :param axes: a flat list of axes to plot on
        """
        _, pos, _ = self.model_evaluator.aggregate_models(
            keys=keys,
            weights=weights,
            mode=mode,
            target_volatility=target_volatility,
        )
        if axes is None:
            num_plots = 2
            _, axes = coplotti.get_multiple_plots(
                num_plots, 1, y_scale=5, constrained_layout=True
            )
        # Set OOS start if applicable.
        events = None
        if mode == "all_available" and self.model_evaluator.oos_start is not None:
            events = [(self.model_evaluator.oos_start, "OOS start")]
        # Plot holdings.
        coplotti.plot_holdings(pos, ax=axes[0], events=events)
        # Plot turnover.
        coplotti.plot_turnover(pos, unit="%", ax=axes[1], events=events)

    def plot_sharpe_ratio_panel(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        frequencies: Optional[List[str]] = None,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> None:
        """
        Plot how the SR varies under resampling.

        :param keys: Use all available if `None`
        :param weights: Average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param resample_rule: Resampling frequency to apply before plotting
        """
        rets, _, _ = self.model_evaluator.aggregate_models(
            keys=keys, weights=weights, mode=mode
        )
        coplotti.plot_sharpe_ratio_panel(rets, frequencies=frequencies, ax=ax)

    def plot_holding_diffs(
        self,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
    ) -> None:
        """
        Plot holding diffs (per key).
        """
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        for k, v in pnl_dict.items():
            # TODO(gp): The linter reports that `label` is not part of the interface.
            coplotti.plot_holding_diffs(
                v["positions"], label=f"Holdings diffs {k}"
            )
        plt.legend()

    def plot_returns_and_predictions(
        self,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> None:
        """
        Plot returns and model predictions (per key).

        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        :param resample_rule: Resampling frequency to apply before plotting
        """
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        keys = self.model_evaluator.get_keys(keys)
        if axes is None:
            _, axes = coplotti.get_multiple_plots(
                len(keys), 1, y_scale=5, sharex=True, sharey=True
            )
            plt.suptitle("Returns and predictions over time", y=1.01)
        for idx, key in enumerate(keys):
            y_yhat = pnl_dict[key][["returns", "predictions"]]
            if resample_rule is not None:
                y_yhat = y_yhat.resample(rule=resample_rule).sum(min_count=1)
            y_yhat.plot(ax=axes[idx], title=f"Model {key}")

    def plot_multiple_tests_adjustment(
        self,
        threshold: float,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        multipletests_plot_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Adjust p-values for selected keys and coplotti.

        :param threshold: Adjust p-value threshold for a "pass"
        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        """
        multipletests_plot_kwargs = multipletests_plot_kwargs or {}
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        pvals = {
            k: costatis.ttest_1samp(v["pnl"]).loc["pval"]
            for k, v in pnl_dict.items()
        }
        coplotti.multipletests_plot(
            pd.Series(pvals), threshold, axes=axes, **multipletests_plot_kwargs
        )

    def plot_multiple_pnls(
        self,
        keys: Optional[List[Any]] = None,
        weights: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> None:
        """
        Plot multiple pnl series (cumulatively summed) simultaneously.

        :param keys: Use all available if `None`
        :param weights: Average if `None`
        :param mode: "all_available", "ins", or "oos"
        :param resample_rule: Resampling frequency to apply before plotting
        """
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        # Extract only the PnL series from `pnl_dict`.
        pnls = {k: v["pnl"] for k, v in pnl_dict.items()}
        aggregate_pnl, _, _ = self.model_evaluator.aggregate_models(
            keys=keys, weights=weights, mode=mode
        )
        hdbg.dassert_not_in("aggregated", pnls.keys())
        pnls["aggregated"] = aggregate_pnl
        if resample_rule is not None:
            for k, v in pnls.items():
                pnls[k] = v.resample(rule=resample_rule).sum(min_count=1)
        coplotti.plot_pnl(pnls, ax=ax)

    def plot_correlation_matrix(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_correlation_matrix_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Plot correlation matrix.

        :param series: "returns", "predictions", "positions", or "pnls"
        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        """
        plot_correlation_matrix_kwargs = plot_correlation_matrix_kwargs or {
            "mode": "heatmap"
        }
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        coplotti.plot_correlation_matrix(
            df, ax=ax, **plot_correlation_matrix_kwargs
        )

    def plot_effective_correlation_rank(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
        plot_effective_correlation_rank_kwargs: Optional[dict] = None,
    ) -> None:
        plot_effective_correlation_rank_kwargs = (
            plot_effective_correlation_rank_kwargs or {}
        )
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        coplotti.plot_effective_correlation_rank(
            df, ax=ax, **plot_effective_correlation_rank_kwargs
        )

    def plot_clustermap(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
        clustermap_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Plot correlation matrix together with dendrogram.

        :param series: "returns", "predictions", "positions", or "pnl"
        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        """
        clustermap_kwargs = clustermap_kwargs or {}
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        corr = df.corr().fillna(0)
        sns.clustermap(corr, ax=ax, **clustermap_kwargs)

    def plot_dendrogram(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> None:
        """
        Plot dendrogram of correlation of selected series.

        :param series: "returns", "predictions", "positions", or "pnl"
        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        """
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        # TODO(Paul): If we fill `NaN`s, we see clusters by data periods
        #     intersections.
        coplotti.plot_dendrogram(df.fillna(0), ax=ax)

    def plot_multiple_time_series(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
        plot_time_series_dict_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Plot one time series per coplotti.

        :param series: "returns", "predictions", "positions", or "pnl"
        :param keys: Use all available if `None`
        :param mode: "all_available", "ins", or "oos"
        :param resample_rule: Resampling frequency to apply before plotting
        """
        plot_time_series_dict_kwargs = plot_time_series_dict_kwargs or {}
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        hdbg.dassert_in(series, ["returns", "predictions", "positions", "pnl"])
        series_dict = {k: v[series] for k, v in pnl_dict.items()}
        if resample_rule is not None:
            for k, v in series_dict.items():
                series_dict[k] = v.resample(rule=resample_rule).sum(min_count=1)
        coplotti.plot_time_series_dict(
            series_dict, axes=axes, **plot_time_series_dict_kwargs
        )

    def plot_pca_components(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        num_components: Optional[int] = None,
        axes: Optional[List[mpl.axes.Axes]] = None,
    ) -> None:
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        pca = coplotti.PCA(mode="standard")
        pca.fit(df.fillna(0))
        pca.plot_components(num_components, axes=axes)

    def plot_explained_variance(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
        ax: Optional[mpl.axes.Axes] = None,
    ) -> None:
        df = self._get_series_as_df(
            series, keys=keys, mode=mode, resample_rule=resample_rule
        )
        pca = coplotti.PCA(mode="standard")
        pca.fit(df.fillna(0))
        pca.plot_explained_variance(ax=ax)

    def _get_series_as_df(
        self,
        series: str,
        keys: Optional[List[Any]] = None,
        mode: Optional[str] = None,
        resample_rule: Optional[str] = None,
    ) -> pd.DataFrame:
        pnl_dict = self.model_evaluator.compute_pnl(keys=keys, mode=mode)
        hdbg.dassert_in(series, ["returns", "predictions", "positions", "pnl"])
        series_dict = {k: v[series] for k, v in pnl_dict.items()}
        if resample_rule is not None:
            for k, v in series_dict.items():
                series_dict[k] = v.resample(rule=resample_rule).sum(min_count=1)
        df = pd.DataFrame.from_dict(series_dict)
        return df
