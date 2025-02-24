"""
Import as:

import oms.order.order_converter as oororcon
"""
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


# TODO(gp): -> _convert_single_asset_order_df_to_target_position_df
def convert_single_asset_order_df_to_target_position_df(
    order_df: pd.DataFrame,
    price_srs: pd.Series,
) -> pd.DataFrame:
    """
    Create a target_position_df for a single asset.

    :param order_df: an order dataframe for a single asset
    :param price_srs: reference prices for a single asset
    :return: a target position dataframe for a single asset
    """
    # Confirm that the order data is for a single asset.
    hdbg.dassert_eq(len(order_df["asset_id"].unique()), 1)
    #
    price_srs_freq = price_srs.index.freq
    hdbg.dassert(price_srs_freq is not None)
    # Extract holdings and shift index so that end-of-bar holdings are
    # reflected.
    holdings_shares = order_df.set_index("end_timestamp")["curr_num_shares"]
    holdings_shares = holdings_shares.resample(price_srs_freq).bfill()
    holdings_shares.index = holdings_shares.index.shift(-1)
    holdings_idx = holdings_shares.index
    # Multiply by end-of-bar price to get notional holdings.
    holdings_notional = holdings_shares.multiply(price_srs.loc[holdings_idx])
    # Extract target trades in shares and shift to end-of-bar semantics.
    target_trades_shares = order_df.set_index("end_timestamp")["diff_num_shares"]
    target_trades_shares = target_trades_shares.resample(price_srs_freq).sum()
    target_trades_shares.index = target_trades_shares.index.shift(-1)
    # Compute target notional trades.
    target_trades_shares_idx = target_trades_shares.index
    target_trades_notional = target_trades_shares.multiply(
        price_srs.loc[target_trades_shares_idx]
    )
    # Compute the target holdings in shares.
    target_holdings_shares = holdings_shares.add(
        target_trades_shares, fill_value=0
    )
    # Compute notional target holdings.
    target_holdings_idx = target_holdings_shares.index
    target_holdings_notional = target_holdings_shares.multiply(
        price_srs.loc[target_holdings_idx]
    )
    # Restrict price index to union of holdings and target_holdings indices.
    price_idx = holdings_idx.union(target_holdings_idx)
    target_position_df = pd.concat(
        {
            "holdings_shares": holdings_shares,
            "price": price_srs.loc[price_idx],
            "holdings_notional": holdings_notional,
            "target_holdings_notional": target_holdings_notional,
            "target_trades_notional": target_trades_notional,
            "target_trades_shares": target_trades_shares,
            "target_holdings_shares": target_holdings_shares,
        },
        axis=1,
    )
    return target_position_df


# TODO(gp): Add an example of order_df and a target position df.
def convert_order_df_to_target_position_df(
    order_df: pd.DataFrame,
    price_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a target position dataframe from an orders dataframe.

    :param order_df: an order dataframe (bar-level)
    :param price_df: a bar reference price (e.g., TWAP or VWAP)
    :return: a target position-style dataframe
    """
    cols = [
        "asset_id",
        "curr_num_shares",
        "diff_num_shares",
    ]
    hdbg.dassert_is_subset(cols, order_df.columns)
    hpandas.dassert_time_indexed_df(
        price_df, allow_empty=False, strictly_increasing=True
    )
    price_df_freq = price_df.index.freq
    hdbg.dassert_is_not(price_df_freq, None)
    asset_ids = order_df["asset_id"].unique()
    asset_id_to_target_position_df = {}
    for asset_id in asset_ids:
        asset_target_position_df = (
            convert_single_asset_order_df_to_target_position_df(
                order_df[order_df["asset_id"] == asset_id],
                price_df[asset_id],
            )
        )
        asset_id_to_target_position_df[asset_id] = asset_target_position_df
    target_position_df = pd.concat(asset_id_to_target_position_df, axis=1)
    target_position_df = target_position_df.swaplevel(axis=1).sort_index(axis=1)
    return target_position_df
