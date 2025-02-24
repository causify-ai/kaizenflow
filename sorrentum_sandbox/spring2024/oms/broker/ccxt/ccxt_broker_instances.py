"""
Import as:

import oms.broker.ccxt.ccxt_broker_instances as obccbrin
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdict as hdict
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe as ivcu
import market_data as mdata
import oms.broker.ccxt.ccxt_broker as obccccbr
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.broker.ccxt.dataframe_ccxt_broker as obcdccbr
import oms.broker.ccxt.replayed_ccxt_exchange as obcrccex
import oms.broker.replayed_data_reader as obredare
import oms.broker.replayed_fills_dataframe_broker as obrfdabr
import oms.child_order_quantity_computer as ochorquco
import oms.hsecrets as omssec
import oms.hsecrets.secret_identifier as ohsseide
import oms.limit_price_computer as oliprcom

_LOG = logging.getLogger(__name__)


def get_CcxtBroker_exchange_only_instance1(
    universe_version: str,
    secret_identifier: omssec.SecretIdentifier,
    log_dir: str,
) -> obccccbr.CcxtBroker:
    """
    Build a `CcxtBroker` for exchange only operations or tests.

    - No ImClient
    - No RawDataReader
    - MarketData object is present because of dependence on
    the wall clock and lower level interface
    """
    # Strategy ID is a dummy value
    strategy_id = "C1b"
    exchange_id = secret_identifier.exchange_id
    # exchange_id = "binance"
    stage = secret_identifier.stage
    # stage = "preprod"
    account_type = secret_identifier.account_type
    # account_type = "trading"
    contract_type = "swap"
    portfolio_id = "ccxt_portfolio_1"
    # Build logger.
    logger = obcccclo.CcxtLogger(log_dir, mode="write")
    # Build ImClient.
    secret_identifier.stage
    # bid_ask_table = "ccxt_bid_ask_futures_raw"
    # im_client = icdcl.get_CcxtSqlRealTimeImClient_example1(
    #    universe_version, db_stage, bid_ask_table
    # )
    # `MarketData` is not strictly needed to talk to exchange, but since it is
    #  required to init the `Broker` we pass something to make it work.
    asset_ids = None
    db_stage = "preprod"
    market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(
        asset_ids, db_stage
    )
    sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
        secret_identifier, contract_type, exchange_id, account_type
    )
    max_order_submit_retries = 1
    volatility_multiple = [0.75, 0.7, 0.6, 0.8, 1.0]
    # Build Broker.
    broker = obccccbr.CcxtBroker(
        exchange_id=exchange_id,
        account_type=account_type,
        portfolio_id=portfolio_id,
        contract_type=contract_type,
        secret_identifier=secret_identifier,
        strategy_id=strategy_id,
        market_data=market_data,
        universe_version=universe_version,
        stage=stage,
        logger=logger,
        bid_ask_im_client=None,
        max_order_submit_retries=max_order_submit_retries,
        # This broker instance will be only used for
        # script like flattening - no bid/ask data needed.
        bid_ask_raw_data_reader=None,
        log_dir=log_dir,
        sync_exchange=sync_exchange,
        async_exchange=async_exchange,
        # TODO(Nina): use `get_LimitPriceComputer_instance1()` to build the
        # `LimitPriceComputer` object.
        limit_price_computer=oliprcom.LimitPriceComputerUsingVolatility(
            volatility_multiple
        ),
        child_order_quantity_computer=ochorquco.DynamicSchedulingChildOrderQuantityComputer(),
    )
    return broker


def get_CcxtBroker_prod_instance1(
    strategy_id: str,
    market_data: mdata.MarketData,
    universe_version: str,
    secret_identifier: omssec.SecretIdentifier,
    broker_config: Dict[str, Any],
    log_dir: str,
) -> obccccbr.CcxtBroker:
    """
    Build a `CcxtBroker` for production.
    """
    # E.g., exchange_id = "binance"
    exchange_id = secret_identifier.exchange_id
    # E.g., stage = "preprod"
    stage = secret_identifier.stage
    # E.g., account_type = "trading"
    account_type = secret_identifier.account_type
    contract_type = "swap"
    portfolio_id = "ccxt_portfolio_1"
    # Build logger.
    logger = obcccclo.CcxtLogger(log_dir, mode="write")
    # Build ImClient.
    bid_ask_table = "ccxt_bid_ask_futures_raw"
    db_stage = stage
    im_client = icdcl.get_CcxtSqlRealTimeImClient_example1(
        universe_version, db_stage, bid_ask_table
    )
    # Build exchange.
    sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
        secret_identifier, contract_type, exchange_id, account_type
    )
    # Build bid_ask_raw_data_reader.
    bid_ask_raw_data_reader = imvcdcimrdc.get_bid_ask_realtime_raw_data_reader(
        stage, "CCXT", universe_version
    )
    max_order_submit_retries = 1
    # Build LimitPriceComputer.
    limit_price_computer_type = hdict.checked_get(
        broker_config, "limit_price_computer_type"
    )
    limit_price_computer_kwargs = hdict.checked_get(
        broker_config, "limit_price_computer_kwargs"
    )
    limit_price_computer = oliprcom.get_LimitPriceComputer_instance1(
        limit_price_computer_type, limit_price_computer_kwargs
    )
    # Build Broker.
    broker = obccccbr.CcxtBroker(
        exchange_id=exchange_id,
        account_type=account_type,
        portfolio_id=portfolio_id,
        contract_type=contract_type,
        secret_identifier=secret_identifier,
        strategy_id=strategy_id,
        market_data=market_data,
        universe_version=universe_version,
        stage=stage,
        logger=logger,
        bid_ask_im_client=im_client,
        max_order_submit_retries=max_order_submit_retries,
        bid_ask_raw_data_reader=bid_ask_raw_data_reader,
        log_dir=log_dir,
        sync_exchange=sync_exchange,
        async_exchange=async_exchange,
        limit_price_computer=limit_price_computer,
        child_order_quantity_computer=ochorquco.DynamicSchedulingChildOrderQuantityComputer(),
    )
    # Log the config of the broker instance.
    # TODO(Danya): Move inside the Broker init.
    # The broker is saved only in this instance function so we don't have to
    # provide a scratch directory for each test instance of the Broker object.
    logger.log_broker_config(broker.get_broker_config())
    return broker


# TODO(Nina): expose `LimitPriceComputer` type and kwargs instead of hardwiring
# them inside the function.
def get_CcxtReplayedExchangeBroker_instance1(
    strategy_id: str,
    market_data: mdata.MarketData,
    universe_version: str,
    secret_identifier: omssec.SecretIdentifier,
    fill_percents: Union[float, List[float]],
    log_dir: str,
    replayed_dir: str,
    volatility_multiple: Union[float, List[float]],
) -> obccccbr.CcxtBroker:
    """
    Build a `CcxtBroker` for production.
    """
    exchange_id = secret_identifier.exchange_id
    # E.g., exchange_id = "binance"
    stage = secret_identifier.stage
    # E.g., stage = "preprod"
    account_type = secret_identifier.account_type
    # E.g., account_type = "trading"
    contract_type = "futures"
    portfolio_id = "ccxt_portfolio_1"
    # Build logger.
    logger = obcccclo.CcxtLogger(log_dir, mode="write")
    # Read logged data.
    reader = obcccclo.CcxtLogger(replayed_dir, mode="read")
    log_data = reader.load_all_data(
        convert_to_dataframe=False, abort_on_missing_data=False
    )
    # Build replay exchange.
    replay_exchange = obcrccex.ReplayedCcxtExchange(
        ccxt_orders=log_data["ccxt_order_responses"],
        ccxt_fill_list=log_data["ccxt_fills"],
        ccxt_trades_list=log_data["ccxt_trades"],
        exchange_markets=log_data["exchange_markets"],
        leverage_info=log_data["leverage_info"],
        reduce_only_ccxt_orders=log_data["reduce_only_order_responses"],
        positions=log_data["positions"],
        balances=log_data["balances"],
        # This is just an arbitrary wait time to simulate time taken by exchange
        # to create an order. It should be > 0.
        delay_in_secs=1,
        event_loop=None,
        get_wall_clock_time=None,
        fill_percents=fill_percents,
    )
    sync_exchange = replay_exchange
    async_exchange = replay_exchange
    # Build replay data reader.
    bid_ask_raw_data_reader = obredare.ReplayDataReader(log_data["bid_ask_files"])
    max_order_submit_retries = 1
    # Build CcxtBroker.
    broker = obccccbr.CcxtBroker(
        exchange_id=exchange_id,
        account_type=account_type,
        portfolio_id=portfolio_id,
        contract_type=contract_type,
        secret_identifier=secret_identifier,
        strategy_id=strategy_id,
        market_data=market_data,
        universe_version=universe_version,
        stage=stage,
        logger=logger,
        bid_ask_im_client=None,
        max_order_submit_retries=max_order_submit_retries,
        bid_ask_raw_data_reader=bid_ask_raw_data_reader,
        log_dir=log_dir,
        sync_exchange=sync_exchange,
        async_exchange=async_exchange,
        limit_price_computer=oliprcom.LimitPriceComputerUsingVolatility(
            volatility_multiple
        ),
        child_order_quantity_computer=ochorquco.DynamicSchedulingChildOrderQuantityComputer(),
    )
    return broker


def get_CcxtReplayedFillsDataFrameBroker_instance1(
    fills_dir: str,
    strategy_id: str,
    market_data: mdata.MarketData,
    universe_version: str,
    stage: str,
    *,
    column_remap: Optional[Dict[str, str]] = None,
) -> obrfdabr.ReplayedFillsDataFrameBroker:
    """
    Build a `ReplayedFillsDataFrameBroker` that is compatible with a CCXT
    exchange.

    :param fills_dir: a dir where orders and fills logs are stored
    :param strategy_id: same as in the abstract `Broker` class
    :param market_data: same as in the abstract `Broker` class
    :param universe_version: same as in the abstract `Broker` class
    :param stage: same as in the abstract `Broker` class
    """
    oms_fills = obcccclo.load_oms_fills(fills_dir)
    market_info = obccccut.load_market_data_info()
    broker = obcdccbr.CcxtReplayedFillsDataFrameBroker(
        market_info=market_info,
        strategy_id=strategy_id,
        market_data=market_data,
        universe_version=universe_version,
        stage=stage,
        fills=oms_fills,
        column_remap=column_remap,
    )
    return broker


def get_CcxtBroker(
    secret_id: int,
    log_dir: str,
    universe: str,
    broker_config: Dict[str, Any],
    *,
    stage: str = "prod",
) -> obccccbr.CcxtBroker:
    """
    Get a `CcxtBroker` instance.

    :param stage: it is being used to construct the `SecretIdentifier` and also
    as a db_stage in a nested call `get_CcxtBroker_prod_instance1()`
    """
    # `MarketData` is not strictly needed to talk to exchange, but since it is
    #  required to init the `Broker` we pass something to make it work.
    asset_ids = None
    market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance2(
        asset_ids, universe
    )
    universe_version = universe
    strategy_id = "C1b"
    exchange_id = "binance"
    account_type = "trading"
    secret_identifier = omssec.SecretIdentifier(
        exchange_id, stage, account_type, secret_id
    )
    # Build CcxtBroker.
    ccxt_broker = get_CcxtBroker_prod_instance1(
        strategy_id,
        market_data,
        universe_version,
        secret_identifier,
        broker_config,
        log_dir,
    )
    return ccxt_broker


# TODO(Nina): expose `LimitPriceComputer` type and kwargs instead of hardwiring
# them inside the function.
def get_CcxtReplayedExchangeBroker(
    secret_id: int,
    log_dir: str,
    replayed_dir: str,
    market_data: mdata.MarketData,
    event_loop: asyncio.AbstractEventLoop,
    universe: str,
    fill_percents: Union[float, List[float]],
    volatility_multiple: Union[float, List[float]],
) -> obccccbr.CcxtBroker:
    """
    Get a `CcxtBroker` instance with Replayed Exchange.

    :param log_dir: the dir where the logs of the replayed experiment will
        be saved
    :param replayed_dir: the dir storing the experiment data
        The experiment dir is populated by running `run_ccxt_broker` for
        placing orders and it's used to initialize the ReplayedCcxtExchange
        for replaying
    """
    universe_version = universe
    strategy_id = "C1b"
    exchange_id = "binance"
    stage = "preprod"
    account_type = "trading"
    secret_identifier = omssec.SecretIdentifier(
        exchange_id, stage, account_type, secret_id
    )
    ccxt_broker = get_CcxtReplayedExchangeBroker_instance1(
        strategy_id,
        market_data,
        universe_version,
        secret_identifier,
        fill_percents,
        log_dir,
        replayed_dir,
        volatility_multiple,
    )
    return ccxt_broker


# #############################################################################
# Example Instances
# #############################################################################


def get_CcxtBroker_example1(
    market_data: mdata.MarketData,
    exchange_id: str,
    contract_type: str,
    stage: str,
    secret_id: int,
) -> obccccbr.CcxtBroker:
    """
    Construct a CcxtBroker for connecting to the exchange inside scripts.

    :param exchange_id: name of exchange, e.g. "binance"
    :param contract_type: e.g. "futures"
    :param stage: e.g. "preprod"
    :param secret_id: e.g., 1
    :return: initialized CCXT broker
    """
    # Set default broker values.
    # TODO(Danya): Pass the universe as a parameter.
    # TODO(Danya): Build MarketData inside the function.
    # See the TODO comment in `obrbrexa.get_DataFrameBroker_example1()`.
    universe = ivcu.get_latest_universe_version()
    portfolio_id = "ccxt_portfolio_1"
    strategy_id = "C1b"
    account_type = "trading"
    secret_identifier = ohsseide.SecretIdentifier(
        exchange_id, stage, account_type, secret_id
    )
    sync_exchange, async_exchange = obccccut.create_ccxt_exchanges(
        secret_identifier, contract_type, exchange_id, account_type
    )
    # Initialize the broker.
    broker = obccccbr.CcxtBroker(
        exchange_id=exchange_id,
        account_type=account_type,
        portfolio_id=portfolio_id,
        contract_type=contract_type,
        secret_identifier=secret_identifier,
        market_data=market_data,
        universe_version=universe,
        stage=stage,
        strategy_id=strategy_id,
        sync_exchange=sync_exchange,
        async_exchange=async_exchange,
        child_order_quantity_computer=ochorquco.StaticSchedulingChildOrderQuantityComputer(),
    )
    return broker


# TODO(Dan): -> `get_MockCcxtRealTimeImClientMarketData`?
def get_RealTimeImClientMarketData_example2(
    im_client: icdc.RealTimeImClient,
) -> mdata.RealTimeMarketData2:
    """
    Create a RealTimeMarketData2 to use as placeholder in Broker.

    This example is geared to work with CcxtBroker.
    """
    asset_id_col = "asset_id"
    asset_ids = [1464553467]
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    get_wall_clock_time = lambda: pd.Timestamp.now(tz="America/New_York")
    market_data = mdata.RealTimeMarketData2(
        im_client,
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
    )
    return market_data
