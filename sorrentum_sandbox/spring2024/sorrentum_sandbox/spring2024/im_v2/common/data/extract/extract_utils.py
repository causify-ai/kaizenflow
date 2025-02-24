"""
Implement common exchange download operations.

Import as:

import im_v2.common.data.extract.extract_utils as imvcdeexut
"""

import argparse
import asyncio
import logging
import os
import re
import time
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional, Union

import pandas as pd

import data_schema.dataset_schema_utils as dsdascut
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hparquet as hparque
import helpers.hs3 as hs3
import helpers.htimer as htimer
import im_v2.ccxt.data.extract.cryptocom_extractor as imvcdecrex
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.data.extract.extractor as ivcdexex
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe as ivcu
from helpers.hthreading import timeout

_LOG = logging.getLogger(__name__)

SUPPORTED_DOWNLOAD_METHODS = ["rest", "websocket"]

# Provide parameters for handling websocket download.
#  - sleep_between_iter_in_ms: time to sleep between iterations in miliseconds.
#  - max_buffer_size: specifies number of websocket
#    messages to cache before attempting DB insert.
WEBSOCKET_CONFIG = {
    "ohlcv": {
        # Buffer size is 0 for OHLCV because we want to insert after round of
        # receival from websockets.
        "max_buffer_size": 0,
        "sleep_between_iter_in_ms": 60000,
        # How many consecutive iterations can happen for a given symbol
        # without receiving new data before resubscribing to the websocket feed.
        "resubscription_threshold_in_iter": 5,
    },
    "bid_ask": {
        "max_buffer_size": 250,
        "sleep_between_iter_in_ms": 200,
        "resubscription_threshold_in_iter": 3,
    },
    "trades": {
        "max_buffer_size": 0,
        "sleep_between_iter_in_ms": 200,
        "resubscription_threshold_in_iter": 3,
    },
    # This data_type is used when to build OHLCV data from trades.
    "ohlcv_from_trades": {
        "max_buffer_size": 0,
        "sleep_between_iter_in_ms": 200,
        "resubscription_threshold_in_iter": 3,
    },
}


def _add_common_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add command line arguments common to all downloaders.
    """
    parser.add_argument(
        "--download_mode",
        action="store",
        required=True,
        type=str,
        help="What type of download is this (e.g., 'periodic_daily')",
    )
    parser.add_argument(
        "--downloading_entity",
        action="store",
        required=True,
        type=str,
        help="Who is the executor (e.g. airflow, manual)",
    )
    parser.add_argument(
        "--action_tag",
        action="store",
        required=True,
        type=str,
        help="Capture the nature of the task and data (e.g. downloaded_1min)",
    )
    parser.add_argument(
        "--vendor",
        action="store",
        required=True,
        type=str,
        help="Vendor to use for downloading (e.g., 'ccxt')",
    )
    parser.add_argument(
        "--exchange_id",
        action="store",
        required=True,
        type=str,
        help="Name of exchange to download data from (e.g., 'binance')",
    )
    parser.add_argument(
        "--universe",
        action="store",
        required=True,
        type=str,
        help="Trading universe to download data for",
    )
    parser.add_argument(
        "--data_type",
        action="store",
        required=True,
        type=str,
        choices=["ohlcv", "bid_ask", "trades"],
        help="OHLCV, bid/ask or trades data.",
    )
    parser.add_argument(
        "--contract_type",
        action="store",
        required=True,
        type=str,
        help="Type of contract, spot, swap or futures",
    )
    parser.add_argument(
        "--bid_ask_depth",
        action="store",
        required=False,
        default=10,
        type=int,
        help="Specifies depth of order book to \
            download (applies when data_type=bid_ask).",
    )
    parser.add_argument(
        "--data_format",
        action="store",
        required=True,
        type=str,
        help="Format of the data (e.g. csv, parquet, postgres)",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        required=False,
        type=str,
        help="Path to the directory where the data will be \
            downloaded locally (e.g. '/User/Output').",
    )
    parser.add_argument(
        "--pq_save_mode",
        action="store",
        required=False,
        type=str,
        default="append",
        choices=["list_and_merge", "append"],
        help="mode used to save data into a parquet file",
    )
    parser.add_argument(
        "--universe_part",
        action="store",
        required=False,
        type=int,
        nargs=2,
        help="Pass two int argument x,y. Split universe into N chunks each contains X symbols. \
            groups of 10 pairs, 'y' denotes which part should be downloaded \
            (e.g. 10, 1 - download first 10 symbols)",
    )
    return parser


def add_exchange_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser = _add_common_download_args(parser)
    parser.add_argument(
        "--start_timestamp",
        required=False,
        action="store",
        type=str,
        help="Beginning of the downloaded period",
    )
    parser.add_argument(
        "--end_timestamp",
        action="store",
        required=False,
        type=str,
        help="End of the downloaded period",
    )
    # Deprecated in CmTask5432.
    # parser.add_argument(
    #     "--incremental",
    #     action="store_true",
    #     required=False,
    #     help="Append data instead of overwriting it",
    # )
    return parser


def add_periodical_download_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options exchange download.
    """
    parser = _add_common_download_args(parser)
    parser.add_argument(
        "--start_time",
        action="store",
        required=True,
        type=str,
        help="Timestamp when the download should start (e.g., '2022-05-03 00:40:00')",
    )
    parser.add_argument(
        "--stop_time",
        action="store",
        required=True,
        type=str,
        help="Timestamp when the script should stop (e.g., '2022-05-03 00:30:00')",
    )
    parser.add_argument(
        "--method",
        action="store",
        required=True,
        type=str,
        choices=SUPPORTED_DOWNLOAD_METHODS,
        help="Method used to download the data: rest (for HTTP REST based download), or websocket",
    )
    parser.add_argument(
        "--interval_min",
        type=int,
        help="Interval between download attempts, in minutes (applicable for --method=rest)",
    )
    return parser


# Time limit for each download execution.
TIMEOUT_SEC = 60

# Define the validation schema of the data.
DATASET_SCHEMA = {
    # TODO(Juraj): bid_ask and ohlcv contain each other's columns as well,
    #  needs cleanup:
    "bid_ask": {
        "bid_ask_midpoint": "float64",
        "half_spread": "float64",
        "log_size_imbalance": "float64",
        "bid_ask_midpoint_var": "float",
        "ask_price": "float64",
        "ask_size": "float64",
        "bid_price": "float64",
        "bid_size": "float64",
        "close": "float64",
        "currency_pair": "object",
        "end_download_timestamp": "datetime64[ns, UTC]",
        "exchange_id": "object",
        "high": "float64",
        "knowledge_timestamp": "datetime64[ns, UTC]",
        "level": "int32",
        "low": "float64",
        "month": "int32",
        "number_of_trades": "int32",
        "open": "float64",
        "timestamp": "int64",
        "twap": "float64",
        "volume": "float64",
        "vwap": "float64",
        "year": "int32",
        "day": "int32",
    },
    "ohlcv": {
        "ask_price": "float64",
        "ask_size": "float64",
        "bid_price": "float64",
        "bid_size": "float64",
        "close": "float64",
        "currency_pair": "object",
        "end_download_timestamp": "datetime64[ns, UTC]",
        "exchange_id": "object",
        "high": "float64",
        "knowledge_timestamp": "datetime64[ns, UTC]",
        "level": "int32",
        "low": "float64",
        "month": "int32",
        "number_of_trades": "int32",
        "open": "float64",
        "timestamp": "int64",
        "twap": "float64",
        "volume": "float64",
        "vwap": "float64",
        "year": "int32",
        "day": "int32",
    },
    "trades": {
        "currency_pair": "object",
        "symbol": "object",
        "end_download_timestamp": "datetime64[ns, UTC]",
        "exchange_id": "object",
        "is_buyer_maker": "int32",
        "is_buyer_maker": "bool",
        "knowledge_timestamp": "datetime64[ns, UTC]",
        "month": "int32",
        "price": "float64",
        "amount": "float64",
        "size": "float64",
        "timestamp": "int64",
        "year": "int32",
        "day": "int32",
        "id": "int64",
        "quote_qty": "float64",
    },
}


def download_exchange_data_to_db(
    args: Dict[str, Any], exchange: ivcdexex.Extractor
) -> None:
    """
    Encapsulate common logic for downloading exchange data.

    :param args: arguments passed on script run
    :param exchange: which exchange is used in script run
    """
    # Load currency pairs.
    mode = "download"
    universe = ivcu.get_vendor_universe(
        exchange.vendor, mode, version=args["universe"]
    )
    currency_pairs = universe[args["exchange_id"]]
    # Connect to database.
    db_connection = imvcddbut.DbConnectionManager.get_connection(args["db_stage"])
    # Load DB table to save data to.
    db_table = args["db_table"]
    data_type = args["data_type"]
    exchange_id = args["exchange_id"]
    bid_ask_depth = args.get("bid_ask_depth")
    if data_type in ("ohlcv", "bid_ask", "trades"):
        # Convert timestamps.
        start_timestamp = pd.Timestamp(args["start_timestamp"])
        start_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
            start_timestamp
        )
        end_timestamp = pd.Timestamp(args["end_timestamp"])
        end_timestamp_as_unix = hdateti.convert_timestamp_to_unix_epoch(
            end_timestamp
        )
    else:
        raise ValueError(
            "Downloading for %s data_type is not implemented.", data_type
        )
    # Download data for specified time period.
    for currency_pair in currency_pairs:
        # Download data.
        #  Note: timestamp arguments are ignored since historical data is absent
        #  from CCXT and only current state can be downloaded.
        data = exchange.download_data(
            data_type=data_type,
            currency_pair=currency_pair,
            exchange_id=exchange_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            depth=bid_ask_depth,
        )
        # Assign pair and exchange columns.
        data["currency_pair"] = currency_pair
        data["exchange_id"] = exchange_id
        # Add exchange specific filter.
        if data_type == "ohlcv" and exchange_id == "binance":
            data = imvcdttrut.remove_unfinished_ohlcv_bars(data)
        # Save data to the database.
        imvcddbut.save_data_to_db(
            data, data_type, db_connection, db_table, str(start_timestamp.tz)
        )


@timeout(TIMEOUT_SEC)
def _download_exchange_data_to_db_with_timeout(
    args: Dict[str, Any],
    exchange_class: ivcdexex.Extractor,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> None:
    """
    Wrapper for download_exchange_data_to_db. Download data for given time
    range, raise Interrupt in case if timeout occurred.

    :param args: arguments passed on script run
    :param start_timestamp: beginning of the downloaded period
    :param end_timestamp: end of the downloaded period
    """
    args["start_timestamp"], args["end_timestamp"] = (
        start_timestamp,
        end_timestamp,
    )
    _LOG.info(
        "Starting data download from: %s, till: %s",
        start_timestamp,
        end_timestamp,
    )
    download_exchange_data_to_db(args, exchange_class)


def _should_add_timestamp(
    timestamp: int, currency_pair: str, timestamps_dict: Dict[str, Any]
) -> bool:
    """
    Determine if a timestamp should be added to the timestamps dictionary.

    :param timestamp: Timestamp of the OHLCV data point
    :param currency_pair: Currency pair of the data_point
    :param timestamps_dict: Dictionary to store the latest_downloaded
        timestamp for the currency_pair.
    :return: True if timestamp is new or missed before, False otherwise.
    """
    # Backfill timestamps which got missed due to delay from Binance.
    is_missed_timestamp = (
        timestamp
        not in timestamps_dict[currency_pair]["all_downloaded_timestamp"]
        and timestamp
        < timestamps_dict[currency_pair]["latest_downloaded_timestamp"]
    )
    if is_missed_timestamp:
        _LOG.info(
            "Backfilling Missing timestamp=%s for currency_pair=%s",
            timestamp,
            currency_pair,
        )
    # The timestamp is added if it is missed or it is the latest timestamp.
    return (
        is_missed_timestamp
        or timestamps_dict[currency_pair]["latest_downloaded_timestamp"]
        < timestamp
    )


def _is_fresh_data_point(
    currency_pair: str,
    data_point: Dict[Any, Any],
    data_type: str,
    timestamps_dict: Dict[str, Any],
    start_time_unix_epoch: int,
) -> Union[bool, Dict]:
    """
    Check if a data point is valid based on its current timestamp and the
    already downloaded latest timestamp. This function has a side effect of
    updating timestamps_dict with the latest timestamp.

    This function has another side_effect of updating data_point for
    data_type == "ohlcv", this is needed because we want to filter out
    some data in the data_point.

    This function rejects the data point if it is None. For "bid_ask"
    data type, it additionally rejects the data point if the timestamp
    is None or if both the bid and ask sizes in the data point are zero.

    :param currency_pair: currency_pair of the data_point needs to be
        validated
    :param data_point: downloaded data from the exchange
    :param data_type: "bid_ask" or "OHLCV"
    :param timestamps_dict: dict to store the latest_downloaded
        timestamp for the currency_pair
    """
    if data_point is None:
        return False, timestamps_dict, data_point
    if data_type == "trades":
        return True, timestamps_dict, data_point
    if data_type == "bid_ask":
        if data_point["timestamp"] is None or (
            len(data_point["bids"]) == 0 and len(data_point["asks"]) == 0
        ):
            return False, timestamps_dict, data_point
        latest_download_timestamp = data_point["timestamp"]
        if (
            currency_pair not in timestamps_dict
            or timestamps_dict[currency_pair] < latest_download_timestamp
        ):
            timestamps_dict[currency_pair] = latest_download_timestamp
            return True, timestamps_dict, data_point
    elif data_type == "ohlcv":
        # Example format of an OHLCV data point:
        # data_point["ohlcv"] = [
        #    [1695120600000, 1645.08, 1645.23, 1643.83, 1643.97, 1584.69],
        #    [1695120600000, 1646.08, 1641.23, 1643.31, 1643.57, 1584.59],
        #    [1695120601000, 1648.08, 1643.23, 1643.84, 1643.67, 1584.49]
        # ]
        # Handle potential unfinished cases in OHLCV data, where we may receive
        # incomplete data in one iteration and then complete one in the next
        # iteration. So, check the `end_download_timestamp` value and compare
        # it with all previous values. Keep only those values which are not already
        # added in db (check using timestamp dict) and they have download timestamp
        # greater than 1 minute (60000ms) than the timestamp.
        new_data_point = deepcopy(data_point)
        new_data_point["ohlcv"] = []
        end_download_timestamp = pd.Timestamp(
            data_point["end_download_timestamp"]
        )
        end_download_timestamp_unix = hdateti.convert_timestamp_to_unix_epoch(
            end_download_timestamp
        )
        # Set the limit for the number of data points to ingest.
        ingestion_limit = 10
        # Initialize `timestamps_dict`.
        if currency_pair not in timestamps_dict:
            timestamps_dict[currency_pair] = {}
            timestamps_dict[currency_pair]["latest_downloaded_timestamp"] = -1
            timestamps_dict[currency_pair]["all_downloaded_timestamp"] = []
        for ohlcv_data in data_point["ohlcv"][-ingestion_limit:]:
            timestamp = ohlcv_data[0]
            # Check download timestamp greater than 1 minute (60000ms) than the timestamp.
            if timestamp + 60000 <= end_download_timestamp_unix:
                if _should_add_timestamp(
                    timestamp, currency_pair, timestamps_dict
                ):
                    new_data_point["ohlcv"].append(ohlcv_data)
                    timestamps_dict[currency_pair][
                        "latest_downloaded_timestamp"
                    ] = timestamp
                    timestamps_dict[currency_pair][
                        "all_downloaded_timestamp"
                    ].append(timestamp)
                    if (
                        len(
                            timestamps_dict[currency_pair][
                                "all_downloaded_timestamp"
                            ]
                        )
                        > ingestion_limit
                    ):
                        # Remove older timestamps to preserve the length.
                        timestamps_dict[currency_pair]["all_downloaded_timestamp"].pop(0)
        if len(new_data_point["ohlcv"]) > 0:
            return True, timestamps_dict, new_data_point
    elif data_type == "ohlcv_from_trades":
        # Example format of an ohlcv_trades data_point
        # data_point = { "ohlcv" : [
        #                           [1695120600000, 1645.08, 1645.23, 1643.83, 1643.97, 1584.69, 100],
        #                           [1695120660000, 1648.08, 1643.23, 1643.84, 1643.67, 1584.49, 120]
        #                          ],
        #                 "trades_endtimestamp" : 1695120659800,
        #                 "currency_pair" : "BTC_USD",
        #               }
        # Building OHLCV bars from trades data. Only keeping OHLCV bars not already stored in the database.
        # This is checked via timestamps dict. Ensuring complete OHLCV bars by verifying if the latest trades timestamp
        # is greater than 1 minute for that bar to be valid.
        # new_data_point = { "ohlcv" : [
        #                           [1695120600000, 1645.08, 1645.23, 1643.83, 1643.97, 1584.69],
        #                          ],
        #                 "trades_endtimestamp" : 1695120659800,
        #                 "currency_pair" : "BTC_USD",
        #               }
        new_data_point = deepcopy(data_point)
        new_data_point["ohlcv"] = []
        for ohlcv_data in data_point["ohlcv"]:
            timestamp = ohlcv_data[0]
            is_valid = start_time_unix_epoch <= timestamp
            if (
                is_valid
                and (
                    currency_pair not in timestamps_dict
                    or timestamps_dict[currency_pair] < timestamp
                )
                and data_point["trades_endtimestamp"] >= timestamp + 60000
            ):
                timestamps_dict[currency_pair] = timestamp
                # Remove the number of trades in that bar info.
                new_data_point["ohlcv"].append(ohlcv_data[:-1])
        if len(new_data_point["ohlcv"]) > 0:
            return True, timestamps_dict, new_data_point
    else:
        raise ValueError(f"Invalid data_type {data_type}")
    return False, timestamps_dict, data_point


async def _subscribe_to_websocket_data(
    args: Dict[str, Any],
    exchange: ivcdexex.Extractor,
    currency_pairs: List[str],
    bid_ask_depth: int,
    *,
    tz="UTC",
):
    """
    Subscribe to WebSocket data for the specified exchange, data type, and
    currency pairs.

    :param args: arguments passed on script run
    :param currency_pair: List of symbols to subscribe
    :param bid_ask_depth: how many levels of order book to download
    """
    data_type = args["data_type"]
    vendor = args["vendor"]
    exchange_id = args["exchange_id"]
    # Multiple symbols subscription is only supported by vendor CCXT.
    use_concurrent = False
    # Multiple symbols methods on error block the system for 6-9mins,
    # refer. ccxt/ccxt/issues/20911.
    # Tokyo region seems to be working fine with multiple symbols but Stockholm was
    # facing ping-pong inactive errors ref. cryptokaizen/cmamp/issues/7322.
    if (
        vendor == "ccxt"
        and args.get("watch_multiple_symbols", False)
        and data_type == "bid_ask"
    ):
        # Check if the exchange supports multiple symbols subscription.
        use_concurrent = exchange._async_exchange.describe()["has"].get(
            "watchOrderBookForSymbols", False
        )
    # Binance extractor supports multiple subscription for all the data types.
    if vendor == "binance":
        use_concurrent = True
    if use_concurrent:
        await exchange.subscribe_to_websocket_data_multiple_symbols(
            data_type, exchange, currency_pairs, bid_ask_depth=bid_ask_depth
        )
    else:
        subscribe_tasks = []
        for currency_pair in currency_pairs:
            task = exchange.subscribe_to_websocket_data(
                data_type,
                exchange_id,
                currency_pair,
                since=hdateti.convert_timestamp_to_unix_epoch(
                    pd.Timestamp.now(tz)
                ),
                # The following arguments are only applied for
                # the corresponding data type
                bid_ask_depth=bid_ask_depth,
            )
            subscribe_tasks.append(task)
        await asyncio.gather(*subscribe_tasks)


# TODO(Juraj): refactor names to get rid of "_for_one_exchange" part of the
#  functions' names since it spreads across the codebase. Docstring and the
#  method signature should sufficiently explain what the function does.
async def _download_websocket_realtime_for_one_exchange_periodically(
    args: Dict[str, Any], exchange: ivcdexex.Extractor
) -> None:
    """
    Encapsulate common logic for periodical exchange data download using
    websocket based download.

    :param args: arguments passed on script run
    :param exchange: name of exchange used in script run
    """
    data_type = args["data_type"]
    # Time related arguments.
    start_time = pd.Timestamp(args["start_time"])
    stop_time = pd.Timestamp(args["stop_time"])
    tz = start_time.tz
    # Data related arguments
    universe = ivcu.get_vendor_universe(
        exchange.vendor, mode="download", version=args["universe"]
    )
    exchange_id = args["exchange_id"]
    currency_pairs = universe[exchange_id]
    if args.get("universe_part"):
        currency_pairs = _split_universe(
            currency_pairs, args["universe_part"][0], args["universe_part"][1]
        )
    await _subscribe_to_websocket_data(
        args,
        exchange,
        currency_pairs,
        bid_ask_depth=args.get("bid_ask_depth"),
        tz=tz,
    )
    _LOG.info("Subscribed to %s websocket data successfully", exchange_id)
    db_connection = imvcddbut.DbConnectionManager.get_connection(args["db_stage"])
    db_table = args["db_table"]
    # In order not to bombard the database with many small insert operations
    # a buffer is created, its size is determined by the config specific to each
    # data type.
    data_buffer = []
    data_buffer_to_resample: List[pd.DataFrame] = []
    # Sync to the specified start_time.
    start_delay = max(0, ((start_time - datetime.now(tz)).total_seconds()))
    _LOG.info("Syncing with the start time, waiting for %s seconds", start_delay)
    # Exchange.sleep() method is needed instead of built in python time.sleep()
    #  to ensure websocket ping-pong messages are exchanged in a timely fashion.
    #  The method expects value in miliseconds.
    await exchange.sleep(start_delay * 1000)
    # Start data collection.
    timestamps_dict = {}
    # If bid/ask data is resampled alongside side raw data collection, the resampling is done exactly after
    # a given minutes ends.
    next_bid_ask_resampling_threshold = pd.Timestamp.now(tz).replace(
        second=0, microsecond=0
    ) + pd.Timedelta(minutes=1)
    start_time_unix_epoch = hdateti.convert_timestamp_to_unix_epoch(start_time)
    while pd.Timestamp.now(tz) < stop_time:
        if data_type == "bid_ask" and args.get("vendor") == "ccxt":
            try:
                await _subscribe_to_websocket_data(
                    args,
                    exchange,
                    currency_pairs,
                    bid_ask_depth=args.get("bid_ask_depth"),
                    tz=tz,
                )
            except Exception as e:
                _LOG.info("Subscription to symbols failed %s", e)
                # Handling potential issues: Sometimes the order book may fall out of sync,
                # leading to an error like "handleOrderBook received an out-of-order nonce".
                # Sleeping for 1 second to allow the system to catch up and get back in sync.
                # ref. https://github.com/ccxt/ccxt/issues/17827#issuecomment-1537532598
                await exchange.sleep(1000)
        iter_start_time = pd.Timestamp.now(tz)
        for curr_pair in currency_pairs:
            data_point = exchange.download_websocket_data(
                data_type, exchange_id, curr_pair
            )
            if data_type == "ohlcv_from_trades" and args.get("vendor") == "ccxt":
                since = (
                    timestamps_dict[curr_pair]
                    if curr_pair in timestamps_dict
                    else 0
                )
                # Building ohlcv every iteration because there is a limit on trades which we can store
                # as ccxt follows FIFO approach. This has been observed that building ohlcv every minute
                # adds an extra layer of complexity and corner cases which is unnecessary considering the
                # speed is already very fast. Still adding a todo for future improvements.
                # TODO(Sonaal): Build ohlcv every minute instead of every iteration.
                data_point["ohlcv"] = exchange.build_ohlcvc(
                    curr_pair, data_point["trades"], timeframe="1m", since=since
                )
                del data_point["trades"]
            # Check if the data point is not a duplicate one.
            is_fresh, timestamps_dict, data_point = _is_fresh_data_point(
                curr_pair,
                data_point,
                data_type,
                timestamps_dict,
                start_time_unix_epoch,
            )
            if is_fresh:
                data_buffer.append(data_point)
        download_time = (
            pd.Timestamp.now(tz) - iter_start_time
        ).total_seconds() * 1000
        # If the buffer is full or this is the last iteration, process and save buffered data.
        is_buffer_full = (
            len(data_buffer) >= WEBSOCKET_CONFIG[data_type]["max_buffer_size"]
        )
        is_last_iteration = pd.Timestamp.now(tz) >= stop_time
        is_non_empty_buffer = len(data_buffer) > 0
        # Save the data if the download was faster.
        is_download_fast = (
            download_time
            < WEBSOCKET_CONFIG[data_type]["sleep_between_iter_in_ms"] / 2
            and args["db_saving_mode"] == "on_sufficient_time"
        )
        if (
            is_buffer_full or is_last_iteration or is_download_fast
        ) and is_non_empty_buffer:
            df = imvcdttrut.transform_raw_websocket_data(
                data_buffer,
                data_type,
                exchange_id,
                max_num_levels=args.get("bid_ask_depth"),
            )
            # Store the names of currency pairs that were successfully downloaded
            # to log missing symbols every iteration.
            downloaded_currency_pairs = df["currency_pair"].unique().tolist()
            hdbg.dassert_set_eq(
                currency_pairs, downloaded_currency_pairs, only_warning=True
            )
            imvcddbut.save_data_to_db(
                df, data_type, db_connection, db_table, str(tz)
            )
            # Empty buffer after persisting the data.
            data_buffer = []
        # Determine actual sleep time needed based on the difference
        # between value set in config and actual time it took to complete
        # an iteration, this provides an "time align" mechanism.
        iter_length = (
            pd.Timestamp.now(tz) - iter_start_time
        ).total_seconds() * 1000
        actual_sleep_time = max(
            0,
            WEBSOCKET_CONFIG[data_type]["sleep_between_iter_in_ms"] - iter_length,
        )
        _LOG.info(
            "Iteration took %i ms, waiting between iterations for %i ms",
            iter_length,
            actual_sleep_time,
        )
        await exchange.sleep(actual_sleep_time)
    _LOG.info("Websocket download finished at %s", pd.Timestamp.now(tz))


def _download_rest_realtime_for_one_exchange_periodically(
    args: Dict[str, Any], exchange: ivcdexex.Extractor
) -> None:
    """
    Encapsulate common logic for periodical exchange data download using REST
    API based download.

    :param args: arguments passed on script run
    :param exchange: name of exchange used in script run
    """
    # Time range for each download.
    time_window_min = 5
    # Check values.
    start_time = pd.Timestamp(args["start_time"])
    stop_time = pd.Timestamp(args["stop_time"])
    interval_min = args["interval_min"]
    hdbg.dassert_lte(
        1, interval_min, "interval_min: %s should be greater than 0", interval_min
    )
    tz = start_time.tz
    # Error will be raised if we miss full 5 minute window of data,
    # even if the next download succeeds, we don't recover all of the previous data.
    num_failures = 0
    max_num_failures = (
        time_window_min // interval_min + time_window_min % interval_min
    )
    # Delay start.
    iteration_start_time = start_time
    iteration_delay_sec = (
        iteration_start_time - datetime.now(tz)
    ).total_seconds()
    while (
        datetime.now(tz) + timedelta(seconds=iteration_delay_sec) < stop_time
        and num_failures < max_num_failures
    ):
        # Wait until next download.
        _LOG.info("Delay %s sec until next iteration", iteration_delay_sec)
        time.sleep(iteration_delay_sec)
        start_timestamp = iteration_start_time - timedelta(
            minutes=time_window_min
        )
        # The floor function does a cosmetic change to the parameters
        # so the logs are completely clear.
        start_timestamp = start_timestamp.floor("min")
        end_timestamp = pd.to_datetime(datetime.now(tz)).floor("min")
        try:
            _download_exchange_data_to_db_with_timeout(
                args, exchange, start_timestamp, end_timestamp
            )
            # Reset failures counter.
            num_failures = 0
        except (KeyboardInterrupt, Exception) as e:
            num_failures += 1
            _LOG.error("Download failed %s", str(e))
            # Download failed.
            if num_failures >= max_num_failures:
                raise RuntimeError(
                    f"{max_num_failures} consecutive downloads were failed"
                ) from e
        # if the download took more than expected, we need to align on the grid.
        if datetime.now(tz) > iteration_start_time + timedelta(
            minutes=interval_min
        ):
            _LOG.error(
                "The download was not finished in %s minutes.", interval_min
            )
            _LOG.debug(
                "Initial start time before align `%s`.", iteration_start_time
            )
            iteration_delay_sec = 0
            # Download that will start after repeated one, should follow to the initial schedule.
            while datetime.now(tz) > iteration_start_time + timedelta(
                minutes=interval_min
            ):
                iteration_start_time = iteration_start_time + timedelta(
                    minutes=interval_min
                )
                _LOG.debug("Start time after align `%s`.", iteration_start_time)
        # If download failed, but there is time before next download.
        elif num_failures > 0:
            _LOG.info("Start repeat download immediately.")
            iteration_delay_sec = 0
        else:
            download_duration_sec = (
                datetime.now(tz) - iteration_start_time
            ).total_seconds()
            # Calculate delay before next download.
            iteration_delay_sec = (
                iteration_start_time
                + timedelta(minutes=interval_min)
                - datetime.now(tz)
            ).total_seconds()
            # Add interval in order to get next download time.
            iteration_start_time = iteration_start_time + timedelta(
                minutes=interval_min
            )
            _LOG.info(
                "Successfully completed, iteration took %s sec",
                download_duration_sec,
            )


def download_realtime_for_one_exchange_periodically(
    args: Dict[str, Any], exchange: ivcdexex.Extractor
) -> None:
    """
    Encapsulate common logic for periodical exchange data download via REST API
    or websocket.

    :param args: arguments passed on script run
    :param exchange: name of exchange used in script run
    """
    # Peform assertions common to all downloaders.
    start_time = pd.Timestamp(args["start_time"])
    stop_time = pd.Timestamp(args["stop_time"])
    hdateti.dassert_have_same_tz(start_time, stop_time)
    tz = start_time.tz
    hdbg.dassert_lt(datetime.now(tz), start_time, "start_time is in the past")
    hdbg.dassert_lt(start_time, stop_time, "stop_time is less than start_time")
    method = args["method"]
    if method == "rest":
        _download_rest_realtime_for_one_exchange_periodically(args, exchange)
    elif method == "websocket":
        # Websockets work asynchronously, in order this outer function synchronous
        # the websocket download needs go be executed using asyncio.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            _download_websocket_realtime_for_one_exchange_periodically(
                args, exchange
            )
        )
        loop.close()
    else:
        raise ValueError(
            f"Method: {method} is not a valid method for periodical download, "
            + f"supported methods are: {SUPPORTED_DOWNLOAD_METHODS}"
        )


def save_csv(
    data: pd.DataFrame,
    exchange_folder_path: str,
    currency_pair: str,
    # Deprecated in CmTask5432.
    # incremental: bool,
    aws_profile: Optional[str],
) -> None:
    """
    Save extracted data to .csv.gz.

    :param data: newly extracted data to save as .csv.gz file
    :param exchange_folder_path: path where to save the data
    :param currency_pair: currency pair, e.g. "BTC_USDT"
    :param incremental: update existing file instead of overwriting
    """
    full_target_path = os.path.join(
        exchange_folder_path, f"{currency_pair}.csv.gz"
    )
    # Deprecated in #CmTask5432
    # if incremental:
    hs3.dassert_path_exists(full_target_path, aws_profile)
    original_data = pd.read_csv(full_target_path)
    # Append new data and drop duplicates.
    hdbg.dassert_is_subset(data.columns, original_data.columns)
    data = data[original_data.columns.to_list()]
    data = pd.concat([original_data, data])
    # Drop duplicates on non-metadata columns.
    metadata_columns = ["end_download_timestamp", "knowledge_timestamp"]
    non_metadata_columns = data.drop(
        metadata_columns, axis=1, errors="ignore"
    ).columns.to_list()
    data = data.drop_duplicates(subset=non_metadata_columns)
    data.to_csv(full_target_path, index=False, compression="gzip")


def save_parquet(
    data: pd.DataFrame,
    path_to_dataset: str,
    unit: str,
    aws_profile: Optional[str],
    data_type: str,
    *,
    drop_columns: List[str] = ["end_download_timestamp"],
    mode: str = "list_and_merge",
    partition_mode: str = "by_year_month",
) -> None:
    """
    Save Parquet dataset.

    :param data: dataframe to save
    :param path_to_dataset: path to the dataset
    :param unit: unit of the data, e.g. "ms", "s", "m", "h", "D"
    :param aws_profile: AWS profile to use
    :param data_type: type of the data, e.g. "bid_ask"
    :param drop_columns: list of columns to drop
    :param mode: mode of saving, e.g. "list_and_merge", "append"
    :param partition_mode: partition mode, e.g. "by_year_month"
    """
    hdbg.dassert_in(mode, ["list_and_merge", "append"])
    # Update indexing and add partition columns.
    # TODO(Danya): Add `unit` as a parameter in the function.
    data = imvcdttrut.reindex_on_datetime(data, "timestamp", unit=unit)
    data, partition_cols = hparque.add_date_partition_columns(
        data, partition_mode
    )
    # Drop DB metadata columns.
    for column in drop_columns:
        data = data.drop(column, axis=1, errors="ignore")
    # Verify the schema of Dataframe.
    data = verify_schema(data, data_type)
    # Save filename as `uuid`, e.g.
    #  "16132792-79c2-4e96-a2a2-ac40a5fac9c7".
    hparque.to_partitioned_parquet(
        data,
        ["currency_pair"] + partition_cols,
        path_to_dataset,
        aws_profile=aws_profile,
    )
    # Merge all new parquet into a single `data.parquet`.
    if mode == "list_and_merge":
        hparque.list_and_merge_pq_files(
            path_to_dataset,
            aws_profile=aws_profile,
            drop_duplicates_mode=data_type,
        )


def handle_empty_data(assert_on_missing_data: bool, currency_pair: str) -> None:
    """
    Handle an empty data and raise an error or log a warning.

    :param assert_on_missing_data: assert on missing data
    :param currency_pair: currency pair, e.g. "BTC_USDT"
    """
    base_message = "No data for currency_pair='%s' was downloaded."
    if assert_on_missing_data:
        raise RuntimeError(base_message, currency_pair)
    else:
        _LOG.warning(base_message + " Continuing.", currency_pair)


def process_downloaded_historical_data(
    data: Union[pd.DataFrame, Iterator[pd.DataFrame]],
    args: Dict[str, Any],
    currency_pair: str,
    path_to_dataset: str,
) -> None:
    """
    Process downloaded historical data:

        - Assign pair and exchange columns.
        - Add knowledge timestamp column.
        - Save data to S3 filesystem.

    :param data: downloaded data
        It can be either a single DataFrame or an iterator of DataFrames.
    :param args: arguments from the command line
    :param currency_pair: currency pair, e.g. "BTC_USDT"
    :param path_to_dataset: path to the dataset
    """
    if isinstance(data, Iterator):
        # If data is an iterator, we need to check if it is empty.
        is_data_empty = True
        for df in data:
            is_data_empty = False
            process_downloaded_historical_data(
                df, args, currency_pair, path_to_dataset
            )
        if is_data_empty:
            handle_empty_data(args["assert_on_missing_data"], currency_pair)
        return
    if data.empty:
        handle_empty_data(args["assert_on_missing_data"], currency_pair)
        return
    # Assign pair and exchange columns.
    data["currency_pair"] = currency_pair
    data["exchange_id"] = args["exchange_id"]
    data = imvcdttrut.add_knowledge_timestamp_col(data, "UTC")
    # Save data to S3 filesystem.
    # TODO(Vlad): Refactor log messages when we save data by a day.
    _LOG.info("Saving the dataset into %s", path_to_dataset)
    if args.get("dst_dir"):
        if args["data_format"] == "csv":
            start_timestamp = args["start_timestamp"]
            end_timestamp = args["end_timestamp"]
            if not os.path.exists(args["dst_dir"]):
                os.makedirs(args["dst_dir"])
            full_target_path = os.path.join(
                args["dst_dir"], f"{start_timestamp}_{end_timestamp}.csv"
            )
            data.to_csv(full_target_path, index=False)
        # TODO: Add elif to handle parquet data format.
        else:
            hdbg.dfatal(f"Unsupported `{args['data_format']}` format!")
    else:
        if args["data_format"] == "parquet":
            # Save by day for trades, by month for everything else.
            partition_mode = "by_year_month"
            if args["data_type"] == "trades":
                partition_mode = "by_year_month_day"
            save_parquet(
                data,
                path_to_dataset,
                args["unit"],
                args["aws_profile"],
                args["data_type"],
                mode=args["pq_save_mode"],
                partition_mode=partition_mode,
            )
        elif args["data_format"] == "csv":
            save_csv(
                data,
                path_to_dataset,
                currency_pair,
                # Deprecated in CmTask5432.
                # args["incremental"],
                args["aws_profile"],
            )
        else:
            hdbg.dfatal(f"Unsupported `{args['data_format']}` format!")


def _split_universe(
    universe: List[str], group_size: int, universe_part: int
) -> List[str]:
    """
    Split the universe into groups of group_size symbols and return only
    universe_part- th group.

    If the split is not even, then the last group is the smaller than the rest.

    Examples:
    universe = [
                "ALICE_USDT",
                "GALA_USDT",
                "FLOW_USDT",
                "HBAR_USDT",
                "INJ_USDT",
                "NEAR_USDT"
    ]

    group_size = 2, universe_part = 1 returns
    ["ALICE_USDT", "GALA_USDT"]
    group_size = 3, universe_part = 2  returns
    ["HBAR_USDT", "INJ_USDT", "NEAR_USDT"]


    :oaram universe: universe of currency pairs
    :param group_size: number of symbols in  each group
    :param universe_part: which part after the split to return
    :return: subgroup of the original universe
    """
    lower_bound = (universe_part - 1) * group_size
    # If no such part exists raise an error, i.e. user asks for 3rd part of
    #  universe with 18 symbols.
    if lower_bound > len(universe):
        raise RuntimeError(
            f"Universe does not have {universe_part} parts of {group_size} pairs. \
            It has {len(universe)} symbols."
        )
    upper_bound = min(len(universe), (universe_part * group_size))
    universe_subset = universe[lower_bound:upper_bound]
    _LOG.warning(
        f"Using only part {universe_part} of the universe:"
        f"\t {universe_subset}"
    )
    return universe_subset


# TODO(Juraj): rename based on sorrentum protocol conventions.
def download_historical_data(
    args: Dict[str, Any], exchange: ivcdexex.Extractor
) -> None:
    """
    Encapsulate common logic for downloading historical exchange data.

    :param args: arguments passed on script run
    :param exchange_class: which exchange class is used in script run
        e.g. "CcxtExtractor"
    """
    # Convert Namespace object with processing arguments to dict format.
    # TODO(Juraj): refactor cmd line arguments to accept `asset_type`
    #  instead of `contract_type` once a decision is made.
    args["asset_type"] = args["contract_type"]
    if args.get("dst_dir"):
        path_to_dataset = args["dst_dir"]
    else:
        path_to_dataset = dsdascut.build_s3_dataset_path_from_args(
            args["s3_path"], args
        )
        # Deprecated in CmTask5432.
        # Verify that data exists for incremental mode to work.
        # if args["incremental"]:
        #     hs3.dassert_path_exists(path_to_dataset, args["aws_profile"])
        # elif not args["incremental"]:
        #     hs3.dassert_path_not_exists(path_to_dataset, args["aws_profile"])
    # Load currency pairs.
    mode = "download"
    universe = ivcu.get_vendor_universe(
        exchange.vendor, mode, version=args["universe"]
    )
    currency_pairs = universe[args["exchange_id"]]
    if args.get("universe_part"):
        currency_pairs = _split_universe(
            currency_pairs, args["universe_part"][0], args["universe_part"][1]
        )
    # Convert timestamps.
    start_timestamp = pd.Timestamp(args["start_timestamp"])
    end_timestamp = pd.Timestamp(args["end_timestamp"])
    for currency_pair in currency_pairs:
        # Download data.
        data = exchange.download_data(
            args["data_type"],
            args["exchange_id"],
            currency_pair,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            # If data_type = ohlcv, depth is ignored.
            depth=args.get("bid_ask_depth"),
        )
        process_downloaded_historical_data(
            data, args, currency_pair, path_to_dataset
        )


def verify_schema(data: pd.DataFrame, data_type: str) -> pd.DataFrame:
    """
    Validate the columns types in the extracted data.

    :param data: the dataframe to verify
    :param data_type: type of the data in the `data` argument.
    """
    error_msg = []
    if data.isnull().values.any():
        _LOG.warning("Extracted Dataframe contains NaNs")

    # Regex match if the column name contains one of the bid/ask column names`.
    regex = re.compile(
        "(bid_size|bid_price|ask_price|ask_size|bid_ask_midpoint|half_spread|"
        "log_size_imbalance|log_size_imbalance_var|bid_ask_midpoint_var)"
    )
    for column in data.columns:
        # There is a variety of Bid/Ask related columns, for
        #  simplicity, only the base names are stored in the schema.
        # Get the substring containing bid/ask related column if
        #  it's one of the level values, or the original column name
        #  otherwise.
        col_match = regex.search(column)
        col_after_regex = col_match.group(0) if col_match else column
        # Extract the expected type of the column from the schema.
        expected_type = DATASET_SCHEMA[data_type][col_after_regex]
        if (
            expected_type in ["float64", "int32", "int64"]
            and pd.to_numeric(data[column], errors="coerce").notnull().all()
        ):
            # Fix the type of numerical column.
            data[column] = data[column].astype(expected_type)
        # Get the actual data type of the column.
        actual_type = str(data[column].dtype)
        # Compare types.
        if actual_type != expected_type:
            # TODO(Grisha): extract timezone from `DATASET_SCHEMA` instead
            # of hard-coding `UTC`.
            if (
                "datetime64" in expected_type
                and "datetime64" in actual_type
                and "UTC" in actual_type
            ):
                # Datetime objects should not perfectly match, it is sufficient
                # to check timezones and that type is `datetime64`. E.g.,
                # `actual_type = datetime64[us, UTC]` and `expected_type =
                # datetime64[ns, UTC]` are considered equal in this case.
                # See CmTask5918 for details.
                _LOG.warning(
                    "Actual type=%s != expected type=%s because of the "
                    "different unit, continuing.",
                    actual_type,
                    expected_type,
                )
            else:
                # Log the error.
                error_msg.append(
                    f"Invalid dtype of `{column}` column: expected type"
                    f" `{expected_type}`, found `{actual_type}`"
                )
    if error_msg:
        hdbg.dfatal(message="\n".join(error_msg))
    return data


def resample_rt_bid_ask_data_periodically(
    db_stage: str,
    src_table: str,
    dst_table: str,
    exchange_id: str,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> None:
    """
    Load raw bid/ask data from specified DB table every minute, resample to 1
    minute and insert back during a specified time interval <start_ts, end_ts>.

    :param db_stage: DB stage to use
    :param src_table: Source table to get raw data from
    :param dst_table: Destination table to insert resampled data into
    :param exchange_id: which exchange to use data from
    :param start_ts: start of the time interval
    :param end_ts: end of the time interval
    """
    # Peform timestamp assertions.
    hdateti.dassert_have_same_tz(start_ts, end_ts)
    tz = start_ts.tz
    hdbg.dassert_lt(pd.Timestamp.now(tz), start_ts, "start_ts is in the past")
    hdbg.dassert_lt(start_ts, end_ts, "end_ts is less than start_time")
    db_connection = imvcddbut.DbConnectionManager.get_connection(db_stage)
    tz = start_ts.tz
    _LOG.info("Syncing with the start time.")
    hasynci.sync_wait_until(
        start_ts, lambda: pd.Timestamp.now(tz), log_verbosity=logging.INFO
    )
    # Start resampling.
    next_iter_start_time = start_ts
    while pd.Timestamp.now(tz) < end_ts:
        next_iter_start_time += pd.Timedelta(seconds=60)
        with htimer.TimedScope(logging.INFO, "# Load last minute of raw data"):
            # TODO(Juraj): the function uses `bid_ask_levels` internally,
            # expose `bid_ask_levels` as a cmdline parameter.
            df_raw = imvcddbut.fetch_last_minute_bid_ask_rt_db_data(
                db_connection, src_table, str(tz), exchange_id
            )
        if df_raw.empty:
            _LOG.warning("Empty Dataframe, nothing to resample")
        else:
            with htimer.TimedScope(
                logging.INFO, "# Resample last minute of raw data"
            ):
                df_resampled = imvcdttrut.transform_and_resample_rt_bid_ask_data(
                    df_raw
                )
            with htimer.TimedScope(logging.INFO, "# Save resampled data to DB"):
                df_resampled["end_download_timestamp"] = pd.Timestamp.now(tz)
                imvcddbut.save_data_to_db(
                    df_resampled,
                    "bid_ask",
                    db_connection,
                    dst_table,
                    str(start_ts.tz),
                    add_knowledge_timestamp=False,
                )
        hasynci.sync_wait_until(
            next_iter_start_time,
            lambda: pd.Timestamp.now(tz),
            log_verbosity=logging.INFO,
        )
    _LOG.info("Resampling finished at %s", pd.Timestamp.now(tz))


def get_CcxtExtractor(exchange_id: str, contract_type: str) -> ivcdexex.Extractor:
    """
    Helper function to build the correct extractor depending on the
    exchange_id.

    :param exchange_id: Name of exchange to download data from
    :param contract_type: Type of contract, spot, swap or futures
    """
    if exchange_id == "cryptocom":
        exchange = imvcdecrex.CryptocomCcxtExtractor(exchange_id, contract_type)
    else:
        exchange = imvcdexex.CcxtExtractor(exchange_id, contract_type)
    return exchange
