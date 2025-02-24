"""
Import as:

import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
"""
import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import im_v2.common.universe.universe_utils as imvcuunut
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.broker.replayed_data_reader as obredare

_LOG = logging.getLogger(__name__)


# #############################################################################
# CCXT order response processing
# #############################################################################


def aggregate_ccxt_orders_by_bar(
    df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    """
    Summarize ccxt order responses by bar and instrument.

    :param df: result of `load_ccxt_order_response_df()`
    :param freq: bar duration as a string, e.g, `"5T"`
    :return: DataFrame with 2 col levels, with various order stats
        organized by asset and by bar (a timestamp index)
    """
    df = df.set_index("order")
    df["bar_start_datetime"] = df["order_update_datetime"].dt.floor(freq)
    df["bar_end_datetime"] = df["order_update_datetime"].dt.ceil(freq)
    # Convert CCXT full symbol to full symbol format.
    # There are 2 CCXT symbol formats, e.g.'GMT/USDT:USDT' for futures
    # and 'GMT/USDT' for spot trades and older versions of CCXT.
    df["full_symbol"] = df["symbol"].apply(lambda x: x.split(":")[0])
    df["full_symbol"] = (
        "binance" + "::" + df["full_symbol"].apply(lambda x: x.replace("/", "_"))
    )
    # Convert resulting full symbols to asset ids.
    df_symbols = df["full_symbol"].unique()
    asset_id_to_full_symbol = imvcuunut.build_numerical_to_string_id_mapping(
        df_symbols
    )
    full_symbol_to_asset_id = {v: k for k, v in asset_id_to_full_symbol.items()}
    df["asset_id"] = df["full_symbol"].apply(lambda x: full_symbol_to_asset_id[x])
    #
    buy_orders = df[df["side"] == "buy"]
    sell_orders = df[df["side"] == "sell"]
    #
    buy_orders["buy_notional"] = (
        buy_orders["order_amount"] * buy_orders["order_price"]
    )
    sell_orders["sell_notional"] = (
        sell_orders["order_amount"] * sell_orders["order_price"]
    )
    #
    buy_groupby = buy_orders.groupby(["bar_end_datetime", "asset_id"])
    sell_groupby = sell_orders.groupby(["bar_end_datetime", "asset_id"])
    #
    buy_order_count = (
        buy_groupby["client_order_id"]
        .count()
        .unstack()
        .fillna(0)
        .astype(np.int64)
    )
    sell_order_count = (
        sell_groupby["client_order_id"]
        .count()
        .unstack()
        .fillna(0)
        .astype(np.int64)
    )
    order_count = buy_order_count.add(sell_order_count, fill_value=0)
    #
    buy_limit_twap = buy_groupby["order_price"].mean().unstack()
    sell_limit_twap = sell_groupby["order_price"].mean().unstack()
    #
    buy_amount = buy_groupby["order_amount"].sum().unstack()
    sell_amount = sell_groupby["order_amount"].sum().abs().unstack()
    #
    buy_notional = buy_groupby["buy_notional"].sum().unstack()
    sell_notional = sell_groupby["sell_notional"].sum().unstack()
    #
    buy_limit_vwap = buy_notional / buy_amount
    sell_limit_vwap = sell_notional / sell_amount
    #
    out_df = {
        "order_count": order_count,
        "buy_order_count": buy_order_count,
        "buy_limit_twap": buy_limit_twap,
        "buy_limit_vwap": buy_limit_vwap,
        "buy_amount": buy_amount,
        "buy_notional": buy_notional,
        "sell_order_count": sell_order_count,
        "sell_limit_twap": sell_limit_twap,
        "sell_limit_vwap": sell_limit_vwap,
        "sell_amount": sell_amount,
        "sell_notional": sell_notional,
    }
    out_df = pd.concat(out_df, axis=1)
    # # Convert the integer columns.
    # # In cases of order side alternating by bar, concatenation results in
    # # NaN values on some of the bars.
    integer_cols = ["order_count", "buy_order_count", "sell_order_count"]
    for col in integer_cols:
        # Verify that the corresponding order count is present.
        # E.g. a buy_order_count can be absent if the CCXT orders
        # were only on the 'sell' side.
        if col in out_df.columns.get_level_values(0):
            out_df[col] = out_df[col].fillna(0).astype(np.int64)
    return out_df


def aggregate_child_limit_orders_by_bar(
    df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    """
    Summarize OMS child orders by bar and instrument.

    This is similar to `aggregate_ccxt_orders_by_bar()`, but it's a
    separate function due to different column name conventions and
    expected fields.

    :param df: result of `load_child_order_df()`
    :param freq: bar duration as a string, e.g, `"5T"`
    :return: DataFrame with 2 col levels, with various order stats
        organized by asset and by bar (a timestamp index)
    """
    # Don't modify the DataFrame.
    df = df.copy()
    #
    df["bar_start_datetime"] = df["start_timestamp"].dt.floor(freq)
    df["bar_end_datetime"] = df["start_timestamp"].dt.ceil(freq)
    #
    buy_orders = df[df["diff_num_shares"] > 0]
    sell_orders = df[df["diff_num_shares"] < 0]
    #
    buy_orders["buy_notional"] = (
        buy_orders["diff_num_shares"] * buy_orders["limit_price"]
    )
    sell_orders["sell_notional"] = (
        sell_orders["diff_num_shares"].abs() * sell_orders["limit_price"]
    )
    #
    buy_groupby = buy_orders.groupby(["bar_end_datetime", "asset_id"])
    sell_groupby = sell_orders.groupby(["bar_end_datetime", "asset_id"])
    #
    buy_order_count = (
        buy_groupby["creation_timestamp"]
        .count()
        .unstack()
        .fillna(0)
        .astype(np.int64)
    )
    sell_order_count = (
        sell_groupby["creation_timestamp"]
        .count()
        .unstack()
        .fillna(0)
        .astype(np.int64)
    )
    order_count = pd.concat([buy_order_count, sell_order_count], axis=1)
    #
    buy_limit_twap = buy_groupby["limit_price"].mean().unstack()
    sell_limit_twap = sell_groupby["limit_price"].mean().unstack()
    #
    buy_amount = buy_groupby["diff_num_shares"].sum().unstack()
    sell_amount = sell_groupby["diff_num_shares"].sum().abs().unstack()
    #
    buy_notional = buy_groupby["buy_notional"].sum().unstack()
    sell_notional = sell_groupby["sell_notional"].sum().unstack()
    #
    buy_limit_vwap = buy_notional / buy_amount
    sell_limit_vwap = sell_notional / sell_amount
    #
    out_df = {
        "order_count": order_count,
        "buy_order_count": buy_order_count,
        "buy_limit_twap": buy_limit_twap,
        "buy_limit_vwap": buy_limit_vwap,
        "buy_amount": buy_amount,
        "buy_notional": buy_notional,
        "sell_order_count": sell_order_count,
        "sell_limit_twap": sell_limit_twap,
        "sell_limit_vwap": sell_limit_vwap,
        "sell_amount": sell_amount,
        "sell_notional": sell_notional,
    }
    out_df = pd.concat(out_df, axis=1)
    return out_df


# #############################################################################
# Fill processing
# #############################################################################


def aggregate_fills_by_bar(
    df: pd.DataFrame,
    freq: str,
    *,
    offset: str = "0T",
    groupby_id_col: str = "asset_id",
) -> pd.DataFrame:
    """
    Aggregate a fills DataFrame by order id, then by bar at `freq`.

    :param df: a fills DataFrame as returned by
        `convert_fills_json_to_dataframe()`
    :param freq: bar frequency
    """
    hdbg.dassert_in(groupby_id_col, ["asset_id", "symbol"])
    df = aggregate_fills_by_order(df)
    df["bar_start_datetime"] = df["first_datetime"].dt.floor(freq) + pd.Timedelta(
        offset
    )
    df["bar_end_datetime"] = df["first_datetime"].dt.ceil(freq) + pd.Timedelta(
        offset
    )
    # If, for a given instruments, only buys or sells occur within any given
    #  bar, then a single aggregation makes sense. Otherwise, we need to
    #  explicitly separate buys and sells.
    aggregated = df.groupby(
        ["bar_end_datetime", groupby_id_col], group_keys=True
    ).apply(_aggregate_fills)
    return aggregated


def compute_buy_sell_prices_by_bar(
    df: pd.DataFrame,
    freq: str,
    *,
    offset: str = "0T",
    groupby_id_col: str = "asset_id",
) -> pd.DataFrame:
    """
    Compute buy/sell trade prices by symbol and bar.

    :param df: a fills DataFrame as returned by
        `convert_fills_json_to_dataframe()`
    :param freq: bar frequency
    :return: DataFrame indexed by bar end datetimes and multilevel
        columns; outer level consists of "buy_trade_price",
        "sell_trade_price", and inner level consists of symbols
    """
    hdbg.dassert_in(groupby_id_col, ["asset_id", "symbol"])
    df = aggregate_fills_by_order(df)
    df["bar_end_datetime"] = df["first_datetime"].dt.ceil(freq) + pd.Timedelta(
        offset
    )
    #
    buys = df[df["buy_count"] > 0]
    sells = df[df["sell_count"] > 0]
    hdbg.dassert(buys.index.intersection(sells.index).empty)
    bar_buys = buys.groupby(
        ["bar_end_datetime", groupby_id_col], group_keys=True
    ).apply(_aggregate_fills)
    bar_sells = sells.groupby(
        ["bar_end_datetime", groupby_id_col], group_keys=True
    ).apply(_aggregate_fills)
    dict_ = {
        "buy_trade_price": bar_buys.unstack()["price"],
        "sell_trade_price": bar_sells.unstack()["price"],
    }
    df_out = pd.concat(dict_, axis=1)
    return df_out


def aggregate_fills_by_order(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate a fills DataFrame by order id.

    :param df: a fills DataFrame as returned by
        `convert_fills_json_to_dataframe()`
    """
    aggregated = (
        df.set_index(["order", "id"])
        .groupby("order", group_keys=True)
        .apply(_aggregate_fills)
    )
    return aggregated


def _aggregate_fills(df: pd.DataFrame) -> pd.Series:
    # Extract first and last fill timestamps.
    first_timestamp = df["first_timestamp"].min()
    last_timestamp = df["last_timestamp"].max()
    # Extract first and last fill datetimes.
    first_datetime = df["first_datetime"].min()
    last_datetime = df["last_datetime"].max()
    # Get symbol.
    symbols = df["symbol"].unique()
    hdbg.dassert_eq(len(symbols), 1)
    symbol = symbols[0]
    #
    asset_ids = df["asset_id"].unique()
    hdbg.dassert_eq(len(asset_ids), 1)
    asset_id = asset_ids[0]
    # Accumulate buys and sells.
    buy_count = df["buy_count"].sum()
    sell_count = df["sell_count"].sum()
    # Accumulate taker/maker counts.
    taker_count = df["taker_count"].sum()
    maker_count = df["maker_count"].sum()
    # Accumulate buys and sells volumes.
    buy_volume = df["buy_volume"].sum()
    sell_volume = df["sell_volume"].sum()
    # Accumulate taker/maker volumes.
    taker_volume = df["taker_volume"].sum()
    maker_volume = df["maker_volume"].sum()
    # Accumulate buys and sells notional.
    buy_notional = df["buy_notional"].sum()
    sell_notional = df["sell_notional"].sum()
    # Accumulate taker/maker notional.
    taker_notional = df["taker_notional"].sum()
    maker_notional = df["maker_notional"].sum()
    # Accumulate share counts and costs.
    amount = df["amount"].sum()
    cost = df["cost"].sum()
    transaction_cost = df["transaction_cost"].sum()
    realized_pnl = df["realized_pnl"].sum()
    # Compute average price.
    price = cost / amount
    # Package the results and return.
    aggregated = pd.Series(
        {
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "first_datetime": first_datetime,
            "last_datetime": last_datetime,
            "symbol": symbol,
            "asset_id": asset_id,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "taker_count": taker_count,
            "maker_count": maker_count,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "taker_volume": taker_volume,
            "maker_volume": maker_volume,
            "buy_notional": buy_notional,
            "sell_notional": sell_notional,
            "taker_notional": taker_notional,
            "maker_notional": maker_notional,
            "price": price,
            "amount": amount,
            "cost": cost,
            "transaction_cost": transaction_cost,
            "realized_pnl": realized_pnl,
        }
    )
    return aggregated


def combine_sim_and_actual_trades(
    simulated_execution_df: pd.DataFrame,
    fills: pd.DataFrame,
    freq: str,
    offset: str,
) -> pd.DataFrame:
    """
    Combine simulated and actual trades.

    :param simulated_execution_df: simulated execution DataFrame
    :param fills: fills DataFrame
    :param freq: bar frequency
    :param offset: bar offset
    """
    actual_executed_trades_prices = compute_buy_sell_prices_by_bar(
        fills,
        freq,
        offset=offset,
        groupby_id_col="asset_id",
    )
    resampled_simulated_execution_df = simulated_execution_df.resample(
        freq,
        closed="right",
        label="right",
        offset=offset,
    ).mean()
    #
    col_set = actual_executed_trades_prices.columns.levels[1].union(
        resampled_simulated_execution_df.columns.levels[1]
    )
    col_set = col_set.sort_values()
    #
    trade_price_dict = {
        "actual_buy_trade_price": actual_executed_trades_prices[
            "buy_trade_price"
        ].reindex(columns=col_set),
        "actual_sell_trade_price": actual_executed_trades_prices[
            "sell_trade_price"
        ].reindex(columns=col_set),
        "simulated_buy_trade_price": resampled_simulated_execution_df[
            "buy_trade_price"
        ].reindex(columns=col_set),
        "simulated_sell_trade_price": resampled_simulated_execution_df[
            "sell_trade_price"
        ].reindex(columns=col_set),
    }
    simulated_and_actual_trade_price_df = pd.concat(trade_price_dict, axis=1)
    return simulated_and_actual_trade_price_df


# #############################################################################
# Load bid-ask data
# #############################################################################


def load_bid_ask_data(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    ccxt_log_reader: obcccclo.CcxtLogger,
    data_source: str,
    asset_ids: Optional[List[int]],
    child_order_execution_freq: str,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Load bid/ask data from the DB/S3 location.

    :param start_timestamp: start timestamp
    :param end_timestamp: end timestamp
    :param ccxt_log_reader: CCXT log reader
    :param data_source: source of the bid/ask data: S3 - archived data, "logged_during_experiment"
     - data logged before each wave (possible gaps in full system runs if there are no trades sent to
     broker during run), "logged_after_experiment" - data logged after experiment using
     `im_v2/ccxt/db/log_experiment_data.py`
    :param asset_ids: list of asset ids to load
    :param child_order_execution_freq: child order execution frequency
    :return: deduplicated bid/ask data, and a dataframe of duplicated
        data or None
    """
    hdbg.dassert_in(
        data_source, ["S3", "logged_during_experiment", "logged_after_experiment"]
    )
    # Load the input bid/ask data from the DB/ S3 location.
    # Commented out since we are using replayed data.
    # To be removed after the correctness of the replayed data is established.
    # if data_source == "S3":
    #     signature = "periodic_daily.airflow.archived_200ms.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
    #     reader = imvcdcimrdc.RawDataReader(signature, stage="preprod")
    # else:
    #     signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
    #     reader = imvcdcimrdc.RawDataReader(signature)
    # bid_ask = reader.read_data(start_timestamp, end_timestamp, bid_ask_levels=[1])
    bid_ask_files = ccxt_log_reader.load_bid_ask_files(
        load_data_for_full_period=data_source == "logged_after_experiment"
    )
    bid_ask_reader = obredare.ReplayDataReader(bid_ask_files)
    dataframes = []
    for file in bid_ask_files:
        df = bid_ask_reader._read_csv_file(file)
        dataframes.append(df)
    bid_ask = pd.concat(dataframes)
    hdbg.dassert(not bid_ask.empty, "Requested bid-ask data not available.")
    # Check bid/ask data for duplicates and drop if present.
    bid_ask, duplicates = obccccut.drop_bid_ask_duplicates(
        bid_ask, max_num_dups=None
    )
    currency_pair_to_full_symbol = {
        x: "binance::" + x for x in bid_ask["currency_pair"].unique()
    }
    asset_id_to_full_symbol = imvcuunut.build_numerical_to_string_id_mapping(
        currency_pair_to_full_symbol.values()
    )
    full_symbol_mapping_to_asset_id = {
        v: k for k, v in asset_id_to_full_symbol.items()
    }
    currency_pair_to_asset_id = {
        x: full_symbol_mapping_to_asset_id[currency_pair_to_full_symbol[x]]
        for x in bid_ask["currency_pair"].unique()
    }
    # Add asset_ids.
    bid_ask_asset_ids = bid_ask["currency_pair"].apply(
        lambda x: currency_pair_to_asset_id[x]
    )
    bid_ask["asset_id"] = bid_ask_asset_ids
    #
    if asset_ids is not None:
        bid_ask = bid_ask[bid_ask["asset_id"].isin(asset_ids)]
    #
    if data_source != "S3":
        asset_ids = bid_ask["asset_id"].unique()
        bid_ask_dfs = []
        for asset_id in asset_ids:
            asset_bid_ask = bid_ask[bid_ask["asset_id"] == asset_id].copy()
            asset_bid_ask.index = pd.to_datetime(
                1000000 * asset_bid_ask.index, utc=True
            )
            asset_bid_ask = asset_bid_ask[
                ["bid_price_l1", "ask_price_l1", "bid_size_l1", "ask_size_l1"]
            ].rename(
                columns={
                    "bid_price_l1": "bid_price",
                    "ask_price_l1": "ask_price",
                    "bid_size_l1": "bid_size",
                    "ask_size_l1": "ask_size",
                },
            )
            asset_bid_ask = pd.concat([asset_bid_ask], axis=1, keys=[asset_id])
            asset_bid_ask = (
                asset_bid_ask.resample("100ms").last().ffill(limit=100)
            )
            bid_ask_dfs.append(asset_bid_ask)
        bid_ask = pd.concat(bid_ask_dfs, axis=1)
        bid_ask = bid_ask.swaplevel(axis=1)
    else:
        raise NotImplementedError
    # Verify that the bid/ask data contains the start/end timestamp range.
    # A CCXT order can be processed during a child order execution wave,
    # after the input bid/ask data is logged, so we account for the child order wave duration.
    hdateti.dassert_timestamp_lte(bid_ask.index.min(), start_timestamp)
    child_order_execution_freq = pd.Timedelta(child_order_execution_freq)
    hdateti.dassert_timestamp_lte(
        end_timestamp, bid_ask.index.max() + child_order_execution_freq
    )
    return bid_ask, duplicates
