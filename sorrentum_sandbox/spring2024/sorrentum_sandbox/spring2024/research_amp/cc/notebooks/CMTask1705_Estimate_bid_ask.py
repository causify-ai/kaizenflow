# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import logging

import pandas as pd
import requests

import core.finance.resampling as cfinresa
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.exchange_class as imvcdeexcl

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

hprint.config_notebook()

# %% [markdown]
# # Bid-ask data snippet (current implementation)

# %%
# Specify params.
exchange_id = "binance"
# Initiate the client.
bid_ask_client = imvcdeexcl.CcxtExchange(exchange_id)

# %%
# Load the data snippet for BTC.
currency_pair = "BTC_USDT"
ba_df = bid_ask_client.download_order_book(currency_pair)

# %%
ba_df

# %% [markdown]
# As one can see, the current implementation of bid-ask data loader only allows to show the order book at the exact moment of its initiation.

# %% [markdown]
# # Bid-ask data extraction (proposed solution)

# %% [markdown]
# Thanks to the research that was done in #193, we had a notion that the bid-ask data can be downloaded via open sources and specifically - _crypto-chassis_.
# For more details one can see https://github.com/cryptokaizen/cmamp/issues/193#issuecomment-974822385
#
# Few words about the data:
# - API page: https://github.com/crypto-chassis/cryptochassis-data-api-docs#information
#    - Specifically, `Market Depth` section
# - each GET request allow to download one day of 1-second snapshot data on market depth (aka order books or Level 2 data) up to a depth of 10

# %% [markdown]
# ## Example of a raw data

# %% [markdown]
# For the example I am taking the data with he following characteristics:
# - `full_symbol` = binance::BTC_USDT
# - depth = 1 (default option)

# %% run_control={"marked": false}
example_date = "2022-01-01"
r = requests.get(
    f"https://api.cryptochassis.com/v1/market-depth/binance/btc-usdt?startTime={example_date}"
)
example_data = pd.read_csv(r.json()["urls"][0]["url"], compression="gzip")

# %%
example_data.head()


# %% [markdown]
# ## Get historical data

# %% [markdown]
# Each request is strictly limited to get only one day of bid-ask data. That's why I want to propose the solution that allows to get the DataFrame for any desired time range of historical data.

# %% [markdown]
# ### Functions that convert data to the C-K format

# %%
def clean_up_raw_bid_ask_data(df):
    # Split the columns to differentiate between `price` and `size`.
    df[["bid_price", "bid_size"]] = df["bid_price_bid_size"].str.split(
        "_", expand=True
    )
    df[["ask_price", "ask_size"]] = df["ask_price_ask_size"].str.split(
        "_", expand=True
    )
    df = df.drop(columns=["bid_price_bid_size", "ask_price_ask_size"])
    # Convert `timestamps` to the usual format.
    df = df.rename(columns={"time_seconds": "timestamp"})
    df["timestamp"] = df["timestamp"].apply(
        lambda x: hdateti.convert_unix_epoch_to_timestamp(x, unit="s")
    )
    df = df.set_index("timestamp")
    # Convert to `float`.
    for cols in df.columns:
        df[cols] = df[cols].astype(float)
    # Add `full_symbol` (hardcoded solution).
    df["full_symbol"] = "binance::BTC_USDT"
    return df


# %%
def resample_bid_ask(df, resampling_rule):
    """
    In the current format the data is presented in the `seconds` frequency. In
    order to convert it to the minutely (or other) frequencies the following
    aggregation rules are applied:

    - Size is the sum of all sizes during the resampling period
    - Price is the mean of all prices during the resampling period
    """
    new_df = cfinresa.resample(df, rule=resampling_rule).agg(
        {
            "bid_price": "mean",
            "bid_size": "sum",
            "ask_price": "mean",
            "ask_size": "sum",
            "full_symbol": "last",
        }
    )
    return new_df


# %%
def process_bid_ask_data(df):
    # Convert the data to the right format.
    converted_df = clean_up_raw_bid_ask_data(df)
    # Resample.
    converted_resampled_df = resample_bid_ask(converted_df, "1T")
    return converted_resampled_df


# %% [markdown]
# ### Load historical data

# %% [markdown]
# For the example I am taking the data with he following characteristics:
# - `full_symbol` = binance::BTC_USDT
# - depth = 1 (default option)
# - start_ts = "2022-01-01"
# - end_ts = "2022-01-30" (15 days in total)

# %%
# Get the list of all dates in the range.
datelist = pd.date_range("2022-01-01", periods=30).tolist()
datelist = [str(x.strftime("%Y-%m-%d")) for x in datelist]

# %%
# Using the variables from `datelist` the multiple requests can be sent to the API.
result = []
for date in datelist:
    # Interaction with the API.
    r = requests.get(
        f"https://api.cryptochassis.com/v1/market-depth/binance/btc-usdt?startTime={date}"
    )
    data = pd.read_csv(r.json()["urls"][0]["url"], compression="gzip")
    # Attaching it day-by-day to the final DataFrame.
    result.append(data)
bid_ask_df = pd.concat(result)

# %%
# Transforming the data.
processed_data = process_bid_ask_data(bid_ask_df)

# %%
# Show the data.
display(processed_data.shape)
display(processed_data)

# %% [markdown]
# Now, this data is in the format that is compatible for working with CCXT OHLCV data.
#
# It takes ±1.5mins to load and process data for 1 month (30 days), so it shouldn't take much time to load big chunks of historical data.
