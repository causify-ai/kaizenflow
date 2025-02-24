# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging
import time

import ccxt

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
ALL_EXCHANGES = [
    "binance",
    "coinbase",
    "kraken",
    "huobi",
    "ftx",
    "kucoin",
    "bitfinex",
    "gateio",
    # "binanceus" # no API access for these three exchanges.
    # "bithumb"
    # "bitstamp"
]

# %%
credentials = hio.from_json("API_keys.json")


# %% [markdown]
# ## Functions

# %% [markdown]
# These are the functions introduced in `CMTask12_CCXT_historical_data_access.ipynb`

# %%
def log_into_exchange(exchange_id: str):
    """
    Log into exchange via ccxt.
    """
    credentials = hio.from_json("API_keys.json")
    hdbg.dassert_in(exchange_id, credentials, msg="%s exchange ID not correct.")
    credentials = credentials[exchange_id]
    credentials["rateLimit"] = True
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class(credentials)
    hdbg.dassert(
        exchange.checkRequiredCredentials(),
        msg="Required credentials not passed.",
    )
    return exchange


def describe_exchange_data(exchange_id: str):
    """ """
    exchange = log_into_exchange(exchange_id)
    print("%s:" % exchange_id)
    print("Has fetchOHLCV: %s" % exchange.has["fetchOHLCV"])
    print("Has fetchTrades: %s" % exchange.has["fetchTrades"])
    print("Available timeframes:")
    print(exchange.timeframes)
    print("Available currency pairs:")
    print(exchange.load_markets().keys())
    print("=" * 50)
    return None


def download_ohlcv_data(
    exchange_id,
    start_date,
    end_date,
    curr_symbol,
    timeframe="1m",
    step=500,
    sleep_time=3,
):
    """
    Download historical OHLCV data for given time period and currency.
    """
    exchange = log_into_exchange(exchange_id)
    hdbg.dassert_in(timeframe, exchange.timeframes)
    hdbg.dassert(exchange.has["fetchOHLCV"])
    hdbg.dassert_in(curr_symbol, exchange.load_markets().keys())
    start_date = exchange.parse8601(start_date)
    end_date = exchange.parse8601(end_date)
    # Convert to ms.
    duration = exchange.parse_timeframe(timeframe) * 1000
    all_candles = []
    for t in range(start_date, end_date + duration, duration * step):
        candles = exchange.fetch_ohlcv(curr_symbol, timeframe, t, step)
        print("Fetched", len(candles), "candles")
        if candles:
            print(
                "From",
                exchange.iso8601(candles[0][0]),
                "to",
                exchange.iso8601(candles[-1][0]),
            )
        all_candles += candles
        total_length = len(all_candles)
        print("Fetched", total_length, "candles in total")
        time.sleep(sleep_time)
    return all_candles


def download_trade_data(
    exchange_id,
    start_date,
    end_date,
    curr_symbol,
    timeframe="1m",
    step=500,
    sleep_time=3,
):
    """
    Download historical data for given time period and currency.
    """
    exchange = log_into_exchange(exchange_id)
    hdbg.dassert_in(timeframe, exchange.timeframes)
    hdbg.dassert(exchange.has["fetchTrades"])
    hdbg.dassert_in(curr_symbol, exchange.load_markets().keys())
    start_date = exchange.parse8601(start_date)
    end_date = exchange.parse8601(end_date)
    latest_trade = start_date
    all_trades = []
    while latest_trade <= end_date:
        trades = exchange.fetch_trades(
            curr_symbol,
            since=latest_trade,
            limit=step,
            params={"endTime": latest_trade + 36000},
        )
        print("Fetched", len(trades), "trades")
        if trades:
            print(
                "From",
                exchange.iso8601(trades[0]["timestamp"]),
                "to",
                exchange.iso8601(trades[-1]["timestamp"]),
            )
            latest_trade = trades[-1]["timestamp"]
        all_trades += trades
        total_length = len(all_trades)
        print("Fetched", total_length, "trades in total")
        time.sleep(sleep_time)
    return all_trades


# %% [markdown]
# ## Check availability of historical data for exchanges

# %%
credentials = hio.from_json("API_keys.json")

# %%
for e in ALL_EXCHANGES:
    describe_exchange_data(e)

# %% [markdown]
# ### Checking data availability at coinbase

# %%
coinbase = log_into_exchange("coinbase")

# %%
coinbase.has

# %% [markdown]
# `coinbase` exchange does not provide any kind of historical data (neither on OHLCV nor on trading orders), and it seems that its API allows only for trading.

# %% [markdown]
# ## Loading OHLCV data

# %% [markdown]
# ### Binance

# %% [markdown]
# Binance data is being loaded correctly with specified functions.

# %%
binance_data = download_ohlcv_data(
    "binance", "2018-01-01T00:00:00Z", "2018-02-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# ### Huobi

# %% [markdown]
# For Huobi we see that the data is starting to be loaded from incorrect and a very recent time period that does not belong to the specified time range.

# %%
huobi_data = download_ohlcv_data(
    "huobi", "2021-01-01T00:00:00Z", "2021-02-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# The reason behind it is that Huobi outputs candles in reverced order.<br>
# To demonstrate it let's run `fetch_ohlcv()` for Huobi with differnt limits.

# %%
huobi_exchange = log_into_exchange("huobi")
start_date = huobi_exchange.parse8601("2021-01-01T00:00:00Z")
limit1 = 500
limit2 = 1000
limit3 = 2000

# %%
huobi_all_data1 = huobi_exchange.fetch_ohlcv("BTC/USDT", "1m", start_date, limit1)
huobi_all_data2 = huobi_exchange.fetch_ohlcv("BTC/USDT", "1m", start_date, limit2)
huobi_all_data3 = huobi_exchange.fetch_ohlcv("BTC/USDT", "1m", start_date, limit3)

# %% [markdown]
# The amount of loaded candles is equal to the specified limit, so the data is available.

# %%
print(len(huobi_all_data1))
print(len(huobi_all_data2))
print(len(huobi_all_data3))

# %% [markdown]
# However, if we take a look at the timestamps of the first and the last candles, we see that the last candle is always the most recent one while the first one is equal to the most recent candle's timestamp munis the rime range specified in the request.

# %%
huobi_first_candle_date1 = huobi_exchange.iso8601(huobi_all_data1[0][0])
print(huobi_first_candle_date1)
#
huobi_first_candle_date2 = huobi_exchange.iso8601(huobi_all_data2[0][0])
print(huobi_first_candle_date2)
#
huobi_first_candle_date3 = huobi_exchange.iso8601(huobi_all_data3[0][0])
print(huobi_first_candle_date3)

# %%
huobi_last_candle_date1 = huobi_exchange.iso8601(huobi_all_data1[-1][0])
print(huobi_last_candle_date1)
#
huobi_last_candle_date2 = huobi_exchange.iso8601(huobi_all_data2[-1][0])
print(huobi_last_candle_date2)
#
huobi_last_candle_date3 = huobi_exchange.iso8601(huobi_all_data3[-1][0])
print(huobi_last_candle_date3)

# %% [markdown]
# This is confirmed by calculation of steps between the last and first candles timestamps

# %%
print((huobi_all_data1[-1][0] - huobi_all_data1[0][0]) / 60 / 1000 + 1)
print((huobi_all_data2[-1][0] - huobi_all_data2[0][0]) / 60 / 1000 + 1)
print((huobi_all_data3[-1][0] - huobi_all_data3[0][0]) / 60 / 1000 + 1)

# %% [markdown]
# Therefore, it seems that Huobi data can be loaded, but additional research is needed to understand, how to do it correctly and it definitely needs a 'personal' approach.

# %% [markdown]
# ### FTX

# %% [markdown]
# FTX data is being loaded correctly, we have it starting from 2020-03-28 14:40:00

# %%
ftx_data = download_ohlcv_data(
    "ftx", "2020-03-28T00:00:00Z", "2020-04-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# ### Kucoin

# %% [markdown]
# Kucoin data is being loaded correctly as well.

# %%
kucoin_data2021 = download_ohlcv_data(
    "kucoin", "2021-01-01T00:00:00Z", "2021-01-04T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# However, the amount of candles for earlier periods is unstable and timestamps are slipping. Additional research is required to understand if the data is really missing or its some sort of a bug.

# %%
kucoin_data2018 = download_ohlcv_data(
    "kucoin", "2018-01-01T00:00:00Z", "2018-01-04T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# ### Bitfinex

# %% [markdown]
# The Bitfinex candles are being loaded with overlapping time periods.

# %%
bitfinex_data = download_ohlcv_data(
    "bitfinex", "2020-01-01T00:00:00Z", "2020-02-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# To research this let's check the amount of minute steps between the last candle timestamp and the first one.

# %%
bitfinex_exchange = log_into_exchange("bitfinex")
start_date = bitfinex_exchange.parse8601("2021-01-01T00:00:00Z")
limit1 = 500
limit2 = 1000
limit3 = 2000

# %%
bitfinex_all_data1 = bitfinex_exchange.fetch_ohlcv(
    "BTC/USDT", "1m", start_date, limit1
)
bitfinex_all_data2 = bitfinex_exchange.fetch_ohlcv(
    "BTC/USDT", "1m", start_date, limit2
)
bitfinex_all_data3 = bitfinex_exchange.fetch_ohlcv(
    "BTC/USDT", "1m", start_date, limit3
)

# %%
print(len(bitfinex_all_data1))
print(len(bitfinex_all_data2))
print(len(bitfinex_all_data3))

# %%
bitfinex_first_candle_date1 = bitfinex_exchange.iso8601(bitfinex_all_data1[0][0])
print(bitfinex_first_candle_date1)
#
bitfinex_first_candle_date2 = bitfinex_exchange.iso8601(bitfinex_all_data2[0][0])
print(bitfinex_first_candle_date2)
#
bitfinex_first_candle_date3 = bitfinex_exchange.iso8601(bitfinex_all_data3[0][0])
print(bitfinex_first_candle_date3)

# %%
bitfinex_last_candle_date1 = bitfinex_exchange.iso8601(bitfinex_all_data1[-1][0])
print(bitfinex_last_candle_date1)
#
bitfinex_last_candle_date2 = bitfinex_exchange.iso8601(bitfinex_all_data2[-1][0])
print(bitfinex_last_candle_date2)
#
bitfinex_last_candle_date3 = bitfinex_exchange.iso8601(bitfinex_all_data3[-1][0])
print(bitfinex_last_candle_date3)

# %% [markdown]
# Turns out that the amount of minute steps betweent the last and the firt candles is higher than the specified limits. One possible reason is that Bitfinex has gaps in its data. However, if this is true, why the behaviour for Kucoin was correct since there is a clear gap in data for it in 2018?
# Thus, this should be researched.

# %%
print((bitfinex_all_data1[-1][0] - bitfinex_all_data1[0][0]) / 60 / 1000 + 1)
print((bitfinex_all_data2[-1][0] - bitfinex_all_data2[0][0]) / 60 / 1000 + 1)
print((bitfinex_all_data3[-1][0] - bitfinex_all_data3[0][0]) / 60 / 1000 + 1)

# %% [markdown]
# Still, we see that Bitfinex has data and it is more than possible to extract it. Here we wanted to develop a unified approach for loading data from different exchanges. If this doesn't work for Bitfinex, there is and example guide in CCXT library https://github.com/ccxt/ccxt/blob/master/examples/py/fetch-bitfinex-ohlcv-history.py that we can use to develop a 'personal' approach to this exchange. So we're good here.

# %% [markdown]
# ### Gateio

# %% [markdown]
# Gateio data is being loaded correctly, we have it starting from 2021-06-05 13:33:00

# %%
gateio_data = download_ohlcv_data(
    "gateio", "2021-06-05T00:00:00Z", "2021-06-10T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# ### Kraken

# %% [markdown]
# Kraken provides only 720 of candles into the past for any selected time step. (see https://github.com/ccxt/ccxt/issues/8091#issuecomment-739600165)<br>
# We can track its data further on but there is no way to get its historical data further than that.

# %%
kraken_exchange = log_into_exchange("kraken")
start_date = kraken_exchange.parse8601("2020-01-01T00:00:00Z")
kraken_all_data = kraken_exchange.fetch_ohlcv("BTC/USDT", "1m", start_date, 1000)

# %%
len(kraken_all_data)

# %% [markdown]
# The first and the last candles timstamps are being updated all the time, no matter which start date you specify in the query.

# %%
kraken_first_candle_date = kraken_exchange.iso8601(kraken_all_data[0][0])
kraken_first_candle_date

# %%
kraken_last_candle_date = kraken_exchange.iso8601(kraken_all_data[-1][0])
kraken_last_candle_date

# %% [markdown]
# ## Summary

# %% [markdown]
# - We can apply sort of a unified approach to load all the historical data for Binance, FTX, Kucoin, and Gateio. Although, Kucoin case should be investigated a bit more in order to confirm that there is no bug.
# - Huobi and Bitfinex seem to have the data to provide but they require a 'personal' approaches that need to be developed.
# - Kraken provides only 720 last candles for a specified time step. We may decide to track it from acertain moment or just forget about it in terms of historical data.
# - Coinbase exchange does not provide any kind of historical data.

# %%
