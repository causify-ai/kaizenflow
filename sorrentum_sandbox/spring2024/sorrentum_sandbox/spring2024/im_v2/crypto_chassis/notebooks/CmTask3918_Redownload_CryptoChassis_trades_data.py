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
import im_v2.crypto_chassis.data.extract.extractor as imvccdexex

# %load_ext autoreload
# %autoreload 2

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
# Imports

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

hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Crypto chassis Script bulk download

# %% language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2022-01-01T01:00:00+00:00' \
#     --end_timestamp '2022-03-15T02:00:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --universe_part 1 \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# ### Check data by reader

# %%
signature = "bulk.manual.downloaded_1min.parquet.trades.futures.v4.crypto_chassis.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2022-01-01T01:00:00+00:00")
end_timestamp = pd.Timestamp("2022-03-15T02:00:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)

# %%
trades.head()

# %% [markdown]
# # Fetch trades by CryptoChassisExtractor

# %%
contract_type = "futures"
cc_extractor = imvccdexex.CryptoChassisExtractor(contract_type)
exchange_id = "binance"
currency_pair = "BTC_USDT"
converted_currency_pair = cc_extractor.convert_currency_pair(currency_pair)
trades = cc_extractor._download_trades(exchange_id, converted_currency_pair)

# %%
trades.head()

# %% [markdown]
# ## Manual QA

# %%
signature = "bulk.manual.downloaded_1min.parquet.trades.futures.v4.crypto_chassis.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-15T01:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-15T02:00:00+00:00")

# %%
trades = reader.read_data(start_timestamp, end_timestamp)
trades.head()

# %% [markdown] heading_collapsed=true
# # CCXT script bulk download

# %% hidden=true language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2023-02-05T01:00:00+00:00' \
#     --end_timestamp '2023-02-05T02:00:00+00:00' \
#     --exchange_id 'binance' \
#     --incremental \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# # Compare trades crypto_chassis vs CCXT

# %%
signature = "bulk.airflow.downloaded_1min.parquet.trades.futures.v4.crypto_chassis.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-15T01:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-15T02:00:00+00:00")

# %%
crypto_chassis_trades = reader.read_data(start_timestamp, end_timestamp)

# %%
crypto_chassis_trades.head()

# %%
crypto_chassis_trades.columns

# %%
crypto_chassis_trades = crypto_chassis_trades.rename(columns={"size": "amount"})

# %%
crypto_chassis_trades = crypto_chassis_trades[
    ["timestamp", "price", "amount", "side", "currency_pair"]
]

# %%
crypto_chassis_trades = crypto_chassis_trades.drop_duplicates().sort_index()

# %%
signature = (
    "bulk.manual.downloaded_1min.parquet.trades.futures.v7_3.ccxt.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-02-05T01:00:00+00:00")
end_timestamp = pd.Timestamp("2023-02-05T02:00:00+00:00")

ccxt_trades = reader.read_data(start_timestamp, end_timestamp)


# %%
ccxt_trades = ccxt_trades[
    ["timestamp", "price", "amount", "side", "currency_pair"]
]

# %%
ccxt_trades = ccxt_trades.drop_duplicates().sort_index()

# %%
ccxt_trades.equals(crypto_chassis_trades)

# %%
ccxt_trades.index.name == crypto_chassis_trades.index.name

# %%
ccxt_trades.columns == crypto_chassis_trades.columns

# %%
crypto_chassis_trades.sort_index(inplace=True)

# %%
ccxt_trades.sort_index(inplace=True)

# %%
ccxt_trades.shape

# %%
crypto_chassis_trades.shape

# %%
crypto_chassis_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
ccxt_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
ccxt_trades = ccxt_trades[
    ccxt_trades.timestamp <= crypto_chassis_trades.timestamp.max()
]

# %%
crypto_chassis_trades.currency_pair.unique()

# %%
ccxt_trades.currency_pair.unique()

# %%
ccxt_trades = ccxt_trades[
    ccxt_trades.currency_pair.isin(crypto_chassis_trades.currency_pair.unique())
]

# %%
ccxt_trades == crypto_chassis_trades

# %% [markdown]
# # Compare OKX trades spot data from CCXT and crypto_chassis

# %%
ccxt_trades = pd.read_csv("/app/im_v2/ccxt/notebooks/ccxt_okx_trades_spot")
ccxt_trades.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")


# %%
ccxt_trades.timestamp.unique()[:5]

# %%
ccxt_trades_ts_min = min(ccxt_trades.timestamp)
ccxt_trades_ts_max = max(ccxt_trades.timestamp)

# %%
import im_v2.crypto_chassis.data.extract.extractor as imvccdexex

contract_type = "spot"
cc_extractor = imvccdexex.CryptoChassisExtractor(contract_type)

# %%
exchange_id = "okx"
currency_pair = "ETH_USDT"
start_timestamp = pd.Timestamp("2023-05-08 14:32:44")
converted_currency_pair = cc_extractor.convert_currency_pair(currency_pair)
# start_timestamp = hdateti.convert_timestamp_to_unix_epoch(
#     start_timestamp
# )
start_timestamp
cc_data = cc_extractor._download_trades(
    exchange_id, converted_currency_pair, start_timestamp=start_timestamp
)


# %%
cc_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
cc_data_part = cc_data[
    cc_data.timestamp.between(ccxt_trades_ts_min, ccxt_trades_ts_max)
]

# %%
cc_data_part[cc_data_part.timestamp == 1683556365542]

# %%
1683556365542

# %%
ccxt_trades[ccxt_trades.timestamp == 1683556365542]

# %%
