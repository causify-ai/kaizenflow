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
# This notebook performs cross-vendor QA checks to compare CCXT and CryptoChassis futures data in terms of:
#    - Difference and intersection of vendor universes
#    - Time intervals, i.e. which vendor has the longest data available for each full symbol in intersecting universe
#    - Data quality (bad data [%], missing bars [%], volume=0 [%], NaNs [%]) for intersecting universe and time intervals

# %% [markdown]
# # Imports

# %%
import logging
import os

import core.config.config_ as cconconf
import core.config.config_utils as ccocouti
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
def get_cmtask2188_config() -> cconconf.Config:
    """
    Get task specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            "ccxt": {
                "universe_version": "v5",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "futures",
                "data_snapshot": "20220620",
                "aws_profile": "ck",
            },
            "crypto_chassis": {
                "universe_version": "v2",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "futures",
                "data_snapshot": "20220620",
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
config = get_cmtask2188_config()
print(config)

# %% [markdown]
# # Compare universes

# %%
crypto_chassis_client = iccdc.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["crypto_chassis"]
)
ccxt_client = icdcl.CcxtHistoricalPqByTileClient(**config["data"]["ccxt"])

# %%
# We have futures data only for Binance.
crypto_chassis_universe = [
    full_symbol
    for full_symbol in crypto_chassis_client.get_universe()
    if full_symbol.startswith("binance")
]
ccxt_universe = [
    full_symbol
    for full_symbol in ccxt_client.get_universe()
    if full_symbol.startswith("binance")
]

# %%
common_universe = list(set(crypto_chassis_universe) & set(ccxt_universe))

# %%
compare_universe = hprint.set_diff_to_str(
    crypto_chassis_universe, ccxt_universe, add_space=True
)
print(compare_universe)

# %% [markdown]
# # Compare QA stats

# %%
ccxt_binance_data = ccxt_client.read_data(
    common_universe, **config["data"]["read_data"]
)
ccxt_binance_data.head(3)

# %%
crypto_chassis_binance_data = crypto_chassis_client.read_data(
    common_universe, **config["data"]["read_data"]
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

# %%
