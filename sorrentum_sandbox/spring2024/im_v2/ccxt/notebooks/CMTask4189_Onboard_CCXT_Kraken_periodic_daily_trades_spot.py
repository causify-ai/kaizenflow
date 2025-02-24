# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown] heading_collapsed=true
# # Imports

# %% hidden=true
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

# %% hidden=true
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown] heading_collapsed=true
# # Bare CCXT extractor test

# %% hidden=true
since = None

# %% hidden=true
import ccxt

extractor = ccxt.kraken()

start_timestamp = pd.Timestamp("2021-01-01T00:00:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
currency_pair = "ETH/USDT"

data = extractor.fetch_trades(
    currency_pair,
    since=since or start_timestamp,
)


# %% hidden=true
data[0]

# %% hidden=true
since = data[-1]["timestamp"]

# %% hidden=true
data = pd.DataFrame(data)

# %% hidden=true
data.head()

# %% hidden=true
data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% hidden=true
last_data_id = 1609509956295391408

# %% hidden=true
params = {"fromId": last_data_id}
data = extractor.fetch_trades(currency_pair, since=160950995629539.1408)

# %% hidden=true
data

# %% hidden=true
since = data[-1]["info"][-1]

# %% [markdown]
# # CCXT extractor test

# %%
import im_v2.ccxt.data.extract.extractor as imvcdexex

exchange_id = "kraken"
contract_type = "spot"
ccxt_extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %%
data_type = "trades"
currency_pair = "ETH/USDT"
converted_currency_pair = currency_pair
start_timestamp = pd.Timestamp("2021-01-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-01-07T23:59:59+00:00")
data = ccxt_extractor.download_data(
    data_type,
    exchange_id,
    converted_currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=10,
)

# %%
data.head()

# %%
data["timestamp1"] = data["timestamp"].apply(pd.Timestamp, unit="ms")

# %%
len(data)

# %%
data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
data.isna().any().any()

# %% [markdown]
# # Bulk script data download

# %% language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'periodic_daily' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-02-01T00:00:00+00:00' \
#     --end_timestamp '2023-02-20T00:00:00+00:00' \
#     --exchange_id 'kraken' \
#     --incremental \
#     --universe 'v7.4' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# # Read and check data by RawReader

# %%
signature = "periodic_daily.airflow.downloaded_1min.parquet.trades.spot.v7_4.ccxt.kraken.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-02-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-02-20T00:00:00+00:00")
trades = reader.read_data(start_timestamp, end_timestamp)


# %%
trades

# %%
trades.isna().any().any()

# %%
pd.Series(trades.currency_pair.unique())

# %%
a = [
    "ETH_USDT",
    "BTC_USDT",
    "APE_USDT",
    "MATIC_USDT",
    "DOT_USDT",
    "XRP_USDT",
    "DOGE_USDT",
    "SOL_USDT",
    "USDC_USDT",
    "ADA_USDT",
    "LTC_USDT",
    "SHIB_USDT",
    "AVAX_USDT",
    "DAI_USDT",
    "LINK/USDT",
    "ATOM/USDT",
    "XMR/USDT",
    "BCH/USDT",
]

# %%
unique_currency_pair = pd.Series(trades.currency_pair.unique())

# %%
unique_currency_pair[~unique_currency_pair.isin(a)]

# %% [markdown]
# # QA  exploratory analysis

# %% run_control={"marked": false}
mode = "download"
vendor_name = "CCXT"
version = "v7.4"
universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
universe_list = universe[exchange_id]
qa_check_list = [
    imvcdqqach.NaNChecks(),
    imvcdqqach.FullUniversePresentCheck(universe_list),
]
dataset_validator1 = imvcdqdava.DataFrameDatasetValidator(qa_check_list)

# %%
dataset_validator1.run_all_checks([trades])

# %%
