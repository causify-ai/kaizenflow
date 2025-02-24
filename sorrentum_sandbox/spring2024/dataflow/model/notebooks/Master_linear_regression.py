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

import pandas as pd

import core.config as cconfig
import core.signal_processing as csigproc
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

# %% run_control={"marked": true}
amp_dir = hgit.get_amp_abs_path()
dir_name = os.path.join(
    amp_dir,
    "/shared_data/backtest.danya/build_tile_configs.C11a.ccxt_v8_1-all.60T.2023-08-01_2024-01-31.ins.run0/tiled_results",
)
cols = [
    "p1.c",
    "p2.c",
    "p_lr.c",
    "q1.c",
    "q2.c",
    "q3.c",
    "r1.c",
    "r2.c",
    "r4.c",
    "r5.c",
    "r6.c",
    "r_lr.c",
    "v_ld.c",
]

config = {
    "dir_name": dir_name,
    "asset_id_col": "asset_id",
    "feature_col_names": cols,
    "price_col_name": "close",
    "regression_config": {
        "x_cols": cols,
        "x_col_shift": 1,
    },
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Report tile metadata

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
# # Load features

# %%
asset_batch_size = len(asset_ids)
# Add the `asset_id_col` to also display the instruments. This is also required
# to make `yield_parquet_tiles_by_assets()` work.
requested_columns = [config["asset_id_col"]] + config["feature_col_names"]
tile_iter = hparque.yield_parquet_tiles_by_assets(
    config["dir_name"], asset_ids, config["asset_id_col"], asset_batch_size, None
)

# %%
tile = next(tile_iter)

# %%
feature_df = dtfmod.process_parquet_read_df(
    tile[config["feature_col_names"] + [config["asset_id_col"]]],
    config["asset_id_col"],
)

# %% [markdown]
# # Generate target

# %%
asset_batch_size = len(asset_ids)
# Add the `asset_id_col` to also display the instruments. This is also required
# to make `yield_parquet_tiles_by_assets()` work.
requested_columns = [config["asset_id_col"]] + [config["price_col_name"]]
tile_iter = hparque.yield_parquet_tiles_by_assets(
    config["dir_name"], asset_ids, config["asset_id_col"], asset_batch_size, None
)

# %%
tile = next(tile_iter)

# %%
price_df = dtfmod.process_parquet_read_df(
    tile[[config["price_col_name"]] + [config["asset_id_col"]]],
    config["asset_id_col"],
)

# %%
rets_df = price_df.pct_change()
rets_df = rets_df.rename(mapper={"close": "rets"}, axis=1, level=0)
vol_df = rets_df.rolling(30).std()
zrets_df = csigproc.compress_tails(
    rets_df / vol_df.shift(config["regression_config"]["x_col_shift"]), 4
)
zrets_df = zrets_df.rename(mapper={"rets": "zrets"}, axis=1, level=0)

# %%
zrets_df.stack().hist(bins=31)

# %%
# Approximate total volatility in bps.
1e4 * vol_df.mean().mean()

# %%
# Approximate total vol in bps by asset.
1e4 * vol_df.mean()

# %% [markdown]
# # Combine features and target

# %%
regression_df = pd.concat([feature_df, zrets_df], axis=1)

# %%
regression_df.columns.levels[0]

# %%
regression_coeffs = costatis.compute_regression_coefficients_by_group(
    regression_df,
    y_col="zrets",
    **config["regression_config"].to_dict(),
)
display(regression_coeffs.head())

# %%
regression_coeffs.groupby(level=1).mean()

# %%
q_vals = costatis.estimate_q_values(regression_coeffs["p_val_2s"])
regression_coeffs["q_val"] = q_vals

# %%
q_val_df = []
for feature in config["feature_col_names"]:
    q_val_srs = (
        regression_coeffs["q_val"]
        .xs(feature, level=1)
        .sort_values()
        .reset_index()["q_val"]
    )
    q_val_srs.name = feature
    q_val_df.append(q_val_srs)
q_val_df = pd.concat(q_val_df, axis=1)

# %%
q_val_df.plot()
