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
# # Descrption

# %% [markdown]
# The notebook runs the Mock3 pipeline using stitched data (OHLCV and bid/ask).

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

import core.config as cconfig
import core.finance.bid_ask as cfibiask
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.pipelines.mock3.mock3_pipeline as dtfapmmopi
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import market_data.market_data_example as mdmadaex

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Config

# %%
bid_ask_level = 1
_LOG.info("Order book depth=%s", bid_ask_level)

# %%
trade_universe_version = "v7.5"
_LOG.info("Trade universe version=%s", trade_universe_version)

# %%
config = {
    "universe": {
        "vendor": "CCXT",
        "version": trade_universe_version,
        "mode": "trade",
    },
    "start_timestamp": pd.Timestamp("2023-09-11T00:00:00", tz="UTC"),
    "end_timestamp": pd.Timestamp("2023-09-11T04:00:00", tz="UTC"),
    "ohlcv_market_data": {
        "ohlcv_im_client_config": {
            # Download universe version.
            "download_universe_version": "v7_3",
            "dataset": "ohlcv",
            "contract_type": "futures",
            # Data snapshot is not applicable for data version = "v3".
            "data_snapshot": "",
            "universe_version": trade_universe_version,
            # Data currently residing in the test bucket
            "root_dir": "s3://cryptokaizen-data.preprod/v3/",
            "partition_mode": "by_year_month",
            "version": "v1_0_0",
            "tag": "downloaded_1min",
            "aws_profile": "ck",
        },
        "ts_col_name": "timestamp",
        "columns": None,
        "column_remap": None,
        "wall_clock_time": pd.Timestamp("2100-01-01T00:00:00+00:00"),
        "filter_data_mode": "assert",
    },
    "bid_ask_market_data": {
        "bid_ask_im_client_config": {
            # Download universe version.
            "download_universe_version": "v7",
            "dataset": "bid_ask",
            "contract_type": "futures",
            # Data snapshot is not applicable for data version = "v3".
            "data_snapshot": "",
            "universe_version": trade_universe_version,
            # Data currently residing in the test bucket
            "root_dir": "s3://cryptokaizen-data.preprod/v3/",
            "partition_mode": "by_year_month",
            "version": "v1_0_0",
            "tag": "resampled_1min",
            "aws_profile": "ck",
        },
        "ts_col_name": "timestamp",
        # TODO(Grisha): for some reason the current filtering mechanism filters out `asset_ids` which
        # makes it impossible to stitch the 2 market data dfs. So adding the necessary columns manually.
        "columns": cfibiask.get_bid_ask_columns_by_level(bid_ask_level)
        + ["asset_id", "full_symbol", "start_ts", "knowledge_timestamp"],
        "column_remap": None,
        "wall_clock_time": pd.Timestamp("2100-01-01T00:00:00+00:00"),
        "filter_data_mode": "assert",
    },
    "stitched_market_data": {
        "ts_col_name": "timestamp",
        "columns": None,
        "column_remap": None,
        # TODO(Grisha): check why it fails when the mode is `assert`.
        "filter_data_mode": "warn_and_trim",
    },
    "historical_data_source": {
        "nid": "read_data",
        "ts_col_name": "end_ts",
        "multiindex_output": True,
        "columns_to_remove": ["start_ts", "full_symbol"],
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # HistoricalDataSource

# %%
as_full_symbol = True
full_symbols = ivcu.get_vendor_universe(
    config["universe"]["vendor"],
    config["universe"]["mode"],
    version=config["universe"]["version"],
    as_full_symbol=as_full_symbol,
)
# Use only a subset for the demonstration.
_LOG.info("Full symbols=%s", full_symbols)

# %%
asset_ids = list(ivcu.build_numerical_to_string_id_mapping(full_symbols).keys())
_LOG.info("Asset ids=%s", asset_ids)

# %%
ohlcv_im_client = icdcl.CcxtHistoricalPqByTileClient(
    **config["ohlcv_market_data"]["ohlcv_im_client_config"]
)
ohlcv_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    ohlcv_im_client,
    asset_ids,
    config["ohlcv_market_data"]["columns"],
    config["ohlcv_market_data"]["column_remap"],
    wall_clock_time=config["ohlcv_market_data"]["wall_clock_time"],
    filter_data_mode=config["ohlcv_market_data"]["filter_data_mode"],
)

# %%
bid_ask_im_client = icdcl.CcxtHistoricalPqByTileClient(
    **config["bid_ask_market_data"]["bid_ask_im_client_config"]
)
bid_ask_market_data = mdmadaex.get_HistoricalImClientMarketData_example1(
    bid_ask_im_client,
    asset_ids,
    config["bid_ask_market_data"]["columns"],
    config["bid_ask_market_data"]["column_remap"],
    wall_clock_time=config["bid_ask_market_data"]["wall_clock_time"],
    filter_data_mode=config["bid_ask_market_data"]["filter_data_mode"],
)

# %%
stitched_mdata = mdmadaex.get_HorizontalStitchedMarketData_example1(
    bid_ask_market_data,
    ohlcv_market_data,
    asset_ids,
    config["stitched_market_data"]["columns"],
    config["stitched_market_data"]["column_remap"],
    filter_data_mode=config["stitched_market_data"]["filter_data_mode"],
)

# %%
data_source_node = dtfsys.HistoricalDataSource(
    config["historical_data_source"]["nid"],
    stitched_mdata,
    config["historical_data_source"]["ts_col_name"],
    config["historical_data_source"]["multiindex_output"],
    col_names_to_remove=config["historical_data_source"]["columns_to_remove"],
)
data_source_node.set_fit_intervals(
    [(config["start_timestamp"], config["end_timestamp"])]
)

# %% [markdown]
# # Build and run the DAG

# %%
dag_builder = dtfapmmopi.Mock3_DagBuilder()
dag = dag_builder.get_fully_built_dag()
dtfcore.draw(dag)

# %%
dag.insert_at_head(data_source_node)
dtfcore.draw(dag)

# %% run_control={"marked": true}
dag_df_out = dag.run_leq_node("compute_half_spread_in_bps", "fit")["df_out"]
dag_df_out.head(5)
