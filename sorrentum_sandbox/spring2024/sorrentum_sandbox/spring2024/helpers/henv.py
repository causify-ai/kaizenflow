"""
Import as:

import helpers.henv as henv
"""

import functools
import logging
import os
from typing import Any, Dict, List, Tuple, Union

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import helpers.hversion as hversio

# This module can depend only on:
# - Python standard modules
# - a few helpers as described in `helpers/dependencies.txt`


_LOG = logging.getLogger(__name__)


# #############################################################################


_WARNING = "\033[33mWARNING\033[0m"


def has_module(module: str) -> bool:
    """
    Return whether a Python module can be imported or not.
    """
    if module == "gluonts" and hserver.is_mac():
        # Gluonts and mxnet modules are not properly supported on the ARM
        # architecture yet, see CmTask4886 for details.
        return False
    code = f"""
try:
    import {module}
    has_module_ = True
except ImportError as e:
    _LOG.warning("%s: %s", _WARNING, str(e))
    has_module_ = False
"""
    # To make the linter happy.
    has_module_ = True
    locals_: Dict[str, Any] = {}
    # Need to explicitly declare and pass `locals_`:
    # https://docs.python.org/3/library/functions.html#exec
    # `Pass an explicit locals dictionary if you need to see effects
    # of the code on locals after function exec() returns.`
    exec(code, globals(), locals_)
    has_module_ = locals_["has_module_"]
    return has_module_


# #############################################################################
# Print the env vars.
# #############################################################################


def get_env_var(
    env_name: str,
    as_bool: bool = False,
    default_value: Any = None,
    abort_on_missing: bool = True,
) -> Union[str, bool]:
    """
    Get an environment variable by name.

    :param env_name: name of the env var
    :param as_bool: convert the value into a Boolean
    :param default_value: the default value to use in case it's not defined
    :param abort_on_missing: if the env var is not defined aborts, otherwise use
        the default value
    :return: value of env var
    """
    if env_name not in os.environ:
        if abort_on_missing:
            assert 0, f"Can't find env var '{env_name}' in '{str(os.environ)}'"
        else:
            return default_value
    value = os.environ[env_name]
    if as_bool:
        # Convert the value into a boolean.
        if value in ("0", "", "None", "False"):
            value = False
        else:
            value = True
    return value


def get_env_vars() -> List[str]:
    """
    Return all the env vars that are expected to be set in Docker.
    """
    # Keep in sync with `lib_tasks.py:_generate_compose_file()`.
    env_var_names = [
        # AM AWS credentials.
        "AM_AWS_ACCESS_KEY_ID",
        "AM_AWS_DEFAULT_REGION",
        # AWS profile to use for AM.
        "AM_AWS_PROFILE",
        # S3 bucket to use for AM.
        "AM_AWS_S3_BUCKET",
        # AM AWS credentials.
        "AM_AWS_SECRET_ACCESS_KEY",
        # Path to the ECR for the Docker images.
        "AM_ECR_BASE_PATH",
        # Force enabling Docker-in-Docker.
        "AM_ENABLE_DIND",
        # Enable forcing certain unit tests to fail to check that unit test
        # failures are caught.
        "AM_FORCE_TEST_FAIL",
        # The name of the host running Docker.
        "AM_HOST_NAME",
        # The OS of the host running Docker.
        "AM_HOST_OS_NAME",
        # The name of the user running the host.
        "AM_HOST_USER_NAME",
        # The version of the host running Docker.
        "AM_HOST_VERSION",
        # Whether to check if certain property of the repo are as expected or not.
        "AM_REPO_CONFIG_CHECK",
        # Path to use for `repo_config.py`. E.g., used when running `dev_tools`
        # container to avoid using the `repo_config.py` corresponding to the
        # container launching the linter.
        "AM_REPO_CONFIG_PATH",
        "AM_TELEGRAM_TOKEN",
        "GH_ACTION_ACCESS_TOKEN",
        # Whether we are running inside GH Actions.
        "CI",
        # TODO(gp): Difference between amp and cmamp.
        # CK AWS credentials.
        "CK_AWS_ACCESS_KEY_ID",
        "CK_AWS_DEFAULT_REGION",
        "CK_AWS_SECRET_ACCESS_KEY",
        # S3 bucket to use for CK.
        "CK_AWS_S3_BUCKET",
        # Path to the ECR for the Docker images for CK.
        "CK_ECR_BASE_PATH",
    ]
    # No duplicates.
    assert len(set(env_var_names)) == len(
        env_var_names
    ), f"There are duplicates: {str(env_var_names)}"
    # Sort.
    env_var_names = sorted(env_var_names)
    return env_var_names


def get_secret_env_vars() -> List[str]:
    """
    Return the list of env vars that are secrets.
    """
    secret_env_var_names = [
        "AM_TELEGRAM_TOKEN",
        "AM_AWS_ACCESS_KEY_ID",
        "AM_AWS_SECRET_ACCESS_KEY",
        # TODO(gp): Difference between amp and cmamp.
        "CK_AWS_ACCESS_KEY_ID",
        "CK_AWS_SECRET_ACCESS_KEY",
        "GH_ACTION_ACCESS_TOKEN",
    ]
    # No duplicates.
    assert len(set(secret_env_var_names)) == len(
        secret_env_var_names
    ), f"There are duplicates: {str(secret_env_var_names)}"
    # Secret env vars are a subset of the env vars.
    env_vars = get_env_vars()
    if not set(secret_env_var_names).issubset(set(env_vars)):
        diff = set(secret_env_var_names).difference(set(env_vars))
        cmd = f"Secret vars in `{str(diff)} are not in '{str(env_vars)}'"
        assert 0, cmd
    # Sort.
    secret_env_var_names = sorted(secret_env_var_names)
    return secret_env_var_names


def check_env_vars() -> None:
    """
    Make sure all the expected env vars are defined.
    """
    env_vars = get_env_vars()
    for env_var in env_vars:
        assert (
            env_var in os.environ
        ), f"env_var='{str(env_var)}' is not in env_vars='{str(os.environ.keys())}''"


def env_vars_to_string() -> str:
    """
    Return a string with the signature of all the expected env vars (including
    the secret ones).
    """
    msg = []
    # Get the expected env vars and the secret ones.
    env_vars = get_env_vars()
    secret_env_vars = get_secret_env_vars()
    # Print a signature.
    for env_name in env_vars:
        is_defined = env_name in os.environ
        is_empty = is_defined and os.environ[env_name] == ""
        if not is_defined:
            msg.append(f"{env_name}=undef")
        else:
            if env_name in secret_env_vars:
                # Secret env var: print if it's empty or not.
                if is_empty:
                    msg.append(f"{env_name}=empty")
                else:
                    msg.append(f"{env_name}=***")
            else:
                # Not a secret var: print the value.
                msg.append(f"{env_name}='{os.environ[env_name]}'")
    msg = "\n".join(msg)
    return msg


def env_to_str(add_system_signature: bool = True) -> str:
    msg = ""
    #
    msg += "# Repo config:\n"
    msg += hprint.indent(execute_repo_config_code("config_func_to_str()"))
    msg += "\n"
    # System signature.
    if add_system_signature:
        msg += "# System signature:\n"
        msg += hprint.indent(get_system_signature()[0])
        msg += "\n"
    # Check which env vars are defined.
    msg += "# Env vars:\n"
    msg += hprint.indent(env_vars_to_string())
    msg += "\n"
    return msg


# #############################################################################
# Print the library versions.
# #############################################################################


def _get_library_version(lib_name: str) -> str:
    try:
        cmd = f"import {lib_name}"
        # pylint: disable=exec-used
        exec(cmd)
    except ImportError:
        version = "?"
    else:
        cmd = f"{lib_name}.__version__"
        version = eval(cmd)
    return version


def _append(
    txt: List[str], to_add: List[str], num_spaces: int = 2
) -> Tuple[List[str], List[str]]:
    txt.extend(
        [
            " " * num_spaces + line
            for txt_tmp in to_add
            for line in txt_tmp.split("\n")
        ]
    )
    to_add: List[str] = []
    return txt, to_add


# Copied from helpers.hgit to avoid circular dependencies.


def _git_log(num_commits: int = 5, my_commits: bool = False) -> str:
    """
    Return the output of a pimped version of git log.

    :param num_commits: number of commits to report
    :param my_commits: True to report only the current user commits
    :return: string
    """
    cmd = []
    cmd.append("git log --date=local --oneline --graph --date-order --decorate")
    cmd.append(
        "--pretty=format:" "'%h %<(8)%aN%  %<(65)%s (%>(14)%ar) %ad %<(10)%d'"
    )
    cmd.append(f"-{num_commits}")
    if my_commits:
        # This doesn't work in a container if the user relies on `~/.gitconfig` to
        # set the user name.
        # TODO(gp): We should use `get_git_name()`.
        cmd.append("--author $(git config user.name)")
    cmd = " ".join(cmd)
    data: Tuple[int, str] = hsystem.system_to_string(cmd)
    _, txt = data
    return txt


# End copy.


def _get_git_signature(git_commit_type: str = "all") -> List[str]:
    """
    Get information about current branch and latest commits.
    """
    txt_tmp: List[str] = []
    # Get the branch name.
    cmd = "git branch --show-current"
    _, branch_name = hsystem.system_to_one_line(cmd)
    txt_tmp.append(f"branch_name='{branch_name}'")
    # Get the short Git hash of the current branch.
    cmd = "git rev-parse --short HEAD"
    _, hash_ = hsystem.system_to_one_line(cmd)
    txt_tmp.append(f"hash='{hash_}'")
    # Add info about the latest commits.
    num_commits = 3
    if git_commit_type == "all":
        txt_tmp.append("# Last commits:")
        log_txt = _git_log(num_commits=num_commits, my_commits=False)
        txt_tmp.append(hprint.indent(log_txt))
    elif git_commit_type == "mine":
        txt_tmp.append("# Your last commits:")
        log_txt = _git_log(num_commits=num_commits, my_commits=True)
        txt_tmp.append(hprint.indent(log_txt))
    elif git_commit_type == "none":
        pass
    else:
        raise ValueError(f"Invalid value='{git_commit_type}'")
    return txt_tmp


def get_system_signature(git_commit_type: str = "all") -> Tuple[str, int]:
    # TODO(gp): This should return a string that we append to the rest.
    container_dir_name = "."
    hversio.check_version(container_dir_name)
    #
    txt: List[str] = []
    # Add git signature.
    txt.append("# Git")
    txt_tmp: List[str] = []
    try:
        txt_tmp += _get_git_signature(git_commit_type)
        # If there is amp as submodule, fetch its git signature.
        if os.path.exists("amp"):
            prev_cwd = os.getcwd()
            try:
                # Temporarily descend into amp.
                os.chdir("amp")
                txt_tmp.append("# Git amp")
                git_amp_sig = _get_git_signature(git_commit_type)
                txt_tmp, git_amp_sig = _append(txt_tmp, git_amp_sig)
            finally:
                os.chdir(prev_cwd)
    except RuntimeError as e:
        _LOG.error(str(e))
    txt, txt_tmp = _append(txt, txt_tmp)
    # Add processor info.
    txt.append("# Machine info")
    txt_tmp: List[str] = []
    import platform

    uname = platform.uname()
    txt_tmp.append(f"system={uname.system}")
    txt_tmp.append(f"node name={uname.node}")
    txt_tmp.append(f"release={uname.release}")
    txt_tmp.append(f"version={uname.version}")
    txt_tmp.append(f"machine={uname.machine}")
    txt_tmp.append(f"processor={uname.processor}")
    try:
        import psutil

        has_psutil = True
    except ModuleNotFoundError as e:
        print(e)
        has_psutil = False
    if has_psutil:
        txt_tmp.append(f"cpu count={psutil.cpu_count()}")
        txt_tmp.append(f"cpu freq={str(psutil.cpu_freq())}")
        # TODO(gp): Report in MB or GB.
        txt_tmp.append(f"memory={str(psutil.virtual_memory())}")
        txt_tmp.append(f"disk usage={str(psutil.disk_usage('/'))}")
        txt, txt_tmp = _append(txt, txt_tmp)
    # Add package info.
    txt.append("# Packages")
    packages = []
    packages.append(("python", platform.python_version()))
    # import sys
    # print(sys.version)
    libs = [
        "cvxopt",
        "cvxpy",
        "gluonnlp",
        "gluonts",
        "joblib",
        "mxnet",
        "numpy",
        "pandas",
        "pyarrow",
        "scipy",
        "seaborn",
        "sklearn",
        "statsmodels",
    ]
    libs = sorted(libs)
    failed_imports = 0
    for lib in libs:
        # This is due to Cmamp4924:
        # WARNING: libarmpl_lp64_mp.so: cannot open shared object file: No such
        #  file or directory
        try:
            version = _get_library_version(lib)
        except OSError as e:
            print(_WARNING + ": " + str(e))
        if version.startswith("ERROR"):
            failed_imports += 1
        packages.append((lib, version))
    txt_tmp.extend([f"{l}: {v}" for (l, v) in packages])
    txt, txt_tmp = _append(txt, txt_tmp)
    #
    txt = "\n".join(txt)
    return txt, failed_imports


# #############################################################################
# Execute code from the `repo_config.py` in the super module.
# #############################################################################


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


def get_repo_config_file(super_module: bool = True) -> str:
    """
    Return the absolute path to `repo_config.py` that should be used.

    The `repo_config.py` is determined based on an overriding env var or
    based on the root of the Git path.
    """
    env_var = "AM_REPO_CONFIG_PATH"
    file_name = get_env_var(env_var, abort_on_missing=False)
    if file_name:
        _LOG.warning("Using value '%s' for %s from env var", file_name, env_var)
    else:
        # TODO(gp): We should actually ask Git where the super-module is.
        client_root = _get_client_root(super_module)
        file_name = os.path.join(client_root, "repo_config.py")
        file_name = os.path.abspath(file_name)
    return file_name


def _get_repo_config_code(super_module: bool = True) -> str:
    """
    Return the text of the code stored in `repo_config.py`.
    """
    file_name = get_repo_config_file(super_module)
    hdbg.dassert_file_exists(file_name)
    code: str = hio.from_file(file_name)
    return code


def execute_repo_config_code(code_to_execute: str) -> Any:
    """
    Execute code in `repo_config.py` by dynamically finding the correct one.

    E.g.,
    ```
    henv.execute_repo_config_code("has_dind_support()")
    ```
    """
    # Read the info from the current repo.
    code = _get_repo_config_code()
    # TODO(gp): make the linter happy creating this symbol that comes from the
    #  `exec()`.
    try:
        exec(code, globals())  # pylint: disable=exec-used
        ret = eval(code_to_execute)
    except NameError as e:
        _LOG.error(
            "While executing '%s' caught error:\n%s\nTrying to continue",
            code_to_execute,
            e,
        )
        ret = None
        _ = e
        # raise e
    return ret
