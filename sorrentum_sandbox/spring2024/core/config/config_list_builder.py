"""
Import as:

import core.config.config_list_builder as cccolibu
"""
import datetime
import logging
import re
from typing import Any, Callable, List, Optional, Tuple, Union

import pandas as pd

import core.config as cconfig
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.INFO)


# #############################################################################
# Asset universe.
# #############################################################################


# TODO(Grisha): consider returning vendor name, universe version and top_n.
def parse_universe_str(universe_str: str) -> Tuple[str, Optional[int]]:
    """
    Parse a string representing an universe.

    E.g., "kibot_v1_0-top100", "kibot_v2_0-all".
    """
    data = universe_str.split("-")
    hdbg.dassert_eq(len(data), 2, "Invalid universe='%s'", universe_str)
    universe_version, top_n = data
    if top_n == "all":
        top_n_ = None
    else:
        prefix = "top"
        hdbg.dassert(top_n.startswith(prefix), "Invalid top_n='%s'", top_n)
        top_n_ = int(top_n[len(prefix) :])
    return universe_version, top_n_


def get_universe_top_n(universe: List[Any], n: Optional[int]) -> List[Any]:
    if n is None:
        # No filtering.
        pass
    else:
        hdbg.dassert_lte(1, n, "Invalid n='%s'", n)
        hdbg.dassert_lte(n, len(universe))
        universe = universe[:n]
    universe = sorted(universe)
    return universe


# #############################################################################
# Period.
# #############################################################################


# TODO(gp): -> get_time_interval
def get_period(period: str) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Get start and end timestamps from the specified period.

    The usual period pattern looks the following: e.g., `2022-01-01_2022-02-01`.

    The interval type is [a, b), i.e. the last day of the interval is
    excluded.
    """
    # E.g., `2022-01-01`.
    date_pattern = "\d{4}[-]\d{2}[-]\d{2}"
    # E.g., `2022-01-01_2022-02-01`.
    period_pattern = rf"{date_pattern}[_]{date_pattern}$"
    if period == "2days":
        start_datetime = datetime.datetime(2020, 1, 6)
        end_datetime = datetime.datetime(2020, 1, 7)
    elif bool(re.match(period_pattern, period)):
        start_date, end_date = period.split("_")
        start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    else:
        hdbg.dfatal(f"Invalid period='{period}'")
    _LOG.info("start_datetime=%s end_datetime=%s", start_datetime, end_datetime)
    hdbg.dassert_lte(start_datetime, end_datetime)
    start_timestamp = pd.Timestamp(start_datetime, tz="UTC")
    end_timestamp = pd.Timestamp(end_datetime, tz="UTC")
    hdbg.dassert_lte(start_timestamp, end_timestamp)
    # Intervals for the time tiling is [a, b].
    end_timestamp -= pd.Timedelta(days=1)
    _LOG.info(
        "start_timestamp=%s end_timestamp=%s", start_timestamp, end_timestamp
    )
    return start_timestamp, end_timestamp


# #############################################################################
# Experiment config.
# #############################################################################


def parse_backtest_config(backtest_config: str) -> Tuple[str, str, str]:
    """
    Parse a string representing an experiment in the format:
    `<universe>.<trading_period>.<time_interval>`, e.g., "top100.15T.all".

    Each token can be composed of multiple chunks separated by `-`. E.g.,
    `universe_str = "eg_v1_0-top100"`

    :return: universe_str, trading_period_str, time_interval_str
    """
    _LOG.info(hprint.to_str("backtest_config"))
    #
    hdbg.dassert_isinstance(backtest_config, str)
    data = backtest_config.split(".")
    hdbg.dassert_eq(len(data), 3)
    universe_str, trading_period_str, time_interval_str = data
    #
    _LOG.info(hprint.to_str("universe_str trading_period_str time_interval_str"))
    return universe_str, trading_period_str, time_interval_str


# #############################################################################
# Experiment config processing.
# #############################################################################


def set_asset_id(
    config: cconfig.Config,
    asset_id_key: cconfig.CompoundKey,
    asset_id: Union[List[int], int],
    *,
    allow_new_key: bool = True,
    assume_dummy: bool = True,
) -> cconfig.Config:
    """
    Assign an `asset_id` to a config.

    :param asset_id_key: the key to assign
        - E.g., `("dag_config", "rets/read_data", "asset_id")`
    :param assume_dummy: assume that the value in the config corresponding to
        `asset_id_key` is `DUMMY`, i.e., it's coming from a template. This is
        used to enforce a use patter like "create a template config and then
        overwrite DUMMY values only once".
    """
    try:
        # Save original update mode and allow overwriting of dummies.
        update_mode = config.update_mode
        config.update_mode = "overwrite"
        hdbg.dassert_isinstance(config, cconfig.Config)
        _LOG.debug("Creating config for egid=`%s`", asset_id)
        if not allow_new_key:
            hdbg.dassert_in(asset_id_key, config)
            if assume_dummy:
                hdbg.dassert_eq(config.get(asset_id_key), cconfig.DUMMY)
        config[asset_id_key] = asset_id
    finally:
        # Reassign original update mode.
        config.update_mode = update_mode
    return config


def build_config_list_varying_asset_id(
    config_list: cconfig.ConfigList,
    asset_id_key: cconfig.CompoundKey,
    asset_ids: List[int],
) -> cconfig.ConfigList:
    """
    Create a list of `Config`s based on `config` using different `asset_ids`.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    _LOG.debug("Universe has %d asset_ids", len(asset_ids))
    configs = []
    config = config_list.get_only_config()
    for asset_id in asset_ids:
        config_tmp = config.copy()
        config_tmp = set_asset_id(config_tmp, asset_id_key, asset_id)
        _LOG.info("config_tmp=%s\n", config_tmp)
        #
        configs.append(config_tmp)
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    return config_list


# #############################################################################


# TODO(gp): -> ...varying_asset_tiles
def build_config_list_varying_universe_tiles(
    config_list: cconfig.ConfigList,
    universe_tile_id: cconfig.CompoundKey,
    # TODO(gp): -> asset_tiles
    universe_tiles: List[List[int]],
) -> cconfig.ConfigList:
    """
    Create a list of `Config`s based on `config` using different universe
    tiles.

    Note that the code is the same as
    `build_config_list_varying_asset_id()` but the interface is
    different.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    _LOG.debug("Universe has %d tiles: %s", len(universe_tiles), universe_tiles)
    configs = []
    config = config_list.get_only_config()
    for universe_tile in universe_tiles:
        config_tmp = config.copy()
        config_tmp = set_asset_id(config_tmp, universe_tile_id, universe_tile)
        _LOG.debug("config_tmp=%s\n", config_tmp)
        #
        configs.append(config_tmp)
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    _LOG.debug("config_list_out=\n%s", str(config_list_out))
    return config_list_out


# TODO(gp): -> ...varying_period_tiles
def build_config_list_varying_tiled_periods(
    config_list: cconfig.ConfigList,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    freq_as_pd_str: str,
    lookback_as_pd_str: str,
) -> cconfig.ConfigList:
    """
    Create a list of `Config`s based on `config` using a partition of the
    interval of time [`start_timestamp`, `end_timestamp`] using intervals like
    `[a, b]`

    :param start_timestamp, end_timestamp: the interval of time to partition
    :param freq_as_pd_str: the frequency of partitioning (e.g., `M`, `W`)
    :param lookback_as_pd_str: the extra period of time (e.g., `10D`) before the
        start of the interval, needed to warm up the period (e.g., compute
        features)
    """
    _LOG.debug(
        hprint.to_str(
            "start_timestamp end_timestamp freq_as_pd_str lookback_as_pd_str"
        )
    )
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    hdbg.dassert_eq(len(config_list), 1)
    hdateti.dassert_has_tz(start_timestamp)
    hdateti.dassert_has_tz(end_timestamp)
    hdbg.dassert_lte(start_timestamp, end_timestamp)
    # TODO(gp): Check that the lookback is > 0.
    lookback = pd.Timedelta(lookback_as_pd_str)
    #
    configs = []
    # We want to cover the interval [start_timestamp, end_timestamp] with
    # `freq_as_pd_str` intervals (e.g., monthly).
    # `pd.date_range()` samples with a given frequency (e.g., `M` for end of the
    # month) a closed interval like [a, b]. E.g.,
    # `pd.date_range("2020-01-01", "2020-02-01", "M")` returns ["2020-01-31"]
    # `pd.date_range("2020-01-01", "2020-01-31", "M")` returns ["2020-01-31"]
    # `pd.date_range("2020-01-01", "2020-01-30", "M")` returns ["2020-01-31"]
    # Thus we need to add an extra interval at the end.
    end_timestamp_tmp = end_timestamp
    end_timestamp_tmp -= pd.Timedelta("1D")
    offset = pd.tseries.frequencies.to_offset(freq_as_pd_str)
    end_timestamp_tmp += offset
    _LOG.debug(hprint.to_str("start_timestamp end_timestamp_tmp"))
    dates = pd.date_range(start_timestamp, end_timestamp_tmp, freq=freq_as_pd_str)
    dates = dates.to_list()
    hdbg.dassert_lte(1, len(dates))
    _LOG.debug(hprint.to_str("dates"))
    #
    config = config_list.get_only_config()
    for end_ts in dates:
        # For an end_ts of "2020-01-31", start_ts needs to be "2020-01-01".
        start_ts = (
            end_ts
            - pd.tseries.frequencies.to_offset(freq_as_pd_str)
            + pd.Timedelta("1D")
        )
        # Move end timestamp to the end of the day.
        # E.g., if a user passes `2022-05-31` it becomes `2022-05-31 00:00:00`
        # but should be `2022-05-31 23:59:00` to include all the data.
        end_ts = end_ts + pd.Timedelta(days=1, seconds=-1)
        _LOG.debug(hprint.to_str("start_ts end_ts"))
        #
        config_tmp = config.copy()
        config_tmp[("backtest_config", "start_timestamp_with_lookback")] = (
            start_ts - lookback
        )
        config_tmp[("backtest_config", "start_timestamp")] = start_ts
        config_tmp[("backtest_config", "end_timestamp")] = end_ts
        #
        _LOG.debug("config_tmp=%s\n", config_tmp)
        #
        configs.append(config_tmp)
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    return config_list_out


# #############################################################################


# TODO(gp): -> build_config_list_using_equal_asset_tiles
def build_config_list_with_tiled_universe(
    config_list: cconfig.ConfigList, asset_ids: List[int]
) -> cconfig.ConfigList:
    """
    Create a list of `Config`s using asset tiles of the same size.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    if len(asset_ids) > 300:
        # if len(asset_ids) > 1000:
        # Split the universe in 2 parts.
        # TODO(gp): We can generalize this.
        split_idx = int(len(asset_ids) / 2)
        asset_ids_part1 = asset_ids[:split_idx]
        asset_ids_part2 = asset_ids[split_idx:]
        #
        universe_tiles: List[List[int]] = [asset_ids_part1, asset_ids_part2]
    else:
        universe_tiles = [asset_ids]
    asset_id_key = ("market_data_config", "asset_ids")
    config_list_out = build_config_list_varying_universe_tiles(
        config_list, asset_id_key, universe_tiles
    )
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    return config_list_out


# TODO(gp): This is probably equivalent to some iterchain.reduce() standard function.
def apply_build_config_list(
    func: Callable, config_list: cconfig.ConfigList
) -> cconfig.ConfigList:
    """
    Apply a `build_config_list_*()` to each Config in `configs` and return the
    accumulated list of all the configs.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    configs = []
    _LOG.debug("configs_list=\n%s", str(config_list))
    for config in config_list.configs:
        config_list_tmp = config_list.copy()
        config_list_tmp.configs = [config]
        _LOG.debug("config_list_tmp=\n%s", config_list_tmp)
        #
        config_list_out_tmp = func(config_list_tmp)
        #
        _LOG.debug("config_list_out_tmp=\n%s", config_list_out_tmp)
        hdbg.dassert_isinstance(config_list_out_tmp, cconfig.ConfigList)
        #
        configs.extend(config_list_out_tmp.configs)
    #
    config_list_out = config_list.copy()
    config_list_out.configs = configs
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    return config_list_out


# TODO(gp): -> build_config_list_using_equal_asset_and_period_tiles
def build_config_list_with_tiled_universe_and_periods(
    config_list: cconfig.ConfigList,
) -> cconfig.ConfigList:
    """
    Create a list of `Config`s using asset and period tiles of the same size.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    #
    config = config_list.get_only_config()
    time_interval_str = config["backtest_config"]["time_interval_str"]
    asset_ids = config["market_data_config"]["asset_ids"]
    # Apply the cross-product by the universe tiles.
    func = lambda cfg: build_config_list_with_tiled_universe(cfg, asset_ids)
    config_list_out = config_list.copy()
    config_list_out.configs = [config]
    config_list_out = apply_build_config_list(func, config_list_out)
    _LOG.info(
        "After applying universe tiles: num_config_list=%s", len(config_list_out)
    )
    hdbg.dassert_lte(1, len(config_list_out))
    # Apply the cross-product by the time tiles.
    start_timestamp, end_timestamp = get_period(time_interval_str)
    freq_as_pd_str = config["backtest_config", "freq_as_pd_str"]
    # Amount of history fed to the DAG.
    lookback_as_pd_str = config["backtest_config", "lookback_as_pd_str"]
    func = lambda cfg: build_config_list_varying_tiled_periods(
        cfg, start_timestamp, end_timestamp, freq_as_pd_str, lookback_as_pd_str
    )
    config_list_out = apply_build_config_list(func, config_list_out)
    hdbg.dassert_lte(1, len(config_list_out))
    _LOG.info(
        "After applying time tiles: num_config_list=%s", len(config_list_out)
    )
    #
    hdbg.dassert_eq(type(config_list_out), type(config_list))
    return config_list_out
