# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# The notebook experiments with custom resampling on data from `HistoricalDataSource`.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Functions

# %%
# Copied from `oms/notebooks/CmTask4275_check_ohlcv_timing_issue.ipynb`.
def _get_prod_market_data(universe_version: str):
    # Get trading universe as asset ids.
    vendor = "CCXT"
    mode = "trade"
    as_full_symbol = True
    full_symbols = ivcu.get_vendor_universe(
        vendor,
        mode,
        version=universe_version,
        as_full_symbol=as_full_symbol,
    )
    # Load data just for 1 asset id for simplicity.
    asset_ids = [1467591036, 1464553467]
    # Get prod `MarketData`.
    db_stage = "prod"
    market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(
        asset_ids, db_stage
    )
    return market_data


def resample_ohlcv_bars(
    df_ohlcv: pd.DataFrame, bar_duration: str
) -> pd.DataFrame:
    """
    Resample 1-minute data to `bar_duration`.
    """
    # Resample.
    resampling_node = dtfcore.GroupedColDfToDfTransformer(
        "resample",
        transformer_func=cofinanc.resample_bars,
        **{
            "in_col_groups": [
                ("open",),
                ("close",),
                ("volume",),
            ],
            "out_col_group": (),
            "transformer_kwargs": {
                "rule": bar_duration,
                "resampling_groups": [
                    ({"close": "close"}, "last", {}),
                    ({"open": "open"}, "first", {}),
                    (
                        {"volume": "volume"},
                        "sum",
                        {"min_count": 1},
                    ),
                ],
                "vwap_groups": [],
            },
            "reindex_like_input": False,
            "join_output_with_input": False,
        },
    )
    resampled_ohlcv = resampling_node.fit(df_ohlcv)["df_out"]
    return resampled_ohlcv


# Copied from `oms/notebooks/CmTask4275_check_ohlcv_timing_issue.ipynb`.
def load_ohlcv_data_from_historical_datasource(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    universe_version: str,
    apply_timing_fix: bool,
) -> pd.DataFrame:
    """
    Load OHLCV data using the prod-like `HistoricalDataSource`.

    :param universe_version: universe version
    :param apply_timing_fix: apply the timing fix if True, otherwise read data as-is
    """
    nid = "read_data"
    market_data = _get_prod_market_data(universe_version)
    ts_col_name = "end_timestamp"
    multiindex_output = True
    col_names_to_remove = None
    historical_data_source = dtfsys.HistoricalDataSource(
        nid,
        market_data,
        ts_col_name,
        multiindex_output,
        col_names_to_remove=col_names_to_remove,
    )
    if apply_timing_fix:
        # Subtract 1 minute to account for the fact that timestamp indicates the start
        # of the bar instead of the end of that.
        start_timestamp = start_timestamp - pd.Timedelta(minutes=1)
        end_timestamp = end_timestamp - pd.Timedelta(minutes=1)
    # Convert to the `dataflow` format.
    fit_intervals = [(start_timestamp, end_timestamp)]
    _LOG.info("fit_intervals=%s", fit_intervals)
    historical_data_source.set_fit_intervals(fit_intervals)
    df_ohlcv = historical_data_source.fit()["df_out"]
    if apply_timing_fix:
        # Add 1 minute back.
        df_ohlcv.index = df_ohlcv.index + pd.Timedelta(minutes=1)
        df_ohlcv["start_timestamp"] = df_ohlcv["start_timestamp"] + pd.Timedelta(
            minutes=1
        )
    return df_ohlcv


# %% [markdown]
# # Load OHLCV data via `HistoricalDataSource`

# %% run_control={"marked": false}
system_log_dir = "/shared_data/ecs/preprod/twap_experiment/system_reconciliation/C3a/20230419/system_log_dir.scheduled.20230419_041000.20230419_100500"
bar_duration = "5T"
universe_version = "v7.1"
#
start_timestamp_UTC = pd.Timestamp("2023-04-19 04:06:00", tz="UTC")
end_timestamp_UTC = pd.Timestamp("2023-04-19 08:05:00", tz="UTC")
start_timestamp_ET = start_timestamp_UTC.tz_convert("America/New_York")
end_timestamp_ET = end_timestamp_UTC.tz_convert("America/New_York")

# %%
apply_timing_fix = True
data = load_ohlcv_data_from_historical_datasource(
    start_timestamp_ET, end_timestamp_ET, universe_version, apply_timing_fix
)
data.head(10)

# %% [markdown]
# # Apply weighted resampling

# %%
rule = "5T"
weights = [0.1, 0.2, 0.3, 0.4, 0.5]

# %% [markdown]
# ## 1 column data

# %%
price_data = data["close"]
price_data.index.freq = pd.infer_freq(price_data.index)
price_data.head(10)

# %%
col = 1464553467
resampled_price_data = cofinanc.resample_with_weights(
    price_data, rule, col, weights
)
resampled_price_data.head()


# %% [markdown]
# ## `dataflow` data format

# %%
def resample_with_weights_ohlcv_bars(
    df_ohlcv: pd.DataFrame, bar_duration: str, weights: List[float]
) -> pd.DataFrame:
    """
    Resample 1-minute data to `bar_duration` with weights.
    """
    # Resample.
    resampling_node = dtfcore.GroupedColDfToDfTransformer(
        "resample",
        transformer_func=cofinanc.resample_with_weights,
        **{
            "in_col_groups": [
                ("close",),
            ],
            "out_col_group": (),
            "transformer_kwargs": {
                "rule": bar_duration,
                "col": "close",
                "weights": weights,
            },
            "reindex_like_input": False,
            "join_output_with_input": False,
        },
    )
    resampled_ohlcv = resampling_node.fit(df_ohlcv)["df_out"]
    return resampled_ohlcv


# %%
resampled_with_weights_data = resample_with_weights_ohlcv_bars(
    data, rule, weights
)
resampled_with_weights_data.head()

# %%
