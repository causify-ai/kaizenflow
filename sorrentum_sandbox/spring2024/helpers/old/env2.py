"""
Import as:

import helpers.old.env2 as holdenv2
"""

import logging
import os
from typing import Tuple

import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.old.conda as holdcond

_LOG = logging.getLogger(__name__)


# #############################################################################


def get_system_info(add_frame: bool) -> str:
    msg = ""
    if add_frame:
        msg += hprint.frame("System info") + "\n"
    msg += f"user name={hsystem.get_user_name()}\n"
    msg += f"server name={hsystem.get_server_name()}\n"
    msg += f"os name={hsystem.get_os_name()}\n"
    msg += f"conda path={holdcond.get_conda_path()}\n"
    msg += f"conda env root={str(holdcond.get_conda_envs_dirs())}\n"
    return msg


def get_package_summary(conda_env_name: str, add_frame: bool) -> str:
    msg = ""
    if add_frame:
        msg += hprint.frame("Package summary") + "\n"
    conda_list = holdcond.get_conda_list(conda_env_name)
    msg = ""
    for package in ["pandas", "numpy", "scipy", "arrow-cpp"]:
        ver = conda_list[package]["version"] if package in conda_list else "None"
        line = f"{package}: {ver}"
        msg += line + "\n"
    return msg


def get_conda_export_list(conda_env_name: str, add_frame: bool) -> str:
    msg = ""
    if add_frame:
        msg += hprint.frame("Package summary") + "\n"
    cmd = rf"(conda activate {conda_env_name} 2>&1 >/dev/null) && conda list --export"
    _, msg_tmp = holdcond.conda_system_to_string(cmd)
    msg += msg_tmp
    return msg


def save_env_file(conda_env_name: str, dir_name: str) -> Tuple[str, str]:
    msg = ""
    msg += get_system_info(add_frame=True)
    msg += get_package_summary(conda_env_name, add_frame=True)
    msg += get_conda_export_list(conda_env_name, add_frame=True)
    # Save results.
    if dir_name is not None:
        file_name = (
            f"{conda_env_name}.{hsystem.get_user_name()}.{hsystem.get_os_name()}."
            f"{hsystem.get_server_name()}.txt"
        )
        dst_file = os.path.join(dir_name, file_name)
        dst_file = os.path.abspath(dst_file)
        hio.create_enclosing_dir(dst_file, incremental=True)
        _LOG.info("Saving conda env signature to '%s'", dst_file)
        hio.to_file(dst_file, msg)
    else:
        dst_file = None
    return msg, dst_file
