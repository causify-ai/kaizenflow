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
# The notebooks performs comparison between bid-ask data loaded from `"v1_0_0"`and `"v2_0_0"` data versions.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import market_data.market_data_example as mdmadaex

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
universe_version = "v8"
wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
config = {
    "universe": {
        "vendor": "CCXT",
        "mode": "trade",
        "version": universe_version,
        "as_full_symbol": True,
    },
    "US_equities_tz": "America/New_York",
    "bid_ask_data": {
        "start_timestamp": pd.Timestamp("2024-01-31T00:00:00+00:00"),
        "end_timestamp": pd.Timestamp("2024-02-19T00:00:00+00:00"),
        "column_names": {
            "timestamp": "timestamp",
        },
        "im_client_config_v1": {
            "universe_version": "v8",
            "root_dir": "s3://cryptokaizen-data-test/v3",
            "partition_mode": "by_year_month",
            "dataset": "bid_ask",
            "contract_type": "futures",
            "data_snapshot": "",
            "version": "v1_0_0",
            "download_universe_version": "v8",
            "tag": "resampled_1min",
            "aws_profile": "ck",
        },
        "market_data_config_v1": {
            "columns": [
                "level_1.bid_price.open",
                "level_1.bid_price.high",
                "level_1.bid_price.low",
                "level_1.bid_price.close",
                "level_1.bid_price.mean",
                "level_1.bid_size.open",
                "level_1.bid_size.max",
                "level_1.bid_size.min",
                "level_1.bid_size.close",
                "level_1.bid_size.mean",
                "level_1.ask_price.open",
                "level_1.ask_price.high",
                "level_1.ask_price.low",
                "level_1.ask_price.close",
                "level_1.ask_price.mean",
                "level_1.ask_size.open",
                "level_1.ask_size.max",
                "level_1.ask_size.min",
                "level_1.ask_size.close",
                "level_1.ask_size.mean",
                "asset_id",
                "full_symbol",
                "start_ts",
                "knowledge_timestamp",
            ],
            "column_remap": None,
            "wall_clock_time": wall_clock_time,
            "filter_data_mode": "assert",
        },
        "im_client_config_v2": {
            "universe_version": "v8",
            "root_dir": "s3://cryptokaizen-data-test/v3",
            "partition_mode": "by_year_month",
            "dataset": "bid_ask",
            "contract_type": "futures",
            "data_snapshot": "",
            "version": "v2_0_0",
            "download_universe_version": "v8",
            "tag": "resampled_1min",
            "aws_profile": "ck",
        },
        "market_data_config_v2": {
            "columns": cofinanc.get_bid_ask_columns_by_level(1)
            + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
            "column_remap": None,
            "wall_clock_time": wall_clock_time,
            "filter_data_mode": "assert",
        },
        "column_names": {
            "timestamp": "timestamp",
            "full_symbol": "full_symbol",
            "close": "close",
            "volume": "volume",
            "volume_notional": "volume_notional",
            "ask_price": "level_1.ask_price.close",
            "bid_price": "level_1.bid_price.close",
            "bid_ask_midpoint": "level_1.bid_ask_midpoint.close",
            "half_spread": "level_1.half_spread.close",
        },
        "rolling_window": 30,
    },
    "liquidity_metrics": {
        "timestamp": "timestamp",
        "full_symbol": "full_symbol",
        "close": "close",
        "volume": "volume",
        "volume_notional": "volume_notional",
        "ask_price": "level_1.ask_price.close",
        "bid_price": "level_1.bid_price.close",
        "half_spread_bps_mean": "half_spread_bps_mean",
        "ask_vol_bps_mean": "ask_vol_bps_mean",
        "bid_vol_bps_mean": "bid_vol_bps_mean",
        "bid_vol_to_half_spread_mean": "bid_vol_to_half_spread_mean",
        "bid_vol_to_half_spread_bucket": "bid_vol_to_half_spread_bucket",
        "half_spread_bucket": "half_spread_bucket",
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Universe

# %%
# Get full symbol universe.
full_symbols = ivcu.get_vendor_universe(**config["universe"])
_LOG.info("The number of coins in the universe=%s", len(full_symbols))
full_symbols

# %%
# Get asset ids.
asset_ids = [
    ivcu.string_to_numerical_id(full_symbol) for full_symbol in full_symbols
]
asset_ids

# %% [markdown]
# # Bid / ask price changes

# %% [markdown]
# ## `"v1_0_0"`

# %%
bid_ask_im_client_v1 = icdcl.ccxt_clients.CcxtHistoricalPqByTileClient(
    **config["bid_ask_data"]["im_client_config_v1"]
)

# %%
bid_ask_market_data_v1 = mdmadaex.get_HistoricalImClientMarketData_example1(
    bid_ask_im_client_v1,
    asset_ids,
    **config["bid_ask_data"]["market_data_config_v1"],
)

# %%
bid_ask_data_v1 = bid_ask_market_data_v1.get_data_for_interval(
    config["bid_ask_data"]["start_timestamp"],
    config["bid_ask_data"]["end_timestamp"],
    config["bid_ask_data"]["column_names"]["timestamp"],
    asset_ids,
)
# Convert to ET to be able to compare with US equities active trading hours.
bid_ask_data_v1.index = bid_ask_data_v1.index.tz_convert(config["US_equities_tz"])
hpandas.df_to_str(bid_ask_data_v1, num_rows=5, log_level=logging.INFO)

# %%
# Set input parameters.
rolling_window = config["bid_ask_data"]["rolling_window"]
full_symbol_col = config["bid_ask_data"]["column_names"]["full_symbol"]
ask_price_col = config["bid_ask_data"]["column_names"]["ask_price"]
bid_price_col = config["bid_ask_data"]["column_names"]["bid_price"]
# Get ask and bid prices for all instruments.
ask_price_df_v1 = bid_ask_data_v1.pivot(
    columns=full_symbol_col, values=ask_price_col
)
bid_price_df_v1 = bid_ask_data_v1.pivot(
    columns=full_symbol_col, values=bid_price_col
)

# %%
bid_ask_midpoint_df_v1 = 0.5 * (ask_price_df_v1 + bid_price_df_v1)
half_spread_df_v1 = (
    0.5 * (ask_price_df_v1 - bid_price_df_v1) / bid_ask_midpoint_df_v1
)
half_spread_bps_df_v1 = 1e4 * half_spread_df_v1
hpandas.df_to_str(half_spread_bps_df_v1, log_level=logging.INFO)

# %%
half_spread_bps_mean_v1 = half_spread_bps_df_v1.mean().sort_values()
half_spread_bps_mean_v1.name = config["liquidity_metrics"]["half_spread_bps_mean"]

# %%
bid_vol_df_v1 = bid_price_df_v1.ffill().pct_change().rolling(rolling_window).std()
bid_vol_bps_df_v1 = 1e4 * bid_vol_df_v1

# %%
bid_vol_to_half_spread_v1 = bid_vol_bps_df_v1.divide(half_spread_bps_df_v1)
hpandas.df_to_str(bid_vol_to_half_spread_v1, log_level=logging.INFO)

# %%
bid_vol_to_half_spread_mean_v1 = bid_vol_to_half_spread_v1.mean().sort_values(
    ascending=False
)
bid_vol_to_half_spread_mean_v1.name = config["liquidity_metrics"][
    "bid_vol_to_half_spread_mean"
]

# %%
# Get the vol metric values and put them in a DataFrame.
bid_vol_to_half_spread_mean_df_v1 = bid_vol_to_half_spread_mean_v1.sort_values(
    ascending=False
).to_frame()
# Set buckets' cutpoints and labels.
cutpoints = [-float("inf"), 1, 5, 10, 25, 250, float("inf")]
labels = [
    "(-inf, 1]",
    "(1, 5]",
    "(5, 10]",
    "(10, 25]",
    "(25, 250]",
    "(250, inf)",
]
# Assign buckets to full symbols.
bid_vol_to_half_spread_bucket_v1 = pd.cut(
    bid_vol_to_half_spread_mean_df_v1[
        config["liquidity_metrics"]["bid_vol_to_half_spread_mean"]
    ],
    bins=cutpoints,
    labels=labels,
)
bid_vol_to_half_spread_bucket_v1.name = config["liquidity_metrics"][
    "bid_vol_to_half_spread_bucket"
]
bid_vol_to_half_spread_mean_df_v1 = pd.concat(
    [bid_vol_to_half_spread_mean_df_v1, bid_vol_to_half_spread_bucket_v1], axis=1
)
hpandas.df_to_str(bid_vol_to_half_spread_mean_df_v1, log_level=logging.INFO)

# %%
# Get the vol metric values and put them in a DataFrame.
half_spread_bps_mean_df_v1 = half_spread_bps_mean_v1.sort_values().to_frame()
# Set buckets' cutpoints and labels.
cutpoints = [-float("inf"), 0.05, 0.5, 1.0, 2.0, 10.0, float("inf")]
labels = [
    "(-inf, 0.05]",
    "(0.05, 0.5]",
    "(0.5, 1.0]",
    "(1.0, 2.0]",
    "(2.0, 10.0]",
    "(10.0, inf)",
]
# Assign buckets to full symbols.
half_spread_bucket_v1 = pd.cut(
    half_spread_bps_mean_df_v1[
        config["liquidity_metrics"]["half_spread_bps_mean"]
    ],
    bins=cutpoints,
    labels=labels,
)
half_spread_bucket_v1.name = config["liquidity_metrics"]["half_spread_bucket"]
half_spread_bps_mean_df_v1 = pd.concat(
    [half_spread_bps_mean_df_v1, half_spread_bucket_v1], axis=1
)
hpandas.df_to_str(half_spread_bps_mean_df_v1, log_level=logging.INFO)

# %%
liquidity_metrics_df_v1 = pd.concat(
    [
        half_spread_bps_mean_v1,
        bid_vol_to_half_spread_mean_v1,
    ],
    axis=1,
)
liquidity_metrics_df_v1

# %%
# Combine liquidity metrics and buckets in a single DataFrame.
combined_liquidity_metrics_df_v1 = pd.concat(
    [
        liquidity_metrics_df_v1,
        half_spread_bucket_v1,
        bid_vol_to_half_spread_bucket_v1,
    ],
    axis=1,
)
# Get universe.
v8_1_metrics_df_v1 = combined_liquidity_metrics_df_v1[
    (
        combined_liquidity_metrics_df_v1[
            config["liquidity_metrics"]["half_spread_bucket"]
        ]
        == "(0.05, 0.5]"
    )
    & (
        combined_liquidity_metrics_df_v1[
            config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
        ]
        == "(25, 250]"
    )
]
v8_1_universe_v1 = sorted(list(v8_1_metrics_df_v1.index))
print(v8_1_universe_v1)

# %%
v8_2_metrics_df_v1 = combined_liquidity_metrics_df_v1[
    (
        combined_liquidity_metrics_df_v1[
            config["liquidity_metrics"]["half_spread_bucket"]
        ].isin(["(0.05, 0.5]", "(0.5, 1.0]"])
    )
    & (
        combined_liquidity_metrics_df_v1[
            config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
        ].isin(["(25, 250]", "(10, 25]"])
    )
    & (~combined_liquidity_metrics_df_v1.index.isin(v8_1_universe_v1))
]
v8_2_universe_v1 = sorted(list(v8_2_metrics_df_v1.index))
print(v8_2_universe_v1)

# %% [markdown]
# ## `"v2_0_0"`

# %%
bid_ask_im_client_v2 = icdcl.ccxt_clients.CcxtHistoricalPqByTileClient(
    **config["bid_ask_data"]["im_client_config_v2"]
)

# %%
bid_ask_market_data_v2 = mdmadaex.get_HistoricalImClientMarketData_example1(
    bid_ask_im_client_v2,
    asset_ids,
    **config["bid_ask_data"]["market_data_config_v2"],
)

# %%
bid_ask_data_v2 = bid_ask_market_data_v2.get_data_for_interval(
    config["bid_ask_data"]["start_timestamp"],
    config["bid_ask_data"]["end_timestamp"],
    config["bid_ask_data"]["column_names"]["timestamp"],
    asset_ids,
)
# Convert to ET to be able to compare with US equities active trading hours.
bid_ask_data_v2.index = bid_ask_data_v2.index.tz_convert(config["US_equities_tz"])
hpandas.df_to_str(bid_ask_data_v2, num_rows=5, log_level=logging.INFO)

# %%
ask_price_df_v2 = bid_ask_data_v2.pivot(
    columns=full_symbol_col, values=ask_price_col
)
bid_price_df_v2 = bid_ask_data_v2.pivot(
    columns=full_symbol_col, values=bid_price_col
)

# %%
bid_ask_midpoint_col = config["bid_ask_data"]["column_names"]["bid_ask_midpoint"]
bid_ask_midpoint_df_v2 = bid_ask_data_v2.pivot(
    columns=full_symbol_col, values=bid_ask_midpoint_col
)
hpandas.df_to_str(bid_ask_midpoint_df_v2, log_level=logging.INFO)

# %%
half_spread_col = config["bid_ask_data"]["column_names"]["half_spread"]
half_spread_df_v2 = bid_ask_data_v2.pivot(
    columns=full_symbol_col, values=half_spread_col
)
half_spread_bps_df_v2 = 1e4 * half_spread_df_v2 / bid_ask_midpoint_df_v2
hpandas.df_to_str(half_spread_bps_df_v2, log_level=logging.INFO)

# %%
half_spread_bps_mean_v2 = half_spread_bps_df_v2.mean().sort_values()
half_spread_bps_mean_v2.name = config["liquidity_metrics"]["half_spread_bps_mean"]

# %%
ask_vol_df_v2 = ask_price_df_v2.ffill().pct_change().rolling(rolling_window).std()
ask_vol_bps_df_v2 = 1e4 * ask_vol_df_v2
hpandas.df_to_str(ask_vol_bps_df_v2, log_level=logging.INFO)

# %%
bid_vol_df_v2 = bid_price_df_v2.ffill().pct_change().rolling(rolling_window).std()
bid_vol_bps_df_v2 = 1e4 * bid_vol_df_v2
hpandas.df_to_str(bid_vol_bps_df_v2, log_level=logging.INFO)

# %%
bid_vol_bps_mean_v2 = bid_vol_bps_df_v2.mean().sort_values()
bid_vol_bps_mean_v2.name = config["liquidity_metrics"]["bid_vol_bps_mean"]

# %%
bid_vol_to_half_spread_v2 = bid_vol_bps_df_v2.divide(half_spread_bps_df_v2)
hpandas.df_to_str(bid_vol_to_half_spread_v2, log_level=logging.INFO)

# %%
bid_vol_to_half_spread_mean_v2 = bid_vol_to_half_spread_v2.mean().sort_values(
    ascending=False
)
bid_vol_to_half_spread_mean_v2.name = config["liquidity_metrics"][
    "bid_vol_to_half_spread_mean"
]

# %%
liquidity_metrics_df_v2 = pd.concat(
    [
        half_spread_bps_mean_v2,
        bid_vol_to_half_spread_mean_v2,
    ],
    axis=1,
)
liquidity_metrics_df_v2

# %%
# Get the vol metric values and put them in a DataFrame.
bid_vol_to_half_spread_mean_df_v2 = bid_vol_to_half_spread_mean_v2.sort_values(
    ascending=False
).to_frame()
# Set buckets' cutpoints and labels.
cutpoints = [-float("inf"), 1, 5, 10, 25, 250, float("inf")]
labels = [
    "(-inf, 1]",
    "(1, 5]",
    "(5, 10]",
    "(10, 25]",
    "(25, 250]",
    "(250, inf)",
]
# Assign buckets to full symbols.
bid_vol_to_half_spread_bucket_v2 = pd.cut(
    bid_vol_to_half_spread_mean_df_v2[
        config["liquidity_metrics"]["bid_vol_to_half_spread_mean"]
    ],
    bins=cutpoints,
    labels=labels,
)
bid_vol_to_half_spread_bucket_v2.name = config["liquidity_metrics"][
    "bid_vol_to_half_spread_bucket"
]
bid_vol_to_half_spread_mean_df_v2 = pd.concat(
    [bid_vol_to_half_spread_mean_df_v2, bid_vol_to_half_spread_bucket_v2], axis=1
)
hpandas.df_to_str(bid_vol_to_half_spread_mean_df_v2, log_level=logging.INFO)

# %%
# Get the vol metric values and put them in a DataFrame.
half_spread_bps_mean_df_v2 = half_spread_bps_mean_v2.sort_values().to_frame()
# Set buckets' cutpoints and labels.
cutpoints = [-float("inf"), 0.05, 0.5, 1.0, 2.0, 10.0, float("inf")]
labels = [
    "(-inf, 0.05]",
    "(0.05, 0.5]",
    "(0.5, 1.0]",
    "(1.0, 2.0]",
    "(2.0, 10.0]",
    "(10.0, inf)",
]
# Assign buckets to full symbols.
half_spread_bucket_v2 = pd.cut(
    half_spread_bps_mean_df_v2[
        config["liquidity_metrics"]["half_spread_bps_mean"]
    ],
    bins=cutpoints,
    labels=labels,
)
half_spread_bucket_v2.name = config["liquidity_metrics"]["half_spread_bucket"]
half_spread_bps_mean_df_v2 = pd.concat(
    [half_spread_bps_mean_df_v2, half_spread_bucket_v2], axis=1
)
hpandas.df_to_str(half_spread_bps_mean_df_v2, log_level=logging.INFO)

# %%
# Combine liquidity metrics and buckets in a single DataFrame.
combined_liquidity_metrics_df_v2 = pd.concat(
    [
        liquidity_metrics_df_v2,
        half_spread_bucket_v2,
        bid_vol_to_half_spread_bucket_v2,
    ],
    axis=1,
)
# Get universe.
v8_1_metrics_df_v2 = combined_liquidity_metrics_df_v2[
    (
        combined_liquidity_metrics_df_v2[
            config["liquidity_metrics"]["half_spread_bucket"]
        ]
        == "(0.05, 0.5]"
    )
    & (
        combined_liquidity_metrics_df_v2[
            config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
        ]
        == "(25, 250]"
    )
]
v8_1_universe_v2 = sorted(list(v8_1_metrics_df_v2.index))
print(v8_1_universe_v2)

# %%
v8_2_metrics_df_v2 = combined_liquidity_metrics_df_v2[
    (
        combined_liquidity_metrics_df_v2[
            config["liquidity_metrics"]["half_spread_bucket"]
        ].isin(["(0.05, 0.5]", "(0.5, 1.0]"])
    )
    & (
        combined_liquidity_metrics_df_v2[
            config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
        ].isin(["(25, 250]", "(10, 25]"])
    )
    & (~combined_liquidity_metrics_df_v2.index.isin(v8_1_universe_v2))
]
v8_2_universe_v2 = sorted(list(v8_2_metrics_df_v2.index))
print(v8_2_universe_v2)

# %% [markdown]
# ## Compare universes

# %%
# v8_1 universes are equal for both data versions.
v8_1_universe_v1 == v8_1_universe_v2

# %%
set(v8_2_universe_v1) - set(v8_2_universe_v2)

# %%
# The only differing full symbol in v8_2 is DUSK_USDT.
set(v8_2_universe_v2) - set(v8_2_universe_v1)

# %%
# DUSK_USDT `bid_vol_to_half_spread_mean` values seems to be a data artifact.
combined_liquidity_metrics_df_v1.loc["binance::DUSK_USDT"]

# %%
bid_vol_to_half_spread_v1["binance::DUSK_USDT"].dropna().sort_values().tail()

# %%
# The reason is that half spread for DUSK is 0 at 1 bar.
half_spread_bps_df_v1["binance::DUSK_USDT"][
    pd.Timestamp("2024-02-14 10:05:00-05:00")
]

# %%
# In v2_0_0 the coin does not have such a problem.
combined_liquidity_metrics_df_v2.loc["binance::DUSK_USDT"]

# %%
# v2_0_0 has data for DUSK_USDT.
bid_vol_to_half_spread_v2["binance::DUSK_USDT"][
    pd.Timestamp("2024-02-14 10:05:00-05:00")
]

# %%
half_spread_bps_df_v2["binance::DUSK_USDT"][
    pd.Timestamp("2024-02-14 10:05:00-05:00")
]

# %%
# Single bar artifact.
(
    half_spread_bps_df_v1["binance::DUSK_USDT"]
    - half_spread_bps_df_v2["binance::DUSK_USDT"]
).abs().sort_values(ascending=False)

# %%
(
    half_spread_bps_df_v1["binance::DUSK_USDT"]
    - half_spread_bps_df_v2["binance::DUSK_USDT"]
).abs().plot()

# %%
