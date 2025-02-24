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

# %%
# %load_ext autoreload
# %autoreload 2

# %% [markdown]
# # Imports

# %%
import logging

import pandas as pd

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
import market_data as mdata

# %%
hdbg.init_logger(verbosity=logging.INFO)
log_level = logging.INFO

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build config

# %%
config = {
    "start_ts": None,
    "end_ts": None,
    "wall_clock_time": pd.Timestamp("2100-01-01T00:00:00+00:00"),
    "columns": None,
    "columns_remap": None,
    "ts_col_name": "end_ts",
    "im_client": {
        "vendor": "bloomberg",
        "universe_version": "v1",
        "root_dir": "s3://cryptokaizen-data-test/v3/bulk",
        "partition_mode": "by_year_month",
        "dataset": "ohlcv",
        "contract_type": "spot",
        "data_snapshot": "",
        "download_mode": "manual",
        "downloading_entity": "",
        "aws_profile": "ck",
        "resample_1min": False,
        "version": "v1_0_0",
        "tag": "resampled_1min",
    },
}
config = cconfig.Config.from_dict(config)
print(config)

# %% [markdown]
# # Load data

# %%
im_client = imvcdchpcl.HistoricalPqByCurrencyPairTileClient(**config["im_client"])

# %%
full_symbols = im_client.get_universe()
filter_data_mode = "assert"
actual_df = im_client.read_data(
    full_symbols,
    config["start_ts"],
    config["end_ts"],
    config["columns"],
    filter_data_mode,
)
hpandas.df_to_str(actual_df, num_rows=5, log_level=logging.INFO)

# %% run_control={"marked": true}
asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)
market_data = mdata.get_HistoricalImClientMarketData_example1(
    im_client,
    asset_ids,
    config["columns"],
    config["columns_remap"],
    wall_clock_time=config["wall_clock_time"],
)

# %%
asset_ids = None
market_data_df = market_data.get_data_for_interval(
    config["start_ts"], config["end_ts"], config["ts_col_name"], asset_ids
)
hpandas.df_to_str(market_data_df, num_rows=5, log_level=logging.INFO)
