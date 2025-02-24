"""
Example DAG to load Reddit data from DB, transform and save back to the DB.
"""

import datetime

import airflow
from airflow.operators.bash import BashOperator

_DAG_ID = "validate_and_extract_features_periodic_5min_mongo_posts_reddit"
_DAG_DESCRIPTION = (
    "Load data from DB, extract features and save to MongoDB  every 5 minutes"
)
# Specify when to execute the DAG.
_SCHEDULE = "*/5 * * * *"

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
    start_date=datetime.datetime(2022, 1, 1, 0, 0, 0),
)

# Extract features for current time frame minus 5 minutes on order to make sure
# that downloader already finished.
bash_command = [
    "/cmamp/sorrentum_sandbox/examples/reddit/load_validate_transform.py",
    "--start_timestamp '{{ data_interval_start - macros.timedelta(minutes=10)}}'",
    "--end_timestamp '{{ data_interval_end - macros.timedelta(minutes=10) }}'",
    "-v DEBUG",
]

extract_task = BashOperator(
    task_id="validate.extract.features.airflow.5min.mongo.posts.reddit",
    depends_on_past=False,
    bash_command=" ".join(bash_command),
    dag=dag,
)

extract_task
