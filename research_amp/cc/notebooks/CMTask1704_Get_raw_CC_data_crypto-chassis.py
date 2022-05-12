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

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import matplotlib.pyplot as plt
import pandas as pd

import core.config.config_ as cconconf
import core.finance.resampling as cfinresa
import core.finance.tradability as cfintrad
import core.plotting.normality as cplonorm
import core.plotting.plotting_utils as cplpluti
import dataflow.system.source_nodes as dtfsysonod
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
def get_cmtask1704_config_crypto_chassis() -> cconconf.Config:
    """
    Get config, that specifies params for getting raw data from `crypto
    chassis`.
    """
    config = cconconf.Config()
    # Load parameters.
    # config.add_subconfig("load")
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["full_symbols"] = ["binance::BNB_USDT", "binance::BTC_USDT"]
    config["data"]["start_date"] = pd.Timestamp("2022-01-01", tz="UTC")
    config["data"]["end_date"] = pd.Timestamp("2022-02-01", tz="UTC")
    # Transformation parameters.
    config.add_subconfig("transform")
    config["transform"]["resampling_rule"] = "5T"
    config["transform"]["rets_type"] = "pct_change"
    return config


# %%
config = get_cmtask1704_config_crypto_chassis()
print(config)

# %% [markdown]
# # Load OHLCV data from `crypto-chassis`

# %%
# TODO(Max): Refactor the loading part once #1766 is implemented.

# %% [markdown]
# ## Data demonstration

# %%
# Read from crypto_chassis directly.
# full_symbols = config["data"]["full_symbols"]
# start_date = config["data"]["start_date"]
# end_date = config["data"]["end_date"]
# ohlcv_cc = raccchap.read_crypto_chassis_ohlcv(full_symbols, start_date, end_date)

# Read saved 1 month of data.
ohlcv_cc = pd.read_csv("/shared_data/cc_ohlcv.csv", index_col="timestamp")
ohlcv_cc.index = pd.to_datetime(ohlcv_cc.index)
ohlcv_cc.head(3)

# %% [markdown]
# # Calculate VWAP, TWAP and returns in `Dataflow` style

# %%
# VWAP, TWAP transformation.
resampling_rule = config["transform"]["resampling_rule"]
vwap_twap_df = cfintrad.calculate_vwap_twap(ohlcv_cc, resampling_rule)

# Returns calculation.
rets_type = config["transform"]["rets_type"]
vwap_twap_rets_df = cfintrad.calculate_returns(vwap_twap_df, rets_type)

# %% run_control={"marked": false}
# Show the snippet.
vwap_twap_rets_df.head(3)

# %% run_control={"marked": false}
# Stats and vizualisation to check the outcomes.
bnb_ex = vwap_twap_rets_df.swaplevel(axis=1)
bnb_ex = bnb_ex["binance::BNB_USDT"][["close.ret_0", "twap.ret_0", "vwap.ret_0"]]
display(bnb_ex.corr())
bnb_ex.plot()

# %% [markdown]
# # Bid-ask data

# %%
# TODO(Max): Refactor the loading part once #1766 is implemented.

# %%
# Read from crypto_chassis directly.
# Specify the params.
# full_symbols = config["data"]["full_symbols"]
# start_date = config["data"]["start_date"]
# end_date = config["data"]["end_date"]
# Get the data.
# bid_ask_df = raccchap.read_and_resample_bid_ask_data(
#    full_symbols, start_date, end_date, "5T"
# )
# bid_ask_df.head(3)

# Read saved 1 month of data.
bid_ask_df = pd.read_csv("/shared_data/bid_ask_data.csv", index_col="timestamp")
bid_ask_df.index = pd.to_datetime(bid_ask_df.index)
bid_ask_df.head(3)

# %%
# Calculate bid-ask metrics.
bid_ask_df = cfintrad.calculate_bid_ask_statistics(bid_ask_df)
bid_ask_df.tail(3)

# %% [markdown]
# ## Unite VWAP, TWAP, rets statistics with bid-ask stats

# %%
final_df = pd.concat([vwap_twap_rets_df, bid_ask_df], axis=1)
final_df.tail(3)

# %%
# Metrics visualizations.
final_df[["relative_spread_bps"]].plot()

# %% [markdown]
# ## Compute the distribution of (return - spread)

# %%
# Choose the specific `full_symbol`.
df_bnb = final_df.swaplevel(axis=1)["binance::BNB_USDT"]
df_bnb.head(3)

# %%
# Calculate (|returns| - spread) and display descriptive stats.
df_bnb["ret_spr_diff"] = abs(df_bnb["close.ret_0"]) - (
    df_bnb["quoted_spread"] / df_bnb["close"]
)
display(df_bnb["ret_spr_diff"].describe())

# %%
# Visualize the result
cplonorm.plot_qq(df_bnb["ret_spr_diff"])

# %% [markdown]
# # Deep dive into quantitative statistics #1805

# %% [markdown]
# ## How much liquidity is available at the top of the book?

# %%
# liquidity_stats = (final_df["ask_size"] * final_df["ask_price"]).median()
liquidity_stats = final_df["ask_value"].median()
display(liquidity_stats)
cplpluti.plot_barplot(liquidity_stats)


# %% [markdown]
# ## Is the quoted spread constant over the day?

# %% [markdown]
# ### One symbol

# %%
def calculate_overtime_quantities(
    df_sample, full_symbol, resampling_rule, num_stds=1, plot_results=True
):
    # Choose specific `full_symbol`.
    data = df_sample.swaplevel(axis=1)[full_symbol]
    # Resample the data.
    resampler = cfinresa.resample(data, rule=resampling_rule)
    # Quoted spread.
    quoted_spread = resampler["quoted_spread"].mean()
    # Volatility of returns inside `buckets`.
    rets_vix = resampler["close.ret_0"].std().rename("rets_volatility")
    # Volume over time.
    volume = resampler["volume"].sum().rename("trading_volume")
    # Relative spread (in bps).
    rel_spread_bps = resampler["relative_spread_bps"].mean()
    # Bid / Ask value.
    bid_value = resampler["bid_value"].sum()
    ask_value = resampler["ask_value"].sum()
    # Tradability = abs(ret) / spread_bps.
    tradability = resampler["close.ret_0"].mean().abs() / rel_spread_bps
    tradability = tradability.rename("tradability")
    # Collect all the results.
    df = pd.concat(
        [
            quoted_spread,
            rets_vix,
            volume,
            rel_spread_bps,
            bid_value,
            ask_value,
            tradability,
        ],
        axis=1,
    )
    # Integrate time.
    df["time"] = df.index.time
    # Construct value curves over time.
    if plot_results:
        # Get rid of `time`.
        for cols in df.columns[:-1]:
            # Calculate man and std over the daytime.
            time_grouper = df.groupby("time")
            mean = time_grouper[cols].mean()
            std = time_grouper[cols].std()
            # Plot the results.
            fig = plt.figure()
            fig.suptitle(f"{cols} over time", fontsize=20)
            plt.ylabel(cols, fontsize=16)
            (mean + num_stds * std).plot(color="blue")
            mean.plot(lw=2, color="black")
    return df


# %%
full_symbol = "binance::BNB_USDT"  # "binance::BTC_USDT"
resample_rule_stats = "10T"

stats_df = calculate_overtime_quantities(
    final_df, full_symbol, resample_rule_stats
)
display(stats_df.head(3))


# %% [markdown]
# ### Multiple Symbols

# %%
def calculate_overtime_quantities_multiple_symbols(
    df_sample, full_symbols, resampling_rule, plot_results=True
):
    result = []
    # Calculate overtime stats for each `full_symbol`.
    for symb in full_symbols:
        df = calculate_overtime_quantities(
            df_sample, symb, resampling_rule, plot_results=False
        )
        df["full_symbol"] = symb
        result.append(df)
    mult_stats_df = pd.concat(result)
    # Convert to multiindex.
    mult_stats_df_conv = dtfsysonod._convert_to_multiindex(
        mult_stats_df, "full_symbol"
    )
    # Integrate time inside the day.
    mult_stats_df_conv["time_inside_days"] = mult_stats_df_conv.index.time
    # Compute the median value for all quantities.
    mult_stats_df_conv = mult_stats_df_conv.groupby("time_inside_days").agg(
        "median"
    )
    # Plot the results.
    if plot_results:
        # Get rid of `time` and `full_symbol`.
        for cols in mult_stats_df.columns[:-2]:
            mult_stats_df_conv[cols].plot(
                title=f"{cols} median over time", fontsize=12
            )
    return mult_stats_df_conv


# %% run_control={"marked": false}
full_symbols = config["data"]["full_symbols"]
resample_rule_stats = "10T"

stats_df_mult_symbols = calculate_overtime_quantities_multiple_symbols(
    final_df, full_symbols, resample_rule_stats
)
display(stats_df_mult_symbols.head(3))

# %% [markdown]
# ## - Compute some high-level stats (e.g., median relative spread, median bid / ask notional, volatility, volume) by coins

# %%
high_level_stats = pd.DataFrame()
high_level_stats["median_relative_spread"] = final_df[
    "relative_spread_bps"
].median()
high_level_stats["median_notional_bid"] = final_df["bid_value"].median()
high_level_stats["median_notional_ask"] = final_df["ask_value"].median()
high_level_stats["median_notional_volume"] = (
    final_df["volume"] * final_df["close"]
).median()
high_level_stats["volatility_for_period"] = (
    final_df["close.ret_0"].std() * final_df.shape[0] ** 0.5
)

display(high_level_stats.head(3))
# Plot the results.
for cols in high_level_stats.columns:
    fig = plt.figure()
    fig.suptitle(f"{cols}", fontsize=15)
    plt.ylabel(cols, fontsize=12)
    cplpluti.plot_barplot(high_level_stats[cols])
