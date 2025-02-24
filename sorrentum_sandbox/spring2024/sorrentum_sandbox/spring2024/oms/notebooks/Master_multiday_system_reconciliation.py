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
# The notebook stitches together portfolios for multiple daily prod system runs and plots the resulting PnL curves.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %%
import logging
from typing import Any, Dict, Tuple

import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import reconciliation.sim_prod_reconciliation as rsiprrec

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build config

# %%
# Get config from env when running the notebook via the `run_notebook.py`
# script, e.g., in the system reconciliation flow.
config = cconfig.get_config_from_env()
if config:
    _LOG.info("Using config from env vars")
else:
    _LOG.info("Using hardwired config")
    # Specify the config directly when running the notebook manually.
    # Below is just an example.
    dst_root_dir = "/shared_data/ecs/preprod/prod_reconciliation"
    dag_builder_ctor_as_str = (
        "dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp"
    )
    run_mode = "paper_trading"
    start_timestamp_as_str = "20230716_000000"
    end_timestamp_as_str = "20230723_000000"
    config = rsiprrec.build_multiday_system_reconciliation_config(
        dst_root_dir,
        dag_builder_ctor_as_str,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
    )
    config = config[0]
print(config)


# %% [markdown]
# # Functions

# %%
# TODO(Grisha): move all functions under `reconciliation/sim_prod_reconciliation.py`.


# %%
# TODO(Grisha): can we use this idiom in the other system reconciliation
# # notebooks?
def get_prod_dag_output_for_last_node(
    system_log_path_dict: Dict[str, str],
) -> pd.DataFrame:
    """
    Load DAG data for a specified node for all bar timestamps.

    :param system_log_path_dict: system log dirs paths for different
        experiments
    """
    data_type = "dag_data"
    dag_path_dict = rsiprrec.get_system_log_paths(system_log_path_dict, data_type)
    hdbg.dassert_in("prod", dag_path_dict.keys())
    hdbg.dassert_path_exists(dag_path_dict["prod"])
    # Get DAG node names.
    dag_node_names = dtfcore.get_dag_node_names(dag_path_dict["prod"])
    # Get DAG output for the last node and the last timestamp.
    dag_df_prod = dtfcore.load_dag_outputs(
        dag_path_dict["prod"], dag_node_names[-1]
    )
    return dag_df_prod


def compute_research_portfolio(
    dag_df_prod: pd.DataFrame,
    forecast_evaluator_from_prices_dict: Dict[str, Dict[str, Any]],
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute research portfolio and align the indices with the system run start
    and end timestamps.

    :param system_log_path_dict: system log dirs paths for different experiments, e.g.,
        ```
        {
            "prod": "/shared_data/system_log_dir",
            "sim": ...
        }
        ```
    :param forecast_evaluator_from_prices_dict: params to initialize
        `ForecastEvaluatorFromPrices`
    """
    fep = dtfmod.ForecastEvaluatorFromPrices(
        **forecast_evaluator_from_prices_dict["init"]
    )
    annotate_forecasts_kwargs = forecast_evaluator_from_prices_dict[
        "annotate_forecasts_kwargs"
    ].to_dict()
    research_portfolio_df, research_portfolio_stats_df = fep.annotate_forecasts(
        dag_df_prod,
        **annotate_forecasts_kwargs,
    )
    # TODO(Grisha): remove columns sorting if it is not needed.
    research_portfolio_df = research_portfolio_df.sort_index(axis=1)
    research_portfolio_stats_df = research_portfolio_stats_df.sort_index(axis=1)
    # Align index with prod and sim portfolios.
    # TODO(Grisha): remove timestamps filtering if it is not needed.
    research_portfolio_df = research_portfolio_df.loc[
        start_timestamp:end_timestamp
    ]
    research_portfolio_stats_df = research_portfolio_stats_df.loc[
        start_timestamp:end_timestamp
    ]
    return research_portfolio_df, research_portfolio_stats_df


# %% [markdown]
# # Load portfolio stats

# %%
system_run_params = rsiprrec.get_system_run_parameters(
    config["dst_root_dir"],
    config["dag_builder_name"],
    config["run_mode"],
    config["start_timestamp"],
    config["end_timestamp"],
)
system_run_params

# %%
portfolio_stats = []
bar_duration = None
for start_timestamp_as_str, end_timestamp_as_str, mode in system_run_params:
    # Build system reconciliation config.
    config_list = rsiprrec.build_reconciliation_configs(
        config["dst_root_dir"],
        config["dag_builder_ctor_as_str"],
        start_timestamp_as_str,
        end_timestamp_as_str,
        config["run_mode"],
        mode,
    )
    reconciliation_config = config_list[0]
    system_log_path_dict = reconciliation_config["system_log_path"].to_dict()
    bar_duration = reconciliation_config["meta"]["bar_duration"]
    # Load prod and sim portfolios.
    data_type = "portfolio"
    portfolio_path_dict = rsiprrec.get_system_log_paths(
        system_log_path_dict, data_type
    )
    portfolio_dfs, portfolio_stats_dfs = rsiprrec.load_portfolio_dfs(
        portfolio_path_dict,
        bar_duration,
    )
    # Compute research portfolio.
    dag_df_prod = get_prod_dag_output_for_last_node(system_log_path_dict)
    # We add timezone info to `start_timestamp_as_str` and `end_timestamp_as_str`
    # because they are passed in the "UTC" timezone.
    tz = "UTC"
    datetime_format = "%Y%m%d_%H%M%S"
    start_timestamp = hdateti.str_to_timestamp(
        start_timestamp_as_str, tz, datetime_format=datetime_format
    )
    end_timestamp = hdateti.str_to_timestamp(
        end_timestamp_as_str, tz, datetime_format=datetime_format
    )
    # Convert timestamps to a timezone in which prod Portfolio was computed.
    # TODO(Grisha): pass timezone via config instead of setting it manually.
    tz = "America/New_York"
    start_timestamp = start_timestamp.tz_convert(tz)
    end_timestamp = end_timestamp.tz_convert(tz)
    forecast_evaluator_from_prices_dict = reconciliation_config[
        "research_forecast_evaluator_from_prices"
    ]
    (
        research_portfolio_df,
        research_portfolio_stats_df,
    ) = compute_research_portfolio(
        dag_df_prod,
        forecast_evaluator_from_prices_dict,
        start_timestamp,
        end_timestamp,
    )
    # Concatenate prod, sim and research portfolios.
    portfolio_stats_dfs["research"] = research_portfolio_stats_df
    portfolio_stats_df = pd.concat(portfolio_stats_dfs, axis=1)
    portfolio_stats.append(portfolio_stats_df)
# Concatenate multiple daily portfolios.
portfolio_stats_df = pd.concat(portfolio_stats, axis=0)
hpandas.df_to_str(portfolio_stats_df, num_rows=5, log_level=logging.INFO)

# %%
bars_to_burn = 1
coplotti.plot_portfolio_stats(
    portfolio_stats_df.iloc[bars_to_burn:],
    freq=config["pnl_resampling_frequency"],
)

# %%
stats_computer = dtfmod.StatsComputer()
stats_sxs, _ = stats_computer.compute_portfolio_stats(
    portfolio_stats_df.iloc[bars_to_burn:], bar_duration
)
display(stats_sxs)

# %%
# Correlate PnLs.
portfolio_stats_df[[("prod", "pnl"), ("sim", "pnl"), ("research", "pnl")]].corr()
