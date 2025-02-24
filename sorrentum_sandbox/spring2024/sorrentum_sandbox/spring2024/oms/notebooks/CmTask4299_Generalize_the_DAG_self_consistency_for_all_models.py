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
# %matplotlib inline

# %%
import logging
import os
from typing import List, Tuple

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
# # Build config

# %%
# Specify the config directly when running the notebook manually.
# Below is just an example.
dst_root_dir = "/shared_data/ecs/preprod/prod_reconciliation/"
dag_builder_name = "C1b"
start_timestamp_as_str = "20230501_131000"
end_timestamp_as_str = "20230502_130500"
run_mode = "paper_trading"
mode = "scheduled"
config_list = reconcil.build_reconciliation_configs(
    dst_root_dir,
    dag_builder_name,
    start_timestamp_as_str,
    end_timestamp_as_str,
    run_mode,
    mode,
)
config = config_list[0]
print(config)

# %% [markdown]
# # DAG self-consistency check

# %%
prod_system_log_dir = config["system_log_path"]["prod"]
prod_dag_path = os.path.join(prod_system_log_dir, "dag/node_io/node_io.data")
# Get DAG node names.
dag_node_names = dtfcore.get_dag_node_names(prod_dag_path)
_LOG.info(
    "First node='%s' / Last node='%s'", dag_node_names[0], dag_node_names[-1]
)

# %%
# Get timestamps for the last DAG node.
dag_node_timestamps = dtfcore.get_dag_node_timestamps(
    prod_dag_path, dag_node_names[-1], as_timestamp=True
)
_LOG.info(
    "First timestamp='%s'/ Last timestamp='%s'",
    dag_node_timestamps[0][0],
    dag_node_timestamps[-1][0],
)


# %% [markdown]
# ## Check DAG self-consistency.

# %%
def load_dag_outputs(
    node_name: str, timestamps: List[pd.Timestamp]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Load DAG output at `bar_timestamp = t`.
    current_df = dtfcore.get_dag_node_output(
        prod_dag_path, node_name, timestamps[1]
    )
    current_df = current_df.sort_index()
    # Load DAG output at `bar_timestamp = t-1`.
    previous_df = dtfcore.get_dag_node_output(
        prod_dag_path, node_name, timestamps[0]
    )
    previous_df = previous_df.sort_index()
    return previous_df, current_df


# %% [markdown]
# ## Use current and previous timestamp, i.e.  `bar_timestamp = t` and  `bar_timestamp = t-1`

# %%
def check_diff(
    previous_df: pd.DataFrame, current_df: pd.DataFrame
) -> pd.DatetimeIndex:
    # Remove the first row from the previous_df and the last one from
    # the current_df to align indices.
    previous_df = previous_df[1:]
    current_df = current_df[:-1]
    compare = previous_df.compare(current_df)
    return compare


# %% [markdown]
# ### Use the 2 last timestamps.

# %%
node_name = dag_node_names[-1]
timestamps = [dag_node_timestamps[-2][0], dag_node_timestamps[-1][0]]
previous_df, current_df = load_dag_outputs(node_name, timestamps)

# %%
check_diff(previous_df, current_df)

# %% [markdown]
# ### Use the 2 first timestamps.

# %%
node_name = dag_node_names[-1]
timestamps = [dag_node_timestamps[0][0], dag_node_timestamps[1][0]]
previous_df, current_df = load_dag_outputs(node_name, timestamps)

# %%
check_diff(previous_df, current_df)

# %% [markdown]
# <b> Every difference output has an interval 25 mins, i.e. from 6:20:00 - 6:45:00. Firstly we have 10 mins between timestamps, i.e. 6:20:00 - 6:30:00, the rest of them is 5 mins intervals. The interval varies for each timestamp. These differences are in the history look-back period. The reason why difference appeared is that `previous_df` has a value, e.g. `-1.3` in the first column, meanwhile `current_df` has `NaN` and so among all columns. This is burn-in interval which we remove in `_prepare_dfs_for_comparison()`. Seems like all comparisons will have 6 rows difference approximately.</b>
