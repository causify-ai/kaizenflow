# This is a utility DAG to download OHLCV data daily.

import copy
import datetime
import os

import airflow
from airflow.contrib.operators.ecs_operator import ECSOperator
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator

_FILENAME = os.path.basename(__file__)

# This variable will be propagated throughout DAG definition as a prefix to
# names of Airflow configuration variables, allow to switch from test to preprod/prod
# in one line (in best case scenario).
_STAGE = _FILENAME.split(".")[0]
assert _STAGE in ["prod", "preprod", "test"]

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
_USERNAME = ""

# Deployment type, if the task should be run via fargate (serverless execution)
# or EC2 (machines deployed in our auto-scaling group)
_LAUNCH_TYPE = "fargate"
assert _LAUNCH_TYPE in ["ec2", "fargate"]

_DAG_ID = _FILENAME.rsplit(".", 1)[0]
_DATA_TYPES = ["ohlcv"]
# List jobs in the following tuple format:
#  vendor, exchange, contract, data_type, universe
_JOBS = [
    ("crypto_chassis", "binance", "spot", "ohlcv", "v3"),
    ("crypto_chassis", "binance", "futures", "ohlcv", "v3"),
    ("ccxt", "binance", "spot", "ohlcv", "v7"),
    ("ccxt", "binance", "futures", "ohlcv", "v7"),
    ("ccxt", "binanceus", "spot", "ohlcv", "v7"),
    ("ccxt", "okx", "futures", "ohlcv", "v7.3"),
]
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "periodic_daily"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "parquet"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = f"Daily {_DATA_TYPES} data download."
# Specify when/how often to execute the DAG.
_SCHEDULE = Variable.get(f"{_DAG_ID}_schedule")
# Used for container overrides inside DAG task definition.
# If this is a test DAG don't forget to add your username to container suffix.
# i.e. cmamp-test-juraj since we try to follow the convention of container having
# the same name as task-definition if applicable
# Set to the name your task definition is suffixed with i.e. cmamp-test-juraj,
_CONTAINER_SUFFIX = f"-{_STAGE}" if _STAGE in ["preprod", "test"] else ""
_CONTAINER_SUFFIX += f"-{_USERNAME}" if _STAGE == "test" else ""
_CONTAINER_NAME = f"cmamp{_CONTAINER_SUFFIX}"

ecs_cluster = Variable.get(f"{_STAGE}_ecs_cluster")
# The naming convention is set such that this value is then reused
# in log groups, stream prefixes and container names to minimize
# convolution and maximize simplicity.
ecs_task_definition = _CONTAINER_NAME

# Subnets and security group is not needed for EC2 deployment but
# we keep the configuration header unified for convenience/reusability.
ecs_subnets = [Variable.get("ecs_subnet1"), Variable.get("ecs_subnet2")]
ecs_security_group = [Variable.get("ecs_security_group")]
ecs_awslogs_group = f"/ecs/{ecs_task_definition}"
ecs_awslogs_stream_prefix = f"ecs/{ecs_task_definition}"
s3_bucket_path = f"s3://{Variable.get(f'{_STAGE}_s3_data_bucket')}"
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
    catchup=True,
    start_date=datetime.datetime(2023, 2, 1, 0, 0, 0),
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
    # The command needs to be executed manually first because --incremental
    # assumes appending to existing folder.
    "--incremental",
    f"--s3_path '{s3_bucket_path}'",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
]

start_task = DummyOperator(task_id="start_dag", dag=dag)
end_download = DummyOperator(task_id="end_dag", dag=dag)

for vendor, exchange, contract, data_type, universe in _JOBS:

    # TODO(Juraj): Make this code more readable.
    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_bash_command = copy.deepcopy(download_command)
    curr_bash_command[3] = curr_bash_command[3].format(vendor)
    curr_bash_command[4] = curr_bash_command[4].format(exchange)
    curr_bash_command[5] = curr_bash_command[5].format(universe)
    curr_bash_command[6] = curr_bash_command[6].format(data_type)
    curr_bash_command[7] = curr_bash_command[7].format(contract)

    kwargs = {}
    kwargs["network_configuration"] = {
        "awsvpcConfiguration": {
            "securityGroups": ecs_security_group,
            "subnets": ecs_subnets,
        },
    }

    downloading_task = ECSOperator(
        task_id=f"download.{_DOWNLOAD_MODE}.{vendor}.{exchange}.{contract}.{universe}",
        dag=dag,
        aws_conn_id=None,
        cluster=ecs_cluster,
        task_definition=ecs_task_definition,
        launch_type=_LAUNCH_TYPE.upper(),
        overrides={
            "containerOverrides": [
                {
                    "name": _CONTAINER_NAME,
                    "command": curr_bash_command,
                }
            ]
        },
        awslogs_group=ecs_awslogs_group,
        awslogs_stream_prefix=ecs_awslogs_stream_prefix,
        execution_timeout=datetime.timedelta(minutes=15),
        **kwargs,
    )

    start_task >> downloading_task >> end_download
