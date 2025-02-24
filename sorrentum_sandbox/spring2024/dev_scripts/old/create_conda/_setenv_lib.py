"""
Contains functions used by a `setenv_*.py` script in a repo to generate a bash
script that is executed to configure the development environment.

Import as:

import dev_scripts.old.create_conda._setenv_lib as dsoccseli
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import helpers.hdbg as hdbg  # isort:skip # noqa: E402
import helpers.hio as hio  # isort:skip # noqa: E402
import helpers.hparser as hparser  # isort:skip # noqa: E402
import helpers.hsystem as hsystem  # isort:skip # noqa: E402


_LOG = logging.getLogger(__name__)

# #############################################################################
# Helpers for the phases.
# #############################################################################


# TODO(gp): This is kind of useless since the cleaning of the path is done at
#  run-time now.
def _remove_redundant_paths(paths: List[str]) -> List[str]:
    # Set of unique paths.
    found_paths = set()
    paths_out = []
    for p in paths:
        if p == "":
            continue
        if p not in found_paths:
            # Found a new path. Add it to the output.
            found_paths.add(p)
            paths_out.append(p)
    return paths_out


def _export_env_var(val_name: str, vals: List[Any]) -> List[str]:
    """
    Create a snippet of bash script equivalent to the following:

    ```
    # Update variable.
    PYTHONPATH=$CURR_DIR:$PYTHONPATH
    # Remove redundant paths.
    PYTHONPATH="$(echo $PYTHONPATH | perl -e
      'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))')"
    echo "PYTHONPATH=$PYTHONPATH"
    echo $PYTHONPATH | $EXEC_PATH/print_paths.sh
    ```
    """
    txt = []
    # Update variable.
    txt.append("# Update variable.")
    vals = _remove_redundant_paths(vals)
    txt.append(f"{val_name}=" + ":".join(vals))
    txt_tmp = f"{val_name}="
    txt_tmp += f"$(echo ${val_name}"
    # TODO(gp): Improve this script. It doesn't seem to work for the empty
    #  paths and with repeated paths.
    txt_tmp += (
        " | perl -e "
        + """'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))'"""
    )
    txt_tmp += ")"
    txt.append(txt_tmp)
    #
    txt.append("# Print variable.")
    txt.append(f"echo {val_name}=${val_name}")
    txt.append(
        f"echo ${val_name}"
        + """ | perl -e 'print "  "; print join("\\n  ", split(/:/, scalar <>))'"""
    )
    #
    txt.append("# Export variable.")
    txt.append(f"export {val_name}")
    return txt


def _frame(comment: str, txt: List[str]) -> None:
    txt_tmp = []
    line = "#" * 80
    txt_tmp.append("\n" + f"echo '{line}'")
    txt_tmp.append("echo " + comment)
    txt_tmp.append(f"echo '{line}'")
    txt.extend(txt_tmp)


def _execute(cmd: str, txt: List[str]) -> None:
    txt.append(f"echo '> {cmd}'")
    txt.append(cmd)


def _log_var(var_name: str, var_val: str, txt: List[str]) -> None:
    txt.append(f"echo '{var_name}={var_val}'")
    _LOG.debug("%s='%s'", var_name, var_val)


# #############################################################################
# Various phases.
# #############################################################################


def report_info(txt: List[str]) -> Tuple[str, str]:
    """
    Add to the bash script `txt` diagnostic informations.

    :return:
        - client_root_path: the directory that includes the executable as
          `dev_scripts/_setenv_*.py` (i.e., the dir that is ../exec_path)
        - user_name
    """
    _frame("Info", txt)
    _log_var("cmd_line", hdbg.get_command_line(), txt)
    exec_name = os.path.abspath(sys.argv[0])
    hdbg.dassert_path_exists(exec_name)
    _log_var("exec_name", exec_name, txt)
    # Full path of this executable which is the same as setenv_*.sh.
    exec_path = os.path.dirname(exec_name)
    _log_var("exec_path", exec_path, txt)
    hdbg.dassert(
        os.path.basename(exec_path), "dev_scripts", "exec_path=%s", exec_path
    )
    # Get the path of the root of the Git client.
    client_root_path = os.path.abspath(os.path.join(exec_path, ".."))
    hdbg.dassert_path_exists(client_root_path)
    # Current dir.
    curr_path = os.getcwd()
    _log_var("curr_path", curr_path, txt)
    # Get name.
    user_name = hsystem.get_user_name()
    _log_var("user_name", user_name, txt)
    server_name = hsystem.get_server_name()
    _log_var("server_name", server_name, txt)
    return client_root_path, user_name


def config_git(
    user_name: str, user_credentials: Dict[str, str], txt: List[str]
) -> None:
    """
    Add to the bash script in `txt` instructions to:

    - configure git user name and user email
    """
    _frame("Config git", txt)
    git_user_name = user_credentials["git_user_name"]
    if git_user_name:
        cmd = f'git config --local user.name "{git_user_name}"'
        _execute(cmd, txt)
    #
    git_user_email = user_credentials["git_user_email"]
    if git_user_email:
        cmd = f'git config --local user.email "{git_user_email}"'
        _execute(cmd, txt)
    #
    if user_name == "jenkins":
        cmd = "git config --list"
        _execute(cmd, txt)


def config_python(dirs: List[str], txt: List[str]) -> None:
    """
    Add to the bash script `txt` instructions to configure python by:

    - disable python caching
    - appending the submodule path to $PYTHONPATH
    """
    _frame("Config python", txt)
    #
    txt.append("# Disable python code caching.")
    txt.append("export PYTHONDONTWRITEBYTECODE=x")
    #
    txt.append("# Append paths to PYTHONPATH.")
    hdbg.dassert_isinstance(dirs, list)
    dirs = sorted(dirs)
    dirs = [os.path.abspath(d) for d in dirs]
    for d in dirs:
        hdbg.dassert_path_exists(d)
    python_path = dirs + ["$PYTHONPATH"]
    txt.extend(_export_env_var("PYTHONPATH", python_path))
    txt.append("# Assign MYPYPATH to let mypy find the modules.")
    txt.append("export MYPYPATH=$PYTHONPATH")


def config_conda(
    conda_env: str, user_credentials: Dict[str, str], txt: List[str]
) -> None:
    """
    Add to the bash script `txt` instructions to activate a conda environment.
    """
    _frame("Config conda", txt)
    #
    conda_sh_path = user_credentials["conda_sh_path"]
    _log_var("conda_sh_path", conda_sh_path, txt)
    # TODO(gp): This makes conda not working for some reason.
    # txt.append("source %s" % conda_sh_path)
    hdbg.dassert_path_exists(conda_sh_path)
    #
    txt.append('echo "CONDA_PATH="$(which conda)')
    txt.append('echo "CONDA_VER="$(conda -V)')
    #
    cmd = "conda info --envs"
    _execute(cmd, txt)
    #
    cmd = "which python"
    _execute(cmd, txt)
    #
    cmd = f"conda activate {conda_env}"
    _execute(cmd, txt)
    #
    cmd = "conda info --envs"
    _execute(cmd, txt)
    #
    cmd = "which python"
    _execute(cmd, txt)


def get_dev_scripts_subdirs() -> Tuple:
    return (".", "aws", "git", "infra", "install", "notebooks", "testing")


def config_path(dirs: List[str], txt: List[str]) -> List[str]:
    """
    Prepend to PATH the directories `dirs` rooted in `path`.
    """
    _frame("Config path", txt)
    hdbg.dassert_isinstance(dirs, list)
    dirs = sorted(dirs)
    dirs = [os.path.abspath(d) for d in dirs]
    for d in dirs:
        hdbg.dassert_path_exists(d)
    path = dirs + ["$PATH"]
    txt.extend(_export_env_var("PATH", path))
    return txt


def test_packages(amp_path: str, txt: List[str]) -> None:
    _frame("Test packages", txt)
    script = os.path.join(
        amp_path, "dev_scripts/install/check_develop_packages.py"
    )
    script = os.path.abspath(script)
    hdbg.dassert_path_exists(script)
    _execute(script, txt)


def save_script(args: argparse.Namespace, txt: List[str]) -> None:
    txt_str = "\n".join(txt)
    if args.output_file:
        hio.to_file(args.output_file, txt_str)
    else:
        # stdout.
        print(txt_str)


# #############################################################################


def parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-o", "--output_file", default=None, help="File to write. None for stdout"
    )
    parser.add_argument(
        "-e", "--conda_env", default=None, help="Select the conda env to use."
    )
    hparser.add_verbosity_arg(parser)
    # To capture some dummy command options (e.g., "bell-style none") passed by
    # source on some systems.
    parser.add_argument("positional", nargs="*", help="...")
    return parser
