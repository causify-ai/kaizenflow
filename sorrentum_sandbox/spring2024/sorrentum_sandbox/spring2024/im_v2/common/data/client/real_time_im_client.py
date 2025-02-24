"""
Import as:

import im_v2.common.data.client.real_time_im_client as imvcdcrtimc
"""

import abc
import logging
from typing import Any, List, Optional, Tuple

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.common.data.client.abstract_im_clients as imvcdcaimcl
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)

# #############################################################################
# SqlRealTimeImClient
# #############################################################################


class RealTimeImClient(imvcdcaimcl.ImClient):
    """
    A realtime client for typing annotation.

    In practice all realtime clients use SQL backend.
    """


# TODO(Grisha): derive from `imvcdcaimcl.ImClientReadingMultipleSymbols`.
class SqlRealTimeImClient(RealTimeImClient):
    """
    Read data from a table of an SQL DB.
    """

    def __init__(
        self,
        vendor: str,
        universe_version: str,
        db_connection: hsql.DbConnection,
        table_name: str,
        *,
        resample_1min: bool = False,
    ) -> None:
        _LOG.debug(hprint.to_str("db_connection table_name"))
        # These parameters are needed to get the universe which is needed to init
        # the parent class so they go before the parent's init.
        self._table_name = table_name
        self._db_connection = db_connection
        super().__init__(vendor, universe_version, resample_1min=resample_1min)

    @staticmethod
    def get_metadata() -> pd.DataFrame:
        """
        Return metadata.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        pass

    def get_universe(self) -> List[ivcu.FullSymbol]:
        """
        See the description in the parent class.

        The method is overriden to make it possible to infer universe
        from available data for this specific class.
        """
        if self._universe_version == "infer_from_data":
            # Infer universe from data.
            universe = self.infer_universe_from_data()
        else:
            # Use the parent class implementation.
            universe = super().get_universe()
        return universe

    def infer_universe_from_data(self) -> List[ivcu.FullSymbol]:
        """
        Infer universe from available data.

        :return: universe as full symbols
        """
        # Extract DataFrame with unique combinations of `exchange_id`,
        # `currency_pair`.
        query = (
            f"SELECT DISTINCT exchange_id, currency_pair FROM {self._table_name}"
        )
        currency_exchange_df = hsql.execute_query_to_df(
            self._db_connection, query
        )
        # Merge these columns to the general `full_symbol` format.
        full_symbols = ivcu.build_full_symbol(
            currency_exchange_df["exchange_id"],
            currency_exchange_df["currency_pair"],
        )
        # Convert to list.
        full_symbols = full_symbols.to_list()
        _LOG.debug(hprint.to_str("full_symbols"))
        return full_symbols

    # /////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////

    # TODO(Danya): Propagate usage of `columns` parameter here and in descendant
    #  classes.
    def _read_data(
        self,
        full_symbols: List[ivcu.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        columns: Optional[List[str]],
        *,
        full_symbol_col_name: Optional[str] = None,
        # Extra arguments for building a query.
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Create a select query and load data from database.

        Extra parameters for building a query can also be passed,
        see keyword args for `_build_select_query`.

        :param full_symbols: a list of full symbols, e.g., `["ftx::BTC_USDT"]`
        :param start_ts: beginning of the time interval
        :param end_ts: end of the time interval
        :param full_symbol_col_name: name of column containing full symbols
        :return:
        """
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts columns full_symbol_col_name kwargs"
            )
        )
        # Parse symbols into exchange and currency pair.
        parsed_symbols = [ivcu.parse_full_symbol(s) for s in full_symbols]
        # Convert timestamps to epochs.
        if start_ts:
            start_unix_epoch = hdateti.convert_timestamp_to_unix_epoch(start_ts)
        else:
            start_unix_epoch = start_ts
        if end_ts:
            end_unix_epoch = hdateti.convert_timestamp_to_unix_epoch(end_ts)
        else:
            end_unix_epoch = end_ts
        # Read data from DB.
        select_query = self._build_select_query(
            parsed_symbols, start_unix_epoch, end_unix_epoch, **kwargs
        )
        data = hsql.execute_query_to_df(self._db_connection, select_query)
        _LOG.debug(
            "-> df after execute_query_to_df=\n%s", hpandas.df_to_str(data)
        )
        # Add a full symbol column.
        full_symbol_col_name = self._get_full_symbol_col_name(
            full_symbol_col_name
        )
        data[full_symbol_col_name] = ivcu.build_full_symbol(
            data["exchange_id"], data["currency_pair"]
        )
        data = data.drop(["exchange_id", "currency_pair"], axis=1)
        # Convert timestamp column with Unix epoch to timestamp format.
        data[self._timestamp_col_name] = data[self._timestamp_col_name].apply(
            hdateti.convert_unix_epoch_to_timestamp
        )
        # Set timestamp column as index.
        data = data.set_index(self._timestamp_col_name)
        # TODO(Dan): Move column filtering to the SQL query.
        if columns is None:
            columns = data.columns
        hdbg.dassert_is_subset(columns, data.columns.to_list())
        data = data[columns]
        return data

    def _build_select_query(
        self,
        parsed_symbols: List[Tuple],
        start_unix_epoch: Optional[int],
        end_unix_epoch: Optional[int],
        *,
        columns: Optional[List[str]] = None,
        ts_col_name: Optional[str] = "timestamp",
        left_close: bool = True,
        right_close: bool = True,
        limit: Optional[int] = None,
    ) -> str:
        """
        Build a SELECT query for SQL DB.

        Time is provided as unix epochs in ms, the time range
        is considered closed on both sides, i.e. [1647470940000, 1647471180000]

        Example of a full query:
        ```
        SELECT * FROM ccxt_ohlcv WHERE timestamp >= 1647470940000
            AND timestamp <= 1647471180000
            AND ((exchange_id='binance' AND currency_pair='AVAX_USDT')
            OR (exchange_id='ftx' AND currency_pair='BTC_USDT'))
        ```

        :param parsed_symbols: List of tuples, e.g. [(`exchange_id`, `currency_pair`),..]
        :param start_unix_epoch: start of time period in ms, e.g. 1647470940000
        :param end_unix_epoch: end of the time period in ms, e.g. 1647471180000
        :param columns: columns to select from `table_name`
        - `None` means all columns.
        :param ts_col_name: name of timestamp column
        :param left_close: if operator for `start_unix_epoch` is either > or >=
        :param right_close: if operator for `end_unix_epoch` is either < or <=
        :param limit: number of rows to return
        :return: SELECT query for SQL data
        """
        _LOG.debug(
            hprint.to_str(
                "parsed_symbols start_unix_epoch end_unix_epoch columns ts_col_name left_close right_close limit"
            )
        )
        hdbg.dassert_container_type(
            obj=parsed_symbols,
            container_type=List,
            elem_type=tuple,
            msg="`parsed_symbols` should be a list of tuple",
        )
        table_columns = hsql.get_table_columns(
            self._db_connection, self._table_name
        )
        _LOG.debug(hprint.to_str("table_columns"))
        if columns is None:
            columns = table_columns
        hdbg.dassert_is_subset(columns, table_columns)
        # Add columns to the SELECT query
        columns_as_str = ",".join(columns)
        # Build a SELECT query.
        select_query = f"SELECT {columns_as_str} FROM {self._table_name} WHERE "
        # Build a WHERE query.
        # TODO(Danya): Generalize to hsql with dictionary input.
        where_clause = []
        if start_unix_epoch:
            hdbg.dassert_isinstance(
                start_unix_epoch,
                int,
            )
            operator = ">=" if left_close else ">"
            where_clause.append(f"{ts_col_name} {operator} {start_unix_epoch}")
        if end_unix_epoch:
            hdbg.dassert_isinstance(
                end_unix_epoch,
                int,
            )
            operator = "<=" if right_close else "<"
            where_clause.append(f"{ts_col_name} {operator} {end_unix_epoch}")
        if start_unix_epoch and end_unix_epoch:
            hdbg.dassert_lte(
                start_unix_epoch,
                end_unix_epoch,
                msg="Start unix epoch should be smaller than end.",
            )
        # Create conditions for getting values by exchange_id and currency_pair
        # In the end there should be something like:
        # (exchange_id='binance' AND currency_pair='ADA_USDT') OR (exchange_id='ftx' AND currency_pair='BTC_USDT') # pylint: disable=line-too-long
        exchange_currency_conditions = [
            f"(exchange_id='{exchange_id}' AND currency_pair='{currency_pair}')"
            for exchange_id, currency_pair in parsed_symbols
            if exchange_id and currency_pair
        ]
        if exchange_currency_conditions:
            # Add OR conditions between each pair of `exchange_id` and `currency_pair`
            where_clause.append(
                "(" + " OR ".join(exchange_currency_conditions) + ")"
            )
        # Build whole query.
        query = select_query + " AND ".join(where_clause)
        if limit:
            query += f" LIMIT {limit}"
        _LOG.debug(hprint.to_str("query"))
        return query

    # TODO(Grisha): does not work in the current architecture, we cannot integrate
    # vendor-specific (e.g., CCXT-Binance) behaviours when a function
    # overrides the base
    # class method.
    # def _get_start_end_ts_for_symbol(
    #     self, full_symbol: ivcu.FullSymbol, mode: str
    # ) -> pd.Timestamp:
    #     """
    #     Select a maximum/minimum timestamp for the given symbol.

    #     Overrides the method in parent class to utilize
    #     the MIN/MAX SQL operators.

    #     :param full_symbol: unparsed full_symbol value
    #     :param mode: 'start' or 'end'
    #     :return: min or max value of 'timestamp' column.
    #     """
    #     _LOG.debug(hprint.to_str("full_symbol"))
    #     exchange, currency_pair = ivcu.parse_full_symbol(full_symbol)
    #     # Build a MIN/MAX query.
    #     if mode == "start":
    #         query = (
    #             f"SELECT MIN(timestamp) from {self._table_name}"
    #             f" WHERE currency_pair='{currency_pair}'"
    #             f" AND exchange_id='{exchange}'"
    #         )
    #     elif mode == "end":
    #         query = (
    #             f"SELECT MAX(timestamp) from {self._table_name}"
    #             f" WHERE currency_pair='{currency_pair}'"
    #             f" AND exchange_id='{exchange}'"
    #         )
    #     else:
    #         raise ValueError("Invalid mode='%s'" % mode)
    #     # TODO(Danya): factor out min/max as helper function.
    #     # Load the target timestamp as unix epoch.
    #     timestamp = hsql.execute_query_to_df(self._db_connection, query).loc[0][0]
    #     # Convert to `pd.Timestamp` type.
    #     timestamp = hdateti.convert_unix_epoch_to_timestamp(timestamp)
    #     hdateti.dassert_has_specified_tz(timestamp, ["UTC"])
    #     return timestamp
