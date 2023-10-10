"""
DAG to download stock market data.
"""


import datetime
import time

from airflow.decorators import task
from airflow.models import DAG
from api.mongo_db import Mongo
from models.list_of_tickers import SP500
from models.ticker import Ticker
from models.time_series import DataType, TimeInterval

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime.datetime.now(),
    "end_date": datetime.datetime(2024, 1, 1),
    "retries": 1,
}

with DAG(
    dag_id="update_sp500",
    description="Downloads and updates S&P 500 data",
    max_active_runs=1,
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:

    @task
    def update():
        """Downloads S&P500 data in one minute intervals"""
        counter = 0

        for symbol in SP500:
            ticker = Ticker(symbol, get_name=False)
            ticker.get_data(
                data_type=DataType.INTRADAY, time_interval=TimeInterval.ONE
            )
            Mongo.save_data(ticker)
            counter += 1

            if counter >= 5:
                counter = 0
                time.sleep(61)  # Wait one minute

    update()
