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
# This notebooks performs QA checks for Crypto Chassis `coinbase`:
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
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.crypto_chassis.data.client as imvccdc
import research_amp.cc.qa as ramccqa

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs

# %%
def get_cmtask2051_config_crypto_chassis() -> cconconf.Config:
    """
    Get task2051-specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "vendor": "crypto_chassis",
        "data": {
            # Parameters for client initialization.
            "im_client": {
                "universe_version": "v2",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "data_snapshot": "20220530",
                "aws_profile": "ck",
            },
            # Parameters for data query.
            "read_data": {
                "start_ts": None,
                "end_ts": None,
                "columns": ["full_symbol", "close", "volume"],
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
config = get_cmtask2051_config_crypto_chassis()
print(config)


# %% [markdown]
# # Functions

# %%
# TODO(Dan): Add filtering by dates.
def _plot_bad_data_by_year_month_stats(
    config: cconconf.Config, bad_data_stats: pd.DataFrame
) -> None:
    """
    Plot bad data stats by year and month per unique full symbol in data.

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
client = imvccdc.crypto_chassis_clients.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["im_client"]
)

# %%
universe = client.get_universe()
universe

# %% [markdown]
# ## Coinbase

# %%
coinbase_universe = [
    full_symbol for full_symbol in universe if full_symbol.startswith("coinbase")
]
coinbase_universe

# %%
coinbase_data = client.read_data(coinbase_universe, **config["data"]["read_data"])
coinbase_data.head(3)

# %%
vendor_name = config["vendor"]
coinbase_timestamp_stats = ramccqa.get_timestamp_stats(coinbase_data, vendor_name)
coinbase_timestamp_stats

# %%
agg_level_full_symbol = ["full_symbol"]
coinbase_bad_data_stats = ramccqa.get_bad_data_stats(
    coinbase_data, agg_level_full_symbol, vendor_name
)
coinbase_bad_data_stats

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
coinbase_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    coinbase_data, agg_level_full_symbol_year_month, vendor_name
)
coinbase_bad_data_stats_by_year_month

# %%
_ = _plot_bad_data_by_year_month_stats(
    config, coinbase_bad_data_stats_by_year_month
)
