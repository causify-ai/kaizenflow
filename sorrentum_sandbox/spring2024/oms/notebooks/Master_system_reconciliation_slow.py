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
# The notebook contains full versions of DAG output checks that compare the prod system output vs that of the prod simulation run.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging

import core.config as cconfig
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import reconciliation as reconcil

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build the reconciliation config

# %%
# When running manually, specify the path to the config to load config from file,
# for e.g., `.../reconciliation_notebook/fast/result_0/config.pkl`.
config_file_name = None
config = cconfig.get_notebook_config(config_file_name)
if config is None:
    _LOG.info("Using hardwired config")
    # Specify the config directly when running the notebook manually.
    # Below is just an example.
    dst_root_dir = "/shared_data/ecs/preprod/prod_reconciliation/"
    dag_builder_ctor_as_str = (
        "dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
    )
    start_timestamp_as_str = "20231103_131000"
    end_timestamp_as_str = "20231104_130500"
    run_mode = "paper_trading"
    mode = "scheduled"
    config_list = reconcil.build_reconciliation_configs(
        dst_root_dir,
        dag_builder_ctor_as_str,
        start_timestamp_as_str,
        end_timestamp_as_str,
        run_mode,
        mode,
    )
    config = config_list[0]
print(config)

# %% [markdown]
# # Specify data to load

# %% run_control={"marked": false}
# The dict points to `system_log_dir` for different experiments.
system_log_path_dict = dict(config["system_log_path"].to_dict())

# %%
# This dict points to `system_log_dir/dag/node_io/node_io.data` for different experiments.
data_type = "dag_data"
dag_path_dict = reconcil.get_system_log_paths(
    system_log_path_dict, data_type, only_warning=True
)
dag_path_dict

# %% [markdown]
# # DAG io

# %% [markdown]
# ## Load

# %%
# Get DAG node names.
get_dag_output_mode = config["meta"]["get_dag_output_mode"]
dag_path = reconcil.get_dag_output_path(dag_path_dict, get_dag_output_mode)
dag_node_names = dtfcore.get_dag_node_names(dag_path)
_LOG.info(
    "First node='%s' / Last node='%s'", dag_node_names[0], dag_node_names[-1]
)

# %%
# Get timestamps for the last DAG node.
dag_node_timestamps = dtfcore.get_dag_node_timestamps(
    dag_path, dag_node_names[-1], as_timestamp=True
)
_LOG.info(
    "First timestamp='%s'/ Last timestamp='%s'",
    dag_node_timestamps[0][0],
    dag_node_timestamps[-1][0],
)

# %%
# Get DAG output for the last node and the last timestamp.
dag_df = dtfcore.load_dag_outputs(dag_path, dag_node_names[-1])
_LOG.info("Output of the last node:\n")
hpandas.df_to_str(dag_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Check DAG io self-consistency

# %%
# TODO(Grisha): pass the value via config.
diff_threshold = 1e-3
compare_dfs_kwargs = {
    # TODO(Nina): CmTask4387 "DAG self-consistency check fails when
    # `history_lookback=15T` for C3a".
    "compare_nans": False,
    "diff_mode": "pct_change",
    "assert_diff_threshold": None,
}

# %%
# Run for all timestamps.
bar_timestamp = "all"
dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
    config["dag_builder_ctor_as_str"]
)
if dag_builder_name not in ["C11a", "C12a"]:
    # Self-consistency check fails for C11a. See CmTask6519
    # for more details. Also for C12a, see CmTask7053.
    # Compare DAG output at T with itself at time T-1.
    dtfcore.check_dag_output_self_consistency(
        dag_path,
        dag_node_names[-1],
        bar_timestamp,
        trading_freq=config["meta"]["bar_duration"],
        diff_threshold=diff_threshold,
        **compare_dfs_kwargs,
    )

# %% [markdown]
# ## Compare DAG io (prod vs sim)

# %%
# Run for all nodes and all timestamps.
bar_timestamp = "all"
node_name = "all"
_ = dtfcore.compare_dag_outputs(
    dag_path_dict,
    node_name,
    bar_timestamp,
    diff_threshold=diff_threshold,
    **compare_dfs_kwargs,
)
