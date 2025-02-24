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
# # Description

# %% [markdown]
# This notebook performs a check that missing data is not present at source.

# %% [markdown]
# # Imports

# %%
import logging
import os

import pandas as pd
import requests

import core.statistics as costatis
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.crypto_chassis.data.client.crypto_chassis_clients as imvccdcccc

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Functions

# %%
def _get_full_symbol_data_for_year_month(
    df: pd.DataFrame, full_symbol: str, year: int, month: int
) -> pd.DataFrame:
    """
    Get data for one full symbol for a specific year and month.
    """
    df = df[
        (df.index.year == year)
        & (df.index.month == month)
        & (df["full_symbol"] == full_symbol)
    ]
    df = df.round(8)
    if "knowledge_timestamp" in df.columns.to_list():
        df = df.drop(columns=["knowledge_timestamp"])
        df.index.name = "time_seconds"
    return df


def _get_qa_stats(data: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Get quality assurance stats per full symbol.
    """
    res_stats = []
    for full_symbol, symbol_data in data.groupby("full_symbol"):
        # Compute stats for a full symbol.
        symbol_stats = pd.Series(dtype="object", name=full_symbol)
        symbol_stats["source"] = source
        symbol_stats["min_timestamp"] = symbol_data.index.min()
        symbol_stats["max_timestamp"] = symbol_data.index.max()
        symbol_stats["NaNs [%]"] = 100 * (
            costatis.compute_frac_nan(symbol_data["close"])
        )
        symbol_stats["volume=0 [%]"] = 100 * (
            symbol_data[symbol_data["volume"] == 0].shape[0]
            / symbol_data.shape[0]
        )
        symbol_stats["bad data [%]"] = (
            symbol_stats["NaNs [%]"] + symbol_stats["volume=0 [%]"]
        )
        res_stats.append(symbol_stats)
    res_stats_df = pd.concat(res_stats, axis=1).T
    return res_stats_df


def _load_crypto_chassis_ohlcv(exchange_id: str, currency_pair: str):
    """
    Load data from CryptoChassis API.
    """
    r = requests.get(
        f"https://api.cryptochassis.com/v1/ohlc/{exchange_id}/{currency_pair}?startTime=0"
    )
    df = pd.read_csv(r.json()["historical"]["urls"][0]["url"], compression="gzip")
    df["time_seconds"] = df["time_seconds"].apply(
        lambda x: hdateti.convert_unix_epoch_to_timestamp(x, unit="s")
    )
    df = df.set_index("time_seconds")
    full_symbol = (
        f"{exchange_id.lower()}::{currency_pair.upper().replace('-', '_')}"
    )
    df.insert(0, "full_symbol", full_symbol)
    return df


# %% [markdown]
# # Load data from CryptoChassis API

# %%
source_ftx_xrp = _load_crypto_chassis_ohlcv("ftx", "xrp-usdt")
source_ftx_xrp_2022_4 = _get_full_symbol_data_for_year_month(
    source_ftx_xrp, "ftx::XRP_USDT", 2022, 4
)

# %%
source_ftx_doge = _load_crypto_chassis_ohlcv("ftx", "doge-usdt")
source_ftx_doge_2022_3 = _get_full_symbol_data_for_year_month(
    source_ftx_doge, "ftx::DOGE_USDT", 2022, 3
)

# %% [markdown]
# # Load data with client

# %%
universe_version = "v1"
resample_1min = False
root_dir = os.path.join(
    hs3.get_s3_bucket_path("ck"),
    "reorg",
    "historical.manual.pq",
)
partition_mode = "by_year_month"
client = imvccdcccc.CryptoChassisHistoricalPqByTileClient(
    universe_version, resample_1min, root_dir, partition_mode, aws_profile="ck"
)

# %%
start_ts = None
end_ts = None
columns = None
filter_data_mode = "assert"
full_symbols = ["ftx::XRP_USDT", "ftx::DOGE_USDT"]
s3_ftx = client.read_data(
    full_symbols, start_ts, end_ts, columns, filter_data_mode
)

# %% [markdown]
# # Compare data

# %% [markdown]
# ## ftx::XRP_USDT

# %%
s3_ftx_xrp_2022_04 = _get_full_symbol_data_for_year_month(
    s3_ftx, "ftx::XRP_USDT", 2022, 4
)
s3_ftx_xrp_2022_04.shape[0] == source_ftx_xrp_2022_4.shape[0]

# %% [markdown]
# ## ftx::DOGE_USDT

# %%
s3_ftx_doge_2022_3 = _get_full_symbol_data_for_year_month(
    s3_ftx, "ftx::DOGE_USDT", 2022, 3
)
source_ftx_doge_2022_3.shape[0] == s3_ftx_doge_2022_3.shape[0]

# %%
# There are no NaNs for ftx::DOGE_USDT for all period storing on S3.
s3_ftx_doge_2022_3[s3_ftx_doge_2022_3["close"].isna()].shape[0]

# %%
# There is no volume=0 in the S3 data.
s3_ftx_doge_2022_3[s3_ftx_doge_2022_3["volume"] == 0].shape[0]

# %% [markdown]
# ### Compare non-resampled data from source and S3

# %%
# Check if data in both datasets are equal.
s3_ftx_doge_2022_3.eq(source_ftx_doge_2022_3, axis=1).value_counts()

# %% [markdown]
# ### Compare resampled data from the source and S3

# %%
source_ftx_doge_2022_3_resampled = hpandas.resample_df(
    source_ftx_doge_2022_3, "T"
)
source_ftx_doge_2022_3_resampled["full_symbol"] = "ftx::DOGE_USDT"
# Check how much NaNs in the resampled data.
source_ftx_doge_2022_3_resampled[
    source_ftx_doge_2022_3_resampled["close"].isna()
].shape[0]

# %%
s3_ftx_doge_2022_3_resampled = hpandas.resample_df(s3_ftx_doge_2022_3, "T")
s3_ftx_doge_2022_3_resampled["full_symbol"] = "ftx::DOGE_USDT"
# Check how much NaNs in the resampled data.
s3_ftx_doge_2022_3_resampled[s3_ftx_doge_2022_3_resampled["close"].isna()].shape[
    0
]

# %%
s3_stats = _get_qa_stats(s3_ftx_doge_2022_3, "s3")
source_stats = _get_qa_stats(source_ftx_doge_2022_3, "CryptoChassis")
s3_resampled_stats = _get_qa_stats(s3_ftx_doge_2022_3_resampled, "s3_resampled")
source_resampled_stats = _get_qa_stats(
    source_ftx_doge_2022_3_resampled, "CryptoChassis_resampled"
)

# %%
stats = pd.concat(
    [s3_stats, source_stats, s3_resampled_stats, source_resampled_stats]
)
stats

# %% [markdown]
# Equal amount of NaNs after resampling. Data with NaNs on S3 is absent at the source.
