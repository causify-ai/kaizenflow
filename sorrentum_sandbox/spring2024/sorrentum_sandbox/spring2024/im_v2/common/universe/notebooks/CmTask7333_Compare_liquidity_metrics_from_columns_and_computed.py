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
# The notebooks performs comparison between liquidity metrics taken from columns and computed directly on `"v2_0_0"` version of bid-ask data.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import numpy as np
import pandas as pd
import scipy

import core.config as cconfig
import core.finance as cofinanc
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
import im_v2.common.universe as ivcu
import market_data as mdata
import market_data.market_data_example as mdmadaex

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
config = cconfig.get_config_from_env()
if config:
    # Get config from env when running the notebook via the `run_notebook.py`
    # script, e.g., in the system reconciliation flow.
    _LOG.info("Using config from env vars")
else:
    universe_version = "v8"
    wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
    config = {
        "universe": {
            "vendor": "CCXT",
            "mode": "trade",
            "version": universe_version,
            "as_full_symbol": True,
        },
        "ohlcv_data": {
            "start_timestamp": pd.Timestamp("2024-01-01T00:00:00+00:00"),
            "end_timestamp": pd.Timestamp("2024-02-29T23:59:00+00:00"),
            "im_client_config": {
                "vendor": "ccxt",
                "universe_version": universe_version,
                "root_dir": "s3://cryptokaizen-unit-test/v3",
                "resample_1min": False,
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "futures",
                "data_snapshot": "",
                "aws_profile": "ck",
                "version": "v1_0_0",
                "download_universe_version": "v8",
                "tag": "downloaded_1min",
                "download_mode": "periodic_daily",
                "downloading_entity": "airflow",
            },
            "market_data_config": {
                "columns": None,
                "column_remap": None,
                "wall_clock_time": wall_clock_time,
            },
            "column_names": {
                "close": "close",
                "volume": "volume",
            },
        },
        "bid_ask_data": {
            "start_timestamp": pd.Timestamp("2024-01-23T00:00:00+00:00"),
            "end_timestamp": pd.Timestamp("2024-02-19T00:00:00+00:00"),
            "im_client_config": {
                "universe_version": "v8",
                "root_dir": "s3://cryptokaizen-unit-test/v3",
                "partition_mode": "by_year_month",
                "dataset": "bid_ask",
                "contract_type": "futures",
                "data_snapshot": "",
                "version": "v2_0_0",
                "download_universe_version": "v8",
                "tag": "resampled_1min",
                "aws_profile": "ck",
            },
            "market_data_config": {
                "columns": cofinanc.get_bid_ask_columns_by_level(1)
                + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
                "column_remap": None,
                "wall_clock_time": wall_clock_time,
                "filter_data_mode": "assert",
            },
            "rolling_window": 30,
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
        },
        "liquidity_metrics": {
            "half_spread_bps_mean": "half_spread_bps_mean",
            "ask_vol_bps_mean": "ask_vol_bps_mean",
            "bid_vol_bps_mean": "bid_vol_bps_mean",
            "bid_vol_to_half_spread_mean": "bid_vol_to_half_spread_mean",
            "bid_vol_to_half_spread_bucket": "bid_vol_to_half_spread_bucket",
            "half_spread_bucket": "half_spread_bucket",
        },
        "US_equities_tz": "America/New_York",
        "plot_kwargs": {
            "kind": "barh",
            "logx": True,
            "figsize": (20, 100),
        },
        "partition_universe": True,
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

# %%
# Get asset id to full symbol mapping.
asset_id_to_full_symbol_mapping = ivcu.build_numerical_to_string_id_mapping(
    full_symbols
)
asset_id_to_full_symbol_mapping

# %% [markdown]
# # Mean daily notional volume

# %%
im_client = imvcdchpcl.HistoricalPqByCurrencyPairTileClient(
    **config["ohlcv_data"]["im_client_config"]
)
market_data = mdata.get_HistoricalImClientMarketData_example1(
    im_client,
    asset_ids,
    **config["ohlcv_data"]["market_data_config"],
)

# %%
# Load OHLCV data.
ohlcv_data = dtfamsysc.load_market_data(
    market_data,
    config["ohlcv_data"]["start_timestamp"],
    config["ohlcv_data"]["end_timestamp"],
)
hpandas.df_to_str(ohlcv_data, num_rows=5, log_level=logging.INFO)

# %%
# Compute notional volume.
volume_notional = (
    ohlcv_data[config["ohlcv_data"]["column_names"]["volume"]]
    * ohlcv_data[config["ohlcv_data"]["column_names"]["close"]]
)
hpandas.df_to_str(volume_notional, log_level=logging.INFO)

# %%
# Compute mean daily notional volume.
mdv_notional = volume_notional.resample("D").sum().mean().rename("mdv_notional")
mdv_notional = mdv_notional.sort_values(ascending=False).round(2)
# Replace asset ids with full symbols.
mdv_notional.index = [
    asset_id_to_full_symbol_mapping[idx] for idx in mdv_notional.index
]
# Full symbols with 0 MDV also have 0 volume and constant price in the observed time period.
hpandas.df_to_str(mdv_notional, log_level=logging.INFO)

# %%
title = "MDV"
ylabel = "notional"
mdv_notional.plot(
    title=title,
    ylabel=ylabel,
    **config["plot_kwargs"],
)

# %%
# Convert to ET to be able to compare with US equities active trading hours.
ohlcv_volume = ohlcv_data[
    config["ohlcv_data"]["column_names"]["volume"]
].tz_convert(config["US_equities_tz"])
ohlcv_volume = ohlcv_volume.rename(
    columns={
        col: asset_id_to_full_symbol_mapping[col] for col in ohlcv_volume.columns
    }
)
hpandas.df_to_str(ohlcv_volume, num_rows=5, log_level=logging.INFO)

# %%
mean_hourly_volume = ohlcv_volume.groupby(lambda x: x.hour).mean()
hpandas.df_to_str(mean_hourly_volume, num_rows=5, log_level=logging.INFO)

# %%
title = "Mean hourly volume (Z-score)"
mean_hourly_volume.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
mean_minutely_volume = ohlcv_volume.groupby(lambda x: x.minute).mean()
hpandas.df_to_str(mean_minutely_volume, num_rows=5, log_level=logging.INFO)

# %%
title = "Mean minutely volume (Z-score)"
mean_minutely_volume.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
# Days of the week are numbered as follows:
# Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6.
mean_weekday_volume = ohlcv_volume.groupby(ohlcv_volume.index.weekday).mean()
hpandas.df_to_str(mean_weekday_volume, num_rows=5, log_level=logging.INFO)

# %%
title = "Mean weekday volume (Z-score)"
mean_weekday_volume.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %% [markdown]
# # Bid / ask price changes

# %%
bid_ask_im_client = icdcl.ccxt_clients.CcxtHistoricalPqByTileClient(
    **config["bid_ask_data"]["im_client_config"]
)

# %%
bid_ask_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    bid_ask_im_client,
    asset_ids,
    **config["bid_ask_data"]["market_data_config"],
)

# %%
bid_ask_data = bid_ask_market_data.get_data_for_interval(
    config["bid_ask_data"]["start_timestamp"],
    config["bid_ask_data"]["end_timestamp"],
    config["bid_ask_data"]["column_names"]["timestamp"],
    asset_ids,
)
# Convert to ET to be able to compare with US equities active trading hours.
bid_ask_data.index = bid_ask_data.index.tz_convert(config["US_equities_tz"])
hpandas.df_to_str(bid_ask_data, num_rows=5, log_level=logging.INFO)

# %%
# Set input parameters.
rolling_window = config["bid_ask_data"]["rolling_window"]
full_symbol_col = config["bid_ask_data"]["column_names"]["full_symbol"]
ask_price_col = config["bid_ask_data"]["column_names"]["ask_price"]
bid_price_col = config["bid_ask_data"]["column_names"]["bid_price"]
# Get ask and bid prices for all instruments.
# TODO(Dan): ideally we should use `HistoricalDataSource` so that it converts the data to the DataFlow format.
ask_price_df = bid_ask_data.pivot(columns=full_symbol_col, values=ask_price_col)
bid_price_df = bid_ask_data.pivot(columns=full_symbol_col, values=bid_price_col)

# %%
# Get midpoint from a corresponding column.
bid_ask_midpoint_col = config["bid_ask_data"]["column_names"]["bid_ask_midpoint"]
bid_ask_midpoint_df_from_col = bid_ask_data.pivot(
    columns=full_symbol_col, values=bid_ask_midpoint_col
)
hpandas.df_to_str(bid_ask_midpoint_df_from_col, log_level=logging.INFO)

# %%
# Get half-spread from the corresponding columns.
half_spread_col = config["bid_ask_data"]["column_names"]["half_spread"]
half_spread_df_from_col = bid_ask_data.pivot(
    columns=full_symbol_col, values=half_spread_col
)
half_spread_bps_df_from_col = (
    1e4 * half_spread_df_from_col / bid_ask_midpoint_df_from_col
)
hpandas.df_to_str(half_spread_bps_df_from_col, log_level=logging.INFO)

# %%
# Compute midpoint and half-spread.
bid_ask_midpoint_df_computed = 0.5 * (ask_price_df + bid_price_df)
half_spread_df_computed = (
    0.5 * (ask_price_df - bid_price_df) / bid_ask_midpoint_df_computed
)
half_spread_bps_df_computed = 1e4 * half_spread_df_computed
hpandas.df_to_str(half_spread_bps_df_computed, log_level=logging.INFO)

# %% run_control={"marked": false}
half_spread_bps_mean_from_col = half_spread_bps_df_from_col.mean().sort_values()
half_spread_bps_mean_from_col.name = (
    config["liquidity_metrics"]["half_spread_bps_mean"] + "_from_col"
)
#
title = "Half bid/ask spread from col"
ylabel = "bps"
half_spread_bps_mean_from_col.plot(
    title=title,
    ylabel=ylabel,
    **config["plot_kwargs"],
)

# %%
half_spread_bps_mean_computed = half_spread_bps_df_computed.mean().sort_values()
half_spread_bps_mean_computed.name = (
    config["liquidity_metrics"]["half_spread_bps_mean"] + "_computed"
)
#
title = "Half bid/ask spread computed"
ylabel = "bps"
half_spread_bps_mean_computed.plot(
    title=title,
    ylabel=ylabel,
    **config["plot_kwargs"],
)

# %%
ask_vol_df = ask_price_df.ffill().pct_change().rolling(rolling_window).std()
ask_vol_bps_df = 1e4 * ask_vol_df
hpandas.df_to_str(ask_vol_bps_df, log_level=logging.INFO)

# %%
ask_vol_bps_mean = ask_vol_bps_df.mean().sort_values()
ask_vol_bps_mean.name = config["liquidity_metrics"]["ask_vol_bps_mean"]
#
title = "ask vol"
ylabel = "bps"
ask_vol_bps_mean.plot(
    title=title,
    ylabel=ylabel,
    **config["plot_kwargs"],
)

# %%
mean_hourly_ask_vol = ask_vol_bps_df.groupby(lambda x: x.hour).mean()
title = "Mean hourly ask vol (Z-score)"
mean_hourly_ask_vol.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
bid_vol_df = bid_price_df.ffill().pct_change().rolling(rolling_window).std()
bid_vol_bps_df = 1e4 * bid_vol_df
hpandas.df_to_str(bid_vol_bps_df, log_level=logging.INFO)

# %%
bid_vol_bps_mean = bid_vol_bps_df.mean().sort_values()
bid_vol_bps_mean.name = config["liquidity_metrics"]["bid_vol_bps_mean"]
#
title = "bid vol"
ylabel = "bps"
bid_vol_bps_mean.plot(
    title=title,
    ylabel=ylabel,
    **config["plot_kwargs"],
)

# %%
mean_hourly_bid_vol = bid_vol_bps_df.groupby(lambda x: x.hour).mean()
title = "Mean hourly bid vol (Z-score)"
mean_hourly_bid_vol.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
# Get metric from columns.
bid_vol_to_half_spread_from_col = bid_vol_bps_df.divide(
    half_spread_bps_df_from_col
)
hpandas.df_to_str(bid_vol_to_half_spread_from_col, log_level=logging.INFO)

# %%
# Compute metric.
bid_vol_to_half_spread_computed = bid_vol_bps_df.divide(
    half_spread_bps_df_computed
)
hpandas.df_to_str(bid_vol_to_half_spread_computed, log_level=logging.INFO)

# %%
bid_vol_to_half_spread_mean_from_col = (
    bid_vol_to_half_spread_from_col.mean().sort_values(ascending=False)
)
bid_vol_to_half_spread_mean_from_col.name = (
    config["liquidity_metrics"]["bid_vol_to_half_spread_mean"] + "_from_col"
)
title = "Bid vol / half spread from col"
bid_vol_to_half_spread_mean_from_col.plot(
    title=title,
    **config["plot_kwargs"],
)

# %%
bid_vol_to_half_spread_mean_computed = (
    bid_vol_to_half_spread_computed.mean().sort_values(ascending=False)
)
bid_vol_to_half_spread_mean_computed.name = (
    config["liquidity_metrics"]["bid_vol_to_half_spread_mean"] + "_computed"
)
title = "Bid vol / half spread computed"
bid_vol_to_half_spread_mean_computed.plot(
    title=title,
    **config["plot_kwargs"],
)

# %%
total_vol = np.sqrt(bid_vol_bps_df**2 + ask_vol_bps_df**2)
mean_hourly_total_vol = total_vol.groupby(lambda x: x.hour).mean()
hpandas.df_to_str(mean_hourly_total_vol, log_level=logging.INFO)

# %%
title = "Mean hourly total vol (Z-score)"
mean_hourly_total_vol.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
mean_minutely_total_vol = total_vol.groupby(lambda x: x.minute).mean()
hpandas.df_to_str(mean_minutely_total_vol, log_level=logging.INFO)

# %%
title = "Mean minutely total vol (Z-score)"
mean_minutely_total_vol.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %%
# Days of the week are numbered as follows:
# Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6.
mean_weekday_total_vol = total_vol.groupby(total_vol.index.weekday).mean()
hpandas.df_to_str(mean_weekday_total_vol, log_level=logging.INFO)

# %%
title = "Mean weekday total vol (Z-score)"
mean_weekday_total_vol.apply(scipy.stats.zscore).plot(title=title, legend=False)

# %% [markdown]
# # Compute rank correlation

# %%
liquidity_metrics_df = pd.concat(
    [
        mdv_notional,
        half_spread_bps_mean_from_col,
        half_spread_bps_mean_computed,
        ask_vol_bps_mean,
        bid_vol_bps_mean,
        bid_vol_to_half_spread_mean_from_col,
        bid_vol_to_half_spread_mean_computed,
    ],
    axis=1,
)
liquidity_metrics_df

# %%
liquidity_metrics_df.corr(method="spearman")

# %%
liquidity_metrics_df.corr(method="kendall")

# %% [markdown]
# # Partition universe

# %% [markdown]
# ## Get `bid_vol_to_half_spread_mean` buckets

# %% [markdown]
# ### From col

# %%
# Bucket sizes are arbitrary set and depend on time-frame, universe size.
# Consider adjusting sizes, when re-running.
if config["partition_universe"]:
    # Get the vol metric values and put them in a DataFrame.
    bid_vol_to_half_spread_mean_df_from_col = (
        bid_vol_to_half_spread_mean_from_col.sort_values(
            ascending=False
        ).to_frame()
    )
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
    bid_vol_to_half_spread_bucket_from_col = pd.cut(
        bid_vol_to_half_spread_mean_df_from_col[
            config["liquidity_metrics"]["bid_vol_to_half_spread_mean"]
            + "_from_col"
        ],
        bins=cutpoints,
        labels=labels,
    )
    bid_vol_to_half_spread_bucket_from_col.name = (
        config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"] + "_from_col"
    )
    bid_vol_to_half_spread_mean_df_from_col = pd.concat(
        [
            bid_vol_to_half_spread_mean_df_from_col,
            bid_vol_to_half_spread_bucket_from_col,
        ],
        axis=1,
    )
    hpandas.df_to_str(
        bid_vol_to_half_spread_mean_df_from_col, log_level=logging.INFO
    )

# %% [markdown]
# ### Computed

# %%
# Bucket sizes are arbitrary set and depend on time-frame, universe size.
# Consider adjusting sizes, when re-running.
if config["partition_universe"]:
    # Get the vol metric values and put them in a DataFrame.
    bid_vol_to_half_spread_mean_df_computed = (
        bid_vol_to_half_spread_mean_computed.sort_values(
            ascending=False
        ).to_frame()
    )
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
    bid_vol_to_half_spread_bucket_computed = pd.cut(
        bid_vol_to_half_spread_mean_df_computed[
            config["liquidity_metrics"]["bid_vol_to_half_spread_mean"]
            + "_computed"
        ],
        bins=cutpoints,
        labels=labels,
    )
    bid_vol_to_half_spread_bucket_computed.name = (
        config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"] + "_computed"
    )
    bid_vol_to_half_spread_mean_df_computed = pd.concat(
        [
            bid_vol_to_half_spread_mean_df_computed,
            bid_vol_to_half_spread_bucket_computed,
        ],
        axis=1,
    )
    hpandas.df_to_str(
        bid_vol_to_half_spread_mean_df_computed, log_level=logging.INFO
    )

# %% [markdown]
# ## Get `half_spread_bps_mean` buckets

# %% [markdown]
# ### From col

# %%
# Bucket sizes are arbitrary set and depend on time-frame, universe size.
# Consider adjusting sizes, when re-running.
if config["partition_universe"]:
    # Get the vol metric values and put them in a DataFrame.
    half_spread_bps_mean_df_from_col = (
        half_spread_bps_mean_from_col.sort_values().to_frame()
    )
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
    half_spread_bucket_from_col = pd.cut(
        half_spread_bps_mean_df_from_col[
            config["liquidity_metrics"]["half_spread_bps_mean"] + "_from_col"
        ],
        bins=cutpoints,
        labels=labels,
    )
    half_spread_bucket_from_col.name = (
        config["liquidity_metrics"]["half_spread_bucket"] + "_from_col"
    )
    half_spread_bps_mean_df_from_col = pd.concat(
        [half_spread_bps_mean_df_from_col, half_spread_bucket_from_col], axis=1
    )
    hpandas.df_to_str(half_spread_bps_mean_df_from_col, log_level=logging.INFO)

# %% [markdown]
# ### Computed

# %%
# Bucket sizes are arbitrary set and depend on time-frame, universe size.
# Consider adjusting sizes, when re-running.
if config["partition_universe"]:
    # Get the vol metric values and put them in a DataFrame.
    half_spread_bps_mean_df_computed = (
        half_spread_bps_mean_computed.sort_values().to_frame()
    )
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
    half_spread_bucket_computed = pd.cut(
        half_spread_bps_mean_df_computed[
            config["liquidity_metrics"]["half_spread_bps_mean"] + "_computed"
        ],
        bins=cutpoints,
        labels=labels,
    )
    half_spread_bucket_computed.name = (
        config["liquidity_metrics"]["half_spread_bucket"] + "_computed"
    )
    half_spread_bps_mean_df_computed = pd.concat(
        [half_spread_bps_mean_df_computed, half_spread_bucket_computed], axis=1
    )
    hpandas.df_to_str(half_spread_bps_mean_df_computed, log_level=logging.INFO)

# %% [markdown]
# ## Partition by vol buckets

# %%
combined_liquidity_metrics_df = pd.concat(
    [
        liquidity_metrics_df,
        half_spread_bucket_from_col,
        half_spread_bucket_computed,
        bid_vol_to_half_spread_bucket_from_col,
        bid_vol_to_half_spread_bucket_computed,
    ],
    axis=1,
)

# %% [markdown]
# ### From col

# %%
if config["partition_universe"]:
    # Get universe.
    v8_1_metrics_df_from_col = combined_liquidity_metrics_df[
        (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["half_spread_bucket"] + "_from_col"
            ]
            == "(0.05, 0.5]"
        )
        & (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
                + "_from_col"
            ]
            == "(25, 250]"
        )
    ]
    v8_1_universe_from_col = sorted(list(v8_1_metrics_df_from_col.index))
    print(v8_1_universe_from_col)

# %%
if config["partition_universe"]:
    v8_2_metrics_df_from_col = combined_liquidity_metrics_df[
        (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["half_spread_bucket"] + "_from_col"
            ].isin(["(0.05, 0.5]", "(0.5, 1.0]"])
        )
        & (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
                + "_from_col"
            ].isin(["(25, 250]", "(10, 25]"])
        )
        & (~combined_liquidity_metrics_df.index.isin(v8_1_universe_from_col))
    ]
    v8_2_universe_from_col = sorted(list(v8_2_metrics_df_from_col.index))
    print(v8_2_universe_from_col)

# %% [markdown]
# ### Computed

# %%
if config["partition_universe"]:
    # Get universe.
    v8_1_metrics_df_computed = combined_liquidity_metrics_df[
        (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["half_spread_bucket"] + "_computed"
            ]
            == "(0.05, 0.5]"
        )
        & (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
                + "_computed"
            ]
            == "(25, 250]"
        )
    ]
    v8_1_universe_computed = sorted(list(v8_1_metrics_df_computed.index))
    print(v8_1_universe_computed)

# %%
if config["partition_universe"]:
    v8_2_metrics_df_computed = combined_liquidity_metrics_df[
        (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["half_spread_bucket"] + "_computed"
            ].isin(["(0.05, 0.5]", "(0.5, 1.0]"])
        )
        & (
            combined_liquidity_metrics_df[
                config["liquidity_metrics"]["bid_vol_to_half_spread_bucket"]
                + "_computed"
            ].isin(["(25, 250]", "(10, 25]"])
        )
        & (~combined_liquidity_metrics_df.index.isin(v8_1_universe_computed))
    ]
    v8_2_universe_computed = sorted(list(v8_2_metrics_df_computed.index))
    print(v8_2_universe_computed)

# %% [markdown]
# ## Universe differences

# %% [markdown]
# ### Computed vs from columns

# %%
v8_1_universe_from_col == v8_1_universe_computed

# %%
set(v8_2_universe_from_col) - set(v8_2_universe_computed)

# %%
set(v8_2_universe_computed) - set(v8_2_universe_from_col)

# %%
# Diff with "DUSK_USDT" seems to be a computational artifact.
combined_liquidity_metrics_df.loc["binance::DUSK_USDT"]

# %% [markdown]
# ### Current vs existing

# %% [markdown]
# There is a difference between existing v8 universes and computed in this notebook from columns and directly. The difference is hence explained by switch from `"v1_0_0"` version of bid-ask data to `"v2_0_0"`.

# %%
vendor = "ccxt"
mode = "trade"
v8_1_existing = ivcu.get_vendor_universe(vendor, mode, version="v8.1")["binance"]
v8_2_existing = ivcu.get_vendor_universe(vendor, mode, version="v8.2")["binance"]

# %%
v8_1_from_col = [s.split("::")[-1] for s in v8_1_universe_from_col]
v8_2_from_col = [s.split("::")[-1] for s in v8_2_universe_from_col]

# %%
set(v8_1_from_col) - set(v8_1_existing)

# %%
set(v8_1_existing) - set(v8_1_from_col)

# %%
set(v8_2_from_col) - set(v8_2_existing)

# %%
set(v8_2_existing) - set(v8_2_from_col)

# %%
