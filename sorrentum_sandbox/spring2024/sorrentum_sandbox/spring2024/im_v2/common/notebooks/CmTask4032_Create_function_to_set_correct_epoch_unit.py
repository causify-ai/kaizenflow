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

# %% [markdown]
# # Test download_bulk.py

# %% language="bash"
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
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \b
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-02-05T00:30:00+00:00' \
#     --end_timestamp '2023-02-05T00:40:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'trades' \
#     --incremental \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% language="bash"
# /app/im_v2/common/data/extract/download_bulk.py \
#     --download_mode 'bulk' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_1min' \
#     --vendor 'crypto_chassis' \
#     --start_timestamp '2023-02-05T00:30:00+00:00' \
#     --end_timestamp '2023-02-05T00:40:00+00:00' \
#     --exchange_id 'binance' \
#     --universe 'v4' \
#     --aws_profile 'ck' \
#     --data_type 'bid_ask' \
#     --data_format 'parquet' \
#     --contract_type 'futures' \
#     --s3_path 's3://cryptokaizen-data-test/'

# %% [markdown]
# # Test resample_daily_bid_ask_data.py

# %% language="bash"
# /app/im_v2/common/data/transform/resample_daily_bid_ask_data.py \
#     --start_timestamp '20230101-000000' \
#     --end_timestamp '20230102-000000' \
#     --src_dir 's3://cryptokaizen-data/v3/periodic_daily/airflow/downloaded_1sec/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0' \
#     --dst_dir 's3://cryptokaizen-data-test/v3/periodic_daily/airflow/resampled_1min/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0'

# %% language="bash"
# /app/im_v2/common/data/transform/resample_daily_bid_ask_data.py \
#     --start_timestamp '20230101-000000' \
#     --end_timestamp '20230102-000000' \
#     --src_dir 's3://cryptokaizen-data/v3/periodic_daily/airflow/downloaded_1sec/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0' \
#     --dst_dir 's3://cryptokaizen-data-test/v3/periodic_daily/airflow/resampled_1min/parquet/bid_ask/futures/v3/crypto_chassis/binance/v1_0_0'

# %% [markdown]
# # Test im_raw_data_client.py

# %%
signature = (
    "bulk.manual.downloaded_1min.parquet.trades.futures.v7_3.ccxt.binance.v1_0_0"
)
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-03-01T00:00:00+00:00")
end_timestamp = pd.Timestamp("2023-03-01T00:10:00+00:00")
trades = reader.read_data(start_timestamp, end_timestamp)
trades.head()

# %%
signature = "bulk.manual.downloaded_1min.parquet.trades.futures.v4.crypto_chassis.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-02-05T00:30:00+00:00")
end_timestamp = pd.Timestamp("2023-02-05T00:40:00+00:00")
trades = reader.read_data(start_timestamp, end_timestamp)
trades.head()

# %%
