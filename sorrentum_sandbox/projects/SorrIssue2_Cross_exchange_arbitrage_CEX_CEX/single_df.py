import numpy as np
import pandas as pd
from functools import reduce
import datetime
from typing import List, Optional, str 
import pyarrow as pa
import pyarrow.parquet as pq

def convert_to_multiindex(
    exchange_df: pd.DataFrame, keep_single: Optional[bool] = False
) -> pd.DataFrame:
    """
    Rearrange the given exchange dataframe such that the index is time
    and at any time, features of all coins on the exchange can be 
    determined.

    :param exchange_df: data from some exchange
    :return: nicer dataframe that will be input to define_levels
    """
    # Move timestamp to a column and localize it.
    exchange_df = exchange_df.reset_index()
    exchange_df["timestamp"] = pd.to_datetime(exchange_df["timestamp"])
    exchange_df["timestamp"] = exchange_df["timestamp"].dt.tz_localize(None)
    exchange_df["timestamp"] = exchange_df["timestamp"].astype("datetime64[ns]")
    exchange_df = exchange_df.sort_values(by="timestamp")
    # Get the name of the exchange.
    exchange_id = exchange_df["exchange_id"].unique()[0]
    # Drop all irrelevant columns.
    exchange_df = exchange_df.drop(columns=["timestamp.1", "knowledge_timestamp", "year", "month", "exchange_id"])
    # Group the dataframe by currency pair.
    currency_pair_dfs = exchange_df.groupby("currency_pair")
    currency_pair_dfs = [currency_pair_dfs.get_group(currency_pair) for currency_pair in currency_pair_dfs.groups]
    # Initialize the dataframe that we will return, which starts as just time.
    return_df = pd.DataFrame(exchange_df["timestamp"].unique())
    return_df = return_df.rename(columns={0:"timestamp"})
    # Calls calculate_vwap helper function that also renames OHLCV columns.
    currency_pair_dfs = calculate_vwap(currency_pair_dfs, exchange_id) 
    # Merge all currency pair dataframes into the return dataframe
    for currency_pair in currency_pair_dfs:
        return_df = pd.merge_asof(return_df, currency_pair, on="timestamp")
    # Set index as timestamp which was lost during merging.
    return_df = return_df.set_index("timestamp")
    # Sort by column name to the order is consistent.
    return_df = return_df.sort_index(axis=1)
    # Drop duplicate columns if there are any
    return_df = return_df.loc[:,~return_df.columns.duplicated()]
    # Call define_levels function for next step.
    if keep_single:
        return return_df
    return define_levels(return_df)

def calculate_vwap(
    currency_pair_dfs: List[pd.DataFrame],
    exchange_id: str
) -> List[pd.DataFrame]:
    """
    Calculates volume weighted average price for each currency pair dataframe
    in the given list of currency pair dataframes.

    :param currency_pair_dfs: list of currency pair dataframes
    :param exchange_id: str name of the given exchange
    :return: currency pair dataframes with vwap calculations
    """
    for df in currency_pair_dfs:
        # Get name of currency_pair for renaming purposes.
        currency_pair = df["currency_pair"].unique()[0]
        vwap_column_name = f"vwap-{exchange_id}::{currency_pair}"
        volume_column_name = f"volume-{exchange_id}::{currency_pair}"
        open_column_name = f"open-{exchange_id}::{currency_pair}"
        high_column_name = f"high-{exchange_id}::{currency_pair}"
        low_column_name = f"low-{exchange_id}::{currency_pair}"
        close_column_name = f"close-{exchange_id}::{currency_pair}"
        # Calculate vwap.
        midprice = (df["high"] + df["low"]) / 2
        numerator = np.cumsum(np.multiply(df["volume"], midprice))
        denominator = np.cumsum(df["volume"])
        df[vwap_column_name] = np.divide(numerator, denominator)
        # Now rename the OHLCV columns.
        df.rename(columns={"volume" : volume_column_name, 
                           "open": open_column_name, 
                           "high": high_column_name, 
                           "low": low_column_name, 
                           "close": close_column_name}, inplace=True)
        # Drop irrelevant columns and set timestamp as index.
        df.drop(columns=["currency_pair"], inplace=True)
        df.set_index("timestamp", inplace=True)
    return currency_pair_dfs

def define_levels(single_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create all of the column levels such that we can transform 
    the single_index_df into multi_index.
    
    :param single_df: dataframe returned by convert_to_multi_index
    :return: a multi-index dataframe
    """
    # Store the timestamp for later use.
    timestamp = single_df.index
    # Create a list of all column names.
    columns = list(single_df.columns)
    num_pairs = int(len(columns) / 6)
    # Create outer level (feature).
    close_string = "close " * num_pairs
    high_string = "high " * num_pairs
    low_string = "low " * num_pairs
    open_string = "open " * num_pairs
    volume_string = "volume " * num_pairs
    vwap_string = "vwap " * num_pairs
    feature_string = "".join([close_string, high_string, low_string, open_string, volume_string, vwap_string])
    # Simultaneously inner level (exchange::currency_pair).
    currency_pair_string = ""
    for column_name in columns:
        hyphen = column_name.rfind("-")
        currency_pair_string += column_name[hyphen + 1:] + " "
    # Convert the given dataframe to multi-index.
    return_df = pd.DataFrame(np.array(single_df), columns=[feature_string.split(), currency_pair_string.split()])
    # Restore the initial timestamp.
    return_df.index = timestamp
    # Drop duplicate columns if there are any.
    return_df = return_df.loc[:,~return_df.columns.duplicated()].copy()
    return return_df

def merge_and_convert_to_multiindex(
    exchange_dfs: List[pd.DataFrame]
) -> List[pd.DataFrame]:
    """
    Converts a list of exchange dataframes into one large
    multi-index dataframe.

    :param exchange_dfs: list of all exchange dataframes
    :return: multi-index dataframe
    """
    # Edge case if exchange_dfs of size == 1
    if len(exchange_dfs) == 1:
        return convert_to_multiindex(exchange_df)
    # Make all dataframes in exchange_dfs easily convertible to multi-index
    for i, exchange_df in enumerate(exchange_dfs):
        exchange_dfs[i] = convert_to_multiindex(exchange_df, True)
    # Merge dataframes using reduce().
    return_df = reduce(lambda df1, df2: pd.merge(df1, df2, on="timestamp", how="outer"), exchange_dfs)
    # Sort by time and columns before passing into define_levels
    return_df = return_df.sort_index()
    return_df = return_df.sort_index(axis=1)
    # Drop duplicate columns if there are any.
    return_df = return_df.loc[:,~return_df.columns.duplicated()]
    return define_levels(return_df)

def get_symbols(multindex_df: pd.MultiIndex) -> List[str]:
    """
    Retrieves a list of all of the unique symbols (currency pairs) given a 
    multiindex dataframe.

    :param multiindex_df: a df returned by convert_to_multiindex
    :return: list of symbols
    """
    symbols_with_prefix = multindex_df["close"].columns
    symbols = [symbol[symbol.rfind(":")+1:] for symbol in symbols_with_prefix]
    return list(set(symbols))

def get_symbol_info(multiindex_df: pd.MultiIndex, symbol: str) -> pd.MultiIndex:
    """
    Returns a two-level dataframe with only the given symbol.

    :param multiindex_df: a df returned by convert_to_multiindex
    :param symbol: the desired symbol (currency_pair)
    :return: all data associated with the symbol
    """
    columns_list = multiindex_df.columns
    columns = [column for column in columns_list if symbol in column[1]]
    return multiindex_df[columns]