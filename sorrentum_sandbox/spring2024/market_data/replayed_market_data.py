"""
Import as:

import market_data.replayed_market_data as mdremada
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import core.real_time as creatime
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.htimer as htimer
import market_data.abstract_market_data as mdabmada

_LOG = logging.getLogger(__name__)
# Enable extra verbose debugging. Do not commit.
_TRACE = False


# #############################################################################
# ReplayedMarketData
# #############################################################################


# TODO(gp): This should have a delay and / or we should use timestamp_db.
class ReplayedMarketData(mdabmada.MarketData):
    """
    Implement an interface to a replayed time historical / RT database.

    Another approach to achieve the same goal is to mock the IM directly
    instead of this class.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        knowledge_datetime_col_name: str,
        delay_in_secs: int,
        # Params from `MarketData`.
        *args: Any,
        **kwargs: Any,
    ):
        """
        Constructor.

        :param df: dataframe in the same format of an SQL based data (i.e., not in
            dataflow format, e.g., indexed by `end_time`)
        :param knowledge_datetime_col_name: column with the knowledge time for the
            corresponding data
        :param delay_in_secs: how many seconds to wait beyond the timestamp in
            `knowledge_datetime_col_name`
        """
        _LOG.debug(hprint.to_str("knowledge_datetime_col_name delay_in_secs"))
        _LOG.debug("df=\n%s", hpandas.df_to_str(df))
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._df = df
        self._knowledge_datetime_col_name = knowledge_datetime_col_name
        hdbg.dassert_lte(0, delay_in_secs)
        self._delay_in_secs = delay_in_secs
        # TODO(gp): We should use the better invariant that the data is already
        #  formatted before it's saved instead of reapplying the transformation
        #  to make it palatable to downstream.
        if self._end_time_col_name in df.columns:
            hdbg.dassert_is_subset(
                [
                    self._asset_id_col,
                    self._start_time_col_name,
                    self._end_time_col_name,
                    self._knowledge_datetime_col_name,
                ],
                df.columns,
            )
            self._df.sort_values(
                [self._end_time_col_name, self._asset_id_col], inplace=True
            )

    def should_be_online(self, wall_clock_time: pd.Timestamp) -> bool:
        return True

    def _get_data(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        ts_col_name: str,
        asset_ids: Optional[List[int]],
        left_close: bool,
        right_close: bool,
        limit: Optional[int],
        # TODO(gp): -> ignore_propagation_delay = instantaneous_market_?
        ignore_delay: bool,
    ) -> pd.DataFrame:
        if _TRACE:
            _LOG.trace(
                hprint.to_str(
                    "start_ts end_ts ts_col_name asset_ids left_close "
                    "right_close limit ignore_delay"
                )
            )
        if ignore_delay:
            delay_in_secs = 0
        else:
            delay_in_secs = self._delay_in_secs
        # TODO(gp): This assertion seems very slow. Move this check in a
        #  centralized place instead of calling it every time, if possible.
        if asset_ids is not None:
            # Make sure that the requested asset_ids are in the df at some point.
            # This avoids mistakes when mocking data for certain assets, but request
            # data for assets that don't exist, which can make us wait for data that
            # will never come.
            hdbg.dassert_is_subset(
                asset_ids, self._df[self._asset_id_col].unique()
            )
        # Filter the data by the current time.
        wall_clock_time = self.get_wall_clock_time()
        if _TRACE:
            _LOG.trace(hprint.to_str("wall_clock_time"))
        df_tmp = creatime.get_data_as_of_datetime(
            self._df,
            self._knowledge_datetime_col_name,
            wall_clock_time,
            delay_in_secs=delay_in_secs,
        )
        # Handle `columns`.
        if self._columns is not None:
            hdbg.dassert_is_subset(self._columns, df_tmp.columns)
            df_tmp = df_tmp[self._columns]
        # Handle `period`.
        hdbg.dassert_in(ts_col_name, df_tmp.columns)
        df_tmp = hpandas.trim_df(
            df_tmp, ts_col_name, start_ts, end_ts, left_close, right_close
        )
        # Handle `asset_ids`
        if _TRACE:
            _LOG.trace("before df_tmp=\n%s", hpandas.df_to_str(df_tmp))
        if asset_ids is not None:
            hdbg.dassert_in(self._asset_id_col, df_tmp.columns)
            mask = df_tmp[self._asset_id_col].isin(set(asset_ids))
            df_tmp = df_tmp[mask]
        if _TRACE:
            _LOG.trace("after df_tmp=\n%s", hpandas.df_to_str(df_tmp))
        # Handle `limit`.
        if limit:
            hdbg.dassert_lte(1, limit)
            df_tmp = df_tmp.head(limit)
        if _TRACE:
            _LOG.trace("-> df_tmp=\n%s", hpandas.df_to_str(df_tmp))
        return df_tmp

    def _get_last_end_time(self) -> Optional[pd.Timestamp]:
        # We need to find the last timestamp before the current time. We use
        # `7W` but could also use all the data since we don't call the DB.
        # TODO(gp): SELECT MAX(start_time) instead of getting all the data
        #  and then find the max and use `start_time`
        timedelta = pd.Timedelta("7D")
        df = self.get_data_for_last_period(timedelta)
        _LOG.debug(
            hpandas.df_to_str(df, print_shape_info=True, tag="after get_data")
        )
        if df.empty:
            ret = None
        else:
            ret = df.index.max()
        _LOG.debug("-> ret=%s", ret)
        return ret


# #############################################################################
# Serialize / deserialize example of DB.
# #############################################################################


def save_market_data(
    market_data: mdabmada.MarketData,
    file_name: str,
    timedelta: pd.Timedelta,
    *,
    asset_id_col: str = "asset_id",
    limit: Optional[int] = None,
) -> None:
    """
    Save data from a `MarketData` to a CSV file.

    ```
                                asset_id       full_symbol     open     high     low     close  volume              knowledge_timestamp                  start_ts
    end_ts
    2021-12-19 19:00:00-05:00 1467591036 binance::BTC_USDT 46668.65 46677.22 46575.00 46670.34 620.659 2022-07-09 12:07:51.240219+00:00 2021-12-19 18:59:00-05:00
    2021-12-19 19:01:00-05:00 1467591036 binance::BTC_USDT 46670.34 46670.84 46550.00 46567.11 237.931 2022-06-24 05:47:16.075108+00:00 2021-12-19 19:00:00-05:00
    2021-12-19 19:02:00-05:00 1467591036 binance::BTC_USDT 46567.12 46590.60 46489.61 46513.85 612.955 2022-06-24 05:47:16.075108+00:00 2021-12-19 19:01:00-05:00
    ```

    The data is not processed but saved exactly as it is.
    """
    # hdbg.dassert(market_data.is_online())
    with htimer.TimedScope(logging.DEBUG, "market_data.get_data"):
        rt_df = market_data.get_data_for_last_period(timedelta, limit=limit)
    #
    _LOG.info("index=%s, %s", rt_df.index.min(), rt_df.index.max())
    hdbg.dassert_in(asset_id_col, rt_df.columns)
    asset_ids = rt_df[asset_id_col].unique()
    _LOG.info("asset_id=%s %s", len(asset_ids), str(asset_ids))
    #
    _LOG.debug(
        hpandas.df_to_str(
            rt_df, print_dtypes=True, print_shape_info=True, tag="rt_df"
        )
    )
    #
    _LOG.info("Saving data in '%s' ...", file_name)
    compression = None
    if file_name.endswith(".gz"):
        compression = "gzip"
    rt_df.to_csv(file_name, compression=compression, index=True)
    _LOG.info("Saving in '%s' done", file_name)


def load_market_data(
    file_name: str,
    *,
    aws_profile: hs3.AwsProfile = None,
    column_remap: Optional[Dict[str, str]] = None,
    timestamp_db_column: Optional[str] = None,
    datetime_columns: Optional[List[str]] = None,
    read_csv_kwargs: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Load some example market data from a CSV file.

    ```
                   end_datetime    asset_id        full_symbol      open      high       low     close   volume               knowledge_timestamp            start_datetime              timestamp_db
    index
    0 2021-12-20 00:00:00+00:00  1467591036  binance::BTC_USDT  46668.65  46677.22  46575.00  46670.34  620.659  2022-07-09 12:07:51.240219+00:00 2021-12-19 23:59:00+00:00 2021-12-20 00:00:00+00:00
    1 2021-12-20 00:01:00+00:00  1467591036  binance::BTC_USDT  46670.34  46670.84  46550.00  46567.11  237.931  2022-06-24 05:47:16.075108+00:00 2021-12-20 00:00:00+00:00 2021-12-20 00:01:00+00:00
    2 2021-12-20 00:02:00+00:00  1467591036  binance::BTC_USDT  46567.12  46590.60  46489.61  46513.85  612.955  2022-06-24 05:47:16.075108+00:00 2021-12-20 00:01:00+00:00 2021-12-20 00:02:00+00:00
    ```

    :param column_remap: mapping for columns to remap
    :param timestamp_db_column: column name (after remapping) to use as
        `timestamp_db` if it doesn't exist (e.g., we can use `end_datetime` as
        `timestamp_db`)
    :param datetime_columns: names (after remapping) of the columns to convert
        to datetime
    """
    _LOG.debug(
        hprint.to_str(
            "file_name aws_profile column_remap timestamp_db_column "
            "datetime_columns read_csv_kwargs"
        )
    )
    # Build options for `read_csv_to_df()`.
    if read_csv_kwargs is None:
        read_csv_kwargs = {}
    read_csv_kwargs = read_csv_kwargs.copy()
    if aws_profile:
        s3fs_ = hs3.get_s3fs(aws_profile)
        read_csv_kwargs["s3fs"] = s3fs_
    stream, read_csv_kwargs = hs3.get_local_or_s3_stream(
        file_name, **read_csv_kwargs
    )
    df = hpandas.read_csv_to_df(stream, **read_csv_kwargs)
    # Adjust column names to the processable format.
    if column_remap:
        hpandas.dassert_valid_remap(list(df.columns), column_remap)
        df = df.rename(columns=column_remap)
    #
    if timestamp_db_column:
        hdbg.dassert_not_in("timestamp_db", df.columns)
        hdbg.dassert_in(timestamp_db_column, df.columns)
        df["timestamp_db"] = df[timestamp_db_column]
    # Typically datetime columns are received as strings, while the pipeline
    # requires datetime type for further computations.
    if datetime_columns:
        for col_name in datetime_columns:
            hdbg.dassert_in(col_name, df.columns)
            df[col_name] = pd.to_datetime(df[col_name], utc=True)
    df.reset_index(inplace=True, drop=True)
    #
    _LOG.debug(
        hpandas.df_to_str(df, print_dtypes=True, print_shape_info=True, tag="df")
    )
    return df


# #############################################################################
# Stats about DB delay
# #############################################################################


def compute_rt_delay(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a "delay" column with the difference between `timestamp_db` and
    `end_time`.
    """

    def _to_et(srs: pd.Series) -> pd.Series:
        srs = srs.dt.tz_localize("UTC").dt.tz_convert("America/New_York")
        return srs

    timestamp_db = _to_et(df["timestamp_db"])
    end_time = _to_et(df["end_time"])
    # Compute delay.
    delay = (timestamp_db - end_time).dt.total_seconds()
    delay = round(delay, 2)
    df["delay_in_secs"] = delay
    return df


def describe_rt_delay(df: pd.DataFrame) -> None:
    """
    Compute some statistics for the DB delay.
    """
    delay = df["delay_in_secs"]
    print("delays=%s" % hprint.format_list(delay, max_n=5))
    if False:
        print(
            "delays.value_counts=\n%s" % hprint.indent(str(delay.value_counts()))
        )
    delay.plot.hist()


def describe_rt_df(df: pd.DataFrame, *, include_delay_stats: bool) -> None:
    """
    Print some statistics for a df from the RT DB.
    """
    print("shape=%s" % str(df.shape))
    # Is it sorted?
    end_times = df["end_time"]
    is_sorted = all(sorted(end_times, reverse=True) == end_times)
    print("is_sorted=", is_sorted)
    # Stats about `end_time`.
    min_end_time = df["end_time"].min()
    max_end_time = df["end_time"].max()
    num_mins = df["end_time"].nunique()
    print(
        "end_time: num_mins=%s [%s, %s]" % (num_mins, min_end_time, max_end_time)
    )
    # Stats about `asset_ids`.
    # TODO(gp): Pass the name of the column through the interface.
    print("asset_ids=%s" % hprint.format_list(df["egid"].unique()))
    # Stats about delay.
    if include_delay_stats:
        df = compute_rt_delay(df)
        describe_rt_delay(df)
    #
    from IPython.display import display

    display(df.head(3))
    display(df.tail(3))
