#!/usr/bin/env python
"""
Download OHLCV data from BlockChain and save it into the DB.
Use as:
> download_to_db.py \
    --start_timestamp '2016-01-01 ' \
    --time_span '6years' \
    --target_table 'Historical_Market_Price'\
    --api 'https://api.blockchain.info/charts'\
    --chart_name 'market-price'
    --target_table_forecast 'Forecast_Market_Price'\
"""
import argparse
import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import Block_db as sisebidb
import Block_download as sisebido

#Import libraries to run Dask and Prophet to compute the forecast and to make cross validations.

import os
import dask
import dask.distributed
from prophet import Prophet
from distributed import Client, performance_report
import prophet.diagnostics
from prophet.diagnostics import performance_metrics
from prophet.plot import plot_cross_validation_metric

_LOG = logging.getLogger(__name__)


####Create function whose name is forecast to compute the forecast of the market-price of the bitcoin and to make cross validations in Prophet in Dask.

def forecast(data):
    
    # Change the format of the timestamp column in the dataframe that was read from the db to a datetime format.

    data['ds'] = pd.to_datetime(data['timestamp'], unit='s')

    # Select columns ds and values from the dataframe and rename them as values and y, respectively, because Prophet requires these names for the columns of the dataframe.

    data =data[['ds','values']]
    data.rename(columns={"values": "y"},inplace=True) 

    # Fit Prophet model and request forecast for the following 30 days.

    m=Prophet(daily_seasonality=False)
    m.fit(data)
    future = m.make_future_dataframe(periods=30)
    fcst = m.predict(future)

    client = Client(threads_per_worker = 1) 

    # Define parameters for the cross-validation part of the Prophet model
    # The parameter whose name is initial indicates the length of the training period to perform the cross-validation.
    # The parameter whose name is period indicates the spacing between the cutoff dates for each forecast made during cross-validation.
    # The parameter whose name is horizon indicates the maximum length of the forecast horizon computed during cross-validation.

    df_cv = prophet.diagnostics.cross_validation(m, initial = "400 days", period="30 days", horizon = "30 days", parallel = "dask")

    #### Computes performance metrics for different lengths of the forecast horizon, from 4 days to 30 days. The metrics include mse, rmse, among others. 

    df_p = performance_metrics(df_cv)

    ### The function returns the forecast, the results from the cross-validation and the performance metrics.

    return fcst, df_cv, df_p



def _add_download_args(
     parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--start_timestamp",
        required=True,
        action="store",
        type=str,
        help="Beginning of the loaded period, e.g. 2016-01-01 ",
    )
    parser.add_argument(
        "--time_span",
        action="store",
        required=True,
        type=str,
        help="Time span from the start time, e.g. 6year",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="Path to the target table to store data",
    )

    parser.add_argument(
        "--api",
        action="store",
        default='https://api.blockchain.info/charts',
        type=str,
        help="Base URL for the API",
    )

    parser.add_argument(
        "--chart_name",
        action="store",
        default='market-price',
        required=True,
        type=str,
        help="Name of the chart to download",
    )

    parser.add_argument(
        "--target_table_forecast",
        action="store",
        required=True,
        type=str,
        help="Path to the target table to store forecast",
    )
    
    return parser

def _parse() -> argparse.ArgumentParser:
    hdbg.init_logger(use_exec_path=True)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_download_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # Load data.
    downloader = sisebido.OhlcvRestApiDownloader(api=args.api, chart_name=args.chart_name)
    raw_data = downloader.download(args.start_timestamp,args.time_span)
    # Save data to DB.
    db_conn = sisebidb.get_db_connection()
    saver = sisebidb.PostgresDataFrameSaver(db_conn)
    saver.save(raw_data, args.target_table)
    # Load Historical data into table Forecast_Market_Price.
    db_client = sisebidb.PostgresClient(db_conn)
    data = db_client.load(args.target_table)
    print(data.head)
    # Use Prophet - Dask.
    result, cv, p  = forecast(data)
    # Print last raws (tail) of the forecast.
    print(result.tail())
    # Print last raws (tail) of the results of cross validation in Dask.
    print(cv.tail())
    #  Print last raws (tail) of the results of the performance metrics in Dask.
    print(p.tail())

    
if __name__ == "__main__":
    _main(_parse())