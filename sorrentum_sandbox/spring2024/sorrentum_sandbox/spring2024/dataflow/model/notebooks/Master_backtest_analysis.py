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
# Display the backtest results as the output of the `ForecastEvaluator`, created in `Master_research_backtest_analyzer` notebook.
#
# The user provides a list of the outputs of the 2nd stage of the backtest, and the notebook displays the portfolio stats for the provided runs.

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
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build the config dict

# %%
# Get config from env when running the notebook via the `run_notebook.py` script.
default_config = cconfig.get_config_from_env()
if default_config:
    _LOG.info("Using config from env vars")
else:
    _LOG.info("Using hardwired config")
    default_config_dict = {
        # Provide a list of experiment output dirs for analysis.
        "system_log_dirs": [
"/shared_data/backtest.danya/build_tile_configs.C11a.ccxt_v8_1-all.5T.2023-08-01_2024-03-31.ins.run0/portfolio_dfs/20240501_183113/forecast_evaluator_kwargs:optimizer_config_dict:transaction_cost_penalty=1.4",
"/shared_data/backtest.danya/build_tile_configs.C11a.ccxt_v8_1-all.5T.2023-08-01_2024-03-31.ins.run0/portfolio_dfs/20240501_183113/forecast_evaluator_kwargs:optimizer_config_dict:transaction_cost_penalty=1.6",
"/shared_data/backtest.danya/build_tile_configs.C11a.ccxt_v8_1-all.5T.2023-08-01_2024-03-31.ins.run0/portfolio_dfs/20240501_183113/forecast_evaluator_kwargs:optimizer_config_dict:transaction_cost_penalty=1.8",
        ],
        "pnl_resampling_frequency": "D",
    }
    # Build config from dict.
    default_config = cconfig.Config().from_dict(default_config_dict)
print(default_config)

# %% [markdown]
# # Load portfolio metrics

# %%
# Load the portfolio metrics.
bar_metrics_dict = {}
for index, system_log_dir in enumerate(default_config["system_log_dirs"]):
    bar_metrics = dtfmod.AbstractForecastEvaluator.load_portfolio_stats(system_log_dir)
    bar_metrics_dict[index] = bar_metrics
portfolio_stats_df = pd.concat(bar_metrics_dict, axis=1)

# %% [markdown]
# # Portfolio stats

# %%
coplotti.plot_portfolio_stats(
    portfolio_stats_df, freq=default_config["pnl_resampling_frequency"]
)

# %% [markdown]
# # Aggregate portfolio stats

# %%
stats_computer = dtfmod.StatsComputer()

# %%
portfolio_stats, daily_metrics = stats_computer.compute_portfolio_stats(
    portfolio_stats_df,
    default_config["pnl_resampling_frequency"],
)
display(portfolio_stats)

# %%
