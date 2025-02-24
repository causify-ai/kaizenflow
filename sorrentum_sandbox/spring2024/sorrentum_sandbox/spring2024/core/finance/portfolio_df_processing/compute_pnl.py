"""
Import as:

import core.finance.portfolio_df_processing.compute_pnl as cfpdpcopn
"""
import logging

import pandas as pd

_LOG = logging.getLogger(__name__)


def cross_check_portfolio_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the PnL using multiple generally equivalent calculations.

    Computations may legitimately differ in some cases due to overnight
    holdings, corporate actions, and special beginning-of-day/end-of-day
    settings.

    Computations may also differ if trades were calculation using separate
    execution prices (`buy_price_col`, `sell_price_col`).

    :param df: `portfolio_df` output of `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :return: multiindexed dataframe with PnL correlations
    """
    # Reference PnL (nominal).
    reference_pnl = df["pnl"]
    # PnL computed from notional position changes and notional in/outflows.
    holdings_notional_diff_minus_trades_notional = (
        df["holdings_notional"].diff().subtract(df["executed_trades_notional"])
    )
    # PnL computed from share counts and price differences.
    holdings_shares_times_price_diff = (
        df["holdings_shares"].shift(1).multiply(df["price"].diff())
    )
    # PnL computed from notional position changes and recomputed notional trades.
    holdings_notional_minus_trade_times_price = (
        df["holdings_notional"]
        .diff()
        .subtract(df["price"].multiply(df["holdings_shares"].diff()))
    )
    # PnL computed from notional positions and percentage price changes.
    holdings_notional_times_pct_price_change = (
        df["holdings_notional"].shift(1).multiply(df["price"].pct_change())
    )
    # Organize PnL calculations into a multiindexed dataframe.
    pnl_dict = {
        "reference_pnl": reference_pnl,
        "holdings_notional_diff_minus_trades_notional": holdings_notional_diff_minus_trades_notional,
        "holdings_times_price_diff": holdings_shares_times_price_diff,
        "holdings_notional_minus_trade_times_price": holdings_notional_minus_trade_times_price,
        "holdings_notional_times_pct_price_change": holdings_notional_times_pct_price_change,
    }
    pnl_df = pd.concat(pnl_dict.values(), axis=1, keys=pnl_dict.keys())
    pnl_df = pnl_df.swaplevel(i=0, j=1, axis=1)
    # Compute per-instrument correlations of various PnL calculations.
    pnl_corrs = {}
    for col in pnl_df.columns.levels[0]:
        pnl_corrs[col] = pnl_df[col].corr()
    pnl_corr_df = pd.concat(pnl_corrs.values(), keys=pnl_corrs.keys())
    return pnl_corr_df
