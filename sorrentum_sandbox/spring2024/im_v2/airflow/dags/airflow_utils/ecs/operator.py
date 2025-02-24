"""
Import as:

import im_v2.airflow.dags.airflow_utils.ecs.operator as imvadaueop
"""

import datetime
from typing import List

import airflow
from airflow.models import Variable
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator

# Subnets and security group is not needed for EC2 deployment but
# we keep the configuration header unified for convenience/reusability.
_ECS_SUBNETS = [
    Variable.get("ecs_subnet1"),
    Variable.get("ecs_subnet2"),
    Variable.get("ecs_subnet3"),
]
_ECS_SECURITY_GROUPS = [Variable.get("ecs_security_group")]

# _ECS_PUBLIC_SUBNETS = [Variable.get("ecs_public_subnet1"), Variable.get("ecs_public_subnet2"), Variable.get("ecs_public_subnet3")]
_ECS_PUBLIC_SUBNETS = [Variable.get("ecs_public_subnet3")]
_ECS_PUBLIC_SECURITY_GROUP = [Variable.get("ecs_public_sg")]


def get_task_definition(
    stage: str, is_full_system_run: bool, username: str
) -> str:
    """
    Get task definition name based on given arguments.

    :param stage: stage to run in, e.g. preprod
    :param is_full_system_run:
    :param
    :return: task definition name corresponding to the provided arguments.
    """
    # Test stage task is always ran by a specific developer.
    if stage == "test":
        assert username != ""
    # Assert logical consistency for running in prod, preprod
    # environment.
    if stage != "test":
        assert username == ""

    ecs_task_definition = "cmamp"
    if is_full_system_run and stage != "test":
        ecs_task_definition += "-system"
    if stage in ["preprod", "test"]:
        ecs_task_definition += f"-{stage}"
    if username != "":
        ecs_task_definition += f"-{username}"
    return ecs_task_definition


def get_ecs_run_task_operator(
    dag: airflow.DAG,
    stage: str,
    task_id: str,
    task_cmd: List[str],
    task_definition: str,
    cpu_units: int,
    memory_mb: int,
    *,
    assign_public_ip: bool = False,
    ephemeralStorageGb: int = 21,
    launch_type: str = "fargate",
) -> EcsRunTaskOperator:
    """
    Get operator to run ECS task.

    :param dag: airflow DAG to assign the operator to
    :param stage: stage to run in, e.g. preprod
    :param task_id: unique identifier of the to-be created task in the current DAG
    :param task_cmd: bash command used as an entrypoint for the underlying ECS task executed
     by the operator.
    :param task_definition: ECS task definition to use, e.g. cmamp-system-preprod
    :param cpu_units: CPU units to assign to the ECS task, e.g. 256, 512, 1024, 2048 (where 1024 = 1 CPU)
    :param memory_mb: RAM in megabytes to assign to the task, e.g. 512, 1024
    :param assign_public_ip: specify if the task should have a public IP assigned, default is False
    :param ephemeralStorageGb: Size of virtual hard drive assigned to the task, default is 21 (lowest possible)
    :param launch_type: execution environment to run the task in (EC2 or Fargate)
    :return: fully configured EcsRunTaskOperator assigned to the provided DAG
    """
    assert launch_type in ["ec2", "fargate"]

    container_overrides = [
        {
            # Currently we use a convention to match container name
            #  with the task definition to simplify our life.
            "name": task_definition,
            "command": task_cmd,
        }
    ]

    kwargs = {}
    kwargs["network_configuration"] = {
        "awsvpcConfiguration": {
            "securityGroups": _ECS_PUBLIC_SECURITY_GROUP
            if assign_public_ip
            else _ECS_SECURITY_GROUPS,
            "subnets": _ECS_PUBLIC_SUBNETS if assign_public_ip else _ECS_SUBNETS,
            "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED",
        }
    }

    task = EcsRunTaskOperator(
        task_id=task_id,
        dag=dag,
        region="eu-north-1",
        cluster=Variable.get(f"{stage}_ecs_cluster"),
        task_definition=task_definition,
        launch_type=launch_type.upper(),
        overrides={
            "containerOverrides": container_overrides,
            "cpu": str(cpu_units),
            "memory": str(memory_mb),
            # EphemeralStorage Overrides 'size' setting must be at least 21.
            "ephemeralStorage": {"sizeInGiB": ephemeralStorageGb},
        },
        awslogs_group=f"/ecs/{task_definition}",
        awslogs_stream_prefix=f"ecs/{task_definition}",
        # Must be set to custom big number because of
        # https://github.com/apache/airflow/issues/33711.
        waiter_max_attempts=1000000,
        # Represent how many last lines are returned in the container logs.
        number_logs_exception=200,
        # Assign enough time to make sure any task can finish but do not allow it to get stuck
        #  in a running loop in case of a glitch.
        execution_timeout=datetime.timedelta(hours=26),
        **kwargs,
    )
    return task
