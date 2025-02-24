"""
Import as:

import core.finance.market_data_example as cfmadaex
"""

import datetime
import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hnumpy as hnumpy
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# #############################################################################
# Utils
# #############################################################################


def generate_random_ohlcv_bars_for_asset(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_id: int,
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a dataframe of random OHLCV bars for a single instrument.

    :param start_datetime: initial timestamp
    :param end_datetime: final timestamp
    :param asset_id: asset id for labeling
    :param bar_duration: length of bar in time
    :param bar_volatility_in_bps: expected bar volatility
    :param bar_expected_count: expected volume per bar
    :param last_price: "last price" before start of series
    :param start_time: e.g., start of active trading hours
    :param end_time: e.g., end of active trading hours
    :param seed: seed for numpy `Generator`
    :return: dataframe like
      - index is an integer index
      - columns include timestamps, asset id, open, high, low, close, volume
    TODO(gp): @all add example.
    """
    price_process = carsigen.PriceProcess(seed)
    native_bar_duration = "1T"
    bar_ratio = pd.Timedelta(bar_duration) / pd.Timedelta(native_bar_duration)
    native_bar_volatility_in_bps = int(bar_volatility_in_bps / np.sqrt(bar_ratio))
    _LOG.debug("1-min bar volatility in bps=%d", native_bar_volatility_in_bps)
    native_bar_expected_count = int(bar_expected_count / bar_ratio)
    _LOG.debug("1-min bar expected count=%d", native_bar_expected_count)
    close = price_process.generate_price_series_from_normal_log_returns(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=native_bar_duration,
        bar_volatility_in_bps=native_bar_volatility_in_bps,
        last_price=last_price,
        start_time=start_time,
        end_time=end_time,
    ).rename("close")
    ohlc = (
        close.resample(bar_duration, label="right", closed="right")
        .ohlc()
        .round(2)
    )
    volume = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=native_bar_duration,
        bar_expected_count=native_bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("volume")
    volume = volume.resample(bar_duration, label="right", closed="right").sum(
        min_count=1
    )
    bar_delay = "10s"
    df = build_timestamp_df(
        ohlc.index,
        bar_duration,
        bar_delay,
    )
    df = pd.concat(
        [df, ohlc, volume],
        axis=1,
    )
    df["asset_id"] = asset_id
    return df.reset_index(drop=True)


# TODO(Paul): Consider factoring out this wrapper pattern.
# TODO(gp): Pass the defaults as kwargs.
def generate_random_ohlcv_bars(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Wrap `generate_random_ohlcv_bars_for_asset()` for multiple instruments.

    :return: dataframe as in `generate_random_ohlcv_bars_for_asset()`,
        concatenated along the index, sorted by timestamp then by asset it
    """
    asset_dfs = []
    for asset_id in asset_ids:
        df = generate_random_ohlcv_bars_for_asset(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            bar_expected_count=bar_expected_count,
            last_price=last_price,
            start_time=start_time,
            end_time=end_time,
            seed=seed,
        )
        asset_dfs.append(df)
        seed += 1
    df = pd.concat(asset_dfs, axis=0).sort_values(["end_datetime", "asset_id"])
    df.reset_index(drop=True, inplace=True)
    return df


def generate_random_top_of_book_bars(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_spread_in_bps: int = 4,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Wrap `generate_random_top_of_book_bars_for_asset()` for multiple
    instruments.

    :return: dataframe like
      - index is an integer index
      - columns include timestamps, asset ids, price, volume, and fake features
    ```
                  start_datetime ...        ask     midpoint  volume  asset_id
    0  2000-01-01 09:31:00-05:00     998.897634   998.897480     988       101
    1  2000-01-01 09:31:00-05:00    1000.120981  1000.117331     955       102
    2  2000-01-01 09:32:00-05:00     997.401239   997.399872    1045       101
    ```
    """
    asset_dfs = []
    for asset_id in asset_ids:
        df = generate_random_top_of_book_bars_for_asset(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            bar_spread_in_bps=bar_spread_in_bps,
            bar_expected_count=bar_expected_count,
            last_price=last_price,
            start_time=start_time,
            end_time=end_time,
            seed=seed,
        )
        asset_dfs.append(df)
        seed += 1
    df = pd.concat(asset_dfs, axis=0).sort_values(["end_datetime", "asset_id"])
    return df


def generate_random_top_of_book_bars_for_asset(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_id: int,
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_spread_in_bps: int = 4,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a dataframe of random bars for a single instrument.

    :param start_datetime: initial timestamp
    :param end_datetime: final timestamp
    :param asset_id: asset id for labeling
    :param bar_duration: length of bar in time
    :param bar_volatility_in_bps: expected bar volatility
    :param bar_spread_in_bps: expected bar spread
    :param bar_expected_count: expected volume per bar
    :param last_price: "last price" before start of series
    :param start_time: e.g., start of active trading hours
    :param end_time: e.g., end of active trading hours
    :param seed: seed for numpy `Generator`
    :return: dataframe like
      - index is an integer index
      - columns include timestamps, asset id, price, volume, and fake features
    ```
                  start_datetime ...        ask    midpoint  volume  asset_id
    0  2000-01-01 09:31:00-05:00     998.897634  998.897480     988       101
    1  2000-01-01 09:32:00-05:00     998.120981  998.117331     955       101
    2  2000-01-01 09:33:00-05:00     997.401239  997.399872    1045       101
    ```
    """
    price_process = carsigen.PriceProcess(seed)
    bid = (
        price_process.generate_price_series_from_normal_log_returns(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            last_price=last_price,
            start_time=start_time,
            end_time=end_time,
        )
        .rename("bid")
        .round(2)
    )
    spread = (
        (
            100
            * price_process.generate_price_series_from_normal_log_returns(
                start_datetime,
                end_datetime,
                asset_id,
                bar_duration=bar_duration,
                bar_volatility_in_bps=bar_spread_in_bps,
                last_price=last_price,
                start_time=start_time,
                end_time=end_time,
            )
            .pct_change()
            .shift(-1)
            .abs()
        )
        .round(2)
        .clip(lower=0.01)
    )
    ask = (bid + spread).rename("ask").round(2)
    midpoint = (0.5 * (bid + ask)).rename("midpoint")
    volume = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("volume")
    bar_delay = "1s"
    df = build_timestamp_df(
        bid.index,
        bar_duration,
        bar_delay,
    )
    df = pd.concat(
        [df, bid, ask, midpoint, volume],
        axis=1,
    )
    df["asset_id"] = asset_id
    return df.reset_index(drop=True)


def generate_random_price_data(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    columns: List[str],
    asset_ids: List[int],
    *,
    freq: str = "1T",
    initial_price: float = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic data used to mimic real-time price data.

    :return: dataframe with random walk with a bias of 1000 and increments
        ~ iid U[-0.5, 0.5]
        ```
                      start_datetime ...        price       volume   asset_id
        0  2000-01-01 09:31:00-05:00       999.874540   999.874540        101
        1  2000-01-01 09:32:00-05:00      1000.325254  1000.325254        101
        2  2000-01-01 09:33:00-05:00      1000.525588  1000.525588        101
        ```
    """
    _LOG.debug(
        hprint.to_str("start_datetime end_datetime columns asset_ids freq seed")
    )
    hdateti.dassert_tz_compatible(start_datetime, end_datetime)
    hdbg.dassert_lte(start_datetime, end_datetime)
    hdbg.dassert_isinstance(asset_ids, list)
    #
    start_dates = pd.date_range(start_datetime, end_datetime, freq=freq)
    dfs = []
    time_delta = pd.Timedelta(freq)
    for asset_id in asset_ids:
        df = pd.DataFrame()
        df["start_datetime"] = start_dates
        df["end_datetime"] = start_dates + time_delta
        # TODO(gp): We can add 1 sec here to make it more interesting.
        df["timestamp_db"] = df["end_datetime"]
        # TODO(gp): Filter by ATH, if needed.
        # Random walk with increments independent and uniform in [-0.5, 0.5].
        for column in columns:
            with hnumpy.random_seed_context(seed):
                data = np.random.rand(len(start_dates), 1) - 0.5  # type: ignore[var-annotated]
            df[column] = initial_price + data.cumsum()
        df["asset_id"] = asset_id
        dfs.append(df)
    df = pd.concat(dfs, axis=0)
    return df


def generate_random_bars(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Wrap `generate_random_bars_for_asset()` for multiple instruments.

    :return: dataframe as in `generate_random_bars_for_asset()`, concatenated
        along the index, sorted by timestamp then by asset it
        ```
                      start_datetime ... volume    f1    f2    s1   s2  asset_id
        0  2000-01-01 09:31:00-05:00        941  2010  1990  2.22  111       101
        1  2000-01-01 09:31:00-05:00        997  1999  1985  0.90   90       102
        2  2000-01-01 09:32:00-05:00       1043  2004  2015  6.82  115       101
        ```
    """
    asset_dfs = []
    for asset_id in asset_ids:
        df = generate_random_bars_for_asset(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            bar_expected_count=bar_expected_count,
            last_price=last_price,
            start_time=start_time,
            end_time=end_time,
            seed=seed,
        )
        asset_dfs.append(df)
        seed += 1
    df = pd.concat(asset_dfs, axis=0).sort_values(["end_datetime", "asset_id"])
    df.reset_index(drop=True, inplace=True)
    return df


def generate_random_bars_for_asset(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_id: int,
    *,
    bar_duration: str = "1T",
    bar_volatility_in_bps: int = 10,
    bar_expected_count: int = 1000,
    last_price: float = 1000,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a dataframe of random bars for a single instrument.

    :param start_datetime: initial timestamp
    :param end_datetime: final timestamp
    :param asset_id: asset id for labeling
    :param bar_duration: length of bar in time
    :param bar_volatility_in_bps: expected bar volatility
    :param bar_expected_count: expected volume per bar
    :param last_price: "last price" before start of series
    :param start_time: e.g., start of active trading hours
    :param end_time: e.g., end of active trading hours
    :param seed: seed for numpy `Generator`
    :return: dataframe like
      - index is an integer index
      - columns include timestamps, asset id, price, volume, and fake features
        ```
                      start_datetime ... volume    f1    f2    s1   s2  asset_id
        0  2000-01-01 09:31:00-05:00        941  2010  1990  2.22  111       101
        1  2000-01-01 09:32:00-05:00       1035  1935  1996  1.90  117       101
        2  2000-01-01 09:33:00-05:00       1043  2004  2015  6.82  115       101
        ```
    """
    price_process = carsigen.PriceProcess(seed)
    close = price_process.generate_price_series_from_normal_log_returns(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_volatility_in_bps=bar_volatility_in_bps,
        last_price=last_price,
        start_time=start_time,
        end_time=end_time,
    ).rename("close")
    volume = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("volume")
    f1 = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=2 * bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("f1")
    f2 = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=2 * bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("f2")
    s1 = 0.01 * price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=2,
        start_time=start_time,
        end_time=end_time,
    )
    s2 = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=0.1 * bar_expected_count,
        start_time=start_time,
        end_time=end_time,
    ).rename("s2")
    s1 = (s1 * s2).groupby(lambda x: x.date()).cumsum().rename("s1")
    # TODO(Paul): Expose the bar delay.
    bar_delay = "10s"
    df = build_timestamp_df(
        close.index,
        bar_duration,
        bar_delay,
    )
    df = pd.concat(
        [df, close, volume, f1, f2, s1, s2],
        axis=1,
    )
    df["asset_id"] = asset_id
    return df.reset_index(drop=True)


def build_timestamp_df(
    index: pd.DatetimeIndex,
    bar_duration: str,
    bar_delay: str,
) -> pd.DataFrame:
    """
    Generate dataframe with start, end, and DB timestamps from the given index.

    :param index: index to use as end datetime
    :param bar_duration: duration between start and end timestamps, e.g. "1T"
    :param bar_delay: delay between end and database timestamps, e.g. "10sec"
    :return:
        ```
                                  start_datetime ...        timestamp_db
        2000-01-01 09:31:00  2000-01-01 09:30:00     2000-01-01 09:31:10
        2000-01-01 09:32:00  2000-01-01 09:31:00     2000-01-01 09:32:10
        2000-01-01 09:33:00  2000-01-01 09:32:00     2000-01-01 09:33:10
        ```
    """
    hdbg.dassert_isinstance(index, pd.DatetimeIndex)
    bar_time_delta = pd.Timedelta(bar_duration)
    start_datetime = pd.Series(
        data=index - bar_time_delta, index=index, name="start_datetime"
    )
    end_datetime = pd.Series(data=index, index=index, name="end_datetime")
    bar_time_delay = pd.Timedelta(bar_delay)
    timestamp = pd.Series(
        data=index + bar_time_delay, index=index, name="timestamp_db"
    )
    df = pd.concat(
        [start_datetime, end_datetime, timestamp],
        axis=1,
    )
    return df


# #############################################################################
# MarketDataDf examples
# #############################################################################


# `get_MarketData_df...()` functions return the timeout in seconds corresponding
# the returned data.


# TODO(gp): @all -> get_MarketDataDf_example1()
def get_MarketData_df1() -> Tuple[pd.DataFrame, int]:
    """
    Generate price data with in the interval [2000-01-01 09:31, 2000-01-01
    10:10].

    - return: dataframe, e.g.,
        ```
                                              start_datetime ... volume  feature1
        2000-01-01 09:31:00-05:00  2000-01-01 09:30:00-05:00        100      -1.0
        2000-01-01 09:32:00-05:00  2000-01-01 09:31:00-05:00        100      -1.0
        ...
        2000-01-01 10:09:00-05:00 2000-01-01 10:08:00-05:00         100      -1.0
        2000-01-01 10:10:00-05:00 2000-01-01 10:09:00-05:00         100      -1.0
        ```
    """
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 09:31:00-05:00", tz="America/New_York"),
        end=pd.Timestamp("2000-01-01 10:10:00-05:00", tz="America/New_York"),
        freq="T",
    )
    bar_duration = "1T"
    bar_delay = "0T"
    data = build_timestamp_df(idx, bar_duration, bar_delay)
    price_pattern = [101.0] * 5 + [100.0] * 5
    price = price_pattern * 4
    data["close"] = price
    data["asset_id"] = 101
    data["volume"] = 100
    feature_pattern = [1.0] * 5 + [-1.0] * 5
    feature = feature_pattern * 4
    data["feature1"] = feature
    rt_timeout_in_secs_or_time = 35 * 60
    return data, rt_timeout_in_secs_or_time


def get_MarketData_df2() -> Tuple[pd.DataFrame, int]:
    """
    Generate price like `get_MarketData_df1()` but with a different pattern.

    - return: dataframe, e.g.,
        ```
                                              start_datetime ... volume  feature1
        2000-01-01 09:31:00-05:00  2000-01-01 09:30:00-05:00        100      -1.0
        2000-01-01 09:32:00-05:00  2000-01-01 09:31:00-05:00        100      -1.0
        ...
        2000-01-01 10:09:00-05:00 2000-01-01 10:08:00-05:00         100       1.0
        2000-01-01 10:10:00-05:00 2000-01-01 10:09:00-05:00         100       1.0
        ```
    """
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 09:31:00-05:00", tz="America/New_York"),
        end=pd.Timestamp("2000-01-01 10:10:00-05:00", tz="America/New_York"),
        freq="T",
    )
    bar_duration = "1T"
    bar_delay = "0T"
    data = build_timestamp_df(idx, bar_duration, bar_delay)
    price_pattern = [101.0] * 2 + [100.0] * 2 + [101.0] * 2 + [102.0] * 4
    price = price_pattern * 4
    data["close"] = price
    data["asset_id"] = 101
    data["volume"] = 100
    feature_pattern = [-1.0] * 5 + [1.0] * 5
    feature = feature_pattern * 4
    data["feature1"] = feature
    rt_timeout_in_secs_or_time = 35 * 60
    return data, rt_timeout_in_secs_or_time


def get_MarketData_df3() -> Tuple[pd.DataFrame, int]:
    """
    Generate price series with a price pattern and a real-time loop timeout in
    seconds to test model.

    :return:
        ```
                                              start_datetime ... volume  feature1
        2000-01-01 09:31:00-05:00  2000-01-01 09:30:00-05:00        100      -1.0
        2000-01-01 09:32:00-05:00  2000-01-01 09:31:00-05:00        100      -1.0
        ...
        ```
    """
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 09:31:00-05:00", tz="America/New_York"),
        end=pd.Timestamp("2000-01-01 11:30:00-05:00", tz="America/New_York"),
        freq="T",
    )
    bar_duration = "1T"
    bar_delay = "0T"
    data = build_timestamp_df(idx, bar_duration, bar_delay)
    price_pattern = [101.0] * 3 + [100.0] * 3 + [101.0] * 3 + [102.0] * 6
    price = price_pattern * 8
    data["close"] = price
    data["asset_id"] = 101
    data["volume"] = 100
    feature_pattern = [-1.0] * 5 + [1.0] * 5
    feature = feature_pattern * 12
    data["feature1"] = feature
    rt_timeout_in_secs_or_time = 115 * 60
    return data, rt_timeout_in_secs_or_time


def get_MarketData_df4() -> Tuple[pd.DataFrame, int]:
    """
    Generate price series with a price pattern and a real-time loop timeout in
    seconds to test model.

    :return
        ```
                                              start_datetime ... volume  feature1
        2000-01-01 09:31:00-05:00  2000-01-01 09:30:00-05:00        100      -1.0
        2000-01-01 09:32:00-05:00  2000-01-01 09:31:00-05:00        100      -1.0
        2000-01-01 09:33:00-05:00  2000-01-01 09:32:00-05:00        100      -1.0
        ```
    """
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 09:31:00-05:00", tz="America/New_York"),
        end=pd.Timestamp("2000-01-01 10:30:00-05:00", tz="America/New_York"),
        freq="T",
    )
    bar_duration = "1T"
    bar_delay = "0T"
    data = build_timestamp_df(idx, bar_duration, bar_delay)
    price_pattern = [101.0] * 5 + [100.0] * 5
    price = price_pattern * 6
    data["close"] = price
    data["asset_id"] = 101
    data["volume"] = 100
    feature_pattern = [1.0] * 5 + [-1.0] * 5
    feature = feature_pattern * 6
    data["feature1"] = feature
    rt_timeout_in_secs_or_time = 3 * 5 * 60
    return data, rt_timeout_in_secs_or_time


def get_MarketData_df5() -> pd.DataFrame:
    """
    Generate price series with a price pattern and a real-time loop timeout in
    seconds to test model.

    :return
        ```
                                              start_datetime ... volume  feature1
        2000-01-01 09:31:00-05:00  2000-01-01 09:30:00-05:00        100      -1.0
        2000-01-01 09:32:00-05:00  2000-01-01 09:31:00-05:00        100      -1.0
        2000-01-01 09:33:00-05:00  2000-01-01 09:32:00-05:00        100      -1.0
        ```
    """
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 09:31:00-05:00", tz="America/New_York"),
        end=pd.Timestamp("2000-01-01 10:30:00-05:00", tz="America/New_York"),
        freq="T",
    )
    bar_duration = "1T"
    bar_delay = "0T"
    data = build_timestamp_df(idx, bar_duration, bar_delay)
    price_pattern = [101.0] * 5 + [100.0] * 5
    price = price_pattern * 6
    data["close"] = price
    data["asset_id"] = [1467591036, 3303714233] * 30
    data["volume"] = 100
    feature_pattern = [1.0] * 5 + [-1.0] * 5
    feature = feature_pattern * 6
    data["feature1"] = feature
    rt_timeout_in_secs_or_time = 3 * 5 * 60
    return data, rt_timeout_in_secs_or_time


def get_MarketData_df6(full_symbols: List[str]) -> pd.DataFrame:
    """
    Generate `ImClient` output example with price data that alternates every 5
    minutes.

    Input full symbols represent `icdc.FullSymbol`.

    :return
        ```
                                        full_symbol ... close  volume  feature1
        timestamp
        2000-01-01 14:31:00+00:00  binance:BTC_USDT     101.0       0       1.0
        2000-01-01 14:32:00+00:00  binance:BTC_USDT     101.0       1       1.0
        2000-01-01 14:33:00+00:00  binance:BTC_USDT     101.0       2       1.0
        ```
    """
    # Pass timestamps within the U.S. active trading hours.
    idx = pd.date_range(
        start=pd.Timestamp("2000-01-01 14:31:00+00:00", tz="utc"),
        end=pd.Timestamp("2000-01-01 17:10:00+00:00", tz="utc"),
        freq="T",
    )
    # Set price and feature patterns for data alternating.
    # Data alternates every 5 minutes so we keep the same value for 5 minutes.
    # 10 minute patterns then are multiplied by `len_factor` to match index length.
    hdbg.dassert_eq(
        len(idx) % 10,
        0,
        msg=(
            "The date range is invalid: it must have a number of time periods "
            f"that is a multiple of 10; current number of time periods: {len(idx)}"
        ),
    )
    len_factor = int(len(idx) / 10)
    price_pattern = [101.0] * 5 + [100.0] * 5
    price = price_pattern * len_factor
    feature_pattern = [1.0] * 5 + [-1.0] * 5
    feature = feature_pattern * len_factor
    # Generate unique volume values to avoid dropping rows as duplicates.
    volume = list(range(len(idx)))
    # Generate data for each symbol.
    all_data_list: List = []
    for full_symbol in full_symbols:
        data = pd.DataFrame(index=idx)
        data["full_symbol"] = full_symbol
        data["open"] = 100
        data["high"] = 101
        data["low"] = 99
        data["close"] = price
        data["volume"] = volume
        data["feature1"] = feature
        all_data_list.append(data)
    # Combine data for all the symbols in one dataframe.
    all_data = pd.concat(all_data_list)
    all_data.index.name = "timestamp"
    all_data = all_data.sort_values(["timestamp", "full_symbol"])
    return all_data
