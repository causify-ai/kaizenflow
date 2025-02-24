#!/usr/bin/env python

r"""
Create new test ECS task definition for a particular issue.

For example:

If you are going to develop a test DAG for issue number #7960,
task definitions "cmamp-test-7960" are created in all actively
used regions.

Use as:

> ./im_v2/aws/aws_create_test_task_definition.py --issue_id 7960
"""

import argparse
import copy
import json
import logging
from typing import Dict

import helpers.haws as haws
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

_AWS_PROFILE = "ck"
_REGIONS = ["eu-north-1", "ap-northeast-1"]
_TASK_DEFINITION_PREFIX = "cmamp-test"
_TASK_DEFINITION_JSON_TEMPLATE_PATH = (
    "./im_v2/aws/ecs_test_task_definition_template.json"
)
_TASK_DEFINITION_LOG_OPTIONS_TEMPLATE = {
    "awslogs-create-group": "true",
    "awslogs-group": "/ecs/{}",
    "awslogs-region": "{}",
    "awslogs-stream-prefix": "ecs",
}

# TODO(Juraj): parametrize account number.
_IMAGE_URL_TEMPLATE = (
    "623860924167.dkr.ecr.{}.amazonaws.com/cmamp:prod-placeholder"
)

_EFS_CONFIG = {
    "eu-north-1": {
        "volumes": [
            {
                "name": "efs",
                "efsVolumeConfiguration": {
                    "fileSystemId": "fs-0341af9c333cc9e3b",
                    "rootDirectory": "/",
                    "transitEncryption": "ENABLED",
                    "authorizationConfig": {
                        "accessPointId": "fsap-0cccf2da06edc0872",
                        "iam": "DISABLED",
                    },
                },
            }
        ],
        "mountPoints": [
            {"sourceVolume": "efs", "containerPath": "/data/shared/ecs"}
        ],
    },
    "ap-northeast-1": {
        "volumes": [
            {
                "name": "efs",
                "efsVolumeConfiguration": {
                    "fileSystemId": "fs-0a37fe19d8c3843f3",
                    "rootDirectory": "/",
                    "transitEncryption": "ENABLED",
                    "authorizationConfig": {
                        "accessPointId": "fsap-04759ab2a130965bb",
                        "iam": "DISABLED",
                    },
                },
            }
        ],
        "mountPoints": [
            {"sourceVolume": "efs", "containerPath": "/data/shared/ecs_tokyo"}
        ],
    },
}


def _set_task_definition_config(
    task_definition_config: Dict, task_definition_name: str, region: str
) -> Dict:
    """
    Update template of ECS task definition with concrete values:

    :return: full formed task definition config dictionary
    """
    # Replace placeholder values inside container definition
    # from the template with concrete values.
    # We use single container inside our task definition and
    # the convention is to set the same name as the task
    # definition itself
    task_definition_config["containerDefinitions"][0][
        "name"
    ] = task_definition_name

    # Set placeholder image URL.
    task_definition_config["containerDefinitions"][0][
        "image"
    ] = _IMAGE_URL_TEMPLATE.format(region)

    # Set log configuration options.
    log_config_opts = copy.deepcopy(_TASK_DEFINITION_LOG_OPTIONS_TEMPLATE)
    log_config_opts["awslogs-group"] = log_config_opts["awslogs-group"].format(
        task_definition_name
    )
    log_config_opts["awslogs-region"] = region
    task_definition_config["containerDefinitions"][0]["logConfiguration"][
        "options"
    ] = log_config_opts

    # Set environment variable "CK_AWS_DEFAULT_REGION".
    task_definition_config["containerDefinitions"][0]["environment"][1][
        "value"
    ] = region

    # Configure access to EFS
    task_definition_config["volumes"] = _EFS_CONFIG[region]["volumes"]
    task_definition_config["containerDefinitions"][0][
        "mountPoints"
    ] = _EFS_CONFIG[region]["mountPoints"]

    return task_definition_config


def _register_task_definition(task_definition_name: str, region: str) -> None:
    """
    Register a new ECS task definition.

    :param task_definition_name: The name of the new task definition.
    :param config_file: Path to the JSON file containing the task
        definition configuration.
    :param region: Optional AWS region. If not provided, the default
        region from the AWS profile will be used.
    """
    with open(_TASK_DEFINITION_JSON_TEMPLATE_PATH, "r") as f:
        task_definition_config = json.load(f)

    client = haws.get_ecs_client(_AWS_PROFILE, region=region)

    task_definition_config = _set_task_definition_config(
        task_definition_config, task_definition_name, region
    )

    client.register_task_definition(
        family=task_definition_name,
        taskRoleArn=task_definition_config.get("taskRoleArn", ""),
        executionRoleArn=task_definition_config["executionRoleArn"],
        networkMode=task_definition_config["networkMode"],
        containerDefinitions=task_definition_config["containerDefinitions"],
        volumes=task_definition_config.get("volumes", []),
        placementConstraints=task_definition_config.get(
            "placementConstraints", []
        ),
        requiresCompatibilities=task_definition_config["requiresCompatibilities"],
        cpu=task_definition_config["cpu"],
        memory=task_definition_config["memory"],
    )

    _LOG.info(
        "Registered new task definition: %s in region %s",
        task_definition_name,
        region,
    )


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--issue_id",
        type=int,
        required=True,
        help="Github issue ID (AKA issue number)",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)

    task_definition_name = f"{_TASK_DEFINITION_PREFIX}-{args.issue_id}"

    for region in _REGIONS:
        _register_task_definition(task_definition_name, region=region)


if __name__ == "__main__":
    _main(_parse())
