"""
Import as:

import dataflow.model.stats_computer as dtfmostcom
"""

import collections
import functools
import logging
from typing import Callable, List, Optional, Tuple, Union

import pandas as pd

import core.finance as cofinanc
import core.statistics as costatis
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.htimer as htimer

_LOG = logging.getLogger(__name__)


class StatsComputer:
    """
    Compute a particular piece of stats instead of the whole stats table.
    """

    @staticmethod
    def compute_autocorrelation_stats(srs: pd.Series) -> pd.Series:
        # name = "autocorrelation"
        # ljung_box = costatis.apply_ljung_box_test(srs)
        # TODO(Paul): Only return pvals. Rename according to test and lag.
        #     Change default lags reported.
        raise NotImplementedError

    def compute_time_series_stats(self, srs: pd.Series) -> pd.Series:
        """
        Compute statistics for a non-necessarily financial time series.
        """
        # List of pd.Series each with various metrics.
        stats = []
        with htimer.TimedScope(logging.DEBUG, "Computing ratios"):
            stats.append(self.compute_ratios(srs))
        with htimer.TimedScope(logging.DEBUG, "Computing samplings stats"):
            stats.append(self.compute_sampling_stats(srs))
        with htimer.TimedScope(logging.DEBUG, "Computing summary stats"):
            stats.append(self.compute_summary_stats(srs))
        with htimer.TimedScope(logging.DEBUG, "Computing stationarity stats"):
            stats.append(self.compute_stationarity_stats(srs))
        with htimer.TimedScope(logging.DEBUG, "Computing normality stats"):
            stats.append(self.compute_normality_stats(srs))
        # This seems to be slow.
        # stats.append(self.compute_autocorrelation_stats(srs))
        with htimer.TimedScope(logging.DEBUG, "Computing spectral stats"):
            stats.append(self.compute_spectral_stats(srs))
        # Concatenate the resulting series into a single multi-index series.
        names = [stat.name for stat in stats]
        result = pd.concat(stats, axis=0, keys=names)
        result.name = srs.name
        return result

    def compute_sampling_stats(self, srs: pd.Series) -> pd.Series:
        name = "sampling"
        functions = [
            costatis.summarize_time_index_info,
            costatis.compute_special_value_stats,
        ]
        return self._compute_stat_functions(srs, name, functions)

    def compute_summary_stats(self, srs: pd.Series) -> pd.Series:
        name = "summary"
        # TODO(*): Add
        #   - var and std assuming zero mean
        functions = [
            functools.partial(
                costatis.compute_moments,
                prefix="scipy.",
            ),
            functools.partial(costatis.ttest_1samp, prefix="null_mean_zero."),
            costatis.compute_jensen_ratio,
            lambda x: x.describe(),
        ]
        return self._compute_stat_functions(srs, name, functions)

    def compute_stationarity_stats(self, srs: pd.Series) -> pd.Series:
        name = "stationarity"
        # Restrict the number of lags because
        #   1. On long time series, auto-selection is time-consuming
        #   2. In practice, the focus is typically on lower order lags
        lags = 16
        functions = [
            functools.partial(
                costatis.apply_adf_test, maxlag=lags, prefix="adf."
            ),
            functools.partial(
                costatis.apply_kpss_test, nlags=lags, prefix="kpss."
            ),
        ]
        return self._compute_stat_functions(srs, name, functions)

    def compute_normality_stats(self, srs: pd.Series) -> pd.Series:
        name = "normality"
        functions = [
            functools.partial(
                costatis.apply_normality_test, prefix="omnibus_null_normal."
            ),
            functools.partial(
                costatis.compute_centered_gaussian_total_log_likelihood,
                prefix="centered_gaussian.",
            ),
        ]
        # TODO(*): costatis.compute_centered_gaussian_log_likelihood
        return self._compute_stat_functions(srs, name, functions)

    def compute_spectral_stats(self, srs: pd.Series) -> pd.Series:
        name = "spectral"
        functions = [
            costatis.compute_forecastability,
        ]
        return self._compute_stat_functions(srs, name, functions)

    def compute_ratios(self, srs: pd.Series) -> pd.Series:
        name = "ratios"
        functions = [
            costatis.summarize_sharpe_ratio,
            functools.partial(costatis.ttest_1samp, prefix="sr."),
        ]
        result = self._compute_stat_functions(srs, name, functions)
        kratio = pd.Series(costatis.compute_kratio(srs), index=["kratio"])
        kratio.name = name
        return pd.concat([result, kratio])

    def compute_portfolio_stats(
        self,
        df: pd.DataFrame,
        freq: str,
        *,
        pnl_col: str = "pnl",
        gross_volume_col: str = "gross_volume",
        net_volume_col: str = "net_volume",
        gmv_col: str = "gmv",
        nmv_col: str = "nmv",
    ) -> Tuple[Union[pd.Series, pd.DataFrame], pd.DataFrame]:
        """
        Compute standard portfolio metrics.

        If `df` has multiple column levels, treat the outermost level as
        a portfolio name then compute stats for each portfolio name.
        """
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
        if df.columns.nlevels == 1:
            return self._compute_portfolio_stats(
                df,
                freq,
                pnl_col=pnl_col,
                gross_volume_col=gross_volume_col,
                net_volume_col=net_volume_col,
                gmv_col=gmv_col,
                nmv_col=nmv_col,
            )
        hdbg.dassert_eq(df.columns.nlevels, 2)
        keys = df.columns.levels[0].to_list()
        stats = collections.OrderedDict()
        resampled_dfs = collections.OrderedDict()
        for key in keys:
            stat, resampled_df = self._compute_portfolio_stats(
                df[key],
                freq,
                pnl_col=pnl_col,
                gross_volume_col=gross_volume_col,
                net_volume_col=net_volume_col,
                gmv_col=gmv_col,
                nmv_col=nmv_col,
            )
            stats[key] = stat
            resampled_dfs[key] = resampled_df
        stats_df = pd.DataFrame(stats)
        resampled_df = pd.concat(
            resampled_dfs.values(), axis=1, keys=resampled_dfs.keys()
        )
        return stats_df, resampled_df

    def compute_per_asset_stats(
        self,
        df: pd.DataFrame,
        *,
        returns_col: Optional[str] = None,
        volatility_col: Optional[str] = None,
        prediction_col: Optional[str] = None,
        position_col: Optional[str] = None,
        pnl_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Apply `compute_stats()` to each asset and merge results.

        :param df: multiindexed dataframe
        """
        dfs = dtfcore.GroupedColDfToDfColProcessor.preprocess(
            df,
            [
                (returns_col,),
                (volatility_col,),
                (prediction_col,),
                (position_col,),
                (pnl_col,),
            ],
        )
        stats = []
        for key, value in dfs.items():
            stat = self.compute_finance_stats(
                value,
                returns_col=returns_col,
                volatility_col=volatility_col,
                prediction_col=prediction_col,
                position_col=position_col,
                pnl_col=pnl_col,
            )
            stat.name = key
            stats.append(stat)
        return pd.concat(stats, axis=1)

    # TODO(Paul): rename `compute_stats()`.
    def compute_finance_stats(
        self,
        df: pd.DataFrame,
        *,
        returns_col: Optional[str] = None,
        volatility_col: Optional[str] = None,
        prediction_col: Optional[str] = None,
        position_col: Optional[str] = None,
        pnl_col: Optional[str] = None,
    ) -> pd.Series:
        """
        Compute financially meaningful statistics.

        :param returns_col: returns realized at indexed timestamp
        :param volatility_col: volatility forecast or realized available
            at timestamp
        :param prediction_col: 2-step-ahead predictions of volatility-
            normalized available returns based on data at indexed
            timestamp
        :param position_col: positions at indexed timestamp, informed by
            predictions from the previous timestamp and subject to
            returns realized at the next timestamp
        :param pnl_col: PnL realized at indexed timestamp
        """
        hdbg.dassert(not isinstance(df.columns, pd.MultiIndex))
        results = []
        # Compute stats related to positions.
        if position_col is not None:
            position_stats = self._compute_position_stats(df[position_col])
            results.append(position_stats)
        # Compute stats related to PnL.
        if pnl_col is not None:
            pnl_stats = self._compute_pnl_stats(df[pnl_col])
            results.append(pnl_stats)
        # Currently we do not calculate individual prediction/returns stats.
        if (
            returns_col is not None
            and volatility_col is not None
            and prediction_col is not None
        ):
            name = "pnl"
            returns = df[returns_col]
            predictions = df[prediction_col].divide(df[volatility_col]).shift(2)
            #
            prediction_corr = predictions.corr(returns)
            corr = pd.Series(
                prediction_corr, index=["prediction_corr"], name=name
            )
            results.append(pd.concat([corr], keys=["correlation"]))
            #
            srs = pd.Series(
                costatis.compute_implied_sharpe_ratio(
                    predictions, prediction_corr
                ),
                index=["sr_implied_by_prediction_corr"],
                name=name,
            )
            results.append(pd.concat([srs], keys=["ratios"]))
            #
            j_ratio = costatis.compute_jensen_ratio(returns)["jensen_ratio"]
            hit_rate = pd.Series(
                costatis.compute_hit_rate_implied_by_correlation(
                    prediction_corr, j_ratio
                ),
                index=["hit_rate_implied_by_prediction_corr"],
                name=name,
            )
            results.append(pd.concat([hit_rate], keys=["finance"]))
            #
            hit_rate = costatis.calculate_hit_rate(returns * predictions)
            hit_rate = hit_rate["hit_rate_point_est_(%)"] / 100
            corr2 = pd.Series(
                costatis.compute_correlation_implied_by_hit_rate(
                    hit_rate, j_ratio
                ),
                index=["prediction_corr_implied_by_hit_rate"],
                name=name,
            )
            results.append(pd.concat([corr2], keys=["correlation"]))
        if returns_col is not None and position_col is not None:
            returns = df[returns_col]
            positions = df[position_col].shift(1)
            #
            name = "pnl"
            bets = costatis.compute_bet_stats(positions, returns)
            bets.name = name
            results.append(pd.concat([bets], keys=["bets"]))
        if returns_col is not None and pnl_col is not None:
            returns = df[returns_col]
            pnl = df[pnl_col]
            #
            corr = pd.Series(
                pnl.corr(returns), index=["pnl_corr_to_underlying"], name=name
            )
            results.append(pd.concat([corr], keys=["correlation"]))
        # No predictions and positions calculations yet.
        # No predictions and PnL calculations yet.
        # No positions and PnL calculations yet.
        result = pd.concat(results, axis=0)
        hdbg.dassert_isinstance(result, pd.Series)
        return result

    # TODO(Paul): Make this a decorator.
    @staticmethod
    def _apply_func(
        data: Union[pd.Series, pd.DataFrame],
        func: Callable,
    ) -> Union[pd.Series, pd.DataFrame]:
        is_series = isinstance(data, pd.Series)
        if is_series:
            data = data.to_frame()
        hdbg.dassert_isinstance(data, pd.DataFrame)
        func_result = data.apply(func)
        hdbg.dassert_isinstance(func_result, pd.DataFrame)
        if is_series:
            func_result = func_result.squeeze()
            hdbg.dassert_isinstance(func_result, pd.Series)
        return func_result

    @staticmethod
    def _compute_stat_functions(
        srs: pd.Series,
        name: str,
        functions: List[Callable],
    ) -> pd.Series:
        """
        Apply a list of functions to a series.
        """
        hdbg.dassert_isinstance(srs, pd.Series)
        # Apply the functions.
        stats = [function(srs).rename(name) for function in functions]
        # Concat the list of series in a single one.
        srs_out = pd.concat(stats)
        return srs_out

    def _compute_portfolio_stats(
        self,
        df: pd.DataFrame,
        freq: str,
        *,
        pnl_col: str = "pnl",
        gross_volume_col: str = "gross_volume",
        net_volume_col: str = "net_volume",
        gmv_col: str = "gmv",
        nmv_col: str = "nmv",
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Compute standard portfolio metrics.

        :return: (stats series, `df` resampled at `freq`)
        """
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert(not isinstance(df.columns, pd.MultiIndex))
        hdbg.dassert_is_subset(
            [pnl_col, gross_volume_col, net_volume_col, gmv_col, nmv_col],
            df.columns.to_list(),
        )
        df = cofinanc.resample_portfolio_bar_metrics(
            df,
            freq,
            pnl_col=pnl_col,
            gross_volume_col=gross_volume_col,
            net_volume_col=net_volume_col,
            gmv_col=gmv_col,
            nmv_col=nmv_col,
        )
        results = []
        #
        srs = df["pnl"]
        # Add Sharpe ratio, K-ratio.
        ratios = self.compute_ratios(srs)
        ratios = ratios.round(2)
        results.append(pd.concat([ratios], keys=["ratios"]))
        # Add GMV stats.
        gmv_stats = pd.Series(
            {
                "gmv_mean": df["gmv"].mean(),
                "gmv_stdev": df["gmv"].std(),
            },
        )
        results.append(pd.concat([gmv_stats], keys=["dollar"]))
        # Add dollar return, volatility, drawdown.
        name = "dollar"
        functions = [
            costatis.compute_annualized_return_and_volatility,
            costatis.compute_max_drawdown,
        ]
        stats = self._compute_stat_functions(srs, name, functions)
        results.append(pd.concat([stats], keys=["dollar"]))
        # Add PnL stats.
        pnl_stats = pd.Series(
            {
                "pnl_mean": df["pnl"].mean(),
                "pnl_std": df["pnl"].std(),
            }
        )
        results.append(pd.concat([pnl_stats], keys=["dollar"]))
        # Add dollar turnover, bias.
        dollar_turnover_and_bias = costatis.compute_turnover_and_bias(
            df["gross_volume"],
            df["nmv"],
        )
        results.append(pd.concat([dollar_turnover_and_bias], keys=["dollar"]))
        # Add percentage return, volatility, drawdown.
        srs = df["pnl"] / df["gmv"].mean()
        name = "percentage"
        functions = [
            costatis.compute_annualized_return_and_volatility,
            costatis.compute_max_drawdown,
        ]
        stats = 100 * self._compute_stat_functions(srs, name, functions)
        results.append(pd.concat([stats], keys=["percentage"]))
        #
        pnl_stats = 100 * pd.Series(
            {
                "pnl_mean": srs.mean(),
                "pnl_std": srs.std(),
            }
        )
        results.append(pd.concat([pnl_stats], keys=["percentage"]))
        # Add dollar turnover, bias.
        percentage_turnover_and_bias = 100 * costatis.compute_turnover_and_bias(
            df["gross_volume"] / df["gmv"].mean(),
            df["nmv"] / df["gmv"].mean(),
        )
        results.append(
            pd.concat([percentage_turnover_and_bias], keys=["percentage"])
        )
        result = pd.concat(results, axis=0).astype("float").round(2)
        hdbg.dassert_isinstance(result, pd.Series)
        return result, df

    def _compute_pnl_stats(self, srs: pd.Series) -> pd.Series:
        """
        Compute stats for a PnL stream.

        :param srs: PnL stream. If `srs.index.freq` is `None`, then `srs` will
            be resampled to `B` prior to stats computations.
        :return: multiindexed series of PnL stats
        """
        srs = cofinanc.maybe_resample(srs)
        #
        results = []
        results.append(self.compute_time_series_stats(srs))
        #
        name = "pnl"
        functions = [
            costatis.compute_annualized_return_and_volatility,
            costatis.compute_max_drawdown,
            costatis.calculate_hit_rate,
        ]
        stats = self._compute_stat_functions(srs, name, functions)
        results.append(pd.concat([stats], keys=["portfolio"]))
        #
        corr = pd.Series(
            costatis.compute_implied_correlation(srs),
            index=["prediction_corr_implied_by_pnl"],
            name=name,
        )
        results.append(pd.concat([corr], keys=["correlation"]))
        return pd.concat(results, axis=0)

    def _compute_position_stats(self, srs: pd.Series) -> pd.Series:
        results = []
        # Compute stats related to positions.
        name = "positions"
        functions = [costatis.compute_avg_turnover_and_holding_period]
        stats = self._compute_stat_functions(srs, name, functions)
        _LOG.info("stats=\n%s", stats)
        results.append(pd.concat([stats], keys=["portfolio"]))
        return pd.concat(results, axis=0)
