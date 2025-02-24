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

# %% [markdown]
# # Bare CCXT extractor test

# %%
import ccxt

extractor = ccxt.okx()

# %%
start_timestamp = pd.Timestamp("2020-01-01T00:00:00+00:00")
start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_timestamp)
currency_pair = "ETH/USDT"
timeframe = "1m"
limit = 500

# %%
data = extractor.fetch_ohlcv(
    currency_pair,
    timeframe=timeframe,
    since=start_timestamp,
    limit=limit,
)

# %%
len(data)

# %%
df = pd.DataFrame(
    data, columns=["timestamp", "open", "hi", "low", "close", "value"]
)

# %%
df

# %%
df.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %% [markdown]
# # Bulk download by script

# %% language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'airflow' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'ccxt' \
#     --start_timestamp '2020-01-01T00:00:00+00:00' \
#     --end_timestamp '2020-01-02T00:10:00+00:00' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --aws_profile 'ck' \
#     --data_type 'ohlcv' \
#     --data_format 'parquet' \
#     --contract_type 'spot' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# ## Check data by reader

# %%
signature = "bulk.airflow.downloaded_1min.parquet.ohlcv.spot.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-01-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2022-02-01T00:10:00+00:00")

# %%
ohlcv_data = reader.read_data(start_timestamp, end_timestamp)

# %%
ohlcv_data.head()

# %%
ohlcv_data.timestamp.agg(["min", "max"]).apply(pd.Timestamp, unit="ms")

# %%
ohlcv_data.isna().all().all()

# %%
