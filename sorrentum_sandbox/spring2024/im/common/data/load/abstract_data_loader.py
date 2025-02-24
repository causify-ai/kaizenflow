"""
Import as:

import im.common.data.load.abstract_data_loader as imcdladalo
"""

import abc
import functools
from typing import Optional

import pandas as pd
import psycopg2
import psycopg2.extensions as pexten

import helpers.hdbg as hdbg
import im.common.data.types as imcodatyp


class AbstractDataLoader(abc.ABC):
    """
    Read data of a given frequency for symbols of a given asset and exchange.
    """

    @abc.abstractmethod
    def read_data(
        self,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        contract_type: Optional[imcodatyp.ContractType] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        nrows: Optional[int] = None,
        normalize: bool = True,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Read data.

        :param exchange: name of the exchange
        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param contract_type: required for asset class of type `futures`
        :param unadjusted: required for asset classes of type `stocks` & `etfs`
        :param nrows: if not None, return only the first nrows of the data
        :param normalize: whether to normalize the dataframe based on frequency
        :param start_ts: start time of data to read
        :param end_ts: end time of data to read
        :return: a dataframe with the data
        """


class AbstractS3DataLoader(AbstractDataLoader):
    """
    Interface for class reading data from S3.
    """

    def __init__(self) -> None:
        self._normalizer_dict = {
            imcodatyp.Frequency.Daily: self._normalize_daily,
            imcodatyp.Frequency.Hourly: self._normalize_1_hour,
            imcodatyp.Frequency.Minutely: self._normalize_1_min,
        }

    def normalize(
        self, df: pd.DataFrame, frequency: imcodatyp.Frequency
    ) -> pd.DataFrame:
        """
        Apply a normalizer function based on the frequency.

        :param df: a dataframe to be normalized
        :param frequency: frequency of the data
        :return: the normalized dataframe
        :raises AssertionError: if frequency is not supported
        """
        hdbg.dassert_in(
            frequency,
            self._normalizer_dict,
            "Frequency %s is not supported",
            frequency,
        )
        normalizer = self._normalizer_dict[frequency]
        return normalizer(df)

    # TODO(*): -> _normalize_minute_data
    @staticmethod
    @abc.abstractmethod
    def _normalize_1_min(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize minutely data.

        :param df: pandas df to normalize
        :return: normalized pandas df
        """

    @staticmethod
    @abc.abstractmethod
    def _normalize_1_hour(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize hourly data.

        :param df: pandas df to normalize
        :return: normalized pandas df
        """

    @staticmethod
    @abc.abstractmethod
    def _normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize daily data.

        :param df: pandas df to normalize
        :return: normalized pandas df
        """


class AbstractSqlDataLoader(AbstractDataLoader):
    """
    Interface class loading provider data from an SQL backend.
    """

    def __init__(
        self, dbname: str, user: str, password: str, host: str, port: int
    ):
        self.conn: psycopg2.extensions.connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
        )

    # TODO(*): Factor out common code.
    def get_symbol_id(
        self,
        symbol: str,
    ) -> int:
        """
        Get primary key (id) by its symbol code (e.g., ES).

        :param symbol: symbol code, e.g. GOOGL
        :return: primary key (id)
        """
        symbol_id = -1
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute("SELECT id FROM Symbol WHERE code = %s", [symbol])
                if curs.rowcount:
                    (_symbol_id,) = curs.fetchone()
                    symbol_id = _symbol_id
        if symbol_id == -1:
            hdbg.dfatal(f"Could not find Symbol ${symbol}")
        return symbol_id

    def get_exchange_id(
        self,
        exchange: str,
    ) -> int:
        """
        Get primary key (id) of the exchange by its name.

        :param exchange: name of the Exchange entry as defined in DB
        :return: primary key (id)
        """
        exchange_id = -1
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "SELECT id FROM Exchange WHERE name = %s", [exchange]
                )
                if curs.rowcount:
                    (_exchange_id,) = curs.fetchone()
                    exchange_id = _exchange_id
        if exchange_id == -1:
            hdbg.dfatal(f"Could not find Exchange ${exchange}")
        return exchange_id

    def get_trade_symbol_id(
        self,
        symbol_id: int,
        exchange_id: int,
    ) -> int:
        """
        Get primary key (id) of the TradeSymbol entry by its respective Symbol
        and Exchange ids.

        :param symbol_id: id of Symbol
        :param exchange_id: id of Exchange
        :return: primary key (id)
        """
        trade_symbol_id = -1
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "SELECT id FROM TradeSymbol "
                    "WHERE symbol_id = %s AND exchange_id = %s",
                    [symbol_id, exchange_id],
                )
                if curs.rowcount:
                    (_trade_symbol_id,) = curs.fetchone()
                    trade_symbol_id = _trade_symbol_id
        if trade_symbol_id == -1:
            hdbg.dfatal(
                f"Could not find Trade Symbol with "
                f"symbol_id={symbol_id} and exchange_id={exchange_id}"
            )
        return trade_symbol_id

    # TODO(plyq): Uncomment once #1047 will be resolved.
    # @hcache.cache()
    # Use lru_cache for now.
    @functools.lru_cache(maxsize=64)
    def read_data(
        self,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        contract_type: Optional[imcodatyp.ContractType] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        nrows: Optional[int] = None,
        normalize: bool = True,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Read data.
        """
        return self._read_data(
            exchange=exchange,
            symbol=symbol,
            frequency=frequency,
            nrows=nrows,
        )

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    @abc.abstractmethod
    def _get_table_name_by_frequency(frequency: imcodatyp.Frequency) -> str:
        """
        Get table name by predefined frequency.

        :param frequency: a predefined frequency
        :return: table name in DB
        """

    def _read_data(
        self,
        exchange: str,
        symbol: str,
        frequency: imcodatyp.Frequency,
        nrows: Optional[int] = None,
    ) -> pd.DataFrame:
        exchange_id = self.get_exchange_id(exchange)
        symbol_id = self.get_symbol_id(symbol)
        trade_symbol_id = self.get_trade_symbol_id(symbol_id, exchange_id)
        table_name = self._get_table_name_by_frequency(frequency)
        limit = pexten.AsIs("ALL")
        # TODO(*): Add LIMIT in SQL query only if nrows is specified.
        if nrows:
            hdbg.dassert_lte(1, nrows)
            limit = nrows
        query = "SELECT * FROM %s WHERE trade_symbol_id = %s LIMIT %s"
        df = pd.read_sql_query(
            query,
            self.conn,
            params=[pexten.AsIs(table_name), trade_symbol_id, limit],
        )
        return df
