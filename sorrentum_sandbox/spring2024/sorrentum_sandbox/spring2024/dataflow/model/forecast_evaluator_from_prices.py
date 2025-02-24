"""
Import as:

import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
"""
import collections
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import core.finance as cofinanc
import dataflow.model.abstract_forecast_evaluator as dtfmabfoev
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################
# ForecastEvaluatorFromPrices
# #############################################################################


class ForecastEvaluatorFromPrices(dtfmabfoev.AbstractForecastEvaluator):
    """
    Evaluate returns/volatility forecasts.
    """

    def __init__(
        self,
        price_col: str,
        volatility_col: str,
        prediction_col: str,
        *,
        spread_col: Optional[str] = None,
        buy_price_col: Optional[str] = None,
        sell_price_col: Optional[str] = None,
    ) -> None:
        """
        Construct object.

        :param price_col: price per share
            - the `price_col` is unadjusted price (no adjustment for splits,
              dividends, or volatility); it is used for marking to market and,
              unless buy/sell prices columns are also supplied, execution
              simulation
        :param volatility_col: volatility used for adjustment of forward returns
            - the `volatility_col` is used for position sizing
        :param prediction_col: prediction of volatility-adjusted returns, two
            steps ahead
            - the `prediction_col` is a prediction of vol-adjusted returns
              (presumably with volatility given by `volatility_col`)
        """
        # Initialize dataframe columns.
        super().__init__(price_col, volatility_col, prediction_col)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str(
                    "price_col volatility_col prediction_col spread_col buy_price_col"
                    " sell_price_col"
                )
            )
        # Process optional columns.
        if spread_col is not None:
            hdbg.dassert_isinstance(spread_col, str)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Initialized with spread_col=%s", spread_col)
        self._spread_col = spread_col
        #
        if buy_price_col is not None:
            hdbg.dassert_isinstance(buy_price_col, str)
            # If `buy_price_col` is not `None`, then `sell_price_col` must also
            # not be `None`.
            hdbg.dassert_isinstance(sell_price_col, str)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Initialized with buy_price_col=%s", buy_price_col)
        self._buy_price_col = buy_price_col
        #
        if sell_price_col is not None:
            hdbg.dassert_isinstance(sell_price_col, str)
            # If `sell_price_col` is not `None`, then `buy_price_col` must also
            # not be `None`.
            hdbg.dassert_isinstance(buy_price_col, str)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Initialized with sell_price_col=%s", sell_price_col)
        self._sell_price_col = sell_price_col

    def annotate_forecasts(
        self,
        df: pd.DataFrame,
        **kwargs: Dict[str, Any],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Wrap `compute_portfolio()`, return a single multiindexed dataframe.

        :param df: as in `compute_portfolio()`
        :param kwargs: forwarded to `compute_portfolio()`
        :return: multiindexed portfolio dataframe, stats dataframe
        """
        derived_dfs = self.compute_portfolio(
            df,
            **kwargs,
        )
        dfs = {
            "price": df[self._price_col],
            "volatility": df[self._volatility_col],
            "prediction": df[self._prediction_col],
            "holdings_shares": derived_dfs["holdings_shares"],
            "holdings_notional": derived_dfs["holdings_notional"],
            "executed_trades_shares": derived_dfs["executed_trades_shares"],
            "executed_trades_notional": derived_dfs["executed_trades_notional"],
            "pnl": derived_dfs["pnl"],
        }
        if self._spread_col is not None:
            dfs["spread"] = df[self._spread_col]
        portfolio_df = ForecastEvaluatorFromPrices._build_multiindex_df(dfs)
        return portfolio_df, derived_dfs["stats"]

    def get_cols(self) -> List[str]:
        """
        Return the names of the price, volatility, and prediction columns.
        """
        cols = [
            self._price_col,
            self._volatility_col,
            self._prediction_col,
        ]
        optional_cols = [
            self._spread_col,
            self._buy_price_col,
            self._sell_price_col,
        ]
        for col in optional_cols:
            if col is not None:
                cols = cols + [col]
        return cols

    def compute_counts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute data counts by column grouped by time.
        """
        self._validate_df(df)

        def _compute_counts(df: pd.DataFrame, col: str) -> pd.DataFrame:
            return df[col].groupby(lambda x: x.time()).count()

        count_to_col = {
            "price_count": self._price_col,
            "volatility_count": self._price_col,
            "prediction_count": self._price_col,
            "spread_count": self._spread_col,
            "buy_price_count": self._buy_price_col,
            "sell_price_count": self._sell_price_col,
        }
        dfs = collections.OrderedDict()
        for key, value in count_to_col.items():
            if value is not None:
                dfs[key] = _compute_counts(df, value)
        count_df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        return count_df

    # //////////////////////////////////////////////////////////////////////////////

    def _compute_portfolio(
        self,
        df: pd.DataFrame,
        *,
        style: str = "cross_sectional",
        quantization: Optional[int] = 30,
        liquidate_at_end_of_day: bool = True,
        initialize_beginning_of_day_trades_to_zero: bool = True,
        adjust_for_splits: bool = False,
        reindex_like_input: bool = False,
        burn_in_bars: int = 3,
        burn_in_days: int = 0,
        compute_extended_stats: bool = False,
        asset_id_to_share_decimals: Optional[Dict[int, int]] = None,
        **kwargs: Dict[str, Any],
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute target positions, PnL, and portfolio stats.

        :param df: multiindexed dataframe with predictions, price, volatility
        :param style: belongs to
            - "cross_sectional": cross-sectionally normalize predictions,
              possibly remove a portion of the bulk of the distribution,
              and allocate a target GMV
            - "longitudinal": normalize and threshold predictions
              longitudinally, allocating an equal dollar risk to each name
              independently
        :param quantization: same as in
            `core.finance.share_quantization.quantize_shares()`
        :param liquidate_at_end_of_day: force holdings to zero at the last
            trade if true (otherwise hold overnight)
        :param adjust_for_splits: account for stock splits in considering
            overnight holdings
        :param reindex_like_input: output dataframes to have the same input as
            `df` (e.g., including any weekends or values outside of the
            `start_time`-`end_time` range). If `False`, only return dataframes
            indexed by the inferred "active index" of datetimes
        :param burn_in_bars: number of leading bars to trim (to remove warm-up
            artifacts)
        :param burn_in_days: number of leading days to trim (to remove warm-up
            artifacts). Applied independently of `burn_in_bars`.
        :param compute_extended_stats: compute additional stats beyond the
            five "core" stats.
        :param kwargs: forwarded to either
            `compute_target_positions_cross_sectionally()` or
            `compute_target_positions_longitudinally()` depending upon the
            value of `style`
        :param asset_id_to_share_decimals: same as in
            `core.finance.share_quantization.quantize_shares()`
        :return: dictionary of portfolio dataframes, with keys
            ["holdings_shares", "holdings_notional", "executed_trades_shares",
             "executed_trades_notional", "pnl", "stats"]
        """
        # Record index in case we reindex the results.
        if reindex_like_input:
            idx = df.index
        else:
            idx = None
        # Compute target positions (in dollars).
        target_holdings_notional = self._compute_target_holdings_notional(
            df,
            style,
            **kwargs,
        )
        # Compute holdings (in shares).
        # TODO(Paul): Expose these two parameters.
        ffill_limit = 4
        holdings_shares = self._compute_holdings_shares(
            df,
            target_holdings_notional,
            quantization,
            liquidate_at_end_of_day,
            adjust_for_splits,
            ffill_limit,
            asset_id_to_share_decimals,
        )
        # Compute cash inflows/outflows from trades.
        executed_trades_shares = self._compute_executed_trades_shares(
            df,
            holdings_shares,
            initialize_beginning_of_day_trades_to_zero,
        )
        executed_trades_notional = self._compute_executed_trades_notional(
            df,
            executed_trades_shares,
            ffill_limit,
        )
        # Compute notional positions.
        holdings_notional = self._compute_holdings_notional(df, holdings_shares)
        # Compute PnL.
        pnl = self._compute_pnl(df, holdings_notional, executed_trades_notional)
        # Compute statistics.
        stats = self._compute_stats(
            df,
            holdings_notional,
            executed_trades_notional,
            pnl,
            compute_extended_stats,
        )
        #
        derived_dfs = {
            "holdings_shares": holdings_shares,
            "holdings_notional": holdings_notional,
            "executed_trades_shares": executed_trades_shares,
            "executed_trades_notional": executed_trades_notional,
            "pnl": pnl,
            "stats": stats,
        }
        # Apply burn-in and reindex like input.
        return self._apply_burn_in_and_reindex(
            df,
            derived_dfs,
            burn_in_bars,
            burn_in_days,
            idx,
        )

    # /////////////////////////////////////////////////////////////////////////////

    def _validate_target_position_df(
        self, target_positions: pd.DataFrame, predictions: pd.DataFrame
    ) -> None:
        hpandas.dassert_time_indexed_df(
            target_positions, allow_empty=True, strictly_increasing=True
        )
        hdbg.dassert_eq(target_positions.columns.nlevels, 1)
        hpandas.dassert_axes_equal(target_positions, predictions)

    def _apply_trimming(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trim `df` according to ATH, weekends, missing data.

        :param df: as in `compute_portfolio()`
        :return: `df` trimmed down to:
          - required and possibly optional columns
          - "active" bars (bars where at least one instrument has an end-of-bar
            price)
          - first index with both a returns prediction and a volatility
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df.shape=%s", str(df.shape))
        # Restrict to required columns.
        cols = [self._price_col, self._volatility_col, self._prediction_col]
        optional_cols = [
            self._spread_col,
            self._buy_price_col,
            self._sell_price_col,
        ]
        for col in optional_cols:
            if col is not None and col not in cols:
                cols += [col]
        df = df[cols]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("cols=%s", cols)
        active_index = cofinanc.infer_active_bars(df[self._price_col])
        # Drop rows with no prices (this is an approximate way to handle weekends,
        # market holidays, and shortened trading sessions).
        df = df.reindex(index=active_index)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("after active_index: df.shape=%s", df.shape)
        # Drop indices with prices that precede any returns prediction or
        # volatility computation.
        first_valid_prediction_index = df[
            self._prediction_col
        ].first_valid_index()
        hdbg.dassert_is_not(first_valid_prediction_index, None)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("first_valid_prediction_index"))
        #
        first_valid_volatility_index = df[
            self._volatility_col
        ].first_valid_index()
        hdbg.dassert_is_not(first_valid_volatility_index, None)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("first_valid_volatility_index"))
        #
        first_valid_index = max(
            first_valid_prediction_index, first_valid_volatility_index
        )
        df = df.loc[first_valid_index:]
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df.shape=%s", str(df.shape))
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("trimmed df=\n%s", hpandas.df_to_str(df))
        return df

    def _compute_target_holdings_notional(
        self,
        df: pd.DataFrame,
        style: str,
        **kwargs: Dict[str, Any],
    ) -> pd.DataFrame:
        """
        Compute target positions using returns and volatility predictions.

        :param df: as in `compute_portfolio()`
        :param style: "cross-sectional" or "longitudinal"
        :param kwargs: parameters to forward (depending upon `style`)
        :return: end-of-bar indexed target notional positions to trade into
            over the next bar
        """
        # Extract prediction and volatility dataframes.
        prediction_df = ForecastEvaluatorFromPrices._get_df(
            df, self._prediction_col
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("prediction_df=\n%s", hpandas.df_to_str(prediction_df))
        volatility_df = ForecastEvaluatorFromPrices._get_df(
            df, self._volatility_col
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("volatility_df=\n%s", hpandas.df_to_str(volatility_df))
        spread_df = None
        if self._spread_col is not None:
            spread_df = ForecastEvaluatorFromPrices._get_df(df, self._spread_col)
        # The values of`target_positions` represent cash values.
        if style == "cross_sectional":
            target_notional_positions = (
                cofinanc.compute_target_positions_cross_sectionally(
                    prediction_df,
                    volatility_df,
                    **kwargs,
                )
            )
        elif style == "longitudinal":
            target_notional_positions = (
                cofinanc.compute_target_positions_longitudinally(
                    prediction_df,
                    volatility_df,
                    spread=spread_df,
                    **kwargs,
                )
            )
        else:
            raise ValueError("Unsupported `style`=%s", style)
        self._validate_target_position_df(
            target_notional_positions, prediction_df
        )
        return target_notional_positions

    def _compute_holdings_shares(
        self,
        df: pd.DataFrame,
        target_notional_positions: pd.DataFrame,
        quantization: Optional[int],
        liquidate_at_end_of_day: bool,
        adjust_for_splits: bool,
        ffill_limit: int,
        asset_id_to_share_decimals: Optional[Dict[int, int]],
    ) -> pd.DataFrame:
        """
        Convert next-bar [dollar] positions to end-of-bar [share] holdings.

        :param df: as in `compute_portfolio()`
        :param target_notional_positions: from `_compute_target_holdings_notional()`
        :param quantization: same as in
            `core.finance.share_quantization.quantize_shares()`
        :param liquidate_at_end_of_day: as in `compute_portfolio()`
        :param adjust_for_splits: as in `compute_portfolio()`
        :param ffill_limit: as in `compute_portfolio()`
        :param asset_id_to_share_decimals: same as in
            `core.finance.share_quantization.quantize_shares()`
        :return: end-of-bar indexed holdings in shares (holdings held at the
            end of the bar)
        """
        mark_to_market_price = ForecastEvaluatorFromPrices._get_df(
            df, self._price_col
        )
        # Compute target (next bar) holdings based on prices available at
        # decision time.
        target_holdings_shares = target_notional_positions.divide(
            mark_to_market_price
        )
        # Quantize holdings (e.g., nearest share).
        target_holdings_shares = cofinanc.quantize_holdings(
            target_holdings_shares,
            quantization,
            asset_id_to_decimals=asset_id_to_share_decimals,
        )
        # Adjust holdings for end-of-day and splits. Convert from next-bar
        # desired holdings to end-of-bar realized (assuming perfect fills)
        # holdings.
        ideal_holdings_shares = cofinanc.adjust_holdings_for_overnight(
            target_holdings_shares.shift(1),
            mark_to_market_price,
            liquidate_at_end_of_day,
            adjust_for_splits,
            ffill_limit,
        )
        # If buy/sell prices (possibly with NaNs, indicating no fills) are
        # available, adjust the holdings for underfills (carry positions over).
        if self._buy_price_col is not None:
            buy_price = ForecastEvaluatorFromPrices._get_df(
                df, self._buy_price_col
            )
            sell_price = ForecastEvaluatorFromPrices._get_df(
                df, self._sell_price_col
            )
            holdings_shares = cofinanc.adjust_holdings_for_underfills(
                ideal_holdings_shares,
                mark_to_market_price,
                buy_price,
                sell_price,
            )
        else:
            holdings_shares = ideal_holdings_shares
        return holdings_shares

    def _compute_executed_trades_shares(
        self,
        df: pd.DataFrame,
        holdings_shares: pd.DataFrame,
        initialize_beginning_of_day_trades_to_zero: bool,
    ) -> pd.DataFrame:
        """
        Compute trade inflows and outflows.

        :param df: as in `compute_portfolio()`
        :param holdings_shares: from `_compute_holdings_shares()`
        :param initialize_beginning_of_day_trades_to_zero: whether to force
            beginning-of-day trades to be zero. Set to `True` to take into
            account the impact of corporate actions on overnight holdings.
        :return: end-of-bar indexed trades in shares
        """
        # Compute trades as the difference in (share) holdings.
        executed_trades_shares = holdings_shares.subtract(
            holdings_shares.shift(1), fill_value=0
        )
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "`executed_trades_shares pre-adjusted`=\n%s",
                hpandas.df_to_str(executed_trades_shares),
            )
        # In equity markets with corporate actions, the previous end-of-day
        # share counts may differ from the beginning-of-day share counts even
        # though no trades have taken place. This can be remedied by resetting
        # the beginning-of-day trades to zero.
        if initialize_beginning_of_day_trades_to_zero:
            mark_to_market_price_df = ForecastEvaluatorFromPrices._get_df(
                df, self._price_col
            )
            bod_timestamps = cofinanc.retrieve_beginning_of_day_timestamps(
                mark_to_market_price_df
            )
            # Set overnight trades to zero.
            executed_trades_shares.loc[bod_timestamps["timestamp"]] *= 0
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "`executed_trades_shares adjusted`=\n%s",
                hpandas.df_to_str(executed_trades_shares),
            )
        return executed_trades_shares

    def _compute_executed_trades_notional(
        self,
        df: pd.DataFrame,
        executed_trades_shares: pd.DataFrame,
        ffill_limit: int,
    ) -> pd.DataFrame:
        """
        Compute trade inflows and outflows.

        :param df: as in `compute_portfolio()`
        :param executed_trades_shares:
        :return: end-of-bar indexed notional trades
        """
        execution_price_df = self._compute_execution_prices(
            df, executed_trades_shares, ffill_limit
        )
        executed_trades_notional = executed_trades_shares.multiply(
            execution_price_df.ffill(limit=ffill_limit)
        )
        return executed_trades_notional

    def _compute_execution_prices(
        self,
        df: pd.DataFrame,
        executed_trades_shares: pd.DataFrame,
        ffill_limit: int,
    ) -> pd.DataFrame:
        """
        Compute execution prices from buy/sell price columns if available.

        :param df: as in `compute_portfolio()`
        :param executed_trades_shares:
        :return: end-of-bar indexed dataframe of prices to use to value
            cash outflows/inflows for the buying/selling of shares
        """
        mark_to_market_price_df = ForecastEvaluatorFromPrices._get_df(
            df, self._price_col
        ).ffill(limit=ffill_limit)
        # Use separate buy/sell prices if available.
        if self._buy_price_col is not None and self._sell_price_col is not None:
            buy_price_df = ForecastEvaluatorFromPrices._get_df(
                df, self._buy_price_col
            )
            sell_price_df = ForecastEvaluatorFromPrices._get_df(
                df, self._sell_price_col
            )
            # Market in last bar.
            buy_price_df = cofinanc.replace_end_of_day_values(
                buy_price_df, mark_to_market_price_df
            )
            sell_price_df = cofinanc.replace_end_of_day_values(
                sell_price_df, mark_to_market_price_df
            )
            execution_price_df = cofinanc.apply_execution_prices_to_trades(
                executed_trades_shares,
                buy_price_df,
                sell_price_df,
            )
        else:
            execution_price_df = mark_to_market_price_df
        return execution_price_df

    def _compute_holdings_notional(
        self,
        df: pd.DataFrame,
        holdings_shares: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute positions in dollars from share holdings.

        :param df: as in `compute_portfolio()`
        :param holdings_shares: from `_compute_holdings_shares()`
        :return: end-of-bar indexed dataframe of holdings valued using
            `self.price_col` of `df`
        """
        mark_to_market_price = ForecastEvaluatorFromPrices._get_df(
            df, self._price_col
        )
        holdings_notional = holdings_shares.multiply(mark_to_market_price)
        return holdings_notional

    def _compute_pnl(
        self,
        df: pd.DataFrame,
        holdings_notional: pd.DataFrame,
        executed_trades_notional: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute PnL from dollar positions and dollar inflows/outflows.

        :param df: as in `compute_portfolio()`
        :param holdings_notional: from `_compute_holdings_notional()`
        :param executed_trades_notional: from
            `_compute_executed_trades_notional()`
        :return: end-of-bar indexed dataframe of per-instrument dollar
            PnL
        """
        _ = df
        pnl = holdings_notional.subtract(
            holdings_notional.shift(1), fill_value=0
        ).subtract(executed_trades_notional, fill_value=0)
        return pnl

    def _compute_stats(
        self,
        df: pd.DataFrame,
        holdings_notional: pd.DataFrame,
        executed_trades_notional: pd.DataFrame,
        pnl: pd.DataFrame,
        compute_extended_stats: bool,
    ) -> pd.DataFrame:
        """
        Compute PnL from dollar positions and dollar inflows/outflows.

        :param df: as in `compute_portfolio()`
        :param holdings_notional: from `_compute_holdings_notional()`
        :param executed_trades_notional: from `_compute_flows()`
        :param pnl: from `_compute_pnl()`
        :param compute_extended_stats: forwarded to
            `cofinanc.compute_bar_metrics()`
        :return: per-bar metrics from `cofinanc.compute_bar_metrics()`
        """
        spread_df = None
        if self._spread_col is not None:
            spread_df = ForecastEvaluatorFromPrices._get_df(df, self._spread_col)
        stats = cofinanc.compute_bar_metrics(
            holdings_notional,
            -executed_trades_notional,
            pnl,
            spread_df,
            compute_extended_stats,
        )
        return stats


# #############################################################################


def normalize_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adapt the `ForecastEvaluatorFromPrices` portfolio df to `Portfolio`'s.
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_is_subset(
        [
            "holdings_shares",
            "holdings_notional",
            "executed_trades_shares",
            "executed_trades_notional",
            "pnl",
        ],
        df.columns.levels[0].to_list(),
    )
    #
    holdings = df["holdings_shares"]
    holdings_marked_to_market = df["holdings_notional"]
    flows = -df["executed_trades_notional"]
    pnl = df["pnl"]
    #
    normalized_df = pd.concat(
        {
            "holdings": holdings,
            "holdings_marked_to_market": holdings_marked_to_market,
            "flows": flows,
            "pnl": pnl,
        },
        axis=1,
    )
    return normalized_df
