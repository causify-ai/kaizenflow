"""
DAG to download OHLCV data from Binance.
"""

import datetime

import airflow
from airflow.operators.bash import BashOperator

# dag for histroical data
_DAG_ID = "perform_predictions"
_DAG_DESCRIPTION = (
    "Load data from 'google_trends_data' table, perform predictions and save in 'google_trends_predictions'"
)

# Specify when often to execute the DAG.
# runs once

# schedule for deliverable 4
_SCHEDULE = "*/5 * * * *"

# running on the 1st of every month at 11pm
# _SCHEDULE = '0 23 1 * *'

# Pass default parameters for the DAG.
# adding our time zone
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    'timezone': 'America/New_York'
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
    "/cmamp/src/load_validate_transform.py",
    "--source_table google_trends_data",
    "--target_table google_trends_predictions",
    "--topic ipad"
]

ml_task = BashOperator(
    task_id="predict.postgres.google_trends",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

ml_task
