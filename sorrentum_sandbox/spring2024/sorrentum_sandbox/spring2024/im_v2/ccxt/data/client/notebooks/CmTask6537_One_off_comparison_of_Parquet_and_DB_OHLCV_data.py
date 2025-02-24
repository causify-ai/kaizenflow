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
# # Description

# %%
# TODO(Dan): consider generalizing the notebook, i.e. move the code to a lib to compare OHLCV bars.

# %% [markdown]
# Compare historical data stored in Parquet with data from database.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import datetime
import logging

import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
universe_version = "v7.4"
config_dict = {
    "universe_kwargs": {
        "vendor": "CCXT",
        "mode": "trade",
        "version": universe_version,
        "as_full_symbol": True,
    },
    "pq_client_config": {
        "data_version": "v3",
        "universe_version": universe_version,
        "dataset": "ohlcv",
        "contract_type": "futures",
        "data_snapshot": "",
    },
    "db_client_config": {
        "universe_version": "infer_from_data",
        "db_stage": "prod",
        "table_name": "ccxt_ohlcv_futures",
    },
    "read_data_kwargs": {
        "start_ts": pd.Timestamp(datetime.date(2023, 11, 1), tz="UTC"),
        "end_ts": pd.Timestamp(datetime.date(2023, 11, 30), tz="UTC"),
        "columns": None,
        "filter_data_mode": "assert",
    },
    "columns_to_compare": [
        "timestamp",
        "full_symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ],
}
config = cconfig.Config().from_dict(config_dict)
print(config)

# %% [markdown]
# # Compare Parquet and DB data

# %% [markdown]
# ## Load data

# %%
full_symbols = ivcu.get_vendor_universe(**config["universe_kwargs"])
full_symbols

# %%
pq_im_client = icdcl.get_CcxtHistoricalPqByTileClient_example1(
    **config["pq_client_config"]
)
pq_ohlcv_data = pq_im_client.read_data(
    full_symbols,
    **config["read_data_kwargs"],
)
pq_ohlcv_data = pq_ohlcv_data.reset_index()
pq_ohlcv_data = pq_ohlcv_data[config["columns_to_compare"]]
print(pq_ohlcv_data.shape)
pq_ohlcv_data.head()

# %%
db_im_client = icdcl.get_CcxtSqlRealTimeImClient_example1(
    **config["db_client_config"]
)
db_ohlcv_data = db_im_client.read_data(
    full_symbols,
    **config["read_data_kwargs"],
)
#
db_ohlcv_data = db_ohlcv_data.reset_index()
db_ohlcv_data = db_ohlcv_data[config["columns_to_compare"]]
print(db_ohlcv_data.shape)
db_ohlcv_data.head()

# %% [markdown]
# ## Total

# %%
# Check that data does not contain duplicates.
hdbg.dassert_eq(0, pq_ohlcv_data.duplicated().sum())
hdbg.dassert_eq(0, db_ohlcv_data.duplicated().sum())

# %% run_control={"marked": false}
# Difference in data length.
len_diff = len(pq_ohlcv_data) - len(db_ohlcv_data)
_LOG.info("Length PQ data=%s", len(pq_ohlcv_data))
_LOG.info("Length DB data=%s", len(db_ohlcv_data))
_LOG.info(
    "Percentage of rows that are not intersecting=%s",
    len_diff / max(len(pq_ohlcv_data), len(db_ohlcv_data)) * 100,
)

# %%
# Merge dataframes in order to align data on timestamp and full symbol.
merged_df = pd.merge(
    pq_ohlcv_data,
    db_ohlcv_data,
    on=["timestamp", "full_symbol"],
    suffixes=("_pq", "_db"),
    how="inner",
)
merged_df = merged_df.set_index(["timestamp", "full_symbol"])
#
_LOG.info("Merged data shape=%s", merged_df.shape)
merged_df.head()

# %%
# Get number of minutes in the data time interval.
n_minutes = len(merged_df.unstack())
_LOG.info("N minutes=%s", n_minutes)

# %%
# Get number of days the observations are loaded for.
unique_days = set(merged_df.unstack().index.date)
_LOG.info("N unique days=%s", len(unique_days))

# %%
# Split merged data on aligned Parquet and DB data.
pq_data = merged_df[
    ["open_pq", "high_pq", "low_pq", "close_pq", "volume_pq"]
].copy()
pq_data.columns = ["open", "high", "low", "close", "volume"]
#
db_data = merged_df[
    ["open_db", "high_db", "low_db", "close_db", "volume_db"]
].copy()
db_data.columns = ["open", "high", "low", "close", "volume"]

# %%
df_diff = hpandas.compare_dfs(
    pq_data,
    db_data,
    compare_nans=True,
).abs()
df_diff.max().max()

# %% run_control={"marked": false}
df_is_diff = (df_diff > 0.001).sum(axis=1)
total_diff_rows = df_is_diff[df_is_diff > 0]
diff_rows_perc = (len(total_diff_rows) / len(df_is_diff)) * 100
_LOG.info(
    "Percentage of rows at intersecting time interval with abs diff > 0.001=%s",
    round(diff_rows_perc, 2),
)

# %% [markdown]
# ## NaNs

# %%
# Get observations for which there is data in 1 df and no data in another.
nan_diff_df = hpandas.compare_nans_in_dataframes(pq_data, db_data)
print(len(nan_diff_df))
nan_diff_df.head()

# %%
# Get all the timestamps for which there is a difference with NaN.
nan_diff_timestamps = nan_diff_df.unstack().index
_LOG.info("N minutes with NaN diff=%s", len(nan_diff_timestamps))
_LOG.info(
    "Percentage of minutes with NaN diff=%s",
    len(nan_diff_timestamps) / n_minutes * 100,
)
nan_diff_timestamps

# %% [markdown]
# ## Per bar timestamp

# %%
# Get a bool series representing if a row has any differing values.
ts_diff_rows = (df_diff > 0.001).any(axis=1)
ts_diff_rows

# %%
# Get number of rows per date.
df_ts_diff_rows = ts_diff_rows.reset_index()
df_ts_diff_rows["date"] = df_ts_diff_rows["timestamp"].dt.date
n_rows_per_date = df_ts_diff_rows["date"].value_counts()
# Get differing rows for all the unique dates.
n_diff_rows_per_date = df_ts_diff_rows.groupby("date")[0].sum()
# Get percentage of missing rows per date.
perc_diff_rows_per_date = (n_diff_rows_per_date / n_rows_per_date).dropna() * 100
#
perc_diff_rows_per_date.plot()

# %%
rows_to_plot = perc_diff_rows_per_date[perc_diff_rows_per_date > 0].sort_values()
# Stats are displayed only for days with differing rows.
coplotti.plot_barplot(
    rows_to_plot,
    orientation="horizontal",
    annotation_mode="value",
    title="Percentage of rows with value differences per day",
    figsize=(20, len(rows_to_plot) / 2),
)
_LOG.info(
    "Percentage of days with value differences=%s",
    len(rows_to_plot) / len(unique_days) * 100,
)

# %% [markdown]
# ## Per asset

# %%
# Percentage of rows with value differences per asset.
asset_diff_row_count = (
    (df_diff > 0.001)
    .any(axis=1)
    .reset_index("full_symbol")
    .groupby("full_symbol")
    .sum()[0]
)
# Get number of rows per asset.
asset_n_rows = (
    df_diff.sum(axis=1)
    .reset_index("full_symbol")
    .groupby("full_symbol")
    .count()[0]
)
# Get percentage of missing rows per date.
perc_asset_diff_row_count = (asset_diff_row_count / asset_n_rows * 100).round(2)
#
coplotti.plot_barplot(
    perc_asset_diff_row_count.sort_values(),
    orientation="horizontal",
    annotation_mode="value",
    title="Percentage of rows with value differences per asset",
    figsize=(20, 10),
)

# %% [markdown]
# ## Per column

# %%
diff_row_count = (df_diff > 0.001).sum()
perc_diff_row_count = diff_row_count / len(df_diff) * 100
#
coplotti.plot_barplot(
    perc_diff_row_count,
    annotation_mode="value",
    title="Percentage of rows with value differences per column",
)

# %%
