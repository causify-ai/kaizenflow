"""
DAG to compute real time data from Chainlink.
"""

import datetime
from datetime import timedelta

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_6hr_postgres_chainlink_compute"
_DAG_DESCRIPTION = (
    "Download Chainlink compute data every 6 hours and save to Postgres"
)

# Pass default parameters for the DAG.
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval="30 5,11,17,23 * * *", # Execute the DAG every 6 hours.
    catchup=False,
    start_date=datetime.datetime(2023, 4, 5, 0, 0, 0),
    dagrun_timeout=timedelta(minutes=20),
    )

# SQL query to retrive the maximum roundid of BTC/USC data in chainlink_real_time table.
postgres_query = "\"SELECT max(roundid) FROM chainlink_compute WHERE pair = 'BTC / USD'\""
get_max_roundid = "export max_roundid=$(psql -U postgres -p 5532 -d airflow -h host.docker.internal -c" + \
                  postgres_query + \
                  "| sed -n '3p' | tr -d ' ')"

# bash command we want to execute by the scheduled time.
bash_command = [
    "cd /cmamp/sorrentum_sandbox/examples/ml_projects/Issue26_Team7_Implement_sandbox_for_Chainlink",
    "&&",
    "pip install web3",
    "&&",
    "export PGPASSWORD=postgres",
    "&&",
    get_max_roundid,
    "&&",
    "./compute_to_db.py --start_roundid $max_roundid --target_table 'chainlink_compute'"
]

downloading_task = BashOperator(
    task_id="download.periodic_6hr.postgres.chainlink.compute",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
