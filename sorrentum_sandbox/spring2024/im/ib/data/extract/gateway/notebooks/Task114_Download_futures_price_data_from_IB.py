# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python [conda env:.conda-dev] *
#     language: python
#     name: conda-env-.conda-dev-py
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
import im.ib.data.extract.gateway.utils as imidegaut

# %% [markdown]
# # Connect

# %%
ib = imidegaut.ib_connect(client_id=100, is_notebook=True)

# %% [markdown]
# # Historical data

# %%
import logging

# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)

# %%

# %%
# start_ts = pd.to_datetime(pd.Timestamp("2018-02-01 06:00:00").tz_localize(tz="America/New_York"))
# import datetime

# #datetime.datetime.combine(start_ts, datetime.time())

# %%
# dt = start_ts.to_pydatetime()
# print(dt)

# #datetime.datetime.combine(dt, datetime.time()).tz_localize(tz="America/New_York")
# dt.replace(hour=0, minute=0, second=0)

# %%
start_ts = pd.Timestamp("2019-05-28 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2019-05-29 15:00").tz_localize(tz="America/New_York")
barSizeSetting = "1 hour"

bars = imidegaut.get_data(
    ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)

# %%
start_ts = pd.Timestamp("2019-05-28 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2019-05-29 15:00").tz_localize(tz="America/New_York")
barSizeSetting = "1 hour"

bars = imidegaut.get_data(
    ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)

# %%
start_ts = pd.Timestamp("2019-05-27").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2019-05-28").tz_localize(tz="America/New_York")
barSizeSetting = "1 hour"

bars = imidegaut.get_data(
    ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)

# %%
start_ts2 = start_ts - pd.DateOffset(days=1)
end_ts2 = end_ts + pd.DateOffset(days=1)
barSizeSetting = "1 hour"

bars2 = imidegaut.get_data(
    ib, contract, start_ts2, end_ts2, barSizeSetting, whatToShow, useRTH
)

# %%
set(bars.index).issubset(bars2.index)

# %%
start_ts = pd.Timestamp("2019-04-01 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2019-05-01 15:00").tz_localize(tz="America/New_York")

df = imidegaut.get_historical_data2(
    ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)

# %%
import pandas as pd

contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
whatToShow = "TRADES"
durationStr = "2 D"
barSizeSetting = "1 min"
useRTH = False
# useRTH = True

# start_ts = pd.to_datetime(pd.Timestamp("2018-02-01"))
# Saturday June 1, 2019
end_ts = pd.to_datetime(
    pd.Timestamp("2019-05-30 00:00:00") + pd.DateOffset(days=1)
)
# end_ts = pd.to_datetime(pd.Timestamp("2019-05-30 18:00:00"))
# print(start_ts, end_ts)
print("end_ts=", end_ts)

bars = imidegaut.req_historical_data(
    ib, contract, end_ts, durationStr, barSizeSetting, whatToShow, useRTH
)

print(
    "durationStr=%s barSizeSetting=%s useRTH=%s"
    % (durationStr, barSizeSetting, useRTH)
)
print("bars=[%s, %s]" % (bars.index[0], bars.index[-1]))
print("diff=", bars.index[-1] - bars.index[0])

bars["close"].plot()

# %%
pd.date_range(start="2019-04-01 00:00:00", end="2019-05-01 00:00:00", freq="2D")

# %%

# %%
(bars.index[-1] - bars.index[0])

# %%
import pandas as pd

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
elif True:
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

# endDateTime = pd.Timestamp("2020-12-11 18:00:00")
endDateTime = pd.Timestamp("2020-12-13 18:00:00")
# endDateTime = ""

# Get the datetime of earliest available historical data for the contract.
start_ts = ib.reqHeadTimeStamp(contract, whatToShow=whatToShow, useRTH=True)
print("start_ts=", start_ts)
bars = ib.reqHistoricalData(
    contract,
    endDateTime=endDateTime,
    durationStr=durationStr,
    barSizeSetting=barSizeSetting,
    whatToShow=whatToShow,
    useRTH=True,
    formatDate=1,
)
print("len(bars)=", len(bars))
print(ib_insync.util.df(bars))

# %%
ib_insync.IB.RaiseRequestErrors = True

# %%
bars

# %%
hdbg.shutup_chatty_modules(verbose=True)

# %%
import pandas as pd

contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
whatToShow = "TRADES"
durationStr = "2 D"
barSizeSetting = "1 min"
useRTH = False

start_ts = pd.Timestamp("2018-01-28 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2018-02-28 15:00").tz_localize(tz="America/New_York")

tasks = imidegaut.get_historical_data_workload(
    contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)
print(len(tasks))

imidegaut.get_historical_data2(ib, tasks)

# %% [markdown]
# ##

# %%
# %load_ext autoreload
# %autoreload 2

import ib_insync

print(ib_insync.__all__)

# %%
import logging

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im.ib.data.extract.gateway.utils as imidegaut

hdbg.init_logger(verbosity=logging.DEBUG)
# hdbg.init_logger(verbosity=logging.INFO)

import pandas as pd

hdbg.shutup_chatty_modules(verbose=False)

# %%
ib = imidegaut.ib_connect(8, is_notebook=True)

# %%
# #start_ts = pd.Timestamp("2018-01-28 15:00").tz_localize(tz="America/New_York")
# start_ts = pd.Timestamp("2018-01-28 18:00").tz_localize(tz="America/New_York")
# end_ts = pd.Timestamp("2018-02-28 15:00").tz_localize(tz="America/New_York")

# dates = []
# if (start_ts.hour, start_ts.minute) > (18, 0):
#     dates = [start_ts]
#     # Align start_ts to 18:00.
#     start_ts = start_ts.replace(hour=18, minute=18)
# elif (start_ts.hour, start_ts.minute) < (18, 0):
#     dates = [start_ts]
#     # Align start_ts to 18:00 of the day before.
#     start_ts = start_ts.replace(hour=18, minute=18)
#     start_ts -= pd.DateOffset(days=1)

# hdbg.dassert_eq((start_ts.hour, start_ts.minute), (18, 0))
# dates += pd.date_range(start=start_ts, end=end_ts, freq='2D').tolist()
# print(dates)

# %%
# import datetime
# start_ts = pd.Timestamp(datetime.datetime(2017,6,25,0,31,53,993000))
# print(start_ts)

# start_ts.round('1s')

# %%
contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
whatToShow = "TRADES"
durationStr = "2 D"
barSizeSetting = "1 hour"
useRTH = False

start_ts = pd.Timestamp("2018-01-28 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2018-02-01 15:00").tz_localize(tz="America/New_York")

tasks = imidegaut.get_historical_data_workload(
    ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH
)

df = imidegaut.get_historical_data2(tasks)

# %%

# %%
df

# %%
df2 = imidegaut.get_historical_data_with_IB_loop(
    ib,
    contract,
    start_ts,
    end_ts,
    durationStr,
    barSizeSetting,
    whatToShow,
    useRTH,
)

# %%
hprint.print(df.index)

# %%
contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
whatToShow = "TRADES"
durationStr = "1 D"
barSizeSetting = "1 hour"
# 2021-02-18 is a Thursday and it's full day.
start_ts = pd.Timestamp("2021-02-17 00:00:00")
end_ts = pd.Timestamp("2021-02-18 23:59:59")
useRTH = False
df, return_ts_seq = imidegaut.get_historical_data_with_IB_loop(
    ib,
    contract,
    start_ts,
    end_ts,
    durationStr,
    barSizeSetting,
    whatToShow,
    useRTH,
    return_ts_seq=True,
)
print(return_ts_seq)

# %%
print("\n".join(map(str, return_ts_seq)))
