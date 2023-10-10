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


default_args = {
    "owner": "coder2j",
    "retry": 5,
    "retry_delay": timedelta(minutes=5),
}


def dump_1m():
    dump_latest_data("yahoo_yfinance_spot_downloaded_1min", "1m")


with DAG(
    default_args=default_args,
    dag_id="dag_1min",
    start_date=datetime(2023, 4, 17, 6, 0, 0),
    schedule_interval="*/5 * * * *",
) as dag:
    task1 = PythonOperator(task_id="dump_1m", python_callable=dump_1m)

    task1
