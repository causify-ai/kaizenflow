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
import logging

import ccxt
import pandas as pd

import core.config as cconfig
import core.plotting as coplotti
import dataflow_amp.system.Cx.utils as dtfasycxut
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.data.qa.dataset_validator as imvcdqdava
import im_v2.common.data.qa.qa_check as imvcdqqach
import im_v2.common.universe.universe as imvcounun
import research_amp.cc.qa as ramccqa

# %%
# adhoc to get latest CCXT version.
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install --upgrade ccxt)"

# %%
ccxt.__version__

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
config_dict = {
    "stage": "preprod",
    "start_timestamp": "2023-12-01T00:00:00+00:00",
    "end_timestamp": "2024-01-01T00:00:00+00:00",
    "aws_profile": "ck",
    "dataset_signature": "periodic_daily.airflow.downloaded_200ms.postgres.bid_ask.futures.v7_3.ccxt.binance.v1_0_0",
    "bid_ask_accuracy": 1,
    "data_type": "bid_ask",
    "bid_ask_depth": 1,
    "bid_ask_frequency_sec": "1T",
}
config = cconfig.Config.from_dict(config_dict)
print(config)

# %% [markdown]
# # Overlap of Symbols with Binance

# %%
vendor_name = "CCXT"
mode = "download"
version = "v7.4"
universe = imvcounun.get_vendor_universe(vendor_name, mode, version=version)
universe_list = universe["binance"]
len(universe_list)
universe_list

# %% run_control={"marked": true}
cryptocom_exchange = ccxt.cryptocom()
cryptocom_market_info = pd.DataFrame.from_dict(
    cryptocom_exchange.load_markets(), orient="index"
)
cryptocom_symbols = cryptocom_exchange.symbols
print(len(cryptocom_symbols))

# %%
binance_exchange = ccxt.binance()
binance_market_info = pd.DataFrame.from_dict(
    binance_exchange.load_markets(), orient="index"
)
binance_symbols = binance_exchange.symbols
print(len(binance_symbols))

# %%
intersection_result = set(cryptocom_symbols).intersection(binance_symbols)
print(len(intersection_result))

# %%
crypto_spot_symbols = cryptocom_market_info[cryptocom_market_info["spot"] == True]
binance_spot_symbols = binance_market_info[binance_market_info["spot"] == True]
print("Crypto.com spot symbols:", len(crypto_spot_symbols))
print("Binance spot symbols:", len(binance_spot_symbols))

# %%
crypto_future_symbols = cryptocom_market_info[
    cryptocom_market_info["swap"] == True
]
binance_future_symbols = binance_market_info[binance_market_info["swap"] == True]
print("Crypto.com futures symbols:", len(crypto_future_symbols))
print("Binance futures symbols:", len(binance_future_symbols))
crypto_future_symbols.head()
# binance_future_symbols

# %% [markdown]
# # Historical Data QA

# %%
pd.DataFrame(
    cryptocom_exchange.fetch_ohlcv("BTC/USDT", "1m", since=0, limit=1000)
).head()


# %%
def _download_OHLCV_data(
    start_time: str,
    end_time: str,
    symbol: str,
    *,
    time_frame: str = "1m",
    count: int = 300,
) -> pd.DataFrame():
    start_time = hdateti.convert_timestamp_to_unix_epoch(pd.Timestamp(start_time))
    end_time = hdateti.convert_timestamp_to_unix_epoch(
        pd.Timestamp(end_time) + pd.Timedelta(minutes=1)
    )
    data = pd.DataFrame()
    while end_time != start_time:
        ohlcv = pd.DataFrame(
            cryptocom_exchange.fetchOHLCV(
                symbol,
                time_frame,
                params={
                    "start_ts": start_time,
                    "end_ts": end_time,
                    "count": count,
                },
            )
        )
        if end_time != ohlcv.iloc[0, 0]:
            data = pd.concat([ohlcv, data], ignore_index=True)
            end_time = ohlcv.iloc[0, 0]
    data.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    data["currency_pair"] = symbol
    return data


# %%
data = pd.DataFrame()
universe_list = [
    "ETH_USDT",  # Symbols from universe 7.4
    "BTC_USDT",
    "SAND_USDT",
    "STORJ_USDT",
    "GMT_USDT",
    "AVAX_USDT",
    #                  'BNB_USDT', not in the market
    "APE_USDT",
    "MATIC_USDT",
    "DYDX_USDT",
    "DOT_USDT",
    #                  'UNFI_USDT', not in the market
    "LINK_USDT",
    "XRP_USDT",
    "CRV_USDT",
    "RUNE_USDT",
    #                  'BAKE_USDT', not in the market
    "NEAR_USDT",
    "FTM_USDT",
    "WAVES_USDT",
    "AXS_USDT",
    "OGN_USDT",
    "DOGE_USDT",
    "SOL_USDT",
]
#                  'CTK_USDT'] not in the market
for symbol in universe_list:
    ohlcv = _download_OHLCV_data(
        config["start_timestamp"],
        config["end_timestamp"],
        symbol,
    )
    data = pd.concat([ohlcv, data], ignore_index=True)
data

# %%
qa_check_list = [
    imvcdqqach.GapsInTimeIntervalBySymbolsCheck(
        config["start_timestamp"], config["end_timestamp"], "1T"
    ),
    imvcdqqach.NaNChecks(),
    imvcdqqach.OhlcvLogicalValuesCheck(),
]

# %%
dataset_validator = imvcdqdava.DataFrameDatasetValidator(qa_check_list)

# %%
try:
    dataset_validator.run_all_checks([data])
except Exception as e:
    # Pass information about success or failure of the QA
    #  back to the task that invoked it.
    data_qa_outcome = str(e)
    raise e
# If no exception was raised mark the QA as successful.
data_qa_outcome = "SUCCESS"

# %%
hpandas.df_to_str(data, num_rows=5, log_level=logging.INFO)

# %%
data2 = data.copy(deep=True)
data2 = data2.reset_index()
data2["normal_timestamp"] = pd.to_datetime(data2["timestamp"], unit="ms")
data2.set_index("normal_timestamp", inplace=True)
cry_data = data2.copy(deep=True)
data2


# %%
def convert_to_multiindex(df: pd.DataFrame, asset_id_col: str) -> pd.DataFrame:
    """
    Transform a df like: ```

    :                            id close  volume
    end_time
    2022-01-04 09:01:00-05:00  13684    NaN       0
    2022-01-04 09:01:00-05:00  17085    NaN       0
    2022-01-04 09:02:00-05:00  13684    NaN       0
    2022-01-04 09:02:00-05:00  17085    NaN       0
    2022-01-04 09:03:00-05:00  13684    NaN       0
    ```

    Return a df like:
    ```
                                    close       volume
                              13684 17085  13684 17085
    end_time
    2022-01-04 09:01:00-05:00   NaN   NaN      0     0
    2022-01-04 09:02:00-05:00   NaN   NaN      0     0
    2022-01-04 09:03:00-05:00   NaN   NaN      0     0
    2022-01-04 09:04:00-05:00   NaN   NaN      0     0
    ```

    Note that the `asset_id` column is removed.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_lte(1, df.shape[0])
    # Copied from `_load_multiple_instrument_data()`.
    _LOG.debug(
        "Before multiindex conversion:\n%s",
        hpandas.df_to_str(df.head()),
    )
    # Remove duplicates if any.
    df = hpandas.drop_duplicated(df, subset=[asset_id_col])
    #
    dfs = {}
    # TODO(Paul): Pass the column name through the constructor, so we can make it
    #  programmable.
    hdbg.dassert_in(asset_id_col, df.columns)
    #     hpandas.dassert_series_type_is(df[asset_id_col], np.int64)
    for asset_id, df in df.groupby(asset_id_col):
        hpandas.dassert_strictly_increasing_index(df)
        #
        hdbg.dassert_not_in(asset_id, dfs.keys())
        dfs[asset_id] = df
    # Reorganize the data into the desired format.
    _LOG.debug("keys=%s", str(dfs.keys()))
    df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
    df = df.swaplevel(i=0, j=1, axis=1)
    df.sort_index(axis=1, level=0, inplace=True)
    # Remove the asset_id column, since it's redundant.
    del df[asset_id_col]
    _LOG.debug(
        "After multiindex conversion:\n%s",
        hpandas.df_to_str(df.head()),
    )
    return df


# %%
df = convert_to_multiindex(data2, "currency_pair")
df

# %%
resampled_data = dtfasycxut.resample_ohlcv_data(df, "1T")
resampled_data

# %%
volume_notional = resampled_data["volume"] * resampled_data["close"]
volume_notional

# %%
# Compute mean daily notional volume.
mdv_notional = volume_notional.resample("D").sum().mean()
mdv_notional = mdv_notional.sort_values().round(2)
mdv_notional.name = "mdv_notional"
mdv_notional

# %%
coplotti.plot_barplot(
    mdv_notional,
    annotation_mode="pct",
    orientation="horizontal",
    figsize=[20, 50],
    yscale="log",
)

# %%
cry_data.rename(columns={"currency_pair": "full_symbol"}, inplace=True)
cry_timestamp_stats = ramccqa.get_timestamp_stats(cry_data, vendor_name)
cry_timestamp_stats

# %%
agg_level_full_symbol = ["full_symbol"]
cry_bad_data_stats = ramccqa.get_bad_data_stats(
    cry_data, agg_level_full_symbol, vendor_name
)
cry_bad_data_stats

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
cry_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    cry_data, agg_level_full_symbol_year_month, vendor_name
)
cry_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    cry_bad_data_stats_by_year_month, 30
)

# %% [markdown]
# # Perpetual Symbols Analysis

# %%
perp_data = pd.DataFrame()
universe_list = [
    "ETH/USD:USD",  # Symbols from universe 7.4
    "BTC/USD:USD",
    "SAND/USD:USD",
    "STORJ/USD:USD",
    "GMT/USD:USD",
    "AVAX/USD:USD",
    #                  'BNB_USDT', not in the market
    "APE/USD:USD",
    "MATIC/USD:USD",
    "DYDX/USD:USD",
    "DOT/USD:USD",
    #                  'UNFI_USDT', not in the market
    "LINK/USD:USD",
    "XRP/USD:USD",
    "CRV/USD:USD",
    "RUNE/USD:USD",
    #                  'BAKE_USDT', not in the market
    "NEAR/USD:USD",
    "FTM/USD:USD",
    "WAVES/USD:USD",
    "AXS/USD:USD",
    "OGN/USD:USD",
    "DOGE/USD:USD",
    "SOL/USD:USD",
]
#                  'CTK_USDT'] not in the market
for symbol in universe_list:
    ohlcv = _download_OHLCV_data(
        config["start_timestamp"],
        config["end_timestamp"],
        symbol,
    )
    perp_data = pd.concat([ohlcv, perp_data], ignore_index=True)
perp_data

# %%
try:
    dataset_validator.run_all_checks([perp_data])
except Exception as e:
    # Pass information about success or failure of the QA
    #  back to the task that invoked it.
    data_qa_outcome = str(e)
    raise e
# If no exception was raised mark the QA as successful.
data_qa_outcome = "SUCCESS"

# %%
perp_data2 = perp_data.copy(deep=True)
perp_data2 = perp_data2.reset_index()
perp_data2["normal_timestamp"] = pd.to_datetime(
    perp_data2["timestamp"], unit="ms"
)
perp_data2.set_index("normal_timestamp", inplace=True)
perp_cry_data = perp_data2.copy(deep=True)
perp_data2

# %%
perp_df = convert_to_multiindex(perp_data2, "currency_pair")
perp_df

# %%
resampled_perp_data = dtfasycxut.resample_ohlcv_data(perp_df, "1T")
resampled_perp_data

# %%
volume_notional = resampled_perp_data["volume"] * resampled_perp_data["close"]
volume_notional

# %%
# Compute mean daily notional volume.
mdv_notional = volume_notional.resample("D").sum().mean()
mdv_notional = mdv_notional.sort_values().round(2)
mdv_notional.name = "mdv_notional"
mdv_notional

# %%
coplotti.plot_barplot(
    mdv_notional,
    annotation_mode="pct",
    orientation="horizontal",
    figsize=[20, 50],
    yscale="log",
)

# %%
perp_cry_data.rename(columns={"currency_pair": "full_symbol"}, inplace=True)
cry_timestamp_stats = ramccqa.get_timestamp_stats(perp_cry_data, vendor_name)
cry_timestamp_stats

# %%
agg_level_full_symbol = ["full_symbol"]
cry_bad_data_stats = ramccqa.get_bad_data_stats(
    perp_cry_data, agg_level_full_symbol, vendor_name
)
cry_bad_data_stats

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
cry_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    perp_cry_data, agg_level_full_symbol_year_month, vendor_name
)
cry_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    cry_bad_data_stats_by_year_month, 30
)

# %% [markdown]
# # Cryptocom orderbook history data availability

# %%
perp_data_hist = pd.DataFrame()
universe_list = [  # Symbols from universe 7.4
    "ETH/USD:USD",  # 2021/03/09
    "BTC/USD:USD",  # 2021/03/09
    "SAND/USD:USD",  # 2021/12
    "STORJ/USD:USD",  # 2022/02
    "GMT/USD:USD",  # 2022/05
    "AVAX/USD:USD",  # 2021/09
    "APE/USD:USD",  # 2022/05
    "MATIC/USD:USD",  # 2021/07
    "DYDX/USD:USD",  # 2021/10
    "DOT/USD:USD",  # 2021/04
    "LINK/USD:USD",  # 2021/05
    "XRP/USD:USD",  # 2021/07
    "CRV/USD:USD",  # 2021/07
    "RUNE/USD:USD",  # 2021/12
    "NEAR/USD:USD",  # 2021/10
    "FTM/USD:USD",  # 2021/10
    "WAVES/USD:USD",  # 2022/02
    "AXS/USD:USD",  # 2021/08
    "OGN/USD:USD",  # 2022/05
    "DOGE/USD:USD",  # 2021/05
    "SOL/USD:USD",  # 2021/07
]
for symbol in universe_list:
    ohlcv = _download_OHLCV_data(
        "2022-05-01T01:00:00+00:00",
        "2022-05-01T03:00:00+00:00",
        symbol,
    )
    print("Completed data collection for ", symbol)
    perp_data_hist = pd.concat([ohlcv, perp_data_hist], ignore_index=True)
perp_data_hist

# %%
