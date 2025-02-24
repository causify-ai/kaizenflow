"""
DAG to download real time data from Chainlink.

Import as:

import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.chainlink_BTC_airflow as ssempitisfccba
"""

import datetime
from datetime import timedelta

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_1hr_postgres_chainlink_BTC_USD"
_DAG_DESCRIPTION = (
    "Download Chainlink BTC/USD data every hour and save to Postgres"
)

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
    schedule_interval="@hourly",  # Execute the DAG 1hr.
    catchup=False,
    start_date=datetime.datetime(2023, 4, 5, 0, 0, 0),
    dagrun_timeout=timedelta(minutes=30),
)

# SQL query to retrive the maximum roundid of BTC/USC data in chainlink_real_time table.
postgres_query = (
    "\"SELECT max(roundid) FROM chainlink_real_time WHERE pair = 'BTC / USD'\""
)
get_max_roundid = (
    "export max_roundid=$(psql -U postgres -p 5532 -d airflow -h host.docker.internal -c"
    + postgres_query
    + "| sed -n '3p' | tr -d ' ')"
)

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
    "./download_to_db.py --pair BTC/USD --start_roundid $max_roundid --target_table 'chainlink_real_time'",
]

downloading_task = BashOperator(
    task_id="download.periodic_1hr.postgres.chainlink.BTC.USD",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
