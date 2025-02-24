# This DAG is used to download realtime data to the IM database
#  via REST API.


import copy
import datetime
import os
from itertools import product

import airflow
import airflow_utils.telegram.operator as aiutteop
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
_USERNAME = "juraj"

# Deployment type, if the task should be run via fargate (serverless execution)
# or EC2 (machines deployed in our auto-scaling group)
_LAUNCH_TYPE = "fargate"
assert _LAUNCH_TYPE in ["ec2", "fargate"]

_DAG_ID = _FILENAME.rsplit(".", 1)[0]
_EXCHANGES = ["binance"]
_VENDORS = ["ccxt"]
_UNIVERSES = {"ccxt": "v7"}
# _CONTRACTS = ["spot", "futures"]
_CONTRACTS = ["futures"]
# _DATA_TYPES = ["ohlcv", "bid_ask"]
_DATA_TYPES = ["ohlcv"]
# How often (in minutes) should a downloader within a single container run.
_DOWNLOAD_INTERVAL = {"ohlcv": 1}
# Specify how long should the DAG be running for (in minutes).
_RUN_FOR = 60
# Specify how much in advance should the DAG be scheduled (in minutes).
# We leave a couple minutes to account for delay in container setup
# such that the download can start at a precise point in time.
_DAG_STANDBY = 6
# These values are changed dynamically based on DAG purpose and nature
#  of the downloaded data
_DOWNLOAD_MODE = "periodic_1min"
_ACTION_TAG = "downloaded_1min"
_DATA_FORMAT = "postgres"
# The value is implicit since this is an Airflow DAG.
_DOWNLOADING_ENTITY = "airflow"
_DAG_DESCRIPTION = (
    f"Realtime {_DATA_TYPES} data download, contracts:"
    + f"{_CONTRACTS}, using {_VENDORS} from {_EXCHANGES}."
)
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
ecs_subnets = [Variable.get("ecs_public_subnet")]
ecs_security_group = [Variable.get("ecs_public_sg")]
ecs_awslogs_group = f"/ecs/{ecs_task_definition}"
ecs_awslogs_stream_prefix = f"ecs/{ecs_task_definition}"

# Pass default parameters for the DAG.
default_args = {
    "retries": 1 if _STAGE in ["prod", "preprod"] else 0,
    "retry_delay": 0,
    "email": [Variable.get(f"{_STAGE}_notification_email")],
    "email_on_failure": True if _STAGE == ["prod", "preprod"] else False,
    "owner": "airflow",
}

# Create a command, leave values to be parametrized.
bash_command = [
    "/app/amp/im_v2/{}/data/extract/download_exchange_data_to_db_periodically.py",
    "--exchange_id '{}'",
    "--universe '{}'",
    "--db_table '{}'",
    "--data_type '{}'",
    "--contract_type '{}'",
    "--interval_min '{}'",
    "--vendor {}",
    f"--db_stage '{_STAGE}'",
    "--aws_profile 'ck'",
    # At this point we set up a logic for real time execution
    # Start date is postponed by _DAG_STANDBY minutes and a short
    # few seconds delay to ensure the bars from the nearest minute are finished.
    "--start_time '{{ macros.datetime.now(dag.timezone).replace(second=0, microsecond=0) + macros.timedelta(minutes=var.value.rt_data_download_standby_min | int, seconds=10) }}'",
    "--stop_time '{{ data_interval_end + macros.timedelta(minutes=(var.value.rt_data_download_run_for_min | int) + var.value.rt_data_download_standby_min | int) }}'",
    "--method 'rest'",
    f"--download_mode '{_DOWNLOAD_MODE}'",
    f"--downloading_entity '{_DOWNLOADING_ENTITY}'",
    f"--action_tag '{_ACTION_TAG}'",
    f"--data_format '{_DATA_FORMAT}'",
]

# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=2,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    start_date=datetime.datetime(2022, 7, 1, 0, 0, 0),
)

start_task = DummyOperator(task_id="start", dag=dag)
end_task = DummyOperator(task_id="end", dag=dag)


for vendor, exchange, contract, data_type in product(
    _VENDORS, _EXCHANGES, _CONTRACTS, _DATA_TYPES
):

    table_name = f"{vendor}_{data_type}"
    # TODO(Juraj): CmTask2804.
    if contract == "futures":
        table_name += "_futures"

    # Do a deepcopy of the bash command list so we can reformat params on each iteration.
    curr_bash_command = copy.deepcopy(bash_command)
    curr_bash_command[0] = curr_bash_command[0].format(vendor)
    curr_bash_command[1] = curr_bash_command[1].format(exchange)
    curr_bash_command[2] = curr_bash_command[2].format(_UNIVERSES[vendor])
    curr_bash_command[3] = curr_bash_command[3].format(table_name)
    curr_bash_command[4] = curr_bash_command[4].format(data_type)
    curr_bash_command[5] = curr_bash_command[5].format(contract)
    curr_bash_command[6] = curr_bash_command[6].format(
        _DOWNLOAD_INTERVAL[data_type]
    )
    curr_bash_command[7] = curr_bash_command[7].format(vendor)

    kwargs = {}
    kwargs["network_configuration"] = {
        "awsvpcConfiguration": {
            "securityGroups": ecs_security_group,
            "subnets": ecs_subnets,
            "assignPublicIp": "ENABLED",
        },
    }

    downloading_task = ECSOperator(
        task_id=f"download.{vendor}.{exchange}.{data_type}.{contract}",
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
        # just as a small backup mechanism.
        execution_timeout=datetime.timedelta(
            minutes=_RUN_FOR + (2 * _DAG_STANDBY)
        ),
        **kwargs,
    )
    # Define the sequence of execution of task.
    start_task >> downloading_task >> end_task

if _STAGE != "test":
    telegram_notification_task = aiutteop.get_telegram_operator(
        dag, _STAGE, _DAG_ID, "{{ run_id }}"
    )
    end_task >> telegram_notification_task
