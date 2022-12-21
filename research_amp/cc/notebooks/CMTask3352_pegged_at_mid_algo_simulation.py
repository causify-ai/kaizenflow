# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# The notebook simulates the performance of a "pegged-at-mid" trading algorithm.
#
# - Load the 1sec bid/ask data
# - Conduct a sanity check
# - Calculate the midpoint limit buy/sell prices
# - Aggregate to 5T and check the success of trades in historical data
#
# ```
# dataset_signature=periodic.airflow.downloaded_EOD.parquet.bid_ask.futures.v3.cryptochassis.binance.v1_0_0
# ```

# %%
# %load_ext autoreload
# %autoreload 2
import logging
from typing import Optional

import numpy as np
import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import research_amp.cc.algotrading as ramccalg

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load CryptoChassis data.

# %% [markdown]
# ## Initialize MarketData for `read_data` node

# %%
# Load the default config.
config = ramccalg.get_default_config()

# %%
# Load the historical IM client.
client = ramccalg.get_bid_ask_ImClient(config)
# Load the asset ids of the given universe.
asset_ids = ramccalg.get_universe(config)
# Set up MarketData for
market_data = ramccalg.get_market_data(config)

# %% [markdown]
# ## Initialize DAG

# %%
start_ts = config.get_and_mark_as_used(("market_data_config", "start_ts"))
end_ts = config.get_and_mark_as_used(("market_data_config", "end_ts"))

intervals = [(start_ts, end_ts)]


def _run_dag_node(dag):
    dag_runner = dtfcore.FitPredictDagRunner(dag)
    dag_runner.set_fit_intervals(intervals)
    fit_result_bundle = dag_runner.fit()
    df = fit_result_bundle.result_df
    return df


# %%
# Create an empty DAG.
dag = dtfcore.DAG(mode="strict")
dtfcore.draw(dag)

# %%
stage = "read_data"
ts_col_name = "end_ts"
multiindex_output = True
col_names_to_remove = []
node = dtfsys.HistoricalDataSource(
    stage,
    market_data,
    ts_col_name,
    multiindex_output,
    col_names_to_remove=col_names_to_remove,
)
dag.insert_at_head(node)
dtfcore.draw(dag)

# %% [markdown]
# ## Read data

# %%
df_original = _run_dag_node(dag)
df_original.shape
df_original.head(5)

# %%
# Drop multiindex in single-asset dataframes for human readability.
if len(asset_ids) < 2:
    df_flat = df_original.droplevel(1, axis=1)
else:
    df_flat = df_original.copy()

# %%
df_flat.head()

# %% [markdown]
# ## Sanity check

# %% [markdown]
# A quick sanity-check for the following:
# - What percentage of 1 sec bars are missing?
# - How often is bid_size = 0, ask_size = 0, volume=0?
# - How often is bid !< ask?
#

# %%
# Check for missing data.
df_flat.isna().sum()

# %%
# Check for zeroes.
(df_flat == 0).astype(int).sum(axis=1).sum()

# %% run_control={"marked": false}
# Check bid price !< ask price.
(df_flat["bid_price"] >= df_flat["ask_price"]).any().any()

# %%
df_flat.head()

# %%
# Check the gaps inside the time series.
index_as_series = df_flat.index.to_series()
freq = "S"
gaps_in_seconds = hpandas.find_gaps_in_time_series(
    index_as_series, start_ts, end_ts, freq
)
gaps_in_seconds = gaps_in_seconds.to_series()

# %%
gaps_percent = len(gaps_in_seconds) / (len(df_flat) + len(gaps_in_seconds)) * 100
average_gap = gaps_in_seconds.diff().mean()
print(
    f"Overall {len(gaps_in_seconds)} gaps were found, \
for {gaps_percent}%% of all seconds in the given period, for an average frequency of {average_gap}"
)

# %%
# Display gaps distribution by hour.
gaps_in_seconds.groupby(gaps_in_seconds.dt.hour).count().plot(kind="bar")

# %% [markdown]
# ### Commentary

# %% [markdown]
# - No NaNs or zeroes were found with a simple general check, there is no need for an in-depth look.
# - 575 gaps were found, that mostly concentrate between 0am and 5am.

# %% [markdown]
# ## Augment data with new features

# %%
# Append `mid` data.
# # (bid + ask) / 2.
bid_col = "bid_price"
ask_col = "ask_price"
bid_volume_col = "bid_size"
ask_volume_col = "ask_size"
requested_cols = ["mid"]
join_output_with_input = True
df_mid = cofinanc.process_bid_ask(
    df_flat,
    bid_col,
    ask_col,
    bid_volume_col,
    ask_volume_col,
    requested_cols=requested_cols,
    join_output_with_input=join_output_with_input,
)
df_mid.head(10)

# %%
print(df_mid.shape)
print(df_mid.index.min())
print(df_mid.index.max())

# %%
df_features = df_mid.copy()

# %%
df_features["ask_value"] = df_features["ask_price"] * df_features["ask_size"]
df_features["bid_value"] = df_features["bid_price"] * df_features["bid_size"]

# This is really high. 100m USD per hour on top of the book.
df_features[["bid_value", "ask_value"]].resample("1H").sum().plot()


# %%
def add_limit_order_prices(
    df: pd.DataFrame,
    mid_col_name: str,
    *,
    resample_freq="1T",
    passivity_factor=None,
    abs_spread=None,
):
    print(f"df initial={df.shape}")
    limit_buy_col = "limit_buy_price"
    limit_sell_col = "limit_sell_price"
    limit_buy_srs = df[mid_col_name]
    limit_buy_srs = limit_buy_srs.rename(limit_buy_col)
    limit_sell_srs = df[mid_col_name]
    limit_sell_srs = limit_sell_srs.rename(limit_buy_col)
    #
    if resample_freq:
        limit_buy_srs = limit_buy_srs.resample(resample_freq)
        limit_sell_srs = limit_sell_srs.resample(resample_freq)
    #
    limit_buy_srs = limit_buy_srs.mean().shift(1)
    limit_sell_srs = limit_sell_srs.mean().shift(1)
    #
    if abs_spread is not None and passivity_factor is None:
        limit_buy_srs = limit_buy_srs - abs_spread
        limit_sell_srs = limit_sell_srs + abs_spread
    elif passivity_factor is not None and abs_spread is None:
        limit_buy_srs = limit_buy_srs * (1 - passivity_factor)
        limit_sell_srs = limit_sell_srs * (1 - passivity_factor)
    #
    df_limit_price = pd.DataFrame()
    df_limit_price[limit_buy_col] = limit_buy_srs
    df_limit_price[limit_sell_col] = limit_sell_srs
    print(f"df_limit_price after resampling and shift={df_limit_price.shape}")
    df = df.merge(df_limit_price, right_index=True, left_index=True, how="outer")
    print(f"df after merge={df.shape}")
    #
    df[limit_buy_col] = df[limit_buy_col].ffill()
    df[limit_sell_col] = df[limit_sell_col].ffill()
    #
    df["is_buy"] = df["ask_price"] <= df[limit_buy_col]
    df["is_sell"] = df["bid_price"] >= df[limit_sell_col]
    return df


# %% run_control={"marked": false}
df_limit_order_prices = add_limit_order_prices(
    df_features, "mid", abs_spread=0.0001
)

# %%
df_limit_order_prices.head()

# %%
print(df_features.shape)


# %%
print(df_limit_order_prices.shape)


# %% run_control={"marked": true}
diff = df_limit_order_prices.index.difference(df_features.index)


# %%
df_limit_order_prices.loc[diff]


# %%
df_flat.loc[
    pd.Timestamp("2022-12-13 22:25:59-05:00") : pd.Timestamp(
        "2022-12-13 22:27:00-05:00"
    )
]

# %% [markdown]
# #### Commentary

# %% [markdown]
# As we have seen during the sanity check above, missing data can congregate around certain time points.
#
# For the 4 missing minutes were minutes where the initial second was missing, and then added in the function due to resampling.

# %%


def perform_spread_analysis(
    df, ask_price_col_name: str, bid_price_col_name: str, mid_price_col_name: str
) -> None:
    spread = df[ask_price_col_name] - df[bid_price_col_name]
    spread_in_bps = spread / df[mid_price_col_name] * 1e4
    spread_hist = spread.hist(bins=101)
    spread.plot()
    spread_in_bps.plot()
    # TODO(Danya): Display as subplots.


#     plt.show(spread_hist)
#     plt.show(spread_plot)
#     plt.show(spread_in_bps_plot)
#     display(spread_hist)
#     display()


# %%
perform_spread_analysis(df_limit_order_prices, "ask_price", "bid_price", "mid")


# %%
def plot_limit_orders(
    df,
    start_timestamp: Optional[pd.Timestamp] = None,
    end_timestamp: Optional[pd.Timestamp] = None,
) -> None:
    # TODO(Danya): Display as subplots.
    df[
        ["mid", "ask_price", "bid_price", "limit_buy_price", "limit_sell_price"]
    ].head(1000).plot()
    (df[["is_buy", "is_sell"]] * 1.0).head(1000).plot()


# %% [markdown]
# ## Resample to T_reprice

# %% run_control={"marked": true}
def compute_repricing_df(df, report_stats: bool):
    hdbg.dassert_is_subset(
        ["is_buy", "is_sell", "ask_price", "bid_price"], df.columns
    )
    # TODO(gp): ask_price -> buy_limit?
    df["exec_buy_price"] = df["is_buy"] * df["ask_price"]
    mask = ~df["is_buy"]
    df["exec_buy_price"][mask] = np.nan
    #
    df["exec_sell_price"] = df["is_sell"] * df["bid_price"]
    mask = ~df["is_sell"]
    df["exec_sell_price"][mask] = np.nan
    #
    if report_stats:
        print(
            "buy percentage at repricing freq: ",
            hprint.perc(df["is_buy"].sum(), df.shape[0]),
        )
        print(df["is_sell"].sum() / df.shape[0])
        #
        print(
            "exec_buy_price [%]=",
            hprint.perc(df["exec_buy_price"].isnull().sum(), df.shape[0]),
        )
        print(
            "exec_sell_price [%]=",
            hprint.perc(df["exec_sell_price"].isnull().sum(), df.shape[0]),
        )
    return df


# %%
reprice_df = compute_repricing_df(df_limit_order_prices, report_stats=True)

# %%
reprice_df.shape

# %%
reprice_df.head(5)


# %% [markdown]
# ## Resample to T_exec

# %%
def compute_execution_df(df, report_stats: bool):
    """
    Compute the number and volume of buy/sell executions.
    """
    exec_df = pd.DataFrame()
    # Count how many "buy" executions there were in an interval.
    exec_df["exec_buy_num"] = df["is_buy"].resample("5T").sum()
    exec_df["exec_buy_price"] = df["exec_buy_price"].resample("5T").mean()
    exec_df["exec_is_buy"] = exec_df["exec_buy_num"] > 0
    if report_stats:
        print(
            hprint.perc(
                exec_df["exec_is_buy"].sum(), exec_df["exec_is_buy"].shape[0]
            )
        )
    # Estimate the executed volume.
    exec_df["exec_buy_volume"] = (
        (df["ask_size"] * df["ask_price"] * df["is_buy"]).resample("5T").sum()
    )
    if report_stats:
        print("million USD per 5T=", exec_df["exec_buy_volume"].mean() / 1e6)
    # # Count how many "sell" executions there were in an interval.
    exec_df["exec_sell_num"] = df["is_sell"].resample("5T").sum()
    exec_df["exec_sell_price"] = df["exec_sell_price"].resample("5T").mean()
    exec_df["exec_is_sell"] = exec_df["exec_sell_num"] > 0
    if report_stats:
        print(
            "exec_is_sell [%]=",
            hprint.perc(
                exec_df["exec_is_sell"].sum(), exec_df["exec_is_sell"].shape[0]
            ),
        )

    # Estimate the executed volume.
    exec_df["exec_sell_volume"] = (
        (df["bid_size"] * df["bid_price"] * df["is_sell"]).resample("5T").sum()
    )
    if report_stats:
        print("million USD per 5T=", exec_df["exec_sell_volume"].mean() / 1e6)
    #
    exec_df["mid"] = df["mid"]
    return exec_df


# %%
exec_df = compute_execution_df(reprice_df, report_stats=True)
exec_df.head(5)


# %% [markdown]
# ## Compare to benchmark price.

# %% run_control={"marked": true}
def compute_benchmark_stats(df):
    df["twap_mid_price"] = df["mid"].resample("5T").mean()
    df[["twap_mid_price", "exec_sell_price", "exec_buy_price"]].head(1000).plot()
    return df


# %%
benchmark_df = compute_benchmark_stats(exec_df)

# %%
slippage = exec_df[["twap_mid_price", "exec_sell_price", "exec_buy_price"]]

slippage["sell_slippage_bps"] = (
    (exec_df["exec_sell_price"] - exec_df["twap_mid_price"])
    / exec_df["twap_mid_price"]
    * 1e4
)

# slippage = df["twap_mid_price"] /

slippage["sell_slippage_bps"].hist(bins=21)

print("sell_slippage_bps.mean=", slippage["sell_slippage_bps"].mean())
print("sell_slippage_bps.median=", slippage["sell_slippage_bps"].median())

# %% [markdown]
# ### Commentary

# %% [markdown]
# The quick look into the rate of successful trades indicated that for the given asset (`ADA/USDT`) and the date the successful "buy" order can be met for 16% of the time and a "sell" order is not met at all.
