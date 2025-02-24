"""
Import as:

import im_v2.ig.data.client.compute_stats_from_tiles as imvidccsft
"""

import logging

import pandas as pd

import core.finance as cofinan
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def resample_taq_bars(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Resample (a subset of) TAQ bar columns to `rule`.

    :param df: TAQ bar data for a single name indexed by datetime.
    :param rule:
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(df.columns.nlevels, 1)
    resampling_groups = [
        (
            {
                "open": "open",
            },
            "first",
            {},
        ),
        (
            {
                "ask_high": "ask_high",
                "bid_high": "bid_high",
                "day_high": "day_high",
                "high": "high",
            },
            "max",
            {},
        ),
        (
            {
                "ask_low": "ask_low",
                "bid_low": "bid_low",
                "day_low": "day_low",
                "low": "low",
            },
            "min",
            {},
        ),
        (
            {
                "all_day_notional": "all_day_notional",
                "all_day_volume": "all_day_volume",
                "ask": "ask",
                "ask_size": "ask_size",
                "bid": "bid",
                "bid_size": "bid_size",
                "close": "close",
                "day_notional": "day_notional",
                "day_num_spread": "day_num_spread",
                "day_num_trade": "day_num_trade",
                "day_sided_ask_count": "day_sided_ask_count",
                "day_sided_ask_notional": "day_sided_ask_notional",
                "day_sided_ask_shares": "day_sided_ask_shares",
                "day_sided_bid_count": "day_sided_bid_count",
                "day_sided_bid_notional": "day_sided_bid_notional",
                "day_sided_bid_shares": "day_sided_bid_shares",
                "day_spread": "day_spread",
                "day_volume": "day_volume",
                "last_trade": "last_trade",
                "last_trade_volume": "last_trade_volume",
            },
            "last",
            {},
        ),
        (
            {
                "notional": "notional",
                "sided_ask_count": "sided_ask_count",
                "sided_ask_notional": "sided_ask_notional",
                "sided_ask_shares": "sided_ask_shares",
                "sided_bid_count": "sided_bid_count",
                "sided_bid_notional": "sided_bid_notional",
                "sided_bid_shares": "sided_bid_shares",
                "volume": "volume",
            },
            "sum",
            {},
        ),
    ]
    vwap_groups = [
        ("close", "volume", "close_vwap"),
        ("ask", "ask_size", "ask_vwap"),
        ("bid", "bid_size", "bid_vwap"),
    ]
    resampled = cofinan.resample_bars(df, rule, resampling_groups, vwap_groups)
    return resampled


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-bar quote and trade statistics from underlying TAQ data.

    :param df: TAQ bar data for a single name indexed by datetime.
    :return: stats dataframe, indexed like `df`
    """
    hpandas.dassert_time_indexed_df(
        df, allow_empty=False, strictly_increasing=True
    )
    hdbg.dassert_eq(df.columns.nlevels, 1)
    stats_srs_list = []
    # Convert quantities that strictly accumulate throughout each day to
    # per-bar quantities. There may be artifacts around the open.
    bar_notional = df["day_notional"].diff().rename("bar_notional")
    stats_srs_list.append(bar_notional)
    bar_num_spread = df["day_num_spread"].diff().rename("bar_num_spread")
    stats_srs_list.append(bar_num_spread)
    bar_num_trade = df["day_num_trade"].diff().rename("bar_num_trade")
    stats_srs_list.append(bar_num_trade)
    bar_cum_spread = df["day_spread"].diff().rename("bar_cum_spread")
    stats_srs_list.append(bar_cum_spread)
    bar_notional = df["day_notional"].diff().rename("bar_notional")
    stats_srs_list.append(bar_notional)
    bar_volume = df["day_volume"].diff().rename("bar_volume")
    stats_srs_list.append(bar_volume)
    ig_bar_trade_vwap = (bar_notional / bar_volume).rename("ig_bar_trade_vwap")
    stats_srs_list.append(ig_bar_trade_vwap)
    # Compute price and spread from bid/ask.
    bid_ask_midpoint = (0.5 * (df["ask"] + df["bid"])).rename("bid_ask_midpoint")
    stats_srs_list.append(bid_ask_midpoint)
    bid_ask_spread_dollars = (df["ask"] - df["bid"]).rename(
        "bid_ask_spread_dollars"
    )
    stats_srs_list.append(bid_ask_spread_dollars)
    bid_ask_spread_ratio = (bid_ask_spread_dollars / bid_ask_midpoint).rename(
        "bid_ask_spread_ratio"
    )
    stats_srs_list.append(bid_ask_spread_ratio)
    # Compute bid/ask vwap.
    ig_bar_bid_vwap = (df["sided_bid_notional"] / df["sided_bid_shares"]).rename(
        "ig_bar_bid_vwap"
    )
    stats_srs_list.append(ig_bar_bid_vwap)
    ig_bar_ask_vwap = (df["sided_ask_notional"] / df["sided_ask_shares"]).rename(
        "ig_bar_ask_vwap"
    )
    stats_srs_list.append(ig_bar_ask_vwap)
    # Compute spread from IG sampling.
    bar_mean_spread_dollars = (bar_cum_spread / bar_num_spread).rename(
        "bar_mean_spread_dollars"
    )
    stats_srs_list.append(bar_mean_spread_dollars)
    bar_mean_spread_ratio = (bar_mean_spread_dollars / bid_ask_midpoint).rename(
        "bar_mean_spread_ratio"
    )
    stats_srs_list.append(bar_mean_spread_ratio)
    # Compute ranges and relation of `close` values to the bar range.
    trade_range = (df["high"] - df["low"]).rename("trade_range")
    stats_srs_list.append(trade_range)
    trade_range_ratio = (trade_range / bid_ask_midpoint).rename(
        "trade_range_ratio"
    )
    stats_srs_list.append(trade_range_ratio)
    # TODO(Paul): Factor out a function for this.
    trade_stochastic = (
        (2 * df["close"] - df["high"] - df["low"]) / trade_range
    ).rename("trade_stochastic")
    stats_srs_list.append(trade_stochastic)
    trade_drift_to_range = ((df["close"] - df["open"]) / trade_range).rename(
        "trade_drift_to_range"
    )
    stats_srs_list.append(trade_drift_to_range)
    ask_range = (df["ask_high"] - df["ask_low"]).rename("ask_range")
    stats_srs_list.append(ask_range)
    ask_range_ratio = (ask_range / bid_ask_midpoint).rename("ask_range_ratio")
    stats_srs_list.append(ask_range_ratio)
    ask_stochastic = (
        (2 * df["ask"] - df["ask_high"] - df["ask_low"]) / ask_range
    ).rename("ask_stochastic")
    stats_srs_list.append(ask_stochastic)
    bid_range = (df["bid_high"] - df["bid_low"]).rename("bid_range")
    stats_srs_list.append(bid_range)
    bid_range_ratio = (bid_range / bid_ask_midpoint).rename("bid_range_ratio")
    stats_srs_list.append(bid_range_ratio)
    bid_stochastic = (
        (2 * df["bid"] - df["bid_high"] - df["bid_low"]) / bid_range
    ).rename("bid_stochastic")
    stats_srs_list.append(bid_stochastic)
    # Compute bid/ask range stats.
    bid_ask_outer_range = (df["ask_high"] - df["bid_low"]).rename(
        "bid_ask_outer_range"
    )
    stats_srs_list.append(bid_ask_outer_range)
    bid_ask_outer_range_ratio = (bid_ask_outer_range / bid_ask_midpoint).rename(
        "bid_ask_outer_range_ratio"
    )
    stats_srs_list.append(bid_ask_outer_range_ratio)
    bid_ask_inner_range = (df["ask_low"] - df["bid_high"]).rename(
        "bid_ask_inner_range"
    )
    stats_srs_list.append(bid_ask_inner_range)
    bid_ask_inner_range_ratio = (bid_ask_inner_range / bid_ask_midpoint).rename(
        "bid_ask_inner_range_ratio"
    )
    # Compute close execution cost.
    close_execution_spread_ratio = (
        # (bid + ask) / 2
        #
        (df["close"] - bid_ask_midpoint).abs()
        / bid_ask_spread_dollars
    ).rename("close_execution_spread_ratio")
    stats_srs_list.append(close_execution_spread_ratio)
    # Convert cents to bps.
    cent_to_midpoint_ratio = (0.01 / bid_ask_midpoint).rename(
        "cent_to_midpoint_ratio"
    )
    stats_srs_list.append(cent_to_midpoint_ratio)
    # Put stats in a dataframe.
    stats_srs_list.append(bid_ask_inner_range_ratio)
    stats = pd.concat(stats_srs_list, axis=1)
    return stats
