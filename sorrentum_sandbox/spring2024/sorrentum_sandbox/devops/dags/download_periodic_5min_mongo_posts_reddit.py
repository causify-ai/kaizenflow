"""
DAG to download Reddit data.

Import as:

import sorrentum_sandbox.devops.airflow_data.dags.download_periodic_5min_mongo_posts_reddit as ssdadddp5mpr
"""


import datetime

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "download_periodic_5min_mongo_posts_reddit"
_DAG_DESCRIPTION = "Download Reddit posts every 5 minutes and save to MongoDB"
# Specify when to execute the DAG.
_SCHEDULE = "*/5 * * * *"

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
    start_date=datetime.datetime(2022, 1, 1, 0, 0, 0),
)

bash_command = [
    # Sleep 5 seconds to ensure the post is submitted.
    "sleep 5",
    "&&",
    "/cmamp/sorrentum_sandbox/examples/reddit/download_to_db.py",
    "--start_timestamp '{{ data_interval_start }}'",
    "--end_timestamp '{{ data_interval_end }}'",
    "-v DEBUG",
]

downloading_task = BashOperator(
    task_id="download.airflow.downloaded.5min.mongo.posts.reddit",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

downloading_task
