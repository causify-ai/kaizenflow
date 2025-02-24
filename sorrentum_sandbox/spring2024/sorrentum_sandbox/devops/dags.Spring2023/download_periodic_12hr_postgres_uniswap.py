"""
DAG to download data from uniswap.
"""

from datetime import datetime, timedelta

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_12hr_postgres_uniswap"
_DAG_DESCRIPTION = "Download uniswap data every minute and save to Postgres"
# Specify when often to execute the DAG.
_SCHEDULE = timedelta(hours=12)

# Pass default parameters for the DAG.
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
    start_date=datetime(2023, 4, 27, 0, 0, 0),
)

bash_command = [
    # Sleep 5 seconds to ensure the bar is finished.
    "sleep 5",
    "&&",
    "python3 /cmamp/sorrentum_sandbox/examples/ml_projects/Issue25_Team6_Implement_sandbox_for_Bitquery_and_Uniswap/download_to_db.py",
    "--start_timestamp {{ data_interval_start }}",
    "--target_table uniswap_table",
    "--live_flag",
]

downloading_task = BashOperator(
    task_id="download.periodic_12hr.postgres.uniswap",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
