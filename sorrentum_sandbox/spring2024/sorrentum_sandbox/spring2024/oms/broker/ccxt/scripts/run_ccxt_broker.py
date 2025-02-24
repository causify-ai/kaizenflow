#!/usr/bin/env python

# TODO(gp): This script should only use Broker abstract interface.
"""
Run the order submission via CcxtBroker in an async manner.

Example use:

> oms/broker/ccxt/scripts/run_ccxt_broker.py \
    --log_dir tmp_log_dir \
    --universe 'v7.4' \
    --max_parent_order_notional 60 \
    --randomize_orders \
    --parent_order_duration_in_min 5 \
    --num_bars 3 \
    --num_parent_orders_per_bar 5 \
    --secret_id 4 \
    --clean_up_before_run \
    --clean_up_after_run \
    --close_positions_using_twap \
    --child_order_execution_freq 1T \
    --volatility_multiple 0.75 0.7 0.6 0.8 1.0 \
    --include_btc_usdt True \
    -v DEBUG
"""
import argparse
import asyncio
import logging
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hwall_clock_time as hwacltim
import im_v2.ccxt.utils as imv2ccuti
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe as ivcu
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.ccxt_broker_utils as obccbrut
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)

_BINANCE_MIN_NOTIONAL = 10
_VENDOR = "ccxt"
_EXCHANGE = "binance"
# TODO(Juraj): a hacky way to make progress, implement this as one of the run modes.
_NEXT_ORDER_SIDE_PER_ASSET = {}


def _get_symbols(
    universe_version: str,
    vendor: str,
    exchange: str,
    contract_type: str,
) -> List[str]:
    """
    Get top symbols from the universe.

    :param universe_version: version of the universe
    :param vendor: vendor name
    :param exchange: exchange name
    :return: list of CCXT formatted symbols
    """
    # Get the universe.
    mode = "trade"
    universe = ivcu.get_vendor_universe(vendor, mode, version=universe_version)
    # Reformat symbols.
    symbols = [
        imv2ccuti.convert_currency_pair_to_ccxt_format(
            symbol, exchange, contract_type
        )
        for symbol in universe[exchange]
    ]
    # TODO(Juraj): Remove global var #CmTask7601.
    global _NEXT_ORDER_SIDE_PER_ASSET
    _NEXT_ORDER_SIDE_PER_ASSET = {symbol: None for symbol in symbols}
    return symbols


def _get_asset_ids(
    broker: obcaccbr.AbstractCcxtBroker,
    symbol_to_price_dict: Dict[str, float],
    *,
    number_asset_ids: Optional[int] = None,
    include_btc_usdt: bool = True,
) -> List[dict]:
    """
    Get random asset ids.

    :param broker: broker instance
    :param number_asset_ids: number of asset ids to return
    :return: list of asset ids
    """
    _LOG.debug("number_asset_ids=%s", number_asset_ids)
    if number_asset_ids is None:
        number_asset_ids = np.random.randint(5, 10)
    top_symbols = _get_symbols(
        broker._universe_version, _VENDOR, _EXCHANGE, broker._contract_type
    )
    btc_usdt = "BTC/USDT:USDT"
    if not include_btc_usdt and btc_usdt in top_symbols:
        top_symbols.remove(btc_usdt)
    # Get asset ids.
    asset_ids = [
        {
            "asset_id": broker.ccxt_symbol_to_asset_id_mapping[symbol],
            "price": symbol_to_price_dict[symbol],
            "symbol": symbol,
        }
        for symbol in top_symbols
    ]
    _LOG.debug("prices_by_asset_ids=%s", asset_ids)
    asset_ids = asset_ids[:number_asset_ids]
    # Ensure BTC pair is in the list.
    if include_btc_usdt and btc_usdt not in list(
        map(lambda x: x["symbol"], asset_ids)
    ):
        asset_ids.pop()
        asset_ids.append(
            {
                "asset_id": broker.ccxt_symbol_to_asset_id_mapping[btc_usdt],
                "price": symbol_to_price_dict[btc_usdt],
                "symbol": btc_usdt,
            }
        )
    _LOG.debug("asset_ids=%s", asset_ids)
    return asset_ids


def _get_random_order(
    start_timestamp: pd.Timestamp,
    asset_id: int,
    symbol: str,
    price: float,
    max_parent_order_notional: float,
    parent_order_duration_in_min: int,
    current_position: float,
    close_position: bool,
    *,
    order_direction: Optional[str] = None,
) -> oordorde.Order:
    """
    Get random order.

    :param asset_id: asset id
    :param price: price
    :param max_parent_order_notional: max parent order notional
    :return: order
    """
    # Order type.
    order_type = "price@twap"
    # Order size.
    min_order_size = _BINANCE_MIN_NOTIONAL / price * parent_order_duration_in_min
    max_order_size = max_parent_order_notional / price
    if close_position:
        num_shares = current_position * -1
    else:
        num_shares = np.random.uniform(min_order_size, max_order_size)
        _NEXT_ORDER_SIDE_PER_ASSET[symbol] = "sell"
        # Set negative amount of shares when direction is sell, or direction should be random.
        if order_direction == "sell" or (
            order_direction is None and np.random.choice([True, False])
        ):
            num_shares = -num_shares
            _NEXT_ORDER_SIDE_PER_ASSET[symbol] = "buy"
    _LOG.debug(hprint.to_str2(num_shares))
    # Timestamps.
    end_timestamp = start_timestamp + pd.Timedelta(
        minutes=parent_order_duration_in_min
    )
    diff_num_shares = float(num_shares)
    _LOG.debug(hprint.to_str2(diff_num_shares))
    if diff_num_shares == 0:
        return None
    # Create the order.
    order = oordorde.Order(
        start_timestamp,
        asset_id,
        order_type,
        start_timestamp,
        end_timestamp,
        current_position,
        diff_num_shares,
    )
    _LOG.debug("order=%s", order)
    return order


def _get_random_orders(
    broker: obcaccbr.AbstractCcxtBroker,
    max_parent_order_notional: int,
    parent_order_duration_in_min: int,
    number_orders: int,
    positions: Dict[int, float],
    start_timestamp: pd.Timestamp,
    symbol_to_price_dict: Dict[str, float],
    *,
    close_positions: bool = False,
    orders_direction: Optional[str] = None,
    include_btc_usdt: bool = True,
) -> List[oordorde.Order]:
    """
    Get random orders.

    :param broker: broker instance
    :param max_parent_order_notional: max parent order notional
    :param parent_order_duration_in_min: run length in minutes
    :param number_orders: number of orders to return
    :param orders_directions: "buy", "sell", if None then randomly
        chosen.
    :return: list of orders
    """
    asset_ids = _get_asset_ids(
        broker,
        symbol_to_price_dict,
        number_asset_ids=number_orders,
        include_btc_usdt=include_btc_usdt,
    )
    orders = []
    for asset_id in asset_ids:
        position = positions.get(asset_id["asset_id"], 0)
        if close_positions and position == 0:
            continue
        # Set order direction for the current order.
        symbol = asset_id["symbol"]
        _LOG.debug(_NEXT_ORDER_SIDE_PER_ASSET)
        order_diretion = (
            orders_direction
            if orders_direction is not None
            else _NEXT_ORDER_SIDE_PER_ASSET[symbol]
        )
        order = _get_random_order(
            start_timestamp,
            asset_id["asset_id"],
            symbol,
            asset_id["price"],
            max_parent_order_notional,
            parent_order_duration_in_min,
            position,
            close_positions,
            order_direction=order_diretion,
        )
        if order is not None:
            orders.append(order)
    _LOG.debug("random_orders=%s", str(orders))
    return orders


def get_orders() -> List[oordorde.Order]:
    """
    Generate test orders for concurrent submission.

    The test orders are meant to be submitted simultaneously, and
    therefore should have different `asset_ids` to avoid collision.
    """
    # pylint: disable=line-too-long
    orders_str = "\n".join(
        [
            # DOGE
            "Order: order_id=0 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3065029174 type_=price@twap start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-900.0 tz=America/New_York extra_params={}",
            # APE
            "Order: order_id=1 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=6051632686 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=33.0 tz=America/New_York extra_params={}",
        ]
    )
    #            "Order: order_id=2 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=8717633868 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=3.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=3 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=8968126878 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-0.69 tz=America/New_York extra_params={}",
    #            "Order: order_id=4 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1467591036 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=0.005 tz=America/New_York extra_params={}",
    #            "Order: order_id=5 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2476706208 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-30.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=6 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=5115052901 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=150.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=7 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=3401245610 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-9.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=8 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1464553467 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=0.03 tz=America/New_York extra_params={}",
    #            "Order: order_id=9 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1966583502 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=200.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=10 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1030828978 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=100.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=11 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2683705052 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-120.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=12 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=9872743573 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-18.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=13 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2484635488 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-800.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=14 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2099673105 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=60.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=15 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2237530510 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-5.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=16 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2425308589 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=130.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=17 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=1776791608 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=13.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=18 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=2384892553 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-30.0 tz=America/New_York extra_params={}",
    #            "Order: order_id=19 creation_timestamp=2023-02-21 02:55:44.508525-05:00 asset_id=5118394986 type_=limit start_timestamp=2023-02-21 02:55:44.508525-05:00 end_timestamp=2023-02-21 03:00:00-05:00 curr_num_shares=0.0 diff_num_shares=-30.0 tz=America/New_York extra_params={}",
    #        ]
    #    )
    # pylint: enable=line-too-long
    orders = oordorde.orders_from_string(orders_str)
    start_timestamp = hdateti.get_current_time("ET")
    end_timestamp = start_timestamp + pd.Timedelta("5T")
    for order in orders:
        order.creation_timestamp = hdateti.get_current_time("ET")
        _LOG.debug(hprint.to_str("order.creation_timestamp"))
        order.start_timestamp = start_timestamp
        order.end_timestamp = end_timestamp
    return orders


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--secret_id",
        required=False,
        default=4,
        type=int,
        help="Secret ID.",
    )
    parser.add_argument(
        "--max_parent_order_notional",
        required=False,
        default=25,
        type=int,
        help="Maximal parent order notional.",
    )
    parser.add_argument(
        "--randomize_orders",
        action="store_true",
        required=False,
        default=False,
        help="Randomize orders.",
    )
    parser.add_argument(
        "--log_dir",
        action="store",
        required=True,
        type=str,
        help="Directory path where log files will be saved.",
    )
    parser.add_argument(
        "--universe",
        action="store",
        required=True,
        type=str,
        help="Version of the universe.",
    )
    parser.add_argument(
        "--clean_up_before_run",
        action="store_true",
        required=False,
        help="Clean up before submitting orders.",
    )
    parser.add_argument(
        "--clean_up_after_run",
        action="store_true",
        required=False,
        help="Clean up after submitting orders.",
    )
    parser.add_argument(
        "--parent_order_duration_in_min",
        required=False,
        default=3,
        type=int,
        help="Length of the run in minutes.",
    )
    parser.add_argument(
        "--num_parent_orders_per_bar",
        required=False,
        default=10,
        type=int,
        help="Number of orders (using unique symbols) to generate per bar",
    )
    parser.add_argument(
        "--num_bars",
        required=False,
        default=1,
        type=int,
        help="Number of bars to execute (assuming parent_order_duration_in_min = 5)",
    )
    parser.add_argument(
        "--close_positions_using_twap",
        action="store_true",
        required=False,
        default=False,
        help="Additional bar is added which submits order to flatten positions (caution: fills are not guaranteed)",
    )
    parser.add_argument(
        "--db_stage",
        required=False,
        default="preprod",
        type=str,
        help="Stage of the database to use, e.g. 'prod' or 'local'.",
    )
    parser.add_argument(
        "--child_order_execution_freq",
        required=True,
        type=str,
        default="1T",
        help="Execution frequency of child orders, e.g. 1T or 30s",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        required=False,
        default=False,
        help="Overwrite logs in the given log directory",
    )
    parser.add_argument(
        "--volatility_multiple",
        required=True,
        nargs="+",
        type=float,
        help="List of volatility multiple e.g. 0.75 or 0.75 0.8 1",
    )
    parser.add_argument(
        "--include_btc_usdt",
        required=True,
        type=hparser.str_to_bool,
        help="Flag to control inclusion of BTC_USDT in the experiment.",
    )
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _execute_one_bar_using_twap(
    args: Dict,
    broker: obccccbr.CcxtBroker,
    execution_freq: str,
    symbol_to_price_dict: Dict[str, float],
    *,
    close_positions: bool = False,
    previous_start_timestamp: Optional[pd.Timestamp] = None,
    orders_direction: Optional[str] = None,
    replayed_orders: Optional[List[oordorde.Order]] = None,
) -> pd.Timestamp:
    """
    Generate random orders and submit them in a TWAP manner.

    :return: start timestamp of the parent orders
    """
    # # Ceil the timestamp to the nearest minute so end_timestamp can be calculated correctly.
    # start_timestamp = pd.Timestamp.utcnow().ceil('T')
    # Align start_timestamp to a 5 min grid.
    # TODO(Danya): CMTask4860.
    if previous_start_timestamp is None:
        start_timestamp = pd.Timestamp.utcnow().ceil("5T")
    else:
        start_timestamp = previous_start_timestamp + pd.Timedelta(minutes=5)
    if args.randomize_orders:
        positions = broker.get_open_positions()
        positions = {
            broker.ccxt_symbol_to_asset_id_mapping[key]: value
            for key, value in positions.items()
        }
        orders = _get_random_orders(
            broker,
            args.max_parent_order_notional,
            args.parent_order_duration_in_min,
            number_orders=args.num_parent_orders_per_bar,
            positions=positions,
            start_timestamp=start_timestamp,
            symbol_to_price_dict=symbol_to_price_dict,
            close_positions=close_positions,
            orders_direction=orders_direction,
            include_btc_usdt=args.include_btc_usdt,
        )
        _LOG.debug(str(orders))
    else:
        orders = get_orders()
    _LOG.debug(str(orders))
    hdbg.dassert_no_duplicates([order.asset_id for order in orders])
    # TODO(Danya): A hack to allow correct logging of multiple parent orders
    hwacltim.set_current_bar_timestamp(orders[0].creation_timestamp)
    order_type = "price@custom_twap"
    hasynci.run(
        broker.submit_orders(orders, order_type, execution_freq=execution_freq),
        asyncio.get_event_loop(),
        close_event_loop=False,
    )
    return start_timestamp


def _generate_prices_from_data_reader(
    contract_type: str, db_stage: str, universe_version: str
) -> Dict[str, float]:
    """
    Generate prices for all the currency pairs in the universe.
    """
    signature = f"realtime.airflow.downloaded_1min.postgres.ohlcv.futures.{universe_version.replace('.', '_')}.ccxt.binance.v1_0_0"
    universe = ivcu.get_vendor_universe(
        _VENDOR, "trade", version=universe_version
    )
    currency_pairs = universe[_EXCHANGE]
    # Get latest price for currency from database.
    reader = imvcdcimrdc.RawDataReader(signature, stage=db_stage)
    # Timedelta here has been taken as 4 minutes just to be sure that data from
    # all symbols is there in database.
    start_timestamp = pd.Timestamp.now() - pd.Timedelta(minutes=4)
    df = reader.read_data(start_timestamp, None, currency_pairs=currency_pairs)
    # Convert the 'timestamp' column to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    # Sort the DataFrame by 'timestamp' in descending order
    df = df.sort_values(by="timestamp", ascending=False)
    # Use groupby to get the latest price for each currency pair
    # Any column of from OHLC will be fine as this price is just for approximation.
    latest_prices = df.groupby("currency_pair").first().to_dict()["high"]
    # Convert the result to a dictionary
    latest_prices_dict = dict(latest_prices)
    symbol_to_price_dict = {
        imv2ccuti.convert_currency_pair_to_ccxt_format(
            symbol, _EXCHANGE, contract_type
        ): price
        for symbol, price in latest_prices_dict.items()
    }
    return symbol_to_price_dict


def _main(parser: argparse.ArgumentParser) -> None:
    # Initialize time log for in-script operations.
    args = parser.parse_args()
    log_dir = args.log_dir
    # Create the log directory
    hio.create_dir(log_dir, incremental=args.incremental, abort_if_exists=True)
    # Log args.
    args_logfile = os.path.join(args.log_dir, "args.json")
    hio.to_json(args_logfile, vars(args))
    #
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Initialize broker for the trading account.
    secret_id = args.secret_id
    child_order_execution_freq = args.child_order_execution_freq
    if len(args.volatility_multiple) == 1:
        volatility_multiple = args.volatility_multiple[0]
    else:
        volatility_multiple = args.volatility_multiple
        parent_order_duration_in_min = pd.Timedelta(
            minutes=args.parent_order_duration_in_min
        )
        child_order_duration_in_min = pd.Timedelta(child_order_execution_freq)
        max_num_child_orders = (
            parent_order_duration_in_min / child_order_duration_in_min
        )
        hdbg.dassert_lte(max_num_child_orders, len(volatility_multiple))
    broker_config = {
        "limit_price_computer_type": "LimitPriceComputerUsingVolatility",
        "limit_price_computer_kwargs": {
            "volatility_multiple": volatility_multiple,
        },
    }
    broker = obccbrin.get_CcxtBroker(
        secret_id,
        log_dir,
        args.universe,
        broker_config,
        stage=args.db_stage,
    )
    symbol_to_price_dict = _generate_prices_from_data_reader(
        broker._contract_type, args.db_stage, args.universe
    )
    # Clean up before running the script.
    if args.clean_up_before_run:
        _LOG.debug("Cleaning up before running the script.")
        # TODO(Vlad): Temporarily hardcoded parameters.
        obccbrut.flatten_ccxt_account(
            broker,
            dry_run=False,
            assert_on_non_zero_positions=False,
        )
    try:
        previous_start_timestamp = None
        # orders_direction = "buy"
        for bar in range(args.num_bars):
            previous_start_timestamp = _execute_one_bar_using_twap(
                args,
                broker,
                child_order_execution_freq,
                symbol_to_price_dict,
                previous_start_timestamp=previous_start_timestamp,
                # orders_direction=orders_direction
            )
            # Switch between buy and sell orders in order to avoid position build-up.
            # orders_direction = "sell" if orders_direction == "buy" else "buy"
        if args.close_positions_using_twap:
            _execute_one_bar_using_twap(
                args,
                broker,
                child_order_execution_freq,
                symbol_to_price_dict,
                previous_start_timestamp=previous_start_timestamp,
                close_positions=True,
            )
    except Exception as e:
        raise e
    # Run the order submission but flatten in case some positions
    #  remained open.
    finally:
        # Clean up after running the script.
        if args.clean_up_after_run:
            _LOG.debug("Cleaning up after running the script.")
            obccbrut.flatten_ccxt_account(
                broker,
                dry_run=False,
                assert_on_non_zero_positions=False,
            )


if __name__ == "__main__":
    seed = int(pd.Timestamp.now().timestamp())
    np.random.seed(seed)
    _LOG.debug("seed=%s", seed)
    _main(_parse())
