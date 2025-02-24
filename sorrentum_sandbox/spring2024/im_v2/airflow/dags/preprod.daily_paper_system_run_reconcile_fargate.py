# This is a utility DAG to conduct QA on real time data download
# DAG task downloads data for last N minutes in one batch

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
# _STAGE = _FILENAME.split(".")[0]
_STAGE = "preprod"
assert _STAGE in ["prod", "preprod", "test"]

# Used for seperations of deployment environments
# ignored when executing on prod/preprod.
_USERNAME = ""

# Deployment type, if the task should be run via fargate (serverless execution)
# or EC2 (machines deployed in our auto-scaling group)
_LAUNCH_TYPE = "fargate"
assert _LAUNCH_TYPE in ["ec2", "fargate"]

_DAG_ID = _FILENAME.rsplit(".", 1)[0]
_DAG_BUILDERS = ["C1b", "C3a", "C8b"]
_LIVENESS = "CANDIDATE"
_INSTANCE_TYPE = "PROD"
_VERBOSITY = "DEBUG"
_EXCHANGE = "binance"
_SYSTEM_STAGE = "preprod"
_ACCOUNT_TYPE = "trading"
_SECRET_ID = 3
_DAG_DESCRIPTION = "Test System DAG"
# Run duration (specified in hours so it can be propagated to both container
# ans Airflow 'cron' schedule).
_SYSTEM_RUN_MODE = "paper_trading"
_RUN_DURATION = 24
_RUN_DURATION_IN_SECS = int(_RUN_DURATION) * 3600
# _SCHEDULE = "0 5 * * *" from
_SCHEDULE = "0 13 * * *"


# Used for container overrides inside DAG task definition.
# If this is a test DAG don't forget to add your username to container suffix.
# i.e. cmamp-test-juraj since we try to follow the convention of container having
# the same name as task-definition if applicable
# Set to the name your task definition is suffixed with i.e. cmamp-test-juraj,
_CONTAINER_SUFFIX = f"-{_STAGE}" if _STAGE in ["preprod", "test"] else ""
_CONTAINER_SUFFIX += f"-{_USERNAME}" if _STAGE == "test" else ""
# _CONTAINER_NAME = f"orange{_CONTAINER_SUFFIX}"
_CONTAINER_NAME = "cmamp-test"

ecs_cluster = Variable.get(f"{_STAGE}_ecs_cluster")
# The naming convention is set such that this value is then reused
# in log groups, stream prefixes and container names to minimize
# convolution and maximize simplicity.
ecs_task_definition = _CONTAINER_NAME

# Subnets and security group is not needed for EC2 deployment but
# we keep the configuration header unified for convenience/reusability.
ecs_subnets = [Variable.get("ecs_subnet3")]
ecs_security_group = [Variable.get("ecs_security_group")]
ecs_awslogs_group = f"/ecs/{ecs_task_definition}"
ecs_awslogs_stream_prefix = f"ecs/{ecs_task_definition}"

# Pass default parameters for the DAG.
default_args = {
    "retries": 0,
    "email": [Variable.get(f"{_STAGE}_notification_email")],
    "email_on_failure": True,  # True if _STAGE in ["test", "prod", "preprod"] else False,
    "email_on_retry": True,
    "owner": "airflow",
}


def align_to_5min_grid(date):
    """
    Utility function to align a date to 5 min grid.
    """
    return date.replace(minute=date.minute - date.minute % 5, second=0)


# Create a DAG.
dag = airflow.DAG(
    dag_id=_DAG_ID,
    description=_DAG_DESCRIPTION,
    max_active_runs=2,
    default_args=default_args,
    schedule_interval=_SCHEDULE,
    catchup=False,
    user_defined_filters={
        "align_to_5min_grid": align_to_5min_grid,  # Macro can also be a function
    },
    user_defined_macros={
        "dag_start_time": "{{ data_interval_end if 'scheduled' in run_id else macros.datetime.now() }}",
        "run_duration_in_sec": _RUN_DURATION_IN_SECS,
    },
    start_date=datetime.datetime(2022, 8, 1, 0, 0, 0),
)


efs_mount = "{{ var.value.efs_mount }}"
# We use data_interval_end because the DAG is supposed to start in real-time.
dag_run_mode = "{{ 'scheduled' if 'scheduled' in run_id else 'manual' }}"
start_timestamp = "{{ (data_interval_end + macros.timedelta(seconds=600)) \
                    | align_to_5min_grid | ts_nodash | replace('T', '_') }}"
end_timestamp = "{{ (((data_interval_end + macros.timedelta(seconds=(run_duration_in_sec | int) + 600)) \
                    | align_to_5min_grid) - macros.timedelta(seconds=300)) | ts_nodash | replace('T', '_') }}"
run_date = "{{ data_interval_end.date() | string | replace('-', '') }}"
run_mode_for_log = "{{ '' if 'scheduled' in run_id else '.manual' }}"
log_name_specifier = f"{dag_run_mode}.{start_timestamp}.{end_timestamp}"
system_run_cmd = [
    "/app/amp/dataflow_amp/system/Cx/scripts/run_Cx_prod_system.py",
    # By Airflow's scheduling logic we need to actually the date of
    # the end of the interval.
    "--strategy '{}'",
    "--dag_builder_name '{}'",
    f"--trade_date {run_date}",
    f"--liveness '{_LIVENESS}'",
    f"--instance_type '{_INSTANCE_TYPE}'",
    f"--exchange '{_EXCHANGE}' ",
    f"--stage '{_SYSTEM_STAGE}'",
    f"--account_type '{_ACCOUNT_TYPE}'",
    f"--secret_id '{_SECRET_ID}'",
    f"-v '{_VERBOSITY}' 2>&1",
    "--start_time '{{ (data_interval_end + macros.timedelta(seconds=600)) | \
                    align_to_5min_grid | ts_nodash | replace('T', '_') }}'",
    "--run_duration {{ run_duration_in_sec }}",
    f"--run_mode '{_SYSTEM_RUN_MODE}'",
    "--log_file_name  '{}/logs/log.{}.txt'",
    "--dst_dir '{}/system_log_dir.{}'",
]
system_reconcile_cmd = [
    # This is a hack to pass hserver.is_inside_docker()
    #  because when ran in ECS it is not present there
    #  by default.
    "mkdir /.dockerenv",
    "&&",
    "invoke reconcile_run_all",
    "--dag-builder-name {}",
    "--dst-root-dir {}",
    "--prod-data-source-dir {}",
    f"--start-timestamp-as-str {start_timestamp}",
    f"--end-timestamp-as-str {end_timestamp}",
    f"--mode {dag_run_mode}",
    f"--run-mode '{_SYSTEM_RUN_MODE}'",
    "--run-notebook",
]

kwargs = {}
kwargs["network_configuration"] = {
    "awsvpcConfiguration": {
        "securityGroups": ecs_security_group,
        "subnets": ecs_subnets,
    },
}

start_task = DummyOperator(task_id="start_dag", dag=dag)
end_task = DummyOperator(task_id="end_dag", dag=dag)


def get_task(task_id, task_cmd, is_system_run) -> ECSOperator:
    task = ECSOperator(
        task_id=task_id,
        dag=dag,
        aws_conn_id=None,
        cluster=ecs_cluster,
        task_definition=ecs_task_definition,
        launch_type=_LAUNCH_TYPE.upper(),
        overrides={
            "containerOverrides": [
                {
                    "name": _CONTAINER_NAME,
                    "command": task_cmd,
                }
            ],
            "cpu": "1024" if is_system_run else "2048",
            "memory": "4096" if is_system_run else "6144",
            # EphemeralStorage Overrides 'size' setting must be at least 21.
            "ephemeralStorage": {"sizeInGiB": 21 if is_system_run else 40},
        },
        awslogs_group=ecs_awslogs_group,
        awslogs_stream_prefix=ecs_awslogs_stream_prefix,
        execution_timeout=datetime.timedelta(hours=25),
        **kwargs,
    )
    return task


# HW requirements


for dag_builder in _DAG_BUILDERS:

    log_base_dir = f"{efs_mount}/{_STAGE}/system_reconciliation/{dag_builder}/{run_date + run_mode_for_log}"
    curr_bash_command = copy.deepcopy(system_run_cmd)
    curr_bash_command[1] = curr_bash_command[1].format(dag_builder)
    curr_bash_command[2] = curr_bash_command[2].format(dag_builder)
    curr_bash_command[-2] = curr_bash_command[-2].format(
        log_base_dir, log_name_specifier
    )
    curr_bash_command[-1] = curr_bash_command[-1].format(
        log_base_dir, log_name_specifier
    )

    curr_reconcile_command = copy.deepcopy(system_reconcile_cmd)
    curr_reconcile_command[3] = curr_reconcile_command[3].format(dag_builder)
    reconc_log_base_dir = f"{efs_mount}/{_STAGE}/prod_reconciliation/"
    curr_reconcile_command[4] = curr_reconcile_command[4].format(
        reconc_log_base_dir
    )
    curr_reconcile_command[5] = curr_reconcile_command[5].format(log_base_dir)

    system_run_task = get_task(
        f"{dag_builder}.system_run", curr_bash_command, True
    )
    system_reconcile_task = get_task(
        f"{dag_builder}.system_reconcile", curr_reconcile_command, False
    )

    start_task >> system_run_task >> system_reconcile_task >> end_task
