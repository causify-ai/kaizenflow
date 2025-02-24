"""
Load crypto-chassis data (temporary solution).

Import as:

import research_amp.cc.crypto_chassis_api as raccchap
"""
from typing import Any, List, Tuple, Union

import pandas as pd
import requests

import core.finance.resampling as cfinresa
import helpers.hdatetime as hdateti
import im_v2.common.universe as ivcu


def get_exchange_currency_for_api_request(
    full_symbol: str,
) -> Tuple[Union[str, Any], str]:
    """
    Returns `exchange_id` and `currency_pair` in a format for requests to cc
    API.
    """
    cc_exchange_id, cc_currency_pair = ivcu.parse_full_symbol(full_symbol)
    cc_currency_pair = cc_currency_pair.lower().replace("_", "-")
    return cc_exchange_id, cc_currency_pair


def load_crypto_chassis_ohlcv_for_one_symbol(full_symbol: str) -> pd.DataFrame:
    """
    - Transform CK `full_symbol` to the `crypto-chassis` request format.
    - Construct OHLCV data request for `crypto-chassis` API.
    - Save the data as a DataFrame.
    """
    # Deconstruct `full_symbol`.
    cc_exchange_id, cc_currency_pair = get_exchange_currency_for_api_request(
        full_symbol
    )
    # Build a request.
    r = requests.get(
        f"https://api.cryptochassis.com/v1/ohlc/{cc_exchange_id}/{cc_currency_pair}?startTime=0"
    )
    # Get url with data.
    url = r.json()["historical"]["urls"][0]["url"]
    # Read the data.
    df = pd.read_csv(url, compression="gzip")
    return df


def apply_ohlcv_transformation(
    df: pd.DataFrame,
    full_symbol: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    The following transformations are applied:

    - Convert `timestamps` to the usual format.
    - Convert data columns to `float`.
    - Add `full_symbol` column.
    """
    # Convert `timestamps` to the usual format.
    df = df.rename(columns={"time_seconds": "timestamp"})
    df["timestamp"] = df["timestamp"].apply(
        lambda x: hdateti.convert_unix_epoch_to_timestamp(x, unit="s")
    )
    df = df.set_index("timestamp")
    # Convert to `float`.
    for cols in df.columns:
        df[cols] = df[cols].astype(float)
    # Add `full_symbol`.
    df["full_symbol"] = full_symbol
    # Note: I failed to put [start_time, end_time] to historical request.
    # Now it loads all the available data.
    # For that reason the time interval is hardcoded on this stage.
    df = df.loc[(df.index >= start_date) & (df.index <= end_date)]
    return df


def read_crypto_chassis_ohlcv(
    full_symbols: List[str], start_date: pd.Timestamp, end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    - Load the raw data for one symbol.
    - Convert it to CK format.
    - Repeat the first two steps for all `full_symbols`.
    - Concentrate them into unique DataFrame.
    """
    result = []
    for full_symbol in full_symbols:
        # Load raw data.
        df_raw = load_crypto_chassis_ohlcv_for_one_symbol(full_symbol)
        # Process it to CK format.
        df = apply_ohlcv_transformation(df_raw, full_symbol, start_date, end_date)
        result.append(df)
    final_df = pd.concat(result)
    return final_df


def get_list_of_dates_for_period(
    start_date: pd.Timestamp, end_date: pd.Timestamp
) -> str:
    """
    Since cc API only loads the data for one day, on need to get all the
    timestamps for days in the interval.
    """
    # Get the list of all dates in the range.
    num_of_periods = (end_date - start_date).days
    datelist = pd.date_range(start_date, periods=num_of_periods).tolist()
    datelist = [str(x.strftime("%Y-%m-%d")) for x in datelist]
    return datelist


def load_bid_ask_data_for_one_symbol(
    full_symbol: str, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    For each date inside the period load the bid-ask data.
    """
    # Using the variables from `datelist` the multiple requests can be sent to the API.
    list_of_dates = get_list_of_dates_for_period(start_date, end_date)
    result = []
    for date in list_of_dates:
        # Deconstruct `full_symbol` for API request.
        cc_exchange_id, cc_currency_pair = get_exchange_currency_for_api_request(
            full_symbol
        )
        # Interaction with the API.
        r = requests.get(
            f"https://api.cryptochassis.com/v1/market-depth/{cc_exchange_id}/{cc_currency_pair}?startTime={date}"
        )
        data = pd.read_csv(r.json()["urls"][0]["url"], compression="gzip")
        # Attaching it day-by-day to the final DataFrame.
        result.append(data)
    bid_ask_df = pd.concat(result)
    return bid_ask_df


def apply_bid_ask_transformation(
    df: pd.DataFrame, full_symbol: str
) -> pd.DataFrame:
    """
    - Divide (price, size) columns.
    - Convert timestamps and set them as index.
    - Convert data columns to `float`.
    - Add `full_symbol` column.
    """
    # Split the columns to differentiate between `price` and `size`.
    df[["bid_price", "bid_size"]] = df["bid_price_bid_size"].str.split(
        "_", expand=True
    )
    df[["ask_price", "ask_size"]] = df["ask_price_ask_size"].str.split(
        "_", expand=True
    )
    df = df.drop(columns=["bid_price_bid_size", "ask_price_ask_size"])
    # Convert `timestamps` to the usual format.
    df = df.rename(columns={"time_seconds": "timestamp"})
    df["timestamp"] = df["timestamp"].apply(
        lambda x: hdateti.convert_unix_epoch_to_timestamp(x, unit="s")
    )
    df = df.set_index("timestamp")
    # Convert to `float`.
    for cols in df.columns:
        df[cols] = df[cols].astype(float)
    # Add `full_symbol` column.
    df["full_symbol"] = full_symbol
    return df


def resample_bid_ask(df: pd.DataFrame, resampling_rule: str) -> pd.DataFrame:
    """
    In the current format the data is presented in the `seconds` frequency. In
    order to convert it to the minutely (or other) frequencies the following
    aggregation rules are applied:

    - Size is the sum of all sizes during the resampling period
    - Price is the mean of all prices during the resampling period
    """
    new_df = cfinresa.resample(df, rule=resampling_rule).agg(
        {
            "bid_price": "last",
            "bid_size": "last",
            "ask_price": "last",
            "ask_size": "last",
            "full_symbol": "last",
        }
    )
    return new_df


def read_and_resample_bid_ask_data(
    full_symbols: List[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    resampling_rule: str,
) -> pd.DataFrame:
    """
    General method that does:

    - Data loading
    - Transformation to CK format
    - Resampling
    """
    result = []
    for full_symbol in full_symbols:
        # Load raw bid ask data.
        df = load_bid_ask_data_for_one_symbol(full_symbol, start_date, end_date)
        # Apply transformation.
        df = apply_bid_ask_transformation(df, full_symbol)
        # Resample the data.
        df = resample_bid_ask(df, resampling_rule)
        result.append(df)
    bid_ask_df = pd.concat(result)
    return bid_ask_df
