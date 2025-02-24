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

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import im_v2.im_lib_tasks as imvimlita

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Data delay analysis

# %%
# Get the real-time `ImClient`.
# TODO(Grisha): ideally we should get the values from the config.
resample_1min = False
env_file = imvimlita.get_db_env_path("dev")
connection_params = hsql.get_connection_info_from_env_file(env_file)
db_connection = hsql.get_connection(*connection_params)
table_name = "ccxt_ohlcv_futures"
#
im_client = icdcl.CcxtSqlRealTimeImClient(
    resample_1min, db_connection, table_name
)

# %%
# Get the universe.
# TODO(Grisha): get the version from the config.
vendor = "CCXT"
mode = "trade"
version = "v7.1"
as_full_symbol = True
full_symbols = ivcu.get_vendor_universe(
    vendor,
    mode,
    version=version,
    as_full_symbol=as_full_symbol,
)
full_symbols

# %%
# Load the data for the reconciliation date.
# `ImClient` operates in UTC timezone.
# TODO(Grisha): ideally we should get the values from the config.
date_str = "2022-10-28"
start_ts = pd.Timestamp(date_str, tz="UTC")
end_ts = start_ts + pd.Timedelta(days=1)
columns = None
filter_data_mode = "assert"
df = im_client.read_data(
    full_symbols, start_ts, end_ts, columns, filter_data_mode
)
hpandas.df_to_str(df, num_rows=5, log_level=logging.INFO)

# %%
# TODO(Grisha): move to a lib.
# Compute delay in seconds.
df["delta"] = (df["knowledge_timestamp"] - df.index).dt.total_seconds()
# Plot the delay over assets with the errors bars.
delta_per_asset = df.groupby(by=["full_symbol"])["delta"]
minimums = delta_per_asset.min()
maximums = delta_per_asset.max()
means = delta_per_asset.mean()
errors = [means - minimums, maximums - means]
# TODO(Grisha): sort by maximum delay.
means.plot(kind="bar", yerr=errors, title="DB delay in seconds per asset")

# %%
