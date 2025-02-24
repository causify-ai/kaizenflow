"""
Hi-level functions for CCXT broker.

Import as:

import oms.broker.ccxt.ccxt_broker_utils as obccbrut
"""
import asyncio
import logging
from typing import Optional

import pandas as pd

import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.common.db.db_utils as imvcddbut
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


# TODO(Juraj): this is only used in web_apps/monitoring/app.py,
# consider deprecating.
def get_broker(
    exchange: str,
    contract_type: str,
    stage: str,
    secret_id: int,
    *,
    db_stage: Optional[str] = None,
) -> obcaccbr.AbstractCcxtBroker:
    """
    Initialize and get broker.

    :param exchange: exchange name, e.g., "binance"
    :param contract_type: contract type, e.g., "futures"
    :param stage: stage, e.g., "dev"
    :param secret_id: secret id of the broker
    :param db_stage: stage of the database to use, e.g., "dev"
    :return: broker
    """
    if db_stage is None:
        db_stage = "dev"
    # TODO(Vlad): Remove dependency on having a functional DB connection,
    # it makes no sense here.
    connection = imvcddbut.DbConnectionManager.get_connection(db_stage)
    im_client = icdc.get_mock_realtime_client("v1", connection)
    market_data = obccbrin.get_RealTimeImClientMarketData_example2(im_client)
    broker = obccbrin.get_CcxtBroker_example1(
        market_data, exchange, contract_type, stage, secret_id
    )
    return broker


def flatten_ccxt_account(
    broker: obcaccbr.AbstractCcxtBroker,
    dry_run: bool,
    *,
    deadline_in_secs: int = 60,
    assert_on_non_zero_positions: bool = False,
) -> None:
    """
    Close all open positions on the CCXT account.

    The positions are closed via reduce-only orders of the opposite
    side of the current position, with larger order amount.
    E.g. for a position of `"BTC/USDT": -0.1`, a reduce-only order of "BTC/USDT": 0.1" is placed.

    Note: currently optimized for Binance futures, removing all long/short positions

    :param broker: a CCXT broker object
    :param dry_run: whether to avoid actual execution
    :param deadline_in_secs: deadline for order to be executed, 60 by default
    """
    _LOG.info("Total balance before flattening: %s", broker.get_total_balance())
    # Fetch all open positions.
    open_positions = broker.get_open_positions()
    _LOG.info(hprint.to_str("open_positions"))
    if open_positions:
        # Create orders.
        orders = []
        # TODO(Danya): Replace with reduce only, maybe close all.
        for symbol, position in open_positions.items():
            _LOG.info("%s - %s", symbol, position)
            # Build an order to flatten the account.
            type_ = "market"
            curr_num_shares = float(position)
            diff_num_shares = -curr_num_shares
            asset_id = broker.ccxt_symbol_to_asset_id_mapping[symbol]
            curr_timestamp = pd.Timestamp.now(tz="UTC")
            start_timestamp = curr_timestamp
            end_timestamp = start_timestamp + pd.DateOffset(
                seconds=deadline_in_secs
            )
            order_id = 0
            order = oordorde.Order(
                curr_timestamp,
                asset_id,
                type_,
                start_timestamp,
                end_timestamp,
                curr_num_shares,
                diff_num_shares,
                order_id=order_id,
            )
            # Set order as reduce-only to close the position.
            order.extra_params["reduce_only"] = True
            orders.append(order)
        order_type = "market"
        hasynci.run(
            broker.submit_orders(orders, order_type, dry_run=dry_run),
            asyncio.get_event_loop(),
            close_event_loop=False,
        )
    else:
        _LOG.warning("No open positions found.")
    _LOG.info("Account flattened. Total balance: %s", broker.get_total_balance())
    if assert_on_non_zero_positions:
        # Assert that all positions are closed.
        open_positions = broker.get_open_positions()
        hdbg.dassert_eq(
            len(open_positions),
            0,
            msg=(
                "Some positions failed to close: "
                f"{hprint.to_str('open_positions')}"
            ),
        )
