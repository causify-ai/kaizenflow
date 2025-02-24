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

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import helpers.hdataframe as hdatafr
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
    "backtest_config": "ccxt_v7_1-all.5T.2019-10-01_2023-02-13",
    "start_date": datetime.date(2019, 10, 1),
    "end_date": datetime.date(2023, 2, 13),
    "metrics": {
        "calculate_hit_rate_kwargs": {
            "alpha": None,
            "method": None,
            "threshold": None,
            "prefix": None,
        },
        "n_quantiles": 10,
        "column_names": {
            "hit": "hit",
            "bar_pnl": "bar_pnl",
        },
    },
}
# Add `Daguilder` column names to the config.
dag_builder = dtfcore.get_DagBuilder_from_string(
    config["dag_builder_ctor_as_str"]
)
dag_config = dag_builder.get_config_template()
column_tags = ["price", "volatility", "target_variable", "prediction"]
config["column_names"] = dag_builder.get_column_names_dict(column_tags)
# Add `vol_adj_returns` column if needed.
# config["column_names"]["vol_adj_returns"] = "target_vwap_ret_0.vol_adj"
# Add start and end dates to the config.
if "start_date" in config:
    hdbg.dassert_in("end_date", config)
else:
    # Extract start and end datetimes from the backtest config.
    hdbg.dassert_in("backtest_config", config)
    backtest_config = config["backtest_config"]
    _, _, time_interval_str = cconfig.parse_backtest_config(backtest_config)
    start_ts, end_ts = cconfig.get_period(time_interval_str)
    config["start_date"] = start_ts.date()
    config["end_date"] = end_ts.date()
# Add time scaling to the metrics config.
freq = dag_config["resample"]["transformer_kwargs"]["rule"]
time_scaling = hdatafr.compute_points_per_year_for_given_freq(freq)
config["metrics"]["time_scaling"] = time_scaling
#
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Load results

# %%
# Get data column names to request.
data_cols = list(config["column_names"].to_dict().values())
if config["dag_builder_name"] in ["C3a", "C8b"]:
    # Remove target variable column name for models that do not compute it.
    data_cols.remove(config["column_names"]["target_variable"])

# %%
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
# # Compute metrics

# %%
metric_modes = ["hit_rate", "pnl", "sharpe_ratio"]

# %% [markdown]
# ## Overall

# %%
tag_mode = "all"
stats_all = dtfmod.cross_val_apply_metrics(
    [df_res], tag_mode, metric_modes, config
)
stats_all

# %% [markdown]
# ## Per asset

# %%
tag_mode = "full_symbol"
stats_by_symbol = dtfmod.cross_val_apply_metrics(
    [df_res], tag_mode, metric_modes, config
)

# %%
stats_by_symbol["hit_rate_point_est_(%)"].sort_values().plot(
    kind="bar", ylim=(45, 55)
)

# %%
stats_by_symbol["total_pnl"].sort_values().plot(kind="bar")

# %%
# TODO(Grisha): Seems too big for some assets.
stats_by_symbol["SR"].sort_values().plot(kind="bar")

# %% [markdown]
# ## Per prediction quantile rank

# %%
tag_mode = "prediction_magnitude_quantile_rank"
stats_by_pred_magnitude = dtfmod.cross_val_apply_metrics(
    [df_res], tag_mode, metric_modes, config
)

# %%
stats_by_pred_magnitude["hit_rate_point_est_(%)"].plot(kind="bar", ylim=(45, 55))

# %%
stats_by_pred_magnitude["total_pnl"].plot(kind="bar")

# %%
stats_by_pred_magnitude["SR"].plot(kind="bar")
