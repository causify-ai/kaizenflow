# ---
# jupyter:
#   jupytext:
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
# This is spin off from `CMTask2703_Perform_manual_reconciliation_of_OB_data` notebook
# We would like to reconcile data collected ~200ms via CCXT with historical data from CryptoChassis

# %% [markdown]
# - CCXT data = CCXT real-time DB bid-ask data collection for futures
# - CC data = CryptoChassis historical Parquet bid-ask futures data

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.im_lib_tasks as imvimlita

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Load the data
#
# For CCXT data we have multiple data points within a single, we resample to second by taking the latest entry within
# a second

# %% [markdown]
# ## Specify universe

# %%
universe = [
    "binance::SOL_USDT",
    "binance::DOGE_USDT",
    "binance::BNB_USDT",
    "binance::ETH_USDT",
    "binance::BTC_USDT",
]

# %% [markdown]
# ## Load data

# %%
start_ts = pd.Timestamp("2022-10-11 17:00:00+00:00")
end_ts = pd.Timestamp("2022-10-11 18:00:00+00:00")
start_ts_unix = hdateti.convert_timestamp_to_unix_epoch(start_ts)
end_ts_unix = hdateti.convert_timestamp_to_unix_epoch(end_ts)

# %% [markdown]
# ### CC data

# %%
filters = [("year", "=", 2022), ("month", "=", 10)]
file_name = "s3://cryptokaizen-data.preprod/reorg/daily_staged.airflow.pq/bid_ask-futures/crypto_chassis/binance/"
df = hparque.from_parquet(file_name, filters=filters, aws_profile="ck")

# %%
df.head()

# %%
df.index.max()

# %%
df_chassis = df.loc[(df.index >= start_ts) & (df.index <= end_ts)]
df_chassis = df_chassis.drop_duplicates()
df_chassis["full_symbol"] = "binance::" + df_chassis["currency_pair"]
df_chassis = df_chassis[df_chassis["full_symbol"].isin(universe)]
df_chassis = df_chassis[
    ["bid_size", "bid_price", "ask_size", "ask_price", "full_symbol"]
]
df_chassis = df_chassis.reset_index().set_index(["timestamp", "full_symbol"])
# We drop the first row because CC labels right side of the intrval during resampling, meaning for CCXT we will have
# one less row
df_chassis = df_chassis.drop(start_ts)

# %%
df_chassis.tail()

# %%
df_chassis.shape

# %%
df_chassis[df_chassis.index.isin(["binance::BTC_USDT"], level=1)].head()

# %% [markdown]
# ### CCXT data

# %%
env_file = imvimlita.get_db_env_path("dev")
connection_params = hsql.get_connection_info_from_env_file(env_file)
db_connection = hsql.get_connection(*connection_params)

# %%
query = f"SELECT * FROM public.ccxt_bid_ask_futures_test \
WHERE level = 1 AND timestamp >= {start_ts_unix} AND timestamp <= {end_ts_unix}"
query

# %%
df_ccxt = hsql.execute_query_to_df(db_connection, query)
df_ccxt["timestamp"] = df_ccxt["timestamp"].map(
    hdateti.convert_unix_epoch_to_timestamp
)
df_ccxt = df_ccxt.reset_index(drop=True).set_index(["timestamp"])

# %%
# Use label right to match crypto chassis data
df_ccxt["full_symbol"] = "binance::" + df_ccxt["currency_pair"]
dfs_ccxt = []
for fs in universe:
    df_fs = df_ccxt[df_ccxt["full_symbol"] == fs]
    df_fs = (
        df_fs[["bid_size", "bid_price", "ask_size", "ask_price"]]
        .resample("S", label="right")
        .mean()
    )
    df_fs["full_symbol"] = fs
    df_fs = df_fs.reset_index().set_index(["timestamp", "full_symbol"])
    dfs_ccxt.append(df_fs)
df_ccxt_sec_last = pd.concat(dfs_ccxt)

# %% [markdown]
# # Analysis

# %%
data_ccxt = df_ccxt_sec_last
data_cc = df_chassis

# %%
bid_ask_cols = ["bid_size", "bid_price", "ask_size", "ask_price", "full_symbol"]

# %% [markdown]
# ## Merge CC and DB data into one DataFrame

# %%
data = data_ccxt.merge(
    data_cc,
    how="outer",
    left_index=True,
    right_index=True,
    suffixes=("_ccxt", "_cc"),
)
_LOG.info("Start date = %s", data.reset_index()["timestamp"].min())
_LOG.info("End date = %s", data.reset_index()["timestamp"].max())
_LOG.info(
    "Avg observations per coin = %s",
    len(data) / len(data.reset_index()["full_symbol"].unique()),
)
# Move the same metrics from two vendors together.
data = data.reindex(sorted(data.columns), axis=1)
# NaNs observation.
_LOG.info(
    "Number of observations with NaNs in CryptoChassis = %s",
    len(data[data["bid_price_cc"].isna()]),
)
_LOG.info(
    "Number of observations with NaNs in CCXT = %s",
    len(data[data["bid_price_ccxt"].isna()]),
)
# Remove NaNs.
data = hpandas.dropna(data, report_stats=True)
#
display(data.tail())

# %% [markdown]
# ## Calculate differences

# %%
# Full symbol will not be relevant in calculation loops below.
bid_ask_cols.remove("full_symbol")
# Each bid ask value will have a notional and a relative difference between two sources.
for col in bid_ask_cols:
    # Notional difference: CC value - DB value.
    data[f"{col}_diff"] = data[f"{col}_cc"] - data[f"{col}_ccxt"]
    # Relative value: (CC value - DB value)/DB value.
    data[f"{col}_relative_diff_pct"] = (
        100 * (data[f"{col}_cc"] - data[f"{col}_ccxt"]) / data[f"{col}_ccxt"]
    )
#
data.head()

# %%
# Calculate the mean value of differences for each coin.
diff_stats = []
grouper = data.groupby(["full_symbol"])
for col in bid_ask_cols:
    diff_stats.append(grouper[f"{col}_diff"].mean())
    diff_stats.append(grouper[f"{col}_relative_diff_pct"].mean())
#
diff_stats = pd.concat(diff_stats, axis=1)

# %% [markdown]
# ## Show stats for differences (in %)

# %% [markdown]
# ### Prices

# %%
diff_stats[["bid_price_relative_diff_pct", "ask_price_relative_diff_pct"]]

# %% [markdown]
# As one can see, the difference between bid and ask prices in DB and CC are less than 1%.

# %% [markdown]
# ### Sizes

# %%
diff_stats[["bid_size_relative_diff_pct", "ask_size_relative_diff_pct"]]

# %% [markdown]
# ## Correlations

# %% [markdown]
# ### Bid price

# %%
bid_price_corr_matrix = (
    data[["bid_price_cc", "bid_price_ccxt"]].groupby(level=1).corr()
)
bid_price_corr_matrix

# %% [markdown]
# Correlation stats confirms the stats above: bid prices in DB and CC are highly correlated.

# %% [markdown]
# ### Ask price

# %%
ask_price_corr_matrix = (
    data[["ask_price_cc", "ask_price_ccxt"]].groupby(level=1).corr()
)
ask_price_corr_matrix

# %% [markdown]
# Correlation stats confirms the stats above: ask prices in DB and CC are highly correlated.

# %% [markdown]
# ### Bid size

# %%
bid_size_corr_matrix = (
    data[["bid_size_cc", "bid_size_ccxt"]].groupby(level=1).corr()
)
bid_size_corr_matrix

# %% [markdown]
# Correlation stats confirms the stats above: bid sizes in DB and CC are highly correlated.

# %% [markdown]
# ### Ask size

# %%
ask_size_corr_matrix = (
    data[["ask_size_cc", "ask_size_ccxt"]].groupby(level=1).corr()
)
ask_size_corr_matrix

# %% [markdown]
# Correlation stats confirms the stats above: ask sizes in DB and CC are highly correlated.
