"""
Import as:

import core.finance.holdings as cfinhold
"""
import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

import core.finance.bar_processing as cfibapro
import core.finance.share_quantization as cfishqua
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def quantize_holdings(
    holdings: pd.DataFrame,
    quantization: Optional[int],
    *,
    asset_id_to_decimals: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Keep factional holdings or round to the nearest share or lot.
    """
    # Perform sanity-checks.
    hpandas.dassert_time_indexed_df(
        holdings, allow_empty=True, strictly_increasing=True
    )
    quantized_holdings = cfishqua.quantize_shares(
        holdings,
        quantization,
        asset_id_to_decimals=asset_id_to_decimals,
    )
    return quantized_holdings


def adjust_holdings_for_overnight(
    holdings: pd.DataFrame,
    price: pd.DataFrame,
    liquidate_at_end_of_day: bool,
    adjust_for_splits: bool,
    ffill_limit: int,
) -> pd.DataFrame:
    """
    Adjust holdings for end-of-day liquidation or splits.

    :param holdings: holdings (in shares) indexed by end-of-bar timestamp
    :param price: end-of-bar mark-to-market price
    :param liquidate_at_end_of_day: liquidate at EOD iff `True`
    :param adjust_for_splits: adjust overnight holdings for share splits;
        applies to beginning-of-day positions only
    :param ffill_limit: limit on forward-filling holdings (e.g., useful
        if a bar is missing a mark-to-market price)
    :return: dataframe of share holdings (endtime-indexed)
    """
    hpandas.dassert_time_indexed_df(
        holdings, allow_empty=True, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        price, allow_empty=True, strictly_increasing=True
    )
    hpandas.dassert_axes_equal(holdings, price)
    # Determine beginning-of-day and possibly end-of-day timestamps.
    timestamps = pd.DataFrame(
        price.index.to_list(),
        price.index,
        ["timestamp"],
    )
    bod_timestamps = timestamps.groupby(lambda x: x.date()).min()
    if liquidate_at_end_of_day:
        eod_timestamps = timestamps.groupby(lambda x: x.date()).max()
        holdings.loc[eod_timestamps["timestamp"], :] = 0.0
        holdings.loc[bod_timestamps["timestamp"], :] *= 0
    elif adjust_for_splits:
        # TODO(Paul): Give the user the option of supplying the share
        #  adjustment factors. Infer as below if they are not supplied.
        split_factors = cfibapro.infer_splits(price)
        splits = split_factors.merge(
            bod_timestamps, left_index=True, right_index=True
        ).set_index("timestamp")
        eod_holdings = cfibapro.retrieve_end_of_day_values(holdings)
        bod_holdings = (
            eod_holdings.shift(1)
            .merge(bod_timestamps, left_index=True, right_index=True)
            .set_index("timestamp")
            .multiply(splits)
        )
        # Set beginning-of-day holdings.
        holdings.loc[bod_timestamps["timestamp"], :] = bod_holdings
    else:
        pass
    if ffill_limit > 0:
        holdings = holdings.groupby(lambda x: x.date()).ffill(limit=ffill_limit)
    return holdings


def adjust_holdings_for_underfills(
    holdings: pd.DataFrame,
    mark_to_market_price: pd.DataFrame,
    buy_price: pd.DataFrame,
    sell_price: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adapt holdings by taking into account underfills.
    """
    # Perform sanity-checks.
    dfs = [holdings, mark_to_market_price, buy_price, sell_price]
    for df in dfs:
        hpandas.dassert_time_indexed_df(
            df, allow_empty=True, strictly_increasing=True
        )
        hpandas.dassert_axes_equal(df, holdings)
    # Use mark to market price at close.
    timestamps = pd.DataFrame(
        mark_to_market_price.index.to_list(),
        mark_to_market_price.index,
        ["timestamp"],
    )
    eod_timestamps = timestamps.groupby(lambda x: x.date()).max()
    # TODO(Paul): Factor out ffill_limit.
    ffill_limit = 2
    prices = mark_to_market_price.ffill(limit=ffill_limit)
    buy_price = buy_price.copy()
    buy_price.loc[eod_timestamps["timestamp"]] = prices.loc[
        eod_timestamps["timestamp"]
    ]
    sell_price = sell_price.copy()
    sell_price.loc[eod_timestamps["timestamp"]] = prices.loc[
        eod_timestamps["timestamp"]
    ]
    # Create filters to indicate where no buy price is available (leading
    # to underfills for buy orders) or no sell price is available (leading
    # to underfills for sell orders).
    no_buy_price = buy_price.isna()
    no_sell_price = sell_price.isna()
    # Create a copy of `holdings` to perform the adjustment.
    adjusted_holdings = holdings.copy()
    iteration_count = 1
    while True:
        _LOG.debug("Underfill adjustment iteration cycle=%d", iteration_count)
        # If we want to buy but no buy price is available, or we want to
        # sell and no sell price is available, then hold.
        force_hold = ((adjusted_holdings.diff() > 0) & no_buy_price) | (
            (adjusted_holdings.diff() < 0) & no_sell_price
        )
        if force_hold is None or (force_hold.sum().sum() == 0):
            _LOG.info(
                "Performed %d iterations of underfill adjustments",
                iteration_count - 1,
            )
            break
        # Impute NaN and forward fill to force holding. This is a heuristic
        # that should provide a reasonable approximation in many (not
        # necessarily all) scenarios.
        adjusted_holdings[force_hold.values] = np.nan
        adjusted_holdings.ffill(limit=1, inplace=True)
        adjusted_holdings = adjusted_holdings.combine_first(holdings)
        iteration_count += 1
        hdbg.dassert_lt(
            iteration_count,
            100,
            "Exceeded underfill adjustment iteration limit",
        )
    return adjusted_holdings
