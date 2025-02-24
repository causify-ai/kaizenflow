# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports
#
# Importing all required modules.

# %% pycharm={"name": "#%%\n"}
# %load_ext autoreload
# %autoreload 2

import datetime as dateti
import os
from typing import Dict

import pandas as pd

import helpers.hs3 as hs3
import im.common.data.types as imcodatyp
import im.kibot.data.load as vkdloa
import im.kibot.data.load.kibot_file_path_generator as imkdlkfpge

# %% [markdown] pycharm={"name": "#%% md\n"}
# Define helper functions to calculate the report.


# %% pycharm={"name": "#%%\n"}
def slice_price_data(
    price_df_dict: Dict[str, pd.DataFrame], last_years: int
) -> Dict[str, pd.DataFrame]:
    """
    Slice DataFrames for each symbol to contain records only for the last_years
    years.

    :param price_df_dict: {symbol: prices_for_symbol_df}
    :param last_years: Number of years data is averaged to.
    :return: {symbol: prices_for_symbol_df} sliced.
    """
    now = dateti.datetime.now()
    # TODO(vr): check if dateutils.relativedate is better?
    before = now - dateti.timedelta(days=last_years * 365)
    sliced_price_df_dict = {
        symbol: prices.loc[before:now] for symbol, prices in price_df_dict.items()
    }
    return sliced_price_df_dict


def get_start_date(price_df_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Extract start dates for each time series.

    :param price_df_dict: {symbol: prices_for_symbol_df}
    :return: pd.DataFrame indexed by symbol
    """
    start_date_dict = {
        symbol: prices.index[0].strftime("%Y-%m-%d")
        for symbol, prices in price_df_dict.items()
    }
    start_date_df = pd.DataFrame.from_dict(
        start_date_dict, orient="index", columns=["start_date"]
    )
    return start_date_df


def get_price_data(
    price_df_dict: Dict[str, pd.DataFrame],
    price_col: str,
    agg_func: str,
    last_years: int,
) -> pd.DataFrame:
    """
    Get grouped prices for each symbol.

    :param price_df_dict: {symbol: prices_for_symbol_df}
    :param price_col: The name of the price column
    :param agg_func: The name of the aggregation function that needs to
        be applied to the prices for each symbol
    :param last_years: Number of years data is averaged to.
    :return: pd.DataFrame indexed by symbol
    """
    price_dict = {
        symbol: getattr(prices[price_col], agg_func)()
        for symbol, prices in price_df_dict.items()
    }
    price_df = pd.DataFrame.from_dict(
        price_dict,
        orient="index",
        columns=[f"{agg_func}_{last_years}y_{price_col}"],
    )
    price_df.index.name = "symbol"
    return price_df


# %% [markdown] pycharm={"name": "#%% md\n"}
# Define main method to generate the report for a dataset.

# %% pycharm={"name": "#%%\n"}
def generate_report(
    contract_type: imcodatyp.ContractType, frequency: imcodatyp.Frequency
) -> pd.DataFrame:
    """
    Generate a report for a dataset.

    :param frequency: `D` or `T` for daily or minutely data respectively
    :param contract_type: `continuous` or `expiry`
    :return: a dataframe with the report
    """
    dataset_aws_path = imkdlkfpge.KibotFilePathGenerator().generate_file_path(
        frequency, contract_type, "ROOT", ext=imcodatyp.Extension.CSV
    )
    dataset_aws_directory = os.path.dirname(dataset_aws_path)
    # Get a list of payloads (symbols) in format XYZ.csv.gz.
    s3fs = hs3.get_s3fs("am")
    payloads = s3fs.ls(dataset_aws_directory)
    # Get only first n-rows.
    n_rows = 100
    # Get only symbols list.
    symbols = tuple(
        payload.replace(".csv.gz", "") for payload in payloads[:n_rows]
    )
    # Read dataframes.
    kibot_data_loader = vkdloa.KibotDataLoader()
    price_df_dict = kibot_data_loader.read_data(frequency, contract_type, symbols)
    # Get avg. vol for the last 1 year
    price_1y_df_dict = slice_price_data(price_df_dict, last_years=1)
    mean_1y_vol = get_price_data(price_1y_df_dict, "vol", "mean", last_years=1)
    # Get avg. vol for the last 3 years
    price_3y_df_dict = slice_price_data(price_df_dict, last_years=3)
    mean_3y_vol = get_price_data(price_3y_df_dict, "vol", "mean", last_years=3)
    # Get avg. vol for the last 5 years
    price_5y_df_dict = slice_price_data(price_df_dict, last_years=5)
    mean_5y_vol = get_price_data(price_5y_df_dict, "vol", "mean", last_years=5)
    # Get start date for each symbol.
    start_date_df = get_start_date(price_df_dict)
    # Get report for dataset.
    report = pd.concat(
        [start_date_df, mean_1y_vol, mean_3y_vol, mean_5y_vol],
        axis=1,
        join="inner",
    )
    report.index.name = "symbol"
    report.fillna(0, inplace=True)
    return report


# %% [markdown] pycharm={"name": "#%% md\n"}
# Report for all_futures_contracts_1min

# %% pycharm={"name": "#%%\n"}
dataset_report = generate_report(
    imcodatyp.ContractType.Expiry, imcodatyp.Frequency.Minutely
)
dataset_report

# %% [markdown]
# Report for all_futures_contracts_daily

# %% pycharm={"name": "#%%\n"}
dataset_report = generate_report(
    imcodatyp.ContractType.Expiry, imcodatyp.Frequency.Daily
)
dataset_report

# %% [markdown]
# Report for futures_continuous_contracts_1min

# %% pycharm={"name": "#%%\n", "is_executing": true}
dataset_report = generate_report(
    imcodatyp.ContractType.Continuous, imcodatyp.Frequency.Minutely
)
dataset_report

# %% [markdown]
# Report for futures_continuous_contracts_daily

# %% pycharm={"name": "#%%\n", "is_executing": true}
dataset_report = generate_report(
    imcodatyp.ContractType.Continuous, imcodatyp.Frequency.Daily
)
dataset_report
