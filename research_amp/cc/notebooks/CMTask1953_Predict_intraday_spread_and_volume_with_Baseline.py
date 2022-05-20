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
from datetime import timedelta

import numpy as np
import pandas as pd

import core.explore as coexplor
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import research_amp.transform as ramptran

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Load the data

# %% [markdown]
# ## OHLCV

# %%
# Read saved 1 month of data.
ohlcv_cc = pd.read_csv("/shared_data/cc_ohlcv.csv", index_col="timestamp")
btc_ohlcv = ohlcv_cc[ohlcv_cc["full_symbol"] == "binance::BTC_USDT"]
btc_ohlcv.index = pd.to_datetime(btc_ohlcv.index)
ohlcv_cols = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "full_symbol",
]
btc_ohlcv = btc_ohlcv[ohlcv_cols]
btc_ohlcv.head(3)

# %% [markdown]
# ## Bid ask data

# %%
# Read saved 1 month of data.
bid_ask_btc = pd.read_csv(
    "/shared_data/bid_ask_btc_jan22_1min_last.csv", index_col="timestamp"
)
bid_ask_btc.index = pd.to_datetime(bid_ask_btc.index)

# Transform the data.
bid_ask_btc.index = pd.to_datetime(bid_ask_btc.index)
# Compute bid ask stats.
bid_ask_btc = ramptran.calculate_bid_ask_statistics(bid_ask_btc)
# Choose only necessary values.
bid_ask_btc = bid_ask_btc.swaplevel(axis=1)["binance::BTC_USDT"][
    ["bid_size", "ask_size", "bid_price", "ask_price", "mid", "quoted_spread"]
]
bid_ask_btc.index = bid_ask_btc.index.shift(-1, freq="T")

bid_ask_btc.head(3)

# %% [markdown]
# ## Combined

# %%
# OHLCV + bid ask
btc = pd.concat([btc_ohlcv, bid_ask_btc], axis=1)
btc.head(3)


# %% [markdown]
# # Create and test functions for each estimator

# %% [markdown]
# ## Estimate intraday spread, volume

# %%
def get_target_value(df: pd.DataFrame, timestamp: pd.Timestamp, column_name: str):
    """
    :param df: data that contains spread and/or volume
    :param timestamp: timestamp for prediciton
    :param column_name: targeted estimation value (e.g., "quoted_spread", "volume")
    :return: value of targeted spread or volume
    """
    hpandas.dassert_monotonic_index(df.index)
    if timestamp >= df.index.min() and timestamp <= df.index.max():
        value = df[column_name].loc[timestamp]
    else:
        value = np.nan
    return value


# %%
date = pd.Timestamp("2022-01-01 00:01", tz="UTC")
display(get_target_value(btc, date, "quoted_spread"))
display(get_target_value(btc, date, "volume"))


# %% [markdown]
# ## Naive estimator

# %% [markdown]
# Value(t+2) = Value(t)

# %%
def get_naive_value(
    df: pd.DataFrame,
    timestamp: pd.Timestamp,
    column_name: str,
    delay_in_mins: int = 2,
) -> float:
    """
    Estimator for a given time is a `t - delay_in_mins` of a real value.

    :param df: data that contains spread and/or volume
    :param timestamp: timestamp for prediciton
    :param column_name: targeted estimation value (e.g., "quoted_spread", "volume")
    :param delay_in_mins: desired gap for target estimator, in mins
    :return: value of predicted spread or volume
    """
    # Check and define delay.
    hdbg.dassert_lte(1, delay_in_mins)
    delay_in_mins = timedelta(minutes=delay_in_mins)
    # Get the value.
    lookup_timestamp = timestamp - delay_in_mins
    if lookup_timestamp >= df.index.min() and lookup_timestamp <= df.index.max():
        value = get_target_value(df, lookup_timestamp, column_name)
    else:
        value = np.nan
    return value


# %%
date = pd.Timestamp("2022-01-01 00:03", tz="UTC")
display(get_naive_value(btc, date, "quoted_spread"))
display(get_naive_value(btc, date, "volume"))

# %% [markdown]
# ## Look back N days

# %% [markdown]
# spread_lookback(t) = E_date[spread(t, date)]

# %%
# Add column with intraday time.
btc["time"] = btc.index.time


# %%
def get_lookback_value(
    df: pd.DataFrame,
    timestamp: pd.Timestamp,
    lookback_days: int,
    column_name: str,
    delay: int = 0,
    mode: str = "mean",
) -> float:
    """
    1) Set the period that is equal `timestamp for prediciton` - N days (lookback_days).
    2) For that period, calculate mean (or median) value for spread in time during days.
    3) Choose this mean value as an estimation for spread in the given timestamp.

    :param df: data that contains spread
    :param timestamp: timestamp for prediciton
    :param lookback_days: historical period for estimation, in days
    :param column_name: targeted estimation value (e.g., "quoted_spread", "volume")
    :param delay: how many minutes to substract from the lookback starting period
    :param mode: 'mean' or 'median'
    :return: value of predicted spread
    """
    # Choose sample data using lookback period (with a delay).
    start_date = timestamp - timedelta(days=lookback_days, minutes=delay)
    if start_date >= df.index.min() and start_date <= df.index.max():
        sample = df.loc[start_date:timestamp]
        # Look for the reference value for the period.
        time_grouper = sample.groupby("time")
        if mode == "mean":
            grouped = time_grouper[column_name].mean().to_frame()
        else:
            grouped = time_grouper[column_name].median().to_frame()
        # Choose the lookback spread for a given time.
        # value = grouped[timestamp.time()]
        value = get_target_value(grouped, timestamp.time(), column_name)
    else:
        value = np.nan
    return value


# %%
date = pd.Timestamp("2022-01-21 19:59", tz="UTC")
display(get_lookback_value(btc, date, 14, "quoted_spread"))
display(get_lookback_value(btc, date, 14, "volume"))

# %% [markdown]
# # Collect all estimators for the whole period

# %%
estimation_target = "quoted_spread"

# Generate the separate DataFrame for estimators.
estimators = pd.DataFrame(index=btc.index[1:])
# Add the values of a real spread.
estimators["real_spread"] = estimators.index
estimators["real_spread"] = estimators["real_spread"].apply(
    lambda x: get_target_value(btc, x, estimation_target)
)

# Add the values of naive estimator.
estimators["naive_spread"] = estimators.index
# Starting from the second value since this estimator looks back for two periods.
estimators["naive_spread"] = estimators["naive_spread"].apply(
    lambda x: get_naive_value(btc, x, estimation_target)
)

# Add the values of lookback estimator.
# Parameters.
lookback = 14
# Calculate values.
estimators["lookback_spread"] = estimators.index
estimators["lookback_spread"] = estimators["lookback_spread"].apply(
    lambda x: get_lookback_value(btc, x, lookback, estimation_target)
)

# %% run_control={"marked": false}
estimators


# %% [markdown]
# # Evaluate results

# %%
def get_mean_error(
    df: pd.DataFrame,
    column_name: str,
    num_std: int = 1,
    print_results: bool = True,
) -> pd.Series:
    """
    - Calculate the error of difference between real and estimated values.
    - Show the mean and ± num_std*standard_deviation levels.

    :param df: data with real values and estimators
    :param column_name: estimator (e.g., "naive_spread", "lookback_spread")
    :param num_std: number of standard deviations from mean
    :param print_results: whether or not print results
    :return: errors for each data point
    """
    err = abs(df["real_spread"] - df[column_name]) / df["real_spread"]
    err_mean = err.mean()
    err_std = err.std()
    if print_results:
        print(
            f"Mean error + {num_std} std = {err_mean+num_std*err_std} \
              \nMean error = {err_mean}\
              \nMean error - {num_std} std = {err_mean-num_std*err_std}"
        )
    return err


# %%
# Choose the period that is equally filled by both estimators.
test = estimators[estimators["lookback_spread"].notna()]
test.head(3)

# %% [markdown]
# ## Naive estimator

# %%
# Mean error and upper/lower level of errors' standard deviation.
naive_err = get_mean_error(test, column_name="naive_spread")

# %% run_control={"marked": false}
# Regress (OLS) between `real_spread` and `naive_spread`.
predicted_var = "real_spread"
predictor_vars = "naive_spread"
intercept = True
# Run OLS.
coexplor.ols_regress(
    test,
    predicted_var,
    predictor_vars,
    intercept,
)

# %%
test[["real_spread", "naive_spread"]].plot(figsize=(15, 7))

# %% [markdown]
# ## Lookback estimator

# %%
# Mean error and upper/lower level of errors' standard deviation.
lookback_err = get_mean_error(test, column_name="lookback_spread")

# %%
# Regress (OLS) between `real_spread` and `lookback_spread`.
predicted_var = "real_spread"
predictor_vars = "lookback_spread"
intercept = True
# Run OLS.
coexplor.ols_regress(
    test,
    predicted_var,
    predictor_vars,
    intercept,
)

# %%
test[["real_spread", "lookback_spread"]].plot(figsize=(15, 7))
