# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# This notebook performs EDA on the crypto prices and returns.

# %% [markdown]
# # Imports

# %%
# # %load_ext autoreload
# # %autoreload 2
# # %matplotlib inline

# %%
# TODO(Grisha): move to `core/dataflow_model/notebooks` in #205.

import logging
import os

import pandas as pd
import pytz

import core.config.config_ as cconconf
import core.explore as coexplor
import core.plotting as coplotti
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Config

# %%
def get_eda_config() -> cconconf.Config:
    """
    Get config that controls EDA parameters.
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
    config["data"]["close_price_col_name"] = "close"
    config["data"]["frequency"] = "T"
    config["data"]["vendor"] = "CCXT"
    config["data"]["extension"] = "csv.gz"
    # TODO(Grisha): use `hdateti.get_ET_tz()` once it is fixed.
    config["data"]["timezone"] = pytz.timezone("US/Eastern")
    # Statistics parameters.
    config.add_subconfig("stats")
    config["stats"]["z_score_boundary"] = 3
    config["stats"]["z_score_window"] = "D"
    return config


config = get_eda_config()
print(config)

# %% [markdown]
# # Load data

# %%
vendor = config["data"]["vendor"]
universe_version = "v3"
resample_1min = True
root_dir = config["load"]["data_dir"]
extension = config["data"]["extension"]
aws_profile = config["load"]["aws_profile"]
ccxt_csv_client = icdcl.CcxtCddCsvParquetByAssetClient(
    vendor,
    universe_version,
    resample_1min,
    root_dir,
    extension,
    aws_profile=aws_profile,
)
start_ts = None
end_ts = None
ccxt_data = ccxt_csv_client.read_data(
    ["binance::BTC_USDT"],
    start_ts,
    end_ts,
)
_LOG.info("shape=%s", ccxt_data.shape[0])
ccxt_data.head(3)

# %%
# Check the timezone info.
hdbg.dassert_eq(
    ccxt_data.index.tzinfo,
    config["data"]["timezone"],
)

# %%
# TODO(Grisha): change tz in `CcxtLoader` #217.
ccxt_data.index = ccxt_data.index.tz_convert(config["data"]["timezone"])
ccxt_data.index.tzinfo

# %% [markdown]
# # Select subset

# %%
ccxt_data_subset = ccxt_data[[config["data"]["close_price_col_name"]]]
ccxt_data_subset.head(3)


# %% [markdown]
# # Resample index

# %%
# TODO(Grisha): do we want to merge it with `core.pandas_helpers.resample_index`?
# The problem with `resample_index` in `pandas_helpers` is that it does not
# generate empty rows for missing timestamps.
def resample_index(index: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    """
    Resample `DatetimeIndex`.

    :param index: `DatetimeIndex` to resample
    :param frequency: frequency from `pd.date_range()` to resample to
    :return: resampled `DatetimeIndex`
    """
    hdbg.dassert_isinstance(index, pd.DatetimeIndex)
    min_date = index.min()
    max_date = index.max()
    resampled_index = pd.date_range(
        start=min_date,
        end=max_date,
        freq=frequency,
    )
    return resampled_index


resampled_index = resample_index(
    ccxt_data_subset.index, config["data"]["frequency"]
)
ccxt_data_reindex = ccxt_data_subset.reindex(resampled_index)
_LOG.info("shape=%s", ccxt_data_reindex.shape[0])
ccxt_data_reindex.head(3)

# %% [markdown]
# # Filter data

# %%
# TODO(Grisha): add support for filtering by exchange, currency, asset class.

# %%
# Get the inputs.
# TODO(Grisha): pass tz to `hdateti.to_datetime` once it is fixed.
lower_bound = hdateti.to_datetime("2019-01-01")
lower_bound_ET = config["data"]["timezone"].localize(lower_bound)
upper_bound = hdateti.to_datetime("2020-01-01")
upper_bound_ET = config["data"]["timezone"].localize(upper_bound)
# Fiter data.
ccxt_data_filtered = coexplor.filter_by_time(
    df=ccxt_data_reindex,
    lower_bound=lower_bound_ET,
    upper_bound=upper_bound_ET,
    inclusive="left",
    ts_col_name=None,
    log_level=logging.INFO,
)
ccxt_data_filtered.head(3)

# %% [markdown]
# # Statistics

# %% [markdown]
# ## Plot timeseries

# %%
# TODO(Grisha): replace with a function that does the plotting.
ccxt_data_filtered[config["data"]["close_price_col_name"]].plot()

# %% [markdown]
# ## Plot timeseries distribution

# %%
# TODO(Grisha): fix the function behavior in #204.
coplotti.plot_timeseries_distribution(
    ccxt_data_filtered[config["data"]["close_price_col_name"]],
    datetime_types=["hour"],
)

# %% [markdown]
# ## NaN statistics

# %%
nan_stats_df = coexplor.report_zero_nan_inf_stats(ccxt_data_filtered)
nan_stats_df


# %%
# TODO(Grisha): pretify the function: add assertions, logging.
# TODO(Grisha): add support for zeros, infinities.
# TODO(Grisha): also count NaNs by exchange, currency, asset class.
def count_nans_by_period(
    df: pd.DataFrame,
    config: cconconf.Config,
    period: str,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Count NaNs by period.

    :param df: data
    :param period: time period, e.g. "D" - to group by day
    :param top_n: display top N counts
    :return: table with NaN counts by period
    """
    # Select only NaNs.
    nan_data = df[df[config["data"]["close_price_col_name"]].isna()]
    # Group by specified period.
    nan_grouped = nan_data.groupby(pd.Grouper(freq=period))
    # Count NaNs.
    nan_grouped_counts = nan_grouped.apply(lambda x: x.isnull().sum())
    nan_grouped_counts.columns = ["nan_count"]
    nan_grouped_counts_sorted = nan_grouped_counts.sort_values(
        by=["nan_count"], ascending=False
    )
    return nan_grouped_counts_sorted.head(top_n)


nan_counts = count_nans_by_period(
    ccxt_data_filtered,
    config,
    "D",
)
nan_counts


# %% [markdown]
# ## Detect outliers

# %%
# TODO(Grisha): add support for other approaches, e.g. IQR-based approach.
def detect_outliers(df: pd.DataFrame, config: cconconf.Config) -> pd.DataFrame:
    """
    Detect outliers in a rolling fashion using z-score.

    If an observation has abs(z-score) > `z_score_boundary` it is considered
    an outlier. To compute a `z-score` rolling mean and rolling std are used.

    :param df: data
    :return: outliers
    """
    df_copy = df.copy()
    roll = df_copy[config["data"]["close_price_col_name"]].rolling(
        window=config["stats"]["z_score_window"]
    )
    # Compute z-score for a rolling window.
    df_copy["z-score"] = (
        df_copy[config["data"]["close_price_col_name"]] - roll.mean()
    ) / roll.std()
    # Select outliers based on the z-score.
    df_outliers = df_copy[
        abs(df_copy["z-score"]) > config["stats"]["z_score_boundary"]
    ]
    return df_outliers


outliers = detect_outliers(ccxt_data_filtered, config)
_LOG.info("shape=%s", outliers.shape[0])
outliers.head(3)
