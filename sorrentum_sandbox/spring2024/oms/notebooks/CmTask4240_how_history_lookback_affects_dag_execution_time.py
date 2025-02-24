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

# %% [markdown]
# The goal of the notebook is to measure the effect on DAG execution time from using a shorter history lookback period.

# %% [markdown]
# Compare the results: history lookback is 4 days vs history lookback is 15 minutes.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import pandas as pd

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
# # Specify the paths

# %%
system_log_path_dict = {
    "lookback_4_days": "/shared_data/ecs/preprod/twap_experiment/system_reconciliation/C3a/20230413/system_log_dir.scheduled.20230413_143500.20230413_203000",
    "lookback_15_minutes": "/shared_data/system_log_dir_20230417_lookback_experiment",
}
system_log_path_dict

# %%
data_type = "dag_data"
dag_path_dict = {
    "lookback_4_days": reconcil.get_data_type_system_log_path(
        system_log_path_dict["lookback_4_days"], data_type
    ),
    "lookback_15_minutes": reconcil.get_data_type_system_log_path(
        system_log_path_dict["lookback_15_minutes"], data_type
    ),
}
dag_path_dict

# %% [markdown]
# # Compare DAG execution time

# %%
df_dag_execution_time_4_days = dtfcore.get_execution_time_for_all_dag_nodes(
    dag_path_dict["lookback_4_days"]
)
df_dag_execution_time_15_minutes = dtfcore.get_execution_time_for_all_dag_nodes(
    dag_path_dict["lookback_15_minutes"]
)

# %%
dtfcore.plot_dag_execution_stats(df_dag_execution_time_4_days, report_stats=True)

# %%
dtfcore.plot_dag_execution_stats(
    df_dag_execution_time_15_minutes, report_stats=True
)

# %% [markdown]
# # Sanity check the DAG node output size

# %%
read_data_node = "predict.0.read_data"
resample_node = "predict.2.resample"
timestamp_lookback_15_minutes = pd.Timestamp("2023-04-17 10:35:00")
timestamp_lookback_lookback_4_days = pd.Timestamp("2023-04-13 10:35:00")

# %%
read_data_4_days = dtfcore.get_dag_node_output(
    dag_path_dict["lookback_4_days"],
    read_data_node,
    timestamp_lookback_lookback_4_days,
)
_LOG.info(
    "The df size is %s rows x %s columns",
    read_data_4_days.shape[0],
    read_data_4_days.shape[1],
)

# %%
read_data_15_minutes = dtfcore.get_dag_node_output(
    dag_path_dict["lookback_15_minutes"],
    read_data_node,
    timestamp_lookback_15_minutes,
)
_LOG.info(
    "The df size is %s rows x %s columns",
    read_data_15_minutes.shape[0],
    read_data_15_minutes.shape[1],
)

# %%
resample_4_days = dtfcore.get_dag_node_output(
    dag_path_dict["lookback_4_days"],
    resample_node,
    timestamp_lookback_lookback_4_days,
)
_LOG.info(
    "The df size is %s rows x %s columns",
    resample_4_days.shape[0],
    resample_4_days.shape[1],
)

# %%
resample_15_minutes = dtfcore.get_dag_node_output(
    dag_path_dict["lookback_15_minutes"],
    resample_node,
    timestamp_lookback_15_minutes,
)
_LOG.info(
    "The df size is %s rows x %s columns",
    resample_15_minutes.shape[0],
    resample_15_minutes.shape[1],
)
