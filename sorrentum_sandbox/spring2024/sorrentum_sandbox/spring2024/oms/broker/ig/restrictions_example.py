"""
Import as:

import oms.broker.ig.restrictions_example as obigreex
"""

import logging

import pandas as pd

import helpers.hsql as hsql
import oms.broker.ig.restrictions as obrigres
import oms.db.oms_db as odbomdb

_LOG = logging.getLogger(__name__)


def get_Restrictions_example1(
    db_connection: hsql.DbConnection,
    *,
    table_name: str = odbomdb.RESTRICTIONS_TABLE_NAME,
) -> obrigres.Restrictions:
    strategy_id = "st1"
    account = "paper"
    asset_id_col = "asset_id"
    date_col = "tradedate"
    get_wall_clock_time = lambda: pd.Timestamp("2000-01-01 22:00:00.12345")
    restrictions = obrigres.Restrictions(
        strategy_id,
        account,
        asset_id_col,
        date_col,
        db_connection,
        table_name,
        get_wall_clock_time,
    )
    return restrictions
