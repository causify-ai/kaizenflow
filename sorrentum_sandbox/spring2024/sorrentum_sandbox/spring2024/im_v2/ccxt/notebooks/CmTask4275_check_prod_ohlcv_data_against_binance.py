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
# The goal is to compare OHLCV data from the prod DB that the prod DAG sees with that from the Binance terminal.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline


import logging

import pandas as pd

import dataflow.core as dtfcore
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
import im_v2.common.data.client.im_raw_data_client as imvcdcimrdc
import im_v2.common.db.db_utils as imvcddbut
import im_v2.common.universe as ivcu
import im_v2.common.universe.universe_utils as imvcuunut
import market_data as mdata

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Compare OHLCV data (prod CK vs Binance)

# %%
def get_ccxt_prod_market_data(universe_version: str) -> mdata.MarketData:
    """
    Get `MarketData` backed by the production DB.

    :param universe_version: universe version, e.g., "v7.1"
    """
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
    universe_version = "infer_from_data"
    # Get DB connection.
    db_connection = imvcddbut.DbConnectionManager.get_connection("prod")
    # Get the real-time `ImClient`.
    table_name = "ccxt_ohlcv_futures"
    resample_1min = False
    im_client = imvcdccccl.CcxtSqlRealTimeImClient(
        universe_version, db_connection, table_name, resample_1min=resample_1min
    )
    # Get the real-time `MarketData`.
    market_data, _ = mdata.get_RealTimeImClientMarketData_example1(
        im_client, asset_ids
    )
    return market_data


def load_btc_market_data(
    market_data: mdata.MarketData,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    apply_timing_fix: bool,
) -> pd.DataFrame:
    """
    Load OHLCV data for BTC_USDT perpetual futures.

    :param market_data: `MarketData` backed by the production DB
    :param start_ts: start of the interval of interest
    :param end_ts: end of the interval of interest
    :param apply_timing_fix: convert timestamp from the start of a bar
        to the end of a bar if True otherwise pass
    :return: OHLCV data for BTC_USDT
    """
    if apply_timing_fix:
        start_ts = start_ts - pd.Timedelta(minutes=1)
        end_ts = end_ts - pd.Timedelta(minutes=1)
    timestamp_col_name = "timestamp"
    asset_ids = None
    df = market_data.get_data_for_interval(
        start_ts, end_ts, timestamp_col_name, asset_ids
    )
    if apply_timing_fix:
        df.index = df.index + pd.Timedelta(minutes=1)
    # Convert to Binance timezone.
    df.index = df.index.tz_convert("UTC")
    # Keep only BTC_USDT as an example.
    df_btc = df[df["full_symbol"] == "binance::BTC_USDT"]
    return df_btc


# %% run_control={"marked": true}
# Get the `MarketData` backed by the prod DB.
universe_version = "v7.1"
prod_market_data = get_ccxt_prod_market_data(universe_version)

# %% [markdown]
# Get binance OHLCV data from https://www.binance.com/en/futures/BTCUSDT. The timestamp is in UTC+4 timezone.
#
# ![image.png](attachment:image.png)

# %% [markdown]
# CK OHLCV data without the timing fix matches that from the Binance terminal.

# %%
start_ts = pd.Timestamp("2023-05-08 14:13:00+00:00")
end_ts = pd.Timestamp("2023-05-08 14:14:00+00:00")
apply_timing_fix = False
btc_ohlcv_data = load_btc_market_data(
    prod_market_data, start_ts, end_ts, apply_timing_fix
)
btc_ohlcv_data

# %% [markdown]
# To account for the fact that:
# - Binance timestamp is the start of a 1-minute bar
# - CK timestamp is the end of 1-minute bar
#
# We should apply the timing fix such that data timestamp 14:13 (start of the bar) becomes 14:14 (end of the bar).

# %%
start_ts = pd.Timestamp("2023-05-08 14:13:00+00:00")
end_ts = pd.Timestamp("2023-05-08 14:15:00+00:00")
apply_timing_fix = True
btc_ohlcv_data_with_timing_fix = load_btc_market_data(
    prod_market_data, start_ts, end_ts, apply_timing_fix
)
btc_ohlcv_data_with_timing_fix

# %% [markdown]
# # Check DAG prices vs binance prices

# %% [markdown]
# As one can see: DAG prices are binance prices shifted 1 minute forward which confirms that all works as it should.

# %% [markdown]
# ## DAG prices

# %%
# Paper trading system run with the timing issue fix.
dag_dir = "/shared_data/ecs/preprod/system_reconciliation/C3a/20230511/system_log_dir.scheduled.20230511_131000.20230512_130500/dag/node_io/node_io.data"
node_name = "predict.0.read_data"
bar_timestamp = pd.Timestamp("2023-05-12 06:40:00")
df = dtfcore.get_dag_node_output(dag_dir, node_name, bar_timestamp)
df.tail(5)["close"]

# %% [markdown]
# ## Binance prices as-is from the `RawDataReader`

# %%
# Get the prod universe as `full_symbols`.
universe_version = "v7.1"
vendor = "CCXT"
mode = "trade"
as_full_symbol = True
full_symbols = ivcu.get_vendor_universe(
    vendor,
    mode,
    version=universe_version,
    as_full_symbol=as_full_symbol,
)

# %%
# Use real-time data from the prod DB.
signature = "periodic_daily.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0"
start_timestamp = pd.Timestamp("2023-05-12 06:36:00-04:00")
end_timestamp = pd.Timestamp("2023-05-12 06:40:00-04:00")
reader = imvcdcimrdc.RawDataReader(signature)
ohlcv = reader.read_data(start_timestamp, end_timestamp)
ohlcv["timestamp"] = ohlcv["timestamp"].apply(
    hdateti.convert_unix_epoch_to_timestamp
)
# Set as an index.
ohlcv = ohlcv.set_index("timestamp")
#
ohlcv["full_symbol"] = ohlcv["exchange_id"] + "::" + ohlcv["currency_pair"]
# Keep only the assets that belong to the prod universe.
ohlcv = ohlcv[ohlcv["full_symbol"].isin(full_symbols)]
# Add `asset_id` column.
ohlcv_currency_pairs = ohlcv["full_symbol"].unique()
ohlcv_asset_id_to_full_symbol = imvcuunut.build_numerical_to_string_id_mapping(
    ohlcv_currency_pairs
)
ohlcv_full_symbol_to_asset_id = {
    v: k for k, v in ohlcv_asset_id_to_full_symbol.items()
}
ohlcv["asset_id"] = ohlcv["full_symbol"].apply(
    lambda x: ohlcv_full_symbol_to_asset_id[x]
)
normalized_ohlcv = ohlcv.pivot(
    columns="asset_id",
    values=["open", "high", "low", "close", "volume"],
)
normalized_ohlcv["close"]
