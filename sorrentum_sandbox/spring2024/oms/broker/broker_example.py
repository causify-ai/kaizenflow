"""
Import as:

import oms.broker.broker_example as obrbrexa
"""

import asyncio
from typing import Dict, List, Optional

import helpers.hsql as hsql
import im_v2.common.universe as ivcu
import market_data as mdata
import oms.broker.database_broker as obrdabro
import oms.broker.dataframe_broker as obdabro
import oms.broker.replayed_fills_dataframe_broker as obrfdabr
import oms.db.oms_db as odbomdb
import oms.fill as omfill


def get_DataFrameBroker_example1(
    event_loop: Optional[asyncio.AbstractEventLoop],
    *,
    market_data: Optional[mdata.MarketData] = None,
    timestamp_col: str = "end_datetime",
    column_remap: Optional[Dict[str, str]] = None,
) -> obdabro.DataFrameBroker:
    """
    Build a `DataFrameBroker` using a `MarketData`, unless specified.
    """
    # Build MarketData, if needed.
    if market_data is None:
        (
            market_data,
            _,
        ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
    # Build DataFrameBroker.
    strategy_id = "SAU1"
    account = "candidate"
    # TODO(*): Consider passing the universe version through the interface
    # in case we need to use one that is not the latest (see CmTask6159).
    universe_version = ivcu.get_latest_universe_version()
    stage = "preprod"
    broker = obdabro.DataFrameBroker(
        strategy_id,
        market_data,
        universe_version,
        stage,
        account=account,
        timestamp_col=timestamp_col,
        column_remap=column_remap,
    )
    return broker


def get_ReplayedFillsDataFrameBroker_example1(
    fills: List[List[omfill.Fill]],
    event_loop: Optional[asyncio.AbstractEventLoop],
    *,
    market_data: Optional[mdata.MarketData] = None,
    timestamp_col: str = "end_datetime",
    column_remap: Optional[Dict[str, str]] = None,
) -> obdabro.DataFrameBroker:
    """
    Build a `ReplayedFillsDataFrameBroker` using a `MarketData`, unless
    specified.
    """
    # Build MarketData, if needed.
    if market_data is None:
        (
            market_data,
            _,
        ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
    # Build DataFrameBroker.
    # This is just an artifact of the previous interface.
    strategy_id = "SAU1"
    account = "candidate"
    # See the TODO comment in `get_DataFrameBroker_example1()`.
    universe_version = ivcu.get_latest_universe_version()
    stage = "preprod"
    broker = obrfdabr.ReplayedFillsDataFrameBroker(
        strategy_id,
        market_data,
        universe_version,
        stage,
        fills=fills,
        account=account,
        timestamp_col=timestamp_col,
        column_remap=column_remap,
    )
    return broker


def get_DatabaseBroker_example1(
    event_loop: Optional[asyncio.AbstractEventLoop],
    db_connection: hsql.DbConnection,
    *,
    market_data: Optional[mdata.MarketData] = None,
    timestamp_col: str = "end_datetime",
    submitted_orders_table_name: str = odbomdb.SUBMITTED_ORDERS_TABLE_NAME,
    accepted_orders_table_name: str = odbomdb.ACCEPTED_ORDERS_TABLE_NAME,
    log_dir: Optional[str] = None,
) -> obrdabro.DatabaseBroker:
    """
    Build a `DatabaseBroker` using `MarketData`, unless specified.
    """
    # Build MarketData, if needed.
    if market_data is None:
        (
            market_data,
            _,
        ) = mdata.get_ReplayedTimeMarketData_example3(event_loop)
    # Build DatabaseBroker.
    strategy_id = "SAU1"
    account = "candidate"
    # See the TODO comment in `get_DataFrameBroker_example1()`.
    universe_version = ivcu.get_latest_universe_version()
    stage = "preprod"
    broker = obrdabro.DatabaseBroker(
        strategy_id,
        market_data,
        universe_version,
        stage,
        account=account,
        timestamp_col=timestamp_col,
        db_connection=db_connection,
        submitted_orders_table_name=submitted_orders_table_name,
        accepted_orders_table_name=accepted_orders_table_name,
        log_dir=log_dir,
    )
    return broker
