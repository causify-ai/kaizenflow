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

# %% [markdown]
# # Imports

# %%
import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import core.plotting as coplotti
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
config = {
    "reader": {
        "signature": "bulk.airflow.downloaded_1min.parquet.ohlcv.futures.v7_5.ccxt.binance.v1_0_0",
        "start_timestamp": None,
        # TODO(Grisha): for some reason `RawDataReader` does not work with both timestamps being None.
        "end_timestamp": pd.Timestamp("2023-06-30"),
    },
    "column_names": {
        "timestamp": "timestamp",
        "asset_id_col": "full_symbol",
        "open": "open",
        "low": "low",
        "high": "high",
        "close": "close",
        "volume": "volume",
        "volume_notional": "volume_notional",
    },
    "resampling_rule": "D",
}
config = cconfig.Config().from_dict(config)
print(config)

# %% [markdown]
# # Load and post-process OHLCV data

# %%
# TODO(Grisha): use MarketData, see CmTask4713 "Propagate download_universe_version
# to ImClient".
reader = icdc.RawDataReader(config["reader"]["signature"], stage="test")
ohlcv_data = reader.read_data(
    config["reader"]["start_timestamp"], config["reader"]["end_timestamp"]
)
_LOG.info("df.shape=%s", ohlcv_data.shape)
ohlcv_data.head(3)

# %%
# Add full symbol column to df.
full_symbol_col = ivcu.build_full_symbol(
    ohlcv_data["exchange_id"], ohlcv_data["currency_pair"]
)
ohlcv_data.insert(0, config["column_names"]["asset_id_col"], full_symbol_col)
ohlcv_data.head(3)

# %%
# Remove `timestamp` column since the info is already in index.
ohlcv_data = ohlcv_data.drop(config["column_names"]["timestamp"], axis=1)
ohlcv_data = (
    ohlcv_data.reset_index()
    .sort_values(
        [
            config["column_names"]["asset_id_col"],
            config["column_names"]["timestamp"],
        ]
    )
    .set_index("timestamp")
)
ohlcv_data.head(3)

# %%
# Compute notional volume.
ohlcv_data[config["column_names"]["volume_notional"]] = (
    ohlcv_data[config["column_names"]["volume"]]
    * ohlcv_data[config["column_names"]["close"]]
)
ohlcv_data.head(3)

# %%
# Remove the duplicates.
use_index = True
duplicate_columns = [config["column_names"]["asset_id_col"]]
_LOG.info("The number of rows before removing the dups=%s", ohlcv_data.shape[0])
ohlcv_data = hpandas.drop_duplicates(
    ohlcv_data,
    use_index,
    column_subset=duplicate_columns,
    keep="last",
).sort_index()
_LOG.info("The number of rows after removing the dups=%s", ohlcv_data.shape[0])

# %% [markdown]
# # High-level stats

# %%
# List the coins.
universe = sorted(
    list(ohlcv_data[config["column_names"]["asset_id_col"]].unique())
)
_LOG.info("The number of coins in the universe=%s", len(universe))
universe

# %%
# Calculate min and max timestamps for each symbol. It is easier to do before converting
# to a Multiindex df.
full_symbol_grouped_df = ohlcv_data.reset_index().groupby(
    config["column_names"]["asset_id_col"]
)
symbols_by_timestamps = full_symbol_grouped_df.agg(
    start_timestamp=(config["column_names"]["timestamp"], "min"),
    end_timestamp=(config["column_names"]["timestamp"], "max"),
)
symbols_by_timestamps

# %% [markdown]
# # Convert to the DataFlow format and resample

# %%
ohlcv_data_pivot = ohlcv_data.pivot(
    columns=config["column_names"]["asset_id_col"],
    values=[
        config["column_names"]["open"],
        config["column_names"]["high"],
        config["column_names"]["low"],
        config["column_names"]["close"],
        config["column_names"]["volume"],
        config["column_names"]["volume_notional"],
    ],
)
ohlcv_data_pivot.head(3)

# %%
ohlcv_resampling_node = dtfcore.GroupedColDfToDfTransformer(
    "resample",
    transformer_func=cofinanc.resample_bars,
    **{
        "in_col_groups": [
            (config["column_names"]["volume"],),
            (config["column_names"]["volume_notional"],),
        ],
        "out_col_group": (),
        "transformer_kwargs": {
            "rule": config["resampling_rule"],
            "resampling_groups": [
                (
                    {
                        "volume": config["column_names"]["volume"],
                        "volume_notional": config["column_names"][
                            "volume_notional"
                        ],
                    },
                    "sum",
                    {"min_count": 1},
                ),
            ],
            "vwap_groups": [],
        },
        "reindex_like_input": False,
        "join_output_with_input": False,
    },
)
resampled_volumes = ohlcv_resampling_node.fit(ohlcv_data_pivot)["df_out"]
resampled_volumes.head(3)

# %% [markdown]
# # Compute volume statistics

# %%
mdv_notional = resampled_volumes[config["column_names"]["volume_notional"]].mean()
mdv_notional.head(3)

# %%
coplotti.plot_barplot(
    mdv_notional.sort_values(),
    orientation="horizontal",
    figsize=[20, 50],
)

# %%
# Exclude BTC and ETH.
mask = mdv_notional.index.isin(["binance::BTC_USDT", "binance::ETH_USDT"])
mdv_notional_no_btc_eth = mdv_notional[~mask]

# %%
coplotti.plot_barplot(
    mdv_notional_no_btc_eth.sort_values(),
    orientation="horizontal",
    figsize=[20, 50],
)

# %%
volume_notional_as_pct = (
    mdv_notional_no_btc_eth * 100 / mdv_notional_no_btc_eth.sum()
)
volume_notional_as_pct = volume_notional_as_pct.sort_values(ascending=False)
volume_notional_as_pct
