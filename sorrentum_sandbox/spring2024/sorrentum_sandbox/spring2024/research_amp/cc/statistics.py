"""
Compute crypto-related statistics.

Import as:

import research_amp.cc.statistics as ramccsta
"""
import logging
from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd

import core.config.config_ as cconconf
import core.statistics as costatis
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


def compute_stats_for_universe(
    vendor_universe: List[ivcu.FullSymbol],
    config: cconconf.Config,
    stats_func: Callable,
) -> pd.DataFrame:
    """
    Compute stats on the vendor universe level.

    E.g., to compute start-end table for the universe do:
    `compute_stats_for_universe(vendor_universe, config, compute_start_end_stats)`.

    :param vendor_universe: vendor universe as a list of of exchange-currency tuples
    :param config: parameters config
    :param stats_func: function to compute statistics, e.g. `compute_start_end_stats`
    :return: stats table for all exchanges and currencies in the vendor universe
    """
    hdbg.dassert_isinstance(stats_func, Callable)
    # Initialize loader.
    loader = get_loader_for_vendor(config)
    # Initialize stats data list.
    stats_data = []
    # Iterate over vendor universe tuples.
    for full_symbol in vendor_universe:
        # Read data for current exchange and currency pair.
        start_ts = None
        end_ts = None
        columns = None
        filter_data_mode = "assert"
        data = loader.read_data(
            [full_symbol], start_ts, end_ts, columns, filter_data_mode
        )
        # Compute stats on the exchange-currency level.
        cur_stats_data = stats_func(data)
        cur_stats_data["vendor"] = config["data"]["vendor"]
        stats_data.append(cur_stats_data)
    # Convert results to a dataframe.
    stats_table = pd.concat(stats_data, ignore_index=True)
    return stats_table


def compute_start_end_stats(
    price_data: pd.DataFrame,
    config: cconconf.Config,
) -> pd.DataFrame:
    """
    Compute start-end stats for exchange-currency data.

    Note: `price_data` must be resampled using NaNs.

    Start-end stats's structure is:
        - exchange name
        - currency pair
        - minimum observed timestamp
        - maximum observed timestamp
        - the number of not NaN data points
        - data coverage, which is the number of not NaN data points divided
          by the number of all data points as percentage
        - the number of days for which data is available
        - the average number of not NaN data points per day
        - the number of days of the longest not-NaN sequence
        - the share of the longest not-NaN sequence in data
        - start date of the longest not-NaN sequence
        - end data of the longest not-NaN sequence

    :param price_data: crypto price data
    :param config: parameters config
    :return: start-end stats
    """
    hdbg.dassert_is_subset(
        [
            config["column_names"]["close_price"],
            config["column_names"]["currency_pair"],
            config["column_names"]["exchange_id"],
        ],
        price_data.columns,
    )
    hdbg.dassert_isinstance(price_data.index, pd.DatetimeIndex)
    hpandas.dassert_monotonic_index(price_data.index)
    hdbg.dassert_eq(pd.infer_freq(price_data.index), "T")
    # Get series of close price.
    close_price_srs = price_data[config["column_names"]["close_price"]]
    # Remove leading and trailing NaNs.
    first_idx = close_price_srs.first_valid_index()
    last_idx = close_price_srs.last_valid_index()
    close_price_srs = close_price_srs[first_idx:last_idx].copy()
    # Get the longest not-NaN sequence in the close price series.
    longest_not_nan_seq = find_longest_not_nan_sequence(close_price_srs)
    # Compute necessary stats and put them in a series.
    res_srs = pd.Series(dtype="object")
    res_srs["exchange_id"] = price_data[config["column_names"]["exchange_id"]][0]
    res_srs["currency_pair"] = price_data[
        config["column_names"]["currency_pair"]
    ][0]
    res_srs["min_timestamp"] = first_idx
    res_srs["max_timestamp"] = last_idx
    res_srs["n_data_points"] = close_price_srs.count()
    res_srs["coverage"] = 100 * (1 - costatis.compute_frac_nan(close_price_srs))
    res_srs["days_available"] = (last_idx - first_idx).days
    res_srs["avg_data_points_per_day"] = (
        res_srs["n_data_points"] / res_srs["days_available"]
    )
    res_srs["longest_not_nan_seq_days"] = (
        longest_not_nan_seq.index[-1] - longest_not_nan_seq.index[0]
    ).days
    res_srs["longest_not_nan_seq_perc"] = 100 * (
        len(longest_not_nan_seq) / len(close_price_srs)
    )
    res_srs["longest_not_nan_seq_start_date"] = longest_not_nan_seq.index[0]
    res_srs["longest_not_nan_seq_end_date"] = longest_not_nan_seq.index[-1]
    # TODO(Max): think about what to return: `pd.Series` or `pd.DataFrame`?
    res_srs = pd.DataFrame(res_srs).T
    return res_srs


def compute_start_end_table_by_currency(
    start_end_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute start end table by currency pair.

    :param start_end_table: start end table
    :return: start end table table by currency pair
    """
    # Extract currency pair related stats from the original start end table.
    currency_start_end_table = (
        start_end_table.groupby("currency_pair")
        .agg(
            {
                "min_timestamp": np.min,
                "max_timestamp": np.max,
                "exchange_id": list,
            }
        )
        .reset_index()
    )
    # Compute the number of available days per currency pair.
    currency_start_end_table["days_available"] = (
        currency_start_end_table["max_timestamp"]
        - currency_start_end_table["min_timestamp"]
    ).dt.days
    # Sort by available days and reset index.
    currency_start_end_table_sorted = currency_start_end_table.sort_values(
        by="days_available",
        ascending=False,
    ).reset_index(drop=True)
    # Report the number of unique currency pairs.
    _LOG.info(
        "The number of unique currency pairs=%s",
        currency_start_end_table_sorted.shape[0],
    )
    return currency_start_end_table_sorted


def postprocess_stats_table(
    stats_table: pd.DataFrame,
    cols_to_sort_by: Optional[List[str]] = None,
    cols_to_round: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Post-process start-end stats table.

    :param stats_table: stats table
    :param cols_to_sort_by: columns to sort the table by if specified
    :param cols_to_round: columns to round up to 2 decimals if specified
    :return: post-processed stats table
    """
    if cols_to_sort_by:
        hdbg.dassert_is_subset(cols_to_sort_by, stats_table.columns)
        stats_table = stats_table.sort_values(by=cols_to_sort_by)
    if cols_to_round:
        hdbg.dassert_is_subset(cols_to_round, stats_table.columns)
        stats_table[cols_to_round] = stats_table[cols_to_round].round(2)
    return stats_table


# TODO(Grisha): move `get_loader_for_vendor` out in and use the abstract class in #313.
def get_loader_for_vendor(
    config: cconconf.Config,
) -> icdc.ImClient:
    """
    Get vendor specific loader instance.

    :param config: config
    :return: loader instance
    """
    vendor = config["data"]["vendor"]
    # TODO(Grisha): pass universe version via config.
    universe_version = "v3"
    resample_1min = True
    root_dir = config["load"]["data_dir"]
    extension = "csv.gz"
    loader = icdcl.CcxtCddCsvParquetByAssetClient(
        vendor,
        universe_version,
        resample_1min,
        root_dir,
        extension,
        aws_profile=config["load"]["aws_profile"],
    )
    return loader


def find_longest_not_nan_sequence(
    data: Union[pd.Series, pd.DataFrame]
) -> Union[pd.Series, pd.DataFrame]:
    """
    Find the longest sequence of not-NaN values in a series or dataframe.

    For a dataframe the longest sequence of rows with no NaN values is returned.

    :param data: input series or dataframe
    :return: longest sequence of not-NaN values
    """
    # Verify that index is monotonically increasing.
    hpandas.dassert_strictly_increasing_index(data)
    # Get index frequency.
    freq = pd.infer_freq(data.index)
    # Get indices of only not-NaN values.
    not_nan_index = np.array(data.dropna().index)
    # Get a mask to distinguish not-NaN values that are further from their
    # not-NaN precedent than 1 frequency time step.
    mask = np.where(np.diff(not_nan_index) != pd.Timedelta(1, freq))[0] + 1
    # Get the longest monotonically increasing sequence of indices.
    longest_not_nan_index = max(np.split(not_nan_index, mask), key=len)
    # Get the longest sequence of not-NaN values.
    longest_not_nan_seq = data.loc[longest_not_nan_index].copy()
    return longest_not_nan_seq


def get_universe_price_data(
    vendor_universe: List[ivcu.FullSymbol],
    config: cconconf.Config,
) -> pd.DataFrame:
    """
    Get combined price data for a given vendor universe.

    :param vendor_universe: vendor universe as a list of of exchange-currency tuples
    :param config: parameters config
    :return: universe price data
    """
    # Initialize loader.
    loader = get_loader_for_vendor(config)
    # Initialize lists of column names and price data series.
    colnames = []
    price_srs_list = []
    # Set parameters for data reading.
    start_ts = None
    end_ts = None
    columns = None
    filter_data_mode = "assert"
    # Iterate exchange ids and currency pairs.
    for full_symbol in vendor_universe:
        colnames.append(full_symbol)
        # Read data for current exchange and currency pair.
        data = loader.read_data(
            full_symbol, start_ts, end_ts, columns, filter_data_mode
        )
        # Get series of required prices and append to the list.
        price_srs = data[config["data"]["price_column"]]
        price_srs_list.append(price_srs)
    # Construct a dataframe and assign column names.
    price_data = pd.concat(price_srs_list, axis=1)
    price_data.columns = colnames
    return price_data
