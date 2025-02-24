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
# TODO(Grisha): unit test the notebook.

# %% [markdown]
# The notebook loads prod system run output for debugging purposes. E.g., loads DAG output for a specific node / bar timestamp to check the data.

# %% [markdown]
# # Imports

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
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import reconciliation as reconcil

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build the config

# %%
# Get config from env when running the notebook via the `run_notebook.py` script, e.g.,
# in the system reconciliation flow.
config = cconfig.get_config_from_env()
if config:
    _LOG.info("Using config from env vars")
else:
    _LOG.info("Using hardwired config")
    # Specify the config directly when running the notebook manually.
    # Below is just an example.
    config_dict = {
        "dst_root_dir": "/shared_data/ecs/preprod/system_reconciliation",
        "dag_builder_name": "C5b",
        "run_mode": "paper_trading",
        "start_timestamp_as_str": "20230713_131000",
        "end_timestamp_as_str": "20230714_130500",
        "mode": "scheduled",
        "node_name": "predict.9.process_forecasts",
        "bar_timestamp": pd.Timestamp("2023-07-13 10:20:00-04:00"),
        "asset_id": 2484635488,
        "columns": ["close", "feature"],
    }
    config = cconfig.Config.from_dict(config_dict)
print(config)

# %% [markdown]
# # Specify data to load

# %%
target_dir = reconcil.get_target_dir(
    config["dst_root_dir"],
    config["dag_builder_name"],
    config["run_mode"],
    config["start_timestamp_as_str"],
    config["end_timestamp_as_str"],
)
system_log_dir = reconcil.get_prod_system_log_dir(config["mode"])
system_log_dir = os.path.join(target_dir, system_log_dir)
_LOG.info("system_log_dir=%s", system_log_dir)

# %%
dag_data_dir = reconcil.get_data_type_system_log_path(system_log_dir, "dag_data")
_LOG.info("dag_data_dir=%s", dag_data_dir)

# %%
# Get DAG node names.
dag_node_names = dtfcore.get_dag_node_names(dag_data_dir)
dag_node_names

# %%
# Get timestamps for the specified DAG node.
dag_node_timestamps = dtfcore.get_dag_node_timestamps(
    dag_data_dir, config["node_name"], as_timestamp=True
)
_LOG.info(
    "First timestamp='%s'/ Last timestamp='%s'",
    dag_node_timestamps[0][0],
    dag_node_timestamps[-1][0],
)

# %% [markdown]
# # Load data

# %%
# Load data for a given DAG node and a bar timestmap.
node_df = dtfcore.get_dag_node_output(
    dag_data_dir, config["node_name"], config["bar_timestamp"]
)
node_df.tail(3)

# %%
# Filter by specified asset and display only relevant columns.
slice_df = cofinanc.get_asset_slice(node_df, config["asset_id"])[
    config["columns"]
]
slice_df.tail(3)

# %%
