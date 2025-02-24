# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hparquet as hparque
import helpers.hprint as hprint
import im_v2.ig.data.client.compute_stats_from_tiles as imvidccsft

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load TAQ bar metadata

# %%
tile_dict = {
    "dir_name": "/cache/tiled.bar_data.top100.2010_2020/",
    "asset_id_col": "igid",
}
tile_config = cconfig.Config.from_dict(tile_dict)

# %%
parquet_tile_analyzer = dtfmod.ParquetTileAnalyzer()
parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
    tile_config["dir_name"]
)

# %%
parquet_tile_analyzer.compute_metadata_stats_by_asset_id(parquet_tile_metadata)

# %%
parquet_tile_analyzer.compute_universe_size_by_time(parquet_tile_metadata)

# %%
asset_ids = parquet_tile_metadata.index.levels[0].to_list()
display(asset_ids)

# %% [markdown]
# # Load a single-asset tile

# %%
single_asset_tile = next(
    hparque.yield_parquet_tiles_by_assets(
        tile_config["dir_name"],
        asset_ids[0:1],
        tile_config["asset_id_col"],
        1,
        None,
    )
)

# %%
single_tile_df = dtfmod.process_parquet_read_df(
    single_asset_tile, tile_config["asset_id_col"]
)

# %%
single_tile_df.columns.levels[0]

# %%
single_tile_df.head(3)

# %%
one_asset_df = single_tile_df.droplevel(level=1, axis=1)

# %%
one_asset_df.head(3)

# %% [markdown]
# # Compute stats

# %%
df = imvidccsft.compute_stats(one_asset_df)

# %%
df.columns.to_list()

# %%
df.head(3)

# %% [markdown]
# # Plot

# %%
# This ratio computes (close - bid_ask_midpoint) / bid_ask_spread.
df["close_execution_spread_ratio"].clip(lower=0, upper=1.0).groupby(
    lambda x: x.time()
).mean().plot()

# %%
# The mode is near 0.5, indicating crossing the spread.
# Note, though, that spreads may be artificially wider immediately following an execution.
# The second most common value is near 0.0 (midpoint).
df["close_execution_spread_ratio"].clip(lower=-0.2, upper=1.0).hist(bins=31)

# %%
# Close price vs last bid-ask midpoint price, in dollars.
# Note that peaks near 0, 0.005, 0.01, and at successive half-cent peaks.
(one_asset_df["close"] - df["bid_ask_midpoint"]).abs().clip(upper=0.05).hist(
    bins=31
)

# %%
# The last bid-ask spread in dollars (use as a reference in interpreting trade close prices vs midpoint).
df["bid_ask_spread_dollars"].clip(lower=0.0, upper=0.2).hist()

# %%
# The value (close - open) / (high - low).
df["trade_drift_to_range"].hist(bins=31)

# %%
# The value (2 * close - high - low) / (high - low). A value near +/- 1 indicates that the close price is close to the high/low.
df["trade_stochastic"].hist(bins=31)

# %%
# The "inner range" is ask_low - bid_high.
bid_ask_inner_range_crosses = (df["bid_ask_inner_range"] < 0).sum()
bid_ask_inner_range_no_crosses = (df["bid_ask_inner_range"] >= 0).sum()
bid_ask_inner_range_cross_ratio = bid_ask_inner_range_crosses / (
    bid_ask_inner_range_crosses + bid_ask_inner_range_no_crosses
)
display(bid_ask_inner_range_cross_ratio)

# %% run_control={"marked": true}
# We calculate "VWAP" prices from quotes and then derive the midpoint. A "cross" means a high or low crossed the quote VWAP midpoint.
ig_bar_bid_ask_vwap_midpoint = 0.5 * (
    df["ig_bar_bid_vwap"] + df["ig_bar_ask_vwap"]
)
display(
    "Num ask midpoint crosses = %d"
    % (one_asset_df["ask_low"] < ig_bar_bid_ask_vwap_midpoint).sum()
)
display(
    "Num bid midpoint crosses = %d"
    % (one_asset_df["bid_high"] > ig_bar_bid_ask_vwap_midpoint).sum()
)

# %% [markdown]
# # Resample

# %%
resampled_df = imvidccsft.resample_taq_bars(one_asset_df, "15T")

# %%
resampled_df.head(3)

# %%
resampled_df_stats = imvidccsft.compute_stats(resampled_df)

# %%
(
    resampled_df_stats["ig_bar_trade_vwap"] - resampled_df["close_vwap"]
).abs().groupby(lambda x: x.time()).mean().plot()

# %% [markdown]
# # Midpoint crossings

# %%
df.head(3)

# %%
# Place an order at midpoint every 5 minutes (using midpoint from end of bar).
# In the next 5 minutes, does bid cross the midpoint? Ask?

# %%
small_df = one_asset_df[["bid", "ask", "close"]]

# %%
small_df["midpoint"] = 0.5 * (small_df["bid"] + small_df["ask"])
small_df["quoted_spread"] = small_df["ask"] - small_df["bid"]

# %%
r_df = cofinan.resample_bars(
    gp_df,
    "5T",
    [
        (
            {
                "bid": "max_bid",
            },
            "max",
            {},
        ),
        (
            {
                "ask": "min_ask",
            },
            "min",
            {},
        ),
        (
            {
                "midpoint": "midpoint",
                "quoted_spread": "quoted_spread",
            },
            "last",
            {},
        ),
    ],
    [],
)
r_df = cofinanc.set_non_ath_to_nan(r_df).dropna()

# %%
r_df[["midpoint_lag1"]] = r_df[["midpoint"]].shift(1)
r_df[["quoted_spread_lag1"]] = r_df[["quoted_spread"]].shift(1)

# %%
r_df

# %%
(r_df["max_bid"] >= r_df["midpoint_lag1"]).mean()

# %%
(r_df["min_ask"] <= r_df["midpoint_lag1"]).mean()


# %%
def compute_probability_of_execution(df, k):
    half_quoted_spread_lag1 = 0.5 * df["quoted_spread_lag1"]
    bid_cross = df["max_bid"] >= (
        df["midpoint_lag1"] + half_quoted_spread_lag1 * k
    )
    ask_cross = df["min_ask"] <= (
        df["midpoint_lag1"] - half_quoted_spread_lag1 * k
    )
    val = (bid_cross | ask_cross).mean()
    return val


# %%
vals = {}
for k in range(-1, 2):
    vals[k] = compute_probability_of_execution(r_df, k)
vals = pd.Series(vals)
display(vals)

# %%
import core.plotting.plotting_utils as cplpluti

# %%
cplpluti.configure_notebook_for_presentation()

# %%
vals.plot(
    ylim=(0, 1),
    xlim=(-1, 1),
    xlabel="aggresiveness (units of half spread)",
    ylabel="probability of execution",
)

# %%
bid_cross.sum()
