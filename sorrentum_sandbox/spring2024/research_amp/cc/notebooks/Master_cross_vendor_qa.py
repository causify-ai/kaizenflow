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
# This notebook performs cross-vendor QA checks to compare vendors in terms of:
#    - Difference and intersection of vendor universes
#    - Time intervals, i.e. which vendor has the longest data available for each full symbol in intersecting universe
#    - Data quality (bad data [%], missing bars [%], volume=0 [%], NaNs [%]) for intersecting universe and time intervals

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
import im_v2.crypto_chassis.data.client as iccdc
import research_amp.cc.qa as ramccqa

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()


# %% [markdown]
# # Configs


# %%
def get_master_cross_vendor_qa_config() -> cconconf.Config:
    """
    Get task1966-specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            "ccxt": {
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
            "crypto_chassis": {
                "universe_version": "v1",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "spot",
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
config = get_master_cross_vendor_qa_config()
print(config)

# %% [markdown]
# # Compare universes

# %%
crypto_chassis_client = iccdc.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["crypto_chassis"]
)
ccxt_client = icdcl.CcxtHistoricalPqByTileClient(**config["data"]["ccxt"])

# %%
crypto_chassis_universe = crypto_chassis_client.get_universe()
ccxt_universe = ccxt_client.get_universe()

# %%
common_universe = list(set(crypto_chassis_universe) & set(ccxt_universe))

# %%
compare_universe = hprint.set_diff_to_str(
    crypto_chassis_universe, ccxt_universe, add_space=True
)
print(compare_universe)

# %% [markdown]
# # Compare Binance QA stats

# %%
binance_universe = [
    full_symbol
    for full_symbol in common_universe
    if full_symbol.startswith("binance")
]
binance_universe

# %%
ccxt_binance_data = ccxt_client.read_data(
    binance_universe, **config["data"]["read_data"]
)
ccxt_binance_data.head(3)

# %%
crypto_chassis_binance_data = crypto_chassis_client.read_data(
    binance_universe, **config["data"]["read_data"]
)
crypto_chassis_binance_data.head(3)

# %%
crypto_chassis_vendor = "Crypto Chassis"
crypto_chassis_timestamp_binance_stats = ramccqa.get_timestamp_stats(
    crypto_chassis_binance_data, crypto_chassis_vendor
)
ccxt_vendor = "CCXT"
ccxt_timestamp_binance_stats = ramccqa.get_timestamp_stats(
    ccxt_binance_data, ccxt_vendor
)
#
binance_timestamp_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_timestamp_binance_stats,
    ccxt_timestamp_binance_stats,
)
binance_timestamp_stats_qa

# %%
agg_level_full_symbol = ["full_symbol"]
crypto_chassis_bad_data_binance_stats = ramccqa.get_bad_data_stats(
    crypto_chassis_binance_data, agg_level_full_symbol, crypto_chassis_vendor
)
ccxt_bad_data_binance_stats = ramccqa.get_bad_data_stats(
    ccxt_binance_data, agg_level_full_symbol, ccxt_vendor
)
#
binance_bad_data_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_binance_stats,
    ccxt_bad_data_binance_stats,
)
binance_bad_data_stats_qa

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
crypto_chassis_bad_data_binance_stats_by_year_month = ramccqa.get_bad_data_stats(
    crypto_chassis_binance_data,
    agg_level_full_symbol_year_month,
    crypto_chassis_vendor,
)
ccxt_bad_data_binance_stats_by_year_month = ramccqa.get_bad_data_stats(
    ccxt_binance_data, agg_level_full_symbol_year_month, ccxt_vendor
)
#
binance_bad_data_stats_by_year_month_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_binance_stats_by_year_month,
    ccxt_bad_data_binance_stats_by_year_month,
)
binance_bad_data_stats_by_year_month_qa

# %%
ramccqa.plot_bad_data_by_year_month_stats(
    binance_bad_data_stats_by_year_month_qa, config["stats"]["threshold"]
)

# %% [markdown]
# # Compare FTX QA stats

# %%
ftx_universe = [
    full_symbol
    for full_symbol in common_universe
    if full_symbol.startswith("ftx")
]
ftx_universe

# %%
ccxt_ftx_data = ccxt_client.read_data(ftx_universe, **config["data"]["read_data"])
ccxt_ftx_data.head(3)

# %%
crypto_chassis_ftx_data = crypto_chassis_client.read_data(
    ftx_universe, **config["data"]["read_data"]
)
crypto_chassis_ftx_data.head(3)

# %%
crypto_chassis_timestamp_ftx_stats = ramccqa.get_timestamp_stats(
    crypto_chassis_ftx_data, crypto_chassis_vendor
)
ccxt_timestamp_ftx_stats = ramccqa.get_timestamp_stats(ccxt_ftx_data, ccxt_vendor)
#
ftx_timestamp_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_timestamp_ftx_stats,
    ccxt_timestamp_ftx_stats,
)
ftx_timestamp_stats_qa

# %%
crypto_chassis_bad_data_ftx_stats = ramccqa.get_bad_data_stats(
    crypto_chassis_ftx_data, agg_level_full_symbol, crypto_chassis_vendor
)
ccxt_bad_data_ftx_stats = ramccqa.get_bad_data_stats(
    ccxt_ftx_data, agg_level_full_symbol, ccxt_vendor
)
#
ftx_bad_data_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_ftx_stats,
    ccxt_bad_data_ftx_stats,
)
ftx_bad_data_stats_qa

# %%
crypto_chassis_bad_data_ftx_stats_by_year_month = ramccqa.get_bad_data_stats(
    crypto_chassis_ftx_data,
    agg_level_full_symbol_year_month,
    crypto_chassis_vendor,
)
ccxt_bad_data_ftx_stats_by_year_month = ramccqa.get_bad_data_stats(
    ccxt_ftx_data, agg_level_full_symbol_year_month, ccxt_vendor
)
#
ftx_bad_data_stats_by_year_month_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_ftx_stats_by_year_month,
    ccxt_bad_data_ftx_stats_by_year_month,
)
ftx_bad_data_stats_by_year_month_qa

# %%
ramccqa.plot_bad_data_by_year_month_stats(
    ftx_bad_data_stats_by_year_month_qa, config["stats"]["threshold"]
)

# %% [markdown]
# # Compare Gateio QA stats

# %%
gateio_universe = [
    full_symbol
    for full_symbol in common_universe
    if full_symbol.startswith("gateio")
]
gateio_universe

# %%
ccxt_gateio_data = ccxt_client.read_data(
    gateio_universe, **config["data"]["read_data"]
)
ccxt_gateio_data.head(3)

# %%
crypto_chassis_gateio_data = crypto_chassis_client.read_data(
    gateio_universe, **config["data"]["read_data"]
)
crypto_chassis_gateio_data.head(3)

# %%
crypto_chassis_timestamp_gateio_stats = ramccqa.get_timestamp_stats(
    crypto_chassis_gateio_data, crypto_chassis_vendor
)
ccxt_timestamp_gateio_stats = ramccqa.get_timestamp_stats(
    ccxt_gateio_data, ccxt_vendor
)
#
gateio_timestamp_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_timestamp_gateio_stats,
    ccxt_timestamp_gateio_stats,
)
gateio_timestamp_stats_qa

# %%
crypto_chassis_bad_data_gateio_stats = ramccqa.get_bad_data_stats(
    crypto_chassis_gateio_data, agg_level_full_symbol, crypto_chassis_vendor
)
ccxt_bad_data_gateio_stats = ramccqa.get_bad_data_stats(
    ccxt_gateio_data, agg_level_full_symbol, ccxt_vendor
)
#
gateio_bad_data_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_gateio_stats,
    ccxt_bad_data_gateio_stats,
)
gateio_bad_data_stats_qa

# %%
crypto_chassis_bad_data_gateio_stats_by_year_month = ramccqa.get_bad_data_stats(
    crypto_chassis_gateio_data,
    agg_level_full_symbol_year_month,
    crypto_chassis_vendor,
)
ccxt_bad_data_gateio_stats_by_year_month = ramccqa.get_bad_data_stats(
    ccxt_gateio_data, agg_level_full_symbol_year_month, ccxt_vendor
)
#
gateio_bad_data_stats_by_year_month_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_gateio_stats_by_year_month,
    ccxt_bad_data_gateio_stats_by_year_month,
)
gateio_bad_data_stats_by_year_month_qa

# %%
ramccqa.plot_bad_data_by_year_month_stats(
    gateio_bad_data_stats_by_year_month_qa, config["stats"]["threshold"]
)

# %% [markdown]
# # Compare Kucoin QA stats

# %%
kucoin_universe = [
    full_symbol
    for full_symbol in common_universe
    if full_symbol.startswith("kucoin")
]
kucoin_universe

# %%
ccxt_kucoin_data = ccxt_client.read_data(
    kucoin_universe, **config["data"]["read_data"]
)
ccxt_kucoin_data.head(3)

# %%
crypto_chassis_kucoin_data = crypto_chassis_client.read_data(
    kucoin_universe, **config["data"]["read_data"]
)
crypto_chassis_kucoin_data.head(3)

# %%
crypto_chassis_timestamp_kucoin_stats = ramccqa.get_timestamp_stats(
    crypto_chassis_kucoin_data, crypto_chassis_vendor
)
ccxt_timestamp_kucoin_stats = ramccqa.get_timestamp_stats(
    ccxt_kucoin_data, ccxt_vendor
)
#
kucoin_timestamp_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_timestamp_kucoin_stats,
    ccxt_timestamp_kucoin_stats,
)
kucoin_timestamp_stats_qa

# %%
crypto_chassis_bad_data_kucoin_stats = ramccqa.get_bad_data_stats(
    crypto_chassis_kucoin_data, agg_level_full_symbol, crypto_chassis_vendor
)
ccxt_bad_data_kucoin_stats = ramccqa.get_bad_data_stats(
    ccxt_kucoin_data, agg_level_full_symbol, ccxt_vendor
)
#
kucoin_bad_data_stats_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_kucoin_stats,
    ccxt_bad_data_kucoin_stats,
)
kucoin_bad_data_stats_qa

# %%
crypto_chassis_bad_data_kucoin_stats_by_year_month = ramccqa.get_bad_data_stats(
    crypto_chassis_kucoin_data,
    agg_level_full_symbol_year_month,
    crypto_chassis_vendor,
)
ccxt_bad_data_kucoin_stats_by_year_month = ramccqa.get_bad_data_stats(
    ccxt_kucoin_data, agg_level_full_symbol_year_month, ccxt_vendor
)
#
kucoin_bad_data_stats_by_year_month_qa = ramccqa.compare_data_stats(
    crypto_chassis_bad_data_kucoin_stats_by_year_month,
    ccxt_bad_data_kucoin_stats_by_year_month,
)
kucoin_bad_data_stats_by_year_month_qa

# %%
ramccqa.plot_bad_data_by_year_month_stats(
    kucoin_bad_data_stats_by_year_month_qa, config["stats"]["threshold"]
)
