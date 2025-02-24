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
# The notebook contains checks that compare the prod system output vs that of the prod simulation run ensuring basic sanity.

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
import core.finance.target_position_df_processing as cftpdp
import core.plotting as coplotti
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import oms as oms
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
    start_timestamp_as_str = "20240330_131000"
    end_timestamp_as_str = "20240331_130500"
    run_mode = "paper_trading"
    mode = "scheduled"
    set_config_values = None
    config_list = reconcil.build_reconciliation_configs(
        dst_root_dir,
        dag_builder_ctor_as_str,
        start_timestamp_as_str,
        end_timestamp_as_str,
        run_mode,
        mode,
        set_config_values=set_config_values,
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

# %%
# This dict points to `system_log_dir/process_forecasts/portfolio` for different experiments.
data_type = "portfolio"
portfolio_path_dict = reconcil.get_system_log_paths(
    system_log_path_dict, data_type
)
portfolio_path_dict

# %%
# This dict points to `system_log_dir/process_forecasts/orders` for different experiments.
data_type = "orders"
orders_path_dict = reconcil.get_system_log_paths(system_log_path_dict, data_type)
orders_path_dict

# %%
# TODO(gp): Load the TCA data for crypto.
if config["meta"]["run_tca"]:
    tca_csv = os.path.join(
        root_dir, config["meta"]["date_str"], "tca/sau1_tca.csv"
    )
    hdbg.dassert_file_exists(tca_csv)

# %% [markdown]
# # Configs

# %% [markdown]
# ## Load and display configs

# %%
configs = reconcil.load_config_dict_from_pickle(system_log_path_dict)
# TODO(Dan): Deprecate after switch to updated config logs CmTask6627.
hdbg.dassert_in("dag_runner_config", configs["prod"])
if isinstance(configs["prod"]["dag_runner_config"], tuple):
    # This is a hack to display a config that was made from unpickled dict.
    print(configs["prod"].to_string("only_values").replace("\\n", "\n"))
else:
    print(configs["prod"])

# %%
# TODO(Dan): Deprecate after switch to updated config logs CmTask6627.
hdbg.dassert_in("dag_runner_config", configs["sim"])
if isinstance(configs["sim"]["dag_runner_config"], tuple):
    # This is a hack to display a config that was made from unpickled dict.
    print(configs["sim"].to_string("only_values").replace("\\n", "\n"))
else:
    print(configs["sim"])

# %% [markdown]
# ## Compare configs (prod vs vim)

# %%
# Diff configs.
# TODO(Grisha): the output is only on subconfig level, we should
# compare value vs value instead.
diff_config = cconfig.build_config_diff_dataframe(
    {
        "prod_config": configs["prod"],
        "sim_config": configs["sim"],
    }
)
diff_config.T

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
# Run for the last timestamp only as a sanity check.
bar_timestamp = dag_node_timestamps[-1][0]
dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
    config["dag_builder_ctor_as_str"]
)
if dag_builder_name not in ["C11a", "C12a"]:
    # Self-consistency check fails for C11a. See CmTask6519
    # for more details. Also for C12a, see CmTask7053.
    _LOG.info("Running the DAG self-consistency check for=%s", bar_timestamp)
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
# Run for the last node and the last timestamp only as a sanity check.
bar_timestamp = dag_node_timestamps[-1][0]
node_name = dag_node_names[-1]
_LOG.info(
    "Comparing DAG output for node=%s and bar_timestamp=%s",
    node_name,
    bar_timestamp,
)
_ = dtfcore.compare_dag_outputs(
    dag_path_dict,
    node_name,
    bar_timestamp,
    diff_threshold=diff_threshold,
    **compare_dfs_kwargs,
)

# %%
# TODO(Grisha): Functions do not work currently. Think of another approach to compute stats.
# The functions assumes that it is possible to keep all the DAG output in memory which is
# not always true.
if False:
    dag_diff_df = dtfcore.compute_dag_outputs_diff(
        dag_df_dict, **compare_dfs_kwargs
    )
    dag_diff_detailed_stats = dtfcore.compute_dag_output_diff_detailed_stats(
        dag_diff_df
    )

# %%
if False:
    # Compute correlations.
    prod_sim_dag_corr = dtfmod.compute_correlations(
        dag_df_prod,
        dag_df_sim,
    )
    hpandas.df_to_str(
        prod_sim_dag_corr.min(),
        num_rows=None,
        precision=3,
        log_level=logging.INFO,
    )

# %% [markdown]
# ## Compute DAG execution time

# %%
df_dag_execution_time = dtfcore.get_execution_time_for_all_dag_nodes(dag_path)
_LOG.info("DAG execution time:")
hpandas.df_to_str(df_dag_execution_time, num_rows=5, log_level=logging.INFO)

# %%
dtfcore.plot_dag_execution_stats(df_dag_execution_time, report_stats=True)

# %%
# The time is an approximation of how long it takes to process a bar. Technically the time
# is a distance (in secs) between wall clock time when an order is executed and a bar
# timestamp. The assumption is that order execution is the very last stage.
df_order_execution_time = dtfcore.get_orders_execution_time(
    orders_path_dict["prod"]
)
# TODO(Grisha): consider adding an assertion that checks that the time does not
# exceed one minute.
_LOG.info(
    "Max order execution time=%s secs",
    df_order_execution_time["execution_time"].max(),
)

# %% [markdown]
# # Compute DAG memory consumption

# %%
# Use a results df's size to measure memory consumption.
dag_df_out_size = dtfcore.get_dag_df_out_size_for_all_nodes(dag_path)
_LOG.info("DAG results df size:")
hpandas.df_to_str(dag_df_out_size, num_rows=5, log_level=logging.INFO)

# %%
# Display the results df size distribution over the DAG nodes.
dtfcore.plot_dag_df_out_size_stats(dag_df_out_size, report_stats=False)

# %% [markdown]
# # Portfolio

# %% [markdown]
# ## Compute research portfolio equivalent

# %%
# Set Portofolio start and end timestamps.
if True:
    # By default use the min/max bar timestamps from the DAG.
    start_timestamp = dag_node_timestamps[0][0]
    end_timestamp = dag_node_timestamps[-1][0]
else:
    # Overwrite if needed.
    start_timestamp = pd.Timestamp(
        "2022-11-03 06:05:00-04:00", tz="America/New_York"
    )
    end_timestamp = pd.Timestamp(
        "2022-11-03 08:00:00-04:00", tz="America/New_York"
    )
_LOG.info("start_timestamp=%s", start_timestamp)
_LOG.info("end_timestamp=%s", end_timestamp)

# %%
# Get forecast evaluator.
forecast_evaluator_type = config["forecast_evaluator_config"][
    "forecast_evaluator_type"
]
forecast_evaluator_kwargs = config["forecast_evaluator_config"]["init"]
forecast_evaluator = reconcil.get_forecast_evaluator_instance1(
    forecast_evaluator_type, forecast_evaluator_kwargs
)
#
annotate_forecasts_kwargs = config["forecast_evaluator_config"][
    "annotate_forecasts_kwargs"
].to_dict()
# Get dag data path for research portfolio.
compute_research_portfolio_mode = config["meta"][
    "compute_research_portfolio_mode"
]
computation_dag_path = reconcil.get_dag_output_path(
    dag_path_dict, compute_research_portfolio_mode
)
# Get computation dataframe for research portfolio.
research_portfolio_input_df = dtfcore.load_dag_outputs(
    computation_dag_path, dag_node_names[-1]
)
(
    research_portfolio_df,
    research_portfolio_stats_df,
) = forecast_evaluator.annotate_forecasts(
    research_portfolio_input_df,
    **annotate_forecasts_kwargs,
    compute_extended_stats=True,
)
# TODO(gp): Move it to annotate_forecasts?
research_portfolio_df = research_portfolio_df.sort_index(axis=1)
# Align index with prod and sim portfolios.
research_portfolio_df = research_portfolio_df.loc[start_timestamp:end_timestamp]
research_portfolio_stats_df = research_portfolio_stats_df.loc[
    start_timestamp:end_timestamp
]
#
hpandas.df_to_str(research_portfolio_stats_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Load logged portfolios (prod & sim)

# %%
portfolio_dfs, portfolio_stats_dfs = reconcil.load_portfolio_dfs(
    portfolio_path_dict,
    config["meta"]["bar_duration"],
)
# Add research portfolio.
portfolio_dfs["research"] = research_portfolio_df
hpandas.df_to_str(portfolio_dfs["prod"], num_rows=5, log_level=logging.INFO)

# %%
# Add research df and combine into a single df.
portfolio_stats_dfs["research"] = research_portfolio_stats_df
portfolio_stats_df = pd.concat(portfolio_stats_dfs, axis=1)
#
hpandas.df_to_str(portfolio_stats_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Compute Portfolio statistics (prod vs research vs sim)

# %%
bars_to_burn = config["forecast_evaluator_config"]["annotate_forecasts_kwargs"][
    "burn_in_bars"
]
coplotti.plot_portfolio_stats(portfolio_stats_df.iloc[bars_to_burn:])

# %%
stats_computer = dtfmod.StatsComputer()
stats_sxs, _ = stats_computer.compute_portfolio_stats(
    portfolio_stats_df.iloc[bars_to_burn:], config["meta"]["bar_duration"]
)
display(stats_sxs)

# %% [markdown]
# ## Compare portfolios pairwise (prod vs research vs sim)

# %% [markdown]
# ### Differences

# %% [markdown]
# #### Prod vs sim

# %%
report_stats = False
display_plot = False
compare_dfs_kwargs = {
    "column_mode": "inner",
    "diff_mode": "pct_change",
    "remove_inf": True,
    "assert_diff_threshold": None,
}
portfolio_diff_df = reconcil.compare_portfolios(
    portfolio_dfs,
    report_stats=report_stats,
    display_plot=display_plot,
    **compare_dfs_kwargs,
)
hpandas.df_to_str(portfolio_diff_df, num_rows=None, log_level=logging.INFO)

# %% [markdown]
# ### Correlations

# %% [markdown]
# #### Prod vs sim

# %%
if False:
    dtfmod.compute_correlations(
        portfolio_dfs["prod"],
        portfolio_dfs["sim"],
        allow_unequal_indices=False,
        allow_unequal_columns=False,
    )

# %% [markdown]
# #### Prod vs research

# %%
if False:
    dtfmod.compute_correlations(
        research_portfolio_df,
        portfolio_dfs["prod"],
        allow_unequal_indices=True,
        allow_unequal_columns=True,
    )

# %% [markdown]
# #### Sim vs research

# %%
if False:
    dtfmod.compute_correlations(
        research_portfolio_df,
        portfolio_dfs["sim"],
        allow_unequal_indices=True,
        allow_unequal_columns=True,
    )

# %% [markdown]
# # Target positions

# %% [markdown]
# ## Load target positions (prod)

# %%
prod_target_position_df = reconcil.load_target_positions(
    portfolio_path_dict["prod"].strip("portfolio"),
    config["meta"]["bar_duration"],
)
hpandas.df_to_str(prod_target_position_df, num_rows=5, log_level=logging.INFO)
if False:
    # TODO(Grisha): compare prod vs sim at some point.
    sim_target_position_df = reconcil.load_target_positions(
        portfolio_path_dict["sim"].strip("portfolio"),
        config["meta"]["bar_duration"],
    )

# %% [markdown]
# ## Compare positions target vs executed (prod)

# %%
# TODO(Grisha): use `hpandas.compare_dfs()`.
df1 = prod_target_position_df["target_holdings_shares"].shift(1)
df2 = prod_target_position_df["holdings_shares"]
diff = df1 - df2
hpandas.df_to_str(diff, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Compare target positions (prod vs research)

# %% [markdown]
# ### Price

# %% run_control={"marked": true}
# TODO(Grisha): wrap in a function since it's common for all columns.
column = "price"
prod_df = prod_target_position_df[column]
res_df = research_portfolio_df[column]

# Compute percentage difference.
diff_df = hpandas.compare_dfs(
    prod_df,
    res_df,
    diff_mode="pct_change",
    # Some pipelines (e.g., "C8b") do not use "close" prices to compute
    # "twap" / "vwap". While when computing target positions "close"
    # prices from MarketData are used. Thus the perfect match is not
    # expected.
    assert_diff_threshold=None,
)
# Remove the sign and NaNs.
diff_df = diff_df.abs()
# Check that data is the same.
print(diff_df.max().max())
if False:
    hpandas.heatmap_df(diff_df.round(2))

# %% [markdown]
# ### Volatility

# %%
column = "volatility"
prod_df = prod_target_position_df[column]
res_df = research_portfolio_df[column]

# Compute percentage difference.
diff_df = hpandas.compare_dfs(
    prod_df,
    res_df,
    diff_mode="pct_change",
)
# Remove the sign and NaNs.
diff_df = diff_df.abs()
# Check that data is the same.
print(diff_df.max().max())
if False:
    hpandas.heatmap_df(diff_df.round(2))

# %% [markdown]
# ### Prediction

# %%
column = "prediction"
prod_df = prod_target_position_df[column]
res_df = research_portfolio_df[column]

# Compute percentage difference.
diff_df = hpandas.compare_dfs(
    prod_df,
    res_df,
    diff_mode="pct_change",
)
# Remove the sign and NaNs.
diff_df = diff_df.abs()
# Check that data is the same.
print(diff_df.max().max())
if False:
    hpandas.heatmap_df(diff_df.round(2))

# %% [markdown]
# ### Current holdings

# %%
column = "holdings_shares"
prod_df = prod_target_position_df[column]
res_df = research_portfolio_df[column]

# Compute percentage difference.
diff_df = hpandas.compare_dfs(
    prod_df,
    res_df,
    diff_mode="pct_change",
    assert_diff_threshold=None,
)
# Remove the sign and NaNs.
diff_df = diff_df.abs()
# Check that data is the same.
print(diff_df.max().max())
if False:
    hpandas.heatmap_df(diff_df.round(2))

# %% [markdown]
# ### Target holdings

# %%
prod_df = prod_target_position_df["target_holdings_shares"].shift(1)
res_df = research_portfolio_df["holdings_shares"]

# Compute percentage difference.
diff_df = hpandas.compare_dfs(
    prod_df,
    res_df,
    diff_mode="pct_change",
    assert_diff_threshold=None,
)
# Remove the sign and NaNs.
diff_df = diff_df.abs()
# Check that data is the same.
print(diff_df.max().max())
if False:
    hpandas.heatmap_df(diff_df.round(2))

# %% [markdown]
# # Orders

# %% [markdown]
# ## Load orders (prod & sim)

# %%
prod_order_df = oms.TargetPositionAndOrderGenerator.load_orders(
    portfolio_path_dict["prod"].strip("portfolio"),
)
hpandas.df_to_str(prod_order_df, num_rows=5, log_level=logging.INFO)
sim_order_df = oms.TargetPositionAndOrderGenerator.load_orders(
    portfolio_path_dict["sim"].strip("portfolio"),
)
hpandas.df_to_str(sim_order_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Compare orders (prod vs sim)

# %%
# TODO(Grisha): add comparison using the usual `pct_change` approach.

# %% [markdown]
# # Compute execution quality

# %%
(
    execution_quality_df,
    execution_quality_stats_df,
) = cftpdp.compute_execution_quality_df(
    portfolio_dfs["prod"],
    prod_target_position_df,
)
hpandas.df_to_str(execution_quality_df, num_rows=5, log_level=logging.INFO)
hpandas.df_to_str(execution_quality_stats_df, num_rows=5, log_level=logging.INFO)

# %%
coplotti.plot_execution_stats(execution_quality_stats_df)

# %%
coplotti.plot_execution_ecdfs(execution_quality_df)
