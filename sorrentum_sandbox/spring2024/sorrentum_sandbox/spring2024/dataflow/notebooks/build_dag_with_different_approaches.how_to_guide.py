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

# %%
# %load_ext autoreload
# %autoreload 2

# %% [markdown]
# # Description

# %% [markdown]
# The goal of this notebook is to demonstrate the various approaches of working with `dataflow`.

# %% [markdown]
# # Imports

# %%
import logging

import pandas as pd

import core.config.config_ as cconconf
import core.finance as cofinanc
import core.finance.resampling as cfinresa
import core.finance.returns as cfinretu
import dataflow.core as dtfcore
import dataflow.core.utils as dtfcorutil
import dataflow.universe as dtfuniver
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import market_data as mdata

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()


# %% [markdown]
# # Config


# %%
def get_gallery_dataflow_example_config() -> cconconf.Config:
    """
    Get config, that specifies params for getting raw data.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["data_snapshot"] = "latest"
    config["load"]["dataset"] = "ohlcv"
    config["load"]["contract_type"] = "futures"
    config["load"]["universe_version"] = "v7"
    config["load"]["data_version"] = "v2"
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["start_date"] = pd.Timestamp("2021-09-01", tz="UTC")
    config["data"]["end_date"] = pd.Timestamp("2021-09-15", tz="UTC")
    config["data"]["resampling_rule"] = "5T"
    return config


# %%
config = get_gallery_dataflow_example_config()
print(config)

# %% [markdown]
# # Load historical data

# %% [markdown]
# ## Get IM client

# %%
data_version = config["load"]["data_version"]
universe_version = config["load"]["universe_version"]
contract_type = config["load"]["contract_type"]
dataset = config["load"]["dataset"]
data_snapshot = config["load"]["data_snapshot"]
client = icdcl.ccxt_clients_example.get_CcxtHistoricalPqByTileClient_example1(
    data_version, universe_version, dataset, contract_type, data_snapshot
)


# %% [markdown]
# ## Get universe

# %%
# Set the universe.
universe_str = "ccxt_v7-all"
full_symbols = dtfuniver.get_universe(universe_str)
asset_ids = client.get_asset_ids_from_full_symbols(full_symbols)
# %% [markdown]
# ## Get market data loader

# %% run_control={"marked": true}
columns = None
columns_remap = None
wall_clock_time = pd.Timestamp("2100-01-01T00:00:00+00:00")
market_data = mdata.market_data_example.get_HistoricalImClientMarketData_example1(
    client, asset_ids, columns, columns_remap, wall_clock_time=wall_clock_time
)


# %% [markdown] run_control={"marked": true}
# ## Get data

# %%
start_ts = config["data"]["start_date"]
end_ts = config["data"]["end_date"]
ts_col_name = "timestamp"
data_hist = market_data.get_data_for_interval(
    start_ts, end_ts, ts_col_name, asset_ids
)
print(data_hist.shape)
data_hist.head(3)

# %% [markdown]
# # Task description

# %% [markdown]
# The goal of this exercise is to implement the following transformations to the historical data:
# - resampling
# - VWAP, TWAP computation
# - Calculation of returns
#
# While using the different approaches to working with `dataflow` methods.
# The main feature that these methods are trying to overcome is the fact that when the raw data consists of two and more `full_symbols`, then one needs to be careful to apply transformations that needs to be implemented specifically to each `full_symbol`.
#
# These three approaches are:
# - 1) Use the "low level" functions and do loops
# - 2) Use pandas Multi-index
# - 3) Use Dataflow nodes
#
# The general rule is to use the third and second approach when possible, while keeping the first approach as a bacjup.

# %%
# The resampling frequency is the same for all approaches.
resampling_freq = config["data"]["resampling_rule"]


# %% [markdown]
# # Approach 1 - Use the "low level" functions and do loops

# %% [markdown]
# This approach does both resampling and computation of metrics and applied them individually to each `full_symbol` using the loop.


# %%
def resample_calculate_twap_vwap_and_returns(df, resampling_freq):
    result = []
    full_symbol_list = df["full_symbol"].unique()
    for cc in full_symbol_list:
        # DataFrame with a specific `full_symbol`
        cc_df = df[df["full_symbol"] == cc]
        # Resample OHLCV data inside `full_symbol`-specific DataFrame.
        resampled_cc_df = cfinresa.resample_ohlcv_bars(
            cc_df, rule=resampling_freq
        )
        # Attach VWAP, TWAP.
        resampled_cc_df[["vwap", "twap"]] = cfinresa.compute_twap_vwap(
            cc_df, resampling_freq, price_col="close", volume_col="volume"
        )
        # Calculate returns.
        resampled_cc_df["vwap_rets"] = cfinretu.compute_ret_0(
            resampled_cc_df[["vwap"]], "pct_change"
        )
        resampled_cc_df["twap_rets"] = cfinretu.compute_ret_0(
            resampled_cc_df[["twap"]], "pct_change"
        )
        resampled_cc_df["log_rets"] = cfinretu.compute_ret_0(
            resampled_cc_df[["close"]], "log_rets"
        )
        # Add a column with `full_symbol` indication.
        resampled_cc_df["full_symbol"] = cc
        # Omit unnecesary columns.
        resampled_cc_df = resampled_cc_df.drop(columns=["open", "high", "low"])
        result.append(resampled_cc_df)
    final_df = pd.concat(result)
    return final_df


# %% run_control={"marked": false}
df_approach_1 = resample_calculate_twap_vwap_and_returns(
    data_hist, resampling_freq
)
df_approach_1.head(3)

# %% [markdown]
# # Approach 2 - Use pandas Multi-index

# %%
# Drop non numerical columns to apply computations.
data_hist_num = data_hist.drop(
    columns=["full_symbol", "knowledge_timestamp", "start_ts"]
)

# %% run_control={"marked": false}
# Convert historical data to multiindex format.
converted_data = dtfcorutil.convert_to_multiindex(data_hist_num, "asset_id")
converted_data.head(3)

# %%
# Resampling VWAP (besides potential errors). This implies hardcoded formula in a mix with resampling functions.
vwap_approach_2 = (converted_data["close"] * converted_data["volume"]).resample(
    resampling_freq
).mean() / converted_data["volume"].resample(resampling_freq).sum()
vwap_approach_2.head(3)

# %%
# Compute the ret_0 on all assets. You don't need a loop! But the data needs to be in the "right" format
# (the variable one wants to loop on needs to be the outermost in the levels, so one needs to do swaplevel).
rets_approach_2 = converted_data.swaplevel(axis=1).pct_change()
rets_approach_2.head(3)

# %% run_control={"marked": false}
# To go back to a flat index representation.
rets_approach_2.columns = ["".join(str(col)) for col in rets_approach_2.columns]
rets_approach_2.head(3)

# %% [markdown]
# # Approach 3 - Use Dataflow nodes

# %% [markdown]
# One node does resampling and VWAP, TWAP calculations, the other does returns.

# %%
# Configure the node to do the TWAP / VWAP resampling.
node_resampling_config = {
    "in_col_groups": [
        ("close",),
        ("volume",),
    ],
    "out_col_group": (),
    "transformer_kwargs": {
        "rule": resampling_freq,
        "resampling_groups": [
            ({"close": "close"}, "last", {}),
            (
                {
                    "close": "twap",
                },
                "mean",
                {},
            ),
            (
                {
                    "volume": "volume",
                },
                "sum",
                {"min_count": 1},
            ),
        ],
        "vwap_groups": [
            ("close", "volume", "vwap"),
        ],
    },
    "reindex_like_input": False,
    "join_output_with_input": False,
}
# Put the data in the DataFlow format (which is multi-index).
converted_data = dtfcorutil.convert_to_multiindex(data_hist, "asset_id")
# Create the node.
nid = "resample"
node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=cofinanc.resample_bars,
    **node_resampling_config,
)
# Compute the node on the data.
vwap_twap = node.fit(converted_data)
# Save the result.
vwap_twap_approach_3 = vwap_twap["df_out"]
vwap_twap_approach_3.head(3)

# %%
# Configure the node to calculate the returns.
node_returns_config = {
    "in_col_groups": [
        ("close",),
        ("vwap",),
        ("twap",),
    ],
    "out_col_group": (),
    "transformer_kwargs": {
        "mode": "pct_change",
    },
    "col_mapping": {
        "close": "close.ret_0",
        "vwap": "vwap.ret_0",
        "twap": "twap.ret_0",
    },
}
# Create the node that computes ret_0.
nid = "ret0"
node = dtfcore.GroupedColDfToDfTransformer(
    nid,
    transformer_func=cofinanc.compute_ret_0,
    **node_returns_config,
)
# Compute the node on the data.
rets = node.fit(vwap_twap_approach_3)
# Save the result.
vwap_twap_rets_approach_3 = rets["df_out"]
vwap_twap_rets_approach_3.head(3)
