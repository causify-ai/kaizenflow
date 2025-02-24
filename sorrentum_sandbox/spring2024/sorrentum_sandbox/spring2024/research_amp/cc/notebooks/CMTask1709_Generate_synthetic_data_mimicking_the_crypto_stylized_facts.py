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
# - Compute returns from the real data.
# - Pre-define the hit rate and calculate predictions, hits and confidence intervals.
# - Show PnL and Sharpe Ratio for the corresponding parameters.
# - Bootstrapping to compute pnl = f(hit_rate).

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import seaborn as sns

import core.config.config_ as cconconf
import core.finance as cofinanc
import core.finance.resampling as cfinresa
import core.finance.tradability as cfintrad
import core.plotting.misc_plotting as cplmiplo
import core.statistics.sharpe_ratio as cstshrat
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
def get_synthetic_data_config() -> cconconf.Config:
    """
    Get config that specifies params for analysis.
    """
    config = cconconf.Config()
    # Data parameters.
    config.add_subconfig("data")
    # Reference price to calculate returns.
    config["data"]["reference_price"] = "close"
    # Returns mode: 'pct_change','log_rets' or 'diff'.
    config["data"]["rets_mode"] = "pct_change"
    # Check returns for an analysis: raw ('rets') or cleaned ('rets_cleaned').
    config["data"]["rets_col"] = "rets_cleaned"
    # Choose the timeframe for resampling.
    config["data"]["resampling_rule"] = "5T"
    # Number of periods for returns normalization.
    config["data"]["lookback_in_samples"] = 100
    return config


# %%
config = get_synthetic_data_config()
print(config)


# %% [markdown]
# # Functions

# %%
def compute_normalize_returns(
    df: pd.DataFrame,
    price_col: str,
    rets_mode: str,
    lookback: int,
    rets_col: str,
    plot_rets: bool,
) -> pd.DataFrame:
    """
    Calculate simple returns as well as normalized ones and plot the results.

    :param df: OHLCV data
    :param price_col: Price column that will be used to calculate returns
    :param rets_mode: "pct_change", "log_rets" or "diff"
    :param lookback: Number of periods for returns normalization
    :param rets_col: Column to plot ("rets" or "rets_cleaned")
    :param plot_rets: Whether or not plot returns
    :return: OHLCV data with returns and normalized returns
    """
    # Compute returns.
    df["rets"] = cofinanc.compute_ret_0(df[price_col], rets_mode)
    # Normalize returns.
    df["rets_cleaned"] = df["rets"]
    # Demean step.
    df["rets_cleaned"] -= df["rets_cleaned"].rolling(lookback).mean()
    # Risk adjustment.
    df["rets_cleaned"] /= df["rets_cleaned"].rolling(lookback).std()
    # Remove NaNs.
    df = hpandas.dropna(df, report_stats=True)
    if plot_rets:
        df[rets_col].plot()
    return df


# %% [markdown]
# # Extract returns from the real data

# %% [markdown]
# ## Load BTC data from `crypto-chassis` (shared_data folder)

# %%
btc_df = pd.read_csv("/shared_data/BTC_one_year.csv", index_col="timestamp")
ohlcv_cols = [
    "open",
    "high",
    "low",
    "close",
    "volume",
]
btc_df.index = pd.to_datetime(btc_df.index)
btc_df = btc_df[ohlcv_cols]
btc_df.head(3)

# %% [markdown]
# ## Process returns

# %% run_control={"marked": false}
btc = btc_df.copy()
# Specify params.
price_col = config["data"]["reference_price"]
rets_mode = config["data"]["rets_mode"]
rets_col = config["data"]["rets_col"]
lookback_in_samples = config["data"]["lookback_in_samples"]
resampling_rule = config["data"]["resampling_rule"]
# Resample.
btc = cfinresa.resample_ohlcv_bars(btc, resampling_rule)
# Add returns.
btc = compute_normalize_returns(
    btc, price_col, rets_mode, lookback_in_samples, rets_col, plot_rets=True
)
# Show snippet.
display(btc.head())

# %%
# Show the distribution of returns.
rets_col = config["data"]["rets_col"]
sns.displot(btc, x=rets_col)

# %% [markdown]
# # Pre-defined Predictions, Hit Rates and Confidence Interval

# %%
# Specify params.
sample = btc
ret_col = config["data"]["rets_col"]
hit_rate = 0.505
seed = 2
alpha = 0.05
method = "normal"
# Calculate and attach `predictions` and `hit` to the OHLCV data.
btc[["rets_cleaned", "predictions", "hit"]] = cfintrad.get_predictions_and_hits(
    sample, ret_col, hit_rate, seed
)
display(btc.tail(3))
# Shpw CI stats.
cfintrad.calculate_confidence_interval(btc["hit"], alpha, method)

# %%
## Show PnL for the current `hit_rate`
pnl = (btc["predictions"] * btc[ret_col]).cumsum()
pnl = pnl[pnl.notna()]
cplmiplo.plot_cumulative_returns(pnl, mode="pct")
# Sharpe ratio.
cstshrat.summarize_sharpe_ratio(pnl)

# %% [markdown]
# # PnL as a function of `hit_rate`

# %%
# Specify params.
sample = btc
rets_col = config["data"]["rets_col"]
hit_rates = np.linspace(0.4, 0.6, num=10)
n_experiment = 10
# Perform the simulattion.
pnls = cfintrad.simulate_pnls_for_set_of_hit_rates(
    sample, rets_col, hit_rates, n_experiment
)

# %% run_control={"marked": false}
hit_pnl_df = pd.DataFrame(pnls.items(), columns=["hit_rate", "PnL"])
sns.scatterplot(data=hit_pnl_df, x="hit_rate", y="PnL")

# %%
x = hit_pnl_df["hit_rate"]
y = hit_pnl_df["PnL"]

ols_results = stats.linregress(x, y)
print(f"R-squared = {ols_results.rvalue**2:.4f}")
plt.plot(x, y, "o", label="original data")
plt.plot(
    x, ols_results.intercept + ols_results.slope * x, "r", label="fitted line"
)
plt.legend()
plt.show()
