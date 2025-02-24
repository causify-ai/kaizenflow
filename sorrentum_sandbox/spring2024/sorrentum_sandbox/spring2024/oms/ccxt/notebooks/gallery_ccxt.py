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

# %% [markdown]
# # Description

# %% [markdown]
# This notebook contains examples of CCXT functionality.

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2
import logging
import pprint

import ccxt

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hsecrets as hsecret

# %%
display(HTML("""
<style>
/* Jupyter cell is in normal mode when code mirror */
.edit_mode .cell.selected .CodeMirror-focused.cm-fat-cursor {
  /* background-color: #F5F6EB; */
  background-color: rgba(128, 0, 0, 0.1); 
}
/* Jupyter cell is in insert mode when code mirror */
.edit_mode .cell.selected .CodeMirror-focused:not(.cm-fat-cursor) {
  /* background-color: #F6EBF1; */
  background-color: rgba(0, 128, 0, 0.2); 
}
</style>
"""))

# %%
display(HTML("<style>.container { width:100% !important; }</style>"))

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install sagemath)"

# %%
from typing import Any, Dict, List

def subset_dict(dict_: Dict, keys: List[Any], *, keep_order: bool = True) -> Dict:
    res = {}
    if keep_order:
        for k, v in dict_.items():
            if k in keys:
                res[k] = v
    else:
        for k in keys:
            res[k] = dict_[k]
    return res


# %% [markdown]
# # CCXT
#
# ## Resources
# - https://github.com/ccxt/ccxt
# - https://docs.ccxt.com/#/README
# - https://github.com/ccxt/ccxt#readme
# - https://ccxt.readthedocs.io/en/latest/index.html
# - https://ccxt.readthedocs.io/en/latest/manual.html
#
# ## Intro
#
# - CCXT = CryptoCurrency eXchange Trading library
#
# - Connect with cryptocurrency exchanges and trade
# - Connect with payment processing services
# - Access to market data
# - Algorithmic trading
# - Strategy backtesting
# - Bot programming
#
# - Normalized API for cross-exchange analytics and arbitrage
#
# - There is an async mode using asyncio
#   ```
#   import ccxt.async_support as ccxt
#   ```
#
# - Proxy: in case Cloudflare or your country / IP is rejected
#   - Of course an intermediary adds latency
#   - Server that acts as an intermediary between the client requesting a resource and the server
#
# ## Usage
#
# // https://github.com/ccxt/ccxt#usage
#
# - Public API
#   - Unrestricted access to public information for exchanges without account or
#     API key
#   - E.g.,
#     - Market data
#     - Order books
#     - Price feeds
#     - Trade history
#
# - Private API
#   - Obtain an API key from exchange website by signing up
#     - You might need personal info and verification
#   - Manage personal account info
#   - Query account balance
#   - Query orders
#   - Trade
#   - Deposit and withdraw fiat and crypto funds
#
# - CCXT supports REST APIs for all exchanges
# - CCXT Pro supports WebSocket and FIX

# %% [markdown]
# # Exchanges

# %% [markdown]
# From https://docs.ccxt.com/#/README?id=exchanges
#
# - Each class implements the public and private API for a particular crypto
#   exchange
# - The `Exchange` class shares a set of common methods
#
# - Some exchanges offer:
#   - Margin trading (i.e., leverage)
#   - Derivatives (e.g., futures and options)
#   - Dark pools, OTC trading
#   - Merchant APIs
#
# - Testnets and mainnets envs
#     - Some exchanges offer a separated API for:
#       - Testing purposes (aka "sandboxes", "staging environments", "testnets")
#       - Trading with real assets (aka "mainnets", "production environments")
#     - Typically the sandbox has the same API as the production API but with a
#       different URL (and maybe different market)
#
# - Exchange structure
#     - Every exchange has properties that can be overridden in the constructor
#
#     - `id`: default id for identification purposes (typically a lower case string)
#     - `name`: human-readable exchange name
#     - `countries`: where the exchange is operating from
#     - `urls`: URLs for private and public APIs, main website, documentation
#     - `version`: version of the current exchange API
#     - `api`: API endpoints exposed by a crypto exchange
#     - `has`: array of exchange capabilities
#     - `timeframes`: frequency of available bars (e.g., minutes)
#     - `rateLimit`: minimum delay between two consecutive requests
#     - `markets`: dictionary of markets indexed by symbols
#     - `symbols`: list of symbols available with an exchange
#     - `currencies`: array of currencies available
#
# - Exchange metadata
#     - Each exchange has a `has` with flags about the exchange capabilities
#
# - Rate limit
#     - Exchanges track your user / IP address to throttle querying the API too
#       frequently
#     - You need to stay under the rate limit to avoid being banned
#       - Typical limits are 1 or 2 requests per second
#     - CCXT has an experimental rate-limiter that throttles in background
#       ```
#       exchange.enableRateLimit = True
#       ```
#       - The state is inside the class instance so one should have a single class

# %%
# Print all exchanges.
print(len(ccxt.exchanges), ccxt.exchanges)

# %%
# Create Binance exchange.
exchange_id = "binance"
mode = "test"
contract_type = "futures"

# Select credentials for provided exchange.
if mode == "test":
    secrets_id = exchange_id + "_sandbox"
else:
    secrets_id = exchange_id
exchange_params = hsecret.get_secret(secrets_id)

# Enable rate limit.
exchange_params["rateLimit"] = True

# Log into futures/spot market.
if contract_type == "futures":
    exchange_params["options"] = {"defaultType": "future"}

# Create a CCXT Exchange class object.
ccxt_exchange = getattr(ccxt, exchange_id)
print(hprint.to_str("ccxt_exchange"))
exchange = ccxt_exchange(exchange_params)
print(hprint.to_str("exchange"))
if mode == "test":
    exchange.set_sandbox_mode(True)
    _LOG.warning("Running in sandbox mode")
hdbg.dassert(
    exchange.checkRequiredCredentials(),
    msg="Required credentials not passed",
)

# %% [markdown]
# ## Exchange properties

# %%
print("exchange=", exchange, type(exchange))

# %%
# # Print some properties of the exchange.
# var_names = ["exchange.id", 
#              "exchange.name",
#              "exchange.countries",
#              #"exchange.urls",
#              "exchange.version",
#              "exchange.timeframes",
#              "exchange.timeout",
#              "exchange.rateLimit",
#              "exchange.symbols",
#              "exchange.currencies"]
# for var_name in var_names:
#     print(hprint.to_str(var_name, mode="pprint_color"))

# %%
# Name in user-land to identify the exchange.
hprint.pprint_color(exchange.id)

# %%
# Human readable name.
hprint.pprint_color(exchange.name)

# %%
# Which countries the exchange is operating from.
hprint.pprint_color(exchange.countries)

# %%
# Version identifier for exchange API.
hprint.pprint_color(exchange.version)

# %%
# timeframes for fetchOHLCV().
# TODO(gp): It seems that it has 1s resolution.
hprint.pprint_color(exchange.timeframes)

# %%
# Binance doesn't have this method.
#hprint.pprint_color(exchange.requiredCredentialsCredentials)

# %%
# Exchange decimal precision.
hprint.pprint_color(exchange.precisionMode)

# %%
hprint.pprint_color(exchange.urls)

# %%
hprint.pprint_color(exchange.api)

# %%
exchange.loadMarkets()
print(hprint.list_to_str(exchange.markets.keys(), tag="market_list"))

# %%
print(hprint.list_to_str(exchange.currencies, tag="currencies"))

# %%
hprint.pprint_color(exchange.commonCurrencies)

# %% [markdown]
# ## Exchange metadata

# %%
# Flags for exchange capabilities (true, false, emulated).
# CORS = cross-origin resource sharing.
hprint.pprint_color(exchange.has)

# %% [markdown]
# ## Rate limit

# %% [markdown]
# # Markets
#
# - Valuables
#     - Valuables are exchanged at each market
#       - E.g.,
#         - instruments
#         - symbols
#         - assets
#         - trading pairs
#         - currencies
#         - tokens
#         - contract
#
# - Exchange and Market
#     - Every Exchange offers multiple Markets
#     - A Market is usually a pair of currencies (e.g., crypto, fiat)

# %% [markdown]
# ## Currency structure
#
# - Each currency has an associated dictionary
#     - `id`: currency id within the exchange
#     - `code`: `cctx` representation of the currency
#     - `name`: human readable currency name
#     - `fee`: withdrawal fee
#     - `active`: indicates whether trading and funding this currency is possible
#     - `info`: dictionary of non-common market properties
#     - `precision`
#     - `limits`: min and max for withdrawals

# %% [markdown]
# ## Market structure
#
# - `id` string representing the instrument within the exchange (e.g., `btcusd`)
# - `baseId` (e.g., `btc`), `quoteId` (e.g., `usd`) are exchange-specific ids
# - `symbol` string code representing the trading pair
#   - E.g., typically `BaseCurrency/QuoteCurrency` (e.g., `BTC/USD`)
#   - This is standard in `ccxt`
# - `base` (e.g., `BTC`) / `quote` (`USD`) standardized currency code
# - `active`: indicates whether trading this market is possible
#   - The cache of the markets should be refreshed periodically
# - `maker`: maker fees paid when you provide liquidity to the exchange
#   - E.g., you make an order and someone else fills it
#   - A negative fee means a rebate
# - `taker`: taker fees paid when you take liquidity from the exchange (i.e., you
#   fill someone else's order)
# - `tierBased`: whether the fee depends on your trading tier (e.g., amount of
#   trading done over a period of time)
# - `info`: non-common market properties
# - `precision`: precision used for price, amount, and cost
#   - E.g., decimal places, significant digits, tick size

# %%
# A market is an associative array.

#market_id = exchange.markets_by_id["1000FLOKIUSDT"]
market_id = exchange.markets_by_id["ETHUSDT"]
print(type(market_id))
hprint.pprint_color(market_id)

# %%
# Trade instrument within the exchange. This is the internal representation of each exchange.
market = exchange.markets["ETH/USDT"]
print(market["id"])

# %%
# Trade instrument in CCXT user-land (unified). Typically referrend as "base/quote".
print(market["symbol"])

# %%
# Market ids (unified)
print(market["base"], market["quote"])

# %%
# Symbol ids (not unified).
print(market["baseId"], market["quoteId"])

# %%
print(hprint.to_str('market["active"] market["maker"] market["taker"] market["percentage"]'))

# %%
# Market-specific properties.
hprint.pprint_color(market["info"])

# %% [markdown]
# ## Network structure

# %% [markdown]
# ## Precision and limits

# %%
# limits = min, max for prices / amounts (aka volumes) / costs (= price * amount)
# precision = precision for prices / amounts / costs accepted in order values when placing orders
# They are not related.

hprint.pprint_color(market["limits"], tag="limits", sep="\n")
hprint.pprint_color(market["precision"], tag="precision", sep="\n")

# %%
# Min / max amount (i.e., volume) for an order.
print(market["limits"]["amount"])

# %%
# How many decimal digits.

# %%
# Each exchange has their own way of rounding and truncating.

# %%
exchange.precisionMode

# %%
ccxt.TICK_SIZE

# %%
ccxt.SIGNIFICANT_DIGITS

# %%
ccxt.DECIMAL_PLACES

# %%
# From https://docs.ccxt.com/#/README?id=formatting-to-precision
#ccxt.base.decimal_to_precision.amount_to_precision(symbol, amount)

# %% [markdown]
# ## Loading markets

# %%
markets = exchange.load_markets()

# %% [markdown]
# ## Symbols and Market Ids
#
# ### Symbols and market ids
#
# * Currency code
# - = a code of 3 to 5 uppercase letters
# - E.g., `BTC`, `ETH`, `USD`, `XRP`
#
# * Symbol
# - = a pair of currencies separated by a slash
#   - E.g., `BTC/USD`
# - The first currency is called the "base currency"
# - The second currency is called the "quote currency"
#   - BASE / QUOTE
#
# * Market Ids
# - Market ids are unique per exchange and are used in REST request-response
#   - E.g., the same BTC/USD pair can be called in different ways on different
#     markets (e.g., `BTCUSD`, `btc/usd`)
# - `CCTX` abstracts market ids into standardized symbols
#
# * Market symbol vs market ids
# - "Market symbols" are the abstract representation
# - "Market ids" are specific of each market
#
# ### Methods for markets and currencies
#
# // notebook
#
# ### Naming consistency
#
# * Products
# - Some exchanges call markets as "pairs" or "products"
# - `CCXT` considers each exchange as having one or more "trading markets"
#   - Each market has an `id` and a `symbol`
#   - Most symbols are typically a currency pair
#
# * Exchange -> Markets -> Symbols -> Currencies
# - The logic is:
#   - Exchange (name of the exchange, e.g., Binance)
#   - Markets (a "product" that is traded, e.g., the pair `BTC/USD`)
#   - Symbols (a pair of traded currencies separated by slash)
#   - Currencies (the currency code, e.g., `BTC` and `USD`)
#
# - The same currency:
#   - can have different names on different exchanges
#   - has changed name over time (e.g., `XBT` -> `BTC`, `USD` = `USDT`)
#
# * Expiring / perpetual futures
# - Aka "swaps"
# - Futures market symbol have:
#   - Underlying currency
#   - Quoting currency
#   - Settlement currency
#   - Identifier for a settlement date (typically as YYMMDD)
#
# - E.g., `BTC/USDT:BTC-211225`
#   - BTC/USDT futures contract settled in BTC (inverse) on 2021-12-25
# - E.g., `BTC/USDT:USDT-211225`
#   - BTC/USDT futures contract settled in USDT (linear, vanilla)
#
# * Perpetual futures
# - Aka "perpetual swaps"
# - E.g., `BTC/USDT:BTC`

# %%
exchange.load_markets();

# %%
# Get the market structure.
market = exchange.markets["ETH/USDT"]
hprint.pprint_color(market)

# %%
# Print a subset of interesting values for Market structure.
var_names = [
    "id",
    "symbol",
    "base",
    "quote",
    "baseId",
    "quoteId",
    "active",
    "maker",
    "taker",
    "tierBased",
    "info",
    "precision",
    "limits",
]
# for var_name in var_names:
#     print(f"--> {var_name}=", hprint.pprint_pformat(market[var_name]))
hprint.pprint_color(
    subset_dict(market, var_names))

# %%
# Print all the symbols in one exchange.
symbols = exchange.symbols
print(symbols)

# %%
# Print a dictionary of all currencies.
currencies = exchange.currencies
hprint.pprint_color(currencies)

# %%
#market_id = exchange.markets_by_id["1000FLOKIUSDT"]
market_id = exchange.markets_by_id["ETHUSDT"]
print(type(market_id))
hprint.pprint_color(market_id)

# %%
market_id["symbol"]

# %% [markdown]
# ## Market cache force reload

# %% [markdown]
# # Implicit API methods

# %% [markdown]
# ## API methods / endpoints
#
# - API methods / endpoints
#     - Each exchange offers a set of API methods (aka "endpoints") that are HTTP URLs
#       for querying various types of information
#     - All endpoints return JSON responses
#
# - E.g., an endpoint for:
#   - getting a list of markets from an exchange
#   - retrieving an order book
#   - retrieving trade history
#   - cancelling orders
#   
# - Endpoints are defined in `api` property of an exchange
#
# ## Implicit API methods
#
# - In practice each API method is mapped on callable Python function
# - Each function can be called with a dictionary of parameters and return an
#   unparsed JSON from the exchange API
# - The method is available in both camelCase and under_score notation
#
# ## Public / private / unified
#
# - Each `Exchange` implements:
#   - a public / private API for all endpoints
#   - a unified API supporting a subset of common methods
#
# - One should:
#   - use unified methods
#   - use the private method as fallback
#
# ## Public / Private API
#
# - Public API doesn't require authentication
#     - Aka "market data", "basic api", "market api", "mapi"
#     - E.g.,
#         - Allow to access market data
#         - Price feeds
#         - Order books
#         - Trade history
#         - Bars
#
# - Private API requires authentication
#     - Aka "trading api", "tapi"
#     - E.g.,
#         - Manage personal account info
#         - Query account balances
#         - Trade
#         - Create deposit
#         - Request withdrawal
#         - Query orders
#
# - Some exchanges also expose a "merchant API" to accept crypto and fiat as payments
#     - Aka "merchant", "wallet", "ecapi" (for e-commerce)
#
# * Synch vs async calls
# - `CCXT` supports asyncio
# - The same methods are available but decorated with `asyncio` keyword
#
# * Returned objects
# - Public and private APIs return raw JSON objects (representing the response from
#   the exchange)
# - Unified APIs return a JSON object in a common format across all exchanges

# %%
# Print a list of all the methods in an exchange.
print(dir(ccxt.binance()))

# %% [markdown]
# ## Synchronous vs asynchronous
#
# - CCXT supports async concurrency mode with async/await
# - Use `asyncio` and `aiohttp`
# - The methods are the same but they are decorated with `async`
#
# ```
# import asyncio
# import ccx.async_support as ccxt
#
# ...
# ```

# %% [markdown]
# ## API parameters
#
# - Public / private API endpoints differ from exchange to exchange
#     - Most methods accept an array of key-value params
# - Return a raw JSON object
#
# - Unified API return JSON in a common format uniform across all exchanges

# %% [markdown]
# # Unified API
#
# - fetch...
#   - Markets
#   - Currencies
#   - OrderBook
#   - Status
#   - Trades
#   - Ticker
#   - Balance
# - create...
#   - Order
#   - LimitBuyOrder / LimitSellOrder
#   - MarketBuyOrder / MarketSellOrder
#   - CancelOrder
# - fetch orders
#   - Open
#   - Canceled
#   - Closed
# - fetch
#     - my trades
#     - open interest
#     - transactions
#     - deposit
#     - withdrawals
#
# - A `param` argument is a dictionary of exchange-specific params you want override
#
# ## Pagination
# - Most exchange APIs return a certain number of the most recent objects
# - You can't get all the objects in one call
#   - You need to paginate, i.e., fetch portions of data one by one
#   - Pagination can be performed based on id, time, or page number

# %% [markdown]
# # Public API
#
# https://docs.ccxt.com/#/README?id=public-api

# %%
exchange.fetchMarkets()

# %%
exchange.fetchCurrencies()

# %%
# Not supported for Binance
# exchange.fetchStatus()

# %%
symbol = "BTC/USDT"
data = exchange.fetchOrderBook(symbol)
#data = exchange.fetchL2OrderBook(symbol)
print("keys=", data.keys())

key_names = ["symbol", "timestamp", "datetime", "nonce", "bids"]
hprint.pprint_color(
    subset_dict(data, key_names))

# %%
data = exchange.fetchTrades(symbol)
hprint.pprint_color(data[:2])

# %%
symbol = "BTC/USDT"
data = exchange.fetchTicker(symbol)
hprint.pprint_color(data)

# %% [markdown]
# ## FetchBalance

# %%
symbol = "BTC/USDT"
data = exchange.fetchBalance()
hprint.pprint_color(data)

# %% [markdown]
# - L1: market price only
# - L2: order volume aggregated by price
# - L3: each order is kept separated

# %% [markdown]
# ## Market price

# %%
#symbol = exchange.symbols[0]
symbol = "BTC/USDT"
print(symbol)
orderbook = exchange.fetch_order_book(symbol)
bid = orderbook["bids"][0][0] if len(orderbook["bids"]) > 0 else None
ask = orderbook["asks"][0][0] if len(orderbook["asks"]) > 0 else None
spread = (ask - bid) if (bid and ask) else None
print(exchange.id, {"bid": bid, "ask": ask, "spread": spread})

# %% [markdown]
# ## FetchTicker()

# %%
symbol = "BTC/USDT"
data = exchange.fetchTicker(symbol)
hprint.pprint_color(data)

# %% [markdown]
# ## OHLCV bars

# %%
symbol = "BTC/USDT"
data = exchange.fetchOHLCV(symbol)
# O, H, L, C, V
hprint.pprint_color(data[:5])

# %% [markdown]
# - The info from the current candle may be incomplete until the candle is closed
#
# - Exchanges provide
#     - (fast) primary data (e.g., order books, trades, fills)
#         - WebSockets might be faster than REST API
#     - (slow) secondary data calculated from primary data (e.g., OHLCV bars)
#         - It might be faster to compute data locally

# %% [markdown]
# ## Public trades

# %%
symbol = "BTC/USDT"
data = exchange.fetch_trades(symbol)
hprint.pprint_color(data[:2])

# %% [markdown]
# ## Borrow rates

# %% [markdown]
# - When short trading or trading with leverage on a spot market, currency must be
#   borrowed

# %%
# Binance doesn't support this.
#exchange.fetchBorrowRatesPerSymbol(symbol)

# %% [markdown]
# ## Leverage tiers

# %%
symbol = "BTC/USDT"
data =  exchange.fetchMarketLeverageTiers(symbol)
hprint.pprint_color(data[0])
hprint.pprint_color(data[-1])

# %% [markdown]
# ## Funding rate

# %%
data = exchange.fetchFundingRate(symbol)
hprint.pprint_color(data)

# %%
data = exchange.fetchFundingRateHistory(symbol)
hprint.pprint_color(data[:3])

# %% [markdown]
# ## Open interest

# %%
# Binance doesn't support this.
# data = exchange.fetchOpenInterest(symbol)
# hprint.pprint_color(data[:3])

# %% [markdown]
# # Private API
#
# https://docs.ccxt.com/#/README?id=private-api
#
# - `fetchBalance`
# - `createOrder`, `cancelOrder`
# - `fetchOrder`, `fetchOpenOrder`, `fetchCanceledOrder`, `fetchClosedOrder`
# - `fetchMyTrades`
# - `fetchPositions`
# - `fetchTransactions`
# - `fetchLedger`
#
# ## Authentication
# - Handled automatically if API key provided
# - Generate nonce (integer and increasing, e.g., 32-bit Unix Timestamp in seconds)
# - Append public API key and nonce to the endpoint params, serialize, sign
# - Append signature to HTTP headers
#
# - `apiKey`
#     - non-secret
#     - sent over HTTPS
# - `secret`
#     - private key
#     - used to sign requests locally
#     - used together with the nonce
#     - signature sent with public key to authenticate
# - `uid`
#     - some exchanges generate a user id
# - `password`
#     - some exchanges use also password for trading

# %%
import oms.hsecrets.secret_identifier as ohsseide

exchange_id = "binance"
#account_type = "sandbox"
account_type = "trading"
stage = "preprod"
#secret_id = "4"
secret_id = 4

secret_identifier = ohsseide.SecretIdentifier(
    exchange_id, stage, account_type, secret_id
    )
print(secret_identifier)

# Prepare exchange params.
exchange_params = hsecret.get_secret(str(secret_identifier))
#print(exchange_params)
exchange_params["rateLimit"] = False
exchange_params["options"] = {"defaultType": "future"}

# Build the exchange object.
ccxt_exchange = getattr(ccxt, exchange_id)
exchange = ccxt_exchange(exchange_params)

exchange.options["adjustForTimeDifference"] = True

# %%
# Check what type of authentication an exchange needs.
hprint.pprint_color(exchange.requiredCredentials)

# %%
# Check that the credentials work.
# It throws an `AuthenticationError` if login fails.
exchange.check_required_credentials()

# %% [markdown]
# ## Overriding the nonce

# %% [markdown]
# ## Accounts
#
# * `fetchAccounts()`
# - Return accounts and sub-accounts in a dict.

# %%
# Binance doesn't have.
# exchange.fetchAccounts()

# %% [markdown]
# ## Account balance
#
# * `fetchBalance()`
# - Query for balance and get the amount of funds available

# %%
balance = exchange.fetchBalance()

# %%
hprint.pprint_color(balance)

# %%
balance.keys()

# %%
#print(hprint.to_str('balance["timestamp"] balance["datetime"]'))
key_names = ["timestamp", "datetime"]
hprint.pprint_color(
    subset_dict(balance, key_names))

# %%
# Coins available for trading.
hprint.pprint_color(balance["free"])

# %%
# Coins on hold / locked.
hprint.pprint_color(balance["used"])

# %%
# Total coins (=free + used).
hprint.pprint_color(balance["total"])

# %%
# Indexed by coins.
hprint.pprint_color(balance["BTC"])

# %%
# `info` contains the response (unparsed) from the exchange.
hprint.pprint_color(balance["info"])

# %%
balance["info"].keys()

# %%
# Print info about one asset.
print(len(balance["info"]["assets"]))
hprint.pprint_color(balance["info"]["assets"][0])

# %%
# Print info about one position.
print(len(balance["info"]["positions"]))
hprint.pprint_color(balance["info"]["positions"][0])

# %%
balance["info"]["feeTier"]

# %%
# for key in ["canTrade", "canDeposit", "canWithdraw"]:
#     print(hprint.to_str(f'balance["info"]["{key}"]'))
hprint.pprint_color(
    subset_dict(
        balance["info"],
        ["canTrade", "canDeposit", "canWithdraw"]))

# %%
balance["info"]["updateTime"]

# %%
# https://www.binance.com/en/support/faq/leverage-and-margin-of-usd%E2%93%A2-m-futures-360033162192
# - USD-M futures: margin and settlement in USDT (Tether) and BUSD (Binance Stable coin)
# - COIN-M futures: margin and settlement in alt-coins

# %%
# for key in ['totalInitialMargin',
#             'totalMaintMargin',
#             'totalWalletBalance', 
#             'totalUnrealizedProfit',
#             'totalMarginBalance',
#             'totalPositionInitialMargin',
#             'totalOpenOrderInitialMargin',
#             'totalCrossWalletBalance',
#             'totalCrossUnPnl', 
#             'availableBalance', 'maxWithdrawAmount']:
#     print(hprint.to_str(f'balance["info"]["{key}"]'))

key_names = ['totalInitialMargin',
             'totalMaintMargin',
             'totalWalletBalance', 
             'totalUnrealizedProfit',
             'totalMarginBalance',
             'totalPositionInitialMargin',
             'totalOpenOrderInitialMargin',
             'totalCrossWalletBalance',
             'totalCrossUnPnl', 
             'availableBalance',
             'maxWithdrawAmount']
hprint.pprint_color(
    subset_dict(balance["info"], key_names))

# %% [markdown]
# ## Orders
#
# https://docs.ccxt.com/#/README?id=orders
#
# - You can query orders by an id or symbol
# - Some exchanges might not have all methods


# %%
# for k, v in exchange.has.items():
#     if "order" in k or "Order" in k:
#         print(k, v)

hprint.pprint_color(subset_dict(
    exchange.has, [
    "fetchOrder", "fetchOrders",
    "fetchOpenOrder", "fetchOpenOrders",
    "fetchClosedOrder", "fetchClosedOrders"]))

# %% [markdown]
# ### Understanding the Orders API design
#
# - `fetch{,Open,Canceled}Orders()`
# - `fetchMyTrades()`: history of settled trades
# - `createOrder()`
# - `cancelOrder()`
#
# - All methods returning a list of trades / orders, accept a `since` and `limit` arg
#     - Without `since` the method returns the default set of results from the exchange (e.g., last 24 hours or last N trades
#     - Some exchanges provide pagination through the `params` arg

# %%
orders = exchange.fetchOrders("BTC/USDT", limit=2)

# %%
hprint.pprint_color(orders[0])

# %% [markdown]
# - closed orders are not trades (aka fills)
# - an order doesn't have `fee`
# - trades have `fee` and `cost`

# %%
closed_orders = exchange.fetchClosedOrders("BTC/USDT", limit=2)

# %%
hprint.pprint_color(closed_orders[0])

# %% [markdown]
# ### Order structure
#
# https://docs.ccxt.com/#/README?id=order-structure

# %%
order = orders[0]

# %%
order.keys()

# %%
var_names = ["id",
             # You can tag the order.
             "clientOrderId",
             "timestamp",
             "datetime",
             "lastTradeTimestamp"]
hprint.pprint_color(
    subset_dict(order, var_names, keep_order=False))

# %%
var_names = [
    # 
    'status',
    'symbol',
    # E.g., market, limit
    'type',
    'timeInForce',
    'side',
    # Price in quote currency.
    'price',
    # Average filling price.
    'average',
    # How much is ordered vs filled vs remaining.
    'amount',
    'filled',
    'remaining',
    # = filled * price
    'cost',
    'fee',
    'fees',
    # List of trades.
    'trades',
    #
    'stopPrice',
    'postOnly',
    'reduceOnly',
]
hprint.pprint_color(subset_dict(order, var_names, keep_order=False))

# %%
hprint.pprint_color(order["info"])

# %% [markdown]
# ### Placing orders
#
# https://docs.ccxt.com/#/README?id=placing-orders
#
# - Limit orders
#     - Amount in base currency (how much you want to buy / sell)
#     - Price in quote currency (for which price you want to buy / sell)
# - Trigger orders
#     - Wait for a condition on a market (trigger) and then a market order is placed
# - Stop loss orders / Take profit orders
#     - Like a special trigger order
#     - When price passes a certain value, a market / limit order is triggered

# %% [markdown]
# - `createOrder` is used to place orders:
#   - symbol
#   - side
#       - buy `BTC/USD`, receive quote currency (BTC) for base currency (USD)
#       - sell `BTC/USD`: receive USD for BTC
#   - type
#       - market
#       - limit
#   - amount
#       - Typically expressed in terms of the base currency
#       - For some exchanges it is dependent on the side of the order
#   - price
#       - in units of the quotes currency
#   - params
#       - params specific to the exchange API
#   - a successful order returns an order structure
#  
#  
# - Limit orders
#     - `create_limit_order`
#     - `create_buy_limit_order`
#     - `create_sell_limit_order`
#     - They are placed on the exchange for a certain price
#     - They are fullfilled (closed) when:
#         - there are no orders at a better price
#         - a market / limit order for a price that matches or exceeds the price of the limit order
#
# - Market orders
#     - Executed immediately using orders from the top of the other side of the book
#       (i.e., orders are chosen with best price available)
#     - You are not guaranteed that the order is executed for the price you observe
#       prior to placing the order because
#         - network latency
#         - high loads on the exchange
#         - price volatility
#         - order walking the book


# %% [markdown]
# ### Editing orders
#
# https://docs.ccxt.com/#/README?id=editing-orders
#
# An order can also be edited
#
# TODO(gp): Unclear what happens. I believe it's cancelled and placed again

# %% [markdown]
# ### Canceling orders
#
# https://docs.ccxt.com/#/README?id=canceling-orders
#
# - `cancelOrder`: cancel a single order
# - `candelOrders`: cancel multiple orders
# - `cancelAllOrders`: cancel all the open orders
#
# It is possible that an order gets executed while the cancel command is being executed
#     - Then a `NetworkError` or `OrderNotFound` are thrown

# %% [markdown]
# ## My trades
#
# https://docs.ccxt.com/#/README?id=my-trades
#
# ### How orders are related to trades
# - A trade is also called a "fill"
# - Each trade is a result of order execution
# - One order may result in several trades
#     - i.e., an order can be filled with one or more trades
#     - one-to-many relationship
#
# - Each trade is a result of an order execution (matching opposing orders)
# - An execution of one order can result in several trades (i.e., filled with
#   multiple trades)
#
# ### Personal trades
# - Typically exchanges use pagination to return all the trades

# %% [markdown]
# ### Trade structure
#
# https://docs.ccxt.com/#/README?id=trade-structure

# %%
order_id = None
trades = exchange.fetch_my_trades(symbol, limit=2)

# %%
trade = trades[0]

# %%
hprint.pprint_color(trade)

# %%
trade.keys()

# %%
var_names = ["id",
             "timestamp",
             "datetime"]
hprint.pprint_color(
    subset_dict(trade, var_names, keep_order=False))

# %%
var_names = ["symbol",
             "order",
             "type",
             "side",
             "takerOrMaker",
             # Price in quote currency.
             "price",
             # Amount of base currency.
             "amount",
             # Total cost, i.e., price * amount.
             "cost",
             # Fees.
             "fee",
             "fees"]
hprint.pprint_color(
    subset_dict(trade, var_names, keep_order=False))

# %%
# Original decoded JSON from the exchange.
var_names = ["info"]
hprint.pprint_color(
    subset_dict(trade, var_names, keep_order=False))

# %% [markdown]
# ### Trades by Order id

# %%
# Not supported by Binance.
# order_id = "170643031299"
# trades = exchange.fetch_order_trades(order_id, symbol, limit=2)

# %% [markdown]
# ## Ledger
#
# - = history of changes / actions done by the user affecting the balance
#
# - funding (deposits / withdrawals)
# - profits / losses from trades
# - trading fees
# - rebates, etc.

# %%
# Not supported by Binance.
# exchange.fetchLedger()

# %% [markdown]
# ### Ledger entry structure
#
# https://docs.ccxt.com/#/README?id=ledger-entry-structure

# %% [markdown]
# ## Deposit
#
# https://docs.ccxt.com/#/README?id=deposit

# %%
exchange.fetchDeposits()

# %% [markdown]
# ### Withdraw
#
# ### Transactions
#
# * Trading fees
# - = amount paid to the exchange
# - Typically it is a percentage of volume traded
#
# * Funding fees
# - Fees for depositing and withdrawing
# - Crypto transaction fees
#

# %%
balance = exchange.fetchBalance()

balance

# %%
balance.keys()

# %% [markdown]
# # CCXT Pro
#
# // https://ccxt.readthedocs.io/en/latest/ccxt.pro.manual.html
#
# - Standard CCXT uses request-response based APIs (e.g., REST)
# - CCXT Pro uses connection-based streaming API (e.g., WebSocket)
#
# - `fetch*` methods are replaced with `watch*` methods
#
# - CCXT Pro manages the connection-based interface transparently to the user
#   - On the first call to a `watch*` method a connection is established
#   - If the connection already exists, it is reused
#   - The library watches the status of the connection and keeps it alive
#
# * Sub interface
# - Allows to subscribe to a stream of data and lister for it
#   - E.g., streaming public market data (e.g., order book, bars)
#
# * Pub interface
# - Allows to send data requests towards the server
#   - E.g., placing / cancelling orders
#
# * Incremental data structures
# - In many cases, the application listening needs to
#   - keep a local snapshot of the data in memory
#   - merge the updates received from the exchange server (aka "deltas")
#
# - CCXT Pro automatically handles this

# %%
