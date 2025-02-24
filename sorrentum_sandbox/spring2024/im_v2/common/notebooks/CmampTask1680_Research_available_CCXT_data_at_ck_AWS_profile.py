# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import logging
import os

import pandas as pd

import core.config.config_ as cconconf
import core.statistics as cstats
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hparquet as hparque
import helpers.hprint as hprint
import im_v2.ccxt.data.client as icdcl
import research_amp.cc.statistics as ramccsta

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs

# %%
def get_cmtask1680_config_ccxt() -> cconconf.Config:
    """
    Get task1680-specific config.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = "ck"
    # TODO(Nina): @all replace `s3://cryptokaizen-data` with `get_s3_bucket()` after #1667 is implemented.
    config["load"]["data_dir"] = os.path.join(
        "s3://cryptokaizen-data",
        "historical",
    )
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["vendor"] = "CCXT"
    config["data"]["data_snapshot"] = "latest"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["close_price"] = "close"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange_id"] = "exchange_id"
    return config


# %%
config = get_cmtask1680_config_ccxt()
print(config)


# %% [markdown]
# # Functions

# %%
# TODO(Nina): @all Use functions from `research_amp.cc.statistics` instead.
def compute_stats_per_currency_pair(currency_pair_list: list) -> pd.DataFrame:
    """
    For each currency pair in the list compute stats.

    Statistics include:
       - minimum timestamp
       - maximum timestamp
       - the number of data points
       - days of data available
       - coverage, i.e. the number of not NaN data points divided
         by the number of all data points as percentage
       - average data points per day

    :param currency_pair_list: list of currency pairs to compute stats for.
    """
    res = {}
    # Iterate over currency pairs.
    for currency_pair in currency_pair_list:
        data_currency_pair = data.loc[data["currency_pair"] == currency_pair]
        # Compute the number of days available.
        days_availiable = (
            data_currency_pair.last_valid_index()
            - data_currency_pair.first_valid_index()
        ).days
        # Compute the number of data points.
        n_data_points = data_currency_pair.close.count()
        # Compute data coverage.
        coverage = 100 * (1 - cstats.compute_frac_nan(data_currency_pair.close))
        # Combine the stats in a single dict.
        res.update(
            {
                currency_pair: [
                    data_currency_pair.index.min(),
                    data_currency_pair.index.max(),
                    n_data_points,
                    coverage,
                    days_availiable,
                    n_data_points / days_availiable,
                ]
            }
        )
        # Covert into a DataFrame.
        df_res = pd.DataFrame(
            data=res.values(),
            columns=[
                "min_ts",
                "max_ts",
                "n_data_points",
                "coverage",
                "days_available",
                "avg_data_points_per_day",
            ],
            index=res.keys(),
        )
    return df_res


def get_file_path_for_exchange(config: cconconf.Config, exchange: str) -> str:
    """
    Get file path for exchange-specific data.

    E.g., `"s3://cryptokaizen-data/historical/ccxt/latest/binance/"`.
    """
    data_dir = config["load"]["data_dir"]
    vendor = config["data"]["vendor"].lower()
    data_snapshot = config["data"]["data_snapshot"]
    file_path = os.path.join(data_dir, vendor, data_snapshot, exchange)
    return file_path


# %% [markdown]
# # Load CCXT data from the historical bucket

# %% [markdown]
# ## binance stats

# %%
# TODO(Nina): @all Usage of the client is very slow due to CMTask1726.
#  Until this issue is fixed, you can speed up the client by replacing `apply`
#  with the vectorasied counterpart: `df['exchange_id'] + "::" + df['currency_pair']`.
universe_version = "v3"
resample_1min = True
ccxt_historical_client = icdcl.ccxt_clients.CcxtHistoricalPqByTileClient(
    universe_version,
    resample_1min,
    config["load"]["data_dir"],
    "by_year_month",
    aws_profile=config["load"]["aws_profile"],
)

# %%
universe = ccxt_historical_client.get_universe()
universe

# %%
# TODO(Nina): @all Kernel's dead after trying to load data for the whole universe due to CMTask1726.
# Load all the data available for the 1st full symbol in the universe.
start_ts = None
end_ts = None
data = ccxt_historical_client.read_data([universe[0]], start_ts, end_ts)

# %%
_LOG.info(data.shape)
data.head(3)

# %%
# TODO(Nina): @all Refactor functions from `research_amp.cc.statistics` to properly work with
# `ImClient` data.
compute_start_end_stats = ramccsta.compute_start_end_stats(data, config)
compute_start_end_stats

# %%
# TODO(Nina): @all all exchange ids in a bucket could be extracted via `listdir()` from `helpers.hs3`.
binance_exchange = "binance"
file_path = get_file_path_for_exchange(config, binance_exchange)
data = hparque.from_parquet(file_path, aws_profile=config["load"]["aws_profile"])
_LOG.info(data.shape)
data.head(3)

# %%
currency_pairs = list(data["currency_pair"].unique())
dfb = compute_stats_per_currency_pair(currency_pairs)
dfb["exchange_id"] = binance_exchange
dfb["vendor"] = config["data"]["vendor"]
dfb

# %% [markdown]
# ## bitfinex stats

# %%
bitfinex_exchange = "bitfinex"
file_path = get_file_path_for_exchange(config, bitfinex_exchange)
data = hparque.from_parquet(file_path, aws_profile=config["load"]["aws_profile"])
_LOG.info(data.shape)
data.head(3)

# %%
currency_pairs = list(data["currency_pair"].unique())
dfb = compute_stats_per_currency_pair(currency_pairs)
dfb["exchange_id"] = bitfinex_exchange
dfb["vendor"] = config["data"]["vendor"]
dfb

# %% [markdown]
# ## ftx stats

# %%
ftx_exchange = "ftx"
file_path = get_file_path_for_exchange(config, ftx_exchange)
data = hparque.from_parquet(file_path, aws_profile=config["load"]["aws_profile"])
_LOG.info(data.shape)
data.head(3)

# %%
currency_pairs = list(data["currency_pair"].unique())
dfb = compute_stats_per_currency_pair(currency_pairs)
dfb["exchange_id"] = ftx_exchange
dfb["vendor"] = config["data"]["vendor"]
dfb

# %% [markdown]
# ## gateio stats

# %%
gateio_exchange = "gateio"
file_path = get_file_path_for_exchange(config, gateio_exchange)
data = hparque.from_parquet(file_path, aws_profile=config["load"]["aws_profile"])
_LOG.info(data.shape)
data.head(3)

# %%
currency_pairs = list(data["currency_pair"].unique())
dfb = compute_stats_per_currency_pair(currency_pairs)
dfb["exchange_id"] = gateio_exchange
dfb["vendor"] = config["data"]["vendor"]
dfb

# %% [markdown]
# ## kucoin stat

# %%
kucoin_exchange = "kucoin"
file_path = get_file_path_for_exchange(config, kucoin_exchange)
data = hparque.from_parquet(file_path, aws_profile=config["load"]["aws_profile"])
_LOG.info(data.shape)
data.head(3)

# %%
currency_pairs = list(data["currency_pair"].unique())
dfb = compute_stats_per_currency_pair(currency_pairs)
dfb["exchange_id"] = kucoin_exchange
dfb["vendor"] = config["data"]["vendor"]
dfb

# %%
# See the stats for buckets `cryptokaizen-data2/historical/` and `cryptokaizen-data/daily_staged`,
# we decided not to include them in the analysis at the moment. Feel free to remove if it is not
# needed.

# %% [markdown]
# # Load CCXT data from data2 bucket

# %%
# def read_exchange_df(paths: list) -> pd.DataFrame:
#     """
#     Read csv files from `s3://cryptokaizen-data2/historical/ and convert it to
#     a DataFrame.
#     """
#     all_data = []
#     for currency_pair, path in paths:
#         data = hpandas.read_csv_to_df(path)
#         data["currency_pair"] = currency_pair
#         all_data.append(data)
#     df = pd.concat(all_data)
#     return df

# %% [markdown]
# ## binance stat

# %%
# paths = [
#     (
#         "ADA_USDT",
#         "s3://cryptokaizen-data2/historical/binance/ADA_USDT_20220210-104334.csv",
#     ),
#     (
#         "AVAX_USDT",
#         "s3://cryptokaizen-data2/historical/binance/AVAX_USDT_20220210-105623.csv",
#     ),
#     (
#         "BNB_USDT",
#         "s3://cryptokaizen-data2/historical/binance/BNB_USDT_20220210-110910.csv",
#     ),
#     (
#         "BTC_USDT",
#         "s3://cryptokaizen-data2/historical/binance/BTC_USDT_20220210-112208.csv",
#     ),
#     (
#         "DOGE_USDT",
#         "s3://cryptokaizen-data2/historical/binance/DOGE_USDT_20220210-113502.csv",
#     ),
#     (
#         "EOS_USDT",
#         "s3://cryptokaizen-data2/historical/binance/EOS_USDT_20220210-114748.csv",
#     ),
#     (
#         "ETH_USDT",
#         "s3://cryptokaizen-data2/historical/binance/ETH_USDT_20220210-120031.csv",
#     ),
#     (
#         "LINK_USDT",
#         "s3://cryptokaizen-data2/historical/binance/LINK_USDT_20220210-121311.csv",
#     ),
#     (
#         "SOL_USDT",
#         "s3://cryptokaizen-data2/historical/binance/SOL_USDT_20220210-122551.csv",
#     ),
# ]
# data = read_exchange_df(paths)
# data.head()

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.max())

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.min())

# %% [markdown]
# ## bitfinex stat

# %%
# paths = [
#     (
#         "ADA_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/ADA_USDT_20220211-161045.csv",
#     ),
#     (
#         "AVAX_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/AVAX_USDT_20220211-161212.csv",
#     ),
#     (
#         "BTC_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/BTC_USDT_20220211-161338.csv",
#     ),
#     (
#         "DOGE_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/DOGE_USDT_20220211-161507.csv",
#     ),
#     (
#         "EOS_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/EOS_USDT_20220211-161634.csv",
#     ),
#     (
#         "ETH_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/ETH_USDT_20220211-161801.csv",
#     ),
#     (
#         "FIL_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/FIL_USDT_20220211-161926.csv",
#     ),
#     (
#         "LINK_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/LINK_USDT_20220211-162053.csv",
#     ),
#     (
#         "SOL_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/SOL_USDT_20220211-162219.csv",
#     ),
#     (
#         "XRP_USDT",
#         "s3://cryptokaizen-data2/historical/bitfinex/XRP_USDT_20220211-162345.csv",
#     ),
# ]
# data = read_exchange_df(paths)
# data.head()

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.max())

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.min())

# %% [markdown]
# ## ftx stat

# %%
# paths = [
#     (
#         "BNB_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/BNB_USDT_20220210-104642.csv",
#     ),
#     (
#         "BNB_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/BNB_USDT_20220210-123958.csv",
#     ),
#     (
#         "BTC_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/BTC_USDT_20220210-110047.csv",
#     ),
#     (
#         "BTC_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/BTC_USDT_20220210-125404.csv",
#     ),
#     (
#         "DOGE_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/DOGE_USDT_20220210-111452.csv",
#     ),
#     (
#         "ETH_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/ETH_USDT_20220210-112851.csv",
#     ),
#     (
#         "LINK_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/LINK_USDT_20220210-114240.csv",
#     ),
#     (
#         "SOL_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/SOL_USDT_20220210-115701.csv",
#     ),
#     (
#         "XRP_USDT",
#         "s3://cryptokaizen-data2/historical/ftx/XRP_USDT_20220210-121122.csv",
#     ),
# ]
# data = read_exchange_df(paths)
# data.head()

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.max())

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.min())

# %% [markdown]
# ## gateio stat

# %%
# paths = [
#     (
#         "BNB_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/ADA_USDT_20220210-112115.csv",
#     ),
#     (
#         "AVAX_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/AVAX_USDT_20220210-113306.csv",
#     ),
#     (
#         "BNB_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/BNB_USDT_20220210-114500.csv",
#     ),
#     (
#         "BTC_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/BTC_USDT_20220210-115659.csv",
#     ),
#     (
#         "DOGE_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/DOGE_USDT_20220210-120851.csv",
#     ),
#     (
#         "EOS_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/EOS_USDT_20220210-122048.csv",
#     ),
#     (
#         "ETH_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/ETH_USDT_20220210-123244.csv",
#     ),
#     (
#         "FIL_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/FIL_USDT_20220210-124438.csv",
#     ),
#     (
#         "LINK_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/LINK_USDT_20220210-125629.csv",
#     ),
#     (
#         "SOL_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/SOL_USDT_20220210-130821.csv",
#     ),
#     (
#         "XRP_USDT",
#         "s3://cryptokaizen-data2/historical/gateio/XRP_USDT_20220210-132013.csv",
#     ),
# ]
# data = read_exchange_df(paths)
# data.head()

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.max())

# %%
# hdateti.convert_unix_epoch_to_timestamp(data.timestamp.min())

# %% [markdown]
# # Load CCXT data from daily staged bucket

# %%
# file_path = "%s/ccxt/binance/" % config["load"]["data_dir"]
# kwargs = {"aws_profile": "ck"}
# data = hparque.from_parquet(file_path, **kwargs)
# data.head()
