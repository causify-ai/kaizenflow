# This is a utility DAG to conduct QA on real time data download.
# The task compares the ad-hoc downloaded data with the contents of of the
# database, to confirm a match or show discrepancies.

# IMPORTANT NOTES:
# Make sure to set correct dag schedule `schedule_interval` parameter.

# This DAG's configuration deploys tasks to AWS Fargate to offload the EC2s
# mainly utilized for real-time download.
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

# This variable is propagated throughout DAG definition as a prefix to names of
# Airflow configuration variables, allowing to switch from test to preprod/prod
# in one line.
# _STAGE = _FILENAME.split(".")[0]
_STAGE = aiutmisc.get_stage_from_filename(_FILENAME)

# Used for seperations of deployment environments and ignored when executing on
# prod/preprod.
_USERNAME = ""

_DAG_ID = aiutmisc.get_dag_id_from_filename(_FILENAME)
# List of dicts to specify parameters for each reconciliation jobs.
# "periodic_daily.airflow.downloaded_1min.parquet.ohlcv.futures.v7.ccxt.binance.v1_0_0"
_QA_JOBS = [
    {
        "dataset_signature1": "realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7_3.ccxt.binance.v1_0_0",
        "dataset_signature2": "periodic_10min.airflow.downloaded_1min.parquet.ohlcv.futures.v7_3.ccxt.binance.v1_0_0",
        "add_invoke_params": [],
    },
]
# Shared location to store the reconciliaiton notebook into
_QA_NB_DST_DIR = os.path.join(
    "{{ var.value.efs_mount }}", _STAGE, "data_qa", "period_10min"
)
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "periodic_10min"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "parquet"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = (
    "10 min cross data QA. Run QA notebook and publish results"
    + " to a shared EFS."
)
_SCHEDULE = "*/10 * * * *"

_S3_BUCKET_PATH = f"s3://{Variable.get(f'{_STAGE}_s3_data_bucket')}"

_ECS_TASK_DEFINITION = aiutecop.get_task_definition(_STAGE, False, _USERNAME)

# Pass default parameters for the DAG.
default_args = {
    "retries": 0,
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
    start_date=datetime.datetime(2023, 9, 10, 0, 0, 0),
)

download_command = [
    "/app/amp/im_v2/common/data/extract/download_bulk.py",
    "--start_timestamp '{{ data_interval_start.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--end_timestamp '{{ data_interval_end.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--vendor '{}'",
    "--exchange_id '{}'",
    "--universe '{}'",
    "--data_type '{}'",
    "--contract_type '{}'",
    "--aws_profile 'ck'",
    # The command needs to be executed manually first because --incremental
    # assumes appending to existing folder.
    # "--incremental",
    "--assert_on_missing_data",
    f"--s3_path '{_S3_BUCKET_PATH}'",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
    "--pq_save_mode 'list_and_merge'",
]

invoke_cmd = [
    "mkdir /.dockerenv",
    "&&",
    "invoke run_cross_dataset_qa_notebook",
    f"--stage '{_STAGE}'",
    "--start-timestamp '{{ data_interval_start.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--end-timestamp '{{ data_interval_end.replace(second=0) - macros.timedelta(minutes=5) }}'",
    "--dataset-signature1 '{}'",
    "--dataset-signature2 '{}'",
    "--aws-profile 'ck'",
    f"--base-dst-dir '{_QA_NB_DST_DIR}'",
]

start_comparison = DummyOperator(task_id="start_comparison", dag=dag)
end_comparison = DummyOperator(task_id="end_comparison", dag=dag)
end_dag = DummyOperator(task_id="end_dag", dag=dag)

for job in _QA_JOBS:

    # TODO(Juraj): we should using dataset schema utils for this.
    dataset_signature_10min = job["dataset_signature2"].split(".")
    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_bash_command = copy.deepcopy(download_command)
    curr_bash_command[3] = curr_bash_command[3].format(dataset_signature_10min[7])
    curr_bash_command[4] = curr_bash_command[4].format(dataset_signature_10min[8])
    # In the download script the universe is specified in v7.1 notation.
    curr_bash_command[5] = curr_bash_command[5].format(
        dataset_signature_10min[6].replace("_", ".")
    )
    curr_bash_command[6] = curr_bash_command[6].format(dataset_signature_10min[4])
    curr_bash_command[7] = curr_bash_command[7].format(dataset_signature_10min[5])

    # Do a deepcopy of the bash cmd list so we can reformat params on each iteration.
    curr_invoke_cmd = copy.deepcopy(invoke_cmd)
    curr_invoke_cmd[6] = curr_invoke_cmd[6].format(job["dataset_signature1"])
    curr_invoke_cmd[7] = curr_invoke_cmd[7].format(job["dataset_signature2"])
    for param in job["add_invoke_params"]:
        curr_invoke_cmd.append(param)

    downloading_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        "download_data",
        curr_bash_command,
        _ECS_TASK_DEFINITION,
        512,
        1024,
    )

    comparing_task = aiutecop.get_ecs_run_task_operator(
        dag,
        _STAGE,
        "data_qa",
        curr_invoke_cmd,
        _ECS_TASK_DEFINITION,
        512,
        2048,
    )

    (
        start_comparison
        >> downloading_task
        >> comparing_task
        >> end_comparison
        >> end_dag
    )

if _STAGE != "test":
    telegram_notification_task = aiutteop.get_telegram_operator(
        dag, _STAGE, "datapull", _DAG_ID, "{{ run_id }}"
    )
    end_comparison >> telegram_notification_task >> end_dag
