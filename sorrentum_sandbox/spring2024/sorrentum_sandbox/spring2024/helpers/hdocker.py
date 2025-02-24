"""
Import as:

import helpers.hdocker as hdocker
"""

import logging

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def container_rm(container_name: str) -> None:
    _LOG.debug(hprint.to_str("container_name"))
    # Find the container ID from the name.
    # Docker filter refers to container names using a leading `/`.
    cmd = f"docker container ls --filter name=/{container_name} -aq"
    _, container_id = hsystem.system_to_one_line(cmd)
    container_id = container_id.rstrip("\n")
    hdbg.dassert_ne(container_id, "")
    # Delete the container.
    _LOG.debug(hprint.to_str("container_id"))
    cmd = f"docker container rm --force {container_id}"
    hsystem.system(cmd)
    _LOG.debug("docker container '%s' deleted", container_name)


def volume_rm(volume_name: str) -> None:
    _LOG.debug(hprint.to_str("volume_name"))
    cmd = f"docker volume rm {volume_name}"
    hsystem.system(cmd)
    _LOG.debug("docker volume '%s' deleted", volume_name)


def replace_shared_root_path(path: str) -> str:
    """
    Replace root path of the shared directory based on the mapping.

    :param path: path to replace, e.g., `/data/shared`
    :return: replaced shared data dir root path, e.g., `/shared_data`
    """
    # Inside ECS we keep the original shared data path and replace it only when
    # running inside Docker on the dev server.
    if hserver.is_inside_docker() and not hserver.is_inside_ecs_container():
        shared_data_dirs = henv.execute_repo_config_code("get_shared_data_dirs()")
        for shared_dir, docker_shared_dir in shared_data_dirs.items():
            path = path.replace(shared_dir, docker_shared_dir)
            _LOG.debug(
                "Running inside Docker on the dev server, thus replacing %s "
                "with %s", shared_dir, docker_shared_dir,
            )
    else:
        _LOG.debug("No replacement found, returning path as-is: %s", path)
    return path


# import argparse
# import docker
# def get_volumes(
#         name: str,  # pylint: disable=unused-argument
# ) -> List[Dict[str, str]]:
#     client = docker.from_env()
#     container = client.containers.get("postgres_service")
#     output: List[Dict[str, str]] = container.attrs["Mounts"]
#     return output
#
#
# def get_source_from(name: str) -> str:
#     s = ""
#     for i in get_volumes(name):
#         s += i["Source"] + "\n"
#     return s


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--get_volumes", required=False, type=str, action="store")
#     args = parser.parse_args()
#     # _main(args)
#     if args.get_volumes:
#         print((get_source_from(args.get_volumes)))
