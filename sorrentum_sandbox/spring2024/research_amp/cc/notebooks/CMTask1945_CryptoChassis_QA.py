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
# This notebooks performs QA checks for a single vendor:
#    - Number of NaN data points as % of total
#    - Number of data points where `volume=0` as % of total

# %% [markdown]
# # Imports

# %%
import logging
import os

import pandas as pd

import core.config.config_ as cconconf
import core.config.config_utils as ccocouti
import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.crypto_chassis.data.client.crypto_chassis_clients as imvccdcccc

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs

# %%
def get_cmtask1866_config_ccxt() -> cconconf.Config:
    """
    Get task1866-specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            # Parameters for client initialization.
            "im_client": {
                "universe_version": "v1",
                "resample_1min": True,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"),
                    "reorg",
                    "historical.manual.pq",
                ),
                "partition_mode": "by_year_month",
                "data_snapshot": "latest",
                "aws_profile": "ck",
            },
            # Parameters for data query.
            "read_data": {
                "start_ts": None,
                "end_ts": None,
                "columns": None,
                "filter_data_mode": "assert",
            },
        },
        "column_names": {
            "full_symbol": "full_symbol",
            "close_price": "close",
        },
        "stats": {
            "threshold": 30,
        },
    }
    config = cconfig.Config.from_dict(param_dict)
    return config


# %%
config = get_cmtask1866_config_ccxt()
print(config)


# %% [markdown]
# # Functions

# %%
# TODO(Dan): Clean up and move to a lib.
# TODO(Dan): Separate data reading and computing the stats.
def perform_qa_per_exchange(
    config: cconconf.Config,
    exchange_id: str,
    client: icdc.ImClient,
    *,
    by_year_month: bool = False,
) -> pd.DataFrame:
    """
    Get quality assurance stats for specified exchange.

    QA stats include:
       - % of NaNs
       - % of rows with "volume=0"
       - % of bad data which is the sum of NaNs and "volume=0" stats
       - min and max timestamp if `by_year_month=False`

    E.g.,
    ```
                                    NaNs [%]  volume=0 [%]  bad data [%]
    full_symbol        year  month
    binance::ADA_USDT  2022      1    0.2222        0.2222        0.4444
                                 2       5.9           0.1           6.0
    binance::BTC_USDT  2022      1       0.0           0.0           0.0
    ```
    :param config: parameters config
    :param exchange_id: name of exchange to compute stats for
    :param client: client to read data
    :param by_year_month: compute QA stats by year and month
    """
    # Get exchange data for related full symbols.
    universe = client.get_universe()
    exchange_universe = [
        full_symbol
        for full_symbol in universe
        if full_symbol.startswith(exchange_id)
    ]
    exchange_data = client.read_data(
        exchange_universe, **config["data"]["read_data"]
    )
    # Compute exchange stats.
    if by_year_month:
        qa_stats = _get_qa_stats_by_year_month(config, exchange_data)
    else:
        qa_stats = _get_qa_stats(config, exchange_data)
    return qa_stats


# TODO(Dan): Merge with `_get_qa_stats_by_year_month()` by passing `agg_level`.
def _get_qa_stats(config: cconconf.Config, data: pd.DataFrame) -> pd.DataFrame:
    """
    Get quality assurance stats per full symbol.
    """
    res_stats = []
    for full_symbol, symbol_data in data.groupby(
        config["column_names"]["full_symbol"]
    ):
        # Compute stats for a full symbol.
        symbol_stats = pd.Series(dtype="object", name=full_symbol)
        symbol_stats["min_timestamp"] = symbol_data.index.min()
        symbol_stats["max_timestamp"] = symbol_data.index.max()
        symbol_stats["NaNs [%]"] = 100 * (
            costatis.compute_frac_nan(
                symbol_data[config["column_names"]["close_price"]]
            )
        )
        symbol_stats["volume=0 [%]"] = 100 * (
            symbol_data[symbol_data["volume"] == 0].shape[0]
            / symbol_data.shape[0]
        )
        symbol_stats["bad data [%]"] = (
            symbol_stats["NaNs [%]"] + symbol_stats["volume=0 [%]"]
        )
        res_stats.append(symbol_stats)
    # Combine all full symbol stats.
    res_stats_df = pd.concat(res_stats, axis=1).T
    return res_stats_df


def _get_qa_stats_by_year_month(
    config: cconconf.Config, data: pd.DataFrame
) -> pd.DataFrame:
    """
    Get quality assurance stats per full symbol, year, and month.
    """
    # Get year and month columns to group by them.
    data["year"] = data.index.year
    data["month"] = data.index.month
    #
    res_stats = []
    for index, data_monthly in data.groupby(["year", "month"]):
        #
        year, month = index
        #
        stats_monthly = _get_qa_stats(config, data_monthly)
        #
        stats_monthly["year"] = year
        stats_monthly["month"] = month
        res_stats.append(stats_monthly)
    res_stats_df = pd.concat(res_stats)
    res_stats_df = res_stats_df.drop(["min_timestamp", "max_timestamp"], axis=1)
    #
    # Set index by full symbol, year, and month.
    res_stats_df[config["column_names"]["full_symbol"]] = res_stats_df.index
    index_columns = [config["column_names"]["full_symbol"], "year", "month"]
    res_stats_df = res_stats_df.sort_values(index_columns)
    res_stats_df = res_stats_df.set_index(index_columns)
    return res_stats_df


# TODO(Dan): Add filtering by dates.
def _plot_bad_data_stats(
    config: cconconf.Config, bad_data_stats: pd.DataFrame
) -> None:
    """
    Plot bad data stats per unique full symbol in data.

    Bad data is the sum of NaNs and "volume=0" stats.
    """
    full_symbols = bad_data_stats.index.get_level_values(0).unique()
    for full_symbol in full_symbols:
        bad_data_col_name = "bad data [%]"
        ax = bad_data_stats.loc[full_symbol].plot.bar(
            y=bad_data_col_name, rot=0, title=full_symbol
        )
        #
        ax.hlines(
            y=config["stats"]["threshold"],
            xmin=0,
            xmax=len(bad_data_stats),
            color="r",
        )
        # TODO(Dan): Make ticklabels more readable.
        # Get ticks and labels for x-axis.
        ticks = ax.xaxis.get_ticklocs()
        ticklabels = [
            l.get_text().strip("()").split(", ")
            for l in ax.xaxis.get_ticklabels()
        ]
        ticklabels = [".".join([l[0], l[1]]) for l in ticklabels]
        # Adjust x-axis labels so they do not overlap on plot by
        # picking ticks and labels by specified stride that limits
        # the number of final ticks to 10.
        stride = len(ticks) // 10 + 1
        ax.xaxis.set_ticks(ticks[::stride])
        ax.xaxis.set_ticklabels(ticklabels[::stride])
        ax.figure.show()


# %% [markdown]
# # QA checks

# %% [markdown]
# Major metric for a QA check is `"bad data [%]"` which is the sum of `"volume=0 [%]"` and `"NaNs [%]"`.

# %%
client = imvccdcccc.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["im_client"]
)

# %%
universe = client.get_universe()
universe

# %% [markdown]
# ## Binance

# %%
binance_stats = perform_qa_per_exchange(config, "binance", client)
binance_stats

# %%
binance_stats_by_year_month = perform_qa_per_exchange(
    config, "binance", client, by_year_month=True
)
binance_stats_by_year_month

# %%
_ = _plot_bad_data_stats(config, binance_stats_by_year_month)

# %% [markdown]
# ## FTX

# %%
ftx_stats = perform_qa_per_exchange(config, "ftx", client)
ftx_stats

# %%
ftx_stats_by_year_month = perform_qa_per_exchange(
    config, "ftx", client, by_year_month=True
)
ftx_stats_by_year_month

# %%
_ = _plot_bad_data_stats(config, ftx_stats_by_year_month)

# %% [markdown]
# ## Gateio

# %%
gateio_stats = perform_qa_per_exchange(config, "gateio", client)
gateio_stats

# %%
gateio_stats_by_year_month = perform_qa_per_exchange(
    config, "gateio", client, by_year_month=True
)
gateio_stats_by_year_month

# %%
_ = _plot_bad_data_stats(config, gateio_stats_by_year_month)

# %% [markdown]
# ## Kucoin

# %%
kucoin_stats = perform_qa_per_exchange(config, "kucoin", client)
kucoin_stats

# %%
kucoin_stats_by_year_month = perform_qa_per_exchange(
    config, "kucoin", client, by_year_month=True
)
kucoin_stats_by_year_month

# %%
_ = _plot_bad_data_stats(config, kucoin_stats_by_year_month)

# %% [markdown]
# # Summary

# %% [markdown]
# - There is no `volume = 0` rows at all
# - Binance:
#    - Data is acceptable
#    - All coins have  <1% of NaNs
# - FTX:
#    - NaN spikes for `DOGE` and `XRP` in 2022
#    - Other coins are of decent quality
# - Gateio:
#    - Data is acceptable
#    - All coins have  <2% of NaNs
# - Kucoin:
#    - Data is acceptable
#    - All coins have  <2% of NaNs
