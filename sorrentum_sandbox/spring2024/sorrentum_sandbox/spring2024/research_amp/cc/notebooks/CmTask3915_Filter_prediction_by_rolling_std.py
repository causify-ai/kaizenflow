# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

# %% [markdown]
# # Descriptions

# %% [markdown]
# Filter model predictions by rolling std and compare performance metrics.

# %% [markdown]
# # Imports

# %%
import datetime
import logging

import dataflow_orange.system.Cx as dtfosc
import matplotlib.pyplot as plt
import pandas as pd

import core.config as cconfig
import core.finance.portfolio_df_processing as cofinpdp
import core.plotting as coplotti
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
config = {
    "dir_name": "/shared_data/model/historical/build_tile_configs.C1c.ccxt_v7_1-all.5T.2019-10-01_2023-02-13.ins/tiled_results/",
    "asset_id_col": "asset_id",
    "dag_builder_name": "C1c",
    "start_date": datetime.date(2019, 10, 1),
    "end_date": datetime.date(2023, 2, 13),
    "plot_portfolio_stats_freq": "D",
    "fep_annotate_forecasts_kwargs": {
        "quantization": "no_quantization",
        "burn_in_bars": 3,
        "style": "longitudinal",
        "liquidate_at_end_of_day": False,
        "initialize_beginning_of_day_trades_to_zero": False,
    },
    "fep_binning_portfolio": {
        "proportion_of_data_per_bin": 0.5,
    },
    "rolling_std_dev_factor": 0.5,
}
# Add `DagBuilder` column names to the config.
system_config = dtfosc.get_Cx_system_config_template_instance(
    config["dag_builder_name"]
)
dag_builder = system_config["dag_builder_object"]
column_tags = ["price", "volatility", "prediction"]
config["column_names"] = dag_builder.get_column_names_dict(column_tags)
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Load results

# %% [markdown]
# ## Load actual data

# %%
data_cols = list(config["column_names"].to_dict().values())
iter_ = dtfmod.yield_processed_parquet_tiles_by_year(
    config["dir_name"],
    config["start_date"],
    config["end_date"],
    config["asset_id_col"],
    data_cols,
    asset_ids=None,
)
df_res = hpandas.get_df_from_iterator(iter_)
df_res.head()

# %% [markdown]
# ## Filter data by rolling std

# %%
# TODO(@gp): Decide on the rolling window size.
window = int(pd.Timedelta("4D") / pd.Timedelta("5T"))
window

# %%
prediction_var = config["column_names"]["prediction"]
# Compute rolling mean.
prediction_rolling_mean = (
    df_res[prediction_var]
    .rolling(window)
    .mean()
    .rename(columns={prediction_var: "prediction_rolling_mean"})
)
# Compute rolling std.
prediction_rolling_std = (
    df_res[prediction_var]
    .rolling(window)
    .std()
    .rename(columns={prediction_var: "prediction_rolling_std"})
)
# Set filter condition.
filter_cond = (df_res[prediction_var] - prediction_rolling_mean).abs() > config[
    "rolling_std_dev_factor"
] * prediction_rolling_std
# Create a copy of data with filtered predictions.
df_res_filtered = df_res.copy()
# Replace predictions that do not pass condition with `None`.
df_res_filtered[prediction_var] = df_res_filtered[prediction_var][filter_cond]
df_res_filtered.tail()

# %% [markdown]
# # Compare research PnL

# %%
fep = dtfmod.ForecastEvaluatorFromPrices(
    config["column_names"]["price"],
    config["column_names"]["volatility"],
    config["column_names"]["prediction"],
)

# %%
portfolio_df, bar_metrics = fep.annotate_forecasts(
    df_res,
    # bulk_frac_to_remove=config["fep_annotate_forecasts_kwargs"]["bulk_frac_to_remove"],
    # bulk_fill_method=config["fep_annotate_forecasts_kwargs"]["bulk_fill_method"],
    # target_gmv=config["fep_annotate_forecasts_kwargs"]["target_gmv"],
    quantization=config["fep_annotate_forecasts_kwargs"]["quantization"],
    burn_in_bars=config["fep_annotate_forecasts_kwargs"]["burn_in_bars"],
    style=config["fep_annotate_forecasts_kwargs"]["style"],
    liquidate_at_end_of_day=config["fep_annotate_forecasts_kwargs"][
        "liquidate_at_end_of_day"
    ],
    initialize_beginning_of_day_trades_to_zero=config[
        "fep_annotate_forecasts_kwargs"
    ]["initialize_beginning_of_day_trades_to_zero"],
)

# %%
portfolio_df_filtered, bar_metrics_filtered = fep.annotate_forecasts(
    df_res_filtered,
    # bulk_frac_to_remove=config["fep_annotate_forecasts_kwargs"]["bulk_frac_to_remove"],
    # bulk_fill_method=config["fep_annotate_forecasts_kwargs"]["bulk_fill_method"],
    # target_gmv=config["fep_annotate_forecasts_kwargs"]["target_gmv"],
    quantization=config["fep_annotate_forecasts_kwargs"]["quantization"],
    burn_in_bars=config["fep_annotate_forecasts_kwargs"]["burn_in_bars"],
    style=config["fep_annotate_forecasts_kwargs"]["style"],
    liquidate_at_end_of_day=config["fep_annotate_forecasts_kwargs"][
        "liquidate_at_end_of_day"
    ],
    initialize_beginning_of_day_trades_to_zero=config[
        "fep_annotate_forecasts_kwargs"
    ]["initialize_beginning_of_day_trades_to_zero"],
)

# %%
all_metrics_dict = {
    "original": bar_metrics,
    "filtered": bar_metrics_filtered,
}
all_bar_metrics = pd.concat(
    all_metrics_dict.values(), axis=1, keys=all_metrics_dict.keys()
)
#
coplotti.plot_portfolio_stats(
    all_bar_metrics,
    freq=config["plot_portfolio_stats_freq"],
)

# %% [markdown]
# # Compare stats

# %%
stats_computer = dtfmod.StatsComputer()

# %%
portfolio_stats, _ = stats_computer.compute_portfolio_stats(
    bar_metrics,
    config["plot_portfolio_stats_freq"],
)
portfolio_stats_filtered, _ = stats_computer.compute_portfolio_stats(
    bar_metrics_filtered,
    config["plot_portfolio_stats_freq"],
)
#
all_portfolio_stats = pd.concat(
    [portfolio_stats, portfolio_stats_filtered],
    axis=1,
    keys=["original", "filtered"],
)
with pd.option_context("display.float_format", "{:,.2f}".format):
    display(all_portfolio_stats)

# %% [markdown]
# # Plot metrics

# %%
metric_modes = ["pnl", "pnl_in_bps", "hit_rate"]

# %%
for metric in metric_modes:
    metric_stats = cofinpdp.bin_prediction_annotated_portfolio_df(
        portfolio_df,
        config["fep_binning_portfolio"]["proportion_of_data_per_bin"],
        metric,
    )["mean"].mean(axis=1)
    metric_stats_filtered = cofinpdp.bin_prediction_annotated_portfolio_df(
        portfolio_df_filtered,
        config["fep_binning_portfolio"]["proportion_of_data_per_bin"],
        metric,
    )["mean"].mean(axis=1)
    all_metric_stats = pd.concat(
        [metric_stats, metric_stats_filtered],
        axis=1,
        keys=["original", "filtered"],
    )
    # Plot.
    _ = all_metric_stats.plot(
        kind="line",
        ylabel=metric,
        xlabel="bin",
        rot=0,
    )
    if metric == "hit_rate":
        plt.axhline(y=0.5, color="r", linestyle="--")
        plt.axhline(y=0.55, color="r", linestyle="--")
    else:
        plt.axhline(y=0.0, color="b", linestyle="-")
    plt.show()

# %%
