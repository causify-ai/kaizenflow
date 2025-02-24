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
# # Description

# %% [markdown]
# This notebook computes data statistics per exchange id and currency pair for a given vendor universe.

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
import im_v2.common.universe as ivcu
import research_amp.cc.statistics as ramccsta

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Config

# %%
def get_cmtask232_config() -> cconconf.Config:
    """
    Get task232-specific config.
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
    config["data"]["data_type"] = "OHLCV"
    config["data"]["target_frequency"] = "T"
    config["data"]["universe_version"] = "v03"
    config["data"]["vendor"] = "CCXT"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["close_price"] = "close"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange_id"] = "exchange_id"
    return config


config = get_cmtask232_config()
print(config)

# %% [markdown]
# # Compute start-end table

# %% [markdown]
# ## Per exchange id and currency pair for a specified vendor

# %%
vendor_universe = ivcu.get_vendor_universe(
    config["data"]["vendor"],
    version=config["data"]["universe_version"],
    as_full_symbol=True,
)
vendor_universe

# %%
compute_start_end_stats = lambda data: ramccsta.compute_start_end_stats(
    data, config
)

start_end_table = ramccsta.compute_stats_for_universe(
    vendor_universe, config, compute_start_end_stats
)

# %%
# Post-process results.
cols_to_sort_by = ["coverage", "longest_not_nan_seq_perc"]
cols_to_round = [
    "coverage",
    "avg_data_points_per_day",
    "longest_not_nan_seq_perc",
]
stats_table = ramccsta.postprocess_stats_table(
    start_end_table, cols_to_sort_by, cols_to_round
)
stats_table

# %% [markdown]
# Looking at the results we can see that all the exchanges except for Bitfinex have significantly big longest not-NaN sequence (>13% at least) in combine with high data coverage (>85%). Bitfinex has a very low data coverage and its longest not-NaN sequence lengths are less than 1 day long and comprise less than 1% of the original data. This means that Bitfinex data spottiness is too scattered and we should exclude it from our analysis until we get clearer data for it.

# %%
_LOG.info(
    "The number of unique exchange and currency pair combinations=%s",
    start_end_table.shape[0],
)
start_end_table

# %% [markdown]
# ## Per currency pair

# %%
currency_start_end_table = ramccsta.compute_start_end_table_by_currency(
    start_end_table
)
currency_start_end_table
