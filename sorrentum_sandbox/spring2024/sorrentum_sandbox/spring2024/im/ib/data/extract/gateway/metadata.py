"""
Import as:

import im.ib.data.extract.gateway.metadata as imidegame
"""

# TODO(*): Move to ib/medata and rename contract_metadata.py
import logging
import os
from typing import List

import ib_insync
import pandas as pd

import helpers.hio as hio
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)


class IbMetadata:
    def __init__(self, file_name: str) -> None:
        self.file_name = file_name

    def load(self) -> pd.DataFrame:
        """
        Load the data generated through update.

        The df looks like:
        conId,secType,symbol,lastTradeDateOrContractMonth,strike,right,multiplier,
            exchange,primaryExchange,currency,localSymbol,tradingClass,
            includeExpired,secIdType,secId,comboLegsDescrip,comboLegs,
            deltaNeutralContract
        81596321,FUT,NG,20190327,0.0,,10000,NYMEX,,USD,NGJ9,NG,False,,,,[],
        81596321,FUT,NG,20190327,0.0,,10000,QBALGO,,USD,NGJ9,NG,False,,,,[],
        81596324,FUT,NG,20190426,0.0,,10000,NYMEX,,USD,NGK9,NG,False,,,,[],
        """
        if os.path.exists(self.file_name):
            df = pd.read_csv(self.file_name, index_col=0)
            df = self._clean(df)
        else:
            _LOG.debug("No file '%s'", self.file_name)
            df = pd.DataFrame()
        return df

    def update(
        self,
        ib: ib_insync.ib.IB,
        contracts: List[ib_insync.Contract],
        append: bool = False,
    ) -> None:
        """
        Update metadata in `file_name` for the given contracts.

        :param append: if True it keeps appending
        """
        dfs = []
        for contract in contracts:
            df_tmp = imidegaut.get_contract_details(ib, contract)
            dfs.append(df_tmp)
        df = pd.concat(dfs, axis=0)
        #
        if append:
            df_tmp = self.load()
            df = pd.concat([df_tmp, df], axis=0)
        else:
            _LOG.warning("Resetting data in file '%s'", self.file_name)
        #
        df = self._clean(df)
        #
        hio.create_enclosing_dir(self.file_name, incremental=True)
        df.to_csv(self.file_name)

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df.sort_values(["conId", "exchange"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        _LOG.debug("df=\n%s", df.head())
        return df
