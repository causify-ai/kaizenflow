"""
Tasks related to `oms` project.

Import as:

import oms.oms_lib_tasks as oomlitas
"""

import logging
import os
from typing import Optional

from invoke import task

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


# TODO(gp): This was branched from im/im_lib_tasks.py. We should factor out the
#  common part CMTask #496.


def get_db_env_path(stage: str, *, idx: Optional[int] = None) -> str:
    """
    Get path to db env file that contains db connection parameters.

    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param idx: index used to make the generated file unique
    :return: path to db env file
    """
    hdbg.dassert_in(stage, "local dev prod".split())
    # Get `env` files dir.
    env_dir = "oms/devops/env"
    # Get the file name depending on the stage.
    env_file_name = f"{stage}.oms_db_config.env"
    if idx is not None:
        env_file_name = hio.add_suffix_to_filename(env_file_name, idx)
    # Get file path.
    amp_path = hgit.get_amp_abs_path()
    env_file_path = os.path.join(amp_path, env_dir, env_file_name)
    # We use idx when we want to generate a Docker env file on the fly. So we
    # can't enforce that the file already exists.
    if idx is None:
        hdbg.dassert_file_exists(env_file_path)
    return env_file_path


# TODO(gp): This should be used also from the unit tests?
def _get_docker_compose_path() -> str:
    """
    Return the absolute path to the docker-compose file for this component.

    E.g., `im/devops/compose/docker-compose.yml`.
    """
    # Get `amp` path.
    amp_path = hgit.get_amp_abs_path()
    # Get `docker-compose` file path.
    # TODO(gp): Factor out this dir.
    docker_compose_dir = "oms/devops/compose"
    compose_file_name = "docker-compose.yml"
    docker_compose_path = os.path.join(
        amp_path, docker_compose_dir, compose_file_name
    )
    # Get absolute version of a file path.
    docker_compose_abs_path = os.path.abspath(docker_compose_path)
    # Verify that the file exists.
    hdbg.dassert_file_exists(docker_compose_abs_path)
    return docker_compose_abs_path


# #############################################################################


def _get_docker_run_cmd(stage: str, docker_cmd: str) -> str:
    """
    Construct the `docker-compose' command to run a script inside this
    container Docker component.

    E.g, to run the `.../devops/set_schema_im_db.py`:
    ```
    docker-compose \
        --file devops/compose/docker-compose.yml \
        --env-file devops/env/local.oms_db_config.env \
        run --rm oms_postgres \
        .../devops/set_schema_im_db.py
    ```

    :param docker_cmd: command to execute inside docker
    """
    cmd = ["docker-compose"]
    # Add `docker-compose` file path.
    docker_compose_file_path = _get_docker_compose_path()
    cmd.append(f"--file {docker_compose_file_path}")
    # Add `env file` path.
    env_file = get_db_env_path(stage)
    cmd.append(f"--env-file {env_file}")
    # Add `run`.
    service_name = "oms_postgres"
    cmd.append(f"run --rm {service_name}")
    cmd.append(docker_cmd)
    # Convert the list to a multiline command.
    multiline_docker_cmd = hlitauti.to_multi_line_cmd(cmd)
    return multiline_docker_cmd  # type: ignore[no-any-return]


@task
def oms_docker_cmd(ctx, stage, cmd):  # type: ignore
    """
    Execute the command `cmd` inside a container attached to the `im app`.

    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param cmd: command to execute
    """
    hdbg.dassert_ne(cmd, "")
    # Get docker cmd.
    docker_cmd = _get_docker_run_cmd(stage, cmd)
    # Execute the command.
    hlitauti.run(ctx, docker_cmd, pty=True)


# #############################################################################


def _get_docker_up_cmd(stage: str, detach: bool) -> str:
    """
    Construct the command to bring up the `oms` service.

    E.g.,
    ```
    docker-compose \
        --file devops/compose/docker-compose.yml \
        --env-file devops/env/local.oms_db_config.env \
        up \
        oms_postgres
    ```

    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param detach: run containers in the background
    """
    cmd = ["docker-compose"]
    # Add `docker-compose` file path.
    docker_compose_file_path = _get_docker_compose_path()
    cmd.append(f"--file {docker_compose_file_path}")
    # Add `env file` path.
    env_file = get_db_env_path(stage)
    cmd.append(f"--env-file {env_file}")
    # Add `down` command.
    cmd.append("up")
    if detach:
        # Enable detached mode.
        cmd.append("-d")
    service = "oms_postgres"
    cmd.append(service)
    cmd = hlitauti.to_multi_line_cmd(cmd)
    return cmd  # type: ignore[no-any-return]


@task
def oms_docker_up(ctx, stage, detach=False):  # type: ignore
    """
    Start oms container with Postgres inside.

    :param ctx: `context` object
    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param detach: run containers in the background
    """
    # Get docker down command.
    docker_clean_up_cmd = _get_docker_up_cmd(stage, detach)
    # Execute the command.
    hlitauti.run(ctx, docker_clean_up_cmd, pty=True)


# #############################################################################


def _get_docker_down_cmd(stage: str, volumes_remove: bool) -> str:
    """
    Construct the command to shut down the `oms` service.

    E.g.,
    ```
    docker-compose \
        --file devops/compose/docker-compose.yml \
        --env-file devops/env/local.oms_db_config.env \
        down \
        -v
    ```

    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param volumes_remove: whether to remove attached volumes or not
    """
    cmd = ["docker-compose"]
    # Add `docker-compose` file path.
    docker_compose_file_path = _get_docker_compose_path()
    cmd.append(f"--file {docker_compose_file_path}")
    # Add `env file` path.
    env_file = get_db_env_path(stage)
    cmd.append(f"--env-file {env_file}")
    # Add `down` command.
    cmd.append("down")
    if volumes_remove:
        # Use the '-v' option to remove attached volumes.
        _LOG.warning(
            "Removing the attached volumes resetting the state of the DB"
        )
        cmd.append("-v")
    cmd = hlitauti.to_multi_line_cmd(cmd)
    return cmd  # type: ignore[no-any-return]


@task
def oms_docker_down(ctx, stage, volumes_remove=False):  # type: ignore
    """
    Bring down the `oms` service.

    By default volumes are not removed, to also remove volumes do
    `invoke im_docker_down -v`.

    :param stage: development stage, i.e. `local`, `dev` and `prod`
    :param volumes_remove: whether to remove attached volumes or not
    :param ctx: `context` object
    """
    # Get docker down command.
    cmd = _get_docker_down_cmd(stage, volumes_remove)
    # Execute the command.
    hlitauti.run(ctx, cmd, pty=True)
