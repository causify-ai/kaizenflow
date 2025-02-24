# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.5
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
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl
import im_v2.common.universe as ivcu
import research_amp.cc.statistics as ramccsta
import research_amp.cc.volume as ramccvol

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Config

# %%
def get_cmtask260_config() -> cconconf.Config:
    """
    Get task260-specific config.
    """
    config = cconconf.Config()
    # Load parameters.
    config.add_subconfig("load")
    config["load"]["aws_profile"] = AM_AWS_PROFILE
    config["load"]["data_dir"] = os.path.join(
        hs3.get_s3_bucket_path(AM_AWS_PROFILE), "data"
    )
    # Data parameters.
    config.add_subconfig("data")
    config["data"]["universe_version"] = "v03"
    config["data"]["vendor"] = "CCXT"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["volume"] = "volume"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange"] = "exchange_id"
    config["column_names"]["close"] = "close"
    return config


config = get_cmtask260_config()
print(config)

# %% [markdown]
# # Load the data

# %%
vendor_universe = ivcu.get_vendor_universe(
    config["data"]["vendor"],
    version=config["data"]["universe_version"],
    as_full_symbol=True,
)
vendor_universe

# %%
compute_daily_cumul_volume_ = lambda data: ramccvol.get_daily_cumul_volume(
    data, config, is_notional_volume=False
)

cumul_daily_volume = ramccsta.compute_stats_for_universe(
    vendor_universe, config, compute_daily_cumul_volume_
)

# %%
_LOG.info(
    "The number of (exchanges, currency pairs) =%s", cumul_daily_volume.shape[0]
)
cumul_daily_volume.head(3)

# %% [markdown]
# # Compute total volume per exchange

# %%
total_volume_by_exchange = ramccvol.get_total_exchange_volume(
    cumul_daily_volume, config, avg_daily=False
)
print(total_volume_by_exchange)

# %% [markdown]
# # Compute total volume per currency

# %%
total_volume_by_coins = ramccvol.get_total_coin_volume(
    cumul_daily_volume, config, avg_daily=False
)
print(total_volume_by_coins)

# %% [markdown]
# # Rolling Plots

# %% [markdown]
# ## By exchange

# %%
rolling_volume_per_exchange = ramccvol.get_rolling_volume_per_exchange(
    cumul_daily_volume, config, window=90
)
print(rolling_volume_per_exchange)

# %% [markdown]
# ## By coins

# %%
rolling_volume_per_coin = ramccvol.get_rolling_volume_per_coin(
    cumul_daily_volume, config, window=90
)
print(rolling_volume_per_coin)

# %% [markdown]
# # Compare weekday volumes

# %%
total_volume_by_weekdays = ramccvol.compare_weekday_volumes(
    cumul_daily_volume, config
)
print(total_volume_by_weekdays)


# %% [markdown]
# # Compare ATH volumes

# %% [markdown]
# ## Functions

# %%
def get_initial_df_with_volumes(coins, exchange, is_notional_volume):
    """
    Return DataFrame with the volume of all coins for exchange with initial timestamps
    Parameters: list of coins, exchange name
    """
    result = []
    vendor = config["data"]["vendor"]
    universe_version = "v3"
    resample_1min = True
    root_dir = config["load"]["data_dir"]
    extension = "csv.gz"
    ccxt_csv_client = icdcl.CcxtCddCsvParquetByAssetClient(
        vendor,
        universe_version,
        resample_1min,
        root_dir,
        extension,
        aws_profile=config["load"]["aws_profile"],
    )
    for coin in coins:
        # TODO(Grisha): use `FullSymbols` #587.
        full_symbol = f"{exchange}::{coin}"
        start_ts = None
        end_ts = None
        df = ccxt_csv_client.read_data(
            [full_symbol],
            start_ts,
            end_ts,
        )
        if is_notional_volume:
            df["volume"] = df["volume"] * df["close"]
        result.append(df["volume"])
    final_result = pd.concat(result, axis=1)
    return final_result


def plot_ath_volumes_comparison(df_list):
    """
    Return the graph with the comparison of average minute total trading volume
    in ATH vs.

    non-ATH
    Parameters: dataframe with volumes from a given exchange
    """
    plot_df = []
    for df in df_list:
        df_ath = df.iloc[df.index.indexer_between_time("09:30", "16:00")]
        df_not_ath = df.loc[~df.index.isin(df_ath.index)]
        ath_stat = pd.DataFrame()
        ath_stat.loc[df.name, f"minute_avg_total_volume_ath_{df.name}"] = (
            df_ath.sum().sum() / df_ath.shape[0]
        )
        ath_stat.loc[df.name, f"minute_avg_total_volume_not_ath_{df.name}"] = (
            df_not_ath.sum().sum() / df_not_ath.shape[0]
        )
        plot_df.append(ath_stat)
    plot_df = pd.concat(plot_df)
    plot_df.plot.bar(figsize=(15, 7), logy=True)


# %% [markdown]
# ## Load the data

# %%
# get the list of all coin paires for each exchange
binance_coins = ivcu.get_vendor_universe("CCXT", version="v3")["binance"]
ftx_coins = ivcu.get_vendor_universe("CCXT", version="v3")["ftx"]
gateio_coins = ivcu.get_vendor_universe("CCXT", version="v3")["gateio"]
kucoin_coins = ivcu.get_vendor_universe("CCXT", version="v3")["kucoin"]

# load all the dataframes
binance_1 = get_initial_df_with_volumes(
    binance_coins, "binance", is_notional_volume=True
)
ftx_1 = get_initial_df_with_volumes(ftx_coins, "ftx", is_notional_volume=True)
gateio_1 = get_initial_df_with_volumes(
    gateio_coins, "gateio", is_notional_volume=True
)
kucoin_1 = get_initial_df_with_volumes(
    kucoin_coins, "kucoin", is_notional_volume=True
)

# supportive variables
exchange_list = [binance_1, ftx_1, gateio_1, kucoin_1]
binance_1.name = "binance"
ftx_1.name = "ftx"
gateio_1.name = "gateio"
kucoin_1.name = "kucoin"

# %% [markdown]
# ## Plot

# %%
plot_ath_volumes_comparison(exchange_list)
