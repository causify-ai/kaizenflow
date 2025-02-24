# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python [conda env:.conda-develop] *
#     language: python
#     name: conda-env-.conda-develop-py
# ---

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import datetime
import logging

import matplotlib.pyplot as plt
import pandas as pd

import core.explore as coexplor
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im.ib.data.extract.gateway.utils as imidegaut
import im.kibot as vakibot

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %%
def get_min_max_from_index(df):
    min_dt = min(df.index)
    max_dt = max(df.index)
    if True:
        min_dt = str(pd.Timestamp(min_dt).date())
        max_dt = str(pd.Timestamp(max_dt).date())
    print("min=", min_dt)
    print("max=", max_dt)
    return min_dt, max_dt


def print_df(df, n=3):
    print("shape=", df.shape)
    display(df.head(n))
    display(df.tail(n))


# %% [markdown]
# # Kibot

# %%
df_kibot = vakibot.KibotS3DataLoader().read_data(
    "Kibot",
    "ES",
    vakibot.AssetClass.Futures,
    vakibot.Frequency.Minutely,
    vakibot.ContractType.Continuous,
)
df_kibot.head()
df_kibot_orig = df_kibot.copy()

# %%
df_kibot = df_kibot_orig.copy()
df_kibot.rename({"vol": "volume"}, axis=1, inplace=True)
# df_kibot.index = pd.to_datetime(df_kibot.index, utc=True).tz_convert(tz='America/New_York')
df_kibot.index = pd.to_datetime(df_kibot.index).tz_localize(tz="America/New_York")

print_df(df_kibot, n=2)

# %%
fig, (ax1, ax2, ax3) = plt.subplots(
    nrows=3, ncols=1, sharex=True, figsize=(20, 10)
)

df_tmp = df_kibot.resample("1T").mean()

a = pd.Timestamp("2019-05-27 00:00:00")
# a = pd.Timestamp("2019-05-29 00:00:00")
# a = pd.Timestamp("2019-06-02 00:00:00")
print(a, a.day_name())

# b = a + pd.DateOffset(14)
# b = a + pd.DateOffset(7)
b = a + pd.DateOffset(3)
# b = a + pd.DateOffset(1)
print(b, b.day_name())

df_tmp = df_tmp[a:b][["close", "volume"]]
print(
    "samples=%d [%s, %s]" % (df_tmp.shape[0], df_tmp.index[0], df_tmp.index[-1])
)

dates = sorted(list(set(df_tmp.index.date)))  # .unique()
for date in dates:
    print(date, pd.Timestamp(date).day_name())

df_tmp = df_tmp.resample("1T").mean()
df_tmp["close"].plot(ax=ax1)
df_tmp["volume"].plot(ax=ax2)
print(
    "samples=%d [%s, %s]" % (df_tmp.shape[0], df_tmp.index[0], df_tmp.index[-1])
)

#
# df_tmp2 = df_tmp.resample("1T").mean()
# print("samples=%d [%s, %s]" % (df_tmp2.shape[0], df_tmp2.index[0], df_tmp2.index[-1]))

# support = ~pd.isnull(df_tmp["close"])
support = ~pd.isnull(df_tmp["volume"])
print(support[~support].head())
print("no support=", (~support[~support]).sum())
print("with support=", support[support].sum())
pd.DataFrame(1.0 * support).plot(ax=ax3)

for date in dates:
    for h, m in ((9, 0), (16, 30)):
        date_tmp = datetime.datetime.combine(date, datetime.time(h, m))
        date_tmp = pd.Timestamp(date_tmp).tz_localize(tz="America/New_York")
        plt.axvline(date_tmp, color="red", linestyle="--", linewidth=3)

# %% [markdown]
# # IB

# %%
import ib_insync

ib = imidegaut.ib_connect(1)

# %%
contract = ib_insync.ContFuture("ES", "GLOBEX", "USD")
whatToShow = "TRADES"
barSizeSetting = "1 min"
# barSizeSetting = '1 hour'
useRTH = False

start_ts = pd.Timestamp("2019-05-28 15:00").tz_localize(tz="America/New_York")
end_ts = pd.Timestamp("2019-05-29 15:00").tz_localize(tz="America/New_York")

# file_name = "ES.csv"
# if os.path.exists(file_name):
# df_ib = imidegaut.get_data(ib, contract, start_ts, end_ts, barSizeSetting, whatToShow, useRTH)
# df_ib.to_csv("ES.csv")

durationStr = "1 D"
df_ib = imidegaut.req_historical_data(
    ib, contract, end_ts, durationStr, barSizeSetting, whatToShow, useRTH
)

# %%
display(df_ib.head(2))
print(df_ib.index[0], df_ib.index[-1])

display(df_kibot.head(2))
print(df_kibot.index[0], df_kibot.index[-1])

# %% [markdown]
# # Compare

# %%
target_col = "close"
# target_col = "open"
# target_col = "high"
# target_col = "volume"

# %%
if True:
    print_df(df_ib, n=1)
    print_df(df_kibot, n=1)

# %%
# min_dt = "2013-10-06"
# max_dt = "2013-10-09"
min_dt = start_ts
max_dt = end_ts

#
df_ib_tmp = df_ib.loc[min_dt:max_dt]
df_ib_tmp.columns = ["%s_ib" % c for c in df_ib_tmp.columns]
df_ib_tmp.head()
#
df_kibot_tmp = df_kibot.loc[min_dt:max_dt]
df_kibot_tmp.columns = ["%s_kibot" % c for c in df_kibot_tmp.columns]
df_kibot_tmp.head()

# df = pd.concat([df_ib_tmp, df_kibot_tmp], axis=1, join="outer")
df = pd.concat([df_ib_tmp, df_kibot_tmp], axis=1, join="inner")
display(df.head(1))

# Shift.
df["%s_ib" % target_col] = df["%s_ib" % target_col].shift(0)

# Filter columns.
display(df[cols].head(10))
cols = ["%s_%s" % (target_col, src) for src in "ib kibot".split()]
df[cols].plot()

# %%
df.iloc[:100][cols].plot()

# %%
ds1 = "ib"
ds2 = "kibot"
diff = df[target_col + "_" + ds1] - df[target_col + "_" + ds2]

diff.plot()

hpandas.dropna(pd.DataFrame(diff), drop_infs=True).hist(bins=101)

# %%
intercept = False
coexplor.ols_regress(
    df,
    target_col + "_" + ds1,
    target_col + "_" + ds2,
    intercept,
    jointplot_=True,
    max_nrows=None,
)
