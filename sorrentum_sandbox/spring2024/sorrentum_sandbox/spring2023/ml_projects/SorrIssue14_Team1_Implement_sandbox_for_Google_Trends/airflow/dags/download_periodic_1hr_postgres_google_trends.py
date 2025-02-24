"""
DAG to download OHLCV data from Binance.
"""

import datetime

import airflow
from airflow.operators.bash import BashOperator

# Real time data fetching
_DAG_ID = "download_periodic_1hr_postgres"
_DAG_DESCRIPTION = "Download Google trends data every hour and save to Postgres"
# Specify when often to execute the DAG.
_SCHEDULE = "0 * * * *"

# Pass default parameters for the DAG.
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "timezone": "America/New_York",
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    start_date=datetime.datetime(2023, 4, 16, 4, 0, 0),
)

bash_command = [
    # Sleep 5 seconds to ensure the bar is finished.
    "sleep 5",
    "&&",
    "/cmamp/src/download_to_db.py",
    "--target_table google_trends_data",
    "--use_api True",
    "--real_time_data False",
]

downloading_task = BashOperator(
    task_id="download.periodic_1min.postgres.google_trends",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
