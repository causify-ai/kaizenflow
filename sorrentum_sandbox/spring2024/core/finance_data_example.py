"""
Import as:

import core.finance_data_example as cfidaexa
"""
import collections
import datetime
import logging
from typing import List

import pandas as pd

import core.artificial_signal_generators as carsigen
import core.signal_processing as csigproc
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def get_forecast_dataframe(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    num_features: int = 0,
    bar_duration: str = "5T",
    bar_volatility_in_bps: int = 10,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a multiindexed dataframe of returns, vol, predictions per asset.

    Timestamps are to be regarded as knowledge times. The `prediction` and
    `volatility` columns are to be interpreted as forecasts for two bars
    ahead.

    Example output (with `num_features=0`):
                                 prediction           returns          volatility
                               100      200      100      200        100      200
    2022-01-03 09:35:00   -0.00025 -0.00034 -0.00110  0.00048    0.00110  0.00048
    2022-01-03 09:40:00    0.00013 -0.00005 -0.00073 -0.00045    0.00091  0.00046
    2022-01-03 09:45:00    0.00084 -0.00097 -0.00078 -0.00075    0.00086  0.00060
    2022-01-03 09:50:00    0.00086 -0.00113  0.00027 -0.00081    0.00071  0.00068

    Note that changes to any inputs may change the random output on any
    overlapping data.
    """
    hdbg.dassert_lte(0, num_features)
    price_process = carsigen.PriceProcess(seed=seed)
    dfs = {}
    for asset_id in asset_ids:
        rets = price_process.generate_log_normal_series(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        )
        vol = csigproc.compute_rolling_norm(rets, tau=4)
        noise = price_process.generate_log_normal_series(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        )
        dict_ = {
            "returns": rets,
            "volatility": vol,
            "prediction": noise,
        }
        if num_features > 0:
            for idx in range(1, num_features + 1):
                feature = price_process.generate_log_normal_series(
                    start_datetime,
                    end_datetime,
                    asset_id,
                    bar_duration=bar_duration,
                    bar_volatility_in_bps=bar_volatility_in_bps,
                    start_time=start_time,
                    end_time=end_time,
                )
                dict_[idx] = feature
        df = pd.DataFrame(dict_)
        dfs[asset_id] = df
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    # Swap column levels so that symbols are leaves.
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    return df


def get_forecast_price_based_dataframe(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    num_features: int = 0,
    bar_duration: str = "5T",
    bar_volatility_in_bps: int = 10,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a multiindexed dataframe of returns, vol, predictions per asset.

    Timestamps are to be regarded as knowledge times. The `prediction` and
    `volatility` columns are to be interpreted as forecasts for two bars
    ahead.

    Example output (with `num_features=0`):
                                 prediction             price          volatility
                               100      200      100      200        100      200
    2022-01-03 09:35:00   -0.00025 -0.00034 -0.00110  0.00048    0.00110  0.00048
    2022-01-03 09:40:00    0.00013 -0.00005 -0.00073 -0.00045    0.00091  0.00046
    2022-01-03 09:45:00    0.00084 -0.00097 -0.00078 -0.00075    0.00086  0.00060
    2022-01-03 09:50:00    0.00086 -0.00113  0.00027 -0.00081    0.00071  0.00068

    Note that changes to any inputs may change the random output on any
    overlapping data.
    """
    hdbg.dassert_lte(0, num_features)
    price_process = carsigen.PriceProcess(seed=seed)
    dfs = {}
    for asset_id in asset_ids:
        price = price_process.generate_price_series_from_normal_log_returns(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        )
        vol = csigproc.compute_rolling_norm(price.pct_change(), tau=4)
        noise = price_process.generate_log_normal_series(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        )
        dict_ = {
            "price": price,
            "volatility": vol,
            "prediction": noise,
        }
        if num_features > 0:
            for idx in range(1, num_features + 1):
                feature = price_process.generate_log_normal_series(
                    start_datetime,
                    end_datetime,
                    asset_id,
                    bar_duration=bar_duration,
                    bar_volatility_in_bps=bar_volatility_in_bps,
                    start_time=start_time,
                    end_time=end_time,
                )
                dict_[idx] = feature
        df = pd.DataFrame(dict_)
        dfs[asset_id] = df
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    # Swap column levels so that symbols are leaves.
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    return df


def get_portfolio_bar_metrics_dataframe(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    *,
    bar_duration: str = "5T",
    mean_gmv: float = 1e6,
    mean_turnover_percentage: float = 5,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a dataframe of synthetic per-bar portfolio metrics.

    Timestamps are to be regarded as knowledge times.

    Example output:

                                  pnl  gross_volume  net_volume        gmv     nmv
    2022-01-03 09:30:00-05:00  125.44         49863      -31.10  1000000.0     NaN
    2022-01-03 09:40:00-05:00  174.18        100215       24.68  1000000.0   12.47
    2022-01-03 09:50:00-05:00  -21.52        100041      -90.39  1000000.0  -55.06
    2022-01-03 10:00:00-05:00  -16.82         50202       99.19  1000000.0  167.08
    """
    price_process = carsigen.PriceProcess(seed=seed)
    asset_id = 0
    #
    bar_volatility_in_bps = 1
    pnl = price_process.generate_log_normal_series(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_volatility_in_bps=bar_volatility_in_bps,
        start_time=start_time,
        end_time=end_time,
    )
    pnl = mean_gmv * pnl
    #
    turnover = mean_turnover_percentage * 1e-2 * mean_gmv
    gross_volume = price_process.generate_volume_series_from_poisson_process(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_expected_count=turnover,
        start_time=start_time,
        end_time=end_time,
    )
    #
    net_volume = price_process.generate_log_normal_series(
        start_datetime,
        end_datetime,
        asset_id,
        bar_duration=bar_duration,
        bar_volatility_in_bps=bar_volatility_in_bps,
        start_time=start_time,
        end_time=end_time,
    )
    net_volume = mean_gmv * net_volume
    #
    nmv = net_volume.diff().shift(1)
    dict_ = {
        "pnl": pnl,
        "gross_volume": gross_volume,
        "net_volume": net_volume,
        "gmv": mean_gmv,
        "nmv": nmv,
    }
    df = pd.DataFrame(dict_)
    return df


def get_target_position_generation_dataframe(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    num_features: int = 0,
    bar_duration: str = "5T",
    bar_volatility_in_bps: int = 10,
    start_time: datetime.time = datetime.time(9, 31),
    end_time: datetime.time = datetime.time(16, 00),
    vol_to_spread_ratio: float = 5.0,
    seed: int = 10,
) -> pd.DataFrame:
    """
    Return a multiindexed dataframe of predictions, vol, spread per asset.

    Timestamps are to be regarded as knowledge times. All columns are to be
    interpreted as forecasts for two bars ahead.

    Example output (with `num_features=0`):

    Note that changes to any inputs may change the random output on any
    overlapping data.
    """
    hdbg.dassert_lte(0, num_features)
    price_process = carsigen.PriceProcess(seed=seed)
    dfs = {}
    for asset_id in asset_ids:
        prediction = price_process.generate_log_normal_series(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        )
        volatility = price_process.generate_log_normal_series(
            start_datetime,
            end_datetime,
            asset_id,
            bar_duration=bar_duration,
            bar_volatility_in_bps=bar_volatility_in_bps,
            start_time=start_time,
            end_time=end_time,
        ).abs()
        spread = (
            price_process.generate_log_normal_series(
                start_datetime,
                end_datetime,
                asset_id,
                bar_duration=bar_duration,
                bar_volatility_in_bps=bar_volatility_in_bps,
                start_time=start_time,
                end_time=end_time,
            ).abs()
            / vol_to_spread_ratio
        )
        dict_ = collections.OrderedDict()
        dict_["prediction"] = prediction
        dict_["volatility"] = volatility
        dict_["spread"] = spread
        if num_features > 0:
            for idx in range(1, num_features + 1):
                feature = price_process.generate_log_normal_series(
                    start_datetime,
                    end_datetime,
                    asset_id,
                    bar_duration=bar_duration,
                    bar_volatility_in_bps=bar_volatility_in_bps,
                    start_time=start_time,
                    end_time=end_time,
                )
                dict_[idx] = feature
        df = pd.DataFrame(dict_)
        dfs[asset_id] = df
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    # Swap column levels so that symbols are leaves.
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    return df
