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
# # Imports

# %%
import datetime
import logging

import pandas as pd

import core.finance.bid_ask as cfibiask
import im_v2.common.data.transform.transform_utils as imvcdttrut
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hdatetime as hdateti
import helpers.hparquet as hparque
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc

# %%
hdbg.init_logger(verbosity=logging.INFO)
log_level = logging.INFO

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# ## Set params

# %%
start = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp("2023-05-05 14:00:00+00:00"), unit="ms"
)
end = hdateti.convert_timestamp_to_unix_epoch(
    pd.Timestamp("2023-05-05 14:10:00+00:00"), unit="ms"
)
s3_path = "s3://cryptokaizen-data.preprod/v3/periodic_daily/airflow/archived_200ms/parquet/bid_ask/futures/v7/ccxt/binance/v1_0_0/"

# %%
filters = [("year", "=", 2023), ("month", "=", 5), ("day", "=", 5), 
           ("timestamp", ">=", start), ("timestamp", "<=", end), ("currency_pair", "=", "BTC_USDT")
          ]
data = hparque.from_parquet(
        "s3://cryptokaizen-data.preprod/v3/periodic_daily/airflow/archived_200ms/parquet/bid_ask/futures/v7/ccxt/binance/v1_0_0/", filters=filters, aws_profile="ck"
)

# %% [markdown]
# ## Drop duplicates

# %%
data = data.drop_duplicates(
    subset=["timestamp", "exchange_id", "currency_pair", "level"]
)
# Timestamp is in the index, column is obsolete
data = data.drop("timestamp", axis=1)

# %% [markdown]
# ## Transform from long to wide format

# %%
data = cfibiask.transform_bid_ask_long_data_to_wide(data, "timestamp")

# %% [markdown]
# ## Resample

# %% [markdown]
# ### Resample using approach of double resampling (first to 1 sec, then to 1 min)

# %% run_control={"marked": true}
## The function name is not 100% correct since the input data need not be 1sec.
data_resampled = imvcdttrut.resample_multilevel_bid_ask_data_from_1sec_to_1min(data)

# %%
data_resampled.head()

# %% [markdown]
# ### Resample using approach of single resampling (fdirectly 200 ms to 1 min)

# %%
data_resampled2 = imvcdttrut.resample_multilevel_bid_ask_data_to_1min(data)

# %%
data_resampled2.head()

# %%
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import pandas as pd
signature = "periodic_daily.airflow.resampled_1min.parquet.bid_ask.futures.v7.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
data2 = reader.read_data(pd.Timestamp("2023-05-05T00:00:00+00:00"), pd.Timestamp("2023-05-06T00:00:00+00:00"))


# %% [markdown]
# TODO(Sonaal):
#
# In the two cells below you see we have run into a discrepancy:
# 1. The first cell shows what a "raw" bid/ask data we collect look like (sampled ~200ms), notice this row:
#
# timestamp bid_size_l1 	bid_size_l2 	ask_size_l1 	ask_size_l2
#
# 2023-05-05 14:04:59.958000+00:00 	7.644 	3.794 	2.962 	0.002
#
# - this is the last row in the minute interval <14:04:00, 14:05:00) and bid_size = 7.644
# - the problem is that the resampled data:
#
# timestamp level_1.bid_price.close 	level_1.bid_size.close
#
# 2023-05-05 14:05:00+00:00 	29156.700 	8.526667 
#
# show that level_1.bid_size.close = 8.526667 while it should be 7.644
#
# Suggested debugging steps:
# 1. Firstly let's try to resample the raw data in a new cell using `resample_multilevel_bid_ask_data_to_1min` from `im_v2.common.data.transform.transform_utils` and observe if the same issue occurs, if yes, that means there is a problem within the function.
# 2. If the function seems to provide the correct values, let's take a look at `im_v2/common/data/transform/resample_daily_bid_ask_data.py` which is a script that produced the incorrect data - it does some transformation before applying the above mentioned resampling function - that would indicate that somewhere in the process there is a bug.
#

# %% [markdown]
# @Juraj I guess I figured out what was the issue causing the discrepancy in the results.
# this is the last row in the minute interval <14:04:00, 14:05:00) and bid_size = 7.644
# ```
# timestamp bid_size_l1 bid_size_l2 ask_size_l1 ask_size_l2
# 2023-05-05 14:04:59.958000+00:00 7.644 3.794 2.962 0.002
# ```
# the problem is that the resampled data:
# ```
# timestamp level_1.bid_price.close level_1.bid_size.close
# 2023-05-05 14:05:00+00:00 29156.700 8.526667
# ```
# Why level_1.bid_size.close = 8.526667 while it should be 7.644 ?
#
# This is caused by the method ```resample_multilevel_bid_ask_data_to_1min ``` which internally calls the method ```resample_bid_ask_data_from_1sec_to_1min ```. This method first resample the data for ```1sec``` using the config
# ```
# # First resample to 1 second.
#     resampling_groups_1sec = [
#         (
#             {
#                 "bid_price": "bid_price",
#                 "bid_size": "bid_size",
#                 "ask_price": "ask_price",
#                 "ask_size": "ask_size",
#             },
#             "mean",
#             {},
#         ),
#     ]
# ```
# This config takes the mean of the value of the values in 1sec interval.
# Eg:
# ```
#
#
# 2023-05-05 14:04:59.043000+00:00 | 9.943 | 3.825 | 5.014 | 0.002
# -- | -- | -- | -- | --
# 7.993 | 3.825 | 5.087 | 0.002
# 7.644 | 3.794 | 2.962 | 0.002
#
# ```
# This is the last 1sec data. If you take the mean of bid ask in this 1sec interval ```(9.943 + 7.993 + 7.644 ) / 3 = 8.52667 ``` which is what we are getting as output. I hope this is what you were trying to debug for 1.
# Let me know if you want me to fix it or you were looking for something else in debugging.

# %%
data.loc["2023-05-05 14:03:59":].head(5 * 60 + 10)[["bid_size_l1", "bid_size_l2", "ask_size_l1", "ask_size_l2"]]

# %%
data2.loc["2023-05-05 14:05:00":]

# %%
data_resampled3 = imvcdttrut.resample_multilevel_bid_ask_data_to_1min(data)

# %%
data_resampled3.loc["2023-05-05 14:05:00":]

# %% [markdown]
# Now level_1.bid_size.close is consistent with the data. 
#

# %%
filters = [("year", "=", 2023), ("month", "=", 5), ("day", "=", 5), 
           ("timestamp", ">=", start), ("timestamp", "<=", end), ("currency_pair", "in", ["BTC_USDT", "ETH_USDT"])
          ]
data = hparque.from_parquet(
        "s3://cryptokaizen-data.preprod/v3/periodic_daily/airflow/archived_200ms/parquet/bid_ask/futures/v7/ccxt/binance/v1_0_0/", filters=filters, aws_profile="ck"
)

# %%
data = data[(data["level"] == 1) | (data["level"] == 2)]
all_cols = imvcdttrut.BID_ASK_COLS + ["timestamp", "currency_pair", "level", "exchange_id"]
data = data[all_cols]
sample_long = data.loc["2023-05-05 14:00:00": "2023-05-05 14:00:01"]

# %%
sample_long.head()
# sample_long.to_csv("../data/transform/test/outcomes/SampleBidAskDataLong.csv")

# %%
# data2 = data.drop("timestamp", axis=1)
sample_long = sample_long.drop_duplicates(
    subset=["timestamp", "exchange_id", "currency_pair", "level"]
)
sample_long = sample_long.drop('timestamp', axis=1)
sample_wide = cfibiask.transform_bid_ask_long_data_to_wide(sample_long, "timestamp")

# %%
sample_wide.head()
# sample_wide.to_csv("../data/transform/test/outcomes/SampleBidAskDataWide.csv")
