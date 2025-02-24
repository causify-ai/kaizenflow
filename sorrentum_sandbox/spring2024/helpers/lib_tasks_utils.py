"""
Import as:

import helpers.lib_tasks_utils as hlitauti
"""

import datetime
import glob
import logging
import os
import pprint
import re
import sys
from typing import Any, Dict, List, Optional, Union

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hversion as hversio

_LOG = logging.getLogger(__name__)


# #############################################################################
# Default params.
# #############################################################################

# This is used to inject the default params.
# TODO(gp): Using a singleton here is not elegant but simple.
_DEFAULT_PARAMS = {}


def set_default_params(params: Dict[str, Any]) -> None:
    global _DEFAULT_PARAMS
    _DEFAULT_PARAMS = params
    _LOG.debug("Assigning:\n%s", pprint.pformat(params))


def has_default_param(key: str) -> bool:
    hdbg.dassert_isinstance(key, str)
    return key in _DEFAULT_PARAMS


def get_default_param(key: str, *, override_value: Any = None) -> Any:
    """
    Return the value from the default parameters dictionary, optionally
    overriding it.
    """
    hdbg.dassert_isinstance(key, str)
    value = None
    if has_default_param(key):
        value = _DEFAULT_PARAMS[key]
    if override_value:
        _LOG.info("Overriding value %s with %s", value, override_value)
        value = override_value
    hdbg.dassert_is_not(
        value, None, "key='%s' not defined from %s", key, _DEFAULT_PARAMS
    )
    return value


def reset_default_params() -> None:
    params: Dict[str, Any] = {}
    set_default_params(params)


# #############################################################################
# Utils.
# #############################################################################


def parse_command_line() -> None:
    # Since it's not easy to add global command line options to invoke, we
    # piggy back the option that already exists.
    # If one uses the debug option for `invoke` we turn off the code
    # debugging.
    # TODO(gp): Check http://docs.pyinvoke.org/en/1.0/concepts/library.html#
    #   modifying-core-parser-arguments
    if ("-d" in sys.argv) or ("--debug" in sys.argv):
        hdbg.init_logger(verbosity=logging.DEBUG)
    else:
        hdbg.init_logger(verbosity=logging.INFO)


# NOTE: We need to use a `# type: ignore` for all the @task functions because
# pyinvoke infers the argument type from the code and mypy annotations confuse
# it (see https://github.com/pyinvoke/invoke/issues/357).

# In the following, when using `lru_cache`, we use functions from `hsyste`
# instead of `ctx.run()` since otherwise `lru_cache` would cache `ctx`.

# We prefer not to cache functions running `git` to avoid stale values if we
# call git (e.g., if we cache Git hash and then we do a `git pull`).

# pyinvoke `ctx.run()` is useful for unit testing, since it allows to:
# - mock the result of a system call
# - register the issued command line (to create the expected outcome of a test)
# On the other side `system_interaction.py` contains many utilities that make
# it easy to interact with the system.
# Once AmpPart1347 is implemented we can replace all the `ctx.run()` with calls
# to `system_interaction.py`.


_WAS_FIRST_CALL_DONE = False


def report_task(txt: str = "", container_dir_name: str = ".") -> None:
    # On the first invocation report the version.
    global _WAS_FIRST_CALL_DONE
    if not _WAS_FIRST_CALL_DONE:
        _WAS_FIRST_CALL_DONE = True
        hversio.check_version(container_dir_name)
    # Print the name of the function.
    func_name = hintros.get_function_name(count=1)
    msg = f"## {func_name}: {txt}"
    print(hprint.color_highlight(msg, color="purple"))


# TODO(gp): Move this to helpers.system_interaction and allow to add the switch
#  globally.
def _to_single_line_cmd(cmd: Union[str, List[str]]) -> str:
    """
    Convert a multiline command (as a string or list of strings) into a single
    line.

    E.g., convert
        ```
        IMAGE=.../amp:dev \
            docker-compose \
            --file devops/compose/docker-compose.yml \
            --file devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env
        ```
    into
        ```
        IMAGE=.../amp:dev docker-compose --file ...
        ```
    """
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    hdbg.dassert_isinstance(cmd, str)
    cmd = cmd.rstrip().lstrip()
    # Remove `\` at the end of the line.
    cmd = re.sub(r" \\\s*$", " ", cmd, flags=re.MULTILINE)
    # Use a single space between words in the command.
    # TODO(gp): This is a bit dangerous if there are multiple spaces in a string
    #  that for some reason are meaningful.
    cmd = " ".join(cmd.split())
    return cmd


def to_multi_line_cmd(docker_cmd_: List[str]) -> str:
    r"""
    Convert a command encoded as a list of strings into a single command
    separated by `\`.

    E.g., convert
    ```
        ['IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp:dev',
            '\n        docker-compose',
            '\n        --file amp/devops/compose/docker-compose.yml',
            '\n        --file amp/devops/compose/docker-compose_as_submodule.yml',
            '\n        --env-file devops/env/default.env']
        ```
    into
        ```
        IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp:dev \
            docker-compose \
            --file devops/compose/docker-compose.yml \
            --file devops/compose/docker-compose_as_submodule.yml \
            --env-file devops/env/default.env
        ```
    """
    # Expand all strings into single lines.
    _LOG.debug("docker_cmd=%s", docker_cmd_)
    docker_cmd_tmp = []
    for dc in docker_cmd_:
        # Add a `\` at the end of each string.
        hdbg.dassert(not dc.endswith("\\"), "dc='%s'", dc)
        dc += " \\"
        docker_cmd_tmp.extend(dc.split("\n"))
    docker_cmd_ = docker_cmd_tmp
    # Remove empty lines.
    docker_cmd_ = [cmd for cmd in docker_cmd_ if cmd.rstrip().lstrip() != ""]
    # Package the command.
    docker_cmd_ = "\n".join(docker_cmd_)
    # Remove a `\` at the end, since it is not needed.
    docker_cmd_ = docker_cmd_.rstrip("\\")
    _LOG.debug("docker_cmd=%s", docker_cmd_)
    return docker_cmd_


# TODO(gp): Pass through command line using a global switch or an env var.
use_one_line_cmd = False


def run(
    ctx: Any,
    cmd: str,
    *args: Any,
    dry_run: bool = False,
    use_system: bool = False,
    print_cmd: bool = False,
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    _LOG.debug(hprint.to_str("cmd dry_run"))
    if use_one_line_cmd:
        cmd = _to_single_line_cmd(cmd)
    _LOG.debug("cmd=%s", cmd)
    if dry_run:
        print(f"Dry-run: > {cmd}")
        _LOG.warning("Skipping execution of '%s'", cmd)
        res = None
    else:
        if print_cmd:
            print(f"> {cmd}")
        if use_system:
            # TODO(gp): Consider using only `hsystem.system()` since it's more
            # reliable.
            res = hsystem.system(cmd, suppress_output=False)
        else:
            result = ctx.run(cmd, *args, **ctx_run_kwargs)
            res = result.return_code
    return res


# TODO(gp): -> system_interaction.py ?
def _to_pbcopy(txt: str, pbcopy: bool) -> None:
    """
    Save the content of txt in the system clipboard.
    """
    txt = txt.rstrip("\n")
    if not pbcopy:
        print(txt)
        return
    if not txt:
        print("Nothing to copy")
        return
    if hsystem.is_running_on_macos():
        # -n = no new line
        cmd = f"echo -n '{txt}' | pbcopy"
        hsystem.system(cmd)
        print(f"\n# Copied to system clipboard:\n{txt}")
    else:
        _LOG.warning("pbcopy works only on macOS")
        print(txt)


# TODO(gp): We should factor out the meaning of the params in a string and add it
#  to all the tasks' help.
def _get_files_to_process(
    modified: bool,
    branch: bool,
    last_commit: bool,
    # TODO(gp): Pass abs_dir, instead of `all_` and remove the calls from the
    # outer clients.
    all_: bool,
    files_from_user: str,
    mutually_exclusive: bool,
    remove_dirs: bool,
) -> List[str]:
    """
    Get a list of files to process.

    The files are selected based on the switches:
    - `branch`: changed in the branch
    - `modified`: changed in the client (both staged and modified)
    - `last_commit`: part of the previous commit
    - `all`: all the files in the repo
    - `files_from_user`: passed by the user

    :param modified: return files modified in the client (i.e., changed with
        respect to HEAD)
    :param branch: return files modified with respect to the branch point
    :param last_commit: return files part of the previous commit
    :param all: return all repo files
    :param files_from_user: return files passed to this function
    :param mutually_exclusive: ensure that all options are mutually exclusive
    :param remove_dirs: whether directories should be processed
    :return: paths to process
    """
    _LOG.debug(
        hprint.to_str(
            "modified branch last_commit all_ files_from_user "
            "mutually_exclusive remove_dirs"
        )
    )
    if mutually_exclusive:
        # All the options are mutually exclusive.
        hdbg.dassert_eq(
            int(modified)
            + int(branch)
            + int(last_commit)
            + int(all_)
            + int(len(files_from_user) > 0),
            1,
            msg="Specify only one among --modified, --branch, --last-commit, "
            "--all_files, and --files",
        )
    else:
        # We filter the files passed from the user through other the options,
        # so only the filtering options need to be mutually exclusive.
        hdbg.dassert_eq(
            int(modified) + int(branch) + int(last_commit) + int(all_),
            1,
            msg="Specify only one among --modified, --branch, --last-commit",
        )
    dir_name = "."
    if modified:
        files = hgit.get_modified_files(dir_name)
    elif branch:
        files = hgit.get_modified_files_in_branch("master", dir_name)
    elif last_commit:
        files = hgit.get_previous_committed_files(dir_name)
    elif all_:
        pattern = "*"
        only_files = True
        use_relative_paths = True
        files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
    if files_from_user:
        # If files were passed, filter out non-existent paths.
        files = _filter_existing_paths(files_from_user.split())
    # Convert into a list.
    hdbg.dassert_isinstance(files, list)
    files_to_process = [f for f in files if f != ""]
    # We need to remove `amp` to avoid copying the entire tree.
    files_to_process = [f for f in files_to_process if f != "amp"]
    _LOG.debug("files_to_process='%s'", str(files_to_process))
    # Remove dirs, if needed.
    if remove_dirs:
        files_to_process = hsystem.remove_dirs(files_to_process)
    _LOG.debug("files_to_process='%s'", str(files_to_process))
    # Ensure that there are files to process.
    if not files_to_process:
        _LOG.warning("No files were selected")
    return files_to_process


def _filter_existing_paths(paths_from_user: List[str]) -> List[str]:
    """
    Filter out the paths to non-existent files.

    :param paths_from_user: paths passed by user
    :return: existing paths
    """
    paths = []
    for user_path in paths_from_user:
        if user_path.endswith("/*"):
            # Get the files according to the "*" pattern.
            dir_files = glob.glob(user_path)
            if dir_files:
                # Check whether the pattern matches files.
                paths.extend(dir_files)
            else:
                _LOG.error(
                    (
                        "'%s' pattern doesn't match any files: "
                        "the directory is empty or path does not exist"
                    ),
                    user_path,
                )
        elif os.path.exists(user_path):
            paths.append(user_path)
        else:
            _LOG.error("'%s' does not exist", user_path)
    return paths


# Copied from helpers.datetime_ to avoid dependency from pandas.


def get_ET_timestamp() -> str:
    # The timezone depends on how the shell is configured.
    timestamp = datetime.datetime.now()
    return timestamp.strftime("%Y%m%d_%H%M%S")


# End copy.
