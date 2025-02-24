"""
Import as:

import oms.broker.ccxt.ccxt_utils as obccccut
"""
import argparse
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import ccxt
import ccxt.pro as ccxtpro
import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hlogging as hloggin
import helpers.hpandas as hpandas
import helpers.hsecrets as hsecret
import oms.hsecrets as omssec
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


def roll_up_child_order_fills_into_parent(
    parent_order: oordorde.Order,
    ccxt_child_order_fills: List[Dict[str, Any]],
    *,
    price_quantization: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Aggregate fill amount and price from child orders into an equivalent parent
    order.

    Fill amount is calculated as sum of fills for all orders. Price is
    calculated as VWAP for each passed child order, based on their fill
    amount.

    :param parent_order: parent order to get fill amount and price for
    :param ccxt_child_order_fills: CCXT order structures for child
        orders
    :param price_quantization: number of decimals to round the price of
        parent order
    :return: fill amount, fill price
    """
    # Get the total fill from all child orders.
    child_order_signed_fill_amounts = []
    for child_order_fill in ccxt_child_order_fills:
        # Get the unsigned fill amount.
        abs_fill_amount = float(child_order_fill["filled"])
        # Change the sign for 'sell' orders.
        side = child_order_fill["side"]
        if side == "buy":
            signed_fill_amount = abs_fill_amount
        elif side == "sell":
            signed_fill_amount = -abs_fill_amount
        else:
            raise ValueError(f"Unrecognized order `side` {side}")
        child_order_signed_fill_amounts.append(signed_fill_amount)
    signed_fill_amounts = pd.Series(child_order_signed_fill_amounts)
    # Verify that aggregated child orders have the same side.
    # All child orders for the given parent should be only 'buy' or 'sell'.
    hdbg.dassert_eq(
        signed_fill_amounts.abs().sum(),
        abs(signed_fill_amounts.sum()),
        "Both `buys` and `sells` detected in child order rollup.",
    )
    # Roll up information from child fills into an equivalent parent order.
    parent_order_signed_fill_num_shares = signed_fill_amounts.sum()
    if parent_order_signed_fill_num_shares == 0:
        # If all no amount is filled, average price is not applicable.
        _LOG.debug(
            "No amount filled for order %s. Skipping.", parent_order.order_id
        )
        parent_order_fill_price = np.nan
    else:
        # Calculate fill price as VWAP of all child order prices.
        # The cost here is the fill price and not the set limit price:
        # https://docs.ccxt.com/#/?id=notes-on-precision-and-limits
        child_order_fill_prices = [
            child_order_fill["cost"]
            for child_order_fill in ccxt_child_order_fills
        ]
        parent_order_fill_price = sum(child_order_fill_prices) / abs(
            parent_order_signed_fill_num_shares
        )
        # Round the price to decimal places provided in price_quantization,
        # if provided.
        if price_quantization is not None:
            hdbg.dassert_type_is(price_quantization, int)
            parent_order_fill_price = np.round(
                parent_order_fill_price, price_quantization
            )
        # Convert to float if the resulting price is an integer.
        # Portfolio downstream only accepts float dtype.
        if isinstance(parent_order_fill_price, int):
            parent_order_fill_price = float(parent_order_fill_price)
        hdbg.dassert_type_in(parent_order_fill_price, [float, np.float64])
    return parent_order_signed_fill_num_shares, parent_order_fill_price


# #############################################################################


def drop_bid_ask_duplicates(
    bid_ask_data: pd.DataFrame, *, max_num_dups: Optional[int] = 1
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Identify and drop duplicated bid/ask data.

    There should be a single data point for a timestamp/asset_id combo.
    Currently we assume that the last data point is the correct one. If
    the number of duplicates exceeds the limit, raise.

    :param bid_ask_data: bid/ask data to be deduplicated
    :param max_num_dups: max allowed number of duplicated entries, None
        for no limit.
    :return: deduplicated data and duplicated rows
    """
    subset = ["timestamp", "currency_pair"]
    # Get duplicated values keeping the last one.
    # Note: the assumption is the last data point will contain fuller info,
    # since it is expected to have a later `knowledge_timestamp`.
    bid_ask_data = bid_ask_data.reset_index()
    duplicates = bid_ask_data.duplicated(subset=subset, keep="last")
    num_duplicates = duplicates.sum()
    if num_duplicates:
        # Check if the number of duplicates is not above the limit.
        if max_num_dups:
            hdbg.dassert_lte(
                num_duplicates,
                max_num_dups,
                msg=f"Number of duplicated rows over {max_num_dups}",
            )
        # Return duplicates and deduplicated data.
        duplicated_rows = bid_ask_data.loc[duplicates].set_index("timestamp")
        # Display the dropped duplicated value.
        _LOG.warning(
            "Duplicate entry found and dropped:\n%s",
            hpandas.df_to_str(duplicated_rows),
        )
        # Display the duplicated value that is kept.
        kept_duplicates = bid_ask_data.duplicated(subset=subset, keep="first")
        _LOG.warning(
            "Duplicated entry that is kept:\n%s",
            hpandas.df_to_str(kept_duplicates),
        )
        # Return deduplicated data.
        bid_ask_data = bid_ask_data.loc[~duplicates].set_index("timestamp")
    else:
        bid_ask_data = bid_ask_data.set_index("timestamp")
        duplicated_rows = None
    return bid_ask_data, duplicated_rows


# #############################################################################


def subset_market_info(
    market_info: Dict[int, Dict[str, Union[float, int]]], info_type: str
) -> Dict[int, Union[float, int]]:
    """
    Return only the relevant information from market info, e.g., info about
    precision.
    """
    # It is assumed that every asset has the same info type structure.
    available_info = list(market_info.values())[0].keys()
    hdbg.dassert_in(info_type, available_info)
    market_info_keys = list(market_info.keys())
    _LOG.debug("market_info keys=%s", market_info_keys)
    market_info_subset = {
        key: market_info[key][info_type] for key in market_info_keys
    }
    return market_info_subset


def load_market_data_info() -> Dict[int, Dict[str, Union[float, int]]]:
    """
    Load pre-saved market info.

    The data looks like:
    {"6051632686":
        {"min_amount": 1.0, "min_cost": 10.0, "amount_precision": 3},
     ...
    """
    file_path = os.path.join(
        hgit.get_amp_abs_path(),
        "oms/broker/ccxt/test/outcomes/TestSaveBrokerData1.test_save_market_info1/input/broker_data.json",
    )
    market_info = hio.from_json(file_path)
    # Convert to int, because asset ids are strings.
    market_info = {int(k): v for k, v in market_info.items()}
    return market_info


def get_asset_id_to_share_decimals() -> Dict[int, int]:
    """
    Get mapping asset ids to the number of decimal places.
    """
    market_info = load_market_data_info()
    info_type = "amount_precision"
    asset_ids_to_decimals = subset_market_info(market_info, info_type)
    return asset_ids_to_decimals


def _assert_exchange_methods_present(
    exchange: Union[ccxt.Exchange, ccxtpro.Exchange],
    exchange_id: str,
    *,
    additional_methods: List[str] = None,
) -> None:
    # Assert that the requested exchange supports all methods necessary to
    # make placing/fetching orders possible.
    methods = [
        "createOrder",
        "fetchClosedOrders",
        "fetchPositions",
        "fetchBalance",
        "fetchLeverageTiers",
        "setLeverage",
        "fetchMyTrades",
    ]
    if additional_methods is not None:
        methods.extend(additional_methods)
    abort = False
    for method in methods:
        if not exchange.has[method]:
            _LOG.error("Method %s is unsupported for %s.", method, exchange_id)
            abort = True
    if abort:
        raise ValueError(
            f"The {exchange_id} exchange does not support all the"
            " required methods for placing orders."
        )


def create_ccxt_exchanges(
    secret_identifier: omssec.SecretIdentifier,
    contract_type: str,
    exchange_id: str,
    account_type: str,
) -> Tuple[ccxt.Exchange, ccxtpro.Exchange]:
    """
    Log into the exchange and return tuple of sync and async `ccxt.Exchange`
    objects.

    :param secret_identifier: a SecretIdentifier holding a full name of secret
            to look for in AWS SecretsManager
    :param contract_type: "spot" or "futures"
    :param exchange_id: name of the exchange to initialize the broker for
            (e.g., Binance)
    :param account_type:
            - "trading" launches the broker in trading environment
            - "sandbox" launches the broker in sandbox environment (not
               supported for every exchange)
    :return: tuple of sync and async exchange
    """
    secrets_id = str(secret_identifier)
    # Select credentials for provided exchange.
    # TODO(Juraj): the problem is that we are mixing DB stage and credential
    # stage and also the intended nomenclature for the secrets id not really
    # valid/useful.
    if ".prod" in secrets_id:
        secrets_id = secrets_id.replace("prod", "preprod")
    exchange_params = hsecret.get_secret(secrets_id)
    # Disable rate limit.
    # Automatic rate limitation is disabled to control submission of orders.
    # If enabled, CCXT can reject an order silently, which we want to avoid.
    # See CMTask4113.
    exchange_params["rateLimit"] = False
    # Log into futures/spot market.
    if contract_type == "futures":
        exchange_params["options"] = {"defaultType": "future"}
    elif contract_type == "swap":
        exchange_params["options"] = {"defaultType": "swap"}
    # Create both sync and async exchange.
    sync_async_exchange = []
    for module in [ccxt, ccxtpro]:
        # Create a CCXT Exchange class object.
        ccxt_exchange = getattr(module, exchange_id)
        exchange = ccxt_exchange(exchange_params)
        # TODO(Danya): Temporary fix, CMTask4971.
        # Set exchange properties.
        if exchange_id == "binance":
            # Necessary option to avoid time out of sync error
            # (CmTask2670 Airflow system run error "Timestamp for this
            # request is outside of the recvWindow.")
            # TODO(Juraj): CmTask5194.
            # exchange.options["adjustForTimeDifference"] = True
            exchange.options["recvWindow"] = 5000
        if account_type == "sandbox":
            _LOG.warning("Running in sandbox mode")
            exchange.set_sandbox_mode(True)
        hdbg.dassert(
            exchange.checkRequiredCredentials(),
            msg="Required credentials not passed",
        )
        if module == ccxtpro:
            _assert_exchange_methods_present(
                exchange, exchange_id, additional_methods=["cancelAllOrders"]
            )
        else:
            _assert_exchange_methods_present(exchange, exchange_id)
        # CCXT registers the logger after it's built, so we need to reduce its
        # logger verbosity.
        hloggin.shutup_chatty_modules()
        sync_async_exchange.append(exchange)
    return tuple(sync_async_exchange)


def create_parent_orders_from_json(
    parent_order_list: List[Dict[str, Any]],
    num_parent_orders_per_bar: int,
    *,
    update_time: bool = True,
) -> List[oordorde.Order]:
    """
    Convert parent orders inside the list from Dict to Order type.

    :param parent_order_list: list of parent orders in List[Dict[...]]
        format which we want to convert to List of Order objects
    :param num_parent_orders_per_bar: number of parent orders to be
        executed for each bar. This parameter is used to update the
        timestamp of parent orders with respect to their bar time
    :return: List of Order objects
    """
    # Converting parent orders from JSON format to Order object.
    parent_orders_csv = []
    for orders in parent_order_list:
        order_dicts = [dict(item) for item in [orders]]
        for order_dict in order_dicts:
            order_string = f"Order: order_id={order_dict['order_id']} creation_timestamp={order_dict['creation_timestamp']} asset_id={order_dict['asset_id']} type_={order_dict['type_']} start_timestamp={order_dict['start_timestamp']} end_timestamp={order_dict['end_timestamp']} curr_num_shares={order_dict['curr_num_shares']} diff_num_shares={order_dict['diff_num_shares']} tz={order_dict['tz']} extra_params={{}}"
            parent_orders_csv.append(order_string)
    parent_orders_string = "\n".join(parent_orders_csv)
    orders = oordorde.orders_from_string(parent_orders_string)
    # Updating timestamps of the log orders.
    order_id = 0
    # Adding 1 minute of buffer time to the start time of parent order so that
    # when the `ReplayedCcxtExchange` object  is initialized and the order is
    # called it has not passed the wall clock time.
    # TODO(Sameep): Remove this code once all tests are changed with the
    # new mocked market data updates. Covered in CmTask5984.
    if update_time:
        start_timestamp = hdateti.get_current_time("ET") + pd.Timedelta(minutes=1)
        for order in orders:
            order_id = order_id + 1
            order.creation_timestamp = start_timestamp
            order.end_timestamp = start_timestamp + (
                order.end_timestamp - order.start_timestamp
            )
            order.start_timestamp = start_timestamp
            if order_id % num_parent_orders_per_bar == 0:
                start_timestamp = order.end_timestamp
    return orders


def add_CcxtBroker_cmd_line_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for broker.
    """
    parser.add_argument(
        "--exchange",
        action="store",
        required=True,
        type=str,
        help="Name of the exchange, e.g. 'binance'.",
    )
    parser.add_argument(
        "--contract_type",
        action="store",
        required=True,
        type=str,
        help="'futures' or 'spot'. Note: only futures contracts are supported.",
    )
    parser.add_argument(
        "--stage",
        action="store",
        required=True,
        type=str,
        help="Stage to run at: local, preprod, prod.",
    )
    parser.add_argument(
        "--secret_id",
        action="store",
        required=True,
        type=int,
        help="ID of the API Keys to use as they are stored in AWS SecretsManager.",
    )
    parser.add_argument(
        "--log_dir",
        action="store",
        type=str,
        required=True,
        help="Log dir to save data.",
    )
    parser.add_argument(
        "--universe",
        type=str,
        required=False,
        help="Version of the universe, e.g. 'v7.4'",
    )
    return parser
