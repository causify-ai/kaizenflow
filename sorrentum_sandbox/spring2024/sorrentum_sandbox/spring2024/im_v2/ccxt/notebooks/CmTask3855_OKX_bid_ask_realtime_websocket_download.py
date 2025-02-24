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
# # Download realtime data

# %% [markdown]
# ## Script

# %% language="bash"
# /app/im_v2/ccxt/data/extract/download_exchange_data_to_db_periodically.py \
#     --download_mode 'realtime' \
#     --downloading_entity 'manual' \
#     --action_tag 'downloaded_200ms' \
#     --vendor 'ccxt' \
#     --exchange_id 'okx' \
#     --universe 'v7.3' \
#     --db_stage 'test' \
#     --db_table 'ccxt_bid_ask_futures_raw' \
#     --aws_profile 'ck' \
#     --data_type 'bid_ask' \
#     --data_format 'postgres' \
#     --contract_type 'futures' \
#     --start_time "$(date -d 'today + 1 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --stop_time "$(date -d 'today + 5 minutes' +'%Y-%m-%d %H:%M:00+00:00')" \
#     --method 'websocket'

# %% [markdown] heading_collapsed=true
# ## Manually by extractor

# %% hidden=true
exchange_id = "okx"
contract_type = "futures"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% hidden=true
extractor._async_exchange.has["watchOrderBook"]

# %% hidden=true
currency_pair = "BTC/USDT"
bid_ask_depth = 10
d1 = await extractor._async_exchange.watch_order_book(
    currency_pair, bid_ask_depth
)

# %% hidden=true
d2 = extractor._async_exchange.orderbooks["BTC/USDT"]

# %% hidden=true
d1.keys()

# %% hidden=true
len(d1["bids"])

# %% hidden=true
d1["timestamp"]

# %% hidden=true
d1["datetime"]

# %% hidden=true
d1["symbol"]

# %% hidden=true
d1["bids"][:10]

# %% hidden=true
d1["asks"][:10]

# %% hidden=true
len(d2["bids"])

# %% [markdown]
# ## Preview data from DB

# %%
signature = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.okx.v1_0_0"
reader = imvcdcimrdc.RawDataReader(signature, stage="test")
start_timestamp = pd.Timestamp("2023-02-26 00:26:00+07:00")
end_timestamp = pd.Timestamp("2023-02-28 00:31:00+07:00")

# %%
bid_ask_data = reader.read_data(start_timestamp, end_timestamp)

# %%
bid_ask_data.head()

# %% [markdown]
# # QA

# %% [markdown]
# ## Levels

# %% [markdown]
# ### Count nan's

# %%
price_size_columns = [
    f"{column_type}{level}"
    for level in range(1, 11)
    for column_type in ["bid_size_l", "ask_size_l", "bid_price_l", "ask_price_l"]
]

# %%
sum(bid_ask_data[price_size_columns].isna().any())

# %% [markdown]
# ### Count nan's per symbol

# %%
data_nan = bid_ask_data[price_size_columns].isnull()
data_nan["currency_pair"] = bid_ask_data["currency_pair"]

# %%
data_nan.groupby(["currency_pair"]).sum().all().all()

# %%
data_nan.groupby(["currency_pair"]).sum()

# %% [markdown]
# # Exploratory analysis

# %% [markdown]
# ## Check all timestamps for a given time interval are present use helpers.hpandas::find_gaps_in_time_series

# %%
bid_ask_timestamp = pd.Series(bid_ask_data.index)

# %%
timestamp_min_max = bid_ask_timestamp.agg(["min", "max"]).apply(
    pd.Timestamp, unit="ms"
)

# %%
start_ts = pd.Timestamp(timestamp_min_max["min"])
end_ts = pd.Timestamp(timestamp_min_max["max"])
freq = "200ms"
rt_data_gaps = hpandas.find_gaps_in_time_series(
    pd.Series(bid_ask_timestamp.unique()),
    start_ts,
    end_ts,
    freq,
)

# %%
rt_data_gaps

# %%
len(rt_data_gaps)

# %%
rt_data_gaps.to_frame().head()

# %%
start_ts = int(pd.Timestamp("2023-02-24 18:36:05.201").timestamp() * 1000)
end_ts = int(pd.Timestamp("2023-02-24 18:36:06.001").timestamp() * 1000)

# %%
start_ts

# %%
pd.Series(
    bid_ask_timestamp[bid_ask_timestamp.between(start_ts, end_ts)].unique()
).apply(pd.Timestamp, unit="ms")

# %% [markdown]
# ## Check logical correctness of the data. I think it makes sense to have this packed into a single check
# - Assure bid_size =/= 0 =/= ask_size for each level (where the values is not Nan)
# - Assure bid_price <= ask_price for each level

# %%
size_columns = [
    f"{column_type}{level}"
    for level in range(1, 11)
    for column_type in ["bid_size_l", "ask_size_l"]
]

# %%
bid_ask_data[size_columns].all().all()

# %%
price_check_columns = [f"price_check_{level}" for level in range(1, 11)]

# %%
bid_ask_data[
    bid_ask_data[[f"bid_price_l1", f"ask_price_l1"]].isnull().all(axis=1)
]

# %%
bid_ask_data[
    bid_ask_data[[f"bid_price_l{level}", f"bid_price_l{level}"]]
    .notna()
    .all(axis=1)
].head()

# %%
for level in range(1, 11):
    bid_ask_data[f"price_check_{level}"] = (
        bid_ask_data[f"bid_price_l{level}"] <= bid_ask_data[f"ask_price_l{level}"]
    )

# %%
bid_ask_data[price_check_columns].all()

# %% [markdown]
# ## Check there are no NaN values
#
# For the most liquid assets, like BTC and ETH count the number of NaNs for a given few minute data sample,
# expected outcome is that there is close to 0 missing values for these assets, for all levels.

# %%
bid_ask_data[size_columns].notna().all().all()
