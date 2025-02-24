"""
Helper functions for im_v2/common/notebooks/Master_raw_data_gallery.ipynb.

Import as:

from im_v2.common.notebooks.master_raw_data_gallery_lib import *
"""
import logging
from typing import Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hsql as hsql
import im_v2.im_lib_tasks as imvimlita

_LOG = logging.getLogger(__name__)


def get_raw_data_from_db(
    db_table: str,
    exchange_id: str,
    start_ts: Optional[str],
    end_ts: Optional[str],
) -> pd.DataFrame:
    """
    Read raw data for the given exchange from the RT DB.

    Bypasses the IM Client to avoid any on-the-fly transformations.

    :param db_table: the name of the table in the DB
    :param exchange_id: the name of exchange, e.g. `binance`
    :param start_ts: the start date of the time filter
    :param end_ts: the end date of the time filter
    :return: the raw data loaded from DB
    """
    # Get DB connection.
    env_file = imvimlita.get_db_env_path("dev")
    # Connect with the parameters from the env file.
    connection_params = hsql.get_connection_info_from_env_file(env_file)
    connection = hsql.get_connection(*connection_params)
    # Read data from DB.
    query = f"SELECT * FROM {db_table} WHERE exchange_id='{exchange_id}'"
    if start_ts:
        start_ts = pd.Timestamp(start_ts)
        unix_start_timestamp = hdateti.convert_timestamp_to_unix_epoch(start_ts)
        query += f" AND timestamp >='{unix_start_timestamp}'"
    if end_ts:
        end_ts = pd.Timestamp(end_ts)
        unix_end_timestamp = hdateti.convert_timestamp_to_unix_epoch(end_ts)
        query += f" AND timestamp <='{unix_end_timestamp}'"
    rt_data = hsql.execute_query_to_df(connection, query)
    return rt_data


def load_parquet_by_period(
    start_ts: pd.Timestamp, end_ts: pd.Timestamp, s3_path: str
) -> pd.DataFrame:
    """
    Read raw historical data from the S3 by time period.

    Suitable for small data, to process larger parquets in chunks
      use `process_s3_data_in_chunks`.

    Bypasses the IM Client to avoid any on-the-fly transformations.

    :param start_ts: the start date of the time filter
    :param end_ts: the end date of the time filter
    :param s3_path: the path to S3 directory, e.g.
      "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq/ohlcv-futures/ccxt/binance"
    """
    # Create timestamp filters.
    timestamp_filters = hparque.get_parquet_filters_from_timestamp_interval(
        "by_year_month", start_ts, end_ts
    )
    # Load daily data from s3 parquet.
    cc_ba_futures_daily = hparque.from_parquet(
        s3_path, filters=timestamp_filters, aws_profile="ck"
    )
    cc_ba_futures_daily = cc_ba_futures_daily.sort_index()
    return cc_ba_futures_daily


def process_s3_data_in_chunks(
    start_ts: str, end_ts: str, s3_path: str, step: int
) -> None:
    """
    Process wide period of S3 historical data by smaller parts,
      display head and tail of each part.

    :param start_ts: the start date of the time filter
    :param end_ts: the end date of the time filter
    :param s3_path: the path to S3 directory, e.g.
      "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask-futures/crypto_chassis/binance"
    :param step: the number of months to load for one chunk of data
    """
    start_ts = pd.Timestamp(start_ts, tz="UTC")
    end_ts = pd.Timestamp(end_ts, tz="UTC")
    # Separate time period to months.
    # E.g. of `dates` sequence `['2022-10-31 00:00:00+00:00', '2022-11-30 00:00:00+00:00']`.
    dates = pd.date_range(start_ts, end_ts, freq="M")
    for i in range(0, len(dates), step):
        # Iterate through the dates to select the loading period boundaries.
        # E.g. if the chunk of data is loaded for two months.
        # the sequence of ['2022-09-31', '2022-10-30', '2022-11-31', '2022-12-31']
        # should be divided into two periods: ['2022-09-31', '2022-10-30']
        # and ['2022-11-31', '2022-12-31']
        period = dates[i : i + step]
        if len(period) == 1:
            start = dates[i]
            end = dates[i]
            _LOG.info(f"Loading data for the month {start.month}")
        else:
            start = period[0]
            end = period[-1]
            _LOG.info(
                f"Loading data for the period of {start.month}-{end.month} months"
            )
        # Load the data of the time period.
        daily_data = load_parquet_by_period(start, end, s3_path)
        _LOG.info("Head:")
        hpandas._display(logging.INFO, daily_data.head(2))
        _LOG.info("Tail:")
        hpandas._display(logging.INFO, daily_data.tail(2))
    return
