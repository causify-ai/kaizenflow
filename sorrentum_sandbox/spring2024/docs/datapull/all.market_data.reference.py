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
# The notebook demonstrates how to use `MarketData`.

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import market_data.market_data_example as mdmadaex

# %%
log_level = logging.INFO
hdbg.init_logger(verbosity=log_level)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Get asset ids

# %%
universe_version = "v7.4"
universe_config = {
    "vendor": "CCXT",
    "version": universe_version,
    "mode": "trade",
    "as_full_symbol": True,
}

# %%
full_symbols = ivcu.get_vendor_universe(**universe_config)
# Use only a subset for the demonstration.
full_symbols = full_symbols[4:6]
_LOG.info("Full symbols=%s", full_symbols)

# %%
asset_ids = list(ivcu.build_numerical_to_string_id_mapping(full_symbols).keys())
_LOG.info("Asset ids=%s", asset_ids)

# %% [markdown]
# # `ImClientMarketData`

# %%
im_client_market_data_config = {
    "start_timestamp": pd.Timestamp("2023-09-11T00:00:00", tz="UTC"),
    "end_timestamp": pd.Timestamp("2023-09-11T04:00:00", tz="UTC"),
    "im_client": {
        "universe_version": universe_version,
        "root_dir": "s3://cryptokaizen-data-test/v3",
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
    "ts_col_name": "timestamp",
    "columns": None,
    "column_remap": None,
    "filter_data_mode": "assert",
    "wall_clock_time": pd.Timestamp("2100-01-01 00:00:00+00:00"),
}
im_client_market_data_config = cconfig.Config().from_dict(
    im_client_market_data_config
)
print(im_client_market_data_config)

# %%
ohlcv_im_client = icdcl.CcxtHistoricalPqByTileClient(
    **im_client_market_data_config["im_client"]
)
ohlcv_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    ohlcv_im_client,
    asset_ids,
    im_client_market_data_config["columns"],
    im_client_market_data_config["column_remap"],
    wall_clock_time=im_client_market_data_config["wall_clock_time"],
    filter_data_mode=im_client_market_data_config["filter_data_mode"],
)
ohlcv_data = ohlcv_market_data.get_data_for_interval(
    im_client_market_data_config["start_timestamp"],
    im_client_market_data_config["end_timestamp"],
    im_client_market_data_config["ts_col_name"],
    asset_ids,
)
ohlcv_data.head(3)

# %% [markdown]
# # `StitchedMarketData`

# %%
stitched_market_data_config = {
    "start_timestamp": pd.Timestamp("2023-05-01T00:00:00", tz="UTC"),
    "end_timestamp": pd.Timestamp("2023-05-10T04:00:00", tz="UTC"),
    "ohlcv_market_data": {
        "im_client": {
            "universe_version": universe_version,
            "root_dir": "s3://cryptokaizen-unit-test/outcomes/Test_run_all_market_data_reference_notebook/v3/",
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
        "ts_col_name": "timestamp",
        "columns": None,
        "column_remap": None,
        "filter_data_mode": "assert",
    },
    "bid_ask_market_data": {
        "im_client": {
            # Download universe version.
            "universe_version": universe_version,
            "dataset": "bid_ask",
            "contract_type": "futures",
            # Data snapshot is not applicable for data version = "v3".
            "data_snapshot": "",
            "universe_version": universe_version,
            # Data currently residing in the test bucket
            "root_dir": "s3://cryptokaizen-unit-test/outcomes/Test_run_all_market_data_reference_notebook/v3/",
            "partition_mode": "by_year_month",
            "dataset": "bid_ask",
            "contract_type": "futures",
            # v2_0_0 is used due to addition of new column in #CmTask7224.
            "version": "v2_0_0",
            "download_universe_version": "v7",
            "tag": "resampled_1min",
            "aws_profile": "ck",
        },
        "ts_col_name": "timestamp",
        # TODO(Grisha): for some reason the current filtering mechanism filters out `asset_ids` which
        # makes it impossible to stitch the 2 market data dfs. So adding the necessary columns manually.
        # Note(Juraj): we currently resampled only top of the book so no need to filter the columns
        # "columns": cfibiask.get_bid_ask_columns_by_level(1)
        # + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
        "columns": None,
        "column_remap": None,
        "filter_data_mode": "assert",
    },
    "stitched_market_data": {
        "ts_col_name": "timestamp",
        "columns": None,
        "column_remap": None,
        # TODO(Grisha): check why it fails when the mode is `assert`.
        "filter_data_mode": "warn_and_trim",
    },
}
stitched_market_data_config = cconfig.Config().from_dict(
    stitched_market_data_config
)
print(stitched_market_data_config)

# %%
ohlcv_im_client = icdcl.CcxtHistoricalPqByTileClient(
    **stitched_market_data_config["ohlcv_market_data"]["im_client"]
)
ohlcv_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    ohlcv_im_client,
    asset_ids,
    stitched_market_data_config["ohlcv_market_data"]["columns"],
    stitched_market_data_config["ohlcv_market_data"]["column_remap"],
    filter_data_mode=stitched_market_data_config["ohlcv_market_data"][
        "filter_data_mode"
    ],
)
ohlcv_data = ohlcv_market_data.get_data_for_interval(
    stitched_market_data_config["start_timestamp"],
    stitched_market_data_config["end_timestamp"],
    stitched_market_data_config["ohlcv_market_data"]["ts_col_name"],
    asset_ids,
)
ohlcv_data.head(3)

# %%
bid_ask_im_client = icdcl.CcxtHistoricalPqByTileClient(
    **stitched_market_data_config["bid_ask_market_data"]["im_client"]
)
bid_ask_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    bid_ask_im_client,
    asset_ids,
    stitched_market_data_config["bid_ask_market_data"]["columns"],
    stitched_market_data_config["bid_ask_market_data"]["column_remap"],
    filter_data_mode=stitched_market_data_config["bid_ask_market_data"][
        "filter_data_mode"
    ],
)

# %%
stitched_mdata = mdmadaex.get_HorizontalStitchedMarketData_example1(
    bid_ask_market_data,
    ohlcv_market_data,
    asset_ids,
    stitched_market_data_config["stitched_market_data"]["columns"],
    stitched_market_data_config["stitched_market_data"]["column_remap"],
    filter_data_mode=stitched_market_data_config["stitched_market_data"][
        "filter_data_mode"
    ],
)
stitched_mdata_df = stitched_mdata.get_data_for_interval(
    stitched_market_data_config["start_timestamp"],
    stitched_market_data_config["end_timestamp"],
    stitched_market_data_config["stitched_market_data"]["ts_col_name"],
    asset_ids,
)
stitched_mdata_df.head(3)

# %% [markdown]
# # `ReplayedMarketData`

# %%
# TODO(Dan): Add reference code for `ReplayedMarketData`.

# %%
