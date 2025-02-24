"""
DAG to download OHLCV data from Binance.
"""

import datetime

import airflow
from airflow.operators.bash import BashOperator

# dag for histroical data
_DAG_ID = "download_historical_postgres"
_DAG_DESCRIPTION = "Download Google trends data once and save to Postgres"

# Specify when often to execute the DAG.
# runs once

_SCHEDULE = "*/2 * * * *"
# _SCHEDULE = "0 * * * *"


# Pass default parameters for the DAG.
# adding our time zone
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
# adding a start date
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2023, 4, 30, 18, 30, 0)
)


bash_command = [
    # Sleep 5 seconds to ensure the bar is finished.
    "sleep 5",
    "&&",
    "/cmamp/src/download_to_db.py",
    "--target_table google_trends_data",
    "--use_api True",
    "--real_time_data False",
    "--topic iPad"
]

downloading_task = BashOperator(
    task_id="download.historical.postgres.google_trends",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
