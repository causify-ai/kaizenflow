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
# Given the output of the production / simulation DAG
# - compute the research PnL / output with the ForecastEvaluator from DAG
# - compare production portfolio PnL / output

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging
import os

import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import dataflow.model as dtfmod
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

# %%
# find /share/data/cf_production/CF_2022_09_08 -name "cf_prod_system_log_dir" -type d
# /share/data/cf_production/CF_2022_09_08/job-sasm_job-jobid-1002410338/user_executable_run_0-1000005273093/cf_prod_system_log_dir

root_dir = (
    # "/data/tmp/AmpTask2534_Prod_reconciliation_20220901/system_log_dir.prod"
    "/data/cf_production/20220914/job.1002436966/job-sasm_job-jobid-1002436966/user_executable_run_0-1000005393900/cf_prod_system_log_dir"
)
# root_dir = "/app/system_log_dir"

# %%
date = "2022-09-14"
start_timestamp = pd.Timestamp(date + " 10:15:00", tz="America/New_York")
_LOG.info("start_timestamp=%s", start_timestamp)
end_timestamp = pd.Timestamp(date + " 15:45:00", tz="America/New_York")
_LOG.info("end_timestamp=%s", start_timestamp)

# %%
# hdbg.dassert_dir_exists(root_dir)
dict_ = {
    "freq": "15T",
    "start_timestamp": start_timestamp,
    "end_timestamp": end_timestamp,
}
#
config = cconfig.Config.from_dict(dict_)
display(config)

# %%

# %% [markdown]
# # Load DAG IO

# %%
config_file_name = f"{root_dir}/system_config.output.txt"
print(config_file_name)
# !cat {config_file_name}

# %%
dag_dir = os.path.join(root_dir, "dag/node_io/node_io.data")
print(dag_dir)
hdbg.dassert_dir_exists(dag_dir)

# %%
stage = "0.read_data"
target_cols = [
    "ask",
    "bid",
    "close",
    "day_num_spread",
    "day_spread",
    "high",
    "low",
    "notional",
    "open",
    "sided_ask_count",
    "sided_bid_count",
    "start_time",
    "volume",
]
# stage = "2.zscore"
stage = "7.process_forecasts"
target_cols = [
    "close",
    "close_vwap",
    "day_num_spread",
    "day_spread",
    "garman_klass_vol",
    "high",
    "low",
    "notional",
    "open",
    "prediction",
    "twap",
    "volume",
]
timestamp = "20220914_154500"

file_name = f"predict.{stage}.df_out.{timestamp}.csv"
file_name = os.path.join(dag_dir, file_name)
print(file_name)
dag_df = pd.read_csv(file_name, parse_dates=True, index_col=0, header=[0, 1])

# dag_df = dag_df[start_timestamp:end_timestamp]

display(dag_df.head(3))

# print(dag_df.columns.levels[0])
# print(sim_dag_df.columns.levels[0])
# dag_df.drop(labels=["end_time"], axis=1, level=0, inplace=True, errors="raise")
asset_ids = dag_df.columns.levels[1].tolist()
# for col in dag_df.columns:
#     if col[0] in target_cols:
#     columns.append()
import itertools

columns = list(itertools.product(target_cols, asset_ids))
dag_df = dag_df[pd.MultiIndex.from_tuples(columns)].copy()
hpandas.df_to_str(dag_df, log_level=logging.INFO)
dag_df.to_csv("prod_tmp.csv")
dag_df = pd.read_csv("prod_tmp.csv", index_col=0, header=[0, 1])

asset_ids = map(int, asset_ids)
columns = list(itertools.product(target_cols, asset_ids))
columns = pd.MultiIndex.from_tuples(columns)
dag_df.columns = columns

dag_df.index = pd.to_datetime(dag_df.index)
dag_df.index = dag_df.index.tz_convert("America/New_York")


# %%
display(dag_df)

# %% [markdown]
# # Run ForecastEvaluator (vectorized research flow)

# %%
# From process_forecasts_dict
#   process_forecasts_dict:
#     order_config:
#       order_type: price@twap
#       order_duration_in_mins: 15
#     optimizer_config:
#       backend: pomo
#       params:
#         style: cross_sectional
#         kwargs:
#           bulk_frac_to_remove: 0.0
#           target_gmv: 20000.0

# From process_forecasts_node_dict
#   prediction_col: prediction
#  volatility_col: garman_klass_vol

fep_dict = {
    "price_col": "close_vwap",
    "prediction_col": "prediction",
    "volatility_col": "garman_klass_vol",
    #
    "quantization": 0,
    "burn_in_bars": 3,
    #
    "style": "cross_sectional",
    "bulk_frac_to_remove": 0.0,
    "target_gmv": 20000.0,
}
fep_config = cconfig.Config.from_dict(fep_dict)

# %%
fep = dtfmod.ForecastEvaluatorFromPrices(
    fep_config["price_col"],
    fep_config["volatility_col"],
    fep_config["prediction_col"],
)

# %%
research_portfolio_df, research_portfolio_stats_df = fep.annotate_forecasts(
    dag_df,
    # bulk_frac_to_remove=fep_config["bulk_frac_to_remove"],
    # bulk_fill_method=fep_config["bulk_fill_method"],
    target_gmv=fep_config["target_gmv"],
    quantization=fep_config["quantization"],
    burn_in_bars=fep_config["burn_in_bars"],
    style=fep_config["style"],
)
# bar_metrics.append(bar_metrics_slice)

# %%
research_portfolio_stats_df["pnl"].cumsum().plot()

# %%
research_portfolio_df = research_portfolio_df.loc[start_timestamp:end_timestamp]
research_portfolio_stats_df = research_portfolio_stats_df.loc[
    start_timestamp:end_timestamp
]

# %% [markdown]
# # Load prod portfolio

# %%
prod_portfolio_dir = os.path.join(root_dir, "process_forecasts/portfolio")

# %%
prod_portfolio_df, prod_portfolio_stats_df = reconcil.load_portfolio_artifacts(
    prod_portfolio_dir,
    start_timestamp,
    end_timestamp,
    "15T",
    normalize_bar_times=True,
)

# %%
# hpandas.df_to_str(prod_portfolio_df, log_level=logging.INFO)

# %%
hpandas.df_to_str(prod_portfolio_stats_df, log_level=logging.INFO)

# %% [markdown]
# # Compare prod and research stats

# %%
portfolio_stats_dfs = {
    "research": research_portfolio_stats_df,
    "prod": prod_portfolio_stats_df,
}
portfolio_stats_dfs = pd.concat(portfolio_stats_dfs, axis=1)

# %%
hpandas.df_to_str(portfolio_stats_dfs, log_level=logging.INFO)

# %%
coplotti.plot_portfolio_stats(portfolio_stats_dfs)

# %%
cols = research_portfolio_stats_df.columns
portfolio_stats_corrs = dtfmod.compute_correlations(
    # TODO: Don't hardcode the tail trimming.
    prod_portfolio_stats_df[cols],
    research_portfolio_stats_df,
)
display(portfolio_stats_corrs.round(3))

# %% [markdown]
# # Compare prod and research portfolios (asset granularity)

# %%
prod_portfolio_df.columns.levels[0]

# %%
prod_portfolio_df.columns.levels[1]

# %%
research_portfolio_df.columns.levels[0]


# %%
normalized_research_portfolio_df = dtfmod.normalize_portfolio_df(
    research_portfolio_df
)

# %%
normalized_prod_portfolio_df = reconcil.normalize_portfolio_df(prod_portfolio_df)

# %%
portfolio_corrs = dtfmod.compute_correlations(
    normalized_prod_portfolio_df,
    normalized_research_portfolio_df,
)
display(portfolio_corrs.round(3))

# %%
