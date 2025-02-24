"""
Import as:

import market_data.abstract_market_data as mdabmada
"""

import abc
import asyncio
import logging
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hwall_clock_time as hwacltim

_LOG = logging.getLogger(__name__)


# Enable extra verbose debugging. Do not commit.
_TRACE = False


AssetId = int


# #############################################################################
# MarketData
# #############################################################################


# TODO(gp): CleanUp. We should use the column_remap as we do for broker.
#  E.g., we tell the remap what's the mapping from the column names to the
#  "official" names. The remap right after the data is retrieved from the
#  ImClient.
#  Instead now we specify the name of each column through `start_time_col_name`
#  and `end_time_col_name`.
#  The remap approach has the benefit of tending to make the naming more stable.

# TODO(gp): One can use start or end of an interval to work on. It's unclear how
#  the knowledge time is handled. It seems that it is handled by the derived
#  classes.
class MarketData(abc.ABC, hobject.PrintableMixin):
    """
    Implement an interface to an historical / real-time source of price data.

    Clients pass values that are typically fixed across the life of `MarketData`
    through the constructor. Some of the class methods allow to optionally
    override the values passed to the constructor.

    `MarketData` allows to query for intervals of data with different open/close
    semantics, using different columns (e.g., start or end time of a data
    interval) as the timestamp, but always preventing future peeking.

    # Responsibilities:
    - Delegate to a data backend in `ImClient` to retrieve historical and
      real-time data. Derived classes implement `_get_data()`.
    - Model data in terms of interval `start_timestamp`, `end_timestamp`
        - `ImClient` models data in terms of end timestamp of the interval
    - Implement RT behaviors (e.g, `is_last_bar_available`, wall clock, ...)
    - Implement knowledge time and delay
        - `ImClient` doesn't have this view of the data
    - Stitch together different data representations (e.g., historical / RT)
      using multiple IM backends
    - Remap columns to connect data backends to consumers
    - Implement some common market-related data transformations
        - E.g., `get_twap_price()`, `get_last_price()`
    - Handle timezones, i.e. convert all timestamp to the provided timezone

    # Non-responsibilities:
    - Do not access data directly but rely on `ImClient` objects to retrieve the
      data from different backends
    - The knowledge time is handled by the derived classes.

    # Output format
    - The class normalizes the data by:
        - sorting by the columns that correspond to `end_time` and `asset_id`
        - indexing by the column that corresponds to `end_time`, so that it is
          suitable to DataFlow computation
    - E.g.,
    ```
                            asset_id                start_time    close   volume
    end_time
    2021-07-20 09:31:00-04:00  17085 2021-07-20 09:30:00-04:00  143.990  1524506
    2021-07-20 09:32:00-04:00  17085 2021-07-20 09:31:00-04:00  143.310   586654
    2021-07-20 09:33:00-04:00  17085 2021-07-20 09:32:00-04:00  143.535   667639
    ```
    """

    def __init__(
        self,
        asset_id_col: str,
        # TODO(gp): This should be first and also potentially be None.
        asset_ids: List[int],
        # TODO(gp): -> start_timestamp_col
        start_time_col_name: str,
        end_time_col_name: str,
        columns: Optional[List[str]],
        get_wall_clock_time: hdateti.GetWallClockTime,
        *,
        # TODO(Dan): Converge on timezone `America/New_York` vs `US/Eastern` (see
        #  CMTask217).
        timezone: str = "America/New_York",
        sleep_in_secs: float = 1.0,
        time_out_in_secs: Optional[int] = 60 * 2,
        column_remap: Optional[Dict[str, str]] = None,
        filter_data_mode: str = "assert",
    ):
        """
        Constructor.

        The (input) name of the columns delivered by the derived classes is set
        through `asset_id_col`, `start_time_col_name`, `end_time_col_name`.
        The (output) name of the columns can be changed through `column_remap`.

        All the column names in the interface (e.g., `start_time_col_name`) are
        before the remapping.

        :param asset_id_col: the name of the column used to select the asset ids
        :param asset_ids: list of ids to access
        :param start_time_col_name: the name of the column storing the `start_time`
        :param end_time_col_name: the name of the column storing the `end_time`
        :param columns: columns to return.
            - `None` means all the available columns
        :param get_wall_clock_time: the wall clock
        :param timezone: timezone to convert normalized output timestamps to
        :param sleep_in_secs, time_out_in_secs: sample every `sleep_in_secs`
            seconds waiting up to `time_out_in_secs` seconds.
            If `time_out_in_secs` is None, sample until manual interruption
        :param column_remap: dict of columns to remap the output data
            - `None` for no remapping
        :param filter_data_mode: control class behavior with respect to extra
            or missing columns, like in
            `hpandas.check_and_filter_matching_columns()`
        """
        _LOG.debug(
            hprint.to_str(
                "asset_id_col asset_ids start_time_col_name "
                "end_time_col_name columns get_wall_clock_time "
                "timezone sleep_in_secs time_out_in_secs column_remap "
                "filter_data_mode"
            )
        )
        self._asset_id_col = asset_id_col
        # TODO(gp): Some tests pass asset_ids=None which is not ideal.
        # hdbg.dassert_is_not(asset_ids, None)
        self._asset_ids = asset_ids
        # This needs `self._asset_ids` to be initialized.
        self._dassert_valid_asset_ids(asset_ids)
        #
        self._start_time_col_name = start_time_col_name
        self._end_time_col_name = end_time_col_name
        self._columns = columns
        #
        hdbg.dassert_isinstance(get_wall_clock_time, Callable)
        self._get_wall_clock_time = get_wall_clock_time
        #
        hdbg.dassert_lt(0, sleep_in_secs)
        self._sleep_in_secs = sleep_in_secs
        #
        self._timezone = timezone
        #
        if column_remap is not None:
            hdbg.dassert_isinstance(column_remap, dict)
        self._column_remap = column_remap
        #
        self._filter_data_mode = filter_data_mode
        # Compute the max number of iterations based on the timeout.
        hdbg.dassert_lt(0, time_out_in_secs)
        if time_out_in_secs is not None:
            max_iterations = int(time_out_in_secs / sleep_in_secs)
            hdbg.dassert_lte(1, max_iterations)
        else:
            max_iterations = None
            _LOG.warning("No time limit is set via `max_iterations`.")
        self._max_iterations = max_iterations

    # TODO(gp): Who needs this? It seems an implementation detail.
    @property
    def asset_id_col(self) -> str:
        return self._asset_id_col

    # ////////////////////////////////////////////////////////////////////////////

    def get_data_for_interval(
        self,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        *,
        left_close: bool = True,
        right_close: bool = False,
        # TODO(gp): Cleanup. Remove limit, since this is a DB implementation.
        limit: Optional[int] = None,
        ignore_delay: bool = False,
    ) -> pd.DataFrame:
        """
        Return data for an interval with `start_ts` and `end_ts` boundaries.

        All the `get_data_*` functions should go through this function since it
        is in charge of converting the data to the right timezone and performing
        the column name remapping.

        :param ts_col_name: the name of the column (before the remapping) to
            filter on
        :param asset_ids: list of asset ids to filter on. `None` for all asset
            ids.
        :param left_close, right_close: represent the type of interval
            - E.g., [start_ts, end_ts), or (start_ts, end_ts]
        """
        _LOG.debug(
            hprint.to_str(
                "start_ts end_ts ts_col_name asset_ids left_close right_close "
                "limit ignore_delay"
            )
        )
        # Resolve the asset ids.
        if asset_ids is None:
            asset_ids = self._asset_ids
        self._dassert_valid_asset_ids(asset_ids)
        # Sanity check the requested interval.
        hdateti.dassert_is_valid_interval(
            start_ts, end_ts, left_close, right_close
        )
        # Delegate to the derived classes to retrieve the data.
        df = self._get_data(
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            left_close,
            right_close,
            limit,
            ignore_delay,
        )
        _LOG.debug("-> df after _get_data=\n%s", hpandas.df_to_str(df))
        _LOG.debug("get_data_for_interval() columns '%s'", df.columns)
        # If the assets were specified, check that the returned data doesn't
        # contain data that we didn't request.
        # TODO(Danya): How do we handle NaNs?
        hdbg.dassert_is_subset(
            df[self._asset_id_col].dropna().unique(), asset_ids
        )
        # TODO(gp): If asset_ids was specified but the backend has a universe
        #  specified already, we might need to apply a filter by asset_ids.
        # Normalize data.
        df = self._normalize_data(df)
        _LOG.debug("-> df after _normalize_data=\n%s", hpandas.df_to_str(df))
        # Convert start and end timestamps to the timezone specified in the ctor.
        df = self._convert_timestamps_to_timezone(df)
        _LOG.debug(
            "-> df after _convert_timestamps_to_timezone=\n%s",
            hpandas.df_to_str(df),
        )
        # Check that columns are the required ones.
        # TODO(gp): Difference between amp and cmamp.
        if self._columns is not None:
            df = hpandas.check_and_filter_matching_columns(
                df, self._columns, self._filter_data_mode
            )
        # Remap result columns to the required names.
        df = self._remap_columns(df)
        _LOG.debug("-> df after _remap_columns=\n%s", hpandas.df_to_str(df))
        if _TRACE:
            _LOG.trace("-> df=\n%s", hpandas.df_to_str(df))
        hdbg.dassert_isinstance(df, pd.DataFrame)
        return df

    def get_data_for_last_period(
        self,
        timedelta: pd.Timedelta,
        *,
        ts_col_name: Optional[str] = None,
        # TODO(gp): Cleanup. Not sure limit is really needed in the abstract
        #  interface. We could move it to the DB implementation.
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get data up to `timedelta` in the past before the current timestamp.

        This is used during real-time execution to evaluate a model.

        Note that we use `asset_ids` from the constructor instead of passing it
        since the use case is for clients to just ask data that has been
        configured upstream when this object was built.

        :param timedelta: length of last time period
        :param ts_col_name: name of timestamp column
            - `None` to use start_timestamp from the constructor
        :param limit: max number of rows to output
        :return: DataFrame with data for last given period
        """
        # Handle `timedelta`.
        if _TRACE:
            _LOG.trace(hprint.to_str("timedelta"))
        hdbg.dassert_isinstance(timedelta, pd.Timedelta)
        wall_clock_time = self.get_wall_clock_time()
        start_ts = self._process_period(timedelta, wall_clock_time)
        end_ts = wall_clock_time
        _LOG.debug(hprint.to_str("start_ts end_ts"))
        if ts_col_name is None:
            # By convention to get the last chunk of data we use the start_time
            # column.
            # TODO(Danya): Make passing of ts_col_name mandatory.
            ts_col_name = self._start_time_col_name
        # Get the data.
        df = self.get_data_for_interval(
            start_ts,
            end_ts,
            ts_col_name,
            self._asset_ids,
            limit=limit,
        )
        # We don't need to remap columns since `get_data_for_interval()` has
        # already done it.
        if _TRACE:
            _LOG.trace("-> df=\n%s", hpandas.df_to_str(df))
        return df

    def get_data_at_timestamp(
        self,
        ts: pd.Timestamp,
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        *,
        ignore_delay: bool = False,
    ) -> pd.DataFrame:
        """
        Return price data at a specific timestamp.

        :param ts: the timestamp to filter on
        :param ts_col_name: the name of the column (before the remapping) to
            filter on and use as index
        :param asset_ids: list of asset ids to filter on. `None` for all asset
            ids.
        :return: df with results, e.g.,
        ```
                                             start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id   price
        end_datetime
        2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44    997.42     978       101  997.42
        ```
        """
        self._dassert_valid_asset_ids(asset_ids)
        start_ts = ts - pd.Timedelta("1S")
        end_ts = ts + pd.Timedelta("1S")
        df = self.get_data_for_interval(
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            ignore_delay=ignore_delay,
        )
        # We don't need to remap columns since `get_data_for_interval()` has
        # already done it.
        if _TRACE:
            _LOG.trace("-> df=\n%s", hpandas.df_to_str(df))
        return df

    def get_wall_clock_time(self) -> pd.Timestamp:
        """
        Return wall clock time in the timezone specified in the ctor.

        Initially wall clock time can be in any timezone, but cannot be
        timezone-naive.
        """
        wall_clock_time = self._get_wall_clock_time()
        hdateti.dassert_has_tz(wall_clock_time)
        wall_clock_time_correct_timezone = wall_clock_time.tz_convert(
            self._timezone
        )
        return wall_clock_time_correct_timezone

    # /////////////////////////////////////////////////////////////////////////////

    def to_price_series(
        self,
        price_df: pd.DataFrame,
        col_name: str,
    ) -> pd.Series:
        """
        Convert a df with prices returned by methods like `get_twap_price()`.
            ```
                                                 start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id   price
            end_datetime
            2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44    997.42     978       101  997.42
            ```
        into a series that is indexed by `asset_id`:
            ```
                       price
            asset_id
            101       997.93
            ```
        """
        hdbg.dassert_isinstance(price_df, pd.DataFrame)
        # Convert the df of data into a series indexed by asset_id.
        hdbg.dassert_in(col_name, price_df.columns)
        price_df = price_df.reset_index()
        price_df = price_df[[col_name, self._asset_id_col]]
        price_df.set_index(self._asset_id_col, inplace=True)
        # Ensure that there are not repeated asset ids.
        hdbg.dassert_no_duplicates(
            price_df.index.to_list(), "price_df=%s", price_df
        )
        # Convert into a series.
        price_srs = hpandas.to_series(price_df)
        hdbg.dassert_isinstance(price_srs, pd.Series)
        price_srs.index.name = self._asset_id_col
        price_srs.name = col_name
        hpandas.dassert_series_type_in(price_srs, [np.float64, np.int64])
        return price_srs

    def get_twap_price(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        ts_col_name: str,
        asset_ids: List[int],
        column: str,
        *,
        ignore_delay: bool = False,
    ) -> pd.DataFrame:
        """
        Compute TWAP of the column `column` in (ts_start, ts_end].

        E.g., TWAP for (9:30, 9:35] means avg(p(9:31), ..., p(9:35)).

        This function should be called `get_twa_price()` or `get_twap()`, but alas
        TWAP is often used as an adjective for price.

        :param start_ts: beginning of the time period
        :param end_ts: end of the time period
        :param ts_col_name: column to use to index (e.g., `start_datetime` or
            `end_datetime`)
        :param column: column to use to compute the TWAP (e.g., `bid`, `ask`,
            `price`)
        :return: df with prices, like:
            ```
                                                 start_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id   price
            end_datetime
            2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00 2000-01-01 09:35:01-05:00  997.41  997.44    997.42     978       101  997.42
            ```
        """
        self._dassert_valid_asset_ids(asset_ids)
        # Get the slice (start_ts, end_ts] of prices.
        left_close = False
        right_close = True
        hdateti.dassert_is_valid_interval(
            start_ts, end_ts, left_close, right_close
        )
        prices = self.get_data_for_interval(
            start_ts,
            end_ts,
            ts_col_name,
            asset_ids,
            left_close=left_close,
            right_close=right_close,
            limit=None,
            ignore_delay=ignore_delay,
        )
        # We don't need to remap columns since `get_data_for_interval()` has
        # already done it.
        hdbg.dassert_in(column, prices.columns)
        # Compute the mean value.
        if _TRACE:
            _LOG.trace("prices=\n%s", prices)
        # twap_srs looks like:
        # ```
        #            price
        # asset_id
        # 101       997.93
        # ```
        twap_srs = prices.groupby(self._asset_id_col)[column].mean()
        hpandas.dassert_series_type_in(twap_srs, [np.float64, np.int64])
        # Add start_ts and end_ts.
        start_datetime_srs = pd.Series(start_ts, index=twap_srs.index)
        start_datetime_srs.name = self._start_time_col_name
        end_datetime_srs = pd.Series(end_ts, index=twap_srs.index)
        end_datetime_srs.name = self._end_time_col_name
        # Swap index from asset_id to end_time_col_name.
        twap_df = pd.concat(
            [start_datetime_srs, end_datetime_srs, twap_srs], axis=1
        )
        twap_df = twap_df.reset_index().set_index(self._end_time_col_name)
        # The df should look like:
        # ```
        #                                      start_datetime   price  asset_id
        # end_datetime
        # 2000-01-01 09:35:00-05:00 2000-01-01 09:34:00-05:00  997.41     101.0
        # ```
        return twap_df

    # TODO(gp): When we want to evaluate a TWAP price in (a, b] we need to:
    #  1) wait until `MarketData` is updated
    #  2) assert that all the requested prices are actually available
    # We should simplify this interface by removing this function and forcing
    # the callers to be explicit about what interval is needed (sometimes we
    # want the freshest data other times we want exactly one interval).
    def get_last_twap_price(
        self,
        bar_duration_as_pd_str: str,
        ts_col_name: str,
        asset_ids: List[int],
        column: str,
    ) -> pd.DataFrame:
        """
        Compute TWAP of the column `column` over last `bar_duration`.

        Prices are computed on bars like:
        ```
                                                 start_time  asset_id  close  volume
                         end_time
        2022-10-03 13:01:00+00:00 2022-10-03 13:00:00+00:00    23135    NaN       0
           ...
        2022-10-04 20:59:00+00:00 2022-10-04 20:58:00+00:00    20122    NaN       0
        ```

        E.g., if
        - ts_col_name = "end_time" (i.e., we are constraining the end of the
          interval)
        - the last end time is 9:35 and `bar_duration=5T`, then end_time in
          (9:30, 9:35] and compute its TWAP.
        """
        self._dassert_valid_asset_ids(asset_ids)
        last_end_time = self.get_last_end_time()
        _LOG.debug("last_end_time=%s", last_end_time)
        # Align on a bar. E.g., `last_end_time` is 09:16 and we ask
        # for data in (09:10, 09:15], not (09:11, 09:16].
        mode = "floor"
        bar_duration_in_secs = pd.Timedelta(bar_duration_as_pd_str).seconds
        last_end_time = hdateti.find_bar_timestamp(
            last_end_time,
            bar_duration_in_secs,
            mode=mode,
        )
        _LOG.debug("last_end_time=%s", last_end_time)
        #
        offset = pd.Timedelta(bar_duration_as_pd_str)
        start_time = last_end_time - offset
        ignore_delay = False
        twap_df = self.get_twap_price(
            start_time,
            last_end_time,
            ts_col_name,
            asset_ids,
            column,
            ignore_delay=ignore_delay,
        )
        return twap_df

    # /////////////////////////////////////////////////////////////////////////////
    # Methods for handling real-time behaviors.
    # /////////////////////////////////////////////////////////////////////////////

    def get_last_end_time(self) -> Optional[pd.Timestamp]:
        """
        Return the last `end_time` present from a real time data source.

        In the actual RT DB there is always some data, so we return a
        timestamp. The only case when we return `None` only for replayed
        time when there is no time (e.g., before the market opens).
        """
        last_end_time = self._get_last_end_time()
        _LOG.debug(hprint.to_str("last_end_time"))
        if last_end_time is not None:
            # Convert to ET.
            # TODO(Dan): Pass timezone from ctor in CmTask1000.
            last_end_time = last_end_time.tz_convert("America/New_York")
        if _TRACE:
            _LOG.trace("-> ret=%s", last_end_time)
        return last_end_time

    def get_last_price(
        self,
        col_name: str,
        asset_ids: List[int],
        *,
        ignore_delay: bool = False,
    ) -> pd.DataFrame:
        """
        Get last price for `asset_ids` using column `col_name` (e.g., "close").

        It returns data in the same format as the get data functions
        (e.g., `get_twap_price()`).
        """
        self._dassert_valid_asset_ids(asset_ids)
        # TODO(Paul): Use a to-be-written `get_last_start_time()` instead.
        last_end_time = self.get_last_end_time()
        _LOG.info("last_end_time=%s", last_end_time)
        # Get the data.
        # TODO(Paul): Remove the hard-coded 1-minute.
        start_time = last_end_time - pd.Timedelta("1T")
        df = self.get_data_at_timestamp(
            start_time,
            self._start_time_col_name,
            asset_ids,
            ignore_delay=ignore_delay,
        )
        # TODO(gp): Print if there are nans.
        return df

    @abc.abstractmethod
    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        """
        Return whether the interface should be available at the given time.
        """
        ...

    def is_online(self) -> bool:
        """
        Return whether the DB is on-line at the current time.

        This is useful to avoid to wait on a real-time source (e.g., a
        DB) that is off-line. We check this property by checking if
        there was data in the last minute.
        """
        # Check if the data in the last minute is empty.
        if _TRACE:
            _LOG.trace("")
        # The DB is online if there was data within the last minute.
        last_db_end_time = self.get_last_end_time()
        if last_db_end_time is None:
            ret = False
        else:
            if _TRACE:
                _LOG.trace(
                    "last_db_end_time=%s -> %s",
                    last_db_end_time,
                    last_db_end_time.floor("Min"),
                )
            wall_clock_time = self.get_wall_clock_time()
            if _TRACE:
                _LOG.trace(
                    "wall_clock_time=%s -> %s",
                    wall_clock_time,
                    wall_clock_time.floor("Min"),
                )
            ret = last_db_end_time.floor("Min") >= (
                wall_clock_time.floor("Min") - pd.Timedelta("1T")
            )
        if _TRACE:
            _LOG.trace("-> ret=%s", ret)
        return ret

    async def wait_for_latest_data(
        self,
    ) -> Tuple[pd.Timestamp, pd.Timestamp, int]:
        """
        Wait until the bar with `end_time` == `current_bar_timestamp` is
        available.

        :return: a triple
            - start_sampling_time: timestamp when the sampling started
            - end_sampling_time: timestamp when the sampling ended, since the bar
              was ready
            - num_iter: number of iterations until the last bar was ready
        """
        start_sampling_time = self.get_wall_clock_time()
        current_bar_timestamp = hwacltim.get_current_bar_timestamp()
        _LOG.debug(hprint.to_str("start_sampling_time current_bar_timestamp"))
        # We should start sampling for a bar inside the bar interval. Sometimes
        # we start a second before or after due to wall-clock drift so we round
        # to the nearest minute.
        hdbg.dassert_lte(start_sampling_time.round("1T"), current_bar_timestamp)
        if _TRACE:
            _LOG.trace("DB on-line: %s", self.is_online())
        #
        hprint.log_frame(_LOG, "Waiting on last bar ...")
        num_iter = 0
        while True:
            wall_clock_time = self.get_wall_clock_time()
            last_db_end_time = self.get_last_end_time()
            # TODO(gp): Cleanup. We should use the new hasynci.poll().
            _LOG.debug(
                "\n### waiting on last bar: "
                "num_iter=%s/%s: current_bar_timestamp=%s wall_clock_time=%s last_db_end_time=%s",
                num_iter,
                self._max_iterations,
                current_bar_timestamp,
                wall_clock_time,
                last_db_end_time,
            )
            if last_db_end_time and (
                last_db_end_time.floor("Min")
                >= current_bar_timestamp.floor("Min")
            ):
                # Get the current timestamp when the call was finally executed.
                hprint.log_frame(_LOG, "Waiting on last bar: done")
                end_sampling_time = wall_clock_time
                break
            # Raise timeout if wait time limit is exceeded.
            if (
                self._max_iterations is not None
                and num_iter >= self._max_iterations
            ):
                msg = f"Timeout after {num_iter} iterations. " + hprint.to_str(
                    "self._max_iterations current_bar_timestamp "
                    "wall_clock_time last_db_end_time"
                )
                _LOG.error(msg)
                raise TimeoutError
            num_iter += 1
            if _TRACE:
                _LOG.trace("Sleep for %s secs", self._sleep_in_secs)
            await asyncio.sleep(self._sleep_in_secs)
        if _TRACE:
            _LOG.trace(
                "-> %s",
                hprint.to_str("start_sampling_time end_sampling_time num_iter"),
            )
        return start_sampling_time, end_sampling_time, num_iter

    # /////////////////////////////////////////////////////////////////////////////

    # TODO(gp): Cleanup. Use a better name _get_XYZ.
    @staticmethod
    def _process_period(
        timedelta: pd.Timedelta, wall_clock_time: pd.Timestamp
    ) -> Optional[pd.Timestamp]:
        """
        Return the start time corresponding to returning the desired
        `timedelta` of time before the current wall clock time.

        E.g., if the df looks like:
        ```
           start_datetime           last_price    id
                     end_datetime
                              timestamp_db
        0  09:30     09:31    09:31  -0.125460  1000
        1  09:31     09:32    09:32   0.325254  1000
        2  09:32     09:33    09:33   0.557248  1000
        3  09:33     09:34    09:34   0.655907  1000
        4  09:34     09:35    09:35   0.311925  1000
        ```
        and `wall_clock_time=09:34` the last minute `1T` should be:
        ```
           start_datetime           last_price    id
                     end_datetime
                              timestamp_db
        4  09:34     09:35    09:35   0.311925  1000
        ```

        :param timedelta: a `pd.Timedelta` like `1D`, `5T`
        """
        if _TRACE:
            _LOG.trace(hprint.to_str("timedelta wall_clock_time"))
        hdbg.dassert_isinstance(timedelta, pd.Timedelta)
        hdbg.dassert_lt(pd.Timedelta("0S"), timedelta)
        last_start_time = wall_clock_time - timedelta
        if _TRACE:
            _LOG.trace("last_start_time=%s", last_start_time)
        return last_start_time

    # /////////////////////////////////////////////////////////////////////////////
    # Derived class interface.
    # /////////////////////////////////////////////////////////////////////////////

    @abc.abstractmethod
    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        ...

    @abc.abstractmethod
    def _get_data(
        self,
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        left_close: bool,
        right_close: bool,
        # TODO(gp): Cleanup. Not sure limit is really needed in the abstract.
        limit: Optional[int],
        ignore_delay: bool,
    ) -> pd.DataFrame:
        """
        Return data in the interval start_ts, end_ts for the given assets.

        This is the only entrypoint to get data from the derived classes.

        :param start_ts: beginning of the time interval to select data for
        :param end_ts: end of the time interval to select data for
        :param ts_col_name: the name of the column (before the remapping) to
            filter on
        :param asset_ids: list of asset ids to filter on. `None` for all asset ids.
        :param left_close, right_close: represent the type of interval
            - E.g., [start_ts, end_ts), or (start_ts, end_ts]
        :param limit: keep only top N records
        :param ignore_delay: TODO
        """
        ...

    # /////////////////////////////////////////////////////////////////////////////
    # Data normalization.
    # /////////////////////////////////////////////////////////////////////////////

    def _dassert_valid_asset_ids(
        self,
        asset_ids: Optional[Iterable[AssetId]],
    ) -> None:
        if asset_ids is not None:
            hdbg.dassert_container_type(
                asset_ids, (np.ndarray, list), (int, np.int64)
            )
            hdbg.dassert_is_subset(asset_ids, self._asset_ids)

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data from `ImClient` output format to `MarketData` format.

        The input df (in `ImClient` format) looks like:
        ```
          asset_id           start_time             end_time     close   volume

        idx
          0  17085  2021-07-26 13:40:00  2021-07-26 13:41:00  149.0250   575024
          1  17085  2021-07-26 13:41:00  2021-07-26 13:42:00  148.8600   400176
          2  17085  2021-07-26 13:30:00  2021-07-26 13:31:00  148.5300  1407725
        ```

        The output df looks like:
        ```
                                 asset_id                 start_time    close   volume
        end_time
        2021-07-20 09:31:00-04:00   17085  2021-07-20 09:30:00-04:00  143.990  1524506
        2021-07-20 09:32:00-04:00   17085  2021-07-20 09:31:00-04:00  143.310   586654
        2021-07-20 09:33:00-04:00   17085  2021-07-20 09:32:00-04:00  143.535   667639
        ```
        """
        # Sort in increasing time order and reindex.
        df.sort_values(
            [self._end_time_col_name, self._asset_id_col], inplace=True
        )
        df.set_index(self._end_time_col_name, drop=True, inplace=True)
        # TODO(gp): Add a check to make sure we are not getting data after the
        #  current time.
        if _TRACE:
            _LOG.trace("df.empty=%s, df.shape=%s", df.empty, str(df.shape))
        # # The data source should not return data after the current time.
        # if not df.empty:
        #     wall_clock_time = self.get_wall_clock_time()
        #     _LOG.debug(hprint.to_str("wall_clock_time df.index.max()"))
        #     hdbg.dassert_lte(df.index.max(), wall_clock_time)
        # _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="after process_data"))
        return df

    def _remap_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remap column names with provided mapping.

        :param df: input data
        :return: df with remapped column names
        """
        if self._column_remap:
            hpandas.dassert_valid_remap(df.columns.tolist(), self._column_remap)
            df = df.rename(columns=self._column_remap)
        return df

    def _convert_timestamps_to_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert start and end timestamps to the specified timezone.

        :param df: normalized data
        :return: df with start and end dates in specified timezone
        """
        if df.empty:
            return df
        # Convert end timestamp values that are used as dataframe index.
        hpandas.dassert_index_is_datetime(df)
        df.index = df.index.tz_convert(self._timezone)
        # Convert start timestamp column values.
        srs = df[self._start_time_col_name].dt.tz_convert(self._timezone)
        df[self._start_time_col_name] = srs
        return df
