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
#
# Use bid-ask data to analyze and simulate trading execution quality.

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import numpy as np
import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import core.plotting as coplotti
import core.statistics as costatis
import dataflow.core as dtfcore
import dataflow.pipelines.execution.execution_pipeline as dtfpexexpi
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
import oms.broker.ccxt.ccxt_execution_quality as obccexqu
import oms.broker.ccxt.ccxt_logger as obcccclo

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
# When running manually, specify the path to the config to load config from file,
# for e.g., `.../reconciliation_notebook/fast/result_0/config.pkl`.
config_file_name = None
config = cconfig.get_notebook_config(config_file_name)
if config is None:
    system_log_dir = "/shared_data/ecs/test/system_reconciliation/C12a/prod/20240226_103300.20240226_113000/system_log_dir.manual/process_forecasts"
    # Use "logged_during_experiment" to use data logged from inside broker during the experiment.
    # (In full system run might result in gaps in data if no trades were generated for one or more bars).
    bid_ask_data_source = "logged_during_experiment"
    bar_duration = "3T"
    test_asset_id = 1464553467
    config_dict = {
        "meta": {"bid_ask_data_source": bid_ask_data_source},
        "universe": {"test_asset_id": test_asset_id},
        "execution_parameters": {"bar_duration": bar_duration},
        "system_log_dir": system_log_dir,
    }
    config = cconfig.Config.from_dict(config_dict)
print(config)

# %%
system_log_dir = config["system_log_dir"]
bar_duration = config.get_and_mark_as_used(
    ("execution_parameters", "bar_duration")
)
test_asset_id = config.get_and_mark_as_used(("universe", "test_asset_id"))
id_col = "asset_id"
# TODO(Sonaal): This should become an attribute for order.
child_order_execution_freq = "1T"
resample_freq = "100ms"

# %%
ccxt_log_reader = obcccclo.CcxtLogger(system_log_dir)
data = ccxt_log_reader.load_all_data(
    convert_to_dataframe=True, abort_on_missing_data=False
)

# %%
ccxt_log_reader._bid_ask_full_dir

# %%
# Print the Broker config.
if "broker_config" in data:
    print(hprint.to_pretty_str(data["broker_config"]))
else:
    _LOG.warning("broker_config file not present in %s", system_log_dir)

# %%
# Print the used Config, if any.
experiment_config = obcccclo.load_config_for_execution_analysis(system_log_dir)
print(experiment_config)

# %%
# Colums containing price data for analysis.
active_cols = ["buy_limit_order_price", "buy_trade_price"]

# %% [markdown]
# # Load data

# %% [markdown]
# ## Load CCXT data

# %%
ccxt_order_response_df = data["ccxt_order_responses"]
ccxt_executed_trades_df = data["ccxt_trades"]

# %%
ccxt_order_response_df.head(3)

# %%
ccxt_executed_trades_df.head(3)

# %%
oms_child_order_df = data["oms_child_orders"]

# %%
oms_child_order_df.iloc[oms_child_order_df["latest_bid_price"].argmax()][
    "extra_params"
]["stats"]

# %% run_control={"marked": true}
# Check if `test_asset_id` is present
# If the `test_asset_id` is not present, choose the first traded asset.
traded_asset_ids = sorted(set(oms_child_order_df["asset_id"]))
if test_asset_id not in traded_asset_ids:
    test_asset_id = traded_asset_ids[0]
_LOG.info("test_asset_id=%s", test_asset_id)

# %% [markdown]
# ## Aggregate CCXT data

# %%
# Aggregated executed trades (fills) by bar.
executed_trades_prices = obccagfu.compute_buy_sell_prices_by_bar(
    ccxt_executed_trades_df, bar_duration, groupby_id_col=id_col
)

# %%
# Get execution event timestamps by child order.
test_asset_orders = (
    obcccclo.process_child_order_timestamps_and_prices_for_single_asset(
        oms_child_order_df, ccxt_executed_trades_df, test_asset_id, resample_freq
    )
)

# %%
test_asset_events = test_asset_orders.sort_index(axis=0)

# %%
test_asset_events.head(10)

# %% [markdown]
# ## Load bid-ask data


# %%
def get_data():
    """
    The simulation section of the notebook contains a definition of a DAG with
    a FunctionDataSource source node which requires a function rather than an
    object, so this function returns an object built inside the notebook.
    """
    return bid_ask


# %%
# TODO(Paul): Refine the cuts around the first and last bars.
start_timestamp = ccxt_order_response_df["order_update_datetime"].min()
_LOG.info("start_timestamp=%s", start_timestamp)
end_timestamp = ccxt_executed_trades_df["datetime"].max()
_LOG.info("end_timestamp=%s", end_timestamp)

# %%
bid_ask, duplicated_rows = obccagfu.load_bid_ask_data(
    start_timestamp,
    end_timestamp,
    ccxt_log_reader,
    config["meta"]["bid_ask_data_source"],
    executed_trades_prices.columns.levels[1],
    child_order_execution_freq,
)

if duplicated_rows is not None:
    display(duplicated_rows)

# %% [markdown]
# ## Load OHLCV data

# %%
# We get the end timestamp from ccxt_trades_df which is not the exact time at which the run was completed.
# This created misalignment in the graphs of bid/ask data and OHLCV. Hence we rectify this by re-defining
# end_timestamp based on the bid/ask data.
actual_ohlcv_end_timestamp = bid_ask.index.max().round("min")

# %%
ohlcv_bar_duration = bar_duration
db_stage = data["broker_config"]["stage"]
# Get prod `MarketData`.
market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(
    [test_asset_id], db_stage=db_stage
)
# Load and resample OHLCV data.
ohlcv_bars = dtfamsysc.load_and_resample_ohlcv_data(
    market_data,
    start_timestamp,
    actual_ohlcv_end_timestamp,
    ohlcv_bar_duration,
)
ohlcv_bars.head(3)

# %%
ohlcv_price_df = {
    "high": ohlcv_bars["high"],
    "low": ohlcv_bars["low"],
}
ohlcv_price_df = pd.concat(ohlcv_price_df, axis=1)
# Slice data for a test asset id.
test_asset_slice_ohlcv = cofinanc.get_asset_slice(ohlcv_price_df, test_asset_id)
test_asset_slice_ohlcv.head(3)

# %% [markdown]
# # Plot bid/ask and OHLCV data

# %%
bid_ask.head(3)

# %%
bid_ask["bid_price"][test_asset_id].tail(10000).plot()

# %%
test_asset_tob = cofinanc.get_asset_slice(bid_ask, test_asset_id)

# %%
test_asset_tob[["ask_price", "bid_price"]].plot()

# %%
test_asset_tob[["ask_size", "bid_size"]].plot()

# %%
# Plot bid-ask prices together with high and low prices.
test_asset_slice_tob_ohlcv = (
    pd.concat([test_asset_tob, test_asset_slice_ohlcv]).sort_index().bfill()
)
#
test_asset_slice_tob_ohlcv[["ask_price", "bid_price", "high", "low"]].plot()

# %%
pd.merge(
    cofinanc.get_asset_slice(
        test_asset_events, test_asset_id, strictly_increasing=False
    ),
    test_asset_tob,
    left_index=True,
    right_index=True,
    how="inner",
).dropna(subset=["event"])

# %% [markdown]
# # Replay limit orders and simulate trades
#
# - Use actual limit prices seen in actual execution
# - Simulate execution using actual limit prices and bid-ask data
# - Compare simulated execution to actual execution

# %% [markdown]
# ## Extract the actual limit orders

# %%
bid_ask.columns.levels[1]

# %%
oms_child_order_df_restricted = oms_child_order_df[
    oms_child_order_df["asset_id"].isin(bid_ask.columns.levels[1])
]
oms_child_order_df_restricted.head(3)

# %%
# Forward fill to represent the time-in-force of the underlying order.
limit_prices = obccexqu.get_limit_order_price(oms_child_order_df_restricted)
limit_prices.head(3)

# %%
buy_order_num = np.sign(limit_prices["buy_limit_order_price"]).abs().cumsum()
sell_order_num = np.sign(limit_prices["sell_limit_order_price"]).abs().cumsum()

# %%
limit_prices = pd.concat(
    {
        "buy_limit_order_price": limit_prices["buy_limit_order_price"],
        "sell_limit_order_price": limit_prices["sell_limit_order_price"],
        "buy_order_num": buy_order_num,
        "sell_order_num": sell_order_num,
    },
    axis=1,
).ffill(limit=59)

# %% [markdown]
# ## Join limit orders with bid-ask data and simulate trades

# %%
in_df = pd.concat([limit_prices, bid_ask], axis=1)
in_df.head(3)

# %%
node = dtfcore.GroupedColDfToDfTransformer(
    "estimate_limit_order_execution",
    transformer_func=cofinanc.estimate_limit_order_execution,
    **{
        "in_col_groups": [
            ("bid_price",),
            ("ask_price",),
            ("buy_limit_order_price",),
            ("sell_limit_order_price",),
            ("buy_order_num",),
            ("sell_order_num",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "bid_col": "bid_price",
            "ask_col": "ask_price",
            "buy_limit_price_col": "buy_limit_order_price",
            "sell_limit_price_col": "sell_limit_order_price",
            "buy_order_num_col": "buy_order_num",
            "sell_order_num_col": "sell_order_num",
        },
    },
)

# %%
simulated_execution_df = node.fit(in_df)["df_out"]

# %%
simulated_execution_df.columns.levels[0].to_list()

# %%
test_asset_exec = cofinanc.get_asset_slice(simulated_execution_df, test_asset_id)
test_asset_exec.loc[~test_asset_exec["buy_trade_price"].isna()][
    [
        "buy_trade_price",
        "buy_limit_order_price",
        "buy_order_num",
        "bid_price",
        "ask_price",
    ]
]

# %%
simulated_execution_df["buy_trade_price"].resample(
    "5T", closed="right", label="right"
).mean()

# %%
test_asset_slice = cofinanc.get_asset_slice(simulated_execution_df, test_asset_id)

# %%
test_asset_slice[active_cols].plot()

# %%
test_asset_slice["buy_trade_price"].ffill(limit=59).plot()

# %% [markdown]
# ## Compute simulated trade execution quality against bid-ask benchmarks

# %%
simulated_execution_quality_node = dtfcore.GroupedColDfToDfTransformer(
    "simulated_execution_quality",
    transformer_func=cofinanc.compute_bid_ask_execution_quality,
    **{
        "in_col_groups": [
            ("buy_trade_price",),
            ("sell_trade_price",),
            ("bid_price",),
            ("ask_price",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "bid_col": "bid_price",
            "ask_col": "ask_price",
            "buy_trade_price_col": "buy_trade_price",
            "sell_trade_price_col": "sell_trade_price",
        },
    },
)

# %%
simulated_execution_quality_df = simulated_execution_quality_node.fit(
    simulated_execution_df
)["df_out"]

# %%
simulated_execution_quality_df.columns.levels[0].to_list()

# %%
test_asset_slice = cofinanc.get_asset_slice(
    simulated_execution_quality_df, test_asset_id
)
test_asset_slice[active_cols].dropna(how="all")

# %%
col = "buy_trade_midpoint_slippage_bps"
coplotti.plot_boxplot(simulated_execution_quality_df[col], "by_col", ylabel=col)

# %%
simulated_execution_quality_df["buy_trade_midpoint_slippage_bps"].unstack().hist(
    bins=31
)

# %%
col = "sell_trade_midpoint_slippage_bps"
coplotti.plot_boxplot(simulated_execution_quality_df[col], "by_col", ylabel=col)

# %%
simulated_execution_quality_df["sell_trade_midpoint_slippage_bps"].unstack().hist(
    bins=31
)

# %%
costatis.compute_moments(
    simulated_execution_quality_df["buy_trade_midpoint_slippage_bps"].unstack()
)

# %%
costatis.compute_moments(simulated_execution_quality_df["spread_bps"].unstack())

# %% [markdown]
# ## Compare actual trade prices to simulated trade prices

# %%
actual_vs_sim_trade_price_resampling_freq = "1T"

# %%
# The "8s" is an empirically-derived estimate of order delay.
simulated_execution_df["sell_limit_order_price"].resample(
    actual_vs_sim_trade_price_resampling_freq,
    closed="right",
    label="right",
    offset="8s",
).mean().head(3)

# %%
executed_trades_prices = obccagfu.compute_buy_sell_prices_by_bar(
    ccxt_executed_trades_df,
    actual_vs_sim_trade_price_resampling_freq,
    offset="8s",
    groupby_id_col="asset_id",
)
executed_trades_prices.head(3)

# %%
resampled_simulated_execution_df = simulated_execution_df.resample(
    actual_vs_sim_trade_price_resampling_freq,
    closed="right",
    label="right",
    offset="8s",
).mean()
resampled_simulated_execution_df.head(3)

# %%
actual_executed_trades_prices = obccagfu.compute_buy_sell_prices_by_bar(
    ccxt_executed_trades_df, "1s", offset="0s", groupby_id_col="asset_id"
)

# %%
actual_vs_sim_trade_price_resampling_freq = "5T"

# %%
simulated_and_actual_trade_price_df = obccagfu.combine_sim_and_actual_trades(
    simulated_execution_df,
    ccxt_executed_trades_df,
    actual_vs_sim_trade_price_resampling_freq,
    offset="8s",
)
simulated_and_actual_trade_price_df.head(3)

# %%
cofinanc.get_asset_slice(simulated_and_actual_trade_price_df, test_asset_id)[
    ["actual_buy_trade_price", "simulated_buy_trade_price"]
].dropna(how="all")

# %%
cofinanc.get_asset_slice(simulated_and_actual_trade_price_df, test_asset_id)[
    ["actual_sell_trade_price", "simulated_sell_trade_price"]
].dropna(how="all")

# %%
execution_quality_node = dtfcore.GroupedColDfToDfTransformer(
    "execution_quality",
    transformer_func=cofinanc.compute_ref_price_execution_quality,
    **{
        "in_col_groups": [
            ("actual_buy_trade_price",),
            ("actual_sell_trade_price",),
            ("simulated_buy_trade_price",),
            ("simulated_sell_trade_price",),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "buy_trade_reference_price_col": "simulated_buy_trade_price",
            "sell_trade_reference_price_col": "simulated_sell_trade_price",
            "buy_trade_price_col": "actual_buy_trade_price",
            "sell_trade_price_col": "actual_sell_trade_price",
        },
    },
)

# %%
sim_vs_actual_execution_quality_df = execution_quality_node.fit(
    simulated_and_actual_trade_price_df
)["df_out"]

# %%
sim_vs_actual_execution_quality_df.columns.levels[0].to_list()

# %%
cofinanc.get_asset_slice(sim_vs_actual_execution_quality_df, test_asset_id)

# %%
col = "buy_trade_slippage_bps"
coplotti.plot_boxplot(
    sim_vs_actual_execution_quality_df[col], "by_col", ylabel=col
)

# %%
sim_vs_actual_execution_quality_df["buy_trade_slippage_bps"].unstack().hist(
    bins=31
)

# %%
col = "sell_trade_slippage_bps"
coplotti.plot_boxplot(
    sim_vs_actual_execution_quality_df[col], "by_col", ylabel=col
)

# %%
sim_vs_actual_execution_quality_df["sell_trade_slippage_bps"].unstack().hist(
    bins=31
)


# %% [markdown]
# # Simulate limit order generation and trades
#
# - Specify buy/sell aggressiveness parameters
# - Specify repricing frequency and time-in-force
# - Simulate average execution prices and percentage of bars filled


# %%
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
config["resample", "transformer_kwargs", "rule"] = "1T"
config["resample", "transformer_kwargs", "resample_kwargs", "offset"] = "8s"
config[
    "generate_limit_orders", "transformer_kwargs", "buy_spread_frac_offset"
] = 0.45
config[
    "generate_limit_orders", "transformer_kwargs", "sell_spread_frac_offset"
] = -0.45
config["generate_limit_orders", "transformer_kwargs", "subsample_freq"] = "60s"
config["generate_limit_orders", "transformer_kwargs", "freq_offset"] = "9s"
config["generate_limit_orders", "transformer_kwargs", "ffill_limit"] = 59

#
_LOG.debug("config after patching=%s", config)
dag = dag_builder.get_dag(config)

# %%
bid_ask_sim_flow_df = dag.run_leq_node(
    "compute_trade_vs_limit_execution_quality", "fit"
)["df_out"]

# %%
bid_ask_sim_flow_df.columns.levels[0].to_list()

# %%
test_asset_df = cofinanc.get_asset_slice(bid_ask_sim_flow_df, test_asset_id)
test_asset_df[
    [
        "bid_price",
        "ask_price",
        "buy_order_num",
        "buy_trade_price",
        "buy_limit_order_price",
    ]
]

# %%
bid_ask_sim_flow_df.head(3)

# %%
cofinanc.get_asset_slice(bid_ask_sim_flow_df, test_asset_id)[
    ["buy_trade_price", "sell_trade_price"]
].plot()

# %%
cofinanc.get_asset_slice(bid_ask_sim_flow_df, test_asset_id).head(3)

# %%
test_asset_simulated_prices = cofinanc.get_asset_slice(
    bid_ask_sim_flow_df, test_asset_id
)
test_asset_simulated_prices[active_cols].dropna(how="all").plot()

# %%
costatis.compute_moments(
    bid_ask_sim_flow_df["buy_trade_limit_slippage_bps"].unstack()
)

# %%
costatis.compute_moments(
    bid_ask_sim_flow_df["sell_trade_limit_slippage_bps"].unstack()
)

# %% [markdown]
# # Compare simulated limit orders and actual limit orders

# %%
simulated_buy_limits = bid_ask_sim_flow_df["buy_limit_order_price"]
simulated_buy_limits.head(3)

# %%
actual_buy_limits = in_df["buy_limit_order_price"]
actual_buy_limits.head(3)

# %%
lim_vs_lim = pd.concat(
    {
        "simulated_buy_limit": simulated_buy_limits,
        "actual_buy_limit": actual_buy_limits.resample(
            "1T", offset="8s", closed="right", label="right"
        ).mean(),
    },
    axis=1,
)

# %%
lim_vs_lim.columns.levels[1]

# %%
cofinanc.get_asset_slice(lim_vs_lim, lim_vs_lim.columns.levels[1][1]).dropna(
    how="all"
).plot()

# %%
cofinanc.get_asset_slice(lim_vs_lim, lim_vs_lim.columns.levels[1][0]).dropna(
    how="all"
).plot()

# %%
