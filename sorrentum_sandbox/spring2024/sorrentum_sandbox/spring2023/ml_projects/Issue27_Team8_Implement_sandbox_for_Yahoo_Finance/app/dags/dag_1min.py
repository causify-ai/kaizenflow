"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue27_Team8_Implement_sandbox_for_Yahoo_Finance.app.dags.dag_1min as ssempitisfyfadd1
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

import os
import download_yahoo as sisebido
from Latest_Data import dump_latest_data
from dask_db import dump_dask_data


default_args = {
    "owner": "coder2j",
    "retry": 5,
    "retry_delay": timedelta(minutes=5),
}


def dump_1m():
    dump_latest_data("yahoo_yfinance_spot_downloaded_1min", "1m")

def dump_dask_1m():
    dump_dask_data()


with DAG(
    default_args=default_args,
    dag_id="dag_1min",
    start_date=datetime(2023, 5, 3,5,30,0),
    schedule_interval='*/5 * * * *'
) as dag:
    task1 = PythonOperator(
        task_id='dump_1m',
        python_callable=dump_1m
    )
    task2 = PythonOperator(
        task_id='dump_dask_1m',
        python_callable=dump_dask_1m
    )

    
   
    task1>>task2
