"""
DAG to download data.
"""


import datetime

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_1mins_outlier"
_DAG_DESCRIPTION = (
    "Download Bitcoin market prices outlier every day and save to dbs"
)
# Specify when to execute the DAG.
_SCHEDULE = "*/1 * * * *"

# Default parameters for the DAG.
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2023, 5, 1, 0, 0, 0),
)

bash_command = [
    "/usr/bin/python3 /cmamp/sorrentum_sandbox/examples/ml_projects/Issue23_Team4_Implement_sandbox_for_Blockchain_2/download_db_all.py",
    "--target_table 'get_diff",
    "-v DEBUG",
]


downloading_task = BashOperator(
    task_id="download.airflow.downloaded.2mins.db.outlier.bitcoin",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
