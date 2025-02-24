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
# # Binance native downloader

# %% [markdown] heading_collapsed=true
# ## Clone repo

# %% [markdown] hidden=true
# ```bash
# git clone https://github.com/binance/binance-public-data.git
# cd binance-public-data
# ```

# %% [markdown] heading_collapsed=true
# ## Download one month data

# %% [markdown] hidden=true
# ```bash
# python3 download-trade.py -t um -s "BTCUSDT" -startDate 2023-03-01 -endDate 2023-03-01 -folder "/app/im_v2/binance/data/download"
# ```

# %% [markdown] hidden=true
# ```bash
# python3 download-trade.py -t spot -s "BTCUSDT" -startDate 2020-01-01 -endDate 2020-02-01 -folder "/app/im_v2/binance/data/download"
# ```

# %% [markdown]
# # Imports

# %%
import logging

import numpy as np
import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as ivcdexex
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe as imvcounun

# %load_ext autoreload
# %autoreload 2

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown] heading_collapsed=true
# # Download 1 day by CCXT extractor

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-03-01T00:00:00+00:00' \
#     --end_timestamp '2023-03-01T00:10:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'csv' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] heading_collapsed=true
# # Read CCXT extractor data

# %% hidden=true
signature = (
    "bulk.manual.downloaded_1min.csv.trades.futures.v7_3.ccxt.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-02T00:00:00+00:00")
currency_pair = "BTC_USDT"
ccxt_trades = reader.load_csv(
    currency_pair, start_timestamp=start_timestamp, end_timestamp=end_timestamp
)
ccxt_trades.head()

# %% hidden=true
ccxt_trades

# %% [markdown] heading_collapsed=true
# # Read native Binance data

# %% hidden=true
file_path = "/app/im_v2/binance/data/download/data/futures/um/daily/trades/BTCUSDT/2023-03-01_2023-03-01/BTCUSDT-trades-2023-03-01.zip"
# columns = ["trade_id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"]
binance_data = pd.read_csv(file_path)

# %% hidden=true
start_timestamp = pd.Timestamp("2023-03-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-01T00:10:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp, "ms")
end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp, "ms")

# %% hidden=true
binance_data = binance_data[
    binance_data.time.between(start_timestamp, end_timestamp)
]

# %% hidden=true
binance_data

# %% [markdown] hidden=true
# ## Compare min-max timestamps

# %% hidden=true
binance_data.time.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% hidden=true
ccxt_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% [markdown] hidden=true
# ## Compare IDs

# %% hidden=true
ccxt_trades[ccxt_trades.id.isin(binance_data.id)]

# %% hidden=true
ccxt_trades[ccxt_trades.timestamp.isin(binance_data.time)].head(10)["timestamp"]

# %% hidden=true
ccxt_trades[ccxt_trades.timestamp == 1677628804255]

# %% hidden=true
binance_data[binance_data.time == 1677628804255]

# %% hidden=true
binance_data[(binance_data.time == 1677628804255) & (binance_data.qty == 0.059)]

# %% hidden=true
binance_data[binance_data.time == 1677628804255].agg("sum")["qty"]

# %% [markdown] hidden=true
# ## Adjust CCXT data

# %% hidden=true
ccxt_trades = ccxt_trades.reset_index(drop=True)

# %% hidden=true
btc_ccxt_trades = ccxt_trades[ccxt_trades.currency_pair == "BTC_USDT"]

# %% hidden=true
btc_ccxt_trades.drop(
    columns=[
        "year",
        "month",
        "day",
        "currency_pair",
        "exchange_id",
        "knowledge_timestamp",
        "symbol",
    ],
    inplace=True,
)

# %% hidden=true
btc_ccxt_trades = btc_ccxt_trades.reset_index(drop=True)

# %% hidden=true
btc_ccxt_trades[~btc_ccxt_trades.timestamp.isin(binance_data.time.unique())]

# %% [markdown] hidden=true
# ## Adjust binance native data

# %% hidden=true
binance_data["side"] = binance_data.is_buyer_maker.map(
    {False: "sell", True: "buy"}
)

# %% hidden=true
binance_data.rename(columns={"time": "timestamp", "qty": "amount"}, inplace=True)

# %% hidden=true
binance_data = binance_data[["timestamp", "side", "price", "amount"]]

# %% hidden=true
btc_ccxt_trades.sort_values(by=["timestamp"], ignore_index=True, inplace=True)

# %% hidden=true
len(binance_data) - len(btc_ccxt_trades)

# %% hidden=true
binance_data = binance_data[
    binance_data.timestamp.isin(btc_ccxt_trades.timestamp)
]

# %% hidden=true
len(binance_data) - len(btc_ccxt_trades)

# %% [markdown] heading_collapsed=true
# # Bare CCXT client data

# %% hidden=true
import ccxt

extractor = ccxt.binance({"options": {"defaultType": "future"}})

# %% hidden=true
start_timestamp = pd.Timestamp("2023-03-01T00:00:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
currency_pair = "BTC/USDT"
limit = 1000
data = extractor.fetch_trades(
    currency_pair,
    since=start_timestamp,
    limit=limit,
)

# %% hidden=true
data = pd.DataFrame(data)

# %% hidden=true
data[data.timestamp.isin(binance_data.time)].head()

# %% hidden=true
import json

# %% hidden=true
data[data.timestamp == 1677628800053]

# %% hidden=true
data[data.timestamp == 1677628800053]["info"].to_json()

# %% hidden=true
binance_data[binance_data.time == 1677628800053]

# %% [markdown] heading_collapsed=true
# # BinanceExtractor download - futures

# %% hidden=true
import im_v2.binance.data.extract.extractor as ivbdexex

contract_type = "futures"
binance_extractor = ivbdexex.BinanceExtractor(contract_type)

# %% hidden=true
exchange_id = "binance"
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("2021-08-31 00:00:00")
end_timestamp = pd.Timestamp("2021-08-31 23:59:59")
binance_data = binance_extractor._download_trades(
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %% hidden=true
binance_data.head()

# %% hidden=true
binance_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% [markdown]
# # BinanceExtractor download - trades - spot

# %%
import im_v2.binance.data.extract.extractor as ivbdexex

contract_type = "spot"
time_period = ivbdexex.BinanceNativeTimePeriod.DAILY
binance_extractor = ivbdexex.BinanceExtractor(contract_type, time_period)

# %%
exchange_id = "binance"
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("2021-04-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-04-30T23:59:59+00:00")
binance_data = binance_extractor._download_trades(
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)

# %%
df1 = next(binance_data)

# %%
df1.timestamp.sort_values().apply(pd.Timestamp, unit="ms")

# %% [markdown]
# # BinanceExtractor download - trades - spot - monthly

# %%
import im_v2.binance.data.extract.extractor as ivbdexex

contract_type = "spot"
time_period = ivbdexex.BinanceNativeTimePeriod.MONTHLY
binance_extractor = ivbdexex.BinanceExtractor(
    contract_type, time_period=time_period
)

# %%
exchange_id = "binance"
currency_pair = "BTCUSDT"
start_timestamp = pd.Timestamp("2020-01-01 00:00:00")
end_timestamp = pd.Timestamp("2020-02-01 00:00:00")
monthly_iterator = binance_extractor._get_trades_iterator(
    currency_pair, start_timestamp, end_timestamp
)

# %%
df = next(monthly_iterator)

# %%
del monthly_iterator

# %%
hasattr(binance_extractor, "tmp_dir_path")

# %%
binance_extractor.tmp_dir_path

# %%
del binance_extractor

# %%
import os

import helpers.hio as hio

# %%
os.path.exists("./tmp/binance/1a9df707-acaf-4f93-8650-27a681f6f21d")

# %%
df

# %% [markdown] heading_collapsed=true
# # Download by script - trades - futures

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'binance' \
#     --start_timestamp '2021-08-31T00:00:00+00:00' \
#     --end_timestamp '2021-08-31T23:59:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v1' \
#     --incremental \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ## Read data saved by script

# %% hidden=true
signature = (
    "bulk.airflow.downloaded_1min.parquet.trades.spot.v1.binance.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2020-02-10T00:00:00+00:00")
end_timestamp = pd.Timestamp("2020-02-10T23:59:00+00:00")
currency_pairs = ["BTC_USDT"]
binance_trades = reader.read_data(
    start_timestamp,
    end_timestamp,
    currency_pairs=currency_pairs,
)
binance_trades.head()

# %% hidden=true
binance_trades.isna().any().any()

# %% hidden=true
binance_trades.shape

# %% hidden=true
binance_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% [markdown] heading_collapsed=true
# # Download by script - trades - spot

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'binance' \
#     --start_timestamp '2021-07-01T00:00:00+00:00' \
#     --end_timestamp '2021-07-01T23:59:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v1' \
#     --incremental \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] heading_collapsed=true
# # Download by script - trades - spot - monthly - 2020

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'binance' \
#     --start_timestamp '2020-02-01T00:00:00+00:00' \
#     --end_timestamp '2020-03-01T00:00:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v1' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown] hidden=true
# ## Read and check the data

# %% hidden=true
signature = (
    "bulk.airflow.downloaded_1min.parquet.trades.spot.v1.binance.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2020-12-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-01-01T00:00:00+00:00")
currency_pairs = ["BTC_USDT"]
binance_trades = reader.read_data(
    start_timestamp,
    end_timestamp,
    currency_pairs=currency_pairs,
)
binance_trades.head()

# %% hidden=true
binance_trades.isna().any().any()

# %% hidden=true
binance_trades.shape

# %% hidden=true
binance_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")
