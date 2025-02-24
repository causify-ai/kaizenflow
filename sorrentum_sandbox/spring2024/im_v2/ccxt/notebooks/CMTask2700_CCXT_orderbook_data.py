# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# This notebook contains an example of accessing order book data from CCXT.

# %%
import logging
import pprint

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.ccxt.data.extract.extractor as imvcdexex
import im_v2.common.universe.universe as imvcounun
import im_v2.crypto_chassis.data.extract.extractor as imvccdexex

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# ### Initialize extractors

# %%
# Initialize CCXT extractor.
ccxt_extractor = imvcdexex.CcxtExtractor("binance", "futures")
exchange = ccxt_extractor._exchange

# %%
# Initialize CryptoChassis extractor and download a bid/ask data example.
cryptochassis_extractor = imvccdexex.CryptoChassisExtractor("futures")
exchange_id = "binance"
currency_pair = "BTC_USDT"
start_timestamp = pd.Timestamp("01-09-2022")
end_timestamp = pd.Timestamp("02-09-2022")
cryptochassis_data_example = cryptochassis_extractor._download_bid_ask(
    exchange_id, currency_pair, start_timestamp, end_timestamp
)

# %%
cryptochassis_data_example

# %%
bid_ask_columns = cryptochassis_data_example.columns.to_list()

# %% [markdown]
# ## Example of CCXT orderbook data

# %%
symbol = "BTC/USDT"
raw_orderbook_data = exchange.fetch_order_book(symbol)

# %%
# Get data keys from CCXT.
print(raw_orderbook_data.keys())

# %%
# Example of raw orderbook data.
pprint.pprint(raw_orderbook_data, sort_dicts=False)

# %%
print(len(raw_orderbook_data["bids"]))

# %%
print(len(raw_orderbook_data["asks"]))

# %% [markdown]
# - The `fetch_order_book` method returns the 500 top of the book results at the moment of request.
# - Note that the `timestamp` and `datetime` are set to a `ms` accuracy.

# %%
# Transform the raw data into a dataframe.
orderbook_df = pd.DataFrame.from_dict(raw_orderbook_data)
orderbook_df

# %% [markdown]
# Each row in the orderbook contains a `list` with 2 values corresponding to `bid_price`, `bid_size`, `ask_price` and `ask_size`, as in CryptoChassis.

# %%
orderbook_df[["bid_price", "bid_size"]] = pd.DataFrame(
    orderbook_df.bids.to_list(), index=orderbook_df.index
)
orderbook_df[["ask_price", "ask_size"]] = pd.DataFrame(
    orderbook_df.asks.to_list(), index=orderbook_df.index
)

# %%
orderbook_df

# %%
orderbook_df = orderbook_df[bid_ask_columns]
orderbook_df

# %%
orderbook_df[:10]


# %% [markdown]
# - The top of the book in CCXT is sorted by price
# - All columns present in CryptoChassis are present in CCXT output

# %% [markdown]
# ## `_download_bid_ask` method proposal

# %%
def _download_bid_ask(extractor, currency_pair: str, *, depth=10):
    """
    Download bid-ask data from CCXT.

    :param depth: depth of the order book to download.
    """
    # Convert symbol to CCXT format, e.g. "BTC_USDT" -> "BTC/USDT".
    currency_pair = extractor.convert_currency_pair(currency_pair)
    # Download order book data.
    order_book = extractor._exchange.fetch_order_book(currency_pair)
    order_book = pd.DataFrame.from_dict(order_book)
    order_book = order_book.loc[:depth]
    # Separate price and size into columns.
    order_book[["bid_price", "bid_size"]] = pd.DataFrame(
        order_book.bids.to_list(), index=order_book.index
    )
    order_book[["ask_price", "ask_size"]] = pd.DataFrame(
        order_book.asks.to_list(), index=order_book.index
    )
    # Select bid/ask columns.
    bid_ask_columns = [
        "timestamp",
        "bid_price",
        "bid_size",
        "ask_price",
        "ask_size",
    ]
    bid_ask = order_book[bid_ask_columns]
    return bid_ask


# %%
data = _download_bid_ask(ccxt_extractor, "BTC_USDT")
data

# %% [markdown]
# ## Check universe

# %% [markdown]
# Verify that all symbols for which we download bid/ask from CryptoChassis are accessible via CCXT.

# %%
binance_universe = imvcounun.get_vendor_universe("crypto_chassis", "download")[
    "binance"
]
binance_universe

# %%
for symbol in binance_universe:
    try:
        _download_bid_ask(ccxt_extractor, symbol)
        print(f"Successfully downloaded {symbol}.")
    except:
        print(f"Symbol {symbol} failed to download.")
