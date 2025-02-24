"""
Identify on which server we are running.

Import as:

import helpers.hserver as hserver
"""

import logging
import os
from typing import List, Optional

# This module should depend only on:
# - Python standard modules
# See `helpers/dependencies.txt` for more details

_LOG = logging.getLogger(__name__)

_WARNING = "\033[33mWARNING\033[0m"


def _print(msg: str) -> None:
    _ = msg
    # _LOG.info(msg)
    if False:
        print(msg)


# #############################################################################
# Detect server.
# #############################################################################


def is_inside_ci() -> bool:
    """
    Return whether we are running inside the Continuous Integration flow.
    """
    if "CI" not in os.environ:
        ret = False
    else:
        ret = os.environ["CI"] != ""
    return ret


def is_inside_docker() -> bool:
    """
    Return whether we are inside a container or not.
    """
    # From https://stackoverflow.com/questions/23513045
    return os.path.exists("/.dockerenv")


# We can't rely only on the name of the host to infer where we are running,
# since inside Docker the name of the host is like `01a7e34a82a5`. Of course,
# there is no way to know anything about the host for security reason, so we
# pass this value from the external environment to the container, through env
# vars (e.g., `AM_HOST_NAME`, `AM_HOST_OS_NAME`).


def is_dev_ck() -> bool:
    # TODO(gp): Update to use dev1 values.
    # sysname='Darwin'
    # nodename='gpmac.lan'
    # release='19.6.0'
    # version='Darwin Kernel Version 19.6.0: Mon Aug 31 22:12:52 PDT 2020;
    #   root:xnu-6153.141.2~1/RELEASE_X86_64'
    # machine='x86_64'
    host_name = os.uname()[1]
    host_names = ("dev1", "dev2")
    am_host_name = os.environ.get("AM_HOST_NAME", "")
    _LOG.debug("host_name=%s am_host_name=%s", host_name, am_host_name)
    is_dev_ck_ = host_name in host_names or am_host_name in host_names
    return is_dev_ck_


def is_dev4() -> bool:
    """
    Return whether it's running on dev4.
    """
    host_name = os.uname()[1]
    am_host_name = os.environ.get("AM_HOST_NAME", None)
    dev4 = "cf-spm-dev4"
    _LOG.debug("host_name=%s am_host_name=%s", host_name, am_host_name)
    is_dev4_ = dev4 in (host_name, am_host_name)
    #
    if not is_dev4_:
        dev4 = "cf-spm-dev8"
        _LOG.debug("host_name=%s am_host_name=%s", host_name, am_host_name)
        is_dev4_ = dev4 in (host_name, am_host_name)
    return is_dev4_


def is_mac(*, version: Optional[str] = None) -> bool:
    """
    Return whether we are running on macOS and, optionally, on a specific
    version.

    :param version: check whether we are running on a certain macOS version (e.g.,
        `Catalina`, `Monterey`)
    """
    _LOG.debug("version=%s", version)
    host_os_name = os.uname()[0]
    _LOG.debug("os.uname()=%s", str(os.uname()))
    am_host_os_name = os.environ.get("AM_HOST_OS_NAME", None)
    _LOG.debug(
        "host_os_name=%s am_host_os_name=%s", host_os_name, am_host_os_name
    )
    is_mac_ = host_os_name == "Darwin" or am_host_os_name == "Darwin"
    if version is None:
        # The user didn't request a specific version, so we return whether we
        # are running on a Mac or not.
        _LOG.debug("is_mac_=%s", is_mac_)
        return is_mac_
    else:
        # The user specified a version: if we are not running on a Mac then we
        # return False, since we don't even have to check the macOS version.
        if not is_mac_:
            _LOG.debug("is_mac_=%s", is_mac_)
            return False
    # Check the macOS version we are running.
    if version == "Catalina":
        # Darwin gpmac.fios-router.home 19.6.0 Darwin Kernel Version 19.6.0:
        # Mon Aug 31 22:12:52 PDT 2020; root:xnu-6153.141.2~1/RELEASE_X86_64 x86_64
        macos_tag = "19.6"
    elif version == "Monterey":
        # Darwin alpha.local 21.5.0 Darwin Kernel Version 21.5.0:
        # Tue Apr 26 21:08:37 PDT 2022;
        #   root:xnu-8020.121.3~4/RELEASE_ARM64_T6000 arm64```
        macos_tag = "21."
    elif version == "Ventura":
        # Darwin alpha.local 21.5.0 Darwin Kernel Version 21.5.0:
        # Tue Apr 26 21:08:37 PDT 2022;
        #   root:xnu-8020.121.3~4/RELEASE_ARM64_T6000 arm64```
        macos_tag = "22."
    else:
        raise ValueError(f"Invalid version='{version}'")
    _LOG.debug("macos_tag=%s", macos_tag)
    host_os_version = os.uname()[2]
    # 'Darwin Kernel Version 19.6.0: Mon Aug 31 22:12:52 PDT 2020;
    #   root:xnu-6153.141.2~1/RELEASE_X86_64'
    am_host_os_version = os.environ.get("AM_HOST_VERSION", "")
    _LOG.debug(
        "host_os_version=%s am_host_os_version=%s",
        host_os_version,
        am_host_os_version,
    )
    is_mac_ = macos_tag in host_os_version or macos_tag in am_host_os_version
    _LOG.debug("is_mac_=%s", is_mac_)
    return is_mac_


def is_cmamp_prod() -> bool:
    """
    Detect whether we are running in a CK production container.

    This env var is set inside `devops/docker_build/prod.Dockerfile`.
    """
    return bool(os.environ.get("CK_IN_PROD_CMAMP_CONTAINER", False))


def is_ig_prod() -> bool:
    """
    Detect whether we are running in an IG production container.

    This env var is set inside `//lime/devops_cf/setenv.sh`
    """
    # CF sets up `DOCKER_BUILD` so we can use it to determine if we are inside
    # a CF container or not.
    # print("os.environ\n", str(os.environ))
    return bool(os.environ.get("DOCKER_BUILD", False))


# TODO(Grisha): consider adding to `setup_to_str()`.
def is_inside_ecs_container() -> bool:
    """
    Detect whether we are running in an ECS container.

    When deploying jobs via ECS the container obtains credentials based
    on passed task role specified in the ECS task-definition, refer to:
    https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html.
    """
    ret = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI" in os.environ
    return ret


def setup_to_str() -> str:
    txt = []
    #
    is_cmamp_prod_ = is_cmamp_prod()
    txt.append(f"is_cmamp_prod={is_cmamp_prod_}")
    #
    is_dev4_ = is_dev4()
    txt.append(f"is_dev4={is_dev4_}")
    #
    is_dev_ck_ = is_dev_ck()
    txt.append(f"is_dev_ck={is_dev_ck_}")
    #
    is_ig_prod_ = is_ig_prod()
    txt.append(f"is_ig_prod={is_ig_prod_}")
    #
    is_inside_ci_ = is_inside_ci()
    txt.append(f"is_inside_ci={is_inside_ci_}")
    #
    is_mac_ = is_mac()
    txt.append(f"is_mac={is_mac_}")
    #
    txt = "\n".join(txt)
    return txt


def _dassert_setup_consistency() -> None:
    """
    Check that one and only one set up config should be true.
    """
    is_cmamp_prod_ = is_cmamp_prod()
    is_dev4_ = is_dev4()
    is_dev_ck_ = is_dev_ck()
    is_ig_prod_ = is_ig_prod()
    is_inside_ci_ = is_inside_ci()
    is_mac_ = is_mac()
    # One and only one set-up should be true.
    sum_ = sum(
        [
            is_dev4_,
            is_dev_ck_,
            is_inside_ci_,
            is_mac_,
            is_cmamp_prod_,
            is_ig_prod_,
        ]
    )
    if sum_ != 1:
        msg = "One and only one set-up config should be true:\n" + setup_to_str()
        # TODO(gp): Unclear if this is a difference between Kaizenflow and cmamp.
        _LOG.warning(msg)
        # raise ValueError(msg)


# If the env var is not defined then we want to check. The only reason to skip
# it's if the env var is defined and equal to False.
check_repo = os.environ.get("AM_REPO_CONFIG_CHECK", "True") != "False"
_is_called = False
if check_repo:
    if not _is_called:
        _dassert_setup_consistency()
        _is_called = True
else:
    _LOG.warning("Skipping repo check in %s", __file__)


# #############################################################################
# S3 buckets.
# #############################################################################


def is_AM_S3_available() -> bool:
    # AM bucket is always available.
    val = True
    _LOG.debug("val=%s", val)
    return val


def get_host_user_name() -> Optional[str]:
    return os.environ.get("AM_HOST_USER_NAME", None)


# #############################################################################
# Functions.
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


def config_func_to_str() -> str:
    """
    Print the value of all the config functions.
    """
    ret: List[str] = []
    #
    function_names = [
        "is_AM_S3_available()",
        "is_dev_ck()",
        "is_dev4()",
        "is_inside_ci()",
        "is_inside_docker()",
        "is_mac(version='Catalina')",
        "is_mac(version='Monterey')",
        "is_mac(version='Ventura')",
    ]
    for func_name in sorted(function_names):
        try:
            _LOG.debug("func_name=%s", func_name)
            func_value = eval(func_name)
        except NameError:
            func_value = "*undef*"
        msg = f"{func_name}='{func_value}'"
        ret.append(msg)
        # _print(msg)
    # Package.
    ret: str = "# hserver.config\n" + indent("\n".join(ret))
    return ret
