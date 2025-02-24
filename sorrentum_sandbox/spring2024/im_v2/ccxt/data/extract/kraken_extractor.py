"""
Import as:

import im_v2.ccxt.data.extract.kraken_extractor as imvcdekrex
"""

import logging
from typing import Any, Dict

import ccxt
import ccxt.pro as ccxtpro

import helpers.hdbg as hdbg
import im_v2.ccxt.data.extract.extractor as imvcdexex

_LOG = logging.getLogger(__name__)

# TODO(Sonaal): Covered in CmTask4327.
# TODO(gp): -> KrakenCcxtExtractor
class CcxtKrakenExtractor(imvcdexex.CcxtExtractor):

    def __init__(self, exchange_id: str, contract_type: str) -> None:
        # Stick to Kraken futures.
        hdbg.dassert_eq(exchange_id, "kraken")
        hdbg.dassert_eq(contract_type, "futures")
        super().__init__()

    @staticmethod
    def convert_currency_pair(
        currency_pair: str, *, exchange_id: str = None
    ) -> str:
        """
        Convert currency pair used for getting data from exchange.
        """
        # Stick to Kraken futures.
        hdbg.dassert_eq(exchange_id, "kraken")
        # Kraken futures uses a different naming convention for currency pairs.
        # For example, `BTC_USDT` is `BTC/USD:USD`.
        return currency_pair.split("/")[0]

    def log_into_exchange(self, async_: bool) -> ccxt.Exchange:
        """
        Log into Kraken via CCXT and return the corresponding `Exchange` object.

        :param async_: if True, returns CCXT pro Exchange with async support,
            classic, sync ccxt Exchange otherwise.
        """
        if self.contract_type == "futures":
            exchange_id = "krakenfutures"
        else:
            exchange_id = "kraken"
        exchange_params: Dict[str, Any] = {}
        # Enable rate limit.
        exchange_params["rateLimit"] = True
        module = ccxtpro if async_ else ccxt
        exchange_class = getattr(module, exchange_id)
        # Using API keys was deprecated in #2919.
        exchange = exchange_class(exchange_params)
        return exchange
