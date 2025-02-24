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

# %% [markdown]
# # Description

# %% [markdown]
# The notebook compares the data from the `RawDataReader` and `HistoricalDataSource` with that from the production DAG.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import logging
import os
from typing import List

import pandas as pd

import core.finance as cofinanc
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe_utils as imvcuunut

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %% [markdown]
# # Config

# %%
system_log_dir = "/shared_data/ecs/preprod/twap_experiment/system_reconciliation/C3a/20230419/system_log_dir.scheduled.20230419_041000.20230419_100500"
bar_duration = "5T"
universe_version = "v7.1"
# UTC timestamps. Use lookback to get the full bar, where 1 bar consists of five 1-minute rows.
start_timestamp_UTC = pd.Timestamp(
    "2023-04-19 04:10:00", tz="UTC"
) - pd.Timedelta(minutes=4)
_LOG.info("start_timestamp_UTC=%s", start_timestamp_UTC)
end_timestamp_UTC = pd.Timestamp("2023-04-19 08:05:00", tz="UTC")
_LOG.info("end_timestamp_UTC=%s", end_timestamp_UTC)
# ET timestamps.
start_timestamp_ET = start_timestamp_UTC.tz_convert("America/New_York")
_LOG.info("start_timestamp_ET=%s", start_timestamp_ET)
end_timestamp_ET = end_timestamp_UTC.tz_convert("America/New_York")
_LOG.info("end_timestamp_ET=%s", end_timestamp_ET)


# %%
def _print_df_info(df: pd.DataFrame) -> None:
    """
    Print basic stats about a DataFrame.
    """
    _LOG.info(
        "min_timestamp=%s, max_timestamp=%s", df.index.min(), df.index.max()
    )
    _LOG.info("columns=%s", hprint.list_to_str(df.columns.levels[0]))
    _LOG.info("assets=%s", hprint.list_to_str(df.columns.levels[1]))


def resample_ohlcv_bars(
    df_ohlcv: pd.DataFrame, bar_duration: str
) -> pd.DataFrame:
    """
    Resample 1-minute data to `bar_duration`.
    """
    # Resample.
    resampling_node = dtfcore.GroupedColDfToDfTransformer(
        "resample",
        transformer_func=cofinanc.resample_bars,
        **{
            "in_col_groups": [
                ("open",),
                ("high",),
                ("low",),
                ("close",),
                ("volume",),
            ],
            "out_col_group": (),
            "transformer_kwargs": {
                "rule": bar_duration,
                "resampling_groups": [
                    ({"close": "close"}, "last", {}),
                    ({"high": "high"}, "max", {}),
                    ({"low": "low"}, "min", {}),
                    ({"open": "open"}, "first", {}),
                    (
                        {"volume": "volume"},
                        "sum",
                        {"min_count": 1},
                    ),
                    (
                        {
                            "close": "twap",
                        },
                        "mean",
                        {},
                    ),
                ],
                "vwap_groups": [
                    ("close", "volume", "vwap"),
                ],
            },
            "reindex_like_input": False,
            "join_output_with_input": False,
        },
    )
    resampled_ohlcv = resampling_node.fit(df_ohlcv)["df_out"]
    return resampled_ohlcv


# %% [markdown]
# # Load DAG data

# %%
# Get bar timestamps grid. Round up to the nearest bar as DAG saves data every bar.
timestamps = pd.date_range(
    start_timestamp_ET.ceil(bar_duration),
    end_timestamp_ET.ceil(bar_duration),
    freq=bar_duration,
)
_LOG.info("timestamp_min=%s, timestamp_max=%s", timestamps[0], timestamps[-1])
dag_data_dir = os.path.join(system_log_dir, "dag", "node_io", "node_io.data")
_LOG.info("dag_data_dir=%s", dag_data_dir)

# %%
node_name = "predict.0.read_data"
dfs = []
for timestamp in timestamps:
    curr_df = dtfcore.get_dag_node_output(dag_data_dir, node_name, timestamp)
    bar_duration_int = int(bar_duration.strip("T"))
    curr_df = curr_df.sort_index(ascending=True)
    # Resolution is 1 minute for the `read_data` node, load the last 5 rows to get
    # the full bar.
    curr_df = curr_df.tail(bar_duration_int)
    dfs.append(curr_df)
dag_read_data_df_out = pd.concat(dfs)
_print_df_info(dag_read_data_df_out)
dag_read_data_df_out.head(3)

# %%
node_name = "predict.2.resample"
dfs = []
for timestamp in timestamps:
    curr_df = dtfcore.get_dag_node_output(dag_data_dir, node_name, timestamp)
    # Resolution = `bar_duration` so load only the last row.
    curr_df = curr_df.sort_index(ascending=True)
    curr_df = curr_df.tail(1)
    dfs.append(curr_df)
dag_resample_df_out = pd.concat(dfs)
# When loading / resampling the data manually the `compute_bar_feature` node is not run.
dag_resample_df_out = dag_resample_df_out.drop("cmf", axis=1)
_print_df_info(dag_resample_df_out)
dag_resample_df_out.head(3)


# %% [markdown]
# # Compare data from the `RawDataReader` against that from the DAG

# %%
def load_ohlcv_data_from_raw_data_reader(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    bar_duration: str,
    use_historical: bool,
    full_symbols: List[str],
    apply_timing_fix: bool,
    convert_to_multiindex: bool = True,
) -> pd.DataFrame:
    """
    Load OHLCV data using the `RawDataReader`.

    :param use_historical: read historical Parquet data if True, otherwise read data
        from the real-time production DB
    :param full_symbols: read data only for particular assets
    :param apply_timing_fix: apply the timing fix if True, otherwise read data as-is
    :param convert_to_multiindex: convert to the multiindex `dataflow` format, otherwise
        keep as-is
    """
    if use_historical:
        # Historical Parquet data.
        signature = "periodic_daily.airflow.downloaded_1min.parquet.ohlcv.futures.v7.ccxt.binance.v1_0_0"
    else:
        # Real-time from the prod DB.
        signature = "periodic_daily.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0"
    reader = imvcdcimrdc.RawDataReader(signature)
    if apply_timing_fix:
        # Subtract 1 minute to account for the fact that timestamp indicates the start
        # of the bar instead of the end of that.
        start_timestamp = start_timestamp - pd.Timedelta(minutes=1)
        end_timestamp = end_timestamp - pd.Timedelta(minutes=1)
    ohlcv = reader.read_data(start_timestamp, end_timestamp)
    hdbg.dassert(not ohlcv.empty, "Requested OHLCV data not available.")
    # Add asset_id's.
    ohlcv["full_symbol"] = ohlcv["exchange_id"] + "::" + ohlcv["currency_pair"]
    ohlcv_currency_pairs = ohlcv["full_symbol"].unique()
    ohlcv_asset_id_to_full_symbol = (
        imvcuunut.build_numerical_to_string_id_mapping(ohlcv_currency_pairs)
    )
    ohlcv_full_symbol_to_asset_id = {
        v: k for k, v in ohlcv_asset_id_to_full_symbol.items()
    }
    ohlcv["asset_id"] = ohlcv["full_symbol"].apply(
        lambda x: ohlcv_full_symbol_to_asset_id[x]
    )
    # Keep only the assets that belong to the prod universe.
    ohlcv = ohlcv[ohlcv["full_symbol"].isin(full_symbols)]
    # Convert timestamp to `pd.Timestamp`.
    if use_historical:
        # Already converted.
        pass
    else:
        # Convert the timestamp that indicates the end of the sampling
        # period to an index.
        ohlcv["timestamp"] = ohlcv["timestamp"].apply(
            hdateti.convert_unix_epoch_to_timestamp
        )
        ohlcv = ohlcv.set_index("timestamp")
    # Rename `timestamp` column to distinguish between `timestamp` as `pd.Timestamp` and
    # `timestamp` in milliseconds.
    ohlcv = ohlcv.rename(columns={"timestamp": "timestamp_in_milliseconds"})
    # Drop duplicated rows with the same `full_symbol`, `timestamp`, keeping the one
    # with the latest `knowledge_timestamp` as it is done in `ImClient`.
    ohlcv = ohlcv.sort_values(
        by=["full_symbol", "timestamp", "knowledge_timestamp"]
    )
    duplicate_columns = ["full_symbol"]
    use_index = True
    ohlcv = hpandas.drop_duplicates(
        ohlcv,
        use_index,
        column_subset=duplicate_columns,
        keep="last",
    ).sort_index()
    if convert_to_multiindex:
        if use_historical:
            normalized_ohlcv = ohlcv.pivot(
                columns="asset_id",
                values=["open", "high", "low", "close", "volume"],
            )
        else:
            normalized_ohlcv = ohlcv.pivot(
                columns="asset_id",
                values=["open", "high", "low", "close", "volume"],
            )
    else:
        normalized_ohlcv = ohlcv
    # Convert to the ET timezone as DAG operates in the ET timezone.
    normalized_ohlcv.index = normalized_ohlcv.index.tz_convert("America/New_York")
    if apply_timing_fix:
        # Add 1 minute back.
        normalized_ohlcv.index = normalized_ohlcv.index + pd.Timedelta(minutes=1)
    return normalized_ohlcv


# %% [markdown]
# ## Historical data

# %%
# Get the prod universe as `full_symbols`.
vendor = "CCXT"
mode = "trade"
as_full_symbol = True
full_symbols = ivcu.get_vendor_universe(
    vendor,
    mode,
    version=universe_version,
    as_full_symbol=as_full_symbol,
)
_LOG.info(full_symbols)

# %% [markdown]
# ### Without the timing fix

# %%
use_historical = True
apply_timing_fix = False
historical_ohlcv = load_ohlcv_data_from_raw_data_reader(
    start_timestamp_UTC,
    end_timestamp_UTC,
    bar_duration,
    use_historical,
    full_symbols,
    apply_timing_fix,
)
_print_df_info(historical_ohlcv)
historical_ohlcv.head(3)

# %% [markdown]
# There is a timing issue when reading historical data.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    historical_ohlcv[columns_to_compare], dag_read_data_df_out[columns_to_compare]
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ### With the timing fix

# %%
use_historical = True
apply_timing_fix = True
historical_ohlcv_with_fix = load_ohlcv_data_from_raw_data_reader(
    start_timestamp_UTC,
    end_timestamp_UTC,
    bar_duration,
    use_historical,
    full_symbols,
    apply_timing_fix,
)
_print_df_info(historical_ohlcv_with_fix)
historical_ohlcv_with_fix.head(3)

# %% [markdown]
# The data matches that from the prod DAG when the timing fix is applied.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    historical_ohlcv_with_fix[columns_to_compare],
    dag_read_data_df_out[columns_to_compare],
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ### Resampled data with the timing fix

# %%
resampled_historical_ohlcv_with_fix = resample_ohlcv_bars(
    historical_ohlcv_with_fix, bar_duration
)
_print_df_info(resampled_historical_ohlcv_with_fix)
resampled_historical_ohlcv_with_fix.head(3)

# %% [markdown]
# The resampled data also matches that from the prod DAG when the timing fix is applied.

# %%
diff_df = hpandas.compare_dfs(
    resampled_historical_ohlcv_with_fix, dag_resample_df_out
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ## Real-time data

# %% [markdown]
# ### Without the timing fix

# %%
use_historical = False
apply_timing_fix = False
realtime_ohlcv = load_ohlcv_data_from_raw_data_reader(
    start_timestamp_UTC,
    end_timestamp_UTC,
    bar_duration,
    use_historical,
    full_symbols,
    apply_timing_fix,
)
_print_df_info(realtime_ohlcv)
realtime_ohlcv.head(3)

# %% [markdown]
# There is a timing issue when reading real-time data.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    realtime_ohlcv[columns_to_compare], dag_read_data_df_out[columns_to_compare]
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ### With the timing fix

# %%
use_historical = False
apply_timing_fix = True
realtime_ohlcv_with_fix = load_ohlcv_data_from_raw_data_reader(
    start_timestamp_UTC,
    end_timestamp_UTC,
    bar_duration,
    use_historical,
    full_symbols,
    apply_timing_fix,
)
_print_df_info(realtime_ohlcv_with_fix)
realtime_ohlcv_with_fix.head(3)

# %% [markdown]
# The data matches that from the prod DAG when the timing fix is applied.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    realtime_ohlcv_with_fix[columns_to_compare],
    dag_read_data_df_out[columns_to_compare],
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# #### Estimate the delay between `end_download_timestamp`, `knowledge_timestamp` and `timestamp`.

# %%
use_historical = False
apply_timing_fix = True
convert_to_multiindex = False
realtime_ohlcv_with_fix_as_is = load_ohlcv_data_from_raw_data_reader(
    start_timestamp_UTC,
    end_timestamp_UTC,
    bar_duration,
    use_historical,
    full_symbols,
    apply_timing_fix,
    convert_to_multiindex,
)
# Reset the index to use `timestamp` in calculations.
realtime_ohlcv_with_fix_as_is = realtime_ohlcv_with_fix_as_is.reset_index()
realtime_ohlcv_with_fix_as_is.head(3)

# %%
# Compute delay in seconds between `end_download_timestamp` and `timestamp`.
realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"] = (
    realtime_ohlcv_with_fix_as_is["end_download_timestamp"]
    - realtime_ohlcv_with_fix_as_is["timestamp"]
).dt.total_seconds()
_LOG.info(
    "Average delay between `end_download_timestamp` and `timestamp` in seconds is %s, min=%s, max=%s, std=%s",
    round(realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"].mean(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"].min(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"].max(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"].std(), 2),
)
realtime_ohlcv_with_fix_as_is["diff_1_in_seconds"].plot(kind="box")

# %%
# Compute delay in seconds between `knowledge_timestamp` and `timestamp`.
realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"] = (
    realtime_ohlcv_with_fix_as_is["knowledge_timestamp"]
    - realtime_ohlcv_with_fix_as_is["timestamp"]
).dt.total_seconds()
_LOG.info(
    "Average delay between `knowledge_timestamp` and `timestamp` in seconds is %s, min=%s, max=%s, std=%s",
    round(realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"].mean(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"].min(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"].max(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"].std(), 2),
)
realtime_ohlcv_with_fix_as_is["diff_2_in_seconds"].plot(kind="box")

# %%
# Compute delay in seconds between `knowledge_timestamp` and `end_download_timestamp`.
realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"] = (
    realtime_ohlcv_with_fix_as_is["knowledge_timestamp"]
    - realtime_ohlcv_with_fix_as_is["end_download_timestamp"]
).dt.total_seconds()
_LOG.info(
    "Average delay between `knowledge_timestamp` and `end_download_timestamp` in seconds is %s, min=%s, max=%s, std=%s",
    round(realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"].mean(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"].min(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"].max(), 2),
    round(realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"].std(), 2),
)
realtime_ohlcv_with_fix_as_is["diff_3_in_seconds"].plot(kind="box")

# %% [markdown]
# ### Resampled data with the timing fix

# %%
resampled_realtime_ohlcv_with_fix = resample_ohlcv_bars(
    realtime_ohlcv_with_fix, bar_duration
)
_print_df_info(resampled_realtime_ohlcv_with_fix)
resampled_realtime_ohlcv_with_fix.head(3)

# %% [markdown]
# The resampled data also matches that from the prod DAG when the timing fix is applied.

# %%
diff_df = hpandas.compare_dfs(
    resampled_realtime_ohlcv_with_fix, dag_resample_df_out
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)


# %% [markdown]
# # Compare OHLCV data from the prod-like `HistoricalDataSource` with that from the DAG

# %%
def _get_prod_market_data(universe_version: str):
    # Get trading universe as asset ids.
    vendor = "CCXT"
    mode = "trade"
    as_full_symbol = True
    full_symbols = ivcu.get_vendor_universe(
        vendor,
        mode,
        version=universe_version,
        as_full_symbol=as_full_symbol,
    )
    asset_ids = [
        ivcu.string_to_numerical_id(full_symbol) for full_symbol in full_symbols
    ]
    # Get prod `MarketData`.
    market_data = dtfamsysc.get_Cx_RealTimeMarketData_prod_instance1(asset_ids)
    return market_data


def load_ohlcv_data_from_historical_datasource(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    universe_version: str,
    apply_timing_fix: bool,
) -> pd.DataFrame:
    """
    Load OHLCV data using the prod-like `HistoricalDataSource`.

    :param universe_version: universe version
    :param apply_timing_fix: apply the timing fix if True, otherwise read data as-is
    """
    nid = "read_data"
    market_data = _get_prod_market_data(universe_version)
    ts_col_name = "end_timestamp"
    multiindex_output = True
    col_names_to_remove = None
    historical_data_source = dtfsys.HistoricalDataSource(
        nid,
        market_data,
        ts_col_name,
        multiindex_output,
        col_names_to_remove=col_names_to_remove,
    )
    if apply_timing_fix:
        # Subtract 1 minute to account for the fact that timestamp indicates the start
        # of the bar instead of the end of that.
        start_timestamp = start_timestamp - pd.Timedelta(minutes=1)
        end_timestamp = end_timestamp - pd.Timedelta(minutes=1)
    # Convert to the `dataflow` format.
    fit_intervals = [(start_timestamp, end_timestamp)]
    _LOG.info("fit_intervals=%s", fit_intervals)
    historical_data_source.set_fit_intervals(fit_intervals)
    df_ohlcv = historical_data_source.fit()["df_out"]
    if apply_timing_fix:
        # Add 1 minute back.
        df_ohlcv.index = df_ohlcv.index + pd.Timedelta(minutes=1)
        df_ohlcv["start_timestamp"] = df_ohlcv["start_timestamp"] + pd.Timedelta(
            minutes=1
        )
    return df_ohlcv


# %% [markdown]
# ## Without the timing fix

# %%
appy_timing_fix = False
historical_datasource_df = load_ohlcv_data_from_historical_datasource(
    start_timestamp_ET, end_timestamp_ET, universe_version, appy_timing_fix
)
_print_df_info(historical_datasource_df)
historical_datasource_df.head(3)

# %% [markdown]
# There is a timing issue when reading data from `HistoricalDataSource`.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    historical_datasource_df[columns_to_compare],
    dag_read_data_df_out[columns_to_compare],
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ## With the timing fix

# %%
appy_timing_fix = True
historical_datasource_df_with_fix = load_ohlcv_data_from_historical_datasource(
    start_timestamp_ET, end_timestamp_ET, universe_version, appy_timing_fix
)
_print_df_info(historical_datasource_df_with_fix)
historical_datasource_df_with_fix.head(3)

# %% [markdown]
# The data matches that from the prod DAG when the timing fix is applied.

# %%
columns_to_compare = ["open", "high", "low", "close", "volume"]
diff_df = hpandas.compare_dfs(
    historical_datasource_df_with_fix[columns_to_compare],
    dag_read_data_df_out[columns_to_compare],
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)

# %% [markdown]
# ## Resampled data with the timing fix

# %%
resampled_historical_datasource_df_with_fix = resample_ohlcv_bars(
    historical_datasource_df_with_fix, bar_duration
)
_print_df_info(resampled_historical_datasource_df_with_fix)
resampled_historical_datasource_df_with_fix.head(3)

# %% [markdown]
# The resampled data also matches that from the prod DAG when the timing fix is applied.

# %%
diff_df = hpandas.compare_dfs(
    resampled_historical_datasource_df_with_fix, dag_resample_df_out
)
total_abs_diff = diff_df.abs().sum().sum()
_LOG.info("The total absolute difference=%s", total_abs_diff)
