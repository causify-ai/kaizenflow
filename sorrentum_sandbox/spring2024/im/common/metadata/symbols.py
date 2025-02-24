"""
Import as:

import im.common.metadata.symbols as imcomesym
"""
import abc
import dataclasses
import logging
from typing import List, Optional, Tuple

import helpers.hdbg as hdbg
import helpers.hs3 as hs3
import im.common.data.load.file_path_generator as imcdlfpage
import im.common.data.types as imcodatyp

_LOG = logging.getLogger(__name__)


# TODO(*): Add unit test.
# TODO(*): If this represents a symbol we should use it in the other interfaces.
#  On the other side this would complicate the interfaces.
#  E.g., in DataLoader.read_data() the params are:
#    exchange: str,
#    symbol: str,
#    asset_class: vcdtyp.AssetClass,
#    contract_type: Optional[vcdtyp.ContractType] = None,
#  This class is modeled on IB, since Kibot doesn't support `currency`.
@dataclasses.dataclass
class Symbol:
    """
    Represent a specific Symbol in the universe supported by a provider.
    """

    # TODO(*): for symmetry with the rest of the code -> exchange, symbol,
    #  asset_class, contract_type, currency
    ticker: str
    exchange: str
    asset_class: imcodatyp.AssetClass
    contract_type: Optional[imcodatyp.ContractType]
    currency: str

    def __eq__(self, other: "Symbol") -> bool:
        hdbg.dassert_isinstance(other, Symbol)
        return self._to_string_tuple() == other._to_string_tuple()

    def __hash__(self) -> int:
        return hash(self._to_string_tuple())

    def __str__(self) -> str:
        string = "(%s)" % ", ".join(
            [str(part) for part in self._to_string_tuple()]
        )
        return string

    def __lt__(self, other: "Symbol") -> bool:
        hdbg.dassert_isinstance(other, Symbol)
        return self._to_string_tuple() < other._to_string_tuple()

    # TODO(*): matches
    def is_selected(
        self,
        ticker: Optional[str],
        exchange: Optional[str],
        asset_class: Optional[imcodatyp.AssetClass],
        contract_type: Optional[imcodatyp.ContractType],
        currency: Optional[str],
    ) -> bool:
        """
        Return if a symbol matches the passed parameters and `None` matches
        anything.
        """
        if ticker is not None and self.ticker != ticker:
            return False
        if exchange is not None and self.exchange != exchange:
            return False
        if asset_class is not None and self.asset_class != asset_class:
            return False
        if contract_type is not None and self.contract_type != contract_type:
            return False
        if currency is not None and self.currency != currency:
            return False
        return True

    def _to_string_tuple(
        self,
    ) -> Tuple[str, str, str, Optional[str], str]:
        return (
            self.ticker,
            self.exchange,
            self.asset_class.value,
            self.contract_type.value if self.contract_type is not None else None,
            self.currency,
        )


# TODO(*): -> AbstractSymbolUniverse
class SymbolUniverse(abc.ABC):
    """
    Store all the available symbols from a provider.
    """

    @abc.abstractmethod
    def get_all_symbols(self) -> List[Symbol]:
        """
        Return all the available symbols.
        """

    def get(
        self,
        ticker: Optional[str],
        exchange: Optional[str],
        asset_class: Optional[imcodatyp.AssetClass],
        contract_type: Optional[imcodatyp.ContractType],
        currency: Optional[str],
        # TODO(*): is_data_available
        is_downloaded: Optional[bool] = None,
        frequency: Optional[imcodatyp.Frequency] = None,
        path_generator: Optional[imcdlfpage.FilePathGenerator] = None,
    ) -> List[Symbol]:
        """
        Return all the available symbols based on different selection criteria.

        E.g. `get(exchange="GLOBEX", is_downloaded=True)` will return all the
        symbols of GLOBEX exchange, for which data is available.

        :param is_downloaded: is data available for the requested . `frequency` and
            `path_generator` are used only if `is_downloaded` is True.
        :param path_generator: generate path based on symbol
        :return: list of the matched symbols
        :raises ValueError: if parameters are not valid
        """
        matched_symbols = []
        if is_downloaded:
            if frequency is None or path_generator is None:
                raise ValueError(
                    "`frequency` and `path_generator` params are not specified"
                )
        for symbol in self.get_all_symbols():
            _LOG.debug("symbol=%s", symbol)
            if not symbol.is_selected(
                ticker=ticker,
                exchange=exchange,
                asset_class=asset_class,
                contract_type=contract_type,
                currency=currency,
            ):
                # Symbol doesn't satisfy the requested criteria.
                _LOG.debug("symbol=%s doesn't match the criteria")
                continue
            if is_downloaded:
                # Check if the path exists.
                path = path_generator.generate_file_path(
                    symbol=symbol.ticker,
                    frequency=frequency,
                    asset_class=symbol.asset_class,
                    contract_type=symbol.contract_type,
                    exchange=symbol.exchange,
                    currency=symbol.currency,
                    ext=imcodatyp.Extension.CSV,
                )
                # TODO(*): Generalize this so we don't have to rely on S3.
                s3fs = hs3.get_s3fs("ck")
                if not s3fs.exists(path):
                    _LOG.debug(
                        "symbol=%s doesn't have the corresponding file %s",
                        symbol,
                        path,
                    )
                    continue
            _LOG.debug("symbol=%s is part of the universe", symbol)
            matched_symbols.append(symbol)
        return matched_symbols
