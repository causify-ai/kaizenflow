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
import im_v2.ccxt.universe.universe as imvccunun
import research_amp.cc.statistics as ramccsta

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Configs

# %%
# Generate configs for `CDD` and `CCXT`.

# %%
def get_cmtask324_config_ccxt() -> cconconf.Config:
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
    config["data"]["target_frequency"] = "T"
    config["data"]["universe_version"] = "v03"
    config["data"]["vendor"] = "CCXT"
    config["data"]["extension"] = "csv.gz"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["close_price"] = "close"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange_id"] = "exchange_id"
    return config


# %%
config_ccxt = get_cmtask324_config_ccxt()
print(config_ccxt)


# %%
def get_cmtask324_config_cdd() -> cconconf.Config:
    """
    Get task324-specific config.
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
    config["data"]["target_frequency"] = "T"
    config["data"]["universe_version"] = "v01"
    config["data"]["vendor"] = "CDD"
    config["data"]["extension"] = "csv.gz"
    # Column names.
    config.add_subconfig("column_names")
    config["column_names"]["close_price"] = "close"
    config["column_names"]["currency_pair"] = "currency_pair"
    config["column_names"]["exchange_id"] = "exchange_id"
    return config


# %%
config_cdd = get_cmtask324_config_cdd()
print(config_cdd)

# %% [markdown]
# # Load the data universe

# %% [markdown]
# ## CCXT

# %%
ccxt_universe = imvccunun.get_vendor_universe(version="v3")

# %% [markdown]
# ## CDD

# %% run_control={"marked": false}
# TODO(Juraj): this got deprecated with #CmTask1493 and #CmTask1487
cdd_universe = imvccunun.get_vendor_universe(version="v01", vendor="CDD")
# Remove non-USDT elements, since we are not interested in them.
cdd_universe = [element for element in cdd_universe if element.endswith("USDT")]

# %% [markdown]
# # Compare universes

# %%
_LOG.info("Number of full symbols in 'CCXT': %s", len(ccxt_universe))
_LOG.info("Number of full symbols in 'CDD': %s", len(cdd_universe))

# %%
# Intersection of full symbols between two vendors.
currency_pair_intersection = set(ccxt_universe).intersection(cdd_universe)
_LOG.info("Number of similar full symbols: %s", len(currency_pair_intersection))
display(currency_pair_intersection)

# %%
# Full symbols that are included in `CCXT` but not in `CDD`.
ccxt_and_not_cdd = set(ccxt_universe).difference(cdd_universe)
_LOG.info(
    "Number of full symbols that are included in 'CCXT' but not in 'CDD': %s",
    len(ccxt_and_not_cdd),
)
display(ccxt_and_not_cdd)

# %%
# Full symbols that are included in `CDD` but not in `CCXT`.
cdd_and_not_ccxt = set(cdd_universe).difference(ccxt_universe)
_LOG.info(
    "Number of full symbols that are included in 'CDD' but not in 'CCXT': %s",
    len(cdd_and_not_ccxt),
)
display(cdd_and_not_ccxt)

# %% [markdown]
# # Compare close prices / returns from Binance

# %% [markdown]
# ## Load the data

# %% [markdown]
# The code below can be used to load all the existing data from two vendors `CDD` and `CCXT`. Current version is specified to Binance only, however, even for one exchange there's too many data to operate, that's why the output is the intersection of currency pairs between to universe, since one can compare only the intersection of currency pairs for two vendors.

# %%
# Load Binance-specific universe for `CCXT`.
ccxt_binance_universe = [
    element for element in ccxt_universe if element.startswith("binance")
]
# Load Binnance-specific universe for `CDD`.
cdd_binance_universe_initial = [
    element for element in cdd_universe if element.startswith("binance")
]
cdd_binance_universe = cdd_binance_universe_initial.copy()
# SCU_USDT has incorrect columns, so can not be downloaded.
# See CMTask244 - Cannot load CDD - binance - SCU/USDT from s3 for the reference.
cdd_binance_universe.remove("binance::SCU_USDT")
# The intersection of Binance currency pairs from two universes.
currency_pair_intersection_binance = set(ccxt_binance_universe).intersection(
    cdd_binance_universe_initial
)

# %% [markdown]
# ### "CDD"

# %%
vendor_cdd = config_cdd["data"]["vendor"]
universe_version = "v3"
resample_1min = True
root_dir_cdd = config_cdd["load"]["data_dir"]
extension_cdd = config["data"]["extension"]
aws_profile_cdd = config_cdd["load"]["aws_profile"]
cdd_csv_client = icdcl.CcxtCddCsvParquetByAssetClient(
    vendor_cdd,
    universe_version,
    resample_1min,
    root_dir_cdd,
    extension_cdd,
    aws_profile=aws_profile_cdd,
)

start_ts = None
end_ts = None
cdd_binance_df = cdd_csv_client.read_data(
    list(currency_pair_intersection_binance),
    start_ts,
    end_ts,
)

# %%
display(cdd_binance_df.head(3))
display(cdd_binance_df.shape)

# %% [markdown]
# ### "CCXT"

# %%
vendor_ccxt = config_ccxt["data"]["vendor"]
universe_version = "v3"
resample_1min = True
root_dir_ccxt = config_ccxt["load"]["data_dir"]
extension_ccxt = config["data"]["extension"]
aws_profile_ccxt = config_ccxt["load"]["aws_profile"]
ccxt_csv_client = icdcl.CcxtCddCsvParquetByAssetClient(
    vendor_ccxt,
    universe_version,
    resample_1min,
    root_dir_ccxt,
    extension_ccxt,
    aws_profile=aws_profile_ccxt,
)

start_ts = None
end_ts = None
ccxt_binance_df = ccxt_csv_client.read_data(
    list(currency_pair_intersection_binance),
    start_ts,
    end_ts,
)

# %%
display(ccxt_binance_df.head(3))
display(ccxt_binance_df.shape)


# %% [markdown]
# ## Calculate returns and correlation

# %%
def resample_close_price(df: pd.DataFrame, resampling_freq: str) -> pd.Series:
    """
    Resample close price on the currency level to the specified frequency using
    the last close price.

    :param df: OHLCV data
    :param resampling_freq: frequency from `pd.date_range()` to resample to
    :return: resampled close price per currency
    """
    # Reseting DateTime index, since pd.Grouper can't use index values.
    df = df.reset_index().rename(columns={"index": "stamp"})
    # Group by currency pairs and simultaneously resample to the desired frequency.
    resampler = df.groupby(
        ["currency_pair", pd.Grouper(key="timestamp", freq=resampling_freq)]
    )
    # Take the last close value from each resampling period.
    close_series = resampler.close.last()
    return close_series


# %%
def calculate_correlations(
    ccxt_close_price: pd.Series, cdd_close_price: pd.Series, compute_returns: bool
) -> pd.DataFrame:
    """
    Take CCXT and CDD close prices and calculate the correlations for each
    specific currency pair.

    :param ccxt_series: resampled close price per currency for CCXT
    :param cdd_series: resampled close price per currency for CDD
    :param compute_returns: if True - compare returns, if False - compare close prices
    :return: correlation matrix per currency
    """
    if compute_returns:
        # Group by currency pairs in order to calculate the percentage returns.
        grouper_cdd = cdd_close_price.groupby("currency_pair")
        cdd_close_price = grouper_cdd.pct_change()
        grouper_ccxt = ccxt_close_price.groupby("currency_pair")
        ccxt_close_price = grouper_ccxt.pct_change()
    # Combine and calculate correlations.
    combined = pd.merge(
        cdd_close_price, ccxt_close_price, left_index=True, right_index=True
    )
    # Rename the columns.
    if compute_returns:
        combined.columns = ["ccxt_returns", "cdd_returns"]
    else:
        combined.columns = ["cdd_close", "ccxt_close"]
    # Group by again to calculte returns correlation for each currency pair.
    corr_matrix = combined.groupby(level=0).corr()
    return corr_matrix


# %%
# Corresponding resampled Series.
daily_frequency = "1D"
ccxt_binance_series_1d = resample_close_price(ccxt_binance_df, daily_frequency)
cdd_binance_series_1d = resample_close_price(cdd_binance_df, daily_frequency)

five_min_frequency = "5min"
ccxt_binance_series_5min = resample_close_price(
    ccxt_binance_df, five_min_frequency
)
cdd_binance_series_5min = resample_close_price(cdd_binance_df, five_min_frequency)

# %% [markdown]
# ### 1-day returns

# %%
compute_returns = True
returns_corr_1day = calculate_correlations(
    ccxt_binance_series_1d, cdd_binance_series_1d, compute_returns
)
display(returns_corr_1day)

# %% [markdown]
# ### 5-min returns

# %%
compute_returns = True
returns_corr_5min = calculate_correlations(
    ccxt_binance_series_5min, cdd_binance_series_5min, compute_returns
)
display(returns_corr_5min)

# %% [markdown]
# ## Compare close prices

# %% [markdown]
# ### 1-day close prices

# %%
compute_returns = False
close_corr_1day = calculate_correlations(
    ccxt_binance_series_1d, cdd_binance_series_1d, compute_returns
)
display(close_corr_1day)

# %% [markdown]
# ### 5-min close prices

# %%
compute_returns = False
close_corr_5min = calculate_correlations(
    ccxt_binance_series_5min, cdd_binance_series_5min, compute_returns
)
display(close_corr_5min)

# %% [markdown]
# # Statistical properties of a full symbol in CDD

# %%
# Clearing `CDD` currency pairs that are incorrect.

# Binance.
cdd_universe.remove("binance::SCU_USDT")

# FTX has some critical mistakes in the downloading process, so can not continue analysis with them.
# see CMTask801 - Downloading issues of FTX exchange from 'CDD' universe for further reference.
cdd_ftx_universe = [
    element for element in cdd_universe if element.startswith("ftx")
]
for elem in cdd_ftx_universe:
    cdd_universe.remove(elem)

# Kucoin exchange: the timestamps are obviously wrong and with too short time period.
# See CMTask253 - Fix timestamp for CDD - kucoin for reference.
cdd_kucoin_universe = [
    element for element in cdd_universe if element.startswith("kucoin")
]
for elem in cdd_kucoin_universe:
    cdd_universe.remove(elem)

# %% [markdown]
# ## Comparison of intersection of full symbols between 'CCXT' and 'CDD'

# %%
# Full symbols that are included in `CDD` but not in `CCXT` (cleaned from unavailable full symbols).
cdd_and_ccxt_cleaned = set(ccxt_universe).intersection(cdd_universe)
len(cdd_and_ccxt_cleaned)

# %% [markdown]
# ### Load the intersection of full symbols for 'CDD' and 'CCXT'

# %% [markdown]
# #### CDD

# %%
compute_start_end_stats = lambda data: ramccsta.compute_start_end_stats(
    data, config_cdd
)

cdd_start_end_table = ramccsta.compute_stats_for_universe(
    cdd_and_ccxt_cleaned, config_cdd, compute_start_end_stats
)

# %%
cdd_start_end_table.head(3)

# %% [markdown]
# #### CCXT

# %%
compute_start_end_stats = lambda data: ramccsta.compute_start_end_stats(
    data, config_ccxt
)

ccxt_start_end_table = ramccsta.compute_stats_for_universe(
    cdd_and_ccxt_cleaned, config_ccxt, compute_start_end_stats
)

# %%
ccxt_start_end_table.head(3)


# %% [markdown]
# ### Display the union results

# %%
def unify_start_end_tables(
    cdd_df: pd.DataFrame, ccxt_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Combine 'CCXT' and 'CDD' start-end stats tables into one table.

    :param cdd_df: start-end table for 'CCXT'
    :param ccxt_df: start-end table for 'CDD'
    :return: unified start-end table
    """
    # Set Multiindex.
    cdd_df = cdd_df.set_index(["exchange_id", "currency_pair"])
    ccxt_df = ccxt_df.set_index(["exchange_id", "currency_pair"])
    # Add suffixes.
    ccxt_df = ccxt_df.add_suffix("_ccxt")
    cdd_df = cdd_df.add_suffix("_cdd")
    # Combine two universes.
    ccxt_and_cdd = pd.concat([cdd_df, ccxt_df], axis=1)
    # Sort columns.
    cols_to_sort = ccxt_and_cdd.columns.to_list()
    ccxt_and_cdd = ccxt_and_cdd[sorted(cols_to_sort)]
    return ccxt_and_cdd


# %%
union_cdd_ccxt_stats = unify_start_end_tables(
    cdd_start_end_table, ccxt_start_end_table
)
display(union_cdd_ccxt_stats)

# %% [markdown]
# ## Comparison of full symbols that are included in 'CDD' but not available in 'CCXT'

# %%
# Set of full symbols that are included in `CDD` but not available in `CCXT` (cleaned from unavailable full symbols).
cdd_and_not_ccxt_cleaned = set(cdd_universe).difference(ccxt_universe)
len(cdd_and_not_ccxt_cleaned)

# %%
# For 'avg_data_points_per_day' the amount of "days_available" is equal to 0, so it crashes the calculations.
cdd_and_not_ccxt_cleaned.remove("binance::DAI_USDT")

# %%
compute_start_end_stats = lambda data: ramccsta.compute_start_end_stats(
    data, config_cdd
)

cdd_unique_start_end_table = ramccsta.compute_stats_for_universe(
    cdd_and_not_ccxt_cleaned, config_cdd, compute_start_end_stats
)

# %%
display(cdd_unique_start_end_table)
