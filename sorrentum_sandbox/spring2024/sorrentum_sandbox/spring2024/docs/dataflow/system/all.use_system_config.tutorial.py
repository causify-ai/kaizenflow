# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# TODO(Grisha): does it belong to `dataflow/system` or to `dataflow_amp/system`?

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
import os

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.system as dtfsys
import dataflow.universe as dtfuniver
# TODO(Grisha): import as package.
import dataflow_amp.system.mock1.mock1_forecast_system as dtfasmmfosy
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Initialize the System

# %% [markdown]
# During this stage only the DAG config is built.

# %%
system = dtfasmmfosy.Mock1_NonTime_ForecastSystem()
print(system.config)

# %% [markdown]
# # Fill the SystemConfig

# %% [markdown]
# The parameters are required to instantiate System's components (e.g., MarketData, DAG).

# %%
# Fill the backtest config section.
backtest_config = "mock1_v1-top2.5T.Jan2000"
(
    universe_str,
    trading_period_str,
    time_interval_str,
) = cconfig.parse_backtest_config(backtest_config)
hdbg.dassert_in(trading_period_str, ("1T", "5T", "15T"))
# Override the resampling frequency using the backtest config.
system.config[
    "dag_config", "resample", "transformer_kwargs", "rule"
] = trading_period_str
system.config["backtest_config", "universe_str"] = universe_str
system.config["backtest_config", "trading_period_str"] = trading_period_str
system.config["backtest_config", "time_interval_str"] = time_interval_str
system.config["backtest_config", "freq_as_pd_str"] = "M"
system.config["backtest_config", "lookback_as_pd_str"] = "10D"
# TODO(Grisha): the parameters below should be a function of `time_interval_str`.
system.config[
    "backtest_config", "start_timestamp_with_lookback"
] = pd.Timestamp("2000-01-01 00:00:00+0000", tz="UTC")
system.config["backtest_config", "end_timestamp"] = pd.Timestamp(
    "2000-01-31 00:00:00+0000", tz="UTC"
)
print(system.config)

# %%
# Specify ImClient ctor and its configuration and fill the market data config.
vendor = "mock1"
mode = "trade"
universe = ivcu.get_vendor_universe(
    vendor, mode, version="v1", as_full_symbol=True
)
df = cofinanc.get_MarketData_df6(universe)
system.config[
    "market_data_config", "im_client_ctor"
] = icdc.get_DataFrameImClient_example1
system.config[
    "market_data_config", "im_client_config"
] = cconfig.Config().from_dict({"df": df})
# Build ImClient and write it to config.
im_client = dtfsys.build_ImClient_from_System(system)
universe_str = system.config["backtest_config", "universe_str"]
full_symbols = dtfuniver.get_universe(universe_str)
asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)
#
system.config["market_data_config", "im_client"] = im_client
system.config["market_data_config", "asset_ids"] = asset_ids
system.config["market_data_config", "asset_id_col_name"] = "asset_id"
print(system.config)

# %% [markdown]
# # Build all the components and run the System.

# %%
# Calling a DagRunner builds all the components.
dag_runner = system.dag_runner
print(system.is_fully_built())

# %%
# Extract run parameters from the SystemConfig and run.
start_datetime = system.config[
    "backtest_config", "start_timestamp_with_lookback"
]
end_datetime = system.config["backtest_config", "end_timestamp"]
dag_runner.set_predict_intervals([(start_datetime, end_datetime)])
result_bundle = dag_runner.predict()
result_df = result_bundle.result_df
result_df.tail(3)
