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
# # Read all downloaded websocket data by RawReader

# %%
signature = "periodic_daily.airflow.downloaded_200ms.postgres.ohlcv.futures.v7_3.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-06-19T17:00:00+00:00")
end_timestamp = pd.Timestamp("2023-06-23T12:00+00:00")
tables_names = [
    "ccxt_ohlcv_futures_3sec",
    "ccxt_ohlcv_futures_7sec",
    "ccxt_ohlcv_futures_10sec",
    "ccxt_ohlcv_futures_15sec"
]

# %% [markdown]
# ### 3 seconds

# %%
reader.table_name = tables_names[0]
binance_ohlcv_data_3sec = reader.load_db_table(start_timestamp, end_timestamp)

# %%
_3sec_timestamp_by_pairs = (
    binance_ohlcv_data_3sec.reset_index()[["currency_pair", "timestamp"]]
    .drop_duplicates()
    .sort_values(by=["currency_pair", "timestamp"]).reset_index(drop=True)
)

# %% [markdown]
# ### 7 seconds

# %%
reader.table_name = tables_names[1]
binance_ohlcv_data_7sec = reader.load_db_table(start_timestamp, end_timestamp)
_7sec_timestamp_by_pairs = (
    binance_ohlcv_data_7sec.reset_index()[["currency_pair", "timestamp"]]
    .drop_duplicates()
    .sort_values(by=["currency_pair", "timestamp"]).reset_index(drop=True)
)

# %% [markdown]
# ### 10 seconds

# %%
reader.table_name = tables_names[2]
binance_ohlcv_data_10sec = reader.load_db_table(start_timestamp, end_timestamp)
_10sec_timestamp_by_pairs = (
    binance_ohlcv_data_10sec.reset_index()[["currency_pair", "timestamp"]]
    .drop_duplicates()
    .sort_values(by=["currency_pair", "timestamp"]).reset_index(drop=True)
)

# %% [markdown]
# ### 15 seconds

# %%
reader.table_name = tables_names[3]
binance_ohlcv_data_15sec = reader.load_db_table(start_timestamp, end_timestamp)
_15sec_timestamp_by_pairs = (
    binance_ohlcv_data_15sec.reset_index()[["currency_pair", "timestamp"]]
    .drop_duplicates()
    .sort_values(by=["currency_pair", "timestamp"]).reset_index(drop=True)
)

# %% [markdown]
# # Read bulk downloaded data

# %%
signature = "periodic_daily.airflow.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.binance.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="preprod")
binance_ohlcv_bulk_data = reader.read_data(start_timestamp, end_timestamp)

# %%
bulk_timestamp_by_pairs = (
    binance_ohlcv_bulk_data.reset_index(drop=True)[["currency_pair", "timestamp"]]
    .drop_duplicates()
    .sort_values(by=["currency_pair", "timestamp"]).reset_index(drop=True)
)

# %% [markdown]
# # Analyze

# %% [markdown]
# ## Compare 3 seconds vs daily data
#
# Find rows where the value of one the OHLCVs columns does not match between 3 second data and daily data

# %%
#Define a funciton to filter mismatched rows
ohlcvs_cols = ["open", "low", "high", "close", "volume"]
def filter_mismatched_rows(row):
    for col in ohlcvs_cols:
        if row[f"{col}_3sec"] != row[f"{col}_daily"]:
            return True
    return False


# %%
binance_ohlcv_bulk_data = binance_ohlcv_bulk_data.reset_index(drop=True)
binance_ohlcv_data_3sec = binance_ohlcv_data_3sec.reset_index(drop=True)

# %%
_3sec_daily = pd.merge(
    binance_ohlcv_bulk_data,
    binance_ohlcv_data_3sec,
    on=["currency_pair","timestamp"],
    how="inner",
    suffixes=["_daily", "_3sec"]
)

# %%
_3sec_daily_mismatch = _3sec_daily[_3sec_daily.apply(filter_mismatched_rows, axis=1)]
_3sec_daily_mismatch.shape

# %% [markdown]
# As we can see there is not mismatch.

# %% [markdown]
# ### Date ranges

# %%
_3sec_timestamp_by_pairs.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %%
_7sec_timestamp_by_pairs.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %%
_10sec_timestamp_by_pairs.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %%
_15sec_timestamp_by_pairs.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %%
bulk_timestamp_by_pairs.timestamp.agg(["min", "max"]).apply(pd.to_datetime, unit="ms")


# %%
max(bulk_timestamp_by_pairs.timestamp)

# %%
_3sec_timestamp_by_pairs = _3sec_timestamp_by_pairs[_3sec_timestamp_by_pairs.timestamp <= 1687478340000]

# %%
_7sec_timestamp_by_pairs = _7sec_timestamp_by_pairs[_7sec_timestamp_by_pairs.timestamp <= 1687478340000]

# %%
_10sec_timestamp_by_pairs = _10sec_timestamp_by_pairs[_10sec_timestamp_by_pairs.timestamp <= 1687478340000]

# %%
_15sec_timestamp_by_pairs = _15sec_timestamp_by_pairs[_15sec_timestamp_by_pairs.timestamp <= 1687478340000]

# %% [markdown]
# ### 3 sec

# %%
len(_3sec_timestamp_by_pairs)

# %%
len(bulk_timestamp_by_pairs)

# %% run_control={"marked": true}
_3sec_match = pd.merge(
    bulk_timestamp_by_pairs, _3sec_timestamp_by_pairs,
    how="inner",
    on=["currency_pair", "timestamp"]
)

# %%
_3sec_match.shape

# %% run_control={"marked": true}
_3sec_not_match = pd.merge(
    bulk_timestamp_by_pairs,
    _3sec_timestamp_by_pairs,
    on=['currency_pair','timestamp'],
    how="outer",
    indicator=True
)
_3sec_not_match = _3sec_not_match[_3sec_not_match['_merge']=='left_only']

# %%
_3sec_not_match.shape

# %% [markdown]
# ### 7 sec

# %%
len(_7sec_timestamp_by_pairs)

# %%
len(bulk_timestamp_by_pairs)

# %%
pd.merge(
    bulk_timestamp_by_pairs, _7sec_timestamp_by_pairs,
    how="inner",
    on=["currency_pair", "timestamp"]
).shape

# %% run_control={"marked": true}
_7sec_not_match = pd.merge(
    bulk_timestamp_by_pairs,
    _7sec_timestamp_by_pairs,
    on=['currency_pair','timestamp'],
    how="outer",
    indicator=True
)
_7sec_not_match = _7sec_not_match[_7sec_not_match['_merge']=='left_only']

# %%
_7sec_not_match.shape

# %% [markdown]
# ### 10 sec

# %%
len(_10sec_timestamp_by_pairs)

# %%
len(bulk_timestamp_by_pairs)

# %%
pd.merge(
    bulk_timestamp_by_pairs, _10sec_timestamp_by_pairs,
    how="inner",
    on=["currency_pair", "timestamp"]
).shape

# %% run_control={"marked": true}
_10sec_not_match = pd.merge(
    bulk_timestamp_by_pairs,
    _10sec_timestamp_by_pairs,
    on=['currency_pair','timestamp'],
    how="outer",
    indicator=True
)
_10sec_not_match = _3sec_not_match[_10sec_not_match['_merge']=='left_only']

# %%
_10sec_not_match.shape

# %% [markdown]
# ### 15 sec

# %%
len(_15sec_timestamp_by_pairs)

# %%
len(bulk_timestamp_by_pairs)

# %%
pd.merge(
    bulk_timestamp_by_pairs, _15sec_timestamp_by_pairs,
    how="inner",
    on=["currency_pair", "timestamp"]
).shape

# %% run_control={"marked": true}
_15sec_not_match = pd.merge(
    bulk_timestamp_by_pairs,
    _15sec_timestamp_by_pairs,
    on=['currency_pair','timestamp'],
    how="outer",
    indicator=True
)
_15sec_not_match = _15sec_not_match[_15sec_not_match['_merge']=='left_only']

# %%
_15sec_not_match.shape
