"""
Import as:

import core.finance.resampling as cfinresa
"""


import collections
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
import pandas as pd

import core.finance.prediction_processing as cfiprpro
import helpers.hdbg as hdbg
import helpers.htypes as htypes

_LOG = logging.getLogger(__name__)


# #############################################################################
# Resampling.
# #############################################################################


def compute_vwap(
    df: pd.DataFrame,
    rule: str,
    price_col: str,
    volume_col: str,
    # TODO(gp): Add *
    # *,
    offset: Optional[str] = None,
) -> pd.Series:
    """
    Compute VWAP from price and volume columns.

    :param df: input dataframe with datetime index
    :param rule: resampling frequency and VWAP aggregation window
    :param price_col: price for bar
    :param volume_col: volume for bar
    :param offset: offset in the Pandas format (e.g., `1T`) used to shift the
        sampling
    :return: vwap price series
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    hdbg.dassert_in(price_col, df.columns)
    hdbg.dassert_in(volume_col, df.columns)
    # Only use rows where both price and volume are non-NaN.
    non_nan_idx = df[[price_col, volume_col]].dropna().index
    price = df[price_col].loc[non_nan_idx].reindex(index=df.index)
    volume = df[volume_col].loc[non_nan_idx].reindex(index=df.index)
    # Weight price according to volume.
    volume_weighted_price = price.multiply(volume)
    resampled_volume_weighted_price = resample(
        volume_weighted_price,
        rule=rule,
        offset=offset,
    ).sum(min_count=1)
    resampled_volume = resample(volume, rule=rule, offset=offset).sum(min_count=1)
    # Complete the VWAP calculation.
    vwap = resampled_volume_weighted_price.divide(resampled_volume)
    # Replace infs with NaNs.
    vwap = vwap.replace([-np.inf, np.inf], np.nan)
    vwap.name = "vwap"
    return vwap


def _resample_with_aggregate_function(
    df: pd.DataFrame,
    rule: str,
    cols: List[str],
    agg_func: str,
    agg_func_kwargs: htypes.Kwargs,
    # TODO(gp): Add *
    # *,
    resample_kwargs: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Resample columns `cols` of `df` using the passed parameters.
    """
    hdbg.dassert(not df.empty)
    hdbg.dassert_isinstance(cols, list)
    hdbg.dassert(cols, msg="`cols` must be nonempty.")
    hdbg.dassert_is_subset(cols, df.columns)
    if resample_kwargs is None:
        resample_kwargs = {}
    resampler = resample(df[cols], rule=rule, **resample_kwargs)
    resampled = resampler.agg(agg_func, **agg_func_kwargs)
    return resampled


def resample_bars(
    df: pd.DataFrame,
    rule: str,
    resampling_groups: List[Tuple[Dict[str, str], str, htypes.Kwargs]],
    vwap_groups: List[Tuple[str, str, str]],
    # TODO(gp): Add *
    # *,
    resample_kwargs: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Resampling with optional VWAP.

    Output column names must not collide.

    :param resampling_groups: list of tuples of the following form:
        (col_dict, aggregation function, aggregation kwargs)
    :param vwap_groups: list of tuples of the following form:
        (in_price_col_name, in_vol_col_name, vwap_col_name)
    """
    results = []
    for col_dict, agg_func, agg_func_kwargs in resampling_groups:
        resampled = _resample_with_aggregate_function(
            df,
            rule=rule,
            cols=list(col_dict.keys()),
            agg_func=agg_func,
            agg_func_kwargs=agg_func_kwargs,
            resample_kwargs=resample_kwargs,
        )
        resampled = resampled.rename(columns=col_dict)
        hdbg.dassert(not resampled.columns.has_duplicates)
        results.append(resampled)
    if isinstance(resample_kwargs, dict) and "offset" in resample_kwargs:
        offset = resample_kwargs["offset"]
    else:
        offset = None
    for price_col, volume_col, vwap_col in vwap_groups:
        vwap = compute_vwap(
            df,
            rule=rule,
            price_col=price_col,
            volume_col=volume_col,
            offset=offset,
        )
        vwap.name = vwap_col
        results.append(vwap)
    out_df = pd.concat(results, axis=1)
    hdbg.dassert(not out_df.columns.has_duplicates)
    hdbg.dassert(out_df.index.freq)
    return out_df


def resample_portfolio_bar_metrics(
    df: pd.DataFrame,
    freq: str,
    *,
    pnl_col: str = "pnl",
    gross_volume_col: str = "gross_volume",
    net_volume_col: str = "net_volume",
    gmv_col: str = "gmv",
    nmv_col: str = "nmv",
) -> pd.DataFrame:
    def _resample_portfolio_bar_metrics(
        df: pd.DataFrame,
        freq: str,
        pnl_col: str,
        gross_volume_col: str,
        net_volume_col: str,
        gmv_col: str,
        nmv_col: str,
    ) -> pd.DataFrame:
        # TODO(Paul): For this type of resampling, we generally want to
        # annotate with the left side of the interval. Plumb this through
        # the call stack.
        resampled_df = resample_bars(
            df,
            freq,
            resampling_groups=[
                (
                    {
                        pnl_col: "pnl",
                        gross_volume_col: "gross_volume",
                        net_volume_col: "net_volume",
                    },
                    "sum",
                    {"min_count": 1},
                ),
                (
                    {
                        gmv_col: "gmv",
                        nmv_col: "nmv",
                    },
                    "mean",
                    {},
                ),
            ],
            vwap_groups=[],
            resample_kwargs={
                "closed": None,
                "label": None,
            },
        )
        return resampled_df

    if df.columns.nlevels == 1:
        resampled_df = _resample_portfolio_bar_metrics(
            df,
            freq,
            pnl_col,
            gross_volume_col,
            net_volume_col,
            gmv_col,
            nmv_col,
        )
    elif df.columns.nlevels == 2:
        keys = df.columns.levels[0].to_list()
        resampled_dfs = collections.OrderedDict()
        for key in keys:
            resampled_df = _resample_portfolio_bar_metrics(
                df[key],
                freq,
                pnl_col,
                gross_volume_col,
                net_volume_col,
                gmv_col,
                nmv_col,
            )
            resampled_dfs[key] = resampled_df
        resampled_df = pd.concat(
            resampled_dfs.values(), axis=1, keys=resampled_dfs.keys()
        )
    else:
        raise ValueError(
            "Unexpected number of column levels nlevels=%d",
            df.columns.nlevels,
        )
    return resampled_df


def build_repeating_pattern_srs(
    df: pd.DataFrame, pattern: List[Any]
) -> pd.Series:
    """
    Build a series of repeating pattern values aligned with input df index.

    Alignment to the input df index means:
    - output series has the same index as the input df index
    - the input pattern of values repeats (cyclical)
    - the input pattern should start at the 1st minute offset

    :param df: input DataFrame to use for alignment
    :param pattern: pattern of values to repeat
    :return: series of repeating pattern values
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    index = df.index
    hdbg.dassert(index.freq, "Index has no specified freq.")
    hdbg.dassert_eq(index.freq, "1T")
    # Get pattern and index lengths.
    pattern_len = len(pattern)
    index_len = len(index)
    # 1) Build the 1st part of the output preceding full pattern repeats.
    first_index = index[0]
    # Dividing remainder of the number of minutes in the 1st index value
    # by the pattern length indicates how many minutes precede
    # the 1st minute offset in the input index.
    first_index_remainder = first_index.minute % pattern_len
    _LOG.debug("first_index_remainder=%s", first_index_remainder)
    # Add pattern values corresponding to the first indices preceding
    # the 1st minute offset.
    res_values = pattern[first_index_remainder - 1 :]
    # 2) Add the middle part of the output with full repeating patterns.
    remaining_index_len = index_len - len(res_values)
    # Compute how many times the pattern will repeat within the remaining
    # index timeframe.
    num_repeats = remaining_index_len // pattern_len
    _LOG.debug("num_repeats=%s", num_repeats)
    # Add repeating patterns to the result.
    res_values.extend(pattern * num_repeats)
    # 3) Add the last part of the output for remaining tail of indices.
    num_tail = remaining_index_len % pattern_len
    _LOG.debug("num_tails=%s", num_tail)
    res_values.extend(pattern[:num_tail])
    # Check that the count of result values matches index length.
    hdbg.dassert_eq(len(res_values), index_len)
    # Build result series.
    res = pd.Series(data=res_values, index=index)
    return res


def resample_with_weights(
    df: pd.DataFrame,
    rule: str,
    col: str,
    weights: List[float],
) -> pd.DataFrame:
    """
    Resample data to a weighted average of values.

    :param df: input data
    :param rule: resampling frequency with pandas convention (e.g., "5T")
    :param col: column name with values to resample
    :param weights: list of weights to apply to resampler group values
    :return: df[col] resampled with `rule` and weighted by `weights`
    """
    # Check that number of weights equals the rule length in minutes.
    n_minutes_rule = pd.Timedelta(rule).total_seconds() // 60
    hdbg.dassert_eq(n_minutes_rule, len(weights))
    # Get weights series aligned to the input data index.
    weight_srs = build_repeating_pattern_srs(df, weights)
    weight_srs.name = "weight"
    # Get resampled data using VWAP computation approach.
    combined_df = pd.concat([df[col], weight_srs], axis=1)
    weight_col = "weight"
    resampled_srs = compute_vwap(combined_df, rule, col, weight_col)
    resampled_srs.name = col
    resampled_df = resampled_srs.to_frame()
    return resampled_df


# TODO(Paul): Consider deprecating.
# This provides some sensible defaults for `resample_bars()`, but may not be
# worth the additional complexity.
def resample_time_bars(
    df: pd.DataFrame,
    rule: str,
    *,
    return_cols: Optional[List[str]] = None,
    return_agg_func: Optional[str] = None,
    return_agg_func_kwargs: Optional[htypes.Kwargs] = None,
    price_cols: Optional[List[str]] = None,
    price_agg_func: Optional[str] = None,
    price_agg_func_kwargs: Optional[htypes.Kwargs] = None,
    volume_cols: Optional[List[str]] = None,
    volume_agg_func: Optional[str] = None,
    volume_agg_func_kwargs: Optional[htypes.Kwargs] = None,
) -> pd.DataFrame:
    """
    Convenience resampler for time bars.

    Features:
    - Respects causality
    - Chooses sensible defaults:
      - returns are summed
      - prices are averaged
      - volume is summed
    - NaN intervals remain NaN
    - Defaults may be overridden (e.g., choose `last` instead of `mean` for
      price)

    :param df: input dataframe with datetime index
    :param rule: resampling frequency with pandas convention (e.g., "5T")
    :param return_cols: columns containing returns
    :param return_agg_func: aggregation function, default is "sum"
    :param return_agg_func_kwargs: kwargs
    :param price_cols: columns containing price
    :param price_agg_func: aggregation function, default is "mean"
    :param price_agg_func_kwargs: kwargs
    :param volume_cols: columns containing volume
    :param volume_agg_func: aggregation function, default is "sum"
    :param volume_agg_func_kwargs: kwargs
    :return: dataframe of resampled time bars with columns from `*_cols` variables,
        although not in the same order as passed
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    resampling_groups = []
    if return_cols:
        col_mapping = {col: col for col in return_cols}
        agg_func = return_agg_func or "sum"
        agg_func_kwargs = return_agg_func_kwargs or {"min_count": 1}
        group = (col_mapping, agg_func, agg_func_kwargs)
        resampling_groups.append(group)
    if price_cols:
        col_mapping = {col: col for col in price_cols}
        agg_func = price_agg_func or "mean"
        agg_func_kwargs = price_agg_func_kwargs or {}
        group = (col_mapping, agg_func, agg_func_kwargs)
        resampling_groups.append(group)
    if volume_cols:
        col_mapping = {col: col for col in volume_cols}
        agg_func = volume_agg_func or "sum"
        agg_func_kwargs = volume_agg_func_kwargs or {"min_count": 1}
        group = (col_mapping, agg_func, agg_func_kwargs)
        resampling_groups.append(group)
    result_df = resample_bars(
        df,
        rule=rule,
        resampling_groups=resampling_groups,
        vwap_groups=[],
    )
    return result_df


def resample_ohlcv_bars(
    df: pd.DataFrame,
    rule: str,
    *,
    open_col: Optional[str] = "open",
    high_col: Optional[str] = "high",
    low_col: Optional[str] = "low",
    close_col: Optional[str] = "close",
    volume_col: Optional[str] = "volume",
    add_twap_vwap: bool = False,
) -> pd.DataFrame:
    """
    Resample OHLCV bars and optionally add TWAP, VWAP prices based on "close".

    TODO(Paul): compare to native pandas `ohlc` resampling.

    :param df: input dataframe with datetime index
    :param rule: resampling frequency
    :param open_col: name of "open" column
    :param high_col: name of "high" column
    :param low_col: name of "low" column
    :param close_col: name of "close" column
    :param volume_col: name of "volume" column
    :param add_twap_vwap: if `True`, add "twap" and "vwap" columns
    :return: resampled OHLCV dataframe with same column names; if
        `add_twap_vwap`, then also includes "twap" and "vwap" columns.
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # Make sure that requested OHLCV columns are present in the dataframe.
    for col in [open_col, high_col, low_col, close_col, volume_col]:
        if col is not None:
            hdbg.dassert_in(col, df.columns)
    resampling_groups = []
    if open_col:
        group = ({open_col: open_col}, "first", {})
        resampling_groups.append(group)
    if high_col:
        group = ({high_col: high_col}, "max", {})
        resampling_groups.append(group)
    if low_col:
        group = ({low_col: low_col}, "min", {})
        resampling_groups.append(group)
    if close_col:
        group = ({close_col: close_col}, "last", {})
        resampling_groups.append(group)
    if volume_col:
        group = ({volume_col: volume_col}, "sum", {"min_count": 1})
        resampling_groups.append(group)
    result_df = resample_bars(
        df,
        rule=rule,
        resampling_groups=resampling_groups,
        vwap_groups=[],
    )
    # TODO(Paul): Refactor this so that we do not call `compute_twap_vwap()`
    #  directly.
    # Add TWAP / VWAP prices, if needed.
    if add_twap_vwap:
        close_col = cast(str, close_col)
        volume_col = cast(str, volume_col)
        twap_vwap_df = compute_twap_vwap(
            df, rule=rule, price_col=close_col, volume_col=volume_col
        )
        result_df = result_df.merge(
            twap_vwap_df, how="outer", left_index=True, right_index=True
        )
        hdbg.dassert(result_df.index.freq)
    return result_df


# TODO(Paul): Deprecate this function. The bells and whistles do not really
# fit, and the core functionality can be accessed through the above functions.
def compute_twap_vwap(
    df: pd.DataFrame,
    rule: str,
    *,
    price_col: str,
    volume_col: str,
    offset: Optional[str] = None,
    add_bar_volume: bool = False,
    add_bar_start_timestamps: bool = False,
    add_epoch: bool = False,
    add_last_price: bool = False,
) -> pd.DataFrame:
    """
    Compute TWAP/VWAP from price and volume columns.

    :param df: input dataframe with datetime index
    :param rule: resampling frequency and TWAP/VWAP aggregation window
    :param price_col: price for bar
    :param volume_col: volume for bar
    :param offset: offset in the Pandas format (e.g., `1T`) used to shift the
        sampling
    :return: twap and vwap price series
    """
    hdbg.dassert_isinstance(df, pd.DataFrame)
    # TODO(*): Determine whether we really need this. Disabling for now to
    #  accommodate data that is not perfectly aligned with a pandas freq
    #  (e.g., Kibot).
    # hdbg.dassert(df.index.freq)
    vwap = compute_vwap(
        df, rule=rule, price_col=price_col, volume_col=volume_col, offset=offset
    )
    price = df[price_col]
    # Calculate TWAP, but preserve NaNs for all-NaN bars.
    twap = resample(price, rule=rule, offset=offset).mean()
    twap.name = "twap"
    dfs = [vwap, twap]
    if add_last_price:
        # Calculate last price (regardless of whether we have volume data).
        last_price = resample(price, rule=rule, offset=offset).last(min_count=1)
        last_price.name = "last"
        dfs.append(last_price)
    if add_bar_volume:
        volume = df[volume_col]
        # Calculate bar volume (regardless of whether we have price data).
        bar_volume = resample(volume, rule=rule, offset=offset).sum(min_count=1)
        bar_volume.name = "volume"
        dfs.append(bar_volume)
    if add_bar_start_timestamps:
        bar_start_timestamps = cfiprpro.compute_bar_start_timestamps(vwap)
        dfs.append(bar_start_timestamps)
    if add_epoch:
        epoch = cfiprpro.compute_epoch(vwap)
        dfs.append(epoch)
    df_out = pd.concat(dfs, axis=1)
    return df_out


def resample(
    data: Union[pd.Series, pd.DataFrame],
    **resample_kwargs: Dict[str, Any],
) -> Union[pd.Series, pd.DataFrame]:
    """
    Execute series resampling with specified `.resample()` arguments.

    The `rule` argument must always be specified and the `closed` and `label`
    arguments are treated specially by default.

    The default values of `closed` and `label` arguments are intended to make
    pandas `resample()` behavior consistent for every value of `rule` and to
    make resampling causal. So if we have sampling times t_0 < t_1 < t_2, then,
    after resampling, the values at t_1 and t_2 should not be incorporated
    into the resampled value timestamped with t_0. Note that this behavior is
    at odds with what may be intuitive for plotting lower-frequency data, e.g.,
    yearly data is typically labeled in a plot by the start of the year.

    :data: pd.Series or pd.DataFrame with a datetime index
    :resample_kwargs: arguments for pd.DataFrame.resample
    :return: DatetimeIndexResampler object
    """
    hdbg.dassert_in("rule", resample_kwargs, "Argument 'rule' must be specified")
    # Unless specified by the user, the resampling intervals are intended as
    # (a, b] with label on the right.
    if "closed" not in resample_kwargs:
        resample_kwargs["closed"] = "right"
    if "label" not in resample_kwargs:
        resample_kwargs["label"] = "right"
    # Execute resampling with specified kwargs.
    resampled_data = data.resample(**resample_kwargs)
    # _LOG.debug("resampled_data.size=%s" % str(resampled_data.size))
    return resampled_data


def maybe_resample(srs: pd.Series) -> pd.Series:
    """
    Return `srs` resampled to "B" `srs.index.freq` if is `None`.

    This is a no-op if `srs.index.freq` is not `None`.
    """
    hdbg.dassert_isinstance(srs.index, pd.DatetimeIndex)
    if srs.index.freq is None:
        _LOG.debug("No `freq` detected; resampling to 'B'.")
        srs = srs.resample("B").sum(min_count=1)
    return srs
