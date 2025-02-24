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
# # Get couple hours worth of trades data

# %%
import im_v2.ccxt.data.extract.extractor as imvcdexex

exchange_id = "kraken"
contract_type = "spot"
ccxt_extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

data_type = "trades"
currency_pair = "BTC/USDT"
start_timestamp = pd.Timestamp("2023-04-26T10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-04-26T15:00:00+00:00")
data = ccxt_extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=10,
)

# %%
data.head()

# %%
data = data.set_index(data.timestamp.apply(pd.Timestamp, unit="ms"), drop=False)

# %%
df_ohlc = data.price.resample("1Min").ohlc()

# %%
df_ohlc.head()

# %%
df_volume = data.amount.resample("1Min").sum()

# %%
resample_data = pd.concat(
    [df_ohlc, df_volume],
    axis=1,
)

# %%
resample_data.rename(columns={"amount": "volume"}, inplace=True)

# %%
result = resample_data.copy()
result["open"] = resample_data["open"].fillna(
    resample_data["close"].ffill(), limit=1
)
result["close"] = resample_data["close"].fillna(
    resample_data["open"].bfill(), limit=1
)

# %%
result["open"] = result["open"].fillna(result["close"].ffill())
result["close"] = result["close"].fillna(result["close"].ffill())

# %%
result["high"] = result["high"].fillna(result[["open", "close"]].max(axis=1))
result["low"] = result["low"].fillna((result[["open", "close"]].min(axis=1)))

# %% [markdown]
# # get some recent OHLCV data from kraken

# %%
data_type = "ohlcv"
currency_pair = "BTC/USDT"
start_timestamp = pd.Timestamp("2023-04-26T10:00:00+00:00")
end_timestamp = pd.Timestamp("2023-04-26T15:00:00+00:00")
data = ccxt_extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=10,
)

# %%
data["timestamp"].agg(["min", "max"]).apply(pd.to_datetime, unit="ms")

# %% [markdown]
# # Compare resampled data and raw data

# %%
data.head()

# %%
data = data.set_index(data.timestamp.apply(pd.Timestamp, unit="ms"), drop=True)


# %%
data = data.drop(columns=["timestamp", "end_download_timestamp"])

# %%
data.head(10)

# %%
result.head(10)

# %%
result.equals(data)

# %%
result.loc[[pd.Timestamp("2023-04-26 10:04:00")]]

# %%
data.loc[[pd.Timestamp("2023-04-26 10:04:00")]]

# %%
result.compare(data)

# %%
data.shape

# %%
resample_data.shape

# %%
resample_data.iloc[-10:]

# %%
data.iloc[-10:]

# %%
data.drop(data.tail(1).index, inplace=True)

# %%
