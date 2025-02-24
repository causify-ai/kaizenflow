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
# The notebooks loads replayed time simulation results, computes research portfolio and computes portfolio-level stats.

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %% [markdown]
# # Imports

# %%
# TODO(Grisha): Unclear if this should be a separate notebook,
# because most of the code is a copy-paste from the
# `Master_system_reconciliation_fast.py`.
import logging
import os

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
import oms.broker.ccxt.ccxt_utils as obccccut
import optimizer.forecast_evaluator_with_optimizer as ofevwiop
import reconciliation as reconcil

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Sim Config

# %%
# TODO(Grisha): Can we re-use `build_reconciliation_configs()` to automate the config construction?
system_log_dir = "/shared_data/Samarth/CmTask7253_Run_sim_with_the_optimizer/C12a/simulation/20240228_190000.20240305_19000/system_log_dir/"
system_log_path_dict = {"sim": system_log_dir}
configs = reconcil.load_config_dict_from_pickle(system_log_path_dict)
# TODO(Dan): Deprecate after switch to updated config logs CmTask6627.
hdbg.dassert_in("dag_runner_config", configs["sim"])
if isinstance(configs["sim"]["dag_runner_config"], tuple):
    # This is a hack to display a config that was made from unpickled dict.
    print(configs["sim"].to_string("only_values").replace("\\n", "\n"))
else:
    print(configs["sim"])

# %% [markdown]
# # Build config

# %%
dag_data_dir = reconcil.get_data_type_system_log_path(system_log_dir, "dag_data")
portfolio_dir = reconcil.get_data_type_system_log_path(
    system_log_dir, "portfolio"
)
# Load pickled SystemConfig.
config_file_name = "system_config.output.values_as_strings.pkl"
system_config_path = os.path.join(system_log_dir, config_file_name)
system_config = cconfig.load_config_from_pickle(system_config_path)
# Get bar duration.
bar_duration_in_secs = reconcil.get_bar_duration_from_config(system_config)
bar_duration = hdateti.convert_seconds_to_pandas_minutes(bar_duration_in_secs)
# %%
dag_builder_ctor_as_str = (
    "dataflow_lemonade.pipelines.C12.C12a_pipeline.C12a_DagBuilder"
)
dag_builder = dtfcore.get_DagBuilder_from_string(dag_builder_ctor_as_str)
# Get column names from `DagBuilder`.
price_col = dag_builder.get_column_name("price")
prediction_col = dag_builder.get_column_name("prediction")
volatility_col = dag_builder.get_column_name("volatility")
# Get `asset_id_to_share_decimals` from market info.
market_info = obccccut.load_market_data_info()
asset_id_to_share_decimals = obccccut.subset_market_info(
    market_info, "amount_precision"
)

# %%
config_dict = {
    "pnl_freq": "H",
    "bar_duration": bar_duration,
    "dag_path_dict": {
        "prod": "",
        "sim": dag_data_dir,
    },
    "portfolio_path_dict": {
        "sim": portfolio_dir,
    },
    "compute_research_portfolio_mode": "sim",
    "research_forecast_evaluator_config": {
        "init": {
            "price_col": price_col,
            "prediction_col": prediction_col,
            "volatility_col": volatility_col,
            # TODO(Grisha): consider extracting sim optimizer_config from SystemConfig if needed.
            "optimizer_config_dict": {
                "dollar_neutrality_penalty": 0.0,
                "constant_correlation": 0.85,
                "constant_correlation_penalty": 1.0,
                "relative_holding_penalty": 0.0,
                "relative_holding_max_frac_of_gmv": 0.6,
                "target_gmv": 1500.0,
                "target_gmv_upper_bound_penalty": 0.0,
                "target_gmv_hard_upper_bound_multiple": 1.0,
                "transaction_cost_penalty": 0.1,
                "solver": "ECOS",
                "verbose": False,
            },
        },
        "annotate_forecasts_kwargs": {
            "quantization": None,
            "liquidate_at_end_of_day": False,
            "initialize_beginning_of_day_trades_to_zero": False,
            "burn_in_bars": 3,
            "asset_id_to_share_decimals": asset_id_to_share_decimals,
        },
    },
}
config = cconfig.Config().from_dict(config_dict)
print(config)

# %% [markdown]
# # Load Portfolio

# %%
portfolio_dfs, portfolio_stats_dfs = reconcil.load_portfolio_dfs(
    config["portfolio_path_dict"].to_dict(),
    config["bar_duration"],
)
hpandas.df_to_str(portfolio_dfs["sim"], num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Calculate research Portfolio

# %%
fep = ofevwiop.ForecastEvaluatorWithOptimizer(
    **config["research_forecast_evaluator_config"]["init"]
)
annotate_forecasts_kwargs = config["research_forecast_evaluator_config"][
    "annotate_forecasts_kwargs"
].to_dict()
# Get dag data path for research portfolio.
compute_research_portfolio_mode = config["compute_research_portfolio_mode"]
computation_dag_path = reconcil.get_dag_output_path(
    config["dag_path_dict"], compute_research_portfolio_mode
)
# Get computation dataframe for research portfolio.
research_portfolio_input_df = dtfcore.load_dag_outputs(
    computation_dag_path, "predict.7.process_forecasts"
)
research_portfolio_df, research_portfolio_stats_df = fep.annotate_forecasts(
    research_portfolio_input_df,
    **annotate_forecasts_kwargs,
    compute_extended_stats=True,
)
# TODO(Grisha): this is a hack, ideally we should use `close` price
# to compute `holdings_notional` but `open` price to compute `executed_trades_notional`
# shifting the df to make the research PnL look similar to the sim one. See CmTask6902.
research_portfolio_stats_df = research_portfolio_stats_df.shift(-1)
#
hpandas.df_to_str(research_portfolio_stats_df, num_rows=5, log_level=logging.INFO)

# %%
# Add research df and combine into a single df.
portfolio_stats_dfs["research"] = research_portfolio_stats_df
portfolio_stats_df = pd.concat(portfolio_stats_dfs, axis=1)
#
hpandas.df_to_str(portfolio_stats_df, num_rows=5, log_level=logging.INFO)

# %% [markdown]
# ## Plot stats

# %%
bars_to_burn = config["research_forecast_evaluator_config"][
    "annotate_forecasts_kwargs"
]["burn_in_bars"]
coplotti.plot_portfolio_stats(
    portfolio_stats_df.iloc[bars_to_burn:], freq=config["pnl_freq"]
)

# %%
stats_computer = dtfmod.StatsComputer()
stats_sxs, _ = stats_computer.compute_portfolio_stats(
    portfolio_stats_df.iloc[bars_to_burn:], config["bar_duration"]
)
display(stats_sxs)

# %%
