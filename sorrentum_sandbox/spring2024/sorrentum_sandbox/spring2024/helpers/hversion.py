"""
Import as:

import helpers.hversion as hversio
"""

# This code implements version control for code
# The code version is used in two circumstances:
# 1) when any code using `hdbg.py` (which is included everywhere) starts in
#    order to verify that the running code and the container in which the code
#    is running are compatible
# 2) when a container is built to know what version of the code was used to build
#    it

import functools
import logging
import os
import re
from typing import Optional, cast

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hserver as hserver
import helpers.hsystem as hsystem

# This module can depend only on:
# - Python standard modules
# - a few helpers as described in `helpers/dependencies.txt`

_LOG = logging.getLogger(__name__)


_INFO = "\033[36mINFO\033[0m"
_WARNING = "\033[33mWARNING\033[0m"
_ERROR = "\033[31mERROR\033[0m"
#
_VERSION_RE = r"\d+\.\d+\.\d+"


def check_version(container_dir_name: str) -> None:
    """
    Check that the code and container code have compatible version, otherwise
    raises `RuntimeError`.

    :param container_dir_name: container directory relative to the root directory
    """
    # TODO(gp): -> AM_SKIP_VERSION_CHECK.
    if "SKIP_VERSION_CHECK" in os.environ:
        # Skip the check altogether.
        return
    # Get code version.
    code_version = get_changelog_version(container_dir_name)
    container_version = _get_container_version()
    # Check version, if possible.
    if container_version is None:
        # No need to check.
        return
    code_version = cast(str, code_version)
    _check_version(code_version, container_version)


# Copied from helpers.hgit to avoid circular dependencies.


@functools.lru_cache()
def _is_inside_submodule(git_dir: str = ".") -> bool:
    """
    Return whether a dir is inside a Git submodule or a Git supermodule.

    We determine this checking if the current Git repo is included
    inside another Git repo.
    """
    cmd = []
    # - Find the git root of the current directory
    # - Check if the dir one level up is a valid Git repo
    # Go to the dir.
    cmd.append(f"cd {git_dir}")
    # > cd im/
    # > git rev-parse --show-toplevel
    # /Users/saggese/src/.../amp
    cmd.append('cd "$(git rev-parse --show-toplevel)/.."')
    # > git rev-parse --is-inside-work-tree
    # true
    cmd.append("(git rev-parse --is-inside-work-tree | grep -q true)")
    cmd_as_str = " && ".join(cmd)
    rc = hsystem.system(cmd_as_str, abort_on_error=False)
    ret: bool = rc == 0
    return ret


@functools.lru_cache()
def _get_client_root(super_module: bool) -> str:
    """
    Return the full path of the root of the Git client.

    E.g., `/Users/saggese/src/.../amp`.

    :param super_module: if True use the root of the Git super_module,
        if we are in a submodule. Otherwise use the Git sub_module root
    """
    if super_module and _is_inside_submodule():
        # https://stackoverflow.com/questions/957928
        # > cd /Users/saggese/src/.../amp
        # > git rev-parse --show-superproject-working-tree
        # /Users/saggese/src/...
        cmd = "git rev-parse --show-superproject-working-tree"
    else:
        # > git rev-parse --show-toplevel
        # /Users/saggese/src/.../amp
        cmd = "git rev-parse --show-toplevel"
    # TODO(gp): Use system_to_one_line().
    _, out = hsystem.system_to_string(cmd)
    out = out.rstrip("\n")
    hdbg.dassert_eq(len(out.split("\n")), 1, msg=f"Invalid out='{out}'")
    client_root: str = os.path.realpath(out)
    return client_root


# End copy.


def get_changelog_version(container_dir_name: str) -> Optional[str]:
    """
    Return latest version from changelog.txt file.

    :param container_dir_name: container directory relative to the root directory
    """
    version: Optional[str] = None
    supermodule = True
    root_dir = _get_client_root(supermodule)
    # Note: for `amp` as submodule one should pass `container_dir_name` relative
    # to the root, e.g., `amp/optimizer` and not just `optimizer`.
    hdbg.dassert_ne(container_dir_name, "")
    changelog_file = os.path.join(root_dir, container_dir_name, "changelog.txt")
    hdbg.dassert_file_exists(changelog_file)
    changelog = hio.from_file(changelog_file)
    match = re.search(_VERSION_RE, changelog)
    if match:
        version = match.group()
    return version


def _get_container_version() -> Optional[str]:
    """
    Return the container version.

    :return: container code version from the env var
    """
    container_version: Optional[str] = None
    if hserver.is_inside_docker():
        env_var = "AM_CONTAINER_VERSION"
        if env_var not in os.environ:
            # This can happen when GH Actions pull the image using invoke
            # inside their container (but not inside ours), thus there is no
            # AM_CONTAINER_VERSION.
            print(
                _WARNING
                + f": The env var {env_var} should be defined when running inside a"
                " container"
            )
        else:
            # We are running inside a container.
            # Keep the code and the container in sync by versioning both and
            # requiring to be the same.
            container_version = os.environ["AM_CONTAINER_VERSION"]
    return container_version


def _check_version(code_version: str, container_version: str) -> bool:
    """
    Check whether the code version and the container version are the same.

    :param code_version: code version from the changelog
    :param container_version: container code version from the env var
    :return: whether the versions are the same or not
    """
    # Since the code version from the changelog is extracted with the
    # `_VERSION_RE` regex, we apply the same regex to the container version
    # to keep the representations comparable.
    match = re.search(_VERSION_RE, container_version)
    hdbg.dassert(
        match,
        (
            "Invalid format of the container code version '%s'; "
            "it should contain a number like '1.0.0'"
        ),
        container_version,
    )
    container_version = match.group()  # type: ignore
    # Check if the versions are the same.
    is_ok = container_version == code_version
    if not is_ok:
        msg = f"""
-----------------------------------------------------------------------------
This code is not in sync with the container:
code_version='{code_version}' != container_version='{container_version}'
-----------------------------------------------------------------------------
You need to:
- merge origin/master into your branch with `invoke git_merge_master`
- pull the latest container with `invoke docker_pull`
"""
        msg = msg.rstrip().lstrip()
        msg = f"\033[31m{msg}\033[0m"
        print(msg)
        # raise RuntimeError(msg)
    return is_ok
