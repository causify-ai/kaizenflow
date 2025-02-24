# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Importing Libraries

# %%
import ccxt
import pandas as pd

import im_v2.ccxt.data.extract.cryptocom_extractor as imvcdecrex
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe.universe as imvcounun

# %%
ccxt.__version__

# %%
ccxt_exchange = ccxt.cryptocom()


# %% [markdown]
# ## Function to get error percentage between data downlaoded from websocket and data downloaded from REST api calls


# %%
def get_error(REST_ohlcv, fil_data):
    merged_df = pd.merge(REST_ohlcv, fil_data, on="timestamp")
    #     print(merged_df)
    merged_df["open_error"] = (
        100 * abs(merged_df["open_x"] - merged_df["open_y"]) / merged_df["open_y"]
    )
    merged_df["high_error"] = (
        100 * abs(merged_df["high_x"] - merged_df["high_y"]) / merged_df["high_y"]
    )
    merged_df["low_error"] = (
        100 * abs(merged_df["low_x"] - merged_df["low_y"]) / merged_df["low_y"]
    )
    merged_df["close_error"] = (
        100
        * abs(merged_df["close_x"] - merged_df["close_y"])
        / merged_df["close_y"]
    )
    merged_df["volume_error"] = (
        100
        * abs(merged_df["volume_x"] - merged_df["volume_y"])
        / merged_df["volume_y"]
    )
    print("Avg Open error  :", merged_df["open_error"].mean().round(2))
    print("Avg Close error :", merged_df["close_error"].mean().round(2))
    print("Avg High error  :", merged_df["high_error"].mean().round(2))
    print("Avg Low error   :", merged_df["low_error"].mean().round(2))
    print("Avg Volume error:", merged_df["volume_error"].mean().round(2))


# %%
def ohlcv_cross_data_qa(
    start_time,
    end_time,
    symbol,
    exchange,
    *,
    signature="realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7_4.ccxt.cryptocom.v1_0_0",
    stage="test",
):
    data_reader = imvcdcimrdc.RawDataReader(signature, stage=stage)
    ohlcv_trades_data = data_reader.read_data(
        pd.Timestamp(start_time), pd.Timestamp(end_time)
    )
    filtered_data = ohlcv_trades_data[
        ohlcv_trades_data["currency_pair"] == symbol
    ]
    REST_ohlcv = exchange.download_data(
        data_type="ohlcv",
        currency_pair=symbol,
        exchange_id="cryptocom",
        start_timestamp=pd.Timestamp(start_time),
        end_timestamp=pd.Timestamp(end_time),
        depth=1,
    )
    print("Error % for symbol:", symbol)
    get_error(REST_ohlcv, filtered_data)


# %% [markdown]
# ## Getting list of symbols from desired Universe

# %%
vendor_name = "CCXT"
mode = "download"
version = "v7.4"
universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
universe_list = universe["cryptocom"]
len(universe_list)
universe_list

# %% [markdown]
# ## QA Check

# %%
start_time = "2024-01-17T20:10:00+05:30"
end_time = "2024-01-17T20:40:00+05:30"
exchange = imvcdecrex.CryptocomCcxtExtractor("cryptocom", "futures")
for symbol in universe_list:
    ohlcv_cross_data_qa(start_time, end_time, symbol, exchange)

# %%
