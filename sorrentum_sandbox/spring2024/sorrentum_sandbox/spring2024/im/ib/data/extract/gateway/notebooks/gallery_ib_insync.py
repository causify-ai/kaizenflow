# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import ib_insync

print(ib_insync.__all__)

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hstring as hstring
import im.ib.data.extract.gateway.utils as imidegaut

# %% [markdown]
# # Connect

# %%
ib = imidegaut.ib_connect(client_id=32, is_notebook=True)

# %% [markdown]
# # Basic

# %%
# print(hprint.obj_to_str(ib, attr_mode="dir", callable_mode="all"))

# %%
ib.positions()

# %%
[
    v
    for v in ib.accountValues()
    if v.tag == "NetLiquidationByCurrency" and v.currency == "BASE"
]

# %% [markdown]
# ## Equity

# %%
# INTC
contract = ib_insync.Contract(conId=270639)
eq_contract = imidegaut.to_contract_details(ib, contract)

# %%
contract = ib_insync.Stock("AMD", "SMART", "USD")
eq_contract = imidegaut.to_contract_details(ib, contract)

# %%
contract = ib_insync.Stock("INTC", "SMART", "USD", primaryExchange="NASDAQ")
eq_contract = imidegaut.to_contract_details(ib, contract)

# %% [markdown]
# ## Forex

# %%
contract = ib_insync.Forex("EURUSD")
forex_contract = imidegaut.to_contract_details(ib, contract)

# %%
print(hstring.diff_strings(eq_contract, forex_contract))

# %% [markdown]
# ## CFD (contract for difference)

# %%
contract = ib_insync.CFD("IBUS30")
cfd_contract = imidegaut.to_contract_details(ib, contract)

# %%
print(hstring.diff_strings(eq_contract, cfd_contract))

# %% [markdown]
# ## Futures

# %%
contract = ib_insync.Future("ES", "202109", "GLOBEX")
fut_contract = imidegaut.to_contract_details(ib, contract)

# %%
print(hstring.diff_strings(eq_contract, fut_contract, "eq", "fut"))

# %% [markdown]
# ## Continuous Futures

# %%
# contract = ib_insync.ContFuture('ES', '202109', 'GLOBEX')
# fut_contract = imidegaut.to_contract_details(ib, contract)

# %% [markdown]
# ## Option

# %%
contract = ib_insync.Option("SPY", "202107", 240, "C", "SMART")
opt_contract = imidegaut.to_contract_details(ib, contract)

# %% [markdown]
# ## Bond

# %%
contract = Bond(secIdType="ISIN", secId="US03076KAA60")
bond_contract = imidegaut.to_contract_details(ib, contract)

# %% [markdown]
# # Contract details

# %% [markdown]
# ## Equities

# %%
# Look for Stocks matching AMD.
asset = ib_insync.Stock("AMD")
cds = ib.reqContractDetails(asset)
print("num contracts=", len(cds))
print(cds[0])

# %%
contracts = [cd.contract for cd in cds]
print(contracts[0])

ib_insync.util.df(contracts)

# %%
# Show that there is a single AMD in US.
asset = ib_insync.Stock("AMD", "SMART", "USD")
print("asset=", asset)
cds = ib.reqContractDetails(asset)
print("num contracts=", len(cds))
hdbg.dassert_eq(len(cds), 1)
print(cds[0])

# %%
ib.qualifyContracts(asset)

# %%
# Request stocks that match a pattern.
matches = ib.reqMatchingSymbols("intc")
contracts = [m.contract for m in matches]
ib_insync.util.df(contracts)

# %% [markdown]
# ## Futures

# %%
# Look for ES.

asset = ib_insync.Future("ES", includeExpired=True)
imidegaut.get_contract_details(ib, asset)


# %%
cds = ib.reqContractDetails(asset)

contracts = [cd.contract for cd in cds]

ib_insync.util.df(contracts)

# %% [markdown]
# ## Cont futures

# %%
asset = ib_insync.ContFuture("ES", "Globex", "USD")
imidegaut.get_contract_details(ib, asset)

# %%
imidegaut.get_end_timestamp(ib, contract, "TRADES", useRTH=True)

# %% [markdown]
# # Option chain

# %%
# Options on SPX next 3

# %%
spx = ib_insync.Index("SPX", "CBOE")
print("type=%s %s" % (type(spx), spx))

ib.qualifyContracts(spx)

# %%
# Use delayed data.
ib.reqMarketDataType(4)
tickers = ib.reqTickers(spx)
assert len(tickers) == 1
ticker = tickers[0]

print(hprint.type_obj_to_str(ticker))

# %%
spx_value = ticker.marketPrice()
spx_value

# %%
# TODO: finish

# %% [markdown]
# # Historical data

# %%
# 1 = Live
# 2 = Frozen
# 3 = Delayed
# 4 = Delayed frozen
ib.reqMarketDataType(4)

if False:
    contract = ib_insync.Stock("TSLA", "SMART", "USD")
    whatToShow = "TRADES"
elif False:
    contract = ib_insync.Future("ES", "202109", "GLOBEX")
    whatToShow = "TRADES"
elif False:
    contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
    whatToShow = "TRADES"
else:
    contract = ib_insync.Forex("EURUSD")
    whatToShow = "MIDPOINT"

if False:
    durationStr = "1 Y"
    barSizeSetting = "1 day"
    # barSizeSetting='1 hour'
else:
    durationStr = "1 D"
    barSizeSetting = "1 hour"

print("contract=", contract)
print("whatToShow=", whatToShow)
print("durationStr=", durationStr)
print("barSizeSetting=", barSizeSetting)

# Get the datetime of earliest available historical data for the contract.
ts = ib.reqHeadTimeStamp(contract, whatToShow=whatToShow, useRTH=True)
print("ts=", ts)
bars = ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr=durationStr,
    barSizeSetting=barSizeSetting,
    whatToShow=whatToShow,
    useRTH=True,
    formatDate=1,
)
print("len(bars)=", len(bars))
print(ib_insync.util.df(bars))

# %%
# icontract = ib_insync.Stock('TSLA', 'SMART', 'USD')
contract = ib_insync.Forex("EURUSD")

# Get the datetime of earliest available historical data for the contract.
ib.reqHeadTimeStamp(contract, whatToShow="TRADES", useRTH=True)

# %%
print(contract)
ib.reqMarketDataType(4)
bars = ib.reqHistoricalData(
    contract,
    endDateTime="20200101 01:01:01",
    durationStr="60 D",
    barSizeSetting="1 hour",
    whatToShow="TRADES",
    useRTH=True,
    formatDate=1,
)

# %%
print(bars[0])
df = util.df(bars)

display(df.head())
display(df.tail())

# %% [markdown]
# ## Historical data with RT updates

# %%
ib.reqMarketDataType(1)
contract = ib_insync.Forex("EURUSD")

bars = ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr="900 S",
    barSizeSetting="10 secs",
    whatToShow="MIDPOINT",
    useRTH=True,
    formatDate=1,
    keepUpToDate=True,
)

print(bars[-1])

import matplotlib.pyplot as plt

# %%
from IPython.display import clear_output, display


def onBarUpdate(bars, hasNewBar):
    plt.close()
    plot = ib_insync.util.barplot(bars)
    clear_output(wait=True)
    display(plot)


bars.updateEvent += onBarUpdate

ib.sleep(10)
ib.cancelHistoricalData(bars)


# %% [markdown]
# ## Realtime bars

# %%
def onBarUpdate(bars, hasNewBar):
    print(bars[-1])


# %%
bars = ib.reqRealTimeBars(contract, 5, "MIDPOINT", False)
bars.updateEvent += onBarUpdate

# %%
ib.sleep(10)
ib.cancelRealTimeBars(bars)

# %% [markdown]
# # Tick data

# %% [markdown]
# ## Streaming tick data

# %%
contracts = ("EURUSD", "USDJPY", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD")
contracts = [ib_insync.Forex(p) for p in contracts]
ib.qualifyContracts(*contracts)

# %%
# reqMktData: subscribe to tick data or request a snapshot.
# https://interactivebrokers.github.io/tws-api/md_request.html

for contract in contracts:
    # https://ib-insync.readthedocs.io/api.html#ib_insync.ib.IB.reqMktData
    genericTickList = ""
    # Subscribe a stream of real time.
    snapshot = False
    # Request NBBO snapshot.
    regulatory_snapshot = False
    ib.reqMktData(contract, genericTickList, snapshot, regulatory_snapshot)

# %%
eurusd = contracts[1]
ticker = ib.ticker(eurusd)
print(ticker)
print(ticker.midpoint())

# %%
# ticker.marketPrice()
ticker.midpoint()

import pandas as pd

# %%
from IPython.display import clear_output, display

df = pd.DataFrame(
    index=[c.pair() for c in contracts],
    columns=["bidSize", "bid", "ask", "askSize", "high", "low", "close"],
)


def onPendingTickers(tickers):
    for t in tickers:
        df.loc[t.contract.pair()] = (
            t.bidSize,
            t.bid,
            t.ask,
            t.askSize,
            t.high,
            t.low,
            t.close,
        )
        clear_output(wait=True)
    display(df)


ib.pendingTickersEvent += onPendingTickers
ib.sleep(10)
ib.pendingTickersEvent -= onPendingTickers
print("DONE")

# %%
# Stop the update.
for contract in contracts:
    ib.cancelMktData(contract)

# %% [markdown]
# ## Tick by tick data

# %%
# re
# https://interactivebrokers.github.io/tws-api/tick_data.html

# %%
ticker = ib.reqTickByTickData(eurusd, "BidAsk")
ib.sleep(2)
print(ticker)

# %%
ticker = ib.reqTickByTickData(eurusd, "BidAsk")
ib.sleep(2)
print(ticker)

# %%
ib.cancelTickByTickData(ticker.contract, "BidAsk")

# %% [markdown]
# ## Historical tick data

# %%
# reqHistoricalTicks(contract, startDateTime, endDateTime,
#    numberOfTicks, whatToShow, useRth, ignoreSize=False, miscOptions=[]
# Request historical ticks. The time resolution of the ticks is one second.
# This method is blocking.
# https://interactivebrokers.github.io/tws-api/historical_time_and_sales.html

# %%
import datetime

start = ""
end = datetime.datetime.now()
print(start, end)
number_of_ticks = 1000
what_to_show = "BID_ASK"
useRTH = False
ticks = ib.reqHistoricalTicks(
    eurusd, start, end, number_of_ticks, what_to_show, useRTH
)

print(len(ticks))
df = ib_insync.util.df(ticks)
df.drop(columns="tickAttribBidAsk", inplace=True)
# df.index = [t.time for t in ticks]

df.head(5)

# %%
print(str(ticks)[:1000])
print(ticks[0].time, ticks[-1].time)

# %% [markdown]
# # Market depth (order book)

# %% [markdown]
# ## Get exchange info

# %%
l = ib.reqMktDepthExchanges()
print("num exchanges with market depth=", len(l))
print("\n".join(map(str, l[:5])))

# %%
df = ib_insync.util.df(l)
display(df.head(5))
print("secType=", df["secType"].unique())
df.sort_values("secType")
print(len(df))

df_fut = df[df["secType"] == "FUT"].sort_values("exchange")
print(len(df_fut))
display(df_fut)

# %% [markdown]
# ## Get the book

# %%
contract = ib_insync.Forex("EURUSD")
ib.qualifyContracts(contract)
ticker = ib.reqMktDepth(contract)

# %%
ticker

import pandas as pd

# %%
from IPython.display import clear_output, display

df = pd.DataFrame(
    index=range(5), columns="bidSize bidPrice askPrice askSize".split()
)


def onTickerUpdate(ticker):
    bids = ticker.domBids
    for i in range(5):
        df.iloc[i, 0] = bids[i].size if i < len(bids) else 0
        df.iloc[i, 1] = bids[i].price if i < len(bids) else 0
    asks = ticker.domAsks
    for i in range(5):
        df.iloc[i, 2] = asks[i].price if i < len(asks) else 0
        df.iloc[i, 3] = asks[i].size if i < len(asks) else 0
    clear_output(wait=True)
    display(df)


ticker.updateEvent += onTickerUpdate

ib_insync.IB.sleep(15)

# %%
ib.cancelMktDepth(contract)

# %%
assert 0

# %% [markdown]
# # Ordering

# %% [markdown]
# ## Account info

# %%
# List of positions for a given account.
print("positions=\n\t", "\n\t".join(map(str, ib.positions())))

## List of all orders in current session.
print("orders=", ib.orders())

## List of trades in current session.
print("trades=", ib.trades())

# %% [markdown]
# ## Order

# %%
if True:
    contract = ib_insync.Forex("EURUSD")
    ib.qualifyContracts(contract)
    print("contract=", contract)
    #
    total_quantity = 2000
    # total_quantity = 3900
    limit_price = 1.1
else:
    contract = ib_insync.Future("ES", "202109", "GLOBEX")
    ib.qualifyContracts(contract)
    print("contract=", contract)
    #
    total_quantity = 2000
    limit_price = 1.1

# %%

# %%
# %%time
total_quantity = 3900
# limit_price = 1.1
limit_price = 100
order = ib_insync.LimitOrder("BUY", total_quantity, limit_price)
print("order=", order)


# %%
def print_trade(trade):
    # print("trade=", trade)
    print("trade.contract=", trade.contract)
    print("trade.order=", trade.order)
    print("trade.orderStatus=", trade.orderStatus)
    print("log=\n\t%s" % "\n\t".join(map(str, trade.log)))


# %%
trade = ib.placeOrder(contract, order)

# %%
print_trade(trade)

# %%
# The trade is in the trades.
ib.trades()

# %%
ib.orders()

# %% [markdown]
# ## Order can't be filled.

# %%
total_quantity = 2000
limit_price = 1.1
order = ib_insync.LimitOrder("SELL", total_quantity, limit_price)
print("order=", order)

# %%
# Create a buy order with an irrealistic limit price (too low).
print("contract=", contract)
total_quantity = 2000
price = 0.05
order = ib_insync.LimitOrder("BUY", total_quantity, price)
# placeOrder is not blocking.
trade = ib.placeOrder(contract, order)

print_trade(trade)

# %%
# print(ib.openTrades())
print(trade.orderStatus.status)

# %%
print(trade.orderStatus.status)
ib.cancelOrder(order)
print(trade.orderStatus.status)

# %%
trade.log

# %%
# %%time
order = ib_insync.MarketOrder("BUY", 100)

trade = ib.placeOrder(contract, order)
while not trade.isDone():
    print("status=", trade.orderStatus.status)
    ib.waitOnUpdate()

# %%
ib.positions()

# %%
tot_commission = sum(fill.commissionReport.commission for fill in ib.fills())
print(tot_commission)

# %%
# See commission and margin impact without sending order.
order = ib_insync.MarketOrder("SELL", 20000)
order_state = ib.whatIfOrder(contract, order)
print(type(order_state))
print(order_state)

# str(order_state)

# %%
order_state.dict()

# %% [markdown]
# # News articles

# %%
newsProviders = ib.reqNewsProviders()
print("newsProviders=", newsProviders)
codes = "+".join(np.code for np in newsProviders)

#
contract = ib_insync.Stock("AMD", "SMART", "USD")
# contract = ib_insync.Future('ES')
ib.qualifyContracts(contract)

# reqHistoricalNews(conId, providerCodes, startDateTime, endDateTime, totalResults, historicalNewsOptions=None)
startDateTime = ""
endDateTime = ""
totalResults = 10
headlines = ib.reqHistoricalNews(
    contract.conId, codes, startDateTime, endDateTime, totalResults
)

print("\nlen(headlines)=", len(headlines))
latest = headlines[0]
print("\nheadline=", latest)

# Retrieve the article.
article = ib.reqNewsArticle(latest.providerCode, latest.articleId)
print("\narticle=", article)

# %% [markdown]
# # Scanner

# %%
# TODO

# %% [markdown]
# # Code recipes

# %% [markdown]
# ## Fetching consecutive data

# %%
# 1 = Live
# 2 = Frozen
# 3 = Delayed
# 4 = Delayed frozen
ib.reqMarketDataType(4)

if False:
    durationStr = "1 Y"
    barSizeSetting = "1 day"
    # barSizeSetting='1 hour'
else:
    durationStr = "1 D"
    barSizeSetting = "1 hour"

if False:
    contract = ib_insync.Stock("TSLA", "SMART", "USD")
    whatToShow = "TRADES"
elif True:
    contract = ib_insync.Future("ES", "202109", "GLOBEX")
    whatToShow = "TRADES"
else:
    contract = ib_insync.Forex("EURUSD")
    whatToShow = "MIDPOINT"

print("contract=", contract)
print("whatToShow=", whatToShow)
print("durationStr=", durationStr)
print("barSizeSetting=", barSizeSetting)

# Get the datetime of earliest available historical data for the contract.
ts = ib.reqHeadTimeStamp(contract, whatToShow=whatToShow, useRTH=True)
print("ts=", ts)
bars = ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr=durationStr,
    barSizeSetting=barSizeSetting,
    whatToShow=whatToShow,
    useRTH=True,
    formatDate=1,
)
print("len(bars)=", len(bars))

# %%
# contract = Stock('TSLA', 'SMART', 'USD')
contract = ib_insync.Forex("EURUSD")
whatToShow = "MIDPOINT"
ts = ib.reqHeadTimeStamp(contract, whatToShow=whatToShow, useRTH=True)
print(ts)
# assert 0

num_iter = 0
max_iter = 5
dt = ""
barsList = []
while True:
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=dt,
        durationStr="10 D",
        barSizeSetting="1 min",
        whatToShow="MIDPOINT",
        useRTH=False,
        formatDate=1,
    )
    if not bars:
        break
    barsList.append(bars)
    dt = bars[0].date
    print(dt, len(bars))
    num_iter += 1
    if num_iter > max_iter:
        break

# save to CSV file
allBars = [b for bars in reversed(barsList) for b in bars]
df = util.df(allBars)
# df.to_csv(contract.symbol + '.csv')
