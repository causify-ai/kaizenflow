# -*- coding: utf-8 -*-
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
# # Description

# %% [markdown]
# This notebook explores approaches to detect outliers in crypto data.

# %% [markdown]
# # Imports

# %%
import logging
import os

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hs3 as hs3
import im_v2.ccxt.data.client as icdcl
import research_amp.cc.detect_outliers as raccdeou

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

AM_AWS_PROFILE = "am"

# %% [markdown]
# # Load test data

# %%
vendor = "CCXT"
universe_version = "v3"
resample_1min = True
root_dir = os.path.join(hs3.get_s3_bucket_path(AM_AWS_PROFILE), "data")
extension = "csv.gz"
ccxt_csv_client = icdcl.CcxtCddCsvParquetByAssetClient(
    vendor,
    universe_version,
    resample_1min,
    root_dir,
    extension,
    aws_profile=AM_AWS_PROFILE,
)
start_ts = None
end_ts = None
data = ccxt_csv_client.read_data(
    ["kucoin::ETH_USDT"],
    start_ts,
    end_ts,
)
data.head()

# %% [markdown]
# Get multiple chunks of the latest data for performance checks.

# %%
# Exactly 10-days length chunk.
chunk_10days = data.tail(14400).copy()
# Exactly 20-days length chunk.
chunk_20days = data.tail(28800).copy()
# Exactly 40-days length chunk.
chunk_40days = data.tail(57600).copy()

# %% [markdown]
# # Mask approach

# %% [markdown]
# Below you can see that execution time grows exponentially to the growth of input series chunk.
#
# If we take number of days in chunk as `x` for a rough approximation, rounded execution time in seconds as `y`, and build an equation that corresponds to the test samples then we get the following:<br>
# `y = (11/1500)x^2 + (3/4)x + (4/15)`<br>
#
# Then processing full 1619960 length series should take ~3-4 hours to complete so we should think about the ways to apply this function effectively.

# %%
# %%time
outlier_mask_10days = raccdeou.detect_outliers(
    srs=chunk_10days["close"], n_samples=1440, z_score_threshold=4
)

# %%
# %%time
outlier_mask_20days = raccdeou.detect_outliers(
    srs=chunk_20days["close"], n_samples=1440, z_score_threshold=4
)

# %%
# %%time
outlier_mask_40days = raccdeou.detect_outliers(
    srs=chunk_40days["close"], n_samples=1440, z_score_threshold=4
)

# %% [markdown]
# Another problem with this approach is that its results are not robust to the cases when a harsh ascent or decline has happened and the price direction has continued. In this case all the values after this harsh change are considered outliers and dropped.
#
# Take a look at 10-days chunk result. It has 76% of its values considered outliers with Z-score threshold equals 4 while 3 is a standard. After 2021-09-07 04:25:00-04:00 the price falls from 3848.65 to 3841.97 and all the following observations that are below 3841.95 are considered outliers as well.<br>
#
# This is expected since we do not implement window data normalization before computing z-scores while the data we have clearly has trends at least and the values on the brick of z-score window can easily drop out from standard z-score threshold.
#
# Since crypto data is very volatile, we can end up with losing a lot of data in this case so we should consider the right values for window sample size and Z-scores.

# %%
outlier_mask_10days.sum() / outlier_mask_10days.shape[0]

# %%
outlier_mask_10days[:3426]

# %%
outlier_mask_10days[3426:]

# %%
set(outlier_mask_10days[3426:])

# %%
chunk_10days["close"][~outlier_mask_10days].tail()

# %%
chunk_10days["close"][outlier_mask_10days].head()

# %% [markdown]
# All the other chunks have a lot of false outliers as well.

# %%
print(outlier_mask_20days.sum() / outlier_mask_20days.shape[0])
print(outlier_mask_40days.sum() / outlier_mask_40days.shape[0])


# %% [markdown]
# # Dropping outliers on-flight approach

# %%
def remove_outlier_at_index(
    srs: pd.Series,
    z_score_boundary: int,
    z_score_window_size: int,
    index_to_check: int,
) -> pd.Series:
    """
    Check if a series value at index is an outlier and remove it if so.

    Index should be a row of positive integers like 0, 1, 2, etc.

    Z-score window indices are adjusting with respect to its size, the size of input
    and index to check.

    Z-score window size is an integer number of index steps that will be included
    in Z-score computation and outlier detection.

    :param srs: input series
    :param z_score_boundary: boundary value to check for outlier's Z-score
    :param z_score_window_size: size of the window to compute Z-score for
    :param index_to_check: index of a value to check
    :return: input series with removed value at given index if it was considered an outlier
    """
    # Get numerical order of a given index.
    index_order = srs.index.get_loc(index_to_check)
    # Set window indices.
    window_first_index = max(0, index_order - z_score_window_size)
    window_last_index = max(index_order, window_first_index + z_score_window_size)
    # Verify that distance between window indices equals Z-score window size
    # and that index to check is laying between these indices.
    hdbg.dassert_eq(z_score_window_size, window_last_index - window_first_index)
    hdbg.dassert_lte(window_first_index, index_order)
    hdbg.dassert_lte(index_order, window_last_index)
    # Get a window to compute Z-score for.
    window_srs = srs.iloc[window_first_index:window_last_index].copy()
    # Compute Z-score of a value at index.
    z_score = (srs[index_order] - window_srs.mean()) / window_srs.std()
    # Drop the value if its Z-score is None or laying beyond the specified boundaries.
    if not abs(z_score) <= z_score_boundary:
        srs = srs.drop([index_to_check]).copy()
    return srs


def remove_rolling_outliers(
    df: pd.DataFrame,
    col: str,
    z_score_boundary: int,
    z_score_window: int,
) -> pd.DataFrame:
    """
    Remove outliers using a rolling window.

    Outliers are being removed consequtively after every window check.

    Z-score window indices are adjusting with respect to its size, the size of input
    and index to check.

    Z-score window size is an integer number of index steps that will be included
    in Z-score computation and outlier detection.

    :param srs: input dataframe
    :param col: column to check for outliers
    :param z_score_boundary: Z-score boundary to check the value
    :param z_score_window: size of the window to compute Z-score for
    :return: dataframe with removed outliers
    """
    # Get a series to detect outliers in.
    price_srs = df[col].copy()
    # Iterate over series indices.
    for index_ in price_srs.index:
        # For every index check if its value is an outlier and
        # remove it from the series if so.
        price_srs = remove_outlier_at_index(
            price_srs, z_score_boundary, z_score_window, index_
        )
    # Get dataframe rows that correspond to the non-outliers indices.
    clean_df = df[df.index.isin(price_srs.index)].copy()
    return clean_df


# %% [markdown]
# Dropping outliers on-flight approach seems to work slower on small chunks and its execution time grows exponentially to the series length as well.
#
# So needless to say, its less effective than the mask one and should not be used.

# %%
# %%time
old_clean_chunk_10days = remove_rolling_outliers(chunk_10days, "close", 3, 1440)

# %%
# %%time
old_clean_chunk_20days = remove_rolling_outliers(chunk_20days, "close", 3, 1440)

# %%
# %%time
old_clean_chunk_40days = remove_rolling_outliers(chunk_40days, "close", 3, 1440)


# %% [markdown]
# # Overlapping windows approach

# %%
def detect_outliers_new(
    srs: pd.Series,
    n_samples: int = 1440,
    window_step: int = 10,
    z_score_threshold: float = 3.0,
):
    """
    Detect outliers using overlapping windows and averaged z-scores of each
    observation.

    Almost every observation will belong to `n_samples` of windows which means that each one
    is going to have `n_samples` of Z-scores. The mean of these scores will give an averaged
    Z-score which will be a more robust metrics to check if a value is an outlier than
    a rolling Z-score computed just once.

    This function
    - creates list of overlapping z-score windows
    - computes z-score of each element in every window
    - for each observation takes average of all the z-scores from the windows it belongs to
    - compares averaged z-score to the threshold to declare the current element an outlier

    :param srs: input series
    :param n_samples: number of samples in z-score windows
    :param z_score_threshold: threshold to mark a value as an outlier based on its averaged z-score
    :return: whether the element at index idx is an outlier
    """
    # Create a list of overlapping windows.
    windows = [
        srs.iloc[idx : idx + n_samples]
        for idx in range(0, srs.shape[0] - n_samples + window_step, window_step)
    ]
    # Compute z-score for each observation in every window.
    z_scores_list = [
        abs((window - window.mean()) / window.std()) for window in windows
    ]
    # Concatenate z-scores series in one.
    z_scores_srs = pd.concat(z_scores_list)
    # Groupby by index and take the averaged z-score for every index value.
    z_scores_stats = z_scores_srs.groupby(z_scores_srs.index).mean()
    # Get a mask for outliers.
    # Done via `<=` since a series can contain None values that should be detected
    # as well but will result to NaN if compared to the threshold directly.
    outliers_mask = ~(z_scores_stats <= z_score_threshold)
    return outliers_mask


# %% [markdown]
# Since both approaches suggested above are very slow and can't be really applied to all the data directly, I'd like to propose another approach to this problem.
#
# Description of the approach can be found in a function docstrings. In short, this is not an approach that has a memory but here we compute an averaged z-score for each observation for multiple windows it belongs to. IMO this should make outlier detection more robust and give consistent results for most observations (only corner cases may differ, no observations are removed so full-sized windows are always constant).
#
# This approach might be less robust to consecutive outliers than the previous ones but it demonstrates extremely faster performance. it processes the whole series in just 2 minutes with 1-day sized windows that overlap each 10 minutes.<br>
# Therefore, if this algorithm robustness is enough for us, I suggest we use it for outlier detection.

# %%
all_outliers_mask = detect_outliers_new(data["close"])

# %% [markdown]
# The algorithm detects None values and the small amount of outliers.

# %%
all_outliers = data["close"][all_outliers_mask]
len(all_outliers)

# %%
len(all_outliers.dropna())

# %% [markdown]
# Computations for small chunks are done almost immediately, all the detected outliers are stable across the chunks.

# %%
outlier_mask_new_40days = detect_outliers_new(chunk_40days["close"]).dropna()

# %%
chunk_40days["close"][outlier_mask_new_40days]

# %%
outlier_mask_new_20days = detect_outliers_new(chunk_20days["close"]).dropna()

# %%
chunk_20days["close"][outlier_mask_new_20days]

# %%
outlier_mask_new_10days = detect_outliers_new(chunk_10days["close"]).dropna()

# %%
chunk_10days["close"][outlier_mask_new_10days]
