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
# # Imports

# %% [markdown]
# ## Update CCXT to latest version

# %%
# adhoc to get latest CCXT version.
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade ccxt)"

# %%
import ccxt
import pandas as pd

import im_v2.ccxt.data.extract.extractor as imvcdexex

ccxt.__version__

# %% [markdown]
# ## All available exchanges

# %%
print(ccxt.exchanges)

# %% [markdown]
# # binanceus REST

# %% [markdown]
# ## binanceus REST spot

# %%
exchange_id = "binanceus"
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### binanceus REST spot Bid Ask

# %%
currency_pair = "BTC_USDT"
# currency_pair_for_download = extractor.convert_currency_pair(currency_pair)
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 01:00:00")
bid_ask_depth = 10
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %% [markdown]
# ### binanceus REST spot OHLCV

# %%
data_type = "ohlcv"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %% [markdown]
# ### binanceus REST spot Trades

# %%
ccxt_exchange = ccxt.binanceus()
data = pd.DataFrame(ccxt_exchange.fetch_trades("BTC/USDT"))

# %%
data.head()

# %% [markdown]
# # bybit REST

# %%
exchange_id = "bybit"

# %% [markdown]
# ## bybit REST spot

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### bybit REST spot  Bid Ask

# %%
pd.Series(extractor.get_exchange_currency_pairs()).head()

# %%
# currency_pair = "BTC_USDT"
# currency_pair_for_download = extractor.convert_currency_pair(currency_pair)
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 01:00:00")
currency_pair_for_download = "BTC_USDT"
bid_ask_depth = 10
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair_for_download,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data

# %%
bybit_exchange = ccxt.bybit()

# %%
pd.DataFrame(bybit_exchange.load_markets().keys()).head()

# %%
currency_pair = "BTC/USDT:USDT"
pd.DataFrame(bybit_exchange.fetch_order_book(currency_pair)).head()

# %% [markdown]
# ### bybit REST spot OHLCV

# %%
pd.DataFrame(bybit_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### bybit REST spot Trades

# %%
bybit_exchange.has["fetchTrades"]

# %%
pd.DataFrame(bybit_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
# ## bybit REST Futures

# %%
[key for key in bybit_exchange.has if "futur" in key.lower()]

# %%
bybit_exchange.has["future"]


# %% [markdown]
# ### bybit REST Futures Bid Ask

# %%
help(bybit_exchange.fetch_order_book)

# %%
currency_pair = "BTC/USDT:USDT"
future_params = {"options": {"defaultType": "future"}}
pd.DataFrame(
    bybit_exchange.fetch_order_book(currency_pair, 10, future_params)
).head()

# %% [markdown]
# ### bybit REST Futures OHLCV

# %%
help(bybit_exchange.fetch_ohlcv)

# %%
pd.DataFrame(
    bybit_exchange.fetch_ohlcv(currency_pair, "1m", params=future_params)
).head()
# pd.DataFrame(bybit_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### bybit REST Futures trades

# %%
pd.DataFrame(
    bybit_exchange.fetch_trades(currency_pair, params=future_params)
).head()

# %% [markdown]
# # kucoin REST

# %%
exchange_id = "kucoin"

# %% [markdown]
# ## kucoin REST SPOT

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### kucoin REST SPOT Bid Ask

# %%
currency_pair = "BTC_USDT"
# currency_pair_for_download = extractor.convert_currency_pair(currency_pair)
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 01:00:00")
bid_ask_depth = 20
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %% [markdown]
# ### kucoin REST SPOT OHLCV

# %%
data_type = "ohlcv"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
)
data.head()

# %% [markdown]
# ### kucoin REST SPOT Trades

# %%
kucoin_exchange = ccxt.kucoin()

# %%
kucoin_exchange.has["fetchTrades"]

# %%
data = pd.Series(kucoin_exchange.load_markets().keys())
data[data.str.startswith("BTC")]


# %%
currency_pair = "BTC/USDT"
pd.DataFrame(kucoin_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
#
# ## kucoin REST futures

# %%
kucoin_exchange.has["future"]

# %% [markdown]
# # okx REST

# %%
exchange_id = "okx"

# %% [markdown]
# ## okx REST SPOT

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### okx REST SPOT Bid Ask

# %%
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 05:00:00")
bid_ask_depth = 20
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %% [markdown]
# ### okx REST SPOT OHLCV

# %%
data_type = "ohlcv"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %%
okx_exchange = ccxt.okx()
currency_pair = "BTC/USDT:USDT"
pd.DataFrame(okx_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### okx REST SPOT trades

# %%
okx_exchange.has["fetchTrades"]

# %%
pd.DataFrame(okx_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
# ## okx REST futures

# %%
okx_exchange.has["future"]

# %%
future_params = {"options": {"defaultType": "future"}}

# %%
help(okx_exchange.fetch_order_book)

# %% [markdown]
# ### okx REST futures bid_ask

# %%
pd.DataFrame(
    okx_exchange.fetch_order_book(currency_pair, 10, future_params)
).head()

# %% [markdown]
# ### okx REST futures OHLCV

# %%
pd.DataFrame(okx_exchange.fetch_ohlcv(currency_pair, params=future_params)).head()

# %% [markdown]
# ### okx REST futures OHLCV trades

# %%
pd.DataFrame(
    okx_exchange.fetch_trades(currency_pair, params=future_params)
).head()

# %% [markdown]
# # deribit REST

# %%
exchange_id = "deribit"

# %% [markdown]
# ## deribit REST SPOT

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### deribit REST SPOT bid_ask

# %%
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 05:00:00")
bid_ask_depth = 20
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %%
deribit_exchange = ccxt.deribit()
data = pd.Series(deribit_exchange.load_markets().keys())
data[data.str.startswith("BTC")].head()


# %%
currency_pair = "BTC/USDC:USDC"
pd.DataFrame(deribit_exchange.fetch_order_book(currency_pair)).head()

# %% [markdown]
# ### deribit REST SPOT ohlcv

# %%
pd.DataFrame(deribit_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### deribit REST SPOT trades

# %%
pd.DataFrame(deribit_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
# ## deribit REST futures

# %%
deribit_exchange.has["future"]

# %% [markdown]
# ### deribit REST futures bid_ask

# %%
currency_pair = "BTC/USDC:USDC"
pd.DataFrame(
    deribit_exchange.fetch_order_book(currency_pair, params=future_params)
).head()

# %% [markdown]
# ### deribit REST futures ohlcv

# %%
pd.DataFrame(
    deribit_exchange.fetch_ohlcv(currency_pair, params=future_params)
).head()

# %% [markdown]
# ### deribit REST futures trades

# %%
pd.DataFrame(
    deribit_exchange.fetch_trades(currency_pair, params=future_params)
).head()

# %% [markdown]
# # coinbasepro REST

# %%
exchange_id = "coinbasepro"

# %% [markdown]
# ## coinbasepro REST spot

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### coinbasepro REST spot bid_ask

# %%
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 05:00:00")
bid_ask_depth = 20
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %%
coinbasepro_exchange = ccxt.coinbasepro()

# %%
help(coinbasepro_exchange.fetch_order_book)

# %%
currency_pair = "BTC/USDT"
pd.DataFrame(
    coinbasepro_exchange.fetch_order_book(currency_pair, limit=10)
).head()

# %% [markdown]
# ### coinbasepro REST spot ohlcv

# %%
pd.DataFrame(coinbasepro_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### coinbasepro REST spot trades

# %%
pd.DataFrame(coinbasepro_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
# ## coinbasepro REST futures

# %%
coinbasepro_exchange.has["future"]

# %% [markdown]
# # kraken REST

# %%
exchange_id = "kraken"

# %% [markdown]
# ## kraken REST spot

# %%
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### kraken REST spot bid_ask

# %%
currency_pair = "BTC_USDT"
currency_pair_for_download = extractor.convert_currency_pair(currency_pair)
start_timestamp = pd.Timestamp("2023-01-01 00:00:00")
end_timestamp = pd.Timestamp("2023-01-01 05:00:00")
bid_ask_depth = 10
data_type = "bid_ask"
data = extractor.download_data(
    data_type,
    exchange_id,
    currency_pair,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    depth=bid_ask_depth,
)
data.head()

# %%
kraken_exchange = ccxt.kraken()

# %%
currency_pair = "BTC/USDT"
pd.DataFrame(kraken_exchange.fetch_order_book(currency_pair)).head()

# %% [markdown]
# ### kraken REST spot ohlcv

# %%
pd.DataFrame(kraken_exchange.fetch_ohlcv(currency_pair)).head()

# %% [markdown]
# ### kraken REST spot trades

# %%
pd.DataFrame(kraken_exchange.fetch_trades(currency_pair)).head()

# %% [markdown]
# ## kraken REST futures

# %%
kraken_exchange.has["future"]

# %% [markdown]
# # cryptocom

# %% [markdown]
# ## cryptocom REST spot

# %%
exchange_id = "cryptocom"
cryptocom = ccxt.cryptocom()
market_info = pd.DataFrame.from_dict(cryptocom.load_markets(), orient="index")
contract_type = "spot"
extractor = imvcdexex.CcxtExtractor(exchange_id, contract_type)

# %% [markdown]
# ### cryptocom REST spot Bid Ask

# %%
spot_symbols = market_info[market_info["spot"] == True]
spot_symbols

# %%
bid_ask_data = cryptocom.fetch_order_book("BTC/USDT", params={"depth": 5})
bid_ask_data

# %% [markdown]
# ### cryptocom REST spot OHLCV

# %%
ohlcv1 = cryptocom.fetchOHLCV(
    "BTC/USDT",
    params={"start_ts": 1673182859000, "end_ts": 1673186459000, "count": 5},
)
ohlcv1

# %%
# Get historical data over a long period of time
# 300 is maximum number of rows that can be extracted with a single call to fetchOHLCV.
# the function provides latest 300 rows so we have to move back to get historical data.
# Method to get historical data from 1st Dec 2023 to 31st Dec 2023
start_time = 1701388800000  # 12/01/2023
end_time = 1703116800000  # 12/31/2023
data = pd.DataFrame()
while end_time != start_time:
    ohlcv = pd.DataFrame(
        cryptocom.fetchOHLCV(
            "BTC/USDT",
            "1m",
            params={
                "timeframe": "M1",
                "start_ts": start_time,
                "end_ts": end_time,
                "count": 300,
            },
        )
    )
    if end_time != ohlcv.iloc[0, 0]:
        data = pd.concat([ohlcv, data], ignore_index=True)
        end_time = ohlcv.iloc[0, 0]

# %%
data

# %% [markdown]
# ### cryptocom REST SPOT trades

# %%
data = pd.DataFrame(
    cryptocom.fetch_trades(
        "BTC/USDT",
        params={"start_ts": 1673182859000, "end_ts": 1673186459000, "count": 5},
    )
)
data.head()

# %% [markdown]
# ## cryptocom REST Futures

# %%
cryptocom.has["future"]

# %%
futures_symbols = market_info[market_info["future"] == True]
futures_symbols

# %% [markdown]
# ### cryptocom REST Futures Bid Ask

# %%
help(cryptocom.fetch_order_book)

# %%
currency_pair = "BTCUSD-240126"
pd.DataFrame(cryptocom.fetch_order_book(currency_pair, 10)).head()

# %% [markdown]
# ### cryptocom REST Futures OHLCV

# %%
pd.DataFrame(cryptocom.fetch_ohlcv(currency_pair, "1m")).head()

# %% [markdown]
# ### cryptocom REST Futures trades

# %%
pd.DataFrame(cryptocom.fetch_trades(currency_pair)).head()

# %%
