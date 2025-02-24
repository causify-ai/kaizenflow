# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %% run_control={"marked": true}
import logging
import time

import ccxt
import pandas as pd

import core.config.config_ as cconconf
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hsecrets as hsecret
import im_v2.ccxt.data.client as icdcl
import im_v2.ccxt.data.extract.exchange_class as imvcdeexcl

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %%
def get_cmtask1905_config_ccxt() -> cconconf.Config:
    """
    Get task1905-specific config.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = "ck"
    #
    config["load"]["data_dir"] = "s3://cryptokaizen-data/historical"
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["vendor"] = "CCXT"
    config["data"]["data_snapshot"] = "latest"
    config["data"]["version"] = "v3"
    config["data"]["resample_1min"] = True
    config["data"]["partition_mode"] = "by_year_month"
    config["data"]["start_ts"] = None
    config["data"]["end_ts"] = None
    config["data"]["columns"] = None
    config["data"]["filter_data_mode"] = "assert"
    return config


# %%
config = get_cmtask1905_config_ccxt()
print(config)


# %% [markdown]
# # Functions

# %%
def _get_ccxt_ohlcv_data(
    exchange: ccxt.Exchange,
    currency_pair: str,
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
) -> pd.DataFrame:
    """
    Get OHLCV data for a given exchange, currency pair and time period.
    """
    start_timestamp = start_timestamp.asm8.astype(int) // 1000000
    end_timestamp = end_timestamp.asm8.astype(int) // 1000000
    all_bars = []
    duration = exchange.parse_timeframe("1m") * 100
    for t in range(
        start_timestamp,
        end_timestamp + duration,
        duration * 500,
    ):
        bars = _get_ccxt_bar_data(currency_pair, t, exchange)
        all_bars.append(bars)
        time.sleep(1)
    all_data = pd.concat(all_bars)
    return all_data


def _get_ccxt_bar_data(
    currency_pair: str, since: "start timestamp", exchange: ccxt.Exchange
):
    """
    Get data for a single bar from CCXT.
    """
    ccxt_data = exchange.fetch_ohlcv(
        currency_pair, timeframe="1m", since=since, limit=500
    )
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    bars = pd.DataFrame(ccxt_data, columns=columns)
    return bars


def _get_data_for_year_month(
    df: pd.DataFrame, year: int, month: int
) -> pd.DataFrame:
    """
    :return: data for a specific year and month
    """
    df = df.loc[(df.index.year == year) & (df.index.month == month)]
    return df


def _get_data_with_volume_0(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute % of data points where volume = 0.

    :return: data with volume = 0.
    """
    df_volume_0 = df.loc[df["volume"] == 0]
    return df_volume_0


def _log_into_exchange(exchange: str) -> ccxt.Exchange:
    """
    Log into an exchange via CCXT and return the corresponding `ccxt.Exchange`
    object.
    """
    # Select credentials for provided exchange.
    credentials = hsecret.get_secret(exchange)
    # Enable rate limit.
    credentials["rateLimit"] = True
    exchange_class = getattr(ccxt, exchange)
    # Create a CCXT Exchange class object.
    exchange = exchange_class(credentials)
    hdbg.dassert(
        exchange.checkRequiredCredentials(),
        msg="Required credentials not passed",
    )
    return exchange


def _set_index_ts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert epoch column to timestamp index.
    """
    df["timestamp"] = df["timestamp"].apply(
        lambda x: hdateti.convert_unix_epoch_to_timestamp(x)
    )
    df = df.set_index("timestamp")
    return df


# %% [markdown]
# # CcxtHistoricalPqByTileClient

# %%
client = icdcl.CcxtHistoricalPqByTileClient(
    config["data"]["version"],
    config["data"]["resample_1min"],
    config["load"]["data_dir"],
    config["data"]["partition_mode"],
    aws_profile=config["load"]["aws_profile"],
)

# %%
universe = client.get_universe()
universe

# %% [markdown]
# # Binance::DOGE_USDT

# %%
full_symbol_binance = ["binance::DOGE_USDT"]
binance_data = client.read_data(
    full_symbol_binance,
    config["data"]["start_ts"],
    config["data"]["end_ts"],
    config["data"]["columns"],
    config["data"]["filter_data_mode"],
)

# %%
binance_2019_09 = _get_data_for_year_month(binance_data, 2019, 9)
binance_2019_09_volume_0 = _get_data_with_volume_0(binance_2019_09)
binance_2019_09.head(3)

# %%
binance_2019_09_volume_0.head(3)

# %% [markdown]
# # Extractor

# %%
ccxt_binance_DOGE_exchange = imvcdeexcl.CcxtExchange("binance")

# %%
currency_pair_binance = "DOGE/USDT"
start_timestamp = pd.Timestamp("2019-09-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2019-09-30 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_binance_DOGE = ccxt_binance_DOGE_exchange.download_ohlcv_data(
    currency_pair_binance,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_binance_DOGE = _set_index_ts(ccxt_binance_DOGE)
ccxt_binance_DOGE = _get_data_for_year_month(ccxt_binance_DOGE, 2019, 9)
ccxt_binance_DOGE_volume_0 = _get_data_with_volume_0(ccxt_binance_DOGE)
ccxt_binance_DOGE.head(3)

# %%
ccxt_binance_DOGE_volume_0.head(3)

# %% [markdown]
# # CCXT w/o Extractor

# %%
ccxt_exchange = _log_into_exchange("binance")
start_ts = pd.Timestamp("2019-09-01 00:00:00+00:00")
end_ts = pd.Timestamp("2019-09-30 23:59:59+00:00")
ccxt_df = _get_ccxt_ohlcv_data(
    ccxt_exchange, currency_pair_binance, start_ts, end_ts
)
ccxt_df = _set_index_ts(ccxt_df)
ccxt_df = _get_data_for_year_month(ccxt_df, 2019, 9)
ccxt_df_volume_0 = _get_data_with_volume_0(ccxt_df)
ccxt_df

# %%
ccxt_df_volume_0.head(3)

# %% [markdown]
# # Summary

# %% [markdown]
#
# |CCXT | | ||            Extractor    | | | |Client | | |
# |------|--|-||-------------|-|-|-|------|-|-|
# |date|Number of NaN rows %|    Total number of rows| `volume=0` %    |Number of NaN rows %|    Total number of rows| `volume=0` %| Number of NaN rows %|    Total number of rows| `volume=0` %|
# |2019-09|    0          |                       429750|          73.22%       |    0          |                       43200|          73.3%   |      0|                43200| 73.3%|
#

# %% [markdown]
# - The huge amount of data from CCXT is duplicated.
# - Where volume = 0, data from columns open, high, low, close is exactly the same as in the last row with `volume != 0`. It could mean that volume = 0 rows are NaNs at the source, so it could be the way exchange handles missing data.

# %% [markdown]
# # ftx::BTC_USDT

# %% [markdown]
# ## Client

# %%
full_symbol_ftx = ["ftx::BTC_USDT"]
ftx_data = client.read_data(
    full_symbol_ftx,
    config["data"]["start_ts"],
    config["data"]["end_ts"],
    config["data"]["columns"],
    config["data"]["filter_data_mode"],
)

# %%
ftx_2020_04 = _get_data_for_year_month(ftx_data, 2020, 4)
ftx_2020_04_volume_0 = _get_data_with_volume_0(ftx_2020_04)
ftx_2020_04.head(3)

# %%
ftx_2020_04_volume_0.head(3)

# %%
ftx_2020_04.loc[ftx_2020_04["open"].isna()]

# %% [markdown]
# ## Extractor

# %%
ccxt_ftx_BTC_exchange = imvcdeexcl.CcxtExchange("ftx")
currency_pair_ftx = "BTC/USDT"
start_timestamp = pd.Timestamp("2020-04-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2020-04-30 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_ftx_BTC = ccxt_ftx_BTC_exchange.download_ohlcv_data(
    currency_pair_ftx,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_ftx_BTC = _set_index_ts(ccxt_ftx_BTC)
ccxt_ftx_BTC = _get_data_for_year_month(ccxt_ftx_BTC, 2020, 4)
ccxt_ftx_BTC_volume_0 = _get_data_with_volume_0(ccxt_ftx_BTC)
ccxt_ftx_BTC.head(3)


# %%
ccxt_ftx_BTC_volume_0.loc[ccxt_ftx_BTC["high"] == 7493.50000000].head(3)

# %%
ccxt_ftx_BTC.loc[(ccxt_ftx_BTC.index.day == 25) & (ccxt_ftx_BTC.index.hour == 3)][
    30:43
]

# %% [markdown]
# ## CCXT w/o Extractor

# %%
ccxt_exchange_ftx = _log_into_exchange("ftx")
start_ts = pd.Timestamp("2020-04-01 00:00:00+00:00")
end_ts = pd.Timestamp("2020-04-30 23:59:59+00:00")
ccxt_df_ftx = _get_ccxt_ohlcv_data(
    ccxt_exchange_ftx, currency_pair_ftx, start_ts, end_ts
)
ccxt_df_ftx = _set_index_ts(ccxt_df_ftx)
ccxt_df_ftx = _get_data_for_year_month(ccxt_df_ftx, 2020, 4)
ccxt_df_ftx_volume_0 = _get_data_with_volume_0(ccxt_df_ftx)
print(len(ccxt_df_ftx.index.unique()))
display(ccxt_df_ftx.head(3))

# %% [markdown]
#
# |CCXT | | ||            Extractor    | | | |Client | | |
# |------|--|-||-------------|-|-|-|------|-|-|
# |date|Number of NaN rows %|    Total number of rows| `volume=0` %    |Number of NaN rows %|    Total number of rows| `volume=0` %| Number of NaN rows %|    Total number of rows| `volume=0` %|
# |2020-04|    0          |                       429750|          86.09%       |    0          |                       43200|          85.97%   |      0|                43200| 85.97%|
#

# %% [markdown]
# Values in `volume = 0` rows change and don't have the same pattern as binance.

# %% [markdown]
# # gateio::ETH_USDT w/o `volume = 0` in data

# %% [markdown]
# Data from `gateio` has NaN spikes in September, October and November in 2021.

# %% [markdown]
# ## Client

# %%
full_symbols_gateio = ["gateio::ETH_USDT", "gateio::ADA_USDT"]
gateio_data = client.read_data(
    [full_symbols_gateio[0]],
    config["data"]["start_ts"],
    config["data"]["end_ts"],
    config["data"]["columns"],
    config["data"]["filter_data_mode"],
)

# %% [markdown]
# ### October 2021 - 100% of `NaNs`

# %%
gateio_data_2021_10 = _get_data_for_year_month(gateio_data, 2021, 10)
gateio_data_2021_10.head(3)

# %%
gateio_data_2021_10.isna().value_counts()

# %% [markdown]
# ### 34.46% of `NaNs`

# %%
gateio_data_2021_09 = _get_data_for_year_month(gateio_data, 2021, 9)
gateio_data_2021_09.head(3)

# %%
gateio_data_2021_09.isna().value_counts()

# %% [markdown]
# ### No `NaNs`

# %%
gateio_data.loc[
    (gateio_data.index.year == 2021) & (gateio_data.index.month == 12)
].head(3)

# %% [markdown]
# ## Extractor

# %%
ccxt_gateio_exchange = imvcdeexcl.CcxtExchange("gateio")
currency_pair_gateio = ["ETH/USDT", "ADA/USDT"]
start_timestamp = pd.Timestamp("2021-09-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-09-30 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_gateio_ETH = ccxt_gateio_exchange.download_ohlcv_data(
    currency_pair_gateio[0],
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_gateio_ETH

# %%
start_timestamp = pd.Timestamp("2021-10-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-10-31 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_gateio_ETH_10 = ccxt_gateio_exchange.download_ohlcv_data(
    currency_pair_gateio[0],
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_gateio_ETH_10

# %%
start_timestamp = pd.Timestamp("2021-12-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-12-31 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_gateio_ETH_12 = ccxt_gateio_exchange.download_ohlcv_data(
    currency_pair_gateio[0],
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_gateio_ETH_12

# %% [markdown]
# Empty datasets are returned for the dates earlier than December 2021. Probably data is accessible only for a certain amount of time, e.g., 1 year.

# %%
# Load recent data to make sure API and Exctractor are working.
start_timestamp = pd.Timestamp("2022-04-25 00:00:00+00:00")
end_timestamp = pd.Timestamp("2022-05-14 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_gateio_ETH_2022 = ccxt_gateio_exchange.download_ohlcv_data(
    currency_pair_gateio[0],
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_gateio_ETH_2022.head(3)

# %% [markdown]
# ## CCXT w/o Extractor

# %% [markdown]
# Empty data is also returned from CCXT directly which means that the problem is at source.

# %%
ccxt_exchange = _log_into_exchange("gateio")
start_ts = pd.Timestamp("2021-09-01 00:00:00+00:00")
end_ts = pd.Timestamp("2021-09-30 23:59:59+00:00")
ccxt_df = _get_ccxt_ohlcv_data(
    ccxt_exchange, currency_pair_gateio[0], start_ts, end_ts
)
ccxt_df

# %% [markdown]
# ### Summary for `gateio` `volume != 0` data.

# %% [markdown]
# - Data before January 2022 is not accessible from `gateio` via CCXT
# - There are spikes of NaNs in September, October, November 2021 that are common for all coins

# %% [markdown]
# # gateio::ADA_USDT with `volume = 0` in data

# %% [markdown]
# ## Client

# %%
gateio_ADA_data = client.read_data(
    [full_symbols_gateio[1]],
    config["data"]["start_ts"],
    config["data"]["end_ts"],
    config["data"]["columns"],
    config["data"]["filter_data_mode"],
)

# %%
gateio_ADA_data_2021_09 = _get_data_for_year_month(gateio_ADA_data, 2021, 9)
gateio_ADA_data_2021_09_volume_0 = _get_data_with_volume_0(
    gateio_ADA_data_2021_09
)
gateio_ADA_data_2021_09.head(3)

# %%
gateio_ADA_data_2021_09_volume_0

# %%
gateio_ADA_data_2021_09.loc[
    (gateio_ADA_data_2021_09.index.day == 5)
    & (gateio_ADA_data_2021_09.index.hour == 3)
].tail(3)

# %%
# `volume = 0` has the same % as bad data
gateio_ADA_data_2021_07 = _get_data_for_year_month(gateio_ADA_data, 2021, 7)
gateio_ADA_data_2021_07_volume_0 = _get_data_with_volume_0(
    gateio_ADA_data_2021_07
)
gateio_ADA_data_2021_07.head(3)

# %%
gateio_ADA_data_2021_07_volume_0[:10]

# %%
gateio_ADA_data_2021_07.loc[
    gateio_ADA_data_2021_07.index >= "2021-07-03 09:20:00+00:00"
].head(10)

# %% [markdown]
# The pattern is: all values in price-related columns with `volume = 0` are the same as the value of `close` of the last row where `volume != 0`.

# %% [markdown]
# ## Extractor

# %%
start_timestamp = pd.Timestamp("2021-07-01 00:00:00+00:00")
end_timestamp = pd.Timestamp("2021-07-31 23:59:59+00:00")
sleep_time_in_secs = 1
ccxt_gateio_ADA = ccxt_gateio_exchange.download_ohlcv_data(
    currency_pair_gateio[1],
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    sleep_time_in_secs=sleep_time_in_secs,
)

# %%
ccxt_gateio_ADA

# %% [markdown]
# ## Summary for `gateio`

# %% [markdown]
# - Empty data is returned from CCXT and Extractor directly which means that the problem is at source.
# - The pattern is: all values in price-related columns with `volume = 0` are the same as the value of `close` of the last row where `volume != 0`.
# - Data before January 2022 is not accessible from `gateio` via CCXT
# - There are spikes of NaNs in September, October, November 2021 that are common for all coins
