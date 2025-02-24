"""
Import as:

import helpers.old.conda as holdcond
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import helpers.hdbg as hdbg
import helpers.hsystem as hsystem
import helpers.old.user_credentials as holuscre

_LOG = logging.getLogger(__name__)


def conda_system(cmd: str, *args: Any, **kwargs: Any) -> int:
    """
    When running a conda command we need to execute a script to configure
    conda. This script is typically executed in .bashrc but here we create a
    new bash shell every time to execute a command, so we need to re-initialize
    the shell before any conda command.

    :param cmd:
    :param args:
    :param kwargs:
    :return:
    """
    # TODO(gp): Pass conda_env_name as done in get_conda_list()
    path = holuscre.get_credentials()["conda_sh_path"]
    hdbg.dassert_path_exists(path)
    hdbg.dassert(os.path.isfile(path), "'%s' is not a file", path)
    cmd = f"source {path} && {cmd}"
    output: int = hsystem.system(cmd, *args, **kwargs)
    return output


def conda_system_to_string(
    cmd: str, *args: Any, **kwargs: Any
) -> Tuple[int, str]:
    path = holuscre.get_credentials()["conda_sh_path"]
    hdbg.dassert_path_exists(path)
    hdbg.dassert(os.path.isfile(path), "'%s' is not a file", path)
    cmd = f"source {path} && {cmd}"
    output: Tuple[int, str] = hsystem.system_to_string(cmd, *args, **kwargs)
    return output


def get_conda_envs_dirs() -> List[str]:
    """
    :return: list of the env dirs from conda
    """
    _, ret = conda_system_to_string(r"conda config --show envs_dirs --json")
    _LOG.debug("ret=%s", ret)
    envs = json.loads(ret)
    hdbg.dassert_in("envs_dirs", envs)
    envs = envs["envs_dirs"]
    hdbg.dassert_isinstance(envs, list)
    return list(envs)


def set_conda_env_root(conda_env_path: str) -> None:
    """
    Set conda env dirs so that it matches what specified in.

    > conda config --show envs_dirs --json
    {
      "envs_dirs": [
        "/Users/gp/.conda/envs",
      ]
    }

    > conda config --prepend envs_dirs /data/gp_wd/anaconda2/envs2
    """
    envs = get_conda_envs_dirs()
    #
    if not envs or envs[0] != conda_env_path:
        _LOG.warning(
            "%s is not the first env dir in %s", conda_env_path, str(envs)
        )
        # Reset the list of conda envs.
        _LOG.debug("Resetting envs_dir %s", str(envs))
        for env in envs:
            _LOG.debug("Deleting %s", env)
            cmd = f"conda config --remove envs_dirs {env}"
            # We don't abort because of a bug in conda not deleting the key
            # when asked for.
            # CondaKeyError: 'envs_dirs': u'/data/shared/anaconda2/envs' is not
            #   in the u'envs_dirs' key of the config file
            conda_system(cmd, abort_on_error=False)
        envs = get_conda_envs_dirs()
        _LOG.debug("Current envs: %s", str(envs))
        # Add the conda env.
        cmd = f"conda config --prepend envs_dirs {conda_env_path}"
        conda_system(cmd)
        # Check.
        envs = get_conda_envs_dirs()
        hdbg.dassert(
            envs or envs[0] != conda_env_path,
            msg=f"{conda_env_path} is not first env dir in {envs}",
        )
    else:
        _LOG.debug(
            "Nothing to do, since %s is already in %s", conda_env_path, envs
        )


def get_conda_info_envs() -> Tuple[dict, None]:
    """
    :return: (env_dict, active_env)
        - env_dict: map 'conda env name -> conda env path'
        - active_env: name of the active conda env
    """
    # > conda info --envs
    # # conda environments:
    # #
    # aws                      /Users/gp/.conda/envs/aws
    # bbg                      /Users/gp/.conda/envs/bbg
    # deeplearning             /Users/gp/.conda/envs/deeplearning
    # jupyter                  /Users/gp/.conda/envs/jupyter
    # test_conda               /Users/gp/.conda/envs/test_conda
    # TODO(gp): Use --json but we need to parse the json without any module.
    ret = conda_system_to_string(r"conda info --envs")[1]
    _LOG.debug("Parsing conda info\n%s", ret)
    ret = ret.split("\n")
    env_dict = {}
    active_env = None
    for line in ret:
        line = line.rstrip().lstrip()
        if line == "":
            continue
        if line.startswith("#"):
            continue
        vals = line.split()
        if len(vals) == 2:
            env_name, env_path = vals
            env_dict[env_name] = env_path
        elif len(vals) == 3:
            env_name, star, env_path = vals
            hdbg.dassert_eq(star, "*")
            env_dict[env_name] = env_path
        else:
            _LOG.debug("Can't parse line='%s'", line)
    return env_dict, active_env


def get_conda_list(conda_env_name: str) -> Dict[str, Dict[str, str]]:
    """
    :return: env_dict mapping package name to their info
        - env_dict: map 'conda env name -> conda env path'
        - active_env: name of the active conda env
    """
    # > conda list
    # # packages in environment at /Users/gp/.conda/envs/:
    # #
    # # Name                    Version                   Build  Channel
    # absl-py                   0.5.0                      py_0    conda-forge
    # agate                     1.6.0                      py_3    conda-forge
    # agate-dbf                 0.2.0                    py27_0    conda-forge
    # agate-excel               0.2.2                      py_0    conda-forge
    # TODO(gp): Use --json but we need to parse the json without any module.
    cmd = rf"(conda activate {conda_env_name} 2>&1) >/dev/null && conda list"
    ret = conda_system_to_string(cmd)[1]
    ret = ret.split("\n")
    env_dict = {}
    labels = {1: "version", 2: "build", 3: "channel"}
    for line in ret:
        line = line.rstrip().lstrip()
        _LOG.debug("line='%s'", line)
        if line == "":
            continue
        if line.startswith("#"):
            continue
        vals = line.split()
        env_dict[vals[0]] = {labels[k]: vals[k] for k in range(1, len(vals[:4]))}
    return env_dict


_CONDA_PATH = None


def get_conda_path() -> Optional[str]:
    global _CONDA_PATH
    if not _CONDA_PATH:
        rc, txt = conda_system_to_string("which conda", abort_on_error=False)
        if rc == 0:
            _CONDA_PATH = str(txt)
        else:
            _CONDA_PATH = "n/a"
    return _CONDA_PATH
