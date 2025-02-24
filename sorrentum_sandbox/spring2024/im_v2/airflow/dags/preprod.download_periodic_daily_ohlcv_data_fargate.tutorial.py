"""
Import as:

import im_v2.airflow.dags.preprod.download_periodic_daily_ohlcv_data_fargate.tutorial as imvadpdpdodft
"""

# This is a tutorial DAG to demonstrate extract part of the DataPull flow.

import copy
import datetime
import os

import airflow
import airflow_utils.ecs.operator as aiutecop
import airflow_utils.misc as aiutmisc
import airflow_utils.telegram.operator as aiutteop
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator

_FILENAME = os.path.basename(__file__)

# This variable will be propagated throughout DAG definition as a prefix to
# names of Airflow configuration variables, allows to switch between test/preprod/prod stages when specifying resources, e.g. S3 bucket for the correct stage.
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments.
# Ignored when executing on prod/preprod.
_ISSUE_ID = "replace-with-your-issue-id"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _ISSUE_ID)

# Deployment type, determines whether a task should be run via AWS Fargate (serverless execution)
# or EC2 (machines deployed in our auto-scaling group).
_LAUNCH_TYPE = "fargate"

# Simplifies coupling of DAG name and DAG ID (what's displayed in the Airflow UI).
_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)

# List jobs in the following tuple format:
#  vendor, exchange, contract, data_type, universe
_JOBS = [
    ("ccxt", "binance", "spot", "ohlcv", "v7"),
    ("ccxt", "binance", "futures", "ohlcv", "v7.3"),
]
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data.
# Dataset signature is formed based on these parameters,
# determines for example the path to the S3 used to save the data
_DOWNLOAD_MODE = "periodic_daily"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "parquet"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = "Daily OHLCV data download."
_S3_BUCKET_PATH = f"s3://{Variable.get(f'{_STAGE}_s3_data_bucket')}"

# Specify when/how often to execute the DAG.
_SCHEDULE = Variable.get(f"{_DAG_ID}_schedule")
# Pass default parameters for the DAG.
default_args = {
    "retries": 1 if _STAGE in ["prod", "preprod"] else 0,
    "email": [Variable.get(f"{_STAGE}_notification_email")],
    "email_on_failure": True if _STAGE in ["prod", "preprod"] else False,
    "email_on_retry": False,
    "owner": "airflow",
}

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=1,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2023, 3, 20, 0, 0, 0),
    tags=[_STAGE],
)

download_command = [
    "/app/amp/im_v2/common/data/extract/download_bulk.py",
    "--end_timestamp '{{ data_interval_end.replace(hour=0, minute=0, second=0) - macros.timedelta(minutes=1) }}'",
    "--start_timestamp '{{ data_interval_start.replace(hour=0, minute=0, second=0) }}'",
    "--vendor '{}'",
    "--exchange_id '{}'",
    "--universe '{}'",
    "--data_type '{}'",
    "--contract_type '{}'",
    "--aws_profile 'ck'",
    "--assert_on_missing_data",
    f"--s3_path '{_S3_BUCKET_PATH}'",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
]

start_task = DummyOperator(task_id="start_dag", dag=dag)
end_download = DummyOperator(task_id="end_download", dag=dag)
end_dag = DummyOperator(task_id="end_dag", dag=dag)

for vendor, exchange, contract, data_type, universe in _JOBS:
    # TODO(Juraj): Make this code more readable.
    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_bash_command = copy.deepcopy(download_command)
    curr_bash_command[3] = curr_bash_command[3].format(vendor)
    curr_bash_command[4] = curr_bash_command[4].format(exchange)
    curr_bash_command[5] = curr_bash_command[5].format(universe)
    curr_bash_command[6] = curr_bash_command[6].format(data_type)
    curr_bash_command[7] = curr_bash_command[7].format(contract)

    downloading_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        f"download.{_DOWNLOAD_MODE}.{vendor}.{exchange}.{contract}.{universe}",
        curr_bash_command,
        _ECS_TASK_DEFINITION,
        256,
        512,
        assign_public_ip=True,
    )

    start_task >> downloading_task >> end_download >> end_dag

telegram_notification_task = aiutteop.get_telegram_operator(
    dag, _STAGE, "datapull", _DAG_ID, "{{ run_id }}"
)
end_download >> telegram_notification_task >> end_dag
