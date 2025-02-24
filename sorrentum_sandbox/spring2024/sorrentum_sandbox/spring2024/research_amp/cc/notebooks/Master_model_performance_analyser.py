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

# %% [markdown]
# # Descriptions

# %% [markdown]
# Compute model performance metrics.

# %% [markdown]
# # Imports

# %%
import datetime
import logging

import matplotlib.pyplot as plt
import pandas as pd

import core.config as cconfig
import core.finance.portfolio_df_processing as cofinpdp
import core.plotting as coplotti
import dataflow.core as dtfcore
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
    "dir_name": "/shared_data/model/historical/build_tile_configs.C1b.ccxt_v7_1-all.5T.2019-10-01_2023-02-13.ins/tiled_results/",
    "asset_id_col": "asset_id",
    "dag_builder_name": "C1b",
    "dag_builder_ctor_as_str": "dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder",
    "start_date": datetime.date(2019, 10, 1),
    "end_date": datetime.date(2023, 2, 13),
    "plot_portfolio_stats_freq": "D",
    "fep_annotate_forecasts_kwargs": {
        "quantization": 30,
        "burn_in_bars": 3,
        "style": "longitudinal",
        "liquidate_at_end_of_day": False,
        "initialize_beginning_of_day_trades_to_zero": False,
    },
    "fep_binning_portfolio": {
        "proportion_of_data_per_bin": 0.1,
    },
}
# Add `DagBuilder` column names to the config.
dag_builder = dtfcore.get_DagBuilder_from_string(
    config["dag_builder_ctor_as_str"]
)
column_tags = ["price", "volatility", "prediction"]
config["column_names"] = dag_builder.get_column_names_dict(column_tags)
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Load results

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
# # Compute research PnL

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
coplotti.plot_portfolio_stats(
    bar_metrics,
    freq=config["plot_portfolio_stats_freq"],
)

# %% [markdown]
# # Compute stats

# %%
stats_computer = dtfmod.StatsComputer()
#
portfolio_stats, _ = stats_computer.compute_portfolio_stats(
    bar_metrics,
    config["plot_portfolio_stats_freq"],
)
with pd.option_context("display.float_format", "{:,.2f}".format):
    display(portfolio_stats)

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
    _ = metric_stats.plot(
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
