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
import logging

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as imvcdexex
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

# %% [markdown]
# # Bulk download script

# %% [markdown] heading_collapsed=true
# ## Airflow first test run

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'periodic_daily' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-02-05T00:00:00+00:00' \
#     --end_timestamp '2023-02-05T00:10:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-03-01T00:00:00+00:00' \
#     --end_timestamp '2023-03-01T01:00:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v7.3' \
#     --incremental \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# ## Manual QA - airflow download

# %%
signature = "periodic_daily.airflow.downloaded_1min.parquet.trades.futures.v7_3.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-07T18:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-07T19:00:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)

# %%
trades.head()

# %%
trades_pairs = trades.symbol.str.replace("/", "_").unique()

# %%
vendor = "CCXT"
mode = "download"
exchange_id = "binance"
version = "v7.3"
universe = imvcounun.get_vendor_universe(vendor, mode, version=version)

# %%
~pd.Series(trades_pairs).isin(universe[exchange_id]).any()

# %% [markdown]
# ## Manual QA - bulk download

# %%
signature = (
    "bulk.manual.downloaded_1min.parquet.trades.futures.v7_3.ccxt.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2021-03-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-03-01T01:00:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)

# %%
pairs_from_trades = trades.currency_pair.unique()

# %%
vendor = "CCXT"
mode = "download"
exchange_id = "binance"
version = "v7.3"
universe = imvcounun.get_vendor_universe(vendor, mode, version=version)

# %%
~pd.Series(pairs_from_trades).isin(universe[exchange_id]).any()

# %%
trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
trades.isna().any().all()

# %% [markdown]
# ## Manual QA - periodic daily

# %%
signature = "periodic_daily.airflow.downloaded_1min.parquet.trades.futures.v7_3.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-03T17:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-03T17:12:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)

# %%
trades

# %%
trades.isna().any().all()

# %%
pairs_from_trades = trades.currency_pair.unique()

# %%
~pd.Series(pairs_from_trades).isin(universe[exchange_id]).any()

# %%
trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%

# %% [markdown] heading_collapsed=true
# # Bare CCXT extractor test

# %% hidden=true
import ccxt

extractor = ccxt.binance()

# %% hidden=true
start_timestamp = pd.Timestamp("2021-01-01T00:00:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
start_timestamp = 1614556800000
currency_pair = "ETH/BUSD"
limit = 500
data = extractor.fetch_trades(
    currency_pair,
    since=start_timestamp,
    limit=limit,
)

# %% hidden=true
start_timestamp

# %% hidden=true
len(data)

# %% [markdown] heading_collapsed=true
# # CCXT extractor test

# %% hidden=true
import im_v2.ccxt.data.extract.extractor as imvcdexex

exchange_id = "binance"
contract_type = "futures"
ccxt_extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% hidden=true
data_type = "trades"
converted_currency_pair = currency_pair
start_timestamp = pd.Timestamp("2021-03-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-03-01T01:00:00+00:00")
data = ccxt_extractor.download_data(
    data_type,
    exchange_id,
    converted_currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=10,
)

# %% hidden=true
data
