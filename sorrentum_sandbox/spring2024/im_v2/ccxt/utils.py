"""
Import as:

import im_v2.ccxt.utils as imv2ccuti
"""
import re

import helpers.hdbg as hdbg


def convert_currency_pair_to_ccxt_format(
    currency_pair: str,
    exchange: str,
    contract_type: str,
) -> str:
    """
    Convert currency pair used for getting data from exchange.

    :param currency_pair: currency pair, e.g. "BTC_USDT"
    :param exchange_id: exchange from where the data is fetched
    :param contract_type: type of contract e.g. "spot" or "futures"
    """
    hdbg.dassert_in(
        "_",
        currency_pair,
        f"The currency_pair '{currency_pair}' does not match the format '{{str1}}_{{str2}}'.",
    )
    # Unlike other exchanges, Kraken only support spot and has different exchange
    # for futures Krakenfutures.
    if exchange == "kraken":
        hdbg.dassert_eq(contract_type, "spot")
    if exchange == "krakenfutures":
        hdbg.dassert_eq(contract_type, "futures")
    if contract_type == "futures" or contract_type == "swap":
        # In the newer CCXT version symbols are specified using the following format:
        # BTC/USDT:USDT where the :USDT refers to the currency in which the futures contract
        # are settled.
        settlement_coin = currency_pair.split("_")[1]
        currency_pair = currency_pair.replace("_", "/")
        converted_pair = f"{currency_pair}:{settlement_coin}"
    else:
        # E.g., USD_BTC -> USD/BTC.
        converted_pair = currency_pair.replace("_", "/")
    return converted_pair


def convert_full_symbol_to_binance_symbol(
    full_symbol: str, settling_currency: str = "USDT"
) -> str:
    """
    Convert full symbol to Binance symbol.

    The Binance symbol consists of the asset pair, e.g. BTC/USDT, and a settling currency, e.g. USDT.

    :param full_symbol: full symbol, e.g. "binance::AVAX_USDT"
    :return: Binance symbol, e.g. "AVAX/USDT:USDT"
    """
    # Check if the `full_symbol` matches the format.
    match = re.match(r"\b\w+::[A-Z\d]+_[A-Z\d]+\b", full_symbol)
    hdbg.dassert_is_not(
        match,
        None,
        f"The full_symbol '{full_symbol}' does not match the format '{{exchange}}::{{CURRENCY1}}_{{CURRENCY2}}'.",
    )
    # Remove the exchange name, e.g. "binance::AVAX_USDT" -> "AVAX_USDT".
    symbol = full_symbol.split("::")[1]
    # Convert the symbol to the Binance format, e.g. "AVAX_USDT" -> "AVAX/USDT:USDT".
    binance_symbol = symbol.replace("_", "/") + f":{settling_currency}"
    return binance_symbol
