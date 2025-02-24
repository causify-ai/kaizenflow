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

# %%
import datetime
import logging
import os

import core.config as cconfig
import core.plotting as coplotti
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hparquet as hparque
import helpers.hprint as hprint
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build the config

# %%
amp_dir = hgit.get_amp_abs_path()
dir_name = os.path.join(
    "/shared_data/model/historical/build_tile_configs.C5b.ccxt_v7_1-all.5T.2019-10-01_2023-07-02.ins.run0/tiled_results",
)
config = {
    "dir_name": dir_name,
    "start_date": datetime.date(2022, 1, 1),
    "end_date": datetime.date(2022, 1, 31),
    "asset_id_col": "asset_id",
    "pnl_resampling_frequency": "15T",
    "annotate_forecasts_kwargs": {
        "style": "longitudinal",
        "quantization": 30,
        "liquidate_at_end_of_day": False,
        "initialize_beginning_of_day_trades_to_zero": False,
        "burn_in_bars": 3,
        "compute_extended_stats": True,
        "target_dollar_risk_per_name": 1e2,
        "modulate_using_prediction_magnitude": True,
    },
    "column_names": {
        "price_col": "vwap",
        "volatility_col": "garman_klass_vol",
        "prediction_col": "feature",
    },
    "bin_annotated_portfolio_df_kwargs": {
        "proportion_of_data_per_bin": 0.2,
        "output_col": "pnl_in_bps",
        "normalize_prediction_col_values": False,
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Load tiled results

# %% [markdown]
# ## Report tile stats

# %%
parquet_tile_analyzer = dtfmod.ParquetTileAnalyzer()
parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
    config["dir_name"]
)

# %%
parquet_tile_analyzer.compute_metadata_stats_by_asset_id(parquet_tile_metadata)

# %%
parquet_tile_analyzer.compute_universe_size_by_time(parquet_tile_metadata)

# %%
asset_ids = parquet_tile_metadata.index.levels[0].to_list()
display(asset_ids)

# %% [markdown]
# ## Load a single-asset tile

# %%
asset_batch_size = 1
cols = None
single_asset_tile = next(
    hparque.yield_parquet_tiles_by_assets(
        config["dir_name"],
        asset_ids[0:1],
        config["asset_id_col"],
        asset_batch_size,
        cols,
    )
)

# %%
single_tile_df = dtfmod.process_parquet_read_df(
    single_asset_tile, config["asset_id_col"]
)

# %%
single_tile_df.columns.levels[0].to_list()

# %%
single_tile_df.head(3)

# %% [markdown]
# # Compute portfolio bar metrics when forecasting from price without optimizer.

# %%
forecast_evaluator = dtfmod.ForecastEvaluatorFromPrices
portfolio_df, bar_metrics = dtfmod.annotate_forecasts_by_tile(
    config["dir_name"],
    config["start_date"],
    config["end_date"],
    config["asset_id_col"],
    config["column_names"]["price_col"],
    config["column_names"]["volatility_col"],
    config["column_names"]["prediction_col"],
    asset_ids=None,
    annotate_forecasts_kwargs=config["annotate_forecasts_kwargs"].to_dict(),
    return_portfolio_df=True,
    forecast_evaluator=forecast_evaluator,
    optimizer_config_dict=None,
)

# %%
coplotti.plot_portfolio_stats(
    bar_metrics, freq=config["pnl_resampling_frequency"]
)

# %% [markdown]
# # Compute portfolio bar metrics when forecasting, with optimizer.

# %%
forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer
optimizer_config_dict = {
    "dollar_neutrality_penalty": 0.9,
    "volatility_penalty": 1.0,
    "relative_holding_penalty": 3.0,
    "relative_holding_max_frac_of_gmv": 0.6,
    "target_gmv": 1e4,
    "target_gmv_upper_bound_penalty": 0.95,
    "target_gmv_hard_upper_bound_multiple": 1.00,
    "turnover_penalty": 0.09,
    "solver": "ECOS",
}
portfolio_df, bar_metrics = dtfmod.annotate_forecasts_by_tile(
    config["dir_name"],
    config["start_date"],
    config["end_date"],
    config["asset_id_col"],
    config["column_names"]["price_col"],
    config["column_names"]["volatility_col"],
    config["column_names"]["prediction_col"],
    asset_ids=None,
    annotate_forecasts_kwargs=config["annotate_forecasts_kwargs"].to_dict(),
    return_portfolio_df=True,
    forecast_evaluator=forecast_evaluator,
    optimizer_config_dict=optimizer_config_dict,
)

# %%
coplotti.plot_portfolio_stats(
    bar_metrics, freq=config["pnl_resampling_frequency"]
)


# %% [markdown]
# # Compute aggregate portfolio stats

# %%
stats_computer = dtfmod.StatsComputer()

# %%
portfolio_stats, daily_metrics = stats_computer.compute_portfolio_stats(
    bar_metrics,
    config["pnl_resampling_frequency"],
)
display(portfolio_stats)

# %%
