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
# TODO(Vlad): convert into a unit test.

# %% [markdown]
# # Imports

# %%
import pyarrow

import helpers.hparquet as hparque

# %%
filters = [("currency_pair", "in", ["BTC_USDT"])]
file_name = "s3://cryptokaizen-data-test/v3/periodic_daily/airflow/downloaded_1min/parquet/ohlcv/futures/v7_3/ccxt/binance/v1_0_0/"

# %%
pyarrow.__version__

# %% [markdown]
# # Rationale

# %% [markdown]
# From the https://github.com/cryptokaizen/cmamp/issues/7097#issuecomment-1944181433
#
# The notebook verifies that combining new data, saved and read using pyarrow version 14.0.0, with the existing production dataset doesn't impact performance when handling large parquet datasets and does not lead to any issues.
#
# - Considering that we have the snippet of the preprod data at: "s3://cryptokaizen-data-test/v3/periodic_daily/airflow/downloaded_1min/parquet/ohlcv/futures/v7_3/ccxt/binance/v1_0_0/".
# - Read the data from given location using `hparque.from_parquet()`
# - Download the new portion of the data to the same location
# - Read the mixed data
#
# Expected behavior: the reading of large Parquet files does not increases the performance time and does not lead to any errors.

# %% [markdown]
# # Read initial data from preprod

# %%
df = hparque.from_parquet(file_name, filters=filters, aws_profile="ck")

# %%
df.head()

# %%
df.shape

# %% [markdown]
# # Download data

# %%
# !/app/amp/im_v2/common/data/extract/download_bulk.py \
#     --start_timestamp '2023-01-01T00:00:00+00:00' \
#     --end_timestamp '2023-01-31T23:59:00+00:00' \
#     --vendor 'ccxt' \
#     --exchange_id 'binance' \
#     --universe 'v7.3' \
#     --data_type 'ohlcv' \
#     --contract_type 'futures' \
#     --aws_profile 'ck' \
#     --assert_on_missing_data \
#     --s3_path 's3://cryptokaizen-data-test' \
#     --download_mode 'periodic_daily' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --data_format 'parquet'

# %% [markdown]
# # Read data after downloading

# %%
df = hparque.from_parquet(file_name, filters=filters, aws_profile="ck")

# %%
df.head()

# %%
df.shape
