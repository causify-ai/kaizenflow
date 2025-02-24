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
import core.config.config_utils as ccocouti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
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
def get_cmtask2329_config() -> cconconf.Config:
    """
    Get task2329-specific config.
    """
    config = cconconf.Config()
    param_dict = {
        "data": {
            # Parameters for client initialization.
            "im_client": {
                "universe_version": "v4",
                "resample_1min": False,
                "root_dir": os.path.join(
                    hs3.get_s3_bucket_path("ck"), "reorg", "historical.manual.pq"
                ),
                "partition_mode": "by_year_month",
                "dataset": "ohlcv",
                "contract_type": "futures",
                "data_snapshot": "20220707",
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


config = get_cmtask2329_config()
print(config)

# %% [markdown]
# # Load the data

# %%
client = iccdc.CryptoChassisHistoricalPqByTileClient(
    **config["data"]["im_client"]
)

# %%
universe = client.get_universe()
universe

# %%
data = client.read_data(universe, **config["data"]["read_data"])
data.head(3)

# %% [markdown]
# # QA checks

# %% [markdown]
# Major metric for a QA check is `"bad data [%]"` which is the sum of `"volume=0 [%]"` and `"NaNs [%]"`.

# %%
vendor_name = "CryptoChassis"
binance_timestamp_stats = ramccqa.get_timestamp_stats(data, vendor_name)
binance_timestamp_stats

# %%
agg_level_full_symbol = ["full_symbol"]
binance_bad_data_stats = ramccqa.get_bad_data_stats(
    data, agg_level_full_symbol, vendor_name
)
binance_bad_data_stats

# %%
agg_level_full_symbol_year_month = ["full_symbol", "year", "month"]
bad_data_stats_by_year_month = ramccqa.get_bad_data_stats(
    data, agg_level_full_symbol_year_month, vendor_name
)
bad_data_stats_by_year_month

# %%
_ = ramccqa.plot_bad_data_by_year_month_stats(
    bad_data_stats_by_year_month, config["stats"]["threshold"]
)
