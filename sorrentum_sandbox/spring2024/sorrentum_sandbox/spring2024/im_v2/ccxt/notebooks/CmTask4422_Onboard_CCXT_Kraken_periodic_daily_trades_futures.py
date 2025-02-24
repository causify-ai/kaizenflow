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
# # Bare CCXT extractor test

# %%
since = None

# %%
import ccxt

extractor = ccxt.krakenfutures()



# %%
m = extractor.fetch_markets()

# %%
m_f = [s for s in m if s["info"]["type"] == "flexible_futures"]

# %%
s_f = [s["symbol"] for s in m_f]

# %%
s_f

# %%

start_timestamp = pd.Timestamp("2023-05-01T00:00:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
end_timestamp = pd.Timestamp("2023-05-18T01:10:00+00:00")
end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_timestamp)
# currency_pair = "ETH/USDT"
currency_pair = "BTC/USD:USD"



# %%
end_timestamp

# %%
data = extractor.fetch_trades(
    currency_pair,
#     since=start_timestamp,
    params={"until": end_timestamp}
)

# %%
data

# %%
since = data[-1]["timestamp"]

# %%
data = pd.DataFrame(data)

# %%
data.head()

# %%
data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
last_data_id = 1609509956295391408

# %%
params = {"fromId": last_data_id}
data = extractor.fetch_trades(currency_pair, since=160950995629539.1408)

# %%
data

# %%
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
