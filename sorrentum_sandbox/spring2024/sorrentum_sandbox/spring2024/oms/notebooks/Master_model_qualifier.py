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

# %%
# TODO(Grisha): this is a placeholder for the Master model qualifier notebook.
# The goal is to compare the prod system output when changing the system.config.

# TODO(Grisha): probably it belongs to `dataflow/system` or to `dataflow_amp/Cx/system`.
# TODO(Grisha): -> Master_system_config_qualifier?

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
import core.plotting as coplotti
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
# # Config

# %%
config = {
    "bar_duration": "5T",
    "run_dag_comparison": True,
    "system_log_dir_path": {
        "prod": "/shared_data/style_experiment/system_log_dir_style_cross_sectional",
        "candidate": "/shared_data/style_experiment/system_log_dir_style_longitudinal",
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Specify the paths to DAG and Portfolio results

# %%
# This dict points to `system_log_dir/dag/node_io/node_io.data` for different experiments.
data_type = "dag_data"
dag_path_dict = reconcil.get_system_log_paths(
    config["system_log_dir_path"].to_dict(), data_type
)
dag_path_dict

# %%
# This dict points to `system_log_dir/process_forecasts/portfolio` for different experiments.
data_type = "portfolio"
portfolio_path_dict = reconcil.get_system_log_paths(
    config["system_log_dir_path"].to_dict(), data_type
)
portfolio_path_dict

# %% [markdown]
# # Compare DAG output

# %%
if config["run_dag_comparison"]:
    # TODO(Grisha): consider comparing the output for all bars / nodes.
    # The last node, the last timestamp.
    node_name = "predict.5.process_forecasts"
    # TODO(Grisha): get the last bar programatically.
    bar_timestamp = pd.Timestamp(
        "2023-04-18 14:00:00-0400", tz="America/New_York"
    )
    # Load the data.
    dag_prod_df = dtfcore.get_dag_node_output(
        dag_path_dict["prod"], node_name, bar_timestamp
    )
    hpandas.df_to_str(dag_prod_df, num_rows=5, log_level=logging.INFO)
    #
    dag_candidate_df = dtfcore.get_dag_node_output(
        dag_path_dict["candidate"], node_name, bar_timestamp
    )
    hpandas.df_to_str(dag_candidate_df, num_rows=3, log_level=logging.INFO)
    # TODO(Grisha): move kwargs to a config layer.
    compare_dfs_kwargs = {
        "diff_mode": "pct_change",
        "assert_diff_threshold": None,
    }
    diff_df = hpandas.compare_dfs(
        dag_prod_df, dag_candidate_df, **compare_dfs_kwargs
    )
    max_diff = diff_df.abs().max().max()
    _LOG.info(
        "The maximum absolute difference between the DAG ouputs is: %s", max_diff
    )
else:
    # Sometimes it is ok that the DAG results do not match.
    _LOG.info("Skpping the DAG comparison stage as per request")

# %% [markdown]
# # Compare DAG execution time

# %%
# TODO(Grisha): create a plotting function that compares the results back-to-back instead
# of visually comparing 2 plots.

# %% [markdown]
# The DAG execution time almost did not change.

# %%
df_dag_execution_time_prod = dtfcore.get_execution_time_for_all_dag_nodes(
    dag_path_dict["prod"]
)
_LOG.info("DAG execution time:")
hpandas.df_to_str(df_dag_execution_time_prod, num_rows=3, log_level=logging.INFO)

# %%
df_dag_execution_time_candidate = dtfcore.get_execution_time_for_all_dag_nodes(
    dag_path_dict["candidate"]
)
_LOG.info("DAG execution time:")
hpandas.df_to_str(
    df_dag_execution_time_candidate, num_rows=3, log_level=logging.INFO
)

# %%
dtfcore.plot_dag_execution_stats(df_dag_execution_time_prod, report_stats=True)

# %% run_control={"marked": true}
dtfcore.plot_dag_execution_stats(
    df_dag_execution_time_candidate, report_stats=True
)

# %% [markdown]
# # Compare DAG memory consumption

# %%
# TODO(Grisha): create a plotting function that compares the results back-to-back instead
# of visually comparing 2 plots.

# %%
dag_df_out_size_prod = dtfcore.get_dag_df_out_size_for_all_nodes(
    dag_path_dict["prod"]
)
_LOG.info("DAG results df size:")
hpandas.df_to_str(dag_df_out_size_prod, num_rows=5, log_level=logging.INFO)

# %%
dag_df_out_size_candidate = dtfcore.get_dag_df_out_size_for_all_nodes(
    dag_path_dict["candidate"]
)
_LOG.info("DAG results df size:")
hpandas.df_to_str(dag_df_out_size_candidate, num_rows=5, log_level=logging.INFO)

# %%
# Display the results df size distribution over the DAG nodes.
dtfcore.plot_dag_df_out_size_stats(dag_df_out_size_prod, report_stats=False)

# %%
# Display the results df size distribution over the DAG nodes.
dtfcore.plot_dag_df_out_size_stats(dag_df_out_size_candidate, report_stats=False)

# %% [markdown]
# # Compare PnL

# %%
portfolio_dfs, portfolio_stats_dfs = reconcil.load_portfolio_dfs(
    portfolio_path_dict,
    config["bar_duration"],
)
hpandas.df_to_str(portfolio_dfs["prod"], num_rows=5, log_level=logging.INFO)

# %%
portfolio_stats_df = pd.concat(portfolio_stats_dfs, axis=1)
bars_to_burn = 1
coplotti.plot_portfolio_stats(portfolio_stats_df.iloc[bars_to_burn:])
