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

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %% [markdown]
# # Description

# %% [markdown]
# # Imports

# %% run_control={"marked": false}
import logging
import os

import pandas as pd
import seaborn as sns
from tqdm.autonotebook import tqdm

import core.config as cconfig
import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.pipelines.execution.execution_pipeline as dtfpexexpi
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdc
import im_v2.crypto_chassis.data.client as iccdc

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Client general arguments

# %%
s3_bucket_path = hs3.get_s3_bucket_path("ck")
root_dir = os.path.join(s3_bucket_path, "v3")
partition_mode = "by_year_month"
data_snapshot = ""
version = "v1_0_0"
resample_1min = False
aws_profile = "ck"
full_symbols = ["binance::BTC_USDT", "binance::ETH_USDT"]
filter_data_mode = "assert"

# %% [markdown]
# # OHLCV

# %% [markdown]
# ## Read data

# %% [markdown]
# Get OHLCV data for 01-08-2022 to 02-03-2023

# %%
ohlcv_universe_version = (
    "v1"  # Get the smallest universe that contains BTC and ETH
)
ohlcv_dataset = "ohlcv"
ohlcv_contract_type = "spot"
ohlcv_tag = "downloaded_1min"


# %%
ohlcv_ccxt_client = icdc.CcxtHistoricalPqByTileClient(
    ohlcv_universe_version,
    root_dir,
    partition_mode,
    ohlcv_dataset,
    ohlcv_contract_type,
    data_snapshot,
    tag=ohlcv_tag,
    version=version,
    resample_1min=resample_1min,
    aws_profile=aws_profile,
)

# %%
ohlcv_start_ts = pd.Timestamp("2022-08-01", tz="UTC")
ohlcv_end_ts = pd.Timestamp("2023-03-02", tz="UTC")
ohlcv_asset_ids = ohlcv_ccxt_client.get_asset_ids_from_full_symbols(full_symbols)
ohlcv_columns = None

# %%
ohlcv = ohlcv_ccxt_client.read_data(
    full_symbols, ohlcv_start_ts, ohlcv_end_ts, ohlcv_columns, filter_data_mode
)
ohlcv["asset_id"] = ohlcv["full_symbol"].apply(
    lambda x: ohlcv_ccxt_client.get_asset_ids_from_full_symbols([x])[0]
)


# %%
ohlcv.shape

# %%
ohlcv.head()

# %%
pivot_ohlcv = ohlcv.pivot(
    columns="full_symbol",
    values=["open", "high", "low", "close", "volume"],
)
pivot_ohlcv.head()

# %% [markdown]
# ## Resample to 1 hour

# %%
ohlcv_resampling_node = dtfcore.GroupedColDfToDfTransformer(
    "estimate_limit_order_execution",
    transformer_func=cofinanc.resample_bars,
    **{
        "in_col_groups": [
            ("close",),
            ("volume",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "rule": "1H",
            "resampling_groups": [
                ({"close": "close"}, "mean", {}),
                (
                    {"volume": "volume"},
                    "sum",
                    {"min_count": 1},
                ),
                (
                    {
                        "close": "twap",
                    },
                    "mean",
                    {},
                ),
            ],
            "vwap_groups": [
                ("close", "volume", "vwap"),
            ],
        },
        "reindex_like_input": False,
        "join_output_with_input": False,
    },
)

# %%
resampled_ohlcv = ohlcv_resampling_node.fit(pivot_ohlcv)["df_out"]


# %%
resampled_ohlcv.head()

# %% [markdown]
# ## Average volume by hour of the day

# %%
# Extract BTC and ETH dataframes.
resampled_ohlcv_btc = cofinanc.get_asset_slice(
    resampled_ohlcv, "binance::BTC_USDT"
).reset_index()
resampled_ohlcv_eth = cofinanc.get_asset_slice(
    resampled_ohlcv, "binance::ETH_USDT"
).reset_index()

# %%
# Get averages by hour.
resampled_ohlcv_btc_by_hour = resampled_ohlcv_btc.groupby(
    resampled_ohlcv_btc.timestamp.dt.hour
).mean()
resampled_ohlcv_eth_by_hour = resampled_ohlcv_eth.groupby(
    resampled_ohlcv_eth.timestamp.dt.hour
).mean()

# %%
display(resampled_ohlcv_btc_by_hour)
display(resampled_ohlcv_eth_by_hour)

# %% [markdown]
# ### Get total volume percentage by hour

# %%
# Get hourly average volume as percentage of total average day volume.
resampled_ohlcv_btc_by_hour["normalized_volume"] = resampled_ohlcv_btc_by_hour[
    "volume"
].apply(lambda x: x / resampled_ohlcv_btc_by_hour["volume"].sum())
#
resampled_ohlcv_eth_by_hour["normalized_volume"] = resampled_ohlcv_eth_by_hour[
    "volume"
].apply(lambda x: x / resampled_ohlcv_eth_by_hour["volume"].sum())


# %%
display(resampled_ohlcv_btc_by_hour)
display(resampled_ohlcv_eth_by_hour)

# %%
display(resampled_ohlcv_eth_by_hour[["normalized_volume"]].plot(kind="bar"))
display(resampled_ohlcv_btc_by_hour[["normalized_volume"]].plot(kind="bar"))

# %% [markdown]
# ### Get total volume by day of the week

# %%
# BTC.
resampled_ohlcv_btc_by_day = resampled_ohlcv_btc.groupby(
    resampled_ohlcv_btc.timestamp.dt.weekday
).mean()
resampled_ohlcv_btc_by_day

# %%
# ETH.
resampled_ohlcv_eth_by_day = resampled_ohlcv_eth.groupby(
    resampled_ohlcv_eth.timestamp.dt.weekday
).mean()
resampled_ohlcv_eth_by_day

# %% [markdown]
# ### Get percentage of the total volume by day of the week

# %%
# Get daily average volume as percentage of total average weekly volume.
resampled_ohlcv_btc_by_day["normalized_volume"] = resampled_ohlcv_btc_by_day[
    "volume"
].apply(lambda x: x / resampled_ohlcv_btc_by_day["volume"].sum())
#
resampled_ohlcv_eth_by_day["normalized_volume"] = resampled_ohlcv_eth_by_day[
    "volume"
].apply(lambda x: x / resampled_ohlcv_eth_by_day["volume"].sum())


# %% run_control={"marked": true}
display(resampled_ohlcv_btc_by_day[["normalized_volume"]].plot(kind="bar"))
display(resampled_ohlcv_eth_by_day[["normalized_volume"]].plot(kind="bar"))


# %% [markdown]
# # Bid/ask

# %% [markdown]
# ## Functions

# %% [markdown]
# Factored out common operations for loading and transformation of futures/spot bid/ask data.

# %% run_control={"marked": true}
def load_data(data_type: str) -> pd.DataFrame:
    """
    Load futures/spot data for the experiment.
    """
    #
    bid_ask_start_ts = pd.Timestamp("2023-02-01 00:00:00", tz="UTC")
    bid_ask_end_ts = pd.Timestamp("2023-02-28 23:59:59", tz="UTC")
    #
    if data_type == "futures":
        # Load futures data for February 2023.
        bid_ask_universe_version = "v3"
        bid_ask_contract_type = "futures"
        bid_ask_tag = "downloaded_1sec"
        bid_ask_dataset = "bid_ask"
        bid_ask_columns = [
            "full_symbol",
            "bid_price_l1",
            "ask_price_l1",
            "bid_size_l1",
            "ask_size_l1",
            "knowledge_timestamp",
        ]
        cc_bid_ask_client = iccdc.CryptoChassisHistoricalPqByTileClient(
            bid_ask_universe_version,
            root_dir,
            partition_mode,
            bid_ask_dataset,
            bid_ask_contract_type,
            data_snapshot,
            version=version,
            tag=bid_ask_tag,
            aws_profile=aws_profile,
            resample_1min=resample_1min,
        )
        data = cc_bid_ask_client.read_data(
            full_symbols,
            bid_ask_start_ts,
            bid_ask_end_ts,
            bid_ask_columns,
            filter_data_mode,
        )
        col_rename_mapping = {}
        for c in data.columns:
            col_rename_mapping[c] = c.replace("_l1", "")
        data = data.rename(col_rename_mapping, axis=1)
    elif data_type == "spot":
        # Load spot data for November 2022 directly from parquet dataset.
        # Note: this is the only complete data range for 1 sec spot data we have right now (2022-03-06).
        path = "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask/crypto_chassis.downloaded_1sec/binance/"
        data = hparque.from_parquet(path, aws_profile=aws_profile)
        data["full_symbol"] = data["currency_pair"].apply(
            lambda x: "binance::" + x
        )
        data = data[data["full_symbol"].isin(full_symbols)]
        data = data[
            [
                "bid_price",
                "bid_size",
                "ask_price",
                "ask_size",
                "currency_pair",
                "full_symbol",
            ]
        ]
        data = data.loc[data.index <= pd.Timestamp("2022-11-30 23:59:59+00:00")]
    else:
        raise ValueError("Incorrect data type, use 'futures' or 'spot'")
    return data


def create_execution_pipeline(subsample_freq: int):
    """
    Get DAG for computing execution quality.
    """
    dag_builder = dtfpexexpi.ExecutionPipeline()
    #
    config = dag_builder.get_config_template()
    # Set up `overwrite` mode to allow reassignment of values.
    # Note: by default the `update_mode` does not allow overwrites,
    # but they are required by the FeaturePipeline.
    config.update_mode = "overwrite"
    _LOG.debug("config from dag_builder=%s", config)
    # Initialize config.
    config["load_data"] = cconfig.Config.from_dict(
        {
            "source_node_name": "FunctionDataSource",
            "source_node_kwargs": {
                "func": get_data,
            },
        }
    )
    config[
        "generate_limit_orders", "transformer_kwargs", "sell_spread_frac_offset"
    ] = 0.0
    config[
        "generate_limit_orders", "transformer_kwargs", "subsample_freq"
    ] = f"{subsample_freq}s"
    config[
        "generate_limit_orders", "transformer_kwargs", "ffill_limit"
    ] = subsample_freq
    #
    _LOG.debug("config after patching=%s", config)
    dag = dag_builder.get_dag(config)
    return dag


def calculate_and_apply_weights(resampled_bid_ask: pd.DataFrame):
    """
    Apply normalized OHLCV volume by hour as weights to bid price.
    """
    # Get corresponding hour for each 1-hour entry.
    # Slice asset-specific dataframes.
    resampled_bid_ask_btc = cofinanc.get_asset_slice(
        resampled_bid_ask, "binance::BTC_USDT"
    ).reset_index()
    resampled_bid_ask_btc["hour"] = resampled_bid_ask_btc.reset_index()[
        "timestamp"
    ].dt.hour
    resampled_bid_ask_eth = cofinanc.get_asset_slice(
        resampled_bid_ask, "binance::ETH_USDT"
    ).reset_index()
    resampled_bid_ask_eth["hour"] = resampled_bid_ask_eth.reset_index()[
        "timestamp"
    ].dt.hour
    # Convert weights to dicts by asset.
    btc_hour_weights = resampled_ohlcv_btc_by_hour["normalized_volume"].to_dict()
    eth_hour_weights = resampled_ohlcv_eth_by_hour["normalized_volume"].to_dict()
    # Replace hour with corresponding weight.
    resampled_bid_ask_btc["weights"] = resampled_bid_ask_btc["hour"].map(
        btc_hour_weights
    )
    resampled_bid_ask_eth["weights"] = resampled_bid_ask_eth["hour"].map(
        eth_hour_weights
    )
    # Apply weights.
    resampled_bid_ask_btc["weighted_bid_price"] = (
        resampled_bid_ask_btc["bid_price"] * resampled_bid_ask_btc["weights"]
    )
    resampled_bid_ask_eth["weighted_bid_price"] = (
        resampled_bid_ask_eth["bid_price"] * resampled_bid_ask_eth["weights"]
    )
    return resampled_bid_ask_btc, resampled_bid_ask_eth


def get_data():
    """
    Get pivot data (for DataSource node).
    """
    return pivot_bid_ask


def get_sum_bid_price_by_day(resampled_bid_ask: pd.DataFrame):
    """
    Resample data by 1D and get a sum.
    """
    resampled_bid_ask = resampled_bid_ask.set_index("timestamp")
    by_day_bid_ask = (
        resampled_bid_ask["weighted_bid_price"].resample(rule="D").sum()
    )
    return by_day_bid_ask


def apply_weights_to_execution_pipeline(df_out: pd.DataFrame):
    """
    Apply normalized volume weights to hourly execution quality data.
    """
    df_out_btc = cofinanc.get_asset_slice(
        df_out, "binance::BTC_USDT"
    ).reset_index()
    df_out_eth = cofinanc.get_asset_slice(
        df_out, "binance::ETH_USDT"
    ).reset_index()
    df_out_btc["hour"] = df_out_btc.reset_index().timestamp.dt.hour
    df_out_eth["hour"] = df_out_eth.reset_index().timestamp.dt.hour
    # Convert weights to dicts by asset.
    btc_hour_weights = resampled_ohlcv_btc_by_hour["normalized_volume"].to_dict()
    eth_hour_weights = resampled_ohlcv_eth_by_hour["normalized_volume"].to_dict()
    # Replace hour with corresponding weight.
    df_out_btc["weights"] = df_out_btc["hour"].map(btc_hour_weights)
    df_out_eth["weights"] = df_out_eth["hour"].map(eth_hour_weights)
    # Apply weights.
    df_out_btc["weighted_sell_trade_price"] = (
        df_out_btc["sell_trade_price"] * df_out_btc["weights"]
    )
    df_out_eth["weighted_sell_trade_price"] = (
        df_out_eth["sell_trade_price"] * df_out_eth["weights"]
    )
    df_out_btc = df_out_btc.set_index("timestamp")
    df_out_eth = df_out_eth.set_index("timestamp")
    return df_out_btc, df_out_eth


# %% [markdown]
# ## Futures

# %% [markdown]
# ### Read data

# %%
# Load futures data for February 2023.
bid_ask = load_data("futures")

# %% [markdown]
# ### Transform

# %%
# Add spread column.
bid_ask["quoted_spread"] = bid_ask["ask_price"] - bid_ask["bid_price"]
bid_ask

# %%
pivot_bid_ask = bid_ask.pivot(
    columns="full_symbol",
    values=[
        "bid_price",
        "ask_price",
        "bid_size",
        "ask_size",
        "quoted_spread",
    ],
)
pivot_bid_ask.head()

# %%
# Resample futures to 1 hour.
bid_ask_resampling_node = dtfcore.GroupedColDfToDfTransformer(
    "estimate_limit_order_execution",
    transformer_func=cofinanc.resample_bars,
    **{
        "in_col_groups": [
            ("bid_price",),
            ("ask_price",),
            ("bid_size",),
            ("ask_size",),
            ("quoted_spread",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "rule": "1H",
            "resampling_groups": [
                # 1 resampling per aggregation group -> 1 transform function, 1 dict
                (
                    {
                        "bid_price": "bid_price",
                        "ask_price": "ask_price",
                        "bid_size": "bid_size",
                        "ask_size": "ask_size",
                        "quoted_spread": "quoted_spread",
                    },
                    "mean",
                    {},
                ),
            ],
            "vwap_groups": [],
        },
        "reindex_like_input": False,
        "join_output_with_input": False,
    },
)
resampled_bid_ask = bid_ask_resampling_node.fit(pivot_bid_ask)["df_out"]

# %%
# Apply weights to bid price based on OHLCV average hourly volume.
resampled_bid_ask_btc, resampled_bid_ask_eth = calculate_and_apply_weights(
    resampled_bid_ask
)

# %%
# Plot average spread per hour.
resampled_bid_ask_btc["quoted_spread"].groupby(
    resampled_bid_ask_btc.timestamp.dt.hour
).mean().plot()

# %%
# Plot normalized volume by hour (for reference with average spread).
resampled_ohlcv_btc_by_hour[["normalized_volume"]].plot(kind="bar")

# %%
by_day_bid_ask_btc = get_sum_bid_price_by_day(resampled_bid_ask_btc)
by_day_bid_ask_eth = get_sum_bid_price_by_day(resampled_bid_ask_eth)

# %%
by_day_bid_ask_btc.plot(kind="bar")

# %% [markdown]
# ### Execution pipeline

# %%
# Run execution quality pipeline with subsampling=60.
dag = create_execution_pipeline(60)
df_out = dag.run_leq_node("compute_bid_ask_execution_quality", "fit")["df_out"]

# %%
# Apply weights to sell price.
df_out_btc, df_out_eth = apply_weights_to_execution_pipeline(df_out)

# %%
# Get sell and weighted bid prices by day.
sell_trade_price_eth = (
    df_out_eth["weighted_sell_trade_price"].resample(rule="D").sum()
)

bid_price_eth_by_day = (
    resampled_bid_ask_eth.set_index("timestamp")["weighted_bid_price"]
    .resample(rule="D")
    .sum()
)

# %% [markdown]
# ### Check results with different subsamples.

# %%
# Sweep over multiple subsampling values.
frequencies = [1, 60, 300, 900, 3600]
result_dict = {}
for f in frequencies:
    dag = create_execution_pipeline(f)
    df = dag.run_leq_node("compute_bid_ask_execution_quality", "fit")["df_out"]
    result_dict[f] = df

# %% [markdown]
# ## Spot

# %%
# Load spot data for November 2022.
bid_ask = load_data("spot")

# %% [markdown]
# ### Transform

# %%
# Add spread column.
bid_ask["quoted_spread"] = bid_ask["ask_price"] - bid_ask["bid_price"]
bid_ask

# %%
# Pivot for compatibility with Dataflow nodes.
pivot_bid_ask = bid_ask.pivot(
    columns="full_symbol",
    values=[
        "bid_price",
        "ask_price",
        "bid_size",
        "ask_size",
        "quoted_spread",
    ],
)
pivot_bid_ask.head()

# %%
# Resample spot data to 1 hour.
bid_ask_resampling_node = dtfcore.GroupedColDfToDfTransformer(
    "estimate_limit_order_execution",
    transformer_func=cofinanc.resample_bars,
    **{
        "in_col_groups": [
            ("bid_price",),
            ("ask_price",),
            ("bid_size",),
            ("ask_size",),
            ("quoted_spread",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "rule": "1H",
            "resampling_groups": [
                # 1 resampling per aggregation group -> 1 transform function, 1 dict
                (
                    {
                        "bid_price": "bid_price",
                        "ask_price": "ask_price",
                        "bid_size": "bid_size",
                        "ask_size": "ask_size",
                        "quoted_spread": "quoted_spread",
                    },
                    "mean",
                    {},
                ),
            ],
            "vwap_groups": [],
        },
        "reindex_like_input": False,
        "join_output_with_input": False,
    },
)
# Resample to 1 hour.
resampled_bid_ask = bid_ask_resampling_node.fit(pivot_bid_ask)["df_out"]

# %%
resampled_bid_ask.head(5)

# %% [markdown]
# ### Apply weights
#
# - Weights are calculated as the percentage of the total average day volume that the average hour volume constitutes.

# %%
resampled_bid_ask_btc, resampled_bid_ask_eth = calculate_and_apply_weights(
    resampled_bid_ask
)

# %%
display(resampled_bid_ask_btc.head())
display(resampled_bid_ask_eth.head())

# %%
# Plot average spread per hour.
resampled_bid_ask_btc["quoted_spread"].groupby(
    resampled_bid_ask_btc.timestamp.dt.hour
).mean().plot()

# %%
# Plot normalized volume by hour (for reference with average spread).
resampled_ohlcv_btc_by_hour[["normalized_volume"]].plot(kind="bar")

# %%
# Get total bid price by day.
by_day_bid_ask_btc = get_sum_bid_price_by_day(resampled_bid_ask_btc)
by_day_bid_ask_eth = get_sum_bid_price_by_day(resampled_bid_ask_eth)

# %%
display(by_day_bid_ask_btc.plot(kind="bar"))
display(by_day_bid_ask_eth.plot(kind="bar"))

# %% [markdown]
# ### Execution flow simulation

# %%
dag = create_execution_pipeline(60)
df_out = dag.run_leq_node("compute_bid_ask_execution_quality", "fit")["df_out"]
df_out = df_out[df_out.index <= pd.Timestamp("2022-11-30 23:59:59+00:00")]

# %%
df_out["limit_sell_executed"].plot()

# %% run_control={"marked": true}
df_out_btc, df_out_eth = apply_weights_to_execution_pipeline(df_out)

# %%

# %%
df_out_btc["weighted_sell_trade_price"].resample(rule="D").sum()

# %% run_control={"marked": true}
# Get daily sell price and total bid price, weighted by average hourly volume.
sell_trade_price_eth = (
    df_out_eth["weighted_sell_trade_price"].resample(rule="D").sum()
)

bid_price_eth_by_day = (
    resampled_bid_ask_eth.set_index("timestamp")["weighted_bid_price"]
    .resample(rule="D")
    .sum()
)

# %%
pd.concat([sell_trade_price_eth, bid_price_eth_by_day], axis=1).plot(kind="bar")

# %% [markdown]
# ### Sanity check up to `generate_limit_orders`

# %%
limit_order_check = dag.run_leq_node("generate_limit_orders", "fit")["df_out"]

# %%
limit_order_check

# %%
limit_order_check.buy_limit_order_price.isna().sum()

# %% [markdown]
# ### Check results with different subsamples

# %%
frequencies = [1, 60, 300, 900, 3600]
result_dict = {}
for f in frequencies:
    dag = create_execution_pipeline(f)
    df = dag.run_leq_node("compute_bid_ask_execution_quality", "fit")["df_out"]
    result_dict[f] = df

# %%
result_dict[60]

# %% [markdown]
# ## Spot market depth and impact

# %%
# This section relies upon test data.
assert 0

# %%
epoch_unit = "s"
# Convert dates to unix timestamps.
start = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp("2022-11-01T00:00:00+00:00"), epoch_unit
)
end = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp("2022-11-01T23:59:59+00:00"), unit=epoch_unit
)
# Define filters for data period.
filters = [("timestamp", ">=", start), ("timestamp", "<=", end)]
filters.append(("currency_pair", "in", ["BTC_USDT", "ETH_USDT"]))
base_columns = ["timestamp", "currency_pair"]
bid_ask_cols = ["bid_size", "bid_price", "ask_size", "ask_price"]
level_columns = [
    ba_col + f"_l{l}"
    for l in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for ba_col in bid_ask_cols
]
columns = base_columns + level_columns
src_dir = "s3://cryptokaizen-data-test/v3/bulk/manual/downloaded_1sec/parquet/bid_ask/spot/v3/crypto_chassis/binance/v1_0_0"
data = hparque.from_parquet(
    src_dir, columns=columns, filters=filters, aws_profile="ck"
)


# %%
def get_book_slice(
    data: pd.DataFrame,
    timestamp: pd.Timestamp,
    currency_pair: str,
    max_depth: int,
) -> pd.DataFrame:
    data = data[data["currency_pair"] == currency_pair]
    data = data.loc[timestamp]
    bid_srs = {}
    bid_size_srs = {}
    ask_srs = {}
    ask_size_srs = {}
    for level in range(1, max_depth + 1):
        bid_srs[level] = data.loc["bid_price_l" + str(level)]
        bid_size_srs[level] = data.loc["bid_size_l" + str(level)]
        ask_srs[level] = data.loc["ask_price_l" + str(level)]
        ask_size_srs[level] = data.loc["ask_size_l" + str(level)]
    bid_srs = pd.Series(bid_srs, name="bid")
    bid_size_srs = pd.Series(bid_size_srs, name="bid_size")
    ask_srs = pd.Series(ask_srs, name="ask")
    ask_size_srs = pd.Series(ask_size_srs, name="ask_size")
    df = pd.concat([bid_srs, bid_size_srs, ask_srs, ask_size_srs], axis=1)
    return df


# %%
data.head()

# %%
timestamp = pd.Timestamp("2022-11-01 00:03:01+00:00")
obslice = get_book_slice(data, timestamp, "BTC_USDT", 10)
display(obslice)
mi = cofinanc.estimate_market_order_price(
    obslice,
    "bid",
    "bid_size",
)
display(mi)


# %%
def get_price_degradation_and_notional(data, timestamps, symbol):
    price_degradation = {}
    notional = {}
    for timestamp in tqdm(timestamps):
        obslice = get_book_slice(data, timestamp, symbol, 10)
        mi = cofinanc.estimate_market_order_price(
            obslice,
            "bid",
            "bid_size",
        )
        price_degradation[timestamp] = mi["price_degradation_bps"]
        notional[timestamp] = mi["cumulative_notional"]
    mi_curve = pd.concat(price_degradation, axis=1).T
    not_curve = pd.concat(notional, axis=1).T
    return mi_curve, not_curve


# %%
hourly_timestamps = [
    pd.Timestamp("2022-11-01 00:00:00+00:00"),
    pd.Timestamp("2022-11-01 01:00:00+00:00"),
    pd.Timestamp("2022-11-01 02:00:00+00:00"),
    pd.Timestamp("2022-11-01 03:00:00+00:00"),
    pd.Timestamp("2022-11-01 04:00:00+00:00"),
    pd.Timestamp("2022-11-01 05:00:00+00:00"),
    pd.Timestamp("2022-11-01 06:00:00+00:00"),
    pd.Timestamp("2022-11-01 07:00:00+00:00"),
    pd.Timestamp("2022-11-01 08:00:00+00:00"),
    pd.Timestamp("2022-11-01 09:00:00+00:00"),
    pd.Timestamp("2022-11-01 10:00:00+00:00"),
    pd.Timestamp("2022-11-01 11:00:00+00:00"),
    pd.Timestamp("2022-11-01 12:00:00+00:00"),
    pd.Timestamp("2022-11-01 13:00:00+00:00"),
    pd.Timestamp("2022-11-01 14:00:00+00:00"),
    pd.Timestamp("2022-11-01 15:00:00+00:00"),
    pd.Timestamp("2022-11-01 16:00:00+00:00"),
    pd.Timestamp("2022-11-01 17:00:00+00:00"),
    pd.Timestamp("2022-11-01 18:00:00+00:00"),
    pd.Timestamp("2022-11-01 19:00:00+00:00"),
    pd.Timestamp("2022-11-01 20:00:00+00:00"),
    pd.Timestamp("2022-11-01 21:00:00+00:00"),
    pd.Timestamp("2022-11-01 22:00:00+00:00"),
    pd.Timestamp("2022-11-01 23:00:00+00:00"),
]

# %%
price_degradation, volume = get_price_degradation_and_notional(
    data, hourly_timestamps, "BTC_USDT"
)

# %%
price_degradation.mean()

# %%
volume.sum()

# %%
1.0018**24

# %%

# %%
mi_curve, not_curve = get_price_degradation_and_notional(
    data, data.index[:1000], "BTC_USDT"
)

# %%
sns.pointplot(mi_curve, errorbar="sd")

# %%
sns.pointplot(not_curve, errorbar="sd")

# %%
