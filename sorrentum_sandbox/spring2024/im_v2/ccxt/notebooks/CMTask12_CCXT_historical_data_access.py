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


# %% [markdown]
# ## Functions

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

# %%
binance_data = download_ohlcv_data(
    "binance", "2018-01-01T00:00:00Z", "2018-02-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# ### Kraken

# %%
kraken_data = download_ohlcv_data(
    "kraken", "2018-01-01T00:00:00Z", "2018-02-01T00:00:00Z", "BTC/USDT"
)

# %% [markdown]
# Kraken data seems to be corrupted in some way, since `fetch_trades` method does not behave the same, parsing dates incorrectly. Investigate.

# %% [markdown]
# ## Trade data

# %% [markdown]
# ### Binance

# %%
binance_trade = download_trade_data(
    "binance", "2018-01-01T00:00:00Z", "2018-02-01T00:00:00Z", "BTC/USDT"
)

# %%
binance_trade = download_trade_data(
    "binance",
    "2018-01-01T00:00:00Z",
    "2018-01-01T02:00:00Z",
    "BTC/USDT",
    step=1000,
)

# %% [markdown]
# ## Bids/asks

# %%
binance = log_into_exchange("binance")
binance.fetch_bids_asks("BTC/USDT")

# %% [markdown]
# Fetching bids and asks is available only for real-time data.

# %% [markdown]
# ## TODO:
#
# Check trades and OHLCV for other exchanges in the list.
