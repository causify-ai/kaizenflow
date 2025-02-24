"""
Utilities for working with CCXT database.

Import as:

import im_v2.ccxt.db.utils as imvccdbut
"""

import logging

import pandas as pd

import helpers.hsql as hsql

_LOG = logging.getLogger(__name__)


# TODO(gp): -> get_create_ccxt_ohlcv_table_query()
def get_ccxt_ohlcv_create_table_query() -> str:
    """
    Get SQL query to create CCXT OHLCV spot table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_ohlcv_spot(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE,
            UNIQUE(timestamp, exchange_id,
            currency_pair, open, high, low, close, volume)
            )
            """
    return query


# TODO(gp): -> get_create_ccxt_ohlcv_futures_table_query()
def get_ccxt_ohlcv_futures_create_table_query() -> str:
    """
    Get SQL query to create CCXT OHLCV futures table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_ohlcv_futures(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE,
            UNIQUE(timestamp, exchange_id,
            currency_pair, open, high, low, close, volume)
            )
            """
    return query


def get_ccxt_create_bid_ask_raw_table_query() -> str:
    """
    Get SQL query to create CCXT bid/ask raw spot data table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_bid_ask_spot_raw(
            id BIGSERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            bid_size NUMERIC,
            bid_price NUMERIC,
            ask_size NUMERIC,
            ask_price NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            level INTEGER NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE
            )
            """
    return query


def get_ccxt_create_bid_ask_futures_raw_table_query() -> str:
    """
    Get SQL query to create CCXT bid/ask raw futures data table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_bid_ask_futures_raw(
            id BIGSERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            bid_size NUMERIC,
            bid_price NUMERIC,
            ask_size NUMERIC,
            ask_price NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            level INTEGER NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE
            )
            """
    return query


# TODO(Juraj): specify spot in the table name CmTask2804.
def get_ccxt_create_bid_ask_resampled_1min_table_query() -> str:
    """
    Get SQL query to create CCXT bid/ask spot data resampled to 1 min table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_bid_ask_resampled_1min(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            bid_size NUMERIC,
            bid_price NUMERIC,
            ask_size NUMERIC,
            ask_price NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            level INTEGER NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE
            )
            """
    return query


def get_ccxt_create_bid_ask_futures_resampled_1min_table_query() -> str:
    """
    Get SQL query to create CCXT bid/ask futures resampled to 1 min table.
    """
    query = """
    CREATE TABLE IF NOT EXISTS ccxt_bid_ask_futures_resampled_1min(
            id SERIAL PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            "bid_size_open" NUMERIC,
            "bid_size_close" NUMERIC,
            "bid_size_min" NUMERIC,
            "bid_size_max" NUMERIC,
            "bid_size_mean" NUMERIC,
            "bid_price_open" NUMERIC,
            "bid_price_close" NUMERIC,
            "bid_price_high" NUMERIC,
            "bid_price_low" NUMERIC,
            "bid_price_mean" NUMERIC,
            "ask_size_open" NUMERIC,
            "ask_size_close" NUMERIC,
            "ask_size_min" NUMERIC,
            "ask_size_max" NUMERIC,
            "ask_size_mean" NUMERIC,
            "ask_price_open" NUMERIC,
            "ask_price_close" NUMERIC,
            "ask_price_high" NUMERIC,
            "ask_price_low" NUMERIC,
            "ask_price_mean" NUMERIC,
            "bid_ask_midpoint_open" NUMERIC,
            "half_spread_open" NUMERIC,
            "log_size_imbalance_open" NUMERIC,
            "bid_ask_midpoint_close" NUMERIC,
            "half_spread_close" NUMERIC,
            "log_size_imbalance_close" NUMERIC,
            "bid_ask_midpoint_min" NUMERIC,
            "half_spread_min" NUMERIC,
            "log_size_imbalance_min" NUMERIC,
            "bid_ask_midpoint_max" NUMERIC,
            "half_spread_max" NUMERIC,
            "log_size_imbalance_max" NUMERIC,
            "bid_ask_midpoint_mean" NUMERIC,
            "half_spread_mean" NUMERIC,
            "log_size_imbalance_mean" NUMERIC,
            "bid_ask_midpoint_var_100ms" NUMERIC,
            "bid_ask_midpoint_autocovar_100ms" NUMERIC,
            "log_size_imbalance_var_100ms" NUMERIC,
            "log_size_imbalance_autocovar_100ms" NUMERIC,
            currency_pair VARCHAR(255) NOT NULL,
            exchange_id VARCHAR(255) NOT NULL,
            level INTEGER NOT NULL,
            end_download_timestamp TIMESTAMP WITH TIME ZONE,
            knowledge_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
    return query


def get_exchange_name_create_table_query() -> str:
    """
    Get SQL query to define CCXT crypto exchange names.
    """
    query = """
    CREATE TABLE IF NOT EXISTS exchange_name(
            exchange_id SERIAL PRIMARY KEY,
            exchange_name VARCHAR(255) NOT NULL
            )
            """
    return query


def get_currency_pair_create_table_query() -> str:
    """
    Get SQL query to define CCXT currency pairs.
    """
    query = """
    CREATE TABLE IF NOT EXISTS currency_pair(
            currency_pair_id SERIAL PRIMARY KEY,
            currency_pair VARCHAR(255) NOT NULL
            )
            """
    return query


# TODO(Juraj): This is currently not important for the local
#  stage of the DB but it helps to track the desired state of
#  the DB until we find a suitable solution to #CmTask3146.
def get_ccxt_create_bid_ask_futures_raw_index_query() -> str:
    """
    Get SQL query to define index on timestamp column.
    """
    query = """
    CREATE INDEX IF NOT EXISTS ccxt_bid_ask_futures_raw_timestamp_index
            ON ccxt_bid_ask_futures_raw(timestamp)
            """
    return query


# #############################################################################


def populate_exchange_currency_tables(conn: hsql.DbConnection) -> None:
    """
    Populate exchange name and currency pair tables with data from CCXT.

    :param conn: DB connection
    """
    # Extract the list of all CCXT exchange names.
    all_exchange_names = pd.Series(ccxt.exchanges)
    # Create a dataframe with exchange ids and names.
    df_exchange_names = all_exchange_names.reset_index()
    df_exchange_names.columns = ["exchange_id", "exchange_name"]
    # Insert exchange names dataframe in DB.
    hsql.execute_insert_query(conn, df_exchange_names, "exchange_name")
    # Create an empty list for currency pairs.
    currency_pairs = []
    # Extract all the currency pairs for each exchange and append them to the
    # currency pairs list.
    for exchange_name in all_exchange_names:
        # Some few exchanges require credentials for this info so we omit them.
        try:
            exchange_class = getattr(ccxt, exchange_name)()
            exchange_currency_pairs = list(exchange_class.load_markets().keys())
            currency_pairs.extend(exchange_currency_pairs)
        except (ccxt.AuthenticationError, ccxt.NetworkError, TypeError) as e:
            # Continue since these errors are related to denied access for 6
            # exchanges that we ignore.
            _LOG.warning("Skipping exchange_name='%s'", exchange_name)
            continue
    # Create a dataframe with currency pairs and ids.
    currency_pairs_srs = pd.Series(sorted(list(set(currency_pairs))))
    df_currency_pairs = currency_pairs_srs.reset_index()
    df_currency_pairs.columns = ["currency_pair_id", "currency_pair"]
    # Insert currency pairs dataframe in DB.
    hsql.execute_insert_query(conn, df_currency_pairs, "currency_pair")
