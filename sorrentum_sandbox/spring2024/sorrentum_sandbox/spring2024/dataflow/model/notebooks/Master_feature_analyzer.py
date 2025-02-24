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

# %% [markdown]
# # Imports

# %%
import logging
import os

import matplotlib.pyplot as plt

import core.config as cconfig
import core.plotting as coplotti
import core.statistics as costatis
import dataflow.model as dtfmod
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hparquet as hparque
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Build config

# %%
# Get config from env when running the notebook via the run_notebook.py script.
default_config = cconfig.get_config_from_env()
if default_config:
    _LOG.info("Using config from env vars")
else:
    _LOG.info("Using hardwired config")
    amp_dir = hgit.get_amp_abs_path()
    dir_name = os.path.join(
        amp_dir,
        "/shared_data/backtest.danya/build_tile_configs.C13a.ccxt_v7_5-all.2T.2023-06-01_2024-01-31.ins.run0/tiled_results",
    )
    cols = ["f1"]
    default_config_dict = {
        "dir_name": dir_name,
        "asset_id": 1467591036,
        "asset_id_col": "asset_id",
        "resampling_frequency": "2T",
        "feature_column_names": cols,
        "single_feature_column_name": "f1",
    }
    # Build config from dict.
    default_config = cconfig.Config().from_dict(default_config_dict)
print(default_config)

# %% [markdown]
# # Report tile metadata

# %%
parquet_tile_analyzer = dtfmod.ParquetTileAnalyzer()
parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
    default_config["dir_name"]
)

# %%
parquet_tile_analyzer.compute_metadata_stats_by_asset_id(parquet_tile_metadata)

# %%
parquet_tile_analyzer.compute_universe_size_by_time(parquet_tile_metadata)

# %%
asset_ids = parquet_tile_metadata.index.levels[0].to_list()
display(asset_ids)

# %% [markdown]
# # Load features

# %%
asset_batch_size = len(asset_ids)
# Add the `asset_id_col` to also display the instruments. This is also required
# to make `yield_parquet_tiles_by_assets()` work.
requested_columns = [default_config["asset_id_col"]] + default_config[
    "feature_column_names"
]
tile_iter = hparque.yield_parquet_tiles_by_assets(
    default_config["dir_name"],
    asset_ids,
    default_config["asset_id_col"],
    asset_batch_size,
    None,
)

# %%
tile = next(tile_iter)

# %%
feature_df = dtfmod.process_parquet_read_df(
    tile[
        default_config["feature_column_names"] + [default_config["asset_id_col"]]
    ],
    default_config["asset_id_col"],
)

# %%
feature_df.columns.levels[0].to_list()

# %%
feature_stats = costatis.compute_centered_process_stats_by_group(feature_df)
display(feature_stats.head())

# %%
feature_stats.groupby(level=1).mean()

# %%
feature_stats.groupby(level=0).mean()

# %%
feature_stats = costatis.compute_centered_process_stats_by_group(feature_df)
display(feature_stats.head())

# %%
mean_asset_stats_per_feature = feature_stats.groupby(level=1).mean()
display(mean_asset_stats_per_feature)

# %%
_, ax = plt.subplots()
mean_asset_stats_per_feature[
    ["mean", "var", "autocovar", "autocorr", "turn"]
].boxplot(ylabel="mean asset per feature", ax=ax)

# %%
mean_feature_stats_per_asset = feature_stats.groupby(level=0).mean()
display(mean_feature_stats_per_asset)

# %%
_, ax = plt.subplots()
mean_feature_stats_per_asset[
    ["mean", "var", "autocovar", "autocorr", "turn"]
].boxplot(ylabel="mean feature per asset", ax=ax)

# %%
mean_feature_corr = costatis.compute_mean_pearson_correlation_by_group(
    feature_df, 1
)
# Plot heatmap if correlation matrix contains >1 feature.
if mean_feature_corr.shape[1] > 1:
    coplotti.plot_heatmap(mean_feature_corr, mode="clustermap", figsize=(10, 10))

# %%
mean_asset_corr = costatis.compute_mean_pearson_correlation_by_group(
    feature_df, 0
)
coplotti.plot_heatmap(mean_asset_corr, mode="clustermap", figsize=(10, 10))

# %% [markdown]
# # Per-asset cross-sectional feature analysis (all features for a single asset)

# %%
single_asset_feature_df = feature_df.T.xs(default_config["asset_id"], level=1).T

# %%
single_asset_feature_df_corr = single_asset_feature_df.corr()
# Plot heatmap if correlation matrix contains >1 feature.
if single_asset_feature_df_corr.shape[1] > 1:
    coplotti.plot_heatmap(
        single_asset_feature_df.corr(), mode="clustermap", figsize=(10, 10)
    )
# Alternative method (prints correlation matrix and does not reorder columns):
# coplotti.plot_correlation_matrix(features)

# %%
coplotti.plot_effective_correlation_rank(single_asset_feature_df)

# %%
coplotti.plot_projection(
    single_asset_feature_df.resample(default_config["resampling_frequency"]).sum(
        min_count=1
    )
)

# %%
# sc = dtfmod.StatsComputer()
# single_asset_feature_df.apply(sc.compute_summary_stats).round(3)
# Alternative method:
single_asset_feature_df.apply(costatis.compute_moments)

# %% [markdown]
# # Single feature analysis

# %%
feature = default_config["single_feature_column_name"]
_LOG.info("feature=%s", feature)

# %%
coplotti.plot_qq(single_asset_feature_df[feature])

# %%
coplotti.plot_histograms_and_lagged_scatterplot(
    single_asset_feature_df[feature], lag=2, figsize=(20, 10)
)

# %%
coplotti.plot_time_series_by_period(
    single_asset_feature_df[feature],
    "hour",
)

# %% [markdown]
# # Feature cross-section (single feature across all assets)

# %%
xs_feature_df = feature_df[feature]

# %%
coplotti.plot_correlation_matrix(xs_feature_df)

# %%
coplotti.plot_effective_correlation_rank(xs_feature_df)

# %%
