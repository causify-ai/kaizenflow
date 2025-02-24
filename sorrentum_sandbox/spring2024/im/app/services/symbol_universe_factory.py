"""
Produce SymbolUniverse objects.

Import as:

import im.app.services.symbol_universe_factory as imassunfa
"""

from typing import Any

import im.common.metadata.symbols as imcomesym


class SymbolUniverseFactory:
    @classmethod
    def get_symbol_universe(
        cls, provider: str, **kwargs: Any
    ) -> imcomesym.SymbolUniverse:
        """
        Get the universe of supported symbols for a given provider.

        :param provider: provider (e.g., "kibot", "ib", ...)
        :raises ValueError: if SymbolUniverse is not implemented for provider
        """
        symbol_universe: imcomesym.SymbolUniverse
        # TODO(plyq): Implement for kibot.
        if provider == "ib":
            import im.ib.metadata.ib_symbols as imimeibsy

            symbol_universe = imimeibsy.IbSymbolUniverse(**kwargs)
        else:
            raise ValueError(
                "Symbol universe for provider '%s' is not implemented" % provider
            )
        return symbol_universe
