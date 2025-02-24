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

# %%
# adhoc to get latest CCXT version.
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade ccxt)"

# %%
import ccxt
import pandas as pd

import helpers.hdatetime as hdateti
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe.universe as imvcounun

# %%
ccxt.__version__

# %%
ccxt_exchange = ccxt.binance()


# %% run_control={"marked": true}
def get_ohlcv_data(symbol, start_time, end_time):
    since = hdateti.convert_timestamp_to_unix_epoch(pd.Timestamp(start_time))
    end = hdateti.convert_timestamp_to_unix_epoch(pd.Timestamp(end_time))
    limit = int((end - since) / 60000) + 1
    ohlcv = pd.DataFrame(
        ccxt_exchange.fetch_ohlcv(symbol, "1m", since=since, limit=limit)
    )
    ohlcv.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    return ohlcv


# %%
def get_trades_data(symbol, since):
    #     since = hdateti.convert_timestamp_to_unix_epoch(pd.Timestamp(start_time))
    trades = []
    last_data_id = None
    while True:
        if last_data_id is None:
            # Start from beginning, get the data from the start timestamp.
            data = ccxt_exchange.fetch_trades(
                symbol,
                since=since,
                limit=1000,
            )
        else:
            params = {"fromId": last_data_id}
            data = ccxt_exchange.fetch_trades(symbol, limit=1000, params=params)
        last_data_id = int(data[-1]["id"]) + 1
        trades.extend(data)
        if data[-1]["timestamp"] > since + 60000:
            break
    return trades


# %%
def get_error(REST_ohlcv, fil_data):
    merged_df = pd.merge(REST_ohlcv, fil_data, on="timestamp")
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
    diff = merged_df[abs(merged_df["high_x"] - merged_df["high_y"]) > 1e-2]
    print(diff)
    data = fil_data[fil_data["timestamp"].isin(diff["timestamp"])]
    print(data)
    return diff, data


#     import pdb;pdb.set_trace()


# %%
def ohlcv_cross_data_qa(
    start_time,
    end_time,
    symbol,
    *,
    signature="realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7_4.ccxt.binance.v1_0_0",
    stage="test",
):
    data_reader = imvcdcimrdc.RawDataReader(signature, stage=stage)
    ohlcv_trades_data = data_reader.read_data(
        pd.Timestamp(start_time), pd.Timestamp(end_time)
    )
    filtered_data = ohlcv_trades_data[
        ohlcv_trades_data["currency_pair"] == symbol
    ]
    print(
        (
            filtered_data["knowledge_timestamp"]
            - filtered_data["end_download_timestamp"]
        ).mean()
    )
    symbol_rest = symbol.replace("_", "/") + ":USDT"
    REST_ohlcv = get_ohlcv_data(symbol_rest, start_time, end_time)
    print("Error % for symbol:", symbol)
    #     import pdb;pdb.set_trace()
    print(filtered_data)
    #     import pdb;pdb.set_trace()
    return get_error(REST_ohlcv, filtered_data)


# %%
vendor_name = "CCXT"
mode = "download"
version = "v7.3"
universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
universe_list = universe["binance"]
universe_list = ["ETH_USDT"]
len(universe_list)


# %%
start_time = "2024-03-05T10:00:00+00:00"
end_time = "2024-03-05T13:10:00+00:00"
for symbol in universe_list:
    diff, data = ohlcv_cross_data_qa(start_time, end_time, symbol)

# %%
diff[
    [
        "timestamp",
        "open_x",
        "high_x",
        "low_x",
        "close_x",
        "volume_x",
        "open_y",
        "high_y",
        "low_y",
        "close_y",
        "volume_y",
    ]
].tail(10)

# %%
data

# %%
trades = get_trades_data("ETH/USDT:USDT", 1709480580000)

# %%
len(trades)

# %%
trades[29]

# %%
ccxt_exchange.build_ohlcvc(trades)

# %%
import im_v2.ccxt.data.extract.extractor as imvcdexex

extractor = imvcdexex.CcxtExtractor("binance", "futures")


# %%
trades_df = extractor._fetch_trades(
    "ETH_USDT",
    start_timestamp="2024-02-29T11:31:00+00:00",
    end_timestamp="2024-02-29T11:33:00+00:00",
)

# %%
import pickle

trades = pickle.load(open("../../../../../../trades.pkl", "rb"))

# %%
len(trades)

# %%
ccxt_exchange.build_ohlcvc(trades, since=1709231580000)

# %%
from tqdm import tqdm

my_trades = []
for trade in tqdm(trades):
    if (
        trade["timestamp"] >= 1709231580000
        and trade["timestamp"] <= 1709231580000 + 60100
    ):
        my_trades.append(trade)

# %%
len(my_trades)

# %%
my_trades[0]


# %%
df = pd.DataFrame(my_trades)

# %%
df = df[
    ["timestamp", "datetime", "symbol", "id", "side", "price", "amount", "cost"]
]
df = df.drop_duplicates()

# %%
len(df)

# %%
trades_ts = df.to_dict(orient="records")

# %%
ccxt_exchange.build_ohlcvc(trades_ts)

# %%
trades_ts[:20]

# %%
trades[:10]

# %%
trades[-530:-510]

# %%
trades_ts[-32:-12]

# %%
import requests


def fetch_all_trades(symbol, start_time, end_time):
    limit = 1000  # Maximum number of trades per request
    all_trades = []  # List to store all trades

    while True:
        url = f"https://fapi.binance.com/fapi/v1/aggTrades?symbol={symbol}&startTime={start_time}&endTime={end_time}&limit={limit}"
        response = requests.get(url)

        if response.status_code == 200:
            trades_data = response.json()
            all_trades.extend(trades_data)

            # Check if all trades are fetched
            if len(trades_data) < limit:
                break  # Exit loop if fewer trades than limit are returned

            # Update start_time for next request
            start_time = trades_data[-1]["T"]

        else:
            print(
                f"Failed to fetch trades data. Status code: {response.status_code}"
            )
            return None

    all_trades = pd.DataFrame(all_trades)
    all_trades = all_trades.drop_duplicates()
    all_trades = all_trades.to_dict(orient="records")
    return all_trades


# %%
trades_api = fetch_all_trades("ETHUSDT", 1709480580000, 1709480580000 + 60000)

# %%
len(trades_api)

# %%
trades_api[-1]

# %%
trades[5490]

# %%
import pickle

trades_ccxt_ws = pickle.load(open("../../../../../../trades_ccxt.pkl", "rb"))

# %%
len(trades_ccxt_ws)

# %%
trades_ccxt_ws[0]

# %%
from tqdm import tqdm

my_trades = []
for trade in tqdm(trades_ccxt_ws):
    if (
        trade["timestamp"] >= 1709640960000
        and trade["timestamp"] <= 1709640960000 + 60000
    ):
        my_trades.append(trade)

# %%
len(my_trades)

# %%
df = pd.DataFrame(my_trades)

# %%
df = df[
    ["timestamp", "datetime", "symbol", "id", "side", "price", "amount", "cost"]
]
df = df.drop_duplicates()

# %%
len(df)

# %%
trades_ws_ccxt = df.to_dict(orient="records")

# %%
trades_ws_ccxt

# %%
df_full = pd.read_csv("../../../../../../trades_data_ws_binance.csv")

# %%
df_full

# %%
df = df_full[
    ((df_full["T"] >= 1709640960000) & (df_full["T"] <= (1709640960000 + 60000)))
]

# %%
len(df)

# %%
df["timestamp"] = df["T"]
df["id"] = df["t"]
df["price"] = df["p"]
df["amount"] = df["q"]

# %%

# %%
trades_ws_binance = df.to_dict(orient="records")

# %%
ccxt_exchange.build_ohlcvc(trades_ws_binance)

# %%
ccxt_exchange.build_ohlcvc(trades_ws_ccxt)

# %%
for trade in trades_ws_ccxt:
    if trade["price"] == 7042.67:
        print(trade)

# %%
536.6359999999945 - 536.5779999999986


# %%
def found_trade_id(id):
    for trade in trades_ws_binance:
        if trade["l"] >= id and trade["f"] <= id:
            return True
    return False


# %%
for id in range(3691724382, 3691725689 + 1):
    if not found_trade_id(id):
        print(id)

# %%
trades_ws_ccxt

# %%
trades_error = {"binance": trades_ws_binance, "ccxt": trades_ws_ccxt}
pickle.dump(trades_error, open("trades_error_1709640960000.pkl", "wb"))

# %%
df_agg_trade = pd.read_csv("trades_data_ws_binance_agg_trade.csv")
df_trade = pd.read_csv("trades_data_ws_binance_trade.csv")

# %%
df_agg_trade.head()

# %%
df_trade.head()

# %%
df_agg_trade["timestamp"] = df_agg_trade["T"]
df_agg_trade["id"] = df_agg_trade["l"]
df_agg_trade["price"] = df_agg_trade["p"]
df_agg_trade["amount"] = df_agg_trade["q"]
agg_trades_binance = df_agg_trade.to_dict(orient="records")

# %%
df_trade["timestamp"] = df_trade["T"]
df_trade["id"] = df_trade["t"]
df_trade["price"] = df_trade["p"]
df_trade["amount"] = df_trade["q"]
trades_binance = df_trade.to_dict(orient="records")

# %%
ohlcv_agg_trade = pd.DataFrame(
    ccxt_exchange.build_ohlcvc(agg_trades_binance),
    columns=["timestamp", "open", "high", "low", "close", "volume", "count"],
)
ohlcv_trade = pd.DataFrame(
    ccxt_exchange.build_ohlcvc(trades_binance),
    columns=["timestamp", "open", "high", "low", "close", "volume", "count"],
)

# %%
ohlcv_agg_trade

# %%
ohlcv_trade

# %%
get_error(ohlcv_agg_trade, ohlcv_trade)

# %%
df_trade.tail()

# %%
df_agg_trade.tail()

# %%
