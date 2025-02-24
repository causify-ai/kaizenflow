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

import core.config.config_ as cconconf
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl
import research_amp.cc.qa as ramccqa

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs


# %%
def get_master_single_vendor_qa_config() -> cconconf.Config:
    """
    Get task1866-specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            # Parameters for client initialization.
            "im_client": {
                "universe_version": "v3",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "spot",
                "download_universe_version": "v7_3",
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
config = get_master_single_vendor_qa_config()
print(config)

# %% [markdown]
# # QA checks

# %% [markdown]
# Major metric for a QA check is `"bad data [%]"` which is the sum of `"volume=0 [%]"` and `"NaNs [%]"`.

# %%
client = icdcl.CcxtHistoricalPqByTileClient(**config["data"]["im_client"])

# %%
universe = client.get_universe()
universe

# %% [markdown]
# ## Binance

# %%
binance_universe = [
    full_symbol for full_symbol in universe if full_symbol.startswith("binance")
]
binance_universe

# %%
binance_data = client.read_data(binance_universe, **config["data"]["read_data"])
binance_data.head(3)

# %%
vendor_name = "CCXT"
binance_timestamp_stats = ramccqa.get_timestamp_stats(binance_data, vendor_name)
binance_timestamp_stats

# %%
agg_level_full_symbol = ["full_symbol"]
binance_bad_data_stats = ramccqa.get_bad_data_stats(
    binance_data, agg_level_full_symbol, vendor_name
)
binance_bad_data_stats

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
binance_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    binance_data, agg_level_full_symbol_year_month, vendor_name
)
binance_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    binance_bad_data_stats_by_year_month, config["stats"]["threshold"]
)

# %% [markdown]
# ## FTX

# %%
ftx_universe = [
    full_symbol for full_symbol in universe if full_symbol.startswith("ftx")
]
ftx_universe

# %%
ftx_data = client.read_data(ftx_universe, **config["data"]["read_data"])
ftx_data.head(3)

# %%
ftx_timestamp_stats = ramccqa.get_timestamp_stats(ftx_data, vendor_name)
ftx_timestamp_stats

# %%
ftx_bad_data_stats = ramccqa.get_bad_data_stats(
    ftx_data, agg_level_full_symbol, vendor_name
)
ftx_bad_data_stats

# %%
ftx_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    ftx_data, agg_level_full_symbol_year_month, vendor_name
)
ftx_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    ftx_bad_data_stats_by_year_month, config["stats"]["threshold"]
)

# %% [markdown]
# ## Gateio

# %%
gateio_universe = [
    full_symbol for full_symbol in universe if full_symbol.startswith("gateio")
]
gateio_universe

# %%
gateio_data = client.read_data(gateio_universe, **config["data"]["read_data"])
gateio_data.head(3)

# %%
gateio_timestamp_stats = ramccqa.get_timestamp_stats(gateio_data, vendor_name)
gateio_timestamp_stats

# %%
gateio_bad_data_stats = ramccqa.get_bad_data_stats(
    gateio_data, agg_level_full_symbol, vendor_name
)
gateio_bad_data_stats

# %%
gateio_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    gateio_data, agg_level_full_symbol_year_month, vendor_name
)
gateio_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    gateio_bad_data_stats_by_year_month, config["stats"]["threshold"]
)

# %% [markdown]
# ## Kucoin

# %%
kucoin_universe = [
    full_symbol for full_symbol in universe if full_symbol.startswith("kucoin")
]
kucoin_universe

# %%
kucoin_data = client.read_data(kucoin_universe, **config["data"]["read_data"])
kucoin_data.head(3)

# %%
kucoin_timestamp_stats = ramccqa.get_timestamp_stats(kucoin_data, vendor_name)
kucoin_timestamp_stats

# %%
kucoin_bad_data_stats = ramccqa.get_bad_data_stats(
    kucoin_data, agg_level_full_symbol, vendor_name
)
kucoin_bad_data_stats

# %%
kucoin_bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    kucoin_data, agg_level_full_symbol_year_month, vendor_name
)
kucoin_bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    kucoin_bad_data_stats_by_year_month, config["stats"]["threshold"]
)
