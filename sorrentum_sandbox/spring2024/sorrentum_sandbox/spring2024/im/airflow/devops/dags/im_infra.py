"""
Import as:

import im.airflow.devops.dags.im_infra as imaddimin
"""

import os

import airflow
from airflow import DAG
from airflow.operators.bash import BashOperator

P1_AIRFLOW_WORKER_DB_LOADER_QUEUE = os.environ[
    "P1_AIRFLOW_WORKER_DB_LOADER_QUEUE"
]
STAGE = os.environ["STAGE"]
SEND_EMAIL = STAGE not in ["LOCAL", "TEST"]

default_args = {
    "owner": "airflow",
    "start_date": airflow.utils.dates.days_ago(1),
    "email": [],
    "email_on_failure": SEND_EMAIL,
    "email_on_retry": SEND_EMAIL,
}

dag = DAG(
    "IM_INFRA",
    default_args=default_args,
    schedule_interval=None,
    max_active_runs=1,
)

# Create EDGAR DB schema.
test = BashOperator(
    task_id="test",
    bash_command='bash -c "/app/im/devops/docker_build/entrypoints/entrypoint_worker.sh '
    "im/app/transform/convert_s3_to_sql.py "
    "--provider kibot "
    "--symbol AAPL "
    "--frequency T "
    "--contract_type continuous "
    "--asset_class stocks "
    '--exchange NYSE"',
    dag=dag,
    queue=P1_AIRFLOW_WORKER_DB_LOADER_QUEUE,
)
