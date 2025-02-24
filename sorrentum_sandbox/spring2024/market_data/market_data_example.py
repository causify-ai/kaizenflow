"""
Import as:

import market_data.market_data_example as mdmadaex
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

import core.finance as cofinanc
import core.real_time as creatime
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.crypto_chassis.data.client as iccdc
import market_data.im_client_market_data as mdimcmada
import market_data.real_time_market_data as mdrtmada
import market_data.replayed_market_data as mdremada
import market_data.stitched_market_data as mdstmada

_LOG = logging.getLogger(__name__)


# #############################################################################
# ReplayedTimeMarketData examples
# #############################################################################


# TODO(gp): Create an analogue of this for historical market data.
# TODO(gp): Return only MarketData since the wall clock is inside it.
def get_ReplayedTimeMarketData_from_df(
    event_loop: asyncio.AbstractEventLoop,
    # TODO(Grisha): allow to pass timestamps directly.
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
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

    The integer approach for `replayed_delay_in_mins_or_timestamp` is possible
    only when there is a time reference (e.g., the initial or end of data) and
    then one can say "N minutes" before/after and in that case we want to use
    `replayed_delay_in_mins_or_timestamp` as int to resolve it. However, using
    timestamp is prefered whenever possible since it is clearer.

    :param df: dataframe including the columns
        ["timestamp_db", "asset_id", "start_datetime", "end_datetime"]
    :param replayed_delay_in_mins_or_timestamp: how many minutes after the beginning
        of the data the replayed time starts. This is useful to simulate the
        beginning / end of the trading day.
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
    # Find min and max timestamps.
    # TODO(Grisha): use `end_time_col_name` Cm Task #2908.
    min_timestamp = df[start_time_col_name].min()
    max_timestamp = df[start_time_col_name].max()
    _LOG.debug(hprint.to_str("min_timestamp max_timestamp"))
    if isinstance(replayed_delay_in_mins_or_timestamp, int):
        # We can't enable this assertion since some tests
        # (e.g., `TestReplayedMarketData3::test_is_last_bar_available1`)
        # use a negative offset to start replaying the data, before data is
        # available.
        # hdbg.dassert_lte(0, replayed_delay_in_mins_or_timestamp)
        # Shift the minimum timestamp by the specified number of minutes.
        initial_replayed_timestamp = min_timestamp + pd.Timedelta(
            minutes=replayed_delay_in_mins_or_timestamp
        )
    elif isinstance(replayed_delay_in_mins_or_timestamp, pd.Timestamp):
        hdateti.dassert_tz_compatible_timestamp_with_df(
            replayed_delay_in_mins_or_timestamp, df, start_time_col_name
        )
        initial_replayed_timestamp = replayed_delay_in_mins_or_timestamp
    else:
        raise ValueError(
            f"Invalid replayed_delay_in_mins_or_timestamp='{replayed_delay_in_mins_or_timestamp}'"
        )
    _LOG.debug(
        hprint.to_str(
            "replayed_delay_in_mins_or_timestamp initial_replayed_timestamp"
        )
    )
    if initial_replayed_timestamp > max_timestamp:
        _LOG.warning(
            "The initial replayed datetime %s "
            "should be before the end of the data %s",
            initial_replayed_timestamp,
            max_timestamp,
        )
    speed_up_factor = 1.0
    get_wall_clock_time = creatime.get_replayed_wall_clock_time(
        tz,
        initial_replayed_timestamp,
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


def get_ReplayedTimeMarketData_example2(
    event_loop: asyncio.AbstractEventLoop,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp],
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
    :param replayed_delay_in_mins_or_timestamp: how many minutes after the beginning of the data
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
    (
        market_data,
        get_wall_clock_time,
    ) = get_ReplayedTimeMarketData_from_df(
        event_loop,
        replayed_delay_in_mins_or_timestamp,
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
    replayed_delay_in_mins_or_timestamp = 5
    delay_in_secs = 0
    sleep_in_secs = 30
    time_out_in_secs = 60 * 5
    (
        market_data,
        get_wall_clock_time,
    ) = get_ReplayedTimeMarketData_from_df(
        event_loop,
        replayed_delay_in_mins_or_timestamp,
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
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp] = 0,
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
        replayed_delay_in_mins_or_timestamp,
        df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


# TODO(gp): @all -> start_datetime -> start_timestamp
def get_ReplayedTimeMarketData_example5(
    event_loop: asyncio.AbstractEventLoop,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    # TODO(Nina): propagate `generate_random_top_of_book_bars()` kwargs
    # to the params.
    replayed_delay_in_mins_or_timestamp: Union[int, pd.Timestamp] = 0,
    use_midpoint_as_price: bool = False,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    """
    Build a `ReplayedMarketData` with synthetic top-of-the-book data.

    - E.g.,
    ```
                 start_datetime              end_datetime              timestamp_db     bid     ask  midpoint  volume  asset_id
    0 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00 2000-01-01 09:31:01-05:00  998.90  998.96   998.930     994       101
    1 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00 2000-01-01 09:32:01-05:00  998.17  998.19   998.180    1015       101
    2 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00 2000-01-01 09:33:01-05:00  997.39  997.44   997.415     956       101
    ```

    :param use_midpoint_as_price: if True, a column `price` is added equal to the
        column `midpoint`
    """
    # Generate random price data.
    df = cofinanc.generate_random_top_of_book_bars(
        start_datetime,
        end_datetime,
        asset_ids,
    )
    if use_midpoint_as_price:
        df["price"] = df["midpoint"]
    _LOG.debug("df=%s", hpandas.df_to_str(df))
    # Build a `ReplayedMarketData`.
    delay_in_secs = 0
    sleep_in_secs = 30
    time_out_in_secs = 60 * 5
    market_data, get_wall_clock_time = get_ReplayedTimeMarketData_from_df(
        event_loop,
        replayed_delay_in_mins_or_timestamp,
        df,
        delay_in_secs=delay_in_secs,
        sleep_in_secs=sleep_in_secs,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


# #############################################################################
# Historical ImClientMarketData examples
# #############################################################################


def _get_last_timestamp(
    client: icdc.ImClient, asset_ids: Optional[List[int]]
) -> pd.Timestamp:
    """
    Get the min latest timestamp + 1 minute for the provided asset ids.

    We pick the minimum across max timestamps to guarantee that there is data
    for all assets. That is useful when we compute `last_end_time` where we check
    data for the interval `[wall_clock_time - epsilon, wall_clock_time]`. E.g.,
    max timestamp for asset1 is "2022-07-11" and for asset2 it is "2022-07-10".
    If we pick the maximum across assets (i.e. "2022-07-11") we won't be able
    to get data for asset2 in the interval `["2022-07-11" - 1 hour, "2022-07-11"]`.
    """
    # To receive the latest timestamp from `ImClient` one should pass a full
    # symbol, because `ImClient` operates with full symbols.
    full_symbols = client.get_full_symbols_from_asset_ids(asset_ids)
    last_timestamps = []
    for full_symbol in full_symbols:
        last_timestamp = client.get_end_ts_for_symbol(full_symbol)
        last_timestamps.append(last_timestamp)
    last_timestamp = min(last_timestamps) + pd.Timedelta(minutes=1)
    return last_timestamp


# TODO(gp): @Grisha This should not be here. It should be somewhere else.
def get_HistoricalImClientMarketData_example1(
    im_client: icdc.ImClient,
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
    *,
    wall_clock_time: Optional[pd.Timestamp] = None,
    filter_data_mode: str = "assert",
) -> mdimcmada.ImClientMarketData:
    """
    Build a `ImClientMarketData` backed with the data defined by `im_client`.
    """
    # Build a function that returns a wall clock to initialise `MarketData`.
    if wall_clock_time is None:
        # The maximum timestamp is set from the data except for the cases when
        # it's too computationally expensive to read all of the data on the fly.
        wall_clock_time = _get_last_timestamp(im_client, asset_ids)

    def get_wall_clock_time() -> pd.Timestamp:
        return wall_clock_time

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
        filter_data_mode=filter_data_mode,
    )
    return market_data


# #############################################################################
# Real-time ImClientMarketData examples
# #############################################################################


def get_ReplayedImClientMarketData_example1(
    im_client: icdc.ImClient,
    event_loop: asyncio.AbstractEventLoop,
    asset_ids: List[int],
    initial_replayed_timestamp: pd.Timestamp,
) -> Tuple[mdremada.ReplayedMarketData, hdateti.GetWallClockTime]:
    # TODO(Max): Refactor mix of replay and realtime.
    """
    Build a `ReplayedMarketData2` with data coming from an `RealTimeImClient`.
    """
    asset_id_col = "asset_id"
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    # Build a `ReplayedMarketData`.
    tz = "ET"
    # TODO(Grisha): @Dan use the same timezone as above, explore `hdatetime`.
    speed_up_factor = 1.0
    get_wall_clock_time = creatime.get_replayed_wall_clock_time(
        tz,
        initial_replayed_timestamp,
        event_loop=event_loop,
        speed_up_factor=speed_up_factor,
    )
    # Build a `ReplayedMarketData`.
    market_data = mdrtmada.RealTimeMarketData2(
        im_client,
        #
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
    )
    return market_data, get_wall_clock_time


def get_RealtimeMarketData2_example1(
    im_client: icdc.RealTimeImClient,
) -> mdrtmada.RealTimeMarketData2:
    """
    Create a RealTimeMarketData2 to use in tests.

    This example is geared to work with `icdc.get_mock_realtime_client`.
    """
    asset_id_col = "asset_id"
    asset_ids = [1464553467]
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    get_wall_clock_time = lambda: pd.Timestamp(
        "2022-04-23", tz="America/New_York"
    )
    market_data = mdrtmada.RealTimeMarketData2(
        im_client,
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
    )
    return market_data


def get_RealTimeImClientMarketData_example1(
    im_client: icdc.ImClient,
    asset_ids: List[int],
) -> Tuple[mdrtmada.RealTimeMarketData2, hdateti.GetWallClockTime]:
    """
    Build a `RealTimeMarketData` with the real wall-clock.

    `MarketData` is backed by a DB updated in real-time.
    """
    asset_id_col = "asset_id"
    start_time_col_name = "start_timestamp"
    end_time_col_name = "end_timestamp"
    columns = None
    event_loop = None
    get_wall_clock_time = lambda: hdateti.get_current_time(
        tz="ET", event_loop=event_loop
    )
    # We can afford to wait only for 60 seconds in prod because we need to have
    # enough time to compute the forecasts and after one minute we start
    # getting data for the next bar.
    time_out_in_secs = 60
    #
    market_data = mdrtmada.RealTimeMarketData2(
        im_client,
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        time_out_in_secs=time_out_in_secs,
    )
    return market_data, get_wall_clock_time


# #############################################################################
# StitchedMarketData examples
# #############################################################################


def get_HorizontalStitchedMarketData_example1(
    im_client_market_data1: mdimcmada.ImClientMarketData,
    im_client_market_data2: mdimcmada.ImClientMarketData,
    asset_ids: Optional[List[int]],
    columns: List[str],
    column_remap: Optional[Dict[str, str]],
    *,
    wall_clock_time: Optional[pd.Timestamp] = None,
    filter_data_mode: str = "assert",
) -> mdstmada.HorizontalStitchedMarketData:
    """
    Build a `HorizontalStitchedMarketData` backed with the data defined by
    `ImClient`s.
    """
    # Build a function that returns a wall clock to initialise `MarketData`.
    if wall_clock_time is None:
        # The maximum timestamp is set from the data except for the cases when
        # it's too computationally expensive to read all of the data on the fly.
        wall_clock_time1 = im_client_market_data1.get_wall_clock_time()
        wall_clock_time2 = im_client_market_data2.get_wall_clock_time()
        wall_clock_time = max(wall_clock_time1, wall_clock_time2)

    def get_wall_clock_time() -> pd.Timestamp:
        return wall_clock_time

    #
    asset_id_col = "asset_id"
    start_time_col_name = "start_ts"
    end_time_col_name = "end_ts"
    market_data = mdstmada.HorizontalStitchedMarketData(
        asset_id_col,
        asset_ids,
        start_time_col_name,
        end_time_col_name,
        columns,
        get_wall_clock_time,
        im_client_market_data1=im_client_market_data1,
        im_client_market_data2=im_client_market_data2,
        column_remap=column_remap,
        filter_data_mode=filter_data_mode,
    )
    return market_data


# TODO(Grisha): we should mock ImClients.
def get_CryptoChassis_BidAskOhlcvMarketData_example1(
    asset_ids: List[int],
    universe_version1: str,
    data_snapshot1: str,
    *,
    universe_version2: Optional[str] = None,
    data_snapshot2: Optional[str] = None,
    wall_clock_time: Optional[pd.Timestamp] = None,
    filter_data_mode: str = "assert",
) -> mdstmada.HorizontalStitchedMarketData:
    # pylint: disable=line-too-long
    """
    Build a `HorizontalStitchedMarketData`:

    - with "ohlcv" and "bid_ask" dataset type `ImClient`s
    - with CryptoChassis `ImClient`s
    - `contract_type` = "futures"

    Output df:
    ```
                                 asset_id        full_symbol      open      high       low     close    volume        vwap  number_of_trades        twap              knowledge_timestamp                  start_ts     bid_price  bid_size     ask_price  ask_size
    end_ts
    2022-04-30 20:01:00-04:00  1464553467  binance::ETH_USDT   2726.62   2727.16   2724.99   2725.59   648.179   2725.8408               618   2725.7606 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:00:00-04:00   2725.493716  1035.828   2725.731107  1007.609
    2022-04-30 20:01:00-04:00  1467591036  binance::BTC_USDT  37635.00  37635.60  37603.70  37626.80   168.216  37619.4980              1322  37619.8180 2022-06-20 09:48:46.910826+00:00 2022-04-30 20:00:00-04:00  37620.402680   120.039  37622.417898   107.896
    2022-04-30 20:02:00-04:00  1464553467  binance::ETH_USDT   2725.59   2730.42   2725.59   2730.04  1607.265   2728.7821              1295   2728.3652 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:01:00-04:00   2728.740700   732.959   2728.834137  1293.961
    ```
    """
    # pylint: enable=line-too-long
    contract_type = "futures"
    if universe_version2 is None:
        universe_version2 = universe_version1
    if data_snapshot2 is None:
        data_snapshot2 = data_snapshot1
    #
    dataset1 = "ohlcv"
    im_client1 = iccdc.get_CryptoChassisHistoricalPqByTileClient_example1(
        universe_version1,
        dataset1,
        contract_type,
        data_snapshot1,
    )
    #
    dataset2 = "bid_ask"
    im_client2 = iccdc.get_CryptoChassisHistoricalPqByTileClient_example1(
        universe_version2,
        dataset2,
        contract_type,
        data_snapshot2,
    )
    #
    columns = None
    column_remap = None
    #
    im_client_market_data1 = get_HistoricalImClientMarketData_example1(
        im_client1,
        asset_ids,
        columns,
        column_remap,
        wall_clock_time=wall_clock_time,
        filter_data_mode=filter_data_mode,
    )
    im_client_market_data2 = get_HistoricalImClientMarketData_example1(
        im_client2,
        asset_ids,
        columns,
        column_remap,
        wall_clock_time=wall_clock_time,
        filter_data_mode=filter_data_mode,
    )
    market_data = get_HorizontalStitchedMarketData_example1(
        im_client_market_data1,
        im_client_market_data2,
        asset_ids,
        columns,
        column_remap,
        wall_clock_time=wall_clock_time,
        filter_data_mode=filter_data_mode,
    )
    return market_data
