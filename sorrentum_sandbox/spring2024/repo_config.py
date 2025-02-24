"""
Contain info specific of `//cmamp` repo.
"""

# TODO(gp): Centralize all the common functions under hserver.py.

import functools
import logging
import os
from typing import Dict, List, Optional

import helpers.hserver as hserver

_LOG = logging.getLogger(__name__)


_WARNING = "\033[33mWARNING\033[0m"


def _print(msg: str) -> None:
    # _LOG.info(msg)
    if False:
        print(msg)


# We can't use `__file__` since this file is imported with an exec.
# _print("Importing //cmamp/repo_config.py")


# #############################################################################
# Repo info.
# #############################################################################


def get_name() -> str:
    return "//kaizen"


def get_repo_map() -> Dict[str, str]:
    """
    Return a mapping of short repo name -> long repo name.
    """
    repo_map: Dict[str, str] = {"kaizen": "kaizen-ai/kaizenflow"}
    return repo_map


def get_extra_amp_repo_sym_name() -> str:
    return "kaizen-ai/kaizenflow"


# TODO(gp): -> get_gihub_host_name
def get_host_name() -> str:
    return "github.com"


def get_invalid_words() -> List[str]:
    return []


def get_docker_base_image_name() -> str:
    """
    Return a base name for docker image.
    """
    base_image_name = "cmamp"
    return base_image_name


# #############################################################################


# //cmamp runs on:
# - MacOS
#   - Supports Docker privileged mode
#   - The same user and group is used inside the container
#   - Root can also be used
# - Linux (dev server, GitHub CI)
#   - Supports Docker privileged mode
#   - The same user and group is used inside the container
# - Linux (spm-dev4)
#   - Doesn't support Docker privileged mode
#   - A different user and group is used inside the container


def _raise_invalid_host(only_warning: bool) -> None:
    host_os_name = os.uname()[0]
    am_host_os_name = os.environ.get("AM_HOST_OS_NAME", None)
    msg = f"Don't recognize host: host_os_name={host_os_name}, am_host_os_name={am_host_os_name}"
    # TODO(Grisha): unclear if it is a difference between `cmamp` and `kaizenflow`.
    if only_warning:
        _LOG.warning(msg)
    else:
        raise ValueError(msg)


def enable_privileged_mode() -> bool:
    """
    Return whether an host supports privileged mode for its containers.
    """
    ret = False
    if get_name() in ("//dev_tools",):
        ret = False
    else:
        # Keep this in alphabetical order.
        if hserver.is_cmamp_prod():
            ret = False
        elif hserver.is_dev4() or hserver.is_ig_prod():
            ret = False
        elif hserver.is_dev_ck():
            ret = True
        elif hserver.is_inside_ci():
            ret = True
        elif hserver.is_mac(version="Catalina"):
            # Docker for macOS Catalina supports dind.
            ret = True
        elif hserver.is_mac(version="Monterey") or hserver.is_mac(
            version="Ventura"
        ):
            # Docker for macOS Monterey doesn't seem to support dind.
            ret = False
        else:
            ret = False
            only_warning = True
            _raise_invalid_host(only_warning)
    return ret


def has_docker_sudo() -> bool:
    """
    Return whether commands should be run with sudo or not.
    """
    ret = False
    # Keep this in alphabetical order.
    if hserver.is_cmamp_prod():
        ret = False
    elif hserver.is_dev4() or hserver.is_ig_prod():
        ret = False
    elif hserver.is_dev_ck():
        ret = True
    elif hserver.is_inside_ci():
        ret = False
    elif hserver.is_mac():
        # macOS runs Docker with sudo by default.
        ret = True
    else:
        ret = False
        only_warning = True
        _raise_invalid_host(only_warning)
    return ret


def _is_mac_version_with_sibling_containers() -> bool:
    return hserver.is_mac(version="Monterey") or hserver.is_mac(version="Ventura")


# TODO(gp): -> has_docker_privileged_mode
@functools.lru_cache()
def has_dind_support() -> bool:
    """
    Return whether the current container supports privileged mode.

    This is need to use Docker-in-Docker.
    """
    _print("is_inside_docker()=%s" % hserver.is_inside_docker())
    if not hserver.is_inside_docker():
        # Outside Docker there is no privileged mode.
        _print("-> ret = False")
        return False
    # TODO(gp): Not sure this is really needed since we do this check
    #  after enable_privileged_mode controls if we have dind or not.
    if _is_mac_version_with_sibling_containers():
        return False
    # TODO(gp): This part is not multi-process friendly. When multiple
    #  processes try to run this code they interfere. A solution is to run `ip
    #  link` in the entrypoint and create a `has_docker_privileged_mode` file
    #  which contains the value.
    #  We rely on the approach from https://stackoverflow.com/questions/32144575
    #  to check if there is support for privileged mode.
    #  Sometimes there is some state left, so we need to clean it up.
    cmd = "ip link delete dummy0 >/dev/null 2>&1"
    # TODO(gp): use `has_docker_sudo`.
    if hserver.is_mac() or hserver.is_dev_ck():
        cmd = f"sudo {cmd}"
    rc = os.system(cmd)
    _print("cmd=%s -> rc=%s" % (cmd, rc))
    #
    cmd = "ip link add dummy0 type dummy >/dev/null 2>&1"
    if hserver.is_mac() or hserver.is_dev_ck():
        cmd = f"sudo {cmd}"
    rc = os.system(cmd)
    _print("cmd=%s -> rc=%s" % (cmd, rc))
    has_dind = rc == 0
    # Clean up, after the fact.
    cmd = "ip link delete dummy0 >/dev/null 2>&1"
    if hserver.is_mac() or hserver.is_dev_ck():
        cmd = f"sudo {cmd}"
    rc = os.system(cmd)
    _print("cmd=%s -> rc=%s" % (cmd, rc))
    # dind is supported on both Mac and GH Actions.
    check_repo = os.environ.get("AM_REPO_CONFIG_CHECK", "True") != "False"
    if check_repo:
        if hserver.is_inside_ci():
            # Docker-in-docker is needed for GH actions. For all other builds is optional.
            assert has_dind, (
                f"Expected privileged mode: has_dind={has_dind}\n"
                + hserver.setup_to_str()
            )
        else:
            only_warning = True
            _raise_invalid_host(only_warning)
            return False
    else:
        am_repo_config = os.environ.get("AM_REPO_CONFIG_CHECK", "True")
        print(
            _WARNING
            + ": Skip checking since AM_REPO_CONFIG_CHECK="
            + f"'{am_repo_config}'"
        )
    return has_dind


def use_docker_sibling_containers() -> bool:
    """
    Return whether to use Docker sibling containers.

    Using sibling containers requires that all Docker containers in the
    same network so that they can communicate with each other.
    """
    val = hserver.is_dev4() or _is_mac_version_with_sibling_containers()
    return val


def use_main_network() -> bool:
    # TODO(gp): Replace this.
    return use_docker_sibling_containers()


def get_shared_data_dirs() -> Optional[Dict[str, str]]:
    """
    Get path of dir storing data shared between different users on the host and
    Docker.

    E.g., one can mount a central dir `/data/shared`, shared by multiple
    users, on a dir `/shared_data` in Docker.
    """
    # TODO(gp): Keep this in alphabetical order.
    shared_data_dirs: Optional[Dict[str, str]] = None
    if hserver.is_dev4():
        shared_data_dirs = {
            "/local/home/share/cache": "/cache",
            "/local/home/share/data": "/data",
        }
    elif hserver.is_dev_ck():
        shared_data_dirs = {"/data/shared": "/shared_data"}
    elif hserver.is_mac() or hserver.is_inside_ci() or hserver.is_cmamp_prod():
        shared_data_dirs = None
    else:
        shared_data_dirs = None
        only_warning = True
        _raise_invalid_host(only_warning)
    return shared_data_dirs


def use_docker_network_mode_host() -> bool:
    # TODO(gp): Not sure this is needed any more, since we typically run in bridge
    # mode.
    ret = hserver.is_mac() or hserver.is_dev_ck()
    ret = False
    if ret:
        assert use_docker_sibling_containers()
    return ret


def use_docker_db_container_name_to_connect() -> bool:
    """
    Connect to containers running DBs just using the container name, instead of
    using port and localhost / hostname.
    """
    if _is_mac_version_with_sibling_containers():
        # New Macs don't seem to see containers unless we connect with them
        # directly with their name.
        ret = True
    else:
        ret = False
    if ret:
        # This implies that we are using Docker sibling containers.
        assert use_docker_sibling_containers()
    return ret


def run_docker_as_root() -> bool:
    """
    Return whether Docker should be run with root user.

    I.e., adding `--user $(id -u):$(id -g)` to docker compose or not.
    """
    ret = None
    # Keep this in alphabetical order.
    if hserver.is_cmamp_prod():
        ret = False
    elif hserver.is_dev4() or hserver.is_ig_prod():
        # //lime runs on a system with Docker remap which assumes we don't
        # specify user credentials.
        ret = True
    elif hserver.is_dev_ck():
        # On dev1 / dev2 we run as users specifying the user / group id as
        # outside.
        ret = False
    elif hserver.is_inside_ci():
        # When running as user in GH action we get an error:
        # ```
        # /home/.config/gh/config.yml: permission denied
        # ```
        # see https://github.com/alphamatic/amp/issues/1864
        # So we run as root in GH actions.
        ret = True
    elif hserver.is_mac():
        ret = False
    else:
        ret = False
        only_warning = True
        _raise_invalid_host(only_warning)
    return ret


def get_docker_user() -> str:
    """
    Return the user that runs Docker, if any.
    """
    if hserver.is_dev4():
        val = "spm-sasm"
    else:
        val = ""
    return val


def get_unit_test_bucket_path() -> str:
    """
    Return the path to the unit test bucket.
    """
    unit_test_bucket = "cryptokaizen-unit-test"
    # We do not use `os.path.join` since it converts `s3://` to `s3:/`.
    unit_test_bucket_path = "s3://" + unit_test_bucket
    return unit_test_bucket_path


def get_html_bucket_path() -> str:
    """
    Return the path to the bucket where published HTMLs are stored.
    """
    html_bucket = "cryptokaizen-html"
    # We do not use `os.path.join` since it converts `s3://` to `s3:/`.
    html_bucket_path = "s3://" + html_bucket
    return html_bucket_path


def get_html_dir_to_url_mapping() -> Dict[str, str]:
    """
    Return a mapping between directories mapped on URLs.

    This is used when we have web servers serving files from specific
    directories.
    """
    dir_to_url = {"s3://cryptokaizen-html": "http://172.30.2.44"}
    return dir_to_url


def get_docker_shared_group() -> str:
    """
    Return the group of the user running Docker, if any.
    """
    if hserver.is_dev4():
        val = "sasm-fileshare"
    else:
        val = ""
    return val


def skip_submodules_test() -> bool:
    """
    Return whether the tests in the submodules should be skipped.

    E.g. while running `i run_fast_tests`.
    """
    # TODO(gp): Why do we want to skip running tests?
    if get_name() in ("//dev_tools",):
        # Skip running `amp` tests from `dev_tools`.
        return True
    return False


# #############################################################################

# Copied from hprint to avoid import cycles.


# TODO(gp): It should use *.
def indent(txt: str, num_spaces: int = 2) -> str:
    """
    Add `num_spaces` spaces before each line of the passed string.
    """
    spaces = " " * num_spaces
    txt_out = []
    for curr_line in txt.split("\n"):
        if curr_line.lstrip().rstrip() == "":
            # Do not prepend any space to a line with only white characters.
            txt_out.append("")
            continue
        txt_out.append(spaces + curr_line)
    res = "\n".join(txt_out)
    return res


# End copy.


# This function can't be in `helpers.hserver` since it creates circular import
# and `helpers.hserver` should not depend on anything.
def is_CK_S3_available() -> bool:
    val = True
    if hserver.is_inside_ci():
        repo_name = get_name()
        if repo_name in ("//amp", "//dev_tools"):
            # No CK bucket.
            val = False
        # TODO(gp): We might want to enable CK tests also on lemonade.
        if repo_name in ("//lemonade",):
            # No CK bucket.
            val = False
    elif hserver.is_dev4():
        # CK bucket is not available on dev4.
        val = False
    _LOG.debug("val=%s", val)
    return val


def config_func_to_str() -> str:
    """
    Print the value of all the config functions.
    """
    ret: List[str] = []
    #
    function_names = [
        "enable_privileged_mode",
        "get_docker_base_image_name",
        "get_docker_user",
        "get_docker_shared_group",
        # "get_extra_amp_repo_sym_name",
        "get_host_name",
        "get_html_dir_to_url_mapping",
        "get_invalid_words",
        "get_name",
        "get_repo_map",
        "get_shared_data_dirs",
        "has_dind_support",
        "has_docker_sudo",
        "is_CK_S3_available",
        "run_docker_as_root",
        "skip_submodules_test",
        "use_docker_sibling_containers",
        "use_docker_network_mode_host",
        "use_docker_db_container_name_to_connect",
    ]
    for func_name in sorted(function_names):
        try:
            _LOG.debug("func_name=%s", func_name)
            func_value = eval(f"{func_name}()")
        except NameError as e:
            func_value = "*undef*"
            _ = e
            # raise e
        msg = f"{func_name}='{func_value}'"
        ret.append(msg)
        # _print(msg)
    # Package.
    ret: str = "# repo_config.config\n" + indent("\n".join(ret))
    # Add the signature from hserver.
    ret += "\n" + indent(hserver.config_func_to_str())
    return ret


if False:
    print(config_func_to_str())
    # assert 0
