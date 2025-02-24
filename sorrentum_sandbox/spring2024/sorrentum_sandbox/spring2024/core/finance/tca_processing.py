"""
Import as:

import core.finance.tca_processing as cfitcproc
"""
import logging

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


def load_and_normalize_tca_csv(file_name: str) -> pd.DataFrame:
    """
    Load csv as df and normalize datetime columns.
    """
    hdbg.dassert_file_exists(file_name)
    df = pd.read_csv(file_name)
    _LOG.info(
        "csv to df=%s",
        hpandas.df_to_str(
            df, print_dtypes=True, print_shape_info=True, log_level=logging.INFO
        ),
    )
    time_cols = [
        "start_time",
        "desired_end_time",
        "effective_end_time",
        "order_arrival_time",
    ]
    hdbg.dassert_is_subset(time_cols, df.columns)
    for time_col in time_cols:
        idx = (
            pd.DatetimeIndex(df[time_col])
            .tz_localize("UTC")
            .tz_convert("America/New_York")
        )
        srs = idx.to_series().reset_index(drop=True)
        df[time_col] = srs
    _LOG.info(
        "df after datetime conversion=%s",
        hpandas.df_to_str(
            df, print_dtypes=True, print_shape_info=True, log_level=logging.INFO
        ),
    )
    return df


def extract_executed_shares_and_notional(
    df: pd.DataFrame,
    asset_id_col: str,
) -> pd.DataFrame:
    """
    Extract the executed shares and notional as a multiindexed dataframe.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    required_cols = [
        "cum_filled_qty",
        "cum_filled_notional",
        "desired_end_time",
        "side",
        asset_id_col,
    ]
    hdbg.dassert_is_subset(required_cols, df.columns)
    df = df[required_cols]
    # Perform column renamings.
    df = df.rename(
        columns={
            "executed_trades_shares": "cum_filled_qty",
            "executed_trades_notional": "cum_filled_notional",
        }
    )
    # Encode the side in the trades.
    side_as_int = (
        np.sign((df["side"] == "BUY").astype(int) - 0.5)
        .astype(int)
        .rename("side_as_int")
    )
    df = df.drop(["side"], axis=1)
    df["executed_trades_shares"] = df["executed_trades_shares"] * side_as_int
    df["executed_trades_notional"] = df["executed_trades_notional"] * side_as_int
    # Pivot.
    df = df.pivot(index="desired_end_time", columns=asset_id_col)
    df.index.name = None
    df.columns.names = (None, None)
    return df


def compute_tca_price_annotations(
    df: pd.DataFrame,
    join_output_with_input: bool = False,
) -> pd.DataFrame:
    """
    Compute average fill price, interval vwap, and related quantities.
    """
    series_list = []
    # Compute average fill price.
    notional_filled = df["cum_filled_notional"]
    quantity_filled = df["cum_filled_qty"]
    average_fill_price = (notional_filled / quantity_filled).rename(
        "average_fill_price"
    )
    series_list.append(average_fill_price)
    # Compute interval vwap.
    interval_notional = df["mkt_traded_notional_new_order_to_event"]
    interval_quantity = df["mkt_traded_shares_new_order_to_event"]
    interval_vwap = (interval_notional / interval_quantity).rename(
        "interval_vwap"
    )
    series_list.append(interval_vwap)
    # Encode side as +/- 1.
    side_as_int = (
        np.sign((df["side"] == "BUY").astype(int) - 0.5)
        .astype(int)
        .rename("side_as_int")
    )
    series_list.append(side_as_int)
    # Compute slippage.
    slippage = (average_fill_price - interval_vwap) / interval_vwap
    slippage = 1e4 * (slippage * side_as_int).rename("slippage_in_bps")
    series_list.append(slippage)
    # Compute notional inflow/outflow.
    flow = (-side_as_int * notional_filled).rename("flow")
    series_list.append(flow)
    # Concat and return.
    new_df = pd.concat(series_list, axis=1)
    if join_output_with_input:
        new_df = pd.concat([df, new_df], axis=1)
    return new_df


def pivot_and_accumulate_holdings(
    df: pd.DataFrame,
    asset_id_col: str,
) -> pd.DataFrame:
    """
    Pivot asset id to col level and accumulate holdings from fills.
    """
    hdbg.dassert_in(asset_id_col, df.columns)
    hdbg.dassert_in("desired_end_time", df.columns)
    df = df.pivot(index="desired_end_time", columns=asset_id_col)
    # Impute zero for NaN flow.
    df["flow"] = df["flow"].fillna(0)
    # Compute holdings assuming initial are zero.
    signed_fill = df["cum_filled_qty"] * df["side_as_int"]
    holdings = signed_fill.cumsum().ffill().fillna(0)
    holdings = pd.concat([holdings], axis=1, keys=["holdings"])
    df = pd.concat([df, holdings], axis=1)
    # df = df.swaplevel(axis=1)
    # df.sort_index(inplace=True, axis=1)
    return df
