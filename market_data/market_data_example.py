"""
Import as:

import market_data.market_data_example as mdmadaex
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

import core.finance as cofinanc
import core.real_time as creatime
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hsql as hsql
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.talos.data.client as itdcl
import market_data.im_client_market_data as mdimcmada
import market_data.real_time_market_data as mdrtmada
import market_data.replayed_market_data as mdremada

_LOG = logging.getLogger(__name__)


# #############################################################################
# ReplayedTimeMarketData examples
# #############################################################################


# TODO(gp): Return only MarketData since the wall clock is inside it.
def get_ReplayedTimeMarketData_from_df(
    event_loop: asyncio.AbstractEventLoop,
    initial_replayed_delay: int,
    df: pd.DataFrame,
    *,
    knowledge_datetime_col_name: str = "timestamp_db",
    asset_id_col_name: str = "asset_id",
    start_time_col_name: str = "start_datetime",
    end_time_col_name: str = "end_datetime",
    delay_in_secs: int = 0,
    sleep_in_secs: float = 1.0,
    time_out_in_secs: int = 60 * 2,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData` backed by data stored in a dataframe.

    :param df: dataframe including the columns
        ["timestamp_db", "asset_id", "start_datetime", "end_datetime"]
    :param initial_replayed_delay: how many minutes after the beginning of the
        data the replayed time starts. This is useful to simulate the beginning
        / end of the trading day.
    """
    hdbg.dassert_in(knowledge_datetime_col_name, df.columns)
    hdbg.dassert_in(asset_id_col_name, df.columns)
    # Infer the asset ids from the dataframe.
    asset_ids = list(df[asset_id_col_name].unique())
    hdbg.dassert_in(start_time_col_name, df.columns)
    hdbg.dassert_in(end_time_col_name, df.columns)
    columns = None
    # Build the wall clock.
    tz = "ET"
    # Find the initial timestamp of the data and shift by
    # `initial_replayed_delay`.
    initial_replayed_dt = df[start_time_col_name].min() + pd.Timedelta(
        minutes=initial_replayed_delay
    )
    speed_up_factor = 1.0
    get_wall_clock_time = creatime.get_replayed_wall_clock_time(
        tz,
        initial_replayed_dt,
        event_loop=event_loop,
        speed_up_factor=speed_up_factor,
    )
    # Build a `ReplayedMarketData`.
    market_data = mdremada.ReplayedMarketData(
        df,
        knowledge_datetime_col_name,
        delay_in_secs,
        #
        asset_id_col_name,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


# TODO(gp): initial_replayed_delay -> initial_delay_in_mins (or in secs).
def get_ReplayedTimeMarketData_example2(
    event_loop: asyncio.AbstractEventLoop,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    initial_replayed_delay: int,
    asset_ids: List[int],
    *,
    delay_in_secs: int = 0,
    columns: Optional[List[str]] = None,
    sleep_in_secs: float = 1.0,
    time_out_in_secs: int = 60 * 2,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData` backed by synthetic data.

    :param start_datetime: start time for the generation of the synthetic data
    :param end_datetime: end time for the generation of the synthetic data
    :param initial_replayed_delay: how many minutes after the beginning of the data
        the replayed time starts. This is useful to simulate the beginning / end of
        the trading day
    :param asset_ids: asset ids to generate data for. `None` defaults to all the
        available asset ids in the data frame
    """
    # Build the df with the data.
    if columns is None:
        columns = ["last_price"]
    hdbg.dassert_is_not(asset_ids, None)
    df = cofinanc.generate_random_price_data(
        start_datetime, end_datetime, columns, asset_ids
    )
    (market_data, get_wall_clock_time,) = get_ReplayedTimeMarketData_from_df(
        event_loop,
        initial_replayed_delay,
        df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


def get_ReplayedTimeMarketData_example3(
    event_loop: asyncio.AbstractEventLoop,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData`:

    - with synthetic price data between `2000-01-01 9:30` and `10:30`
    - for two assets 101 and 202
    - starting 5 minutes after the data
    """
    # Generate random price data.
    start_datetime = pd.Timestamp(
        "2000-01-01 09:30:00-05:00", tz="America/New_York"
    )
    end_datetime = pd.Timestamp(
        "2000-01-01 10:30:00-05:00", tz="America/New_York"
    )
    columns_ = ["price"]
    asset_ids = [101, 202]
    df = cofinanc.generate_random_price_data(
        start_datetime, end_datetime, columns_, asset_ids
    )
    _LOG.debug("df=%s", hpandas.df_to_str(df))
    # Build a `ReplayedMarketData`.
    initial_replayed_delay = 5
    delay_in_secs = 0
    sleep_in_secs = 30
    time_out_in_secs = 60 * 5
    (market_data, get_wall_clock_time,) = get_ReplayedTimeMarketData_from_df(
        event_loop,
        initial_replayed_delay,
        df=df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


def get_ReplayedTimeMarketData_example4(
    event_loop: asyncio.AbstractEventLoop,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    initial_replayed_delay: int = 0,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData` with synthetic bar data.
    """
    # Generate random price data.
    df = cofinanc.generate_random_bars(start_datetime, end_datetime, asset_ids)
    _LOG.debug("df=%s", hpandas.df_to_str(df))
    # Build a `ReplayedMarketData`.
    delay_in_secs = 0
    sleep_in_secs = 30
    time_out_in_secs = 60 * 5
    market_data, get_wall_clock_time = get_ReplayedTimeMarketData_from_df(
        event_loop,
        initial_replayed_delay,
        df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


def get_ReplayedTimeMarketData_example5(
    event_loop: asyncio.AbstractEventLoop,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    initial_replayed_delay: int = 0,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData` with synthetic top-of-the-book data.
    """
    # Generate random price data.
    df = cofinanc.generate_random_top_of_book_bars(
        start_datetime, end_datetime, asset_ids
    )
    _LOG.debug("df=%s", hpandas.df_to_str(df))
    # Build a `ReplayedMarketData`.
    delay_in_secs = 0
    sleep_in_secs = 30
    time_out_in_secs = 60 * 5
    market_data, get_wall_clock_time = get_ReplayedTimeMarketData_from_df(
        event_loop,
        initial_replayed_delay,
        df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


# #############################################################################
# ImClientMarketData examples
# #############################################################################


def _get_last_timestamp(
    client: icdc.ImClient, asset_ids: Optional[List[int]]
) -> pd.Timestamp:
    """
    Get the latest timestamp + 1 minute for the provided asset ids.
    """
    # To receive the latest timestamp from `ImClient` one should pass a full
    # symbol, because `ImClient` operates with full symbols.
    full_symbols = client.get_full_symbols_from_asset_ids(asset_ids)
    last_timestamps = []
    for full_symbol in full_symbols:
        last_timestamp = client.get_end_ts_for_symbol(full_symbol)
        last_timestamps.append(last_timestamp)
    last_timestamp = max(last_timestamps) + pd.Timedelta(minutes=1)
    return last_timestamp


def get_CcxtCsvImClientMarketData_example1(
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with `CCXT` CSV data.
    """
    resample_1min = True
    im_client = icdcl.get_CcxtCsvClient_example1(resample_1min)
    # Build a function that returns a wall clock to initialise `MarketData`.
    last_timestamp = _get_last_timestamp(im_client, asset_ids)

    def get_wall_clock_time() -> pd.Timestamp:
        return last_timestamp

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdimcmada.ImClientMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client=im_client,
        column_remap=column_remap,
    )
    return market_data


def get_CcxtPqImClientMarketData_example1(
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with `CCXT` Parquet by tile data.

    The wall clock is a hard-wired timestamp. To get the maximum
    timestamp we need to read all the data which is an expensive
    operation.
    """
    resample_1min = False
    im_client = icdcl.get_CcxtHistoricalPqByTileClient_example1(resample_1min)
    # Build a function that returns a wall clock to initialise `MarketData`.

    def get_wall_clock_time() -> pd.Timestamp:
        return pd.Timestamp("2100-01-01T00:00:00+00:00")

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdimcmada.ImClientMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client=im_client,
        column_remap=column_remap,
    )
    return market_data


def get_CcxtPqImClientMarketData_example2(
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with `CCXT` Parquet by tile unit test
    data.
    """
    resample_1min = False
    im_client = icdcl.get_CcxtHistoricalPqByTileClient_example2(resample_1min)
    # Build a function that returns a wall clock to initialise `MarketData`.
    last_timestamp = _get_last_timestamp(im_client, asset_ids)

    def get_wall_clock_time() -> pd.Timestamp:
        return last_timestamp

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdimcmada.ImClientMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client=im_client,
        column_remap=column_remap,
    )
    return market_data


def get_DataFrameImClientMarketData_example1(
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with synthetic data.
    """
    im_client = icdc.get_DataFrameImClient_example1()
    # Build a function that returns a wall clock to initialise `MarketData`.
    last_timestamp = _get_last_timestamp(im_client, asset_ids)

    def get_wall_clock_time() -> pd.Timestamp:
        return last_timestamp

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdimcmada.ImClientMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client=im_client,
        column_remap=column_remap,
    )
    return market_data


def get_TalosPqImClientMarketData_example1(
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with `Talos` Parquet by tile data.
    """
    resample_1min = False
    im_client = itdcl.get_TalosHistoricalPqByTileClient_example2(resample_1min)
    # Build a function that returns a wall clock to initialise `MarketData`.
    last_timestamp = _get_last_timestamp(im_client, asset_ids)

    def get_wall_clock_time() -> pd.Timestamp:
        return last_timestamp

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdimcmada.ImClientMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client=im_client,
        column_remap=column_remap,
    )
    return market_data


def get_RealTimeImClientMarketData_example1(
    # TODO(Danya): Initialize im_client from outside the method.
    connection: hsql.DbConnection,
    event_loop: asyncio.AbstractEventLoop,
    asset_ids: List[int],
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `RealTimeMarketData` with data coming from an `RealTimeImClient`.
    """
    resample_1min = False
    im_client = icdc.get_example1_realtime_client(connection, resample_1min)
    asset_id_col = "asset_id"
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    # Build a `ReplayedMarketData`.
    tz = "ET"
    initial_replayed_dt = pd.Timestamp(
        "2000-01-01 09:30:00-05:00", tz="America/New_York"
    )
    speed_up_factor = 1.0
    get_wall_clock_time = creatime.get_replayed_wall_clock_time(
        tz,
        initial_replayed_dt,
        event_loop=event_loop,
        speed_up_factor=speed_up_factor,
    )
    # Build a `ReplayedMarketData`.
    sleep_in_secs = 1.0
    time_out_in_secs = 60 * 2
    # Note: the `asset_id` value in Example1 data is 1467591036.
    market_data = mdrtmada.RealTimeMarketData2(
        im_client,
        #
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time
