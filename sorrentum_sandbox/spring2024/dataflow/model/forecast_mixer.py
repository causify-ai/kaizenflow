"""
Import as:

import dataflow.model.forecast_mixer as dtfmofomix
"""

import collections
import functools
import logging
from typing import List, Optional, Union

import pandas as pd

import dataflow.model.forecast_evaluator_from_returns as dtfmfefrre
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class ForecastMixer:
    """
    Mix multiple predictions together.
    """

    def __init__(
        self,
        returns_col: str,
        volatility_col: str,
        prediction_cols: List[Union[int, str]],
    ) -> None:
        hdbg.dassert_isinstance(returns_col, str)
        self._returns_col = returns_col
        hdbg.dassert_isinstance(volatility_col, str)
        self._volatility_col = volatility_col
        hdbg.dassert_isinstance(prediction_cols, list)
        self._predictions_cols = prediction_cols
        self._forecast_evaluator = dtfmfefrre.ForecastEvaluatorFromReturns(
            returns_col="returns",
            volatility_col="volatility",
            prediction_col="prediction",
        )

    def generate_portfolio_bar_metrics_df(
        self,
        df: pd.DataFrame,
        weights: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
    ) -> pd.DataFrame:
        """
        Generate portfolio bar metrics given prediction weights.

        :param df: a multiindexed dataframe with predction, volatility,
            returns columns at the outer level and asset ids at the inner
            level.
        :param weights: dataframe of weights, indexed by prediction col. Each
            column of `weights` represents a different collection of weights.
        :param target_gmv: forward to `compute_portfolio()`
        :param dollar_neutrality: forward to `compute_portfolio()`
        :return: a multiindexed dataframe of portfolio bar metrics
        """
        # Ensure `df` is a dataframe with two levels of columns
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert_eq(df.columns.nlevels, 2)
        hdbg.dassert_is_subset(
            self._predictions_cols, df.columns.levels[0].to_list()
        )
        # Ensure `weights` is a dataframe with index equivalent to
        # the prediction cols.
        hdbg.dassert_isinstance(weights, pd.DataFrame)
        hdbg.dassert_eq(weights.columns.nlevels, 1)
        hdbg.dassert(not weights.columns.has_duplicates)
        hdbg.dassert_set_eq(weights.index.to_list(), self._predictions_cols)
        # TODO(Paul): Check uniqueness of weights columns.
        # Create one bar metric df per column in `weights`.
        bar_metrics_dfs = collections.OrderedDict()
        for col in weights.columns:
            weight_srs = weights[col]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("weights=\n%s", weight_srs)
            # Sum weighted predictions
            dfs = []
            for prediction_col in self._predictions_cols:
                dfs.append(weight_srs[prediction_col] * df[prediction_col])
            sum_df = functools.reduce(lambda x, y: x.add(y), dfs)
            # Build forecast dataframe.
            forecast_dfs = {
                "prediction": sum_df,
                "volatility": df[self._volatility_col],
                "returns": df[self._returns_col],
            }
            forecast_df = pd.concat(
                forecast_dfs.values(), axis=1, keys=forecast_dfs.keys()
            )
            # Compute the bar metrics for `forecast_df`.
            _, _, bar_stats = self._forecast_evaluator.compute_portfolio(
                forecast_df,
                target_gmv=target_gmv,
                dollar_neutrality=dollar_neutrality,
                reindex_like_input=True,
            )
            bar_metrics_dfs[col] = bar_stats
        # Build a multiindexed dataframe.
        bar_metrics_df = pd.concat(
            bar_metrics_dfs.values(), axis=1, keys=bar_metrics_dfs.keys()
        )
        return bar_metrics_df
