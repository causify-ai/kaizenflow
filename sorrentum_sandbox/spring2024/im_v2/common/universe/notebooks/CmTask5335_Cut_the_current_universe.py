# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# Compute liquidity-related statistics for the CCXT universe v7.1.

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
import core.plotting as coplotti
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
config = {
    "universe": {
        "vendor": "CCXT",
        "mode": "trade",
        "version": "v7.1",
    },
    "bid_ask_data": {
        "signature": "periodic_daily.airflow.archived_200ms.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0",
        "db_stage": "preprod",
        # We can process only 1 hour of bid-ask data without OOM error.
        "start_timestamp": pd.Timestamp("2023-09-10 15:00:00+00:00"),
        "end_timestamp": pd.Timestamp("2023-09-10 16:00:00+00:00"),
    },
    "ohlcv_data": {
        "start_timestamp": pd.Timestamp("2023-01-01 00:00:00+00:00"),
        "end_timestamp": pd.Timestamp("2023-09-10 16:00:00+00:00"),
        "resampling_rule": "D",
    },
    "column_names": {
        "timestamp": "timestamp",
        "full_symbol_column": "full_symbol",
        "close": "close",
        "volume": "volume",
        "volume_notional": "volume_notional",
    },
    "bar_duration": "5T",
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Universe

# %%
# Get full symbol universe.
full_symbols = ivcu.get_vendor_universe(
    config["universe"]["vendor"],
    config["universe"]["mode"],
    version=config["universe"]["version"],
    as_full_symbol=True,
)
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
# TODO(Grisha): expose DB stage.
# Get prod `MarketData`.
market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(asset_ids)
# Load and resample OHLCV data.
ohlcv_data = dtfamsysc.load_and_resample_ohlcv_data(
    market_data,
    config["ohlcv_data"]["start_timestamp"],
    config["ohlcv_data"]["end_timestamp"],
    config["bar_duration"],
)
hpandas.df_to_str(ohlcv_data, num_rows=5, log_level=logging.INFO)

# %%
# Compute notional volume.
volume_notional = (
    ohlcv_data[config["column_names"]["volume"]]
    * ohlcv_data[config["column_names"]["close"]]
)
volume_notional

# %%
# Compute mean daily notional volume.
mdv_notional = (
    volume_notional.resample(config["ohlcv_data"]["resampling_rule"]).sum().mean()
)
mdv_notional = mdv_notional.sort_values().round(2)
# Replace asset ids with full symbols.
mdv_notional.index = [
    asset_id_to_full_symbol_mapping[idx] for idx in mdv_notional.index
]
mdv_notional.name = "mdv_notional"
mdv_notional

# %%
coplotti.plot_barplot(
    mdv_notional,
    annotation_mode="pct",
    orientation="horizontal",
    figsize=[20, 50],
    yscale="log",
)

# %% [markdown]
# # Bid / ask price changes

# %%
# TODO(Grisha): use `ImClient` once bid/ask data is resampled to 1 minute.
bid_ask_reader = icdc.RawDataReader(
    config["bid_ask_data"]["signature"],
    stage=config["bid_ask_data"]["db_stage"],
)
bid_ask_data = bid_ask_reader.read_data(
    config["bid_ask_data"]["start_timestamp"],
    config["bid_ask_data"]["end_timestamp"],
)
_LOG.info("bid_ask_data.shape=%s", bid_ask_data.shape)
hpandas.df_to_str(bid_ask_data, num_rows=5, log_level=logging.INFO)

# %%
# Keep only the top-of-the-book data for further analysis.
bid_ask_data = bid_ask_data[bid_ask_data["level"] == 1]
bid_ask_data.head()

# %%
full_symbol_col = ivcu.build_full_symbol(
    bid_ask_data["exchange_id"], bid_ask_data["currency_pair"]
)
bid_ask_data.insert(
    0, config["column_names"]["full_symbol_column"], full_symbol_col
)
bid_ask_data.head(3)

# %%
# Remove `timestamp` column since the info is already in index.
bid_ask_data = bid_ask_data.drop(config["column_names"]["timestamp"], axis=1)
bid_ask_data = (
    bid_ask_data.reset_index()
    .sort_values(
        [
            config["column_names"]["full_symbol_column"],
            config["column_names"]["timestamp"],
        ]
    )
    .set_index(config["column_names"]["timestamp"])
)
bid_ask_data = bid_ask_data.sort_index()
bid_ask_data.head(3)

# %%
# Remove duplicates.
use_index = True
duplicate_columns = [config["column_names"]["full_symbol_column"]]
_LOG.info(
    "The number of rows before removing duplicates=%s", bid_ask_data.shape[0]
)
bid_ask_data = hpandas.drop_duplicates(
    bid_ask_data,
    column_subset=duplicate_columns,
    use_index=use_index,
)
_LOG.info(
    "The number of rows after removing duplicates=%s", bid_ask_data.shape[0]
)

# %%
# Check whether the bid price has changed or not.
bid_ask_data["is_bid_price_changed"] = (
    bid_ask_data.groupby(config["column_names"]["full_symbol_column"])[
        "bid_price"
    ]
    .diff()
    .abs()
    > 0
)
# Check whether the ask price has changed or not.
bid_ask_data["is_ask_price_changed"] = (
    bid_ask_data.groupby(config["column_names"]["full_symbol_column"])[
        "ask_price"
    ]
    .diff()
    .abs()
    > 0
)
# The price has changed if either bid or ask price has changed.
bid_ask_data["is_price_changed"] = (
    bid_ask_data["is_bid_price_changed"] | bid_ask_data["is_ask_price_changed"]
)
bid_ask_data.head()

# %%
# Count the number of times when the price has changed within a bar.
price_changes_count = (
    bid_ask_data.groupby(config["column_names"]["full_symbol_column"])
    .resample(config["bar_duration"])["is_price_changed"]
    .sum()
    .reset_index()
)
# Rename column accordingly.
price_changes_count = price_changes_count.rename(
    columns={"is_price_changed": "price_changes_amount"}
)
price_changes_count.head()

# %%
# Average price change counts across all bars.
avg_price_changes_5T = (
    price_changes_count.groupby(config["column_names"]["full_symbol_column"])[
        "price_changes_amount"
    ]
    .mean()
    .sort_values()
    .round(2)
)
avg_price_changes_5T

# %% [markdown]
# # ECDF

# %%
# There are 2 asset_ids in the current universe that are not in the ECDF series.
ecdf = pd.Series(
    index=[
        2484635488,
        1966583502,
        1030828978,
        1528092593,
        6051632686,
        2425308589,
        2099673105,
        4516629366,
        3401245610,
        1891737434,
        2540896331,
        5118394986,
        3065029174,
        2683705052,
        5115052901,
        2601760471,
        8717633868,
        8968126878,
        2237530510,
        2384892553,
        1467591036,
        1464553467,
        1776791608,
    ],
    data=[
        0.008451,
        0.014953,
        0.015789,
        0.025316,
        0.027273,
        0.036446,
        0.040000,
        0.081967,
        0.087719,
        0.127178,
        0.127451,
        0.176252,
        0.181070,
        0.215501,
        0.217923,
        0.284585,
        0.326877,
        0.394872,
        0.510309,
        0.512681,
        0.552356,
        0.555556,
        0.720000,
    ],
)

# %%
ecdf.index = [asset_id_to_full_symbol_mapping[idx] for idx in ecdf.index]
ecdf = ecdf.sort_values()
ecdf.name = "ecdf"
ecdf

# %% [markdown]
# # Compute rank correlation

# %%
liquidity_metrics_df = pd.concat(
    [avg_price_changes_5T, mdv_notional, ecdf],
    axis=1,
)
liquidity_metrics_df

# %%
is_price_changed_rank = liquidity_metrics_df["price_changes_amount"].rank()
mdv_notional_rank = liquidity_metrics_df["mdv_notional"].rank()
ecdf_rank = liquidity_metrics_df["ecdf"].rank()

# %%
rank_df = pd.concat(
    [is_price_changed_rank, mdv_notional_rank, ecdf_rank],
    axis=1,
)
rank_df

# %%
corr_matrix_spearman = rank_df.corr(method="spearman")
corr_matrix_spearman

# %%
corr_matrix_kendall = rank_df.corr(method="kendall")
corr_matrix_kendall

# %%
