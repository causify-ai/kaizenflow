"""
Import as:

import im_v2.common.universe.full_symbol as imvcufusy
"""

import logging
import re
from typing import List, Tuple, Union

import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# Store information about an exchange and a symbol (e.g., `binance::BTC_USDT`).
# Note that information about the vendor is carried in the `ImClient` itself,
# i.e. using `CcxtImClient` serves data from CCXT.
# Full symbols are transformed in `asset_ids` encoded by ints, by `ImClient` and
# used by `MarketData`.
FullSymbol = str


# TODO(gp): -> dassert_valid_full_symbol
def dassert_is_full_symbol_valid(
    full_symbol: Union[pd.Series, FullSymbol]
) -> None:
    """
    Check that a full symbol or all the symbols in a series have a valid
    format, i.e. `exchange::symbol`.

    Note: special symbols (except underscore) are not allowed.
    """
    # Only letters and underscores are allowed in exchanges.
    # Numbers are only allowed for symbols.
    exchange_pattern = "[a-zA-Z_]"
    symbol_pattern = "[a-zA-Z_0-9]"
    # Exchanges and symbols must be separated by `::`.
    regex_pattern = rf"{exchange_pattern}*::{symbol_pattern}*"
    # Set match pattern.
    if isinstance(full_symbol, pd.Series):
        full_match = full_symbol.str.fullmatch(
            regex_pattern, flags=re.IGNORECASE, na=False
        ).all()
    elif isinstance(full_symbol, FullSymbol):
        full_match = re.fullmatch(regex_pattern, full_symbol, re.IGNORECASE)
    else:
        raise TypeError(
            f"Input type is `{type(full_symbol)}` but should be either a string"
            " or a `pd.Series`"
        )
    # Valid full symbols must match the pattern.
    hdbg.dassert(
        full_match,
        "Incorrect full_symbol '%s', it must be `exchange::symbol`",
        full_symbol,
    )


def parse_full_symbol(
    full_symbol: Union[pd.Series, FullSymbol]
) -> Tuple[Union[pd.Series, str], Union[pd.Series, str]]:
    """
    Split a full symbol into exchange and symbol or a series of full symbols
    into series of exchanges and symbols.
    """
    dassert_is_full_symbol_valid(full_symbol)
    if isinstance(full_symbol, pd.Series):
        # Get a dataframe with exchange and symbol columns.
        df_exchange_symbol = full_symbol.str.split("::", expand=True)
        hdbg.dassert_eq(2, df_exchange_symbol.shape[1])
        # Get exchange and symbol series.
        exchange = df_exchange_symbol[0]
        symbol = df_exchange_symbol[1]
    else:
        # Split full symbol on exchange and symbol.
        exchange, symbol = full_symbol.split("::")
    return exchange, symbol


def build_full_symbol(
    exchange: Union[pd.Series, str], symbol: Union[pd.Series, str]
) -> Union[pd.Series, FullSymbol]:
    """
    Combine exchange and symbol in a full symbol or exchange and symbol series
    in a full symbol series.
    """
    if isinstance(exchange, pd.Series) and isinstance(symbol, pd.Series):
        hdbg.dassert_eq(exchange.shape[0], symbol.shape[0])
        full_symbol = exchange + "::" + symbol
    elif isinstance(exchange, str) and isinstance(symbol, str):
        full_symbol = f"{exchange}::{symbol}"
    else:
        raise TypeError(
            f"type(exchange) = `{type(exchange)}`,"
            f" type(symbol)= `{type(symbol)}` but both inputs should have"
            " the same type and be either strings or `pd.Series`"
        )
    dassert_is_full_symbol_valid(full_symbol)
    return full_symbol


def dassert_valid_full_symbols(full_symbols: List[FullSymbol]) -> None:
    """
    Verify that full symbols are passed in a list that has no duplicates.
    """
    hdbg.dassert_container_type(full_symbols, list, FullSymbol)
    hdbg.dassert_no_duplicates(full_symbols)
