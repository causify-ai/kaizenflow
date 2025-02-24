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
# # Descriptions

# %% [markdown]
# The notebook demonstrates how to use `ImClient`.

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %% [markdown]
# # Imports

# %%
import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe as ivcu

# %%
log_level = logging.INFO
hdbg.init_logger(verbosity=log_level)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
config = {
    "universe": {
        "vendor": "CCXT",
        "mode": "trade",
        "version": "v7.4",
        "as_full_symbol": True,
    },
    "start_timestamp": pd.Timestamp("2023-09-11T00:00:00", tz="UTC"),
    "end_timestamp": pd.Timestamp("2023-09-11T04:00:00", tz="UTC"),
    "columns": None,
    "filter_data_mode": "assert",
    "ohlcv_parquet_config": {
        "vendor": "ccxt",
        "universe_version": "v7.4",
        "root_dir": "s3://cryptokaizen-data/v3",
        "partition_mode": "by_year_month",
        "dataset": "ohlcv",
        "contract_type": "futures",
        "data_snapshot": "",
        "aws_profile": "ck",
        "resample_1min": False,
        "version": "v1_0_0",
        "download_universe_version": "v7_3",
        "tag": "downloaded_1min",
    },
    "bid_ask_parquet_config": {
        "vendor": "ccxt",
        "universe_version": "v7.4",
        "root_dir": "s3://cryptokaizen-data-test/v3",
        "partition_mode": "by_year_month",
        "dataset": "bid_ask",
        "contract_type": "futures",
        "data_snapshot": "",
        "version": "v1_0_0",
        "download_universe_version": "v7",
        "tag": "resampled_1min",
        "aws_profile": "ck",
    },
    "ohlcv_db_config": {
        "universe_version": "infer_from_data",
        "db_connection": imvcddbut.DbConnectionManager.get_connection("preprod"),
        "table_name": "ccxt_ohlcv_futures",
        "resample_1min": False,
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # CCXT Binance 1-minute futures data

# %%
full_symbols = ivcu.get_vendor_universe(**config["universe"])
_LOG.info("Full symbols number=%s", len(full_symbols))
full_symbols[:5]

# %% [markdown]
# ## OHLCV Parquet

# %%
ohlcv_im_client = icdc.HistoricalPqByCurrencyPairTileClient(
    **config["ohlcv_parquet_config"]
)

# %%
ohlcv_data = ohlcv_im_client.read_data(
    full_symbols,
    config["start_timestamp"],
    config["end_timestamp"],
    config["columns"],
    config["filter_data_mode"],
)
ohlcv_data.head()

# %% [markdown]
# ## Bid/ask Parquet

# %%
bid_ask_im_client = icdc.HistoricalPqByCurrencyPairTileClient(
    **config["bid_ask_parquet_config"]
)

# %%
bid_ask_data = bid_ask_im_client.read_data(
    full_symbols,
    config["start_timestamp"],
    config["end_timestamp"],
    config["columns"],
    config["filter_data_mode"],
)
bid_ask_data.head()

# %% [markdown]
# ## OHLCV Database

# %%
ohlcv_db_im_client = icdcl.CcxtSqlRealTimeImClient(**config["ohlcv_db_config"])

# %%
ohlcv_db_data = ohlcv_db_im_client.read_data(
    full_symbols,
    config["start_timestamp"],
    config["end_timestamp"],
    config["columns"],
    config["filter_data_mode"],
)
ohlcv_db_data.head()

# %% [markdown]
# # Mock `ImClient`

# %%
df = cofinanc.get_MarketData_df6(full_symbols)
df.head()

# %%
dataframe_im_client = icdc.DataFrameImClient(
    df,
    full_symbols,
)

# %%
start_timestamp = pd.Timestamp("2000-01-01 09:35:00-05:00")
end_timestamp = pd.Timestamp("2000-01-01 10:31:00-05:00")
#
ohlcv_from_df_data = dataframe_im_client.read_data(
    full_symbols,
    start_timestamp,
    end_timestamp,
    config["columns"],
    config["filter_data_mode"],
)
ohlcv_from_df_data.head()

# %%
