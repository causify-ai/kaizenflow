"""
Import as:

import dataflow.system.source_nodes as dtfsysonod
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.core.utils as dtfcorutil
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im.kibot as vkibot
import market_data as mdata


_LOG = logging.getLogger(__name__)


# #############################################################################


def data_source_node_factory(
    nid: dtfcore.NodeId,
    source_node_name: str,
    source_node_kwargs: Dict[str, Any],
) -> dtfcore.DataSource:
    """
    Initialize the appropriate data source node.

    The use case for this function is to create nodes depending on config parameters
    leaving the pipeline DAG unchanged.

    There are several types of nodes:
    - synthetic data generators, e.g.,
        - `ArmaDataSource`
        - `MultivariateNormalDataSource`
    - real-time data sources e.g.,
        - `RealTimeDataSource` (which uses a full-fledged `MarketData`)
    - data generators using data from disk
        - `DiskDataSource` (which reads CSV and PQ files)
    - data generators using pluggable functions
        - `FunctionDataSource` (which uses a passed function to create data)

    - Note that the same goal can be achieved using different nodes in multiple
      ways, e.g.,
      - Synthetic data or data from disk can be generated using the specialized
        node or passing a function to `FunctionDataSource`
      - One could inject synthetic data in the IM and go through the
        high-fidelity data pipeline or mock a later interface

    - In general we want to funnel data sources through `RealTimeDataSource`
      since these nodes have the closest behavior to real-time data sources

    :param nid: node identifier
    :param source_node_name: short name for data source node type
    :param source_node_kwargs: kwargs for data source node
    :return: data source node of appropriate type instantiated with kwargs
    """
    hdbg.dassert_ne(source_node_name, "")
    # TODO(gp): To simplify we can use the name of the class (e.g., "ArmaDataSource"
    #  instead of "arma"), so we don't have to use another level of mnemonics.
    if source_node_name == "arma":
        ret = dtfcore.ArmaDataSource(nid, **source_node_kwargs)
    elif source_node_name == "multivariate_normal":
        ret = dtfcore.MultivariateNormalDataSource(nid, **source_node_kwargs)
    elif source_node_name == "RealTimeDataSource":
        ret = RealTimeDataSource(nid, **source_node_kwargs)
    elif source_node_name == "HistoricalDataSource":
        ret = HistoricalDataSource(nid, **source_node_kwargs)
    elif source_node_name == "disk":
        ret = dtfcore.DiskDataSource(nid, **source_node_kwargs)
    elif source_node_name == "FunctionDataSource":
        ret = dtfcore.FunctionDataSource(nid, **source_node_kwargs)
    elif source_node_name == "kibot":
        # TODO(gp): This should go through RealTimeDataSource.
        ret = KibotDataReader(nid, **source_node_kwargs)
    elif source_node_name == "kibot_equities":
        # TODO(gp): This should go through RealTimeDataSource.
        ret = KibotEquityReader(nid, **source_node_kwargs)
    elif source_node_name == "kibot_multi_col":
        # TODO(gp): This should go through RealTimeDataSource.
        ret = KibotColumnReader(nid, **source_node_kwargs)
    elif source_node_name == "DummyDataSource":
        ret = dtfcore.DummyDataSource(nid, **source_node_kwargs)
    else:
        raise ValueError(f"Unsupported data source node {source_node_name}")
    return ret


# #############################################################################

# TODO(gp): Not sure about all these nodes below. We have too many ways of
#  doing the same thing. They go through IM. Then there are other nodes that
#  go directly to disk bypassing IM.

# TODO(gp): Move all the nodes somewhere else (e.g., sources.py)?


def _process_timestamp(
    timestamp: Optional[hdateti.Datetime],
) -> Optional[pd.Timestamp]:
    if timestamp is pd.NaT:
        timestamp = None
    if timestamp is not None:
        timestamp = pd.Timestamp(timestamp)
        hdbg.dassert_is(timestamp.tz, None)
    return timestamp


def load_kibot_data(
    symbol: str,
    frequency: Union[str, vkibot.Frequency],
    contract_type: Union[str, vkibot.ContractType],
    start_date: Optional[hdateti.Datetime] = None,
    end_date: Optional[hdateti.Datetime] = None,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    frequency = (
        vkibot.Frequency(frequency) if isinstance(frequency, str) else frequency
    )
    contract_type = (
        vkibot.ContractType(contract_type)
        if isinstance(contract_type, str)
        else contract_type
    )
    start_date = _process_timestamp(start_date)
    end_date = _process_timestamp(end_date)
    df_out = vkibot.KibotS3DataLoader().read_data(
        exchange="CME",
        aws_profile="am",
        asset_class=vkibot.AssetClass.Futures,
        frequency=frequency,
        contract_type=contract_type,
        symbol=symbol,
        nrows=nrows,
    )
    df_out = df_out.loc[start_date:end_date]
    return df_out


# TODO(gp): Maybe consolidate KibotDataReader and KibotColumnReader.


# TODO(gp): -> KibotFuturesDataReader
class KibotDataReader(dtfcore.DataSource):
    def __init__(
        self,
        nid: dtfcore.NodeId,
        symbol: str,
        frequency: Union[str, vkibot.Frequency],
        contract_type: Union[str, vkibot.ContractType],
        start_date: Optional[hdateti.Datetime] = None,
        end_date: Optional[hdateti.Datetime] = None,
        nrows: Optional[int] = None,
    ) -> None:
        """
        Create data source node outputting single instrument data from Kibot.

        :param symbol, frequency, contract_type:
            define the Kibot data to load with the same meaning as in get_kibot_path
        :param start_date: data start date in ET, included
        :param end_date: data end date in Et, included
        :param nrows: same as Kibot read_data
        """
        super().__init__(nid)
        self._symbol = symbol
        self._frequency = frequency
        self._contract_type = contract_type
        self._start_date = start_date
        self._end_date = end_date
        self._nrows = nrows

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        df = load_kibot_data(
            symbol=self._symbol,
            frequency=self._frequency,
            contract_type=self._contract_type,
            start_date=self._start_date,
            end_date=self._end_date,
            nrows=self._nrows,
        )
        self.df = df


# #############################################################################


# TODO(gp): Move reading only a subset of columns into KibotS3DataLoader.
#  If we use Parquet we can avoid to read useless data for both time and
#  columns.


class KibotColumnReader(dtfcore.DataSource):
    def __init__(
        self,
        nid: dtfcore.NodeId,
        symbols: List[str],
        frequency: Union[str, vkibot.Frequency],
        contract_type: Union[str, vkibot.ContractType],
        col: str,
        start_date: Optional[hdateti.Datetime] = None,
        end_date: Optional[hdateti.Datetime] = None,
        nrows: Optional[int] = None,
    ) -> None:
        """
        Same interface as KibotDataReader but with multiple symbols.
        """
        super().__init__(nid)
        self._symbols = symbols
        self._frequency = (
            vkibot.Frequency(frequency)
            if isinstance(frequency, str)
            else frequency
        )
        self._contract_type = (
            vkibot.ContractType(contract_type)
            if isinstance(contract_type, str)
            else contract_type
        )
        self._col = col
        self._start_date = start_date
        self._end_date = end_date
        self._nrows = nrows

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        dict_df = {}
        for s in self._symbols:
            data = vkibot.KibotS3DataLoader().read_data(
                exchange="CME",
                asset_class=vkibot.AssetClass.Futures,
                frequency=self._frequency,
                contract_type=self._contract_type,
                symbol=s,
                nrows=self._nrows,
            )[self._col]
            data = data.loc[self._start_date : self._end_date]
            dict_df[s] = data
        self.df = pd.DataFrame.from_dict(dict_df)


# #############################################################################


class KibotEquityReader(dtfcore.DataSource):
    def __init__(
        self,
        nid: dtfcore.NodeId,
        symbols: List[str],
        frequency: Union[str, vkibot.Frequency],
        start_date: Optional[hdateti.Datetime] = None,
        end_date: Optional[hdateti.Datetime] = None,
        nrows: Optional[int] = None,
    ) -> None:
        """
        Read equity OHLCV data.
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(symbols, list)
        self._symbols = symbols
        self._frequency = (
            vkibot.Frequency(frequency)
            if isinstance(frequency, str)
            else frequency
        )
        self._start_date = start_date
        self._end_date = end_date
        self._nrows = nrows

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        if self.df is not None:
            return
        dfs = {}
        for symbol in self._symbols:
            data = vkibot.KibotS3DataLoader().read_data(
                # TODO(*): This is required, but is it used?
                exchange="NYSE",
                aws_profile="am",
                asset_class=vkibot.AssetClass.Stocks,
                frequency=self._frequency,
                symbol=symbol,
                # TODO(*): Pass this through as an option.
                unadjusted=False,
                nrows=self._nrows,
            )
            n_rows = data.shape[0]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug("Read %d rows for symbol=%s", n_rows, symbol)
            data = data.loc[self._start_date : self._end_date]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Retained %s rows for symbol=%s after time filtering (%.2f)",
                    data.shape[0],
                    symbol,
                    data.shape[0] / n_rows,
                )
            hdbg.dassert(
                not data.empty, "No data for %s in requested time range", symbol
            )
            # Rename column for volume so that it adheres with our conventions.
            data = data.rename(columns={"vol": "volume"})
            # Print some info about the data.
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    hpandas.df_to_str(data, print_shape_info=True, tag="data")
                )
            # Ensure data is on a uniform frequency grid.
            data = cofinanc.resample_ohlcv_bars(data, rule=self._frequency.value)
            dfs[symbol] = data
        # Create a dataframe with multiindexed columns.
        df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        # Swap column levels so that symbols are leaves.
        df = df.swaplevel(i=0, j=1, axis=1)
        df.sort_index(axis=1, level=0, inplace=True)
        self.df = df


class RealTimeDataSource(dtfcore.DataSource):
    """
    A RealTimeDataSource is a node that:

    - is backed by a `MarketData` (replayed, simulated, or real-time)
    - emits different data based on the value of a clock
      - This represents the fact the state of a DB is updated over time
    - has a blocking behavior
      - E.g., the data might not be available immediately when the data is
        requested and thus the caller has to wait
    """

    def __init__(
        self,
        nid: dtfcore.NodeId,
        market_data: mdata.MarketData,
        # TODO(gp): -> history_lookback
        timedelta: pd.Timedelta,
        ts_col_name: str,
        multiindex_output: bool,
    ) -> None:
        """
        Constructor.

        :param timedelta: how much history is needed from the real-time
            node. See `MarketData.get_data()` for details.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                hprint.to_str("nid market_data timedelta multiindex_output")
            )
        super().__init__(nid)
        hdbg.dassert_isinstance(market_data, mdata.MarketData)
        self._market_data = market_data
        hdbg.dassert_isinstance(timedelta, pd.Timedelta)
        self._timedelta = timedelta
        self._asset_id_col = market_data.asset_id_col
        hdbg.dassert_isinstance(ts_col_name, str)
        self._ts_col_name = ts_col_name
        hdbg.dassert_isinstance(multiindex_output, bool)
        self._multiindex_output = multiindex_output

    # TODO(gp): Can we use a run and move it inside fit?
    async def wait_for_latest_data(
        self,
    ) -> Tuple[pd.Timestamp, pd.Timestamp, int]:
        ret = await self._market_data.wait_for_latest_data()
        return ret  # type: ignore[no-any-return]

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._get_data()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._get_data()
        return super().predict()  # type: ignore[no-any-return]

    def _get_data(self) -> None:
        # TODO(gp): This approach of communicating params through the state
        #  makes the code difficult to understand.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("timedelta=%s", self._timedelta)
        self.df = self._market_data.get_data_for_last_period(
            self._timedelta, ts_col_name=self._ts_col_name
        )
        if self._multiindex_output:
            self.df = dtfcorutil.convert_to_multiindex(self.df, self._asset_id_col)


# #############################################################################


class HistoricalDataSource(dtfcore.DataSource):
    """
    Stream the data to the DAG from a `MarketData`.

    Note that the `MarketData` decides the universe of asset_ids.
    """

    def __init__(
        self,
        nid: dtfcore.NodeId,
        market_data: mdata.MarketData,
        ts_col_name: str,
        multiindex_output: bool,
        *,
        # TODO(gp): Pass the columns to keep, instead of the columns to remove.
        col_names_to_remove: Optional[List[str]] = None,
    ) -> None:
        """
        Constructor.

        :param ts_col_name: the name of the column from `market_data`
            containing the end time stamp of the interval to filter on
        :param col_names_to_remove: name of the columns to remove from the df
        """
        super().__init__(nid)
        hdbg.dassert_isinstance(market_data, mdata.MarketData)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("market_data ts_col_name multiindex_output"))
        self._market_data = market_data
        self._asset_id_col = market_data.asset_id_col
        self._ts_col_name = ts_col_name
        self._multiindex_output = multiindex_output
        self._col_names_to_remove = col_names_to_remove

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "wall_clock_time=%s",
                self._market_data.get_wall_clock_time(),
            )
        intervals = self._fit_intervals
        self.df = self._get_data(intervals)
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "wall_clock_time=%s",
                self._market_data.get_wall_clock_time(),
            )
        intervals = self._predict_intervals
        self.df = self._get_data(intervals)
        return super().predict()  # type: ignore[no-any-return]

    def _get_data(self, intervals: dtfcore.Intervals) -> pd.DataFrame:
        """
        Get data for the requested [a, b] interval.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("intervals"))
        # For simplicity's sake we get a slice of the data that includes all the
        # requested intervals, relying on parent's `fit()` and `predict()` to
        # extract the data strictly needed.
        (
            min_timestamp,
            max_timestamp,
        ) = dtfcore.find_min_max_timestamps_from_intervals(intervals)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(hprint.to_str("min_timestamp max_timestamp"))
        # From ArmaDataSource._lazy_load():
        #   ```
        #   self.df = df.loc[self._start_date : self._end_date]
        #   ```
        # the interval needs to be [a, b].
        left_close = True
        right_close = True
        # We assume that the `MarketData` object is in charge of specifying
        # the universe of assets.
        asset_ids = None
        df = self._market_data.get_data_for_interval(
            min_timestamp,
            max_timestamp,
            self._ts_col_name,
            asset_ids,
            left_close=left_close,
            right_close=right_close,
        )
        # Remove the columns that are not needed.
        if self._col_names_to_remove is not None:
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "Before column removal\n:%s",
                    hpandas.df_to_str(df.head()),
                )
                _LOG.debug(
                    "Removing %s from %s", self._col_names_to_remove, df.columns
                )
            for col_name in self._col_names_to_remove:
                hdbg.dassert_in(col_name, df.columns)
                del df[col_name]
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "After column removal\n:%s",
                    hpandas.df_to_str(df.head()),
                )
        if self._multiindex_output:
            df = dtfcorutil.convert_to_multiindex(df, self._asset_id_col)
        return df
