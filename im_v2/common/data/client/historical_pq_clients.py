"""
Import as:

import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
"""

import abc
import logging
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import im_v2.common.data.client.base_im_clients as imvcdcbimcl
import im_v2.common.data.client.full_symbol as imvcdcfusy

_LOG = logging.getLogger(__name__)


# TODO(gp): @Grisha Add tests. GP to provide an example of files or we can generate
#  them from CSV.
class HistoricalPqByTileClient(
    imvcdcbimcl.ImClientReadingMultipleSymbols, abc.ABC
):
    """
    Provide historical data stored as Parquet by-asset.
    """

    def __init__(
        self,
        asset_col_name: str,
        root_dir_name: str,
        partitioning_mode: str,
    ):
        """
        Constructor.

        :param asset_col_name: column name storing the asset
        :param root_dir_name: directory storing the tiled Parquet data
        :param partitioning_mode: how the data is partitioned, e.g., "by_year_month"
        """
        self._asset_col_name = asset_col_name
        self._root_dir_name = root_dir_name
        self._partitioning_mode = partitioning_mode

    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[imvcdcfusy.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        full_symbol_col_name: str,
        *,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Same as abstract method.
        """
        _LOG.debug(
            hprint.to_str(
                "full_symbols start_ts end_ts full_symbol_col_name columns"
            )
        )
        asset_ids = self.get_asset_ids_from_full_symbols(full_symbols)
        # TODO(Nikola): Are ids string or int in dataframe?
        asset_ids = list(map(str, asset_ids))
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            self._partitioning_mode, start_ts, end_ts
        )
        asset_and_condition = (self._asset_col_name, "in", asset_ids)
        if not filters:
            filters = [asset_and_condition]
        else:
            # It is important to put assets first in each AND filter because of the performance.
            # Intervals will be checked only for desired assets instead whole dataset.
            for filter_ in filters:
                filter_.insert(0, asset_and_condition)
        # Read the data.
        # TODO(gp): Add support for S3 passing aws_profile.
        df = hparque.from_parquet(
            self._root_dir_name,
            columns=columns,
            filters=filters,
            log_level=logging.INFO,
        )
        hdbg.dassert(not df.empty)
        # Convert to datetime.
        df.index = pd.to_datetime(df.index)
        # The asset data can come back from Parquet as:
        # ```
        # Categories(540, int64): [10025, 10036, 10040, 10045, ..., 82711, 82939,
        #                         83317, 89970]
        # ```
        # which confuses `df.groupby()`. So we convert that column to int.
        # TODO(gp): Move this to the derived class.
        df[self._asset_col_name] = df[self._asset_col_name].astype(int)
        # Rename column storing asset_ids, if needed.
        hdbg.dassert_in(self._asset_col_name, df.columns)
        if full_symbol_col_name != self._asset_col_name:
            hdbg.dassert_not_in(full_symbol_col_name, df.columns)
            df.rename(
                columns={self._asset_col_name: full_symbol_col_name}, inplace=True
            )
        # Since we have normalized the data, the index is a timestamp and we can
        # trim the data with index in [start_ts, end_ts] to remove the excess
        # from filtering in terms of days.
        ts_col_name = None
        left_close = True
        right_close = True
        df = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        return df


# #############################################################################


# TODO(gp): @Grisha Add tests. GP to provide an example of files or we can generate
#  them from CSV.
class HistoricalPqByDateClient(
    imvcdcbimcl.ImClientReadingMultipleSymbols, abc.ABC
):
    """
    Read historical data stored as Parquet by-date.
    """

    # TODO(gp): Do not pass a read_func but use an abstract method.
    def __init__(self, asset_col_name: str, read_func: Callable):
        """
        Constructor.

        :param asset_col_name: column name storing the asset
        """
        self._asset_col_name = asset_col_name
        self._read_func = read_func

    def _read_data_for_multiple_symbols(
        self,
        full_symbols: List[imvcdcfusy.FullSymbol],
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        full_symbol_col_name: str,
        **kwargs: Dict[str, Any],
    ) -> pd.DataFrame:
        """
        Same as abstract method.
        """
        # The data is stored by date, so we need to convert the timestamps into
        # dates and then trim the excess.
        # Compute the start_date.
        if start_ts is not None:
            start_date = start_ts.date()
        else:
            start_date = None
        # Compute the end_date.
        if end_ts is not None:
            end_date = end_ts.date()
        else:
            end_date = None
        # Get the data for [start_date, end_date].
        # TODO(gp): Use an abstract_method.
        tz_zone = "UTC"
        df = self._read_func(
            full_symbols,
            start_date,
            end_date,
            normalize=True,
            tz_zone=tz_zone,
            **kwargs,
        )
        # Convert to datetime.
        df.index = pd.to_datetime(df.index)
        # Rename column storing the asset ids.
        hdbg.dassert_in(self._asset_col_name, df.columns)
        hdbg.dassert_not_in(full_symbol_col_name, df.columns)
        df.rename(
            columns={self._asset_col_name: full_symbol_col_name}, inplace=True
        )
        # Since we have normalized the data, the index is a timestamp, and we can
        # trim the data with index in [start_ts, end_ts] to remove the excess
        # from filtering in terms of days.
        ts_col_name = None
        left_close = True
        right_close = True
        df = hpandas.trim_df(
            df, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        return df
