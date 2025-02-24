"""
Import as:

import im.ib.metadata.ib_symbols as imimeibsy
"""

import functools
import logging
import string
from typing import List, Optional

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im.common.data.types as imcodatyp
import im.common.metadata.symbols as imcomesym

_LOG = logging.getLogger(__name__)


class IbSymbolUniverse(imcomesym.SymbolUniverse):
    """
    Store symbols available in IB and already downloaded.
    """

    def __init__(self, symbols_file: str) -> None:
        # Name of the file storing the symbol universe.
        self._symbols_file = symbols_file
        # List of the available symbols.
        self._symbols_list: Optional[List[str]] = None

    def get_all_symbols(self) -> List[imcomesym.Symbol]:
        """
        Return the symbol list from the file passed to the constructor.
        """
        if self._symbols_list is None:
            # Load the symbol list.
            hdbg.dassert_is_not(self._symbols_file, None)
            _LOG.debug("symbol_file=%s", self._symbols_file)
            self._symbols_list = self._parse_symbols_file(self._symbols_file)
        return self._symbols_list

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def _parse_symbols_file(symbols_file: str) -> List[imcomesym.Symbol]:
        """
        Read the passed file and return the list of symbols.
        """
        _LOG.info("Reading symbols from %s", symbols_file)
        # Prevent to transform values from "NA" to `np.nan`.
        if hs3.is_s3_path(symbols_file):
            # TODO(sonaal): confirm with juraj
            s3fs = hs3.get_s3fs("ck")
            kwargs = {"s3fs": s3fs}
        else:
            kwargs = {}
        stream, kwargs = hs3.get_local_or_s3_stream(symbols_file, **kwargs)
        df = hpandas.read_csv_to_df(
            stream, sep="\t", keep_default_na=False, na_values=["_"], **kwargs
        )
        _LOG.debug("head=%s", df.head())
        # The df looks like:
        # > csvlook im/ib/metadata/test/TestIbSymbolNamespace.test_parse_symbols_file1/input/test_symbols.csv
        # | market                                 | product   | s_title                        | ib_symbol    | symbol   | currency | url                                                                                                                   |
        # | ---------------------------------------| ----------| ------------------------------ | -------------| -------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
        # | CBOE C2 (CBOE2)                        | Options   | CALLON PETROLEUM CO            | CPE          | CPE      | USD      | https://ndcdyn.interactivebrokers.com/en/index.php?f=2222&exch=cboe2&showcategories=OPTGRP&p=&cc=&limit=100&page=8    |
        # | Chicago Board Options Exchange (CBOE)  | Options   | RESMED INC                     | RMD          | RMD      | USD      | https://ndcdyn.interactivebrokers.com/en/index.php?f=2222&exch=cboe&showcategories=OPTGRP&p=&cc=&limit=100&page=32    |
        # | ICE Futures U.S. (NYBOT)               | Futures   | Cotton No. 2                   | CT           | CT       | USD      | https://ndcdyn.interactivebrokers.com/en/index.php?f=2222&exch=nybot&showcategories=FUTGRP                            |
        # | Korea Stock Exchange (KSE)             | Futures   | SAMSUNG ELECTRO-MECHANICS CO   | 009150       | 123      | KRW      | https://ndcdyn.interactivebrokers.com/en/index.php?f=2222&exch=kse&showcategories=FUTGRP
        # Find unique parsed symbols.
        df = (
            df.apply(
                lambda row: IbSymbolUniverse._convert_df_to_row_to_symbol(
                    ib_ticker=row["ib_symbol"],
                    ib_exchange=row["market"],
                    ib_asset_class=row["product"],
                    ib_currency=row["currency"],
                ),
                axis=1,
            )
            .dropna()
            .unique()
        )
        symbols = list(df)
        symbols.sort()
        _LOG.debug("Parsed %s", hprint.perc(len(symbols), df.shape[0]))
        return symbols

    # TODO(gp): Add support also for the exchanges.
    # _S3_EXCHANGE_FILE_PREFIX = os.path.join(
    #    iidcon.S3_METADATA_PREFIX, "exchanges-"
    # )

    @staticmethod
    def _convert_df_to_row_to_symbol(
        ib_ticker: str,
        ib_exchange: str,
        ib_asset_class: str,
        ib_currency: str,
    ) -> Optional[imcomesym.Symbol]:
        """
        Build a Symbol from one row of the IB symbol file.
        """
        # Extract ticker.
        ticker = ib_ticker
        # Extract exchange.
        exchange = IbSymbolUniverse._extract_exchange_code_from_full_name(
            ib_exchange
        )
        # Extract asset class.
        # TODO(plyq): Not covered: `ETF`, `Forex`, `SP500`, expiring `Futures`.
        ib_to_asset = {
            "Futures": imcodatyp.AssetClass.Futures,
            "Indices": None,
            "Stocks": imcodatyp.AssetClass.Stocks,
            "Options": None,
            "Warrants": None,
            "Structured Products": None,
            "Bonds": None,
        }
        asset_class = ib_to_asset[ib_asset_class]
        # Extract contract type.
        # TODO(plyq): Support expiring contracts.
        contract_type = (
            imcodatyp.ContractType.Continuous
            if asset_class == imcodatyp.AssetClass.Futures
            else None
        )
        # Extract currency.
        currency = ib_currency
        # Construct the Symbol object, if possible.
        hprint.log(
            _LOG,
            logging.DEBUG,
            "ticker exchange asset_class contract_type currency",
        )
        if ib_ticker and exchange and asset_class and currency:
            symbol = imcomesym.Symbol(
                ticker=ticker,
                exchange=exchange,
                asset_class=asset_class,
                contract_type=contract_type,
                currency=currency,
            )
        else:
            # Not supported symbol.
            symbol = None
        return symbol

    @staticmethod
    def _extract_exchange_code_from_full_name(exchange: str) -> Optional[str]:
        """
        The exchange code is inside the brackets or it is one word uppercase in
        exchange name.

        E.g., Chicago Board Options Exchange (CBOE)
        """
        # Keep only what in brackets or string itself if there are no brackets.
        exchange: str = exchange.split("(")[-1].split(")")[0].strip()
        # Check if it is one uppercase word.
        if not set(exchange).issubset(string.ascii_uppercase):
            return None
        return exchange
