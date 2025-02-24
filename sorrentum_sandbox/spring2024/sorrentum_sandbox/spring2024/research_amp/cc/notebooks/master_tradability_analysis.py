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

import pandas as pd

import core.config.config_ as cconconf
import core.plotting.normality as cplonorm
import core.plotting.plotting_utils as cplpluti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import research_amp.transform as ramptran

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
    config["data"]["full_symbols"] = [
        "binance::ADA_USDT",
        "binance::BNB_USDT",
        "binance::BTC_USDT",
        "binance::DOGE_USDT",
        "binance::EOS_USDT",
        "binance::ETH_USDT",
        "binance::SOL_USDT",
        "binance::XRP_USDT",
        "binance::LUNA_USDT",
        "binance::DOT_USDT",
        "binance::LTC_USDT",
        "binance::UNI_USDT",
    ]
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
# Note: `exchange_id = binance` was chosen for coins v5 analysis.
# The missing coins in crypto-chassis in `binance`:
# - v4:
#    - Avalanche (AVAX)
#    - Chainlink (LINK)
# - v5:
#    - HEX
#    - SHIB (Shiba Inu)
#    - MATIC (Polygon)
#    - TRX (TRON)
#    - WAVES (Waves)
#    - XLM (Stellar)

# %% [markdown]
# # Load OHLCV data from `crypto-chassis`

# %% [markdown]
# ## Data demonstration

# %%
# TODO(Max): Refactor the loading part once #1766 is implemented.

# Read from crypto_chassis directly.
# full_symbols = config["data"]["full_symbols"]
# start_date = config["data"]["start_date"]
# end_date = config["data"]["end_date"]
# ohlcv_cc = raccchap.read_crypto_chassis_ohlcv(full_symbols, start_date, end_date)

# Read saved 1 month of data.
ohlcv_cc = pd.read_csv("/shared_data/ohlcv_cc_v5.csv", index_col="timestamp")
ohlcv_cc.index = pd.to_datetime(ohlcv_cc.index)
ohlcv_cc.head(3)

# %% [markdown]
# # Calculate VWAP, TWAP and returns in `Dataflow` style

# %%
# VWAP, TWAP transformation.
resampling_rule = config["transform"]["resampling_rule"]
vwap_twap_df = ramptran.calculate_vwap_twap(ohlcv_cc, resampling_rule)

# Returns calculation.
rets_type = config["transform"]["rets_type"]
vwap_twap_rets_df = ramptran.calculate_returns(vwap_twap_df, rets_type)

# %% run_control={"marked": false}
# Show the snippet.
vwap_twap_rets_df.head(3)

# %% run_control={"marked": false}
# Stats and vizualisation to check the outcomes.
coin_ex = vwap_twap_rets_df.swaplevel(axis=1)
coin_ex = coin_ex["binance::DOGE_USDT"][
    ["close.ret_0", "twap.ret_0", "vwap.ret_0"]
]
display(coin_ex.corr())
coin_ex.plot()

# %% [markdown]
# # Bid-ask data

# %%
# TODO(Max): Refactor the loading part once #1766 is implemented.

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
bid_ask_df = pd.read_csv(
    "/shared_data/bid_ask_data_v5.csv", index_col="timestamp"
)
bid_ask_df.index = pd.to_datetime(bid_ask_df.index)
bid_ask_df.head(3)

# %%
# Calculate bid-ask metrics.
bid_ask_df = ramptran.calculate_bid_ask_statistics(bid_ask_df)
bid_ask_df.tail(3)

# %% [markdown]
# ## Unite VWAP, TWAP, rets statistics with bid-ask stats

# %%
final_df = pd.concat([vwap_twap_rets_df, bid_ask_df], axis=1)
final_df.tail(3)

# %%
# Metrics visualizations.
final_df["relative_spread_bps"].plot()

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
liquidity_stats = final_df["ask_value"].median()
display(liquidity_stats)
cplpluti.plot_barplot(liquidity_stats)

# %% [markdown]
# ## Is the quoted spread constant over the day?

# %% [markdown]
# ### One symbol

# %%
full_symbol = "binance::EOS_USDT"
resample_rule_stats = "10T"

stats_df = ramptran.calculate_overtime_quantities(
    final_df, full_symbol, resample_rule_stats
)
display(stats_df.head(3))

# %% [markdown]
# ### Multiple Symbols

# %% run_control={"marked": false}
full_symbols = config["data"]["full_symbols"]
resample_rule_stats = "10T"

stats_df_mult_symbols = ramptran.calculate_overtime_quantities_multiple_symbols(
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
high_level_stats["volatility_per_period"] = (
    final_df["close.ret_0"].std() * final_df.shape[0] ** 0.5
)

display(high_level_stats)
