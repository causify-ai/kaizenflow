"""
Import as:

import im.kibot.metadata.load.contract_symbol_mapping as imkmlcsyma
"""

import logging
from typing import List, Optional, Union

import helpers.hdbg as hdbg

from .kibot_metadata import KibotMetadata

_LOG = logging.getLogger(__name__)


class ContractSymbolMapping:
    def __init__(self) -> None:
        km = KibotMetadata()
        # Minutely and daily dataframes are identical except for the `Link`
        # column, so it does not matter, which one we load.
        self._metadata = km.get_metadata("1min")

    def get_contract(self, symbol: str) -> Optional[str]:
        """
        Get contract for Kibot symbol.

        :param symbol: value for `Kibot_symbol` column
        :return: `Exchange_abbreviation`:`Exchange_symbol` format contract
        """
        contract_metadata = self._metadata[
            self._metadata["Kibot_symbol"] == symbol
        ]
        if contract_metadata.empty:
            _LOG.warning("No metadata for %s symbol", symbol)
            return None
        hdbg.dassert_eq(contract_metadata.shape[0], 1)
        exchange = contract_metadata["Exchange_abbreviation"].iloc[0]
        if exchange is None:
            _LOG.warning("Exchange is `None` for %s symbol", symbol)
            return None
        exchange_symbol = contract_metadata["Exchange_symbol"].iloc[0]
        if exchange_symbol is None:
            _LOG.warning("Exchange symbol is `None` for %s symbol", symbol)
            return None
        return f"{exchange}:{exchange_symbol}"

    def get_kibot_symbol(self, contract: str) -> Optional[Union[str, List[str]]]:
        """
        Get Kibot symbol for contract.

        :param contract: `Exchange_abbreviation`:`Exchange_symbol`
        :return: Kibot symbol
        """
        contract_split = contract.split(":")
        hdbg.dassert_eq(len(contract_split), 2)
        exchange, exchange_symbol = contract_split
        contract_metadata = self._metadata[
            (self._metadata["Exchange_abbreviation"] == exchange)
            & (self._metadata["Exchange_symbol"] == exchange_symbol)
        ]
        if contract_metadata.empty:
            _LOG.warning("No metadata for %s contract", contract)
            return None
        # Seven exchange symbols are mapped to multiple contracts:
        # https://github.com/.../.../issues/2988#issuecomment-646351846.
        # TODO(Julia): Once the mapping is fixed, remove this.
        if contract_metadata.shape[0] > 1:
            if exchange_symbol == "T":
                # There are two contracts with this `Exchage_symbol`:
                # `CONTINUOUS UK FEED WHEAT CONTRACT` and
                # `CONTINUOUS WTI CRUDE CONTRACT`. Return WTI.
                return "CRD"
            if exchange_symbol == "C":
                # There are two contracts with
                # `CONTINUOUS EUA CONTRACT` and
                # `CONTINUOUS LONDON COCOA CONTRACT`. Return EUA.
                return "UX"
            kibot_symbol_list: List[str] = contract_metadata[
                "Kibot_symbol"
            ].tolist()
            return kibot_symbol_list
        kibot_symbol: str = contract_metadata["Kibot_symbol"].iloc[0]
        return kibot_symbol
