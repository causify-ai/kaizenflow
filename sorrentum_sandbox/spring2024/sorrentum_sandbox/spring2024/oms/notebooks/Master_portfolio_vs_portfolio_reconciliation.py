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

import core.config as cconfig
import core.finance.portfolio_df_processing as cofinpdp
import core.plotting as coplotti
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

# %%
date = "2022-08-31"
start_timestamp = pd.Timestamp(date + " 10:15:00", tz="America/New_York")
_LOG.info("start_timestamp=%s", start_timestamp)
end_timestamp = pd.Timestamp(date + " 15:45:00", tz="America/New_York")
_LOG.info("end_timestamp=%s", start_timestamp)

# %%
# !ls /data/cf_production/20220915/job.1002440809/job-sasm_job-jobid-1002440809/user_executable_run_0-1000005405809/cf_prod_system_log_dir/process_forecasts

# %%
# /share/data/cf_production/20220919/job.1002450215/job-sasm_job-jobid-1002450215/user_executable_run_0-1000005484302/cf_prod_system_log_dir
# /share/data/cf_production/20220919/job.1002452903/user_executable_run_0-1000005489454/cf_prod_system_log_dir
prod_dir = (
    # "/share/data/cf_production/20220919/job.1002450215/job-sasm_job-jobid-1002450215/user_executable_run_0-1000005484302/cf_prod_system_log_dir"
    "/share/data/cf_production/20220919/job.1002452903/user_executable_run_0-1000005489454/cf_prod_system_log_dir"
)
prod_dir = prod_dir.replace("/share/data/", "/data/")
prod_portfolio_dir = os.path.join(prod_dir, "process_forecasts/portfolio")
prod_forecast_dir = os.path.join(prod_dir, "process_forecasts")
hdbg.dassert_dir_exists(prod_forecast_dir)

sim_dir = "/app/system_log_dir"
sim_portfolio_dir = os.path.join(sim_dir, "process_forecasts/portfolio")
sim_forecast_dir = os.path.join(sim_dir, "process_forecasts")
hdbg.dassert_dir_exists(sim_forecast_dir)

# %%
# hdbg.dassert_dir_exists(root_dir)
dict_ = {
    "prod_forecast_dir": prod_forecast_dir,
    "sim_forecast_dir": sim_forecast_dir,
    "prod_portfolio_dir": prod_portfolio_dir,
    "sim_portfolio_dir": sim_portfolio_dir,
    "freq": "15T",
    "start_timestamp": start_timestamp,
    "end_timestamp": end_timestamp,
}
#
config = cconfig.Config.from_dict(dict_)
display(config)


# %% [markdown]
# # Forecasts

# %% [markdown]
# ## Load prod and sim forecasts

# %%
prod_forecast_df = oms.ForecastProcessor.read_logged_target_positions(
    config["prod_forecast_dir"]
)
hpandas.df_to_str(prod_forecast_df, log_level=logging.INFO)

# %%
sim_forecast_df = oms.ForecastProcessor.read_logged_target_positions(
    config["sim_forecast_dir"]
)
hpandas.df_to_str(sim_forecast_df, log_level=logging.INFO)

# %% [markdown]
# ## Compute forecast prod delay

# %%
prod_forecast_delay = reconcil.compute_delay(prod_forecast_df, config["freq"])
hpandas.df_to_str(prod_forecast_delay, log_level=logging.INFO)

# %%
prod_forecast_delay.plot()

# %%
prod_forecast_df.index = prod_forecast_df.index.round(config["freq"])
sim_forecast_df.index = sim_forecast_df.index.round(config["freq"])
prod_forecast_df = prod_forecast_df.loc[start_timestamp:end_timestamp]
sim_forecast_df = sim_forecast_df.loc[start_timestamp:end_timestamp]

# %% [markdown]
# ## Compare forecast dataframes

# %%
forecast_corrs = dtfmod.compute_correlations(prod_forecast_df, sim_forecast_df)
hpandas.df_to_str(forecast_corrs, precision=3, log_level=logging.INFO)

# %%
sort_col = "prediction"
hpandas.df_to_str(
    forecast_corrs.sort_values(sort_col, ascending=False),
    num_rows=10,
    precision=3,
    log_level=logging.INFO,
)

# %% [markdown]
# # Orders

# %% [markdown]
# ## Load prod and sim orders

# %%
prod_order_df = oms.ForecastProcessor.read_logged_orders(
    config["prod_forecast_dir"]
)
hpandas.df_to_str(prod_order_df, log_level=logging.INFO)

# %%
sim_order_df = oms.ForecastProcessor.read_logged_orders(
    config["sim_forecast_dir"]
)
hpandas.df_to_str(sim_order_df, log_level=logging.INFO)

# %% [markdown]
# # Portfolios

# %% [markdown]
# ## Load prod portfolio

# %%
prod_portfolio_df, prod_portfolio_stats_df = reconcil.load_portfolio_artifacts(
    config["prod_portfolio_dir"],
    config["start_timestamp"],
    config["end_timestamp"],
    config["freq"],
    normalize_bar_times=False,
)

# %%
hpandas.df_to_str(prod_portfolio_df, log_level=logging.INFO)

# %%
hpandas.df_to_str(prod_portfolio_stats_df, log_level=logging.INFO)

# %% [markdown]
# ## Load sim portfolio

# %%
sim_portfolio_df, sim_portfolio_stats_df = reconcil.load_portfolio_artifacts(
    config["sim_portfolio_dir"],
    config["start_timestamp"],
    config["end_timestamp"],
    config["freq"],
    normalize_bar_times=False,
)

# %%
hpandas.df_to_str(sim_portfolio_df, log_level=logging.INFO)

# %%
hpandas.df_to_str(sim_portfolio_stats_df, log_level=logging.INFO)

# %% [markdown]
# ## Compute prod portfolio delay

# %%
prod_portfolio_delay = reconcil.compute_delay(prod_portfolio_df, config["freq"])

# %%
hpandas.df_to_str(prod_portfolio_delay, log_level=logging.INFO)

# %%
prod_portfolio_delay.plot()

# %%
_LOG.info("prod portfolio delay mean=%s", prod_portfolio_delay.mean())
_LOG.info("prod portfolio delay std=%s", prod_portfolio_delay.std())

# %% [markdown]
# ## Normalize bar times

# %%
dfs = [
    prod_portfolio_df,
    prod_portfolio_stats_df,
    sim_portfolio_df,
    sim_portfolio_stats_df,
]

# %%
for df in dfs:
    df.index = df.index.round(config["freq"])

# %% [markdown]
# ## Compare portfolio stats

# %%
portfolio_stats_dfs = {
    "prod": prod_portfolio_stats_df,
    "sim": sim_portfolio_stats_df,
}
portfolio_stats_dfs = pd.concat(portfolio_stats_dfs, axis=1)

# %%
hpandas.df_to_str(portfolio_stats_dfs, log_level=logging.INFO)

# %%
coplotti.plot_portfolio_stats(portfolio_stats_dfs)

# %%
portfolio_stats_corrs = dtfmod.compute_correlations(
    prod_portfolio_stats_df, sim_portfolio_stats_df
)
display(portfolio_stats_corrs.round(3))

# %%
stats_computer = dtfmod.StatsComputer()
stats_sxs, _ = stats_computer.compute_portfolio_stats(
    portfolio_stats_dfs, config["freq"]
)
display(stats_sxs)

# %% [markdown]
# ## Compare portfolios at the instrument level

# %%
portfolio_corrs = dtfmod.compute_correlations(prod_portfolio_df, sim_portfolio_df)
hpandas.df_to_str(portfolio_corrs, precision=3, log_level=logging.INFO)

# %%
sort_col = "pnl"
hpandas.df_to_str(
    portfolio_corrs.sort_values(sort_col, ascending=False),
    num_rows=10,
    precision=3,
    log_level=logging.INFO,
)

# %%
# OMS

# %%
shares_df = cofinpdp.compute_shares_traded(
    prod_portfolio_df, prod_order_df, "15T"
)

# %%
shares_df.columns.levels[0]

# %%
# shares_df["estimated_price_per_share"]
# shares_df["underfill"] / shares_df["order_share_target_as_int"]
shares_df["order_share_target_as_int"]


# %% [markdown]
# # System configs

# %%
# TODO(Paul): Clean up the system config handling.
def load_config_as_list(path):
    with open(path) as f:
        lines = f.readlines()
    _LOG.debug("Lines read=%d", len(lines))
    return lines


# %%
def diff_lines(list1, list2) -> Tuple[List[str], List[str]]:
    list1_only = list(set(list1) - set(list2))
    list2_only = list(set(list2) - set(list1))
    return list1_only, list2_only


# %%
prod_system_config_output = load_config_as_list(
    prod_dir + "/system_config.output.txt"
)
sim_system_config_output = load_config_as_list(
    sim_dir + "/system_config.output.txt"
)
prod_system_config_input = load_config_as_list(
    prod_dir + "/system_config.input.txt"
)
sim_system_config_input = load_config_as_list(
    sim_dir + "/system_config.input.txt"
)

# %%
prod_output_only, sim_output_only = diff_lines(
    prod_system_config_output, sim_system_config_output
)

# %%
# prod_output_only

# %%
# sim_output_only
