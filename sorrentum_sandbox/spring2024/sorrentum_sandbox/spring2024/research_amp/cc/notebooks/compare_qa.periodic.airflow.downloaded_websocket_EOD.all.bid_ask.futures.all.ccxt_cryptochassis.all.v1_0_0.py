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
# # Description

# %% [markdown]
# This notebook conducts the cross-vendor QA between following datasets:
#
# - periodic.airflow.websocket.postgres.bid_ask.futures.v7_3.ccxt.binance.
# - periodic.airflow.downloaded_EOD.postgres.bid_ask.futures.v3.cryptochassis.binance
#
# The QA consists of the following data checks:
#
# - Start and End date for both datasets
# - Number of observations pet coin for both datasets
# - Number of NaNs per dataset
# - Notional difference (CC value - CCXT value) for `bid_price`, `ask_price`, `bid_size`, `ask_size` columns
# - Relative difference (CC value - CCXT value)/CCXT value for `bid_price`, `ask_price`, `bid_size`, `ask_size` columns
# - Pearson correlation for `bid_price`, `ask_price`, `bid_size`, `ask_size` between both datasets

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import pandas as pd

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.transform.transform_utils as imvcdttrut
import im_v2.crypto_chassis.data.client as iccdc
import im_v2.im_lib_tasks as imvimlita

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
def get_example_config() -> cconfig.Config:
    """
    Config for comparison of 1sec CryptoChassis and 1sec CCXT bid/ask data.
    """
    config = cconfig.Config()
    param_dict = {
        "data": {
            # Whether to resample 1sec data to 1min using our production flow.
            # TODO(Danya): Variable overlaps with `resample_1min` parameter for clients.
            "resample_1sec_to_1min": False,
            # Parameters for client initialization.
            "cc_im_client": {
                "universe_version": None,
                "resample_1min": False,
                "contract_type": "futures",
                "tag": "downloaded_1sec",
            },
            "ccxt_im_client": {
                "universe_version": "infer_from_data",
                "resample_1min": False,
                "db_connection": hsql.get_connection(
                    *hsql.get_connection_info_from_env_file(
                        imvimlita.get_db_env_path("dev")
                    )
                ),
                "table_name": "ccxt_bid_ask_futures_raw",
            },
            # Parameters for data query.
            "read_data": {
                # Get start/end ts as inputs to script.
                #  Note: DB data is archived to S3 every 3 days, so we should use
                #  only the latest dates.
                "start_ts": pd.Timestamp("2022-11-28 00:00:00+00:00"),
                "end_ts": pd.Timestamp("2022-11-29 00:00:00+00:00"),
                "columns": None,
                "filter_data_mode": "assert",
            },
        },
        "column_names": {
            "bid_ask_cols": [
                "bid_price",
                "bid_size",
                "ask_price",
                "ask_size",
            ],
        },
        "order_level": 1,
    }
    config = cconfig.Config.from_dict(param_dict)
    return config


config = get_example_config()
print(config)

# %% [markdown]
# # Clients

# %%
# CCXT client.
ccxt_im_client_config = config.get_and_mark_as_used(("data", "ccxt_im_client"))
ccxt_im_client = icdcl.CcxtSqlRealTimeImClient(**ccxt_im_client_config)
# CC client.
cc_parquet_client_config = config.get_and_mark_as_used(("data", "cc_im_client"))
cc_parquet_client = iccdc.get_CryptoChassisHistoricalPqByTileClient_example2(
    **cc_parquet_client_config
)

# %% [markdown]
# # Universe

# %%
# DB universe
ccxt_universe = ccxt_im_client.get_universe()
# CC universe.
cc_universe = cc_parquet_client.get_universe()
# Intersection of universes that will be used for analysis.
universe = list(set(ccxt_universe) & set(cc_universe))

# %%
compare_universe = hprint.set_diff_to_str(
    cc_universe, ccxt_universe, add_space=True
)
print(compare_universe)

# %% [markdown]
# # Load data

# %%
read_data_config = config.get_and_mark_as_used(("data", "read_data"))

# %% [markdown]
# ## Load CCXT

# %% run_control={"marked": true}
ccxt_df = ccxt_im_client.read_data(universe, **read_data_config)

# %%
display(ccxt_df.head(10))

# %% [markdown]
# On the first glance:
# - It has levels where they are not expected to be
# - The level columns are empty

# %% [markdown]
# ### Clean CCXT data

# %% run_control={"marked": true}
# TODO(Danya): What can be done to make these transformations universal?
#  "if"-switches based on vendor and type?

# Remove level suffix in the TOB column name.
ccxt_df.columns = ccxt_df.columns.str.replace("_l1", "")
# Remove all levels.
target_columns = [col for col in ccxt_df.columns if not col[-1].isnumeric()]
target_columns = [
    col for col in target_columns if col != "end_download_timestamp"
]
ccxt_df = ccxt_df[target_columns]
# CCXT timestamp data goes up to milliseconds, so one needs to round it to seconds.
ccxt_df.index = ccxt_df.reset_index()["timestamp"].apply(
    lambda x: x.ceil(freq="S")
)
display(ccxt_df.head(10))

# %% [markdown]
# ## Load СС

# %%
cc_df = cc_parquet_client.read_data(universe, **read_data_config)
display(cc_df.head(10))

# %% [markdown]
# # Resampling data

# %%
# Perform VWAP resampling if required by config.
resample_1min = config.get_and_mark_as_used(("data", "resample_1sec_to_1min"))
if resample_1min:
    # TODO(Danya): Function as-is has VWAP and TWAP modes and removes the `full_symbol` column.
    ccxt_df = imvcdttrut.resample_bid_ask_data_to_1min(ccxt_df, mode="VWAP")
    # Fixed during #CmTask3225
    cc_df = imvcdttrut.resample_bid_ask_data_to_1min(cc_df, mode="VWAP")
# %% [markdown]
# # Analysis

# %% [markdown]
# ## Merge CC and DB data into one DataFrame
#

# %%
ccxt_df = ccxt_df.reset_index().set_index(["timestamp", "full_symbol"])
cc_df = cc_df.reset_index().set_index(["timestamp", "full_symbol"])

# %%
data = ccxt_df.merge(
    cc_df,
    how="inner",
    left_index=True,
    right_index=True,
    suffixes=("_ccxt", "_cc"),
)

# %%
# Conduct a data sanity check.
# Get number of values for both datasets.
len_cc_data = len(cc_df)
len_ccxt_data = len(ccxt_df)
_LOG.info("Start date = %s", data.reset_index()["timestamp"].min())
_LOG.info("End date = %s", data.reset_index()["timestamp"].max())
_LOG.info(
    "Avg observations per coin = %s",
    len(data) / len(data.reset_index()["full_symbol"].unique()),
)
# Move the same metrics from two vendors together.
data = data.reindex(sorted(data.columns), axis=1)
# NaNs observation.
nans_cc = len(data[data["bid_price_cc"].isna()])
nans_ccxt = len(data[data["bid_price_ccxt"].isna()])
_LOG.info(
    "Number of observations with NaNs in CryptoChassis = %s (%s%%)",
    nans_cc,
    nans_cc / len_cc_data,
)
_LOG.info(
    "Number of observations with NaNs in CCXT = %s (%s%%)",
    nans_ccxt,
    nans_ccxt / len_ccxt_data,
)
# Remove NaNs.
data = hpandas.dropna(data, report_stats=True)
#
# Zero bid size.
zero_bid_size_cc = len(data[data["bid_size_cc"] == 0])
_LOG.info(
    "Number of observations with bid_size=0 in CryptoChassis = %s (%s%%)",
    zero_bid_size_cc,
    zero_bid_size_cc / len_cc_data,
)
zero_bid_size_ccxt = len(data[data["bid_size_ccxt"] == 0])
_LOG.info(
    "Number of observations with bid_size=0 in CCXT = %s (%s%%)",
    zero_bid_size_cc,
    zero_bid_size_ccxt / len_ccxt_data,
)
# Zero ask size.
zero_ask_size_cc = len(data[data["ask_size_cc"] == 0])
_LOG.info(
    "Number of observations with ask_size=0 in CryptoChassis = %s (%s%%)",
    zero_ask_size_cc,
    zero_ask_size_cc / len_cc_data,
)
zero_ask_size_ccxt = len(data[data["ask_size_ccxt"] == 0])
_LOG.info(
    "Number of observations with ask_size=0 in CCXT = %s (%s%%)",
    zero_ask_size_cc,
    zero_ask_size_ccxt / len_ccxt_data,
)
#
# Bid !< Ask.
small_bid_cc = len(data[data["ask_price_cc"] >= data["bid_price_cc"]])
_LOG.info(
    "Number of observations with ask_price >= bid_price in CryptoChassis = %s (%s%%)",
    small_bid_cc,
    small_bid_cc / len_cc_data,
)
small_bid_ccxt = len(data[data["ask_price_ccxt"] >= data["bid_price_ccxt"]])
_LOG.info(
    "Number of observations with ask_price >= bid_price in CCXT = %s (%s%%)",
    small_bid_ccxt,
    small_bid_ccxt / len_ccxt_data,
)
#
display(data.tail())

# %% [markdown]
# ## Calculate differences

# %%
# Full symbol will not be relevant in calculation loops below.
bid_ask_cols = config.get_and_mark_as_used(("column_names", "bid_ask_cols"))
# Each bid ask value will have a notional and a relative difference between two sources.
for col in bid_ask_cols:
    # Notional difference: CC value - DB value.
    data[f"{col}_diff"] = data[f"{col}_cc"] - data[f"{col}_ccxt"]
    # Relative value: (CC value - DB value)/DB value.
    data[f"{col}_relative_pct_diff"] = (
        100 * (data[f"{col}_cc"] - data[f"{col}_ccxt"]) / data[f"{col}_ccxt"]
    )

# %%
# Calculate the mean value of differences for each coin.
diff_stats = []
grouper = data.groupby(["full_symbol"])
for col in bid_ask_cols:
    diff_stats.append(grouper[f"{col}_diff"].mean())
    diff_stats.append(grouper[f"{col}_relative_pct_diff"].mean())
#
diff_stats = pd.concat(diff_stats, axis=1)

# %% [markdown]
# ## Show stats for differences (in %)

# %% [markdown]
# ### Prices

# %%
display(
    diff_stats[["bid_price_relative_pct_diff", "ask_price_relative_pct_diff"]]
)

# %% [markdown]
# ### Sizes

# %%
display(diff_stats[["bid_size_relative_pct_diff", "ask_size_relative_pct_diff"]])

# %% [markdown]
# ## Correlations

# %% [markdown]
# ### Bid price

# %%
bid_price_corr_matrix = (
    data[["bid_price_cc", "bid_price_ccxt"]].groupby(level=1).corr()
)
display(bid_price_corr_matrix)

# %% [markdown]
# ### Ask price

# %%
ask_price_corr_matrix = (
    data[["ask_price_cc", "ask_price_ccxt"]].groupby(level=1).corr()
)
display(ask_price_corr_matrix)

# %% [markdown]
# ### Bid size

# %%
bid_size_corr_matrix = (
    data[["bid_size_cc", "bid_size_ccxt"]].groupby(level=1).corr()
)
display(bid_size_corr_matrix)

# %% [markdown]
# ### Ask size

# %%
ask_size_corr_matrix = (
    data[["ask_size_cc", "ask_size_ccxt"]].groupby(level=1).corr()
)
display(ask_size_corr_matrix)

# %% [markdown]
# # Check unused variables in config

# %% run_control={"marked": true}
display(config)
