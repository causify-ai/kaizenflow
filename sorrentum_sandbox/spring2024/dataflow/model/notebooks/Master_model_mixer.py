# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import datetime
import logging

import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import dataflow.core as dtfcore
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
# # Config

# %%
# TODO(Grisha): infer dag_builder_names (e.g., "C3a") automatically
# from `dag_builder_ctors`.
config = {
    "tiled_results_paths": {
        "C1b": "/shared_data/model/historical/build_tile_configs.C1b.ccxt_v7_1-all.5T.2022-01-01_2023-01-01.run0_rolling/tiled_results",
        "C3a": "/shared_data/model/historical/build_tile_configs.C3a.ccxt_v7_1-all.5T.2019-09-01_2023-02-01.run0_ins/tiled_results",
        "C8b": "/shared_data/model/historical/build_tile_configs.C8b.ccxt_v7_1-all.5T.2019-09-01_2023-02-01.run0_ins/tiled_results",
    },
    "dag_builder_ctors_as_str": {
        "C1b": "dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder",
        "C3a": "dataflow_orange.pipelines.C3.C3a_pipeline_tmp.C3a_DagBuilder_tmp",
        "C8b": "dataflow_orange.pipelines.C8.C8b_pipeline_tmp.C8b_DagBuilder_tmp",
    },
    "market_data_and_volatilty_dag_builder_name": "C3a",
    "infer_column_names_from_dag_builder": True,
    "column_tags": ["price", "volatility", "prediction"],
    "start_date": datetime.date(2022, 1, 1),
    "end_date": datetime.date(2022, 12, 31),
    "asset_id_col": "asset_id",
    "asset_ids": None,
    "freq": "D",
    "index_mode": "leave_unchanged",
    "annotate_forecasts_kwargs": {
        "quantization": 0,
        "burn_in_bars": 3,
        "style": "longitudinal",
        "initialize_beginning_of_day_trades_to_zero": False,
        "liquidate_at_end_of_day": False,
    },
}
# Specify the column names.
config["column_names"] = {}
if config["infer_column_names_from_dag_builder"]:
    # Infer column names from a `DagBuilder` object.
    for dag_builder_name, dag_builder_ctor_as_str in config[
        "dag_builder_ctors_as_str"
    ].items():
        dag_builder = dtfcore.get_DagBuilder_from_string(dag_builder_ctor_as_str)
        config["column_names"][
            dag_builder_name
        ] = dag_builder.get_column_names_dict(config["column_tags"])
else:
    # Set column names manually. See an example below.
    model_1_column_names = [
        "vwap",
        "vwap.ret_0.vol",
        "vwap.ret_0.vol_adj.shift_-2_hat",
    ]
    model_2_column_names = ["vwap", "garman_klass_vol", "feature"]
    model_3_column_names = ["vwap", "garman_klass_vol", "feature"]
    config["column_names"]["C1b"] = dict(
        zip(config["column_tags"], model_1_column_names)
    )
    config["column_names"]["C3a"] = dict(
        zip(config["column_tags"], model_2_column_names)
    )
    config["column_names"]["C8b"] = dict(
        zip(config["column_tags"], model_3_column_names)
    )
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Initialize metadata and weights

# %%
# TODO(Grisha): @Dan Move to lib.
# Initialize dataframe pointing to the simulations.
res_dict = {}
res_dict["tiled_results_paths"] = config["tiled_results_paths"].to_dict()
res_dict["column_names"] = {}
for dag_builder_name, column_names in config["column_names"].to_dict().items():
    res_dict["column_names"][dag_builder_name] = column_names["prediction"]
simulations = pd.DataFrame.from_dict(res_dict, orient="columns")
simulations.columns = ["dir_name", "prediction_col"]
simulations

# %%
# TODO(Grisha): @Dan Move to lib.
# Initialize dataframe of weights.
weights_data = []
n_models = len(config["tiled_results_paths"])
for i in range(n_models):
    row = [0.0] * (n_models + 1)
    row[i] = 1.0
    row[-1] = 1 / n_models
    weights_data.append(row)
index = [key for key in config["tiled_results_paths"].to_dict()]
columns = index + ["equally_weighted"]
weights = pd.DataFrame(data=weights_data, index=index, columns=columns)
weights

# %%
# TODO(Grisha): @Dan Move to lib.
dag_builder_name = config["market_data_and_volatilty_dag_builder_name"]
dag_column_names = config["column_names"][dag_builder_name].to_dict()
hdbg.dassert_in("price", dag_column_names)
hdbg.dassert_in("volatility", dag_column_names)
dir_name = config["tiled_results_paths"][dag_builder_name]
market_data_and_volatility = pd.DataFrame.from_dict(
    {
        "price": dag_column_names["price"],
        "volatility": dag_column_names["volatility"],
    },
    orient="index",
    columns=["col"],
)
market_data_and_volatility.insert(0, "dir_name", dir_name)
display(market_data_and_volatility)

# %% [markdown]
# # Mix models

# %%
# This wraps ForecastEvaluator runs and aggregates results.
bar_metrics = dtfmod.evaluate_weighted_forecasts(
    simulations,
    weights,
    market_data_and_volatility,
    config["start_date"],
    config["end_date"],
    config["asset_id_col"],
    asset_ids=config["asset_ids"],
    annotate_forecasts_kwargs=config["annotate_forecasts_kwargs"],
    target_freq_str=None,
    index_mode=config["index_mode"],
)
bar_metrics.head()

# %%
bar_metrics.tail()

# %%
coplotti.plot_effective_correlation_rank(
    bar_metrics.xs("pnl", level=1, axis=1, drop_level=True)
)

# %%
corr_matrix = bar_metrics.xs("pnl", level=1, axis=1, drop_level=True).corr()
coplotti.plot_heatmap(corr_matrix)

# %%
coplotti.plot_portfolio_stats(bar_metrics, freq=config["freq"])

# %%
stats_computer = dtfmod.StatsComputer()
#
portfolio_stats, daily_metrics = stats_computer.compute_portfolio_stats(
    bar_metrics,
    config["freq"],
)
with pd.option_context("display.float_format", "{:,.2f}".format):
    display(portfolio_stats)
