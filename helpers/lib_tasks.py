"""
Import as:

import helpers.lib_tasks as hlibtask
"""

import datetime
import functools
import glob
import grp
import io
import json
import logging
import os
import pprint
import pwd
import re
import stat
import sys
from typing import Any, Dict, Iterator, List, Match, Optional, Set, Tuple, Union

import tqdm
import yaml
from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hlist as hlist
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.htable as htable
import helpers.htraceback as htraceb
import helpers.hunit_test_utils as hunteuti
import helpers.hversion as hversio

_LOG = logging.getLogger(__name__)


# Conventions around `pyinvoke`:
# - `pyinvoke` uses introspection to infer properties of a task, but doesn't
#   support many Python3 features (see https://github.com/pyinvoke/invoke/issues/357)
# - Don't use type hints in `@tasks`
#   - we use `# ignore: type` to avoid mypy complaints
# - Minimize the code in `@tasks` calling other functions to use Python3 features
# - Use `""` as default instead None since `pyinvoke` can only infer a single type


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

# Since it's not easy to add global command line options to invoke, we piggy
# back the option that already exists.
# If one uses the debug option for `invoke` we turn off the code debugging.
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


def _report_task(txt: str = "", container_dir_name: str = ".") -> None:
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


# TODO(Grisha): make it public #755.
def _to_multi_line_cmd(docker_cmd_: List[str]) -> str:
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


# TODO(Grisha): make it public #755.
def _run(
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
        _LOG.warning("Skipping execution")
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


def _get_ET_timestamp() -> str:
    # The timezone depends on how the shell is configured.
    timestamp = datetime.datetime.now()
    return timestamp.strftime("%Y%m%d_%H%M%S")


# End copy.

# #############################################################################
# Set-up.
# #############################################################################


@task
def print_setup(ctx):  # type: ignore
    """
    Print some configuration variables.
    """
    _report_task()
    _ = ctx
    var_names = "AM_ECR_BASE_PATH BASE_IMAGE".split()
    for v in var_names:
        print(f"{v}={get_default_param(v)}")


@task
def print_tasks(ctx, as_code=False):  # type: ignore
    """
    Print all the available tasks in `lib_tasks.py`.

    These tasks might be exposed or not by different.

    :param as_code: print as python code so that it can be embed in a
        `from helpers.lib_tasks import ...`
    """
    _report_task()
    _ = ctx
    func_names = []
    lib_tasks_file_name = os.path.join(
        hgit.get_amp_abs_path(), "helpers/lib_tasks.py"
    )
    hdbg.dassert_file_exists(lib_tasks_file_name)
    # TODO(gp): Use __file__ instead of hardwiring the file.
    cmd = rf'\grep "^@task" -A 1 {lib_tasks_file_name} | grep def'
    # def print_setup(ctx):  # type: ignore
    # def git_pull(ctx):  # type: ignore
    # def git_fetch_master(ctx):  # type: ignore
    _, txt = hsystem.system_to_string(cmd)
    for line in txt.split("\n"):
        _LOG.debug("line=%s", line)
        m = re.match(r"^def\s+(\S+)\(", line)
        if m:
            func_name = m.group(1)
            _LOG.debug("  -> %s", func_name)
            func_names.append(func_name)
    func_names = sorted(func_names)
    if as_code:
        print("\n".join([f"{fn}," for fn in func_names]))
    else:
        print("\n".join(func_names))


@task
def print_env(ctx):  # type: ignore
    """
    Print the repo configuration.
    """
    _ = ctx
    print(hversio.env_to_str())


# #############################################################################
# Git.
# #############################################################################


@task
def git_pull(ctx):  # type: ignore
    """
    Pull all the repos.
    """
    _report_task()
    #
    cmd = "git pull --autostash"
    _run(ctx, cmd)
    #
    cmd = "git submodule foreach 'git pull --autostash'"
    _run(ctx, cmd)


@task
def git_fetch_master(ctx):  # type: ignore
    """
    Pull master without changing branch.
    """
    _report_task()
    #
    cmd = "git fetch origin master:master"
    _run(ctx, cmd)


@task
def git_merge_master(ctx, ff_only=False, abort_if_not_clean=True):  # type: ignore
    """
    Merge `origin/master` into the current branch.

    :param ff_only: abort if fast-forward is not possible
    """
    _report_task()
    # Check that the Git client is clean.
    hgit.is_client_clean(dir_name=".", abort_if_not_clean=abort_if_not_clean)
    # Pull master.
    git_fetch_master(ctx)
    # Merge master.
    cmd = "git merge master"
    if ff_only:
        cmd += " --ff-only"
    _run(ctx, cmd)


@task
def git_clean(ctx, fix_perms_=False, dry_run=False):  # type: ignore
    """
    Clean the repo_short_name and its submodules from artifacts.

    Run `git status --ignored` to see what it's skipped.
    """
    _report_task(txt=hprint.to_str("dry_run"))
    # TODO(*): Add "are you sure?" or a `--force switch` to avoid to cancel by
    #  mistake.
    # Fix permissions, if needed.
    if fix_perms_:
        cmd = "invoke fix_perms"
        _run(ctx, cmd)
    # Clean recursively.
    git_clean_cmd = "git clean -fd"
    if dry_run:
        git_clean_cmd += " --dry-run"
    # Clean current repo.
    cmd = git_clean_cmd
    _run(ctx, cmd)
    # Clean submodules.
    cmd = f"git submodule foreach '{git_clean_cmd}'"
    _run(ctx, cmd)
    # Delete other files.
    to_delete = [
        r"*\.pyc",
        r"*\.pyo",
        r".coverage",
        r".ipynb_checkpoints",
        r".mypy_cache",
        r".pytest_cache",
        r"__pycache__",
        r"cfile",
        r"tmp.*",
        r"*.tmp",
    ]
    opts = [f"-name '{opt}'" for opt in to_delete]
    opts = " -o ".join(opts)
    cmd = f"find . {opts} | sort"
    if not dry_run:
        cmd += " | xargs rm -rf"
    _run(ctx, cmd)


@task
def git_add_all_untracked(ctx):  # type: ignore
    """
    Add all untracked files to Git.
    """
    _report_task()
    cmd = "git add $(git ls-files -o --exclude-standard)"
    _run(ctx, cmd)


@task
def git_create_patch(  # type: ignore
    ctx, mode="diff", modified=False, branch=False, last_commit=False, files=""
):
    """
    Create a patch file for the entire repo_short_name client from the base
    revision. This script accepts a list of files to package, if specified.

    The parameters `modified`, `branch`, `last_commit` have the same meaning as
    in `_get_files_to_process()`.

    :param mode: what kind of patch to create
        - "diff": (default) creates a patch with the diff of the files
        - "tar": creates a tar ball with all the files
    """
    _report_task(txt=hprint.to_str("mode modified branch last_commit files"))
    _ = ctx
    # TODO(gp): Check that the current branch is up to date with master to avoid
    #  failures when we try to merge the patch.
    hdbg.dassert_in(mode, ("tar", "diff"))
    # For now we just create a patch for the current submodule.
    # TODO(gp): Extend this to handle also nested repos.
    super_module = False
    git_client_root = hgit.get_client_root(super_module)
    hash_ = hgit.get_head_hash(git_client_root, short_hash=True)
    timestamp = _get_ET_timestamp()
    #
    tag = os.path.basename(git_client_root)
    dst_file = f"patch.{tag}.{hash_}.{timestamp}"
    if mode == "tar":
        dst_file += ".tgz"
    elif mode == "diff":
        dst_file += ".patch"
    else:
        hdbg.dfatal("Invalid code path")
    _LOG.debug("dst_file=%s", dst_file)
    # Summary of files.
    _LOG.info(
        "Difference between HEAD and master:\n%s",
        hgit.get_summary_files_in_branch("master", dir_name="."),
    )
    # Get the files.
    all_ = False
    # We allow to specify files as a subset of files modified in the branch or
    # in the client.
    mutually_exclusive = False
    # We don't allow to specify directories.
    remove_dirs = True
    files_as_list = _get_files_to_process(
        modified,
        branch,
        last_commit,
        all_,
        files,
        mutually_exclusive,
        remove_dirs,
    )
    _LOG.info("Files to save:\n%s", hprint.indent("\n".join(files_as_list)))
    if not files_as_list:
        _LOG.warning("Nothing to patch: exiting")
        return
    files_as_str = " ".join(files_as_list)
    # Prepare the patch command.
    cmd = ""
    if mode == "tar":
        cmd = f"tar czvf {dst_file} {files_as_str}"
        cmd_inv = "tar xvzf"
    elif mode == "diff":
        if modified:
            opts = "HEAD"
        elif branch:
            opts = "master..."
        elif last_commit:
            opts = "HEAD^"
        else:
            hdbg.dfatal(
                "You need to specify one among -modified, --branch, "
                "--last-commit"
            )
        cmd = f"git diff {opts} --binary {files_as_str} >{dst_file}"
        cmd_inv = "git apply"
    # Execute patch command.
    _LOG.info("Creating the patch into %s", dst_file)
    hdbg.dassert_ne(cmd, "")
    _LOG.debug("cmd=%s", cmd)
    rc = hsystem.system(cmd, abort_on_error=False)
    if not rc:
        _LOG.warning("Command failed with rc=%d", rc)
    # Print message to apply the patch.
    remote_file = os.path.basename(dst_file)
    abs_path_dst_file = os.path.abspath(dst_file)
    msg = f"""
# To apply the patch and execute:
> git checkout {hash_}
> {cmd_inv} {abs_path_dst_file}

# To apply the patch to a remote client:
> export SERVER="server"
> export CLIENT_PATH="~/src"
> scp {dst_file} $SERVER:
> ssh $SERVER 'cd $CLIENT_PATH && {cmd_inv} ~/{remote_file}'"
    """
    print(msg)


@task
def git_files(  # type: ignore
    ctx, modified=False, branch=False, last_commit=False, pbcopy=False
):
    """
    Report which files are changed in the current branch with respect to
    `master`.

    The params have the same meaning as in `_get_files_to_process()`.
    """
    _report_task()
    _ = ctx
    all_ = False
    files = ""
    mutually_exclusive = True
    # pre-commit doesn't handle directories, but only files.
    remove_dirs = True
    files_as_list = _get_files_to_process(
        modified,
        branch,
        last_commit,
        all_,
        files,
        mutually_exclusive,
        remove_dirs,
    )
    print("\n".join(sorted(files_as_list)))
    if pbcopy:
        res = " ".join(files_as_list)
        _to_pbcopy(res, pbcopy)


@task
def git_last_commit_files(ctx, pbcopy=True):  # type: ignore
    """
    Print the status of the files in the previous commit.

    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    cmd = 'git log -1 --name-status --pretty=""'
    _run(ctx, cmd)
    # Get the list of existing files.
    files = hgit.get_previous_committed_files(".")
    txt = "\n".join(files)
    print(f"\n# The files modified are:\n{txt}")
    # Save to clipboard.
    res = " ".join(files)
    _to_pbcopy(res, pbcopy)


# TODO(gp): Add git_co(ctx)
# Reuse hgit.git_stash_push() and hgit.stash_apply()
# git stash save your-file-name
# git checkout master
# # do whatever you had to do with master
# git checkout staging
# git stash pop


# #############################################################################
# Branches workflows
# #############################################################################


# TODO(gp): Consider renaming the commands as `git_branch_*`


@task
def git_branch_files(ctx):  # type: ignore
    """
    Report which files were added, changed, and modified in the current branch
    with respect to `master`.

    This is a more detailed version of `i git_files --branch`.
    """
    _report_task()
    _ = ctx
    print(
        "Difference between HEAD and master:\n"
        + hgit.get_summary_files_in_branch("master", dir_name=".")
    )


@task
def git_create_branch(  # type: ignore
    ctx,
    branch_name="",
    issue_id=0,
    repo_short_name="current",
    suffix="",
    only_branch_from_master=True,
):
    """
    Create and push upstream branch `branch_name` or the one corresponding to
    `issue_id` in repo_short_name `repo_short_name`.

    E.g.,
    ```
    > git checkout -b LemTask169_Get_GH_actions
    > git push --set- upstream origin LemTask169_Get_GH_actions
    ```

    :param branch_name: name of the branch to create (e.g.,
        `LemTask169_Get_GH_actions`)
    :param issue_id: use the canonical name for the branch corresponding to that
        issue
    :param repo_short_name: name of the GitHub repo_short_name that the `issue_id`
        belongs to
        - "current" (default): the current repo_short_name
        - short name (e.g., "amp", "lm") of the branch
    :param suffix: suffix (e.g., "02") to add to the branch name when using issue_id
    :param only_branch_from_master: only allow to branch from master
    """
    _report_task()
    if issue_id > 0:
        # User specified an issue id on GitHub.
        hdbg.dassert_eq(
            branch_name, "", "You can't specify both --issue and --branch_name"
        )
        title, _ = _get_gh_issue_title(issue_id, repo_short_name)
        branch_name = title
        _LOG.info(
            "Issue %d in %s repo_short_name corresponds to '%s'",
            issue_id,
            repo_short_name,
            branch_name,
        )
        if suffix != "":
            # Add the the suffix.
            _LOG.debug("Adding suffix '%s' to '%s'", suffix, branch_name)
            if suffix[0] in ("-", "_"):
                _LOG.warning(
                    "Suffix '%s' should not start with '%s': removing",
                    suffix,
                    suffix[0],
                )
                suffix = suffix.rstrip("-_")
            branch_name += "_" + suffix
    #
    _LOG.info("branch_name='%s'", branch_name)
    hdbg.dassert_ne(branch_name, "")
    # Check that the branch is not just a number.
    m = re.match(r"^\d+$", branch_name)
    hdbg.dassert(not m, "Branch names with only numbers are invalid")
    # The valid format of a branch name is `AmpTask1903_Implemented_system_...`.
    m = re.match(r"^\S+Task\d+_\S+$", branch_name)
    hdbg.dassert(m, "Branch name should be '{Amp,...}TaskXYZ_...'")
    hdbg.dassert(
        not hgit.does_branch_exist(branch_name, mode="all"),
        "The branch '%s' already exists",
        branch_name,
    )
    # Make sure we are branching from `master`, unless that's what the user wants.
    curr_branch = hgit.get_branch_name()
    if curr_branch != "master":
        if only_branch_from_master:
            hdbg.dfatal(
                f"You should branch from master and not from '{curr_branch}'"
            )
    # Fetch master.
    cmd = "git pull --autostash"
    _run(ctx, cmd)
    # git checkout -b LmTask169_Get_GH_actions_working_on_lm
    cmd = f"git checkout -b {branch_name}"
    _run(ctx, cmd)
    cmd = f"git push --set-upstream origin {branch_name}"
    _run(ctx, cmd)


# TODO(gp): Move to hgit.
def _delete_branches(ctx: Any, tag: str, confirm_delete: bool) -> None:
    if tag == "local":
        # Delete local branches that are already merged into master.
        # > git branch --merged
        # * AmpTask1251_Update_GH_actions_for_amp_02
        find_cmd = r"git branch --merged master | grep -v master | grep -v \*"
        delete_cmd = "git branch -d"
    elif tag == "remote":
        # Get the branches to delete.
        find_cmd = (
            "git branch -r --merged origin/master"
            + r" | grep -v master | sed 's/origin\///'"
        )
        delete_cmd = "git push origin --delete"
    else:
        raise ValueError(f"Invalid tag='{tag}'")
    # TODO(gp): Use system_to_lines
    _, txt = hsystem.system_to_string(find_cmd, abort_on_error=False)
    branches = hsystem.text_to_list(txt)
    # Print info.
    _LOG.info(
        "There are %d %s branches to delete:\n%s",
        len(branches),
        tag,
        "\n".join(branches),
    )
    if not branches:
        # No branch to delete, then we are done.
        return
    # Ask whether to continue.
    if confirm_delete:
        hsystem.query_yes_no(
            hdbg.WARNING + f": Delete these {tag} branches?", abort_on_no=True
        )
    for branch in branches:
        cmd_tmp = f"{delete_cmd} {branch}"
        _run(ctx, cmd_tmp)


@task
def git_delete_merged_branches(ctx, confirm_delete=True):  # type: ignore
    """
    Remove (both local and remote) branches that have been merged into master.
    """
    _report_task()
    hdbg.dassert(
        hgit.get_branch_name(),
        "master",
        "You need to be on master to delete dead branches",
    )
    #
    cmd = "git fetch --all --prune"
    _run(ctx, cmd)
    # Delete local and remote branches that are already merged into master.
    _delete_branches(ctx, "local", confirm_delete)
    _delete_branches(ctx, "remote", confirm_delete)
    #
    cmd = "git fetch --all --prune"
    _run(ctx, cmd)


@task
def git_rename_branch(ctx, new_branch_name):  # type: ignore
    """
    Rename current branch both locally and remotely.
    """
    _report_task()
    #
    old_branch_name = hgit.get_branch_name(".")
    hdbg.dassert_ne(old_branch_name, new_branch_name)
    msg = (
        f"Do you want to rename the current branch '{old_branch_name}' to "
        f"'{new_branch_name}'"
    )
    hsystem.query_yes_no(msg, abort_on_no=True)
    # https://stackoverflow.com/questions/30590083
    # Rename the local branch to the new name.
    # > git branch -m <old_name> <new_name>
    cmd = f"git branch -m {new_branch_name}"
    _run(ctx, cmd)
    # Delete the old branch on remote.
    # > git push <remote> --delete <old_name>
    cmd = f"git push origin --delete {old_branch_name}"
    _run(ctx, cmd)
    # Prevent Git from using the old name when pushing in the next step.
    # Otherwise, Git will use the old upstream name instead of <new_name>.
    # > git branch --unset-upstream <new_name>
    cmd = f"git branch --unset-upstream {new_branch_name}"
    _run(ctx, cmd)
    # Push the new branch to remote.
    # > git push <remote> <new_name>
    cmd = f"git push origin {new_branch_name}"
    _run(ctx, cmd)
    # Reset the upstream branch for the new_name local branch.
    # > git push <remote> -u <new_name>
    cmd = f"git push origin u {new_branch_name}"
    _run(ctx, cmd)
    print("Done")


@task
def git_branch_next_name(ctx):  # type: ignore
    """
    Return a name derived from the branch so that the branch doesn't exist.

    E.g., `AmpTask1903_Implemented_system_Portfolio` ->
    `AmpTask1903_Implemented_system_Portfolio_3`
    """
    _report_task()
    _ = ctx
    branch_next_name = hgit.get_branch_next_name(log_verb=logging.INFO)
    print(f"branch_next_name='{branch_next_name}'")


@task
def git_branch_copy(ctx, new_branch_name="", use_patch=False):  # type: ignore
    """
    Create a new branch with the same content of the current branch.
    """
    hdbg.dassert(not use_patch, "Patch flow not implemented yet")
    #
    curr_branch_name = hgit.get_branch_name()
    hdbg.dassert_ne(curr_branch_name, "master")
    # Make sure `old_branch_name` doesn't need to have `master` merged.
    cmd = "invoke git_merge_master --ff-only"
    _run(ctx, cmd)
    if use_patch:
        # TODO(gp): Create a patch or do a `git merge`.
        pass
    # If new_branch_name was not specified, find a new branch with the next index.
    if new_branch_name == "":
        new_branch_name = hgit.get_branch_next_name()
    _LOG.info("new_branch_name='%s'", new_branch_name)
    # Create or go to the new branch.
    mode = "all"
    new_branch_exists = hgit.does_branch_exist(new_branch_name, mode)
    if new_branch_exists:
        cmd = f"git checkout {new_branch_name}"
    else:
        cmd = f"git checkout master && invoke git_create_branch -b '{new_branch_name}'"
    _run(ctx, cmd)
    if use_patch:
        # TODO(gp): Apply the patch.
        pass
    #
    cmd = f"git merge --squash --ff {curr_branch_name} && git reset HEAD"
    _run(ctx, cmd)


def _git_diff_with_branch(
    ctx: Any,
    hash_: str,
    tag: str,
    dir_name: str,
    diff_type: str,
    subdir: str,
    extensions: str,
    dry_run: bool,
) -> None:
    _LOG.debug(
        hprint.to_str("hash_ tag dir_name diff_type subdir extensions dry_run")
    )
    # Check that this branch is not master.
    curr_branch_name = hgit.get_branch_name()
    hdbg.dassert_ne(curr_branch_name, "master")
    # Get the modified files.
    cmd = []
    cmd.append("git diff")
    if diff_type:
        cmd.append(f"--diff-filter={diff_type}")
    cmd.append(f"--name-only HEAD {hash_}")
    cmd = " ".join(cmd)
    files = hsystem.system_to_files(cmd, dir_name, remove_files_non_present=False)
    files = sorted(files)
    print("files=%s\n%s" % (len(files), "\n".join(files)))
    # Filter the files, if needed.
    if extensions:
        extensions_lst = extensions.split(",")
        _LOG.warning(
            "Requested filtering by %d extensions: %s",
            len(extensions_lst),
            extensions_lst,
        )
        files_tmp = []
        for f in files:
            if any(f.endswith(ext) for ext in extensions_lst):
                files_tmp.append(f)
        files = files_tmp
        print("# After filtering files=%s\n%s" % (len(files), "\n".join(files)))
    if len(files) == 0:
        _LOG.warning("Nothing to diff: exiting")
        return
    # Create the dir storing all the files to compare.
    dst_dir = f"./tmp.{tag}"
    hio.create_dir(dst_dir, incremental=False)
    # Retrieve the original file and create the diff command.
    script_txt = []
    for branch_file in files:
        _LOG.debug("\n%s", hprint.frame(f"branch_file={branch_file}"))
        # Check if it needs to be compared.
        if subdir != "":
            if not branch_file.startswith(subdir):
                _LOG.debug(
                    "Skipping since '%s' doesn't start with '%s'",
                    branch_file,
                    subdir,
                )
                continue
        # Get the file on the right of the vimdiff.
        if os.path.exists(branch_file):
            right_file = branch_file
        else:
            right_file = "/dev/null"
        # Flatten the file dirs: e.g.,
        # dataflow/core/nodes/test/test_volatility_models.base.py
        tmp_file = branch_file
        tmp_file = tmp_file.replace("/", "_")
        tmp_file = os.path.join(dst_dir, tmp_file)
        _LOG.debug(
            "branch_file='%s' exists in branch -> master_file='%s'",
            branch_file,
            tmp_file,
        )
        # Save the base file.
        cmd = f"git show {hash_}:{branch_file} >{tmp_file}"
        rc = hsystem.system(cmd, abort_on_error=False)
        if rc != 0:
            # For new files we get the error:
            # fatal: path 'dev_scripts/configure_env.sh' exists on disk, but
            # not in 'c92cfe4382325678fdfccd0ddcd1927008090602'
            _LOG.debug("branch_file='%s' doesn't exist in master", branch_file)
            left_file = "/dev/null"
        else:
            left_file = tmp_file
        # Update the script to diff.
        cmd = f"vimdiff {left_file} {right_file}"
        _LOG.debug("-> %s", cmd)
        script_txt.append(cmd)
    script_txt = "\n".join(script_txt)
    # Files to diff.
    print(hprint.frame("Diffing script"))
    print(script_txt)
    # Save the script to compare.
    script_file_name = f"./tmp.vimdiff_branch_with_{tag}.sh"
    msg = f"To diff against {tag} run"
    hio.create_executable_script(script_file_name, script_txt, msg=msg)
    _run(ctx, script_file_name, dry_run=dry_run, pty=True)


@task
def git_branch_diff_with_base(  # type: ignore
    ctx, diff_type="", subdir="", extensions="", dry_run=False
):
    """
    Diff files of the current branch with master at the branching point.

    :param diff_type: files to diff using git `--diff-filter` options
    :param subdir: subdir to consider for diffing, instead of `.`
    :param extensions: a comma-separated list of extensions to check, e.g.,
        'csv,py'. An empty string means all the files
    :param dry_run: execute diffing script or not
    """
    # Get the branching point.
    dir_name = "."
    hash_ = hgit.get_branch_hash(dir_name=dir_name)
    #
    tag = "base"
    _git_diff_with_branch(
        ctx, hash_, tag, dir_name, diff_type, subdir, extensions, dry_run
    )


@task
def git_branch_diff_with_master(  # type: ignore
    ctx, diff_type="", subdir="", extensions="", dry_run=False
):
    """
    Diff files of the current branch with origin/master.

    :param diff_type: files to diff using git `--diff-filter` options
    :param subdir: subdir to consider for diffing, instead of `.`
    :param extensions: a comma-separated list of extensions to check, e.g.,
        'csv,py'. An empty string means all the files
    :param dry_run: execute diffing script or not
    """
    dir_name = "."
    hash_ = "origin/master"
    tag = "origin_master"
    _git_diff_with_branch(
        ctx, hash_, tag, dir_name, diff_type, subdir, extensions, dry_run
    )


# pylint: disable=line-too-long

# TODO(gp): Add the following scripts:
# dev_scripts/git/git_backup.sh
# dev_scripts/git/gcl
# dev_scripts/git/git_branch.sh
# dev_scripts/git/git_branch_point.sh
# dev_scripts/create_class_diagram.sh

# #############################################################################
# Integrate.
# #############################################################################

# ## Concepts
#
# - We have two dirs storing two forks of the same repo
#   - Files are touched, e.g., added, modified, deleted in each forks
#   - The most problematic files are the files that are modified in both forks
#   - Files that are added or deleted in one fork, should be added / deleted also
#     in the other fork
# - Often we can integrate "by directory", i.e., finding entire directories that
#   we were touched in one branch but not the other
#   - In this case we can simply copy the entire dir from one dir to the other
# - Other times we need to integrate "by file"
#
# - There are various interesting Git reference points:
#   1) the branch point for each branch, at which the integration branch was started
#   2) the last integration point for each branch, at which the repos are the same,
#      or at least aligned

# ## Create integration branches
#
# - Pull master
#
# - Align `lib_tasks.py`:
#   ```
#   > vimdiff ~/src/{amp1,cmamp1}/tasks.py; vimdiff ~/src/{amp1,cmamp1}/helpers/lib_tasks.py
#   ```
#
# - Create the integration branches
#   ```
#   > cd amp1
#   > i integrate_create_branch --dir-basename amp1
#   > cd cmamp1
#   > i integrate_create_branch --dir-basename cmamp1
#   ```

# ## Preparation
#
# - Lint both dirs:
#   ```
#   > cd amp1
#   > i lint --dir-name . --only-format
#   > cd cmamp1
#   > i lint --dir-name . --only-format
#   ```
#   or at least the files touched by both repos:
#   ```
#   > i integrate_files --file-direction only_files_in_src
#   > cat tmp.integrate_find_files_touched_since_last_integration.cmamp1.txt tmp.integrate_find_files_touched_since_last_integration.amp1.txt | sort | uniq >files.txt
#   > FILES=$(cat files.txt)
#   > i lint --only-format -f "$FILES"
#   ```
#
# - Add end-of-file:
#   ```
#   > find . -name "*.py" -o -name "*.txt" -o -name "*.json" | xargs sed -i '' -e '$a\'
#
#   # Remove end-of-file.
#   > find . -name "*.txt" | xargs perl -pi -e 'chomp if eof'
#   ```

# ## Integration
#
# - Check what files were modified since the last integration in each fork:
#   ```
#   > i integrate_files --file-direction common_files
#   > i integrate_files --file-direction only_files_in_src
#   > i integrate_files --file-direction only_files_in_dst
#   ```
#
# - Look for directory touched on only one branch:
#   ```
#   > i integrate_files --file-direction common_files --mode "print_dirs"
#   > i integrate_files --file-direction only_files_in_src --mode "print_dirs"
#   > i integrate_files --file-direction only_files_in_dst --mode "print_dirs"
#   ```
# - If we find dirs that are touched in one branch but not in the other
#   we can copy / merge without running risks
#   ```
#   > i integrate_diff_dirs --subdir $SUBDIR -c
#   ```
#
# - Check which files are different between the dirs:
#   ```
#   > i integrate_diff_dirs
#   ```
#
# - Diff dir by dir
#   ```
#   > i integrate_diff_dirs --subdir dataflow/system
#   ```
#
# - Copy by dir
#   ```
#   > i integrate_diff_dirs --subdir market_data -c
#   ```
#
# - Remove the empty files
#   ```
#   > find . -type f -empty -print | grep -v .git | grep -v __init__ | grep -v ".log$" | grep -v ".txt$" | xargs git rm
#   ```

# ## Double check the integration
#
# - Check that the regressions are passing on GH
#   ```
#   > i gh_create_pr --no-draft
#   ```
#
# - Check the files that were changed in both branches (i.e., the "problematic ones")
#   since the last integration and compare them to the base in each branch
#   ```
#   > cd amp1
#   > i integrate_diff_overlapping_files --src-dir "amp1" --dst-dir "cmamp1"
#   > cd cmamp1
#   > i integrate_diff_overlapping_files --src-dir "cmamp1" --dst-dir "amp1"
#   ```
#
# - Quickly scan all the changes in the branch compared to the base
#   ```
#   > cd amp1
#   > i git_branch_diff_with_base
#   > cd cmamp1
#   > i git_branch_diff_with_base
#   ```


# Invariants for the integration set-up
#
# - The user runs commands in a abs_dir, e.g., `/Users/saggese/src/{amp1,cmamp1}`
# - The user refers in the command line to `dir_basename`, which is the basename of
#   the integration directories (e.g., `amp1`, `cmamp1`)
#   - The "src_dir_basename" is the one where the command is issued
#   - The "dst_dir_basename" is assumed to be parallel to the "src_dir_basename"
# - The dirs are then transformed in absolute dirs "abs_src_dir"


def _dassert_current_dir_matches(expected_dir_basename: str) -> None:
    """
    Ensure that the name of the current dir is the one expected.

    E.g., `/Users/saggese/src/cmamp1` is a valid dir for an integration
    branch for `cmamp1`.
    """
    _LOG.debug(hprint.to_str("expected_dir_basename"))
    # Get the basename of the current dir.
    curr_dir_basename = os.path.basename(os.getcwd())
    # Check that it's what is expected.
    hdbg.dassert_eq(
        curr_dir_basename,
        expected_dir_basename,
        "The current dir '%s' doesn't match the expected dir '%s'",
        curr_dir_basename,
        expected_dir_basename,
    )


# TODO(gp): -> _dassert_is_integration_dir
def _dassert_is_integration_branch(abs_dir: str) -> None:
    """
    Ensure that the branch in `abs_dir` is a valid integration or lint branch.

    E.g., `AmpTask1786_Integrate_20220402` is a valid integration
    branch.
    """
    _LOG.debug(hprint.to_str("abs_dir"))
    branch_name = hgit.get_branch_name(dir_name=abs_dir)
    hdbg.dassert_ne(branch_name, "master")
    hdbg.dassert(
        ("_Integrate_" in branch_name) or ("_Lint_" in branch_name),
        "Invalid branch_name='%s' in abs_dir='%s'",
        branch_name,
        abs_dir,
    )


def _clean_both_integration_dirs(abs_dir1: str, abs_dir2: str) -> None:
    """
    Run `i git_clean` on the passed dirs.

    :param abs_dir1, abs_dir2: full paths of the dirs to clean
    """
    _LOG.debug(hprint.to_str("abs_dir1 abs_dir2"))
    #
    cmd = f"cd {abs_dir1} && invoke git_clean"
    hsystem.system(cmd)
    #
    cmd = f"cd {abs_dir2} && invoke git_clean"
    hsystem.system(cmd)


@task
def integrate_create_branch(ctx, dir_basename, dry_run=False):  # type: ignore
    """
    Create the branch for integration of `dir_basename` (e.g., amp1) in the
    current dir.

    :param dir_basename: specify the dir name (e.g., `amp1`) to ensure the set-up is
        correct.
    """
    _report_task()
    # Check that the current dir has the name `dir_basename`.
    _dassert_current_dir_matches(dir_basename)
    # Create the integration branch with the current date, e.g.,
    # `AmpTask1786_Integrate_20211231`.
    date = datetime.datetime.now().date()
    date_as_str = date.strftime("%Y%m%d")
    branch_name = f"AmpTask1786_Integrate_{date_as_str}"
    # query_yes_no("Are you sure you want to create the branch ")
    _LOG.info("Creating branch '%s'", branch_name)
    cmd = f"invoke git_create_branch -b '{branch_name}'"
    _run(ctx, cmd, dry_run=dry_run)


# //////////////////////////////////////////////////////////////////////////////


def _resolve_src_dst_names(
    src_dir_basename: str, dst_dir_basename: str, subdir: str
) -> Tuple[str, str]:
    """
    Return the full path of `src_dir_basename` and `dst_dir_basename`.

    :param src_dir_basename: the current dir (e.g., `amp1`)
    :param dst_dir_basename: a dir parallel to the current one (`cmamp1`)

    :return: absolute paths of both directories
    """
    curr_parent_dir = os.path.dirname(os.getcwd())
    #
    abs_src_dir = os.path.join(curr_parent_dir, src_dir_basename, subdir)
    abs_src_dir = os.path.normpath(abs_src_dir)
    hdbg.dassert_dir_exists(abs_src_dir)
    #
    abs_dst_dir = os.path.join(curr_parent_dir, dst_dir_basename, subdir)
    abs_dst_dir = os.path.normpath(abs_dst_dir)
    hdbg.dassert_dir_exists(abs_dst_dir)
    return abs_src_dir, abs_dst_dir


@task
def integrate_diff_dirs(  # type: ignore
    ctx,
    src_dir_basename="amp1",
    dst_dir_basename="cmamp1",
    reverse=False,
    subdir="",
    copy=False,
    use_linux_diff=False,
    check_branches=True,
    clean_branches=True,
    remove_usual=False,
    dry_run=False,
):
    """
    Integrate repos from dirs `src_dir_basename` to `dst_dir_basename` by diffing
    or copying all the files with differences.

    ```
    # Use the default values for src / dst dirs to represent the usual set-up.
    > i integrate_diff_dirs \
        --src-dir-basename amp1 \
        --dst-dir-basename cmamp1 \
        --subdir .
    ```

    :param src_dir_basename: dir with the source branch (e.g., amp1)
    :param dst_dir_basename: dir with the destination branch (e.g., cmamp1)
    :param reverse: switch the roles of the default source and destination branches
    :param subdir: filter to the given subdir for both dirs (e.g.,
        `src_dir_basename/subdir` and `dst_dir_basename/subdir`)
    :param copy: copy the files instead of diffing
    :param use_linux_diff: use Linux `diff` instead of `diff_to_vimdiff.py`
    :param remove_usual: remove the usual mismatching files (e.g., `.github`)
    """
    _report_task()
    if reverse:
        src_dir_basename, dst_dir_basename = dst_dir_basename, src_dir_basename
        _LOG.warning(
            "Reversing dirs: %s",
            hprint.to_str2(src_dir_basename, dst_dir_basename),
        )
    # Check that the integration branches are in the expected state.
    #_dassert_current_dir_matches(src_dir_basename)
    abs_src_dir, abs_dst_dir = _resolve_src_dst_names(
        src_dir_basename, dst_dir_basename, subdir
    )
    if check_branches:
        _dassert_is_integration_branch(abs_src_dir)
        _dassert_is_integration_branch(abs_dst_dir)
    else:
        _LOG.warning("Skipping integration branch check")
    # Clean branches if needed.
    if clean_branches:
        # We can clean up only the root dir.
        if subdir == "":
            _clean_both_integration_dirs(abs_src_dir, abs_dst_dir)
    else:
        _LOG.warning("Skipping integration branch cleaning")
    # Copy or diff dirs.
    _LOG.info("abs_src_dir=%s", abs_src_dir)
    _LOG.info("abs_dst_dir=%s", abs_dst_dir)
    hdbg.dassert_ne(abs_src_dir, abs_dst_dir)
    if copy:
        # Copy the files.
        if dry_run:
            cmd = f"diff -r --brief {abs_src_dir} {abs_dst_dir}"
        else:
            rsync_opts = "--delete -a"
            cmd = f"rsync {rsync_opts} {abs_src_dir}/ {abs_dst_dir}"
    else:
        # Diff the files.
        if use_linux_diff:
            cmd = f"diff -r --brief {abs_src_dir} {abs_dst_dir}"
        else:
            cmd = f"dev_scripts/diff_to_vimdiff.py --dir1 {abs_src_dir} --dir2 {abs_dst_dir}"
            if remove_usual:
                vals = ["\/\.github\/",
                        ]
                regex = "|".join(vals)
                cmd += f" --ignore_files=\'{regex}\'"
    _run(ctx, cmd, dry_run=dry_run, print_cmd=True)


# //////////////////////////////////////////////////////////////////////////////


def _find_files_touched_since_last_integration(
    abs_dir: str, subdir: str
) -> List[str]:
    """
    Return the list of files modified since the last integration for `abs_dir`.

    :param abs_dir: directory to cd before executing this script
    :param subdir: consider only the files under `subdir`
    """
    _LOG.debug(hprint.to_str2(abs_dir))
    dir_basename = os.path.basename(abs_dir)
    # TODO(gp): dir_basename can be computed from abs_dir_name to simplify the
    #  interface.
    # Change the dir to the correct one.
    old_dir = os.getcwd()
    try:
        os.chdir(abs_dir)
        # Find the hash of all integration commits.
        cmd = "git log --date=local --oneline --date-order | grep AmpTask1786_Integrate"
        # Remove integrations like "'... Merge branch 'master' into AmpTask1786_Integrate_20220113'"
        cmd += " | grep -v \"Merge branch 'master' into \""
        _, txt = hsystem.system_to_string(cmd)
        _LOG.debug("integration commits=\n%s", txt)
        txt = txt.split("\n")
        # > git log --date=local --oneline --date-order | grep AmpTask1786_Integrate
        # 72a1a101 AmpTask1786_Integrate_20211218 (#1975)
        # 2acfd6d7 AmpTask1786_Integrate_20211214 (#1950)
        # 318ab0ff AmpTask1786_Integrate_20211210 (#1933)
        hdbg.dassert_lte(2, len(txt))
        print(f"# last_integration: '{txt[0]}'")
        last_integration_hash = txt[0].split()[0]
        print("* " + hprint.to_str("last_integration_hash"))
        # Find the first commit after the commit with the last integration.
        cmd = f"git log --oneline --reverse --ancestry-path {last_integration_hash}^..master"
        _, txt = hsystem.system_to_string(cmd)
        print(f"* commits after last integration=\n{txt}")
        txt = txt.split("\n")
        # > git log --oneline --reverse --ancestry-path 72a1a101^..master
        # 72a1a101 AmpTask1786_Integrate_20211218 (#1975)
        # 90e90353 AmpTask1955_Lint_20211218 (#1976)
        # 4a2b45c6 AmpTask1858_Implement_buildmeister_workflows_in_invoke (#1860)
        hdbg.dassert_lte(2, len(txt))
        first_commit_hash = txt[1].split()[0]
        _LOG.debug("first_commit: '%s'", txt[1])
        _LOG.debug(hprint.to_str("first_commit_hash"))
        # Find all the files touched in each branch.
        cmd = f"git diff --name-only {first_commit_hash}..HEAD"
        _, txt = hsystem.system_to_string(cmd)
        files: List[str] = txt.split("\n")
    finally:
        os.chdir(old_dir)
    _LOG.debug("Files modified since the integration=\n%s", "\n".join(files))
    # Filter files by subdir, if needed.
    if subdir:
        filtered_files = []
        for file in files:
            if file.startswith(subdir):
                filtered_files.append(file)
        files = filtered_files
    # Reorganize the files.
    hdbg.dassert_no_duplicates(files)
    files = sorted(files)
    # Save to file for debugging.
    file_name = os.path.join(
        f"tmp.integrate_find_files_touched_since_last_integration.{dir_basename}.txt"
    )
    hio.to_file(file_name, "\n".join(files))
    _LOG.debug("Saved file to '%s'", file_name)
    return files


@task
def integrate_find_files_touched_since_last_integration(  # type: ignore
    ctx,
    subdir="",
):
    """
    Print the list of files modified since the last integration for this dir.
    """
    _report_task()
    abs_dir = os.getcwd()
    _ = ctx
    files = _find_files_touched_since_last_integration(abs_dir, subdir)
    # Print the result.
    tag = "Files modified since the integration"
    print(hprint.frame(tag))
    print("\n".join(files))


# //////////////////////////////////////////////////////////////////////////////


def _integrate_files(
    files: Set[str],
    abs_left_dir: str,
    abs_right_dir: str,
    only_different_files: bool,
) -> List[Tuple[str, str, str]]:
    """
    Build a list of files to compare based on the pattern.

    :param files: relative path of the files to compare
    :param abs_left_dir, abs_right_dir: path of the left / right dir
    :param only_different_files: include in the script only the files that are
        different
    :return: list of files to compare
    """
    _LOG.debug(hprint.to_str("abs_left_dir abs_right_dir only_different_files"))
    files_to_diff: List[Tuple[str, str, str]] = []
    for file in sorted(list(files)):
        _LOG.debug(hprint.to_str("file"))
        left_file = os.path.join(abs_left_dir, file)
        right_file = os.path.join(abs_right_dir, file)
        # Check if both the files exist and are the same.
        both_exist = os.path.exists(left_file) and os.path.exists(right_file)
        if not both_exist:
            # Both files don't exist: nothing to do.
            equal: Optional[bool] = False
            skip: Optional[bool] = True
        else:
            # They both exist.
            if only_different_files:
                # We want to check if they are the same.
                equal = hio.from_file(left_file) == hio.from_file(right_file)
                skip = equal
            else:
                # They both exists and we want to process even if they are the same.
                equal = None
                skip = False
        _ = left_file, right_file, both_exist, equal, skip
        _LOG.debug(hprint.to_str("left_file right_file both_exist equal skip"))
        # Execute the action on the 2 files.
        if skip:
            _LOG.debug("  Skip %s", file)
        else:
            _LOG.debug("  -> (%s, %s)", left_file, right_file)
            files_to_diff.append((file, left_file, right_file))
    return files_to_diff


@task
def integrate_files(  # type: ignore
    ctx,
    src_dir_basename="amp1",
    dst_dir_basename="cmamp1",
    reverse=False,
    subdir="",
    mode="vimdiff",
    file_direction="",
    only_different_files=True,
    check_branches=True,
):
    """
    Find and copy the files that are touched only in one branch or in both.

    :param src_dir_basename: dir with the source branch (e.g., amp1)
    :param dst_dir_basename: dir with the destination branch (e.g., cmamp1)
    :param reverse: switch the roles of the default source and destination branches
    :param mode:
        - "print_dirs": print the directories
        - "vimdiff": diff the files
        - "copy": copy the files
    :param file_direction: which files to diff / copy:
        - "common_files": files touched in both branches
        - "union_files": files touched in either branch
        - "only_files_in_src": files touched only in the src dir
        - "only_files_in_dst": files touched only in the dst dir
    :param only_different_files: consider only the files that are different among
        the branches
    """
    _report_task()
    _ = ctx
    if reverse:
        src_dir_basename, dst_dir_basename = dst_dir_basename, src_dir_basename
        _LOG.warning(
            "Reversing dirs: %s",
            hprint.to_str2(src_dir_basename, dst_dir_basename),
        )
    # Check that the integration branches are in the expected state.
    _dassert_current_dir_matches(src_dir_basename)
    # We want to stay at the top level dir, since the subdir is handled by
    # `integrate_find_files_touched_since_last_integration`.
    abs_src_dir, abs_dst_dir = _resolve_src_dst_names(
        src_dir_basename, dst_dir_basename, subdir=""
    )
    if check_branches:
        _dassert_is_integration_branch(abs_src_dir)
        _dassert_is_integration_branch(abs_dst_dir)
    else:
        _LOG.warning("Skipping integration branch check")
    # Find the files touched in each branch since the last integration.
    src_files = set(
        _find_files_touched_since_last_integration(abs_src_dir, subdir)
    )
    dst_files = set(
        _find_files_touched_since_last_integration(abs_dst_dir, subdir)
    )
    #
    if file_direction == "common_files":
        files = src_files.intersection(dst_files)
    elif file_direction == "only_files_in_src":
        files = src_files - dst_files
    elif file_direction == "only_files_in_dst":
        files = dst_files - src_files
    elif file_direction == "union_files":
        files = src_files.union(dst_files)
    else:
        raise ValueError(f"Invalid file_direction='{file_direction}'")
    #
    files_to_diff = _integrate_files(
        files,
        abs_src_dir,
        abs_dst_dir,
        only_different_files,
    )
    # Print the files.
    print(hprint.frame(file_direction))
    _LOG.debug(hprint.to_str("files_to_diff"))
    files_set = list(zip(*files_to_diff))
    if not files_set:
        _LOG.warning("No file found: skipping")
        return
    files_set = sorted(list(files_set[0]))
    txt = "\n".join(files_set)
    print(hprint.indent(txt))
    # Process the files touched.
    if mode == "print_dirs":
        files_lst = []
        for file, left_file, right_file in files_to_diff:
            dirname = os.path.dirname(file)
            # Skip empty dir, e.g., for `pytest.ini`.
            if dirname != "":
                files_lst.append(dirname)
        files_lst = sorted(list(set(files_lst)))
        print(hprint.frame("Dirs changed"))
        print("\n".join(files_lst))
    else:
        # Build the script with the operations to perform.
        script_txt = []
        for file, left_file, right_file in files_to_diff:
            if mode == "copy":
                cmd = f"cp -f {left_file} {right_file}"
            elif mode == "vimdiff":
                cmd = f"vimdiff {left_file} {right_file}"
            else:
                raise ValueError(f"Invalid mode='{mode}'")
            _LOG.debug("  -> %s", cmd)
            script_txt.append(cmd)
        script_txt = "\n".join(script_txt)
        # Execute / save the script.
        if mode == "copy":
            for cmd in script_txt:
                hsystem.system(cmd)
        elif mode == "vimdiff":
            # Save the diff script.
            script_file_name = f"./tmp.vimdiff.{file_direction}.sh"
            hio.create_executable_script(script_file_name, script_txt)
            print(f"# To diff run:\n> {script_file_name}")
        else:
            raise ValueError(f"Invalid mode='{mode}'")


@task
def integrate_find_files(  # type: ignore
    ctx,
    subdir="",
):
    """
    Find the files that are touched in the current branch since last
    integration.
    """
    _report_task()
    _ = ctx
    #
    abs_src_dir = "."
    abs_src_dir = os.path.normpath(abs_src_dir)
    hdbg.dassert_dir_exists(abs_src_dir)
    # Find the files touched in each branch since the last integration.
    src_files = sorted(
        _find_files_touched_since_last_integration(abs_src_dir, subdir)
    )
    print("* Files touched:\n%s" % "\n".join(src_files))


@task
def integrate_diff_overlapping_files(  # type: ignore
    ctx, src_dir_basename, dst_dir_basename, subdir=""
):
    """
    Find the files modified in both branches `src_dir_basename` and
    `dst_dir_basename` Compare these files from HEAD to master version before
    the branch point.

    This is used to check what changes were made to files modified by
    both branches.
    """
    _report_task()
    _ = ctx
    # Check that the integration branches are in the expected state.
    _dassert_current_dir_matches(src_dir_basename)
    src_dir_basename, dst_dir_basename = _resolve_src_dst_names(
        src_dir_basename, dst_dir_basename, subdir
    )
    _dassert_is_integration_branch(src_dir_basename)
    _dassert_is_integration_branch(dst_dir_basename)
    _clean_both_integration_dirs(src_dir_basename, dst_dir_basename)
    # Find the files modified in both branches.
    src_hash = hgit.get_branch_hash(src_dir_basename)
    _LOG.info("src_hash=%s", src_hash)
    dst_hash = hgit.get_branch_hash(dst_dir_basename)
    _LOG.info("dst_hash=%s", dst_hash)
    diff_files1 = os.path.abspath("./tmp.files_modified1.txt")
    diff_files2 = os.path.abspath("./tmp.files_modified2.txt")
    cmd = f"cd {src_dir_basename} && git diff --name-only {src_hash} HEAD >{diff_files1}"
    hsystem.system(cmd)
    cmd = f"cd {dst_dir_basename} && git diff --name-only {dst_hash} HEAD >{diff_files2}"
    hsystem.system(cmd)
    common_files = "./tmp.common_files.txt"
    cmd = f"comm -12 {diff_files1} {diff_files2} >{common_files}"
    hsystem.system(cmd)
    # Get the base files to diff.
    files = hio.from_file(common_files).split("\n")
    files = [f for f in files if f != ""]
    _LOG.info("Found %d files to diff:\n%s", len(files), "\n".join(files))
    # Retrieve the original file and create the diff command.
    script_txt = []
    for src_file in files:
        hdbg.dassert_file_exists(src_file)
        # TODO(gp): Add function to add a suffix to a name, using
        #  os.path.dirname(), os.path.basename(), os.path.split_extension().
        dst_file = src_file.replace(".py", ".base.py")
        # Save the base file.
        cmd = f"git show {src_hash}:{src_file} >{dst_file}"
        rc = hsystem.system(cmd, abort_on_error=False)
        if rc == 0:
            # The file was created: nothing to do.
            pass
        elif rc == 128:
            # Note that the file potentially could not exist, i.e., it was added
            # in the branch. In this case Git returns:
            # ```
            # rc=128 fatal: path 'dataflow/pipelines/real_time/test/
            # test_dataflow_pipelines_real_time_pipeline.py' exists on disk, but
            # not in 'ce54877016204315766e90df7c45192bec1fbf20'
            src_file = "/dev/null"
        else:
            raise ValueError(f"cmd='{cmd}' returned {rc}")
        # Update the script to diff.
        script_txt.append(f"vimdiff {dst_file} {src_file}")
    # Save the script to compare.
    script_file_name = "./tmp.vimdiff_overlapping_files.sh"
    script_txt = "\n".join(script_txt)
    hio.create_executable_script(script_file_name, script_txt)
    print(f"# To diff against the base run:\n> {script_file_name}")


# #############################################################################
# Basic Docker commands.
# #############################################################################


def _get_docker_exec(sudo: bool) -> str:
    docker_exec = "docker"
    if sudo:
        docker_exec = "sudo " + docker_exec
    return docker_exec


@task
def docker_images_ls_repo(ctx, sudo=False):  # type: ignore
    """
    List images in the logged in repo_short_name.
    """
    _report_task()
    docker_login(ctx)
    ecr_base_path = get_default_param("AM_ECR_BASE_PATH")
    docker_exec = _get_docker_exec(sudo)
    _run(ctx, f"{docker_exec} image ls {ecr_base_path}")


@task
def docker_ps(ctx, sudo=False):  # type: ignore
    # pylint: disable=line-too-long
    """
    List all the running containers.

    ```
    > docker_ps
    CONTAINER ID  user  IMAGE                    COMMAND                    CREATED        STATUS        PORTS  service
    2ece37303ec9  gp    *****....:latest  "./docker_build/entry.sh"  5 seconds ago  Up 4 seconds         user_space
    ```
    """
    _report_task()
    # pylint: enable=line-too-long
    fmt = (
        r"""table {{.ID}}\t{{.Label "user"}}\t{{.Image}}\t{{.Command}}"""
        + r"\t{{.RunningFor}}\t{{.Status}}\t{{.Ports}}"
        + r'\t{{.Label "com.docker.compose.service"}}'
    )
    docker_exec = _get_docker_exec(sudo)
    cmd = f"{docker_exec} ps --format='{fmt}'"
    cmd = _to_single_line_cmd(cmd)
    _run(ctx, cmd)


def _get_last_container_id(sudo: bool) -> str:
    docker_exec = _get_docker_exec(sudo)
    # Get the last started container.
    cmd = f"{docker_exec} ps -l | grep -v 'CONTAINER ID'"
    # CONTAINER ID   IMAGE          COMMAND                  CREATED
    # 90897241b31a   eeb33fe1880a   "/bin/sh -c '/bin/bash ...
    _, txt = hsystem.system_to_one_line(cmd)
    # Parse the output: there should be at least one line.
    hdbg.dassert_lte(1, len(txt.split(" ")), "Invalid output='%s'", txt)
    container_id: str = txt.split(" ")[0]
    return container_id


@task
def docker_stats(  # type: ignore
    ctx,
    all=False,  # pylint: disable=redefined-builtin
    sudo=False,
):
    # pylint: disable=line-too-long
    """
    Report last started Docker container stats, e.g., CPU, RAM.

    ```
    > docker_stats
    CONTAINER ID  NAME                   CPU %  MEM USAGE / LIMIT     MEM %  NET I/O         BLOCK I/O        PIDS
    2ece37303ec9  ..._user_space_run_30  0.00%  15.74MiB / 31.07GiB   0.05%  351kB / 6.27kB  34.2MB / 12.3kB  4
    ```

    :param all: report stats for all the containers
    """
    # pylint: enable=line-too-long
    _report_task(txt=hprint.to_str("all"))
    _ = ctx
    fmt = (
        r"table {{.ID}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        + r"\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"
    )
    docker_exec = _get_docker_exec(sudo)
    cmd = f"{docker_exec} stats --no-stream --format='{fmt}'"
    _, txt = hsystem.system_to_string(cmd)
    if all:
        output = txt
    else:
        # Get the id of the last started container.
        container_id = _get_last_container_id(sudo)
        print(f"Last container id={container_id}")
        # Parse the output looking for the given container.
        txt = txt.split("\n")
        output = []
        # Save the header.
        output.append(txt[0])
        for line in txt[1:]:
            if line.startswith(container_id):
                output.append(line)
        # There should be at most two rows: the header and the one corresponding to
        # the container.
        hdbg.dassert_lte(
            len(output), 2, "Invalid output='%s' for '%s'", output, txt
        )
        output = "\n".join(output)
    print(output)


@task
def docker_kill(  # type: ignore
    ctx,
    all=False,  # pylint: disable=redefined-builtin
    sudo=False,
):
    """
    Kill the last Docker container started.

    :param all: kill all the containers (be careful!)
    :param sudo: use sudo for the Docker commands
    """
    _report_task(txt=hprint.to_str("all"))
    docker_exec = _get_docker_exec(sudo)
    # Last container.
    opts = "-l"
    if all:
        _LOG.warning("Killing all the containers")
        # TODO(gp): Ask if we are sure and add a --just-do-it option.
        opts = "-a"
    # Print the containers that will be terminated.
    cmd = f"{docker_exec} ps {opts}"
    _run(ctx, cmd)
    # Kill.
    cmd = f"{docker_exec} rm -f $({docker_exec} ps {opts} -q)"
    _run(ctx, cmd)


# docker system prune
# docker container ps -f "status=exited"
# docker container rm $(docker container ps -f "status=exited" -q)
# docker rmi $(docker images --filter="dangling=true" -q)

# pylint: disable=line-too-long
# Remove the images with hash
# > docker image ls
# REPOSITORY                                        TAG                                        IMAGE ID       CREATED         SIZE
# *****.dkr.ecr.us-east-2.amazonaws.com/im          07aea615a2aa9290f7362e99e1cc908876700821   d0889bf972bf   6 minutes ago   684MB
# *****.dkr.ecr.us-east-2.amazonaws.com/im          rc                                         d0889bf972bf   6 minutes ago   684MB
# python                                            3.7-slim-buster                            e7d86653f62f   14 hours ago    113MB
# *****.dkr.ecr.us-east-1.amazonaws.com/dev_tools   ce789e4718175fcdf6e4857581fef1c2a5ee81f3   2f64ade2c048   14 hours ago    2.02GB
# *****.dkr.ecr.us-east-1.amazonaws.com/dev_tools   local                                      2f64ade2c048   14 hours ago    2.02GB
# *****.dkr.ecr.us-east-1.amazonaws.com/dev_tools   d401a2a0bef90b9f047c65f8adb53b28ba05d536   1b11bf234c7f   15 hours ago    2.02GB
# *****.dkr.ecr.us-east-1.amazonaws.com/dev_tools   52ccd63edbc90020f450c074b7c7088a1806c5ac   90b70a55c367   15 hours ago    1.95GB
# *****.dkr.ecr.us-east-1.amazonaws.com/dev_tools   2995608a7d91157fc1a820869a6d18f018c3c598   0cb3858e85c6   15 hours ago    2.01GB
# *****.dkr.ecr.us-east-1.amazonaws.com/amp         415376d58001e804e840bf3907293736ad62b232   e6ea837ab97f   18 hours ago    1.65GB
# *****.dkr.ecr.us-east-1.amazonaws.com/amp         dev                                        e6ea837ab97f   18 hours ago    1.65GB
# *****.dkr.ecr.us-east-1.amazonaws.com/amp         local                                      e6ea837ab97f   18 hours ago    1.65GB
# *****.dkr.ecr.us-east-1.amazonaws.com/amp         9586cc2de70a4075b9fdcdb900476f8a0f324e3e   c75d2447da79   18 hours ago    1.65GB
# pylint: enable=line-too-long


# #############################################################################
# Docker development.
# #############################################################################

# TODO(gp): We might want to organize the code in a base class using a Command
# pattern, so that it's easier to generalize the code for multiple repos.
#
# class DockerCommand:
#   def pull():
#     ...
#   def cmd():
#     ...
#
# For now we pass the customizable part through the default params.


def _docker_pull(
    ctx: Any, base_image: str, stage: str, version: Optional[str]
) -> None:
    """
    Pull images from the registry.
    """
    docker_login(ctx)
    #
    image = get_image(base_image, stage, version)
    _LOG.info("image='%s'", image)
    _dassert_is_image_name_valid(image)
    cmd = f"docker pull {image}"
    _run(ctx, cmd, pty=True)


@task
def docker_pull(ctx, stage="dev", version=None):  # type: ignore
    """
    Pull latest dev image corresponding to the current repo from the registry.
    """
    _report_task()
    #
    base_image = ""
    _docker_pull(ctx, base_image, stage, version)


@task
def docker_pull_dev_tools(ctx, stage="prod", version=None):  # type: ignore
    """
    Pull latest prod image of `dev_tools` from the registry.
    """
    _report_task()
    #
    base_image = get_default_param("AM_ECR_BASE_PATH") + "/dev_tools"
    _docker_pull(ctx, base_image, stage, version)


@functools.lru_cache()
def _get_aws_cli_version() -> int:
    # > aws --version
    # aws-cli/1.19.49 Python/3.7.6 Darwin/19.6.0 botocore/1.20.49
    # aws-cli/1.20.1 Python/3.9.5 Darwin/19.6.0 botocore/1.20.106
    cmd = "aws --version"
    res = hsystem.system_to_one_line(cmd)[1]
    # Parse the output.
    m = re.match(r"aws-cli/((\d+)\.\d+\.\d+)\s", res)
    hdbg.dassert(m, "Can't parse '%s'", res)
    m: Match[Any]
    version = m.group(1)
    _LOG.debug("version=%s", version)
    major_version = int(m.group(2))
    _LOG.debug("major_version=%s", major_version)
    return major_version


@task
def docker_login(ctx):  # type: ignore
    """
    Log in the AM Docker repo_short_name on AWS.
    """
    _report_task()
    if hsystem.is_inside_ci():
        _LOG.warning("Running inside GitHub Action: skipping `docker_login`")
        return
    major_version = _get_aws_cli_version()
    # docker login \
    #   -u AWS \
    #   -p eyJ... \
    #   -e none \
    #   https://*****.dkr.ecr.us-east-1.amazonaws.com
    # TODO(gp): We should get this programmatically from ~/aws/.credentials
    region = "us-east-1"
    if major_version == 1:
        cmd = f"eval $(aws ecr get-login --profile am --no-include-email --region {region})"
    else:
        ecr_base_path = get_default_param("AM_ECR_BASE_PATH")
        cmd = (
            f"docker login -u AWS -p $(aws ecr get-login --region {region}) "
            + f"https://{ecr_base_path}"
        )
    # cmd = ("aws ecr get-login-password" +
    #       " | docker login --username AWS --password-stdin "
    # TODO(Grisha): fix properly. We pass `ctx` despite the fact that we do not
    #  need it with `use_system=True`, but w/o `ctx` invoke tasks (i.e. ones
    #  with `@task` decorator) do not work.
    _run(ctx, cmd, use_system=True)


# ////////////////////////////////////////////////////////////////////////////////
# Compose files.
# ////////////////////////////////////////////////////////////////////////////////

# There are several combinations to consider:
# - whether the Docker host can run with / without privileged mode
# - amp as submodule / as supermodule
# - different supermodules for amp

# TODO(gp): use_privileged_mode -> use_docker_privileged_mode
#  use_sibling_container -> use_docker_containers_containers


def _generate_compose_file(
    use_privileged_mode: bool,
    use_sibling_container: bool,
    use_shared_cache: bool,
    mount_as_submodule: bool,
    use_network_mode_host: bool,
    file_name: Optional[str],
) -> str:
    _LOG.debug(
        hprint.to_str(
            "use_privileged_mode use_sibling_container "
            "use_shared_cache mount_as_submodule use_network_mode_host "
            "file_name"
        )
    )
    txt = []

    def append(txt_tmp: str, indent_level: int) -> None:
        # txt_tmp = txt_tmp.rstrip("\n").lstrip("\n")
        txt_tmp = hprint.dedent(txt_tmp, remove_empty_leading_trailing_lines=True)
        num_spaces = 2 * indent_level
        txt_tmp = hprint.indent(txt_tmp, num_spaces=num_spaces)
        txt.append(txt_tmp)

    # We could pass the env var directly, like:
    # ```
    # - AM_ENABLE_DIND=$AM_ENABLE_DIND
    # ```
    # but we prefer to inline it.
    if use_privileged_mode:
        am_enable_dind = 1
    else:
        am_enable_dind = 0
    # sysname='Linux'
    # nodename='cf-spm-dev4'
    # release='3.10.0-1160.53.1.el7.x86_64'
    # version='#1 SMP Fri Jan 14 13:59:45 UTC 2022'
    # machine='x86_64'
    am_host_os_name = os.uname()[0]
    am_host_name = os.uname()[1]
    # We could do the same also with IMAGE for symmetry.
    # Use % instead of f-string since `${IMAGE}` confuses f-string as a variable.
    # Keep the env vars in sync with what we print in entrypoint.sh.
    txt_tmp = """
    version: '3'

    services:
      base_app:
        cap_add:
          - SYS_ADMIN
        environment:
          - AM_AWS_PROFILE=$AM_AWS_PROFILE
          - AM_ECR_BASE_PATH=$AM_ECR_BASE_PATH
          - AM_ENABLE_DIND=%s
          - AM_FORCE_TEST_FAIL=$AM_FORCE_TEST_FAIL
          - AM_PUBLISH_NOTEBOOK_LOCAL_PATH=$AM_PUBLISH_NOTEBOOK_LOCAL_PATH
          - AM_AWS_S3_BUCKET=$AM_AWS_S3_BUCKET
          - AM_TELEGRAM_TOKEN=$AM_TELEGRAM_TOKEN
          - AM_HOST_NAME=%s
          - AM_HOST_OS_NAME=%s
          - AM_AWS_ACCESS_KEY_ID=$AM_AWS_ACCESS_KEY_ID
          - AM_AWS_DEFAULT_REGION=$AM_AWS_DEFAULT_REGION
          - AM_AWS_SECRET_ACCESS_KEY=$AM_AWS_SECRET_ACCESS_KEY
          - CK_AWS_PROFILE=$CK_AWS_PROFILE
          # - CK_ECR_BASE_PATH=$CK_ECR_BASE_PATH
          # - CK_ENABLE_DIND=
          # - CK_FORCE_TEST_FAIL=$CK_FORCE_TEST_FAIL
          # - CK_PUBLISH_NOTEBOOK_LOCAL_PATH=$CK_PUBLISH_NOTEBOOK_LOCAL_PATH
          - CK_AWS_S3_BUCKET=$CK_AWS_S3_BUCKET
          - CK_TELEGRAM_TOKEN=$CK_TELEGRAM_TOKEN
          # - CK_HOST_NAME=
          # - CK_HOST_OS_NAME=
          - CK_AWS_ACCESS_KEY_ID=$CK_AWS_ACCESS_KEY_ID
          - CK_AWS_DEFAULT_REGION=$CK_AWS_DEFAULT_REGION
          - CK_AWS_SECRET_ACCESS_KEY=$CK_AWS_SECRET_ACCESS_KEY
          - GH_ACTION_ACCESS_TOKEN=$GH_ACTION_ACCESS_TOKEN
          # This env var is used by GH Action to signal that we are inside the CI.
          - CI=$CI
        image: ${IMAGE}
    """ % (
        am_enable_dind,
        am_host_name,
        am_host_os_name,
    )
    indent_level = 0
    append(txt_tmp, indent_level)
    #
    if use_privileged_mode:
        txt_tmp = """
        # This is needed:
        # - for Docker-in-docker (dind)
        # - to mount fstabs
        privileged: true
        """
        # This is at the level of `services.app`.
        indent_level = 2
        append(txt_tmp, indent_level)
    #
    if True:
        txt_tmp = """
        restart: "no"
        volumes:
          # TODO(gp): We should pass the value of $HOME from dev.Dockerfile to here.
          # E.g., we might define $HOME in the env file.
          - ~/.aws:/home/.aws
          - ~/.config/gspread_pandas/:/home/.config/gspread_pandas/
          - ~/.config/gh:/home/.config/gh
        """
        # This is at the level of `services.app`.
        indent_level = 2
        append(txt_tmp, indent_level)
    #
    if use_shared_cache:
        # TODO(gp): Generalize by passing a dictionary.
        txt_tmp = """
        # Shared cache. This is specific of lime.
        - /local/home/share/cache:/cache
        """
        # This is at the level of `services.app.volumes`.
        indent_level = 3
        append(txt_tmp, indent_level)
    #
    if False:
        txt_tmp = """
        # No need to mount file systems.
        - ../docker_build/fstab:/etc/fstab
        """
        # This is at the level of `services.app.volumes`.
        indent_level = 3
        append(txt_tmp, indent_level)
    #
    if use_sibling_container:
        txt_tmp = """
        # Use sibling-container approach.
        - /var/run/docker.sock:/var/run/docker.sock
        """
        # This is at the level of `services.app.volumes`.
        indent_level = 3
        append(txt_tmp, indent_level)
    #
    if False:
        txt_tmp = """
        deploy:
          resources:
            limits:
              # This should be passed from command line depending on how much
              # memory is available.
              memory: 60G
        """
    #
    if mount_as_submodule:
        txt_tmp = """
        # Mount `amp` when it is used as submodule. In this case we need to
        # mount the super project in the container (to make git work with the
        # supermodule) and then change dir to `amp`.
        app:
          extends:
            base_app
          volumes:
            # Move one dir up to include the entire git repo (see AmpTask1017).
            - ../../../:/app
          # Move one dir down to include the entire git repo (see AmpTask1017).
          working_dir: /app/amp
        """
    else:
        txt_tmp = """
        # Mount `amp` when it is used as supermodule.
        app:
          extends:
            base_app
          volumes:
            - ../../:/app
        """
    # This is at the level of `services`.
    indent_level = 1
    append(txt_tmp, indent_level)
    #
    if use_network_mode_host:
        txt_tmp = """
        # Default network mode set to host so we can reach e.g.
        # a database container pointing to localhost:5432.
        # In tests we use dind so we need set back to the default "bridge".
        # See CmTask988 and https://stackoverflow.com/questions/24319662
        network_mode: ${NETWORK_MODE:-host}
        """
        # This is at the level of `services/app`.
        indent_level = 2
        append(txt_tmp, indent_level)
    #
    if True:
        txt_tmp = """
        jupyter_server:
          command: devops/docker_run/run_jupyter_server.sh
          environment:
            - PORT=${PORT}
          extends:
            app
          network_mode: ${NETWORK_MODE:-bridge}
          ports:
            # TODO(gp): Rename `AM_PORT`.
            - "${PORT}:${PORT}"

        # TODO(gp): For some reason the following doesn't work.
        #  jupyter_server_test:
        #    command: jupyter notebook -h 2>&1 >/dev/null
        #    extends:
        #      jupyter_server

        jupyter_server_test:
          command: jupyter notebook -h 2>&1 >/dev/null
          environment:
            - PORT=${PORT}
          extends:
            app
          ports:
            - "${PORT}:${PORT}"
        """
        # This is at the level of `services`.
        indent_level = 1
        append(txt_tmp, indent_level)
    # Save file.
    txt: str = "\n".join(txt)
    if file_name:
        hio.to_file(file_name, txt)
    # Sanity check of the YAML file.
    stream = io.StringIO(txt)
    _ = yaml.safe_load(stream)
    return txt


def get_base_docker_compose_path() -> str:
    """
    Return the absolute path to base docker compose.

    E.g., `devops/compose/docker-compose.yml`.
    """
    # Add the default path.
    dir_name = "devops/compose"
    # TODO(gp): Factor out the piece below.
    docker_compose_path = "docker-compose.yml"
    docker_compose_path = os.path.join(dir_name, docker_compose_path)
    docker_compose_path = os.path.abspath(docker_compose_path)
    return docker_compose_path


def _get_amp_docker_compose_path() -> Optional[str]:
    """
    Return the docker compose to use for `amp`, depending whether it is a
    supermodule or as submodule.

    E.g.,
    - for submodule -> `devops/compose/docker-compose_as_submodule.yml`
    - for supermodule -> None
    """
    path, _ = hgit.get_path_from_supermodule()
    docker_compose_path: Optional[str]
    if path != "":
        _LOG.warning("amp is a submodule")
        docker_compose_path = "docker-compose_as_submodule.yml"
        # Add the default path.
        dir_name = "devops/compose"
        docker_compose_path = os.path.join(dir_name, docker_compose_path)
        docker_compose_path = os.path.abspath(docker_compose_path)
    else:
        docker_compose_path = None
    return docker_compose_path


def _get_docker_compose_paths(
    extra_docker_compose_files: List[str],
) -> List[str]:
    """
    Return the list of the needed docker compose path.
    """
    docker_compose_files = []
    # Get the repo short name (e.g., amp).
    dir_name = hgit.get_repo_full_name_from_dirname(".", include_host_name=False)
    repo_short_name = hgit.get_repo_name(dir_name, in_mode="full_name")
    _LOG.debug("repo_short_name=%s", repo_short_name)
    # Check submodule status, if needed.
    mount_as_submodule = False
    if repo_short_name in ("amp", "cm"):
        # Check if `amp` is a submodule.
        path, _ = hgit.get_path_from_supermodule()
        docker_compose_path: Optional[str]
        if path != "":
            _LOG.warning("amp is a submodule")
            mount_as_submodule = True
    # Write Docker compose file.
    file_name = get_base_docker_compose_path()
    _generate_compose_file(
        hgit.execute_repo_config_code("enable_privileged_mode()"),
        hgit.execute_repo_config_code("use_docker_sibling_containers()"),
        hgit.execute_repo_config_code("use_docker_shared_cache()"),
        mount_as_submodule,
        hgit.execute_repo_config_code("use_docker_network_mode_host()"),
        file_name,
    )
    docker_compose_files.append(file_name)
    # if False:
    # docker_compose_files = []
    # if has_default_param("USE_ONLY_ONE_DOCKER_COMPOSE"):
    #     # Use only one docker compose file, instead of two.
    #     # TODO(gp): Hacky fix for CmampTask386 "Clean up docker compose".
    #     if repo_short_name == "amp":
    #         # For amp use only
    #         docker_compose_file_tmp = _get_amp_docker_compose_path()
    #     else:
    #         docker_compose_file_tmp = get_base_docker_compose_path()
    #     docker_compose_files.append(docker_compose_file_tmp)
    # else:
    #     # Typically we use one or two docker compose files, depending if we need
    #     # submodule behavior or not.
    #     docker_compose_files.append(get_base_docker_compose_path())
    #     if repo_short_name == "amp":
    #         docker_compose_file_tmp = _get_amp_docker_compose_path()
    #         if docker_compose_file_tmp:
    #             docker_compose_files.append(docker_compose_file_tmp)

    # Add the compose files from command line.
    if extra_docker_compose_files:
        hdbg.dassert_isinstance(extra_docker_compose_files, list)
        docker_compose_files.extend(extra_docker_compose_files)
    # Add the compose files from the global params.
    key = "DOCKER_COMPOSE_FILES"
    if has_default_param(key):
        docker_compose_files.append(get_default_param(key))
    #
    _LOG.debug(hprint.to_str("docker_compose_files"))
    for docker_compose in docker_compose_files:
        hdbg.dassert_path_exists(docker_compose)
    return docker_compose_files


# ////////////////////////////////////////////////////////////////////////////////
# Version.
# ////////////////////////////////////////////////////////////////////////////////


_IMAGE_VERSION_RE = r"\d+\.\d+\.\d+"


def _dassert_is_version_valid(version: str) -> None:
    """
    Check that the version is valid, i.e. looks like `1.0.0`.
    """
    hdbg.dassert_isinstance(version, str)
    hdbg.dassert_ne(version, "")
    regex = rf"^({_IMAGE_VERSION_RE})$"
    _LOG.debug("Testing with regex='%s'", regex)
    m = re.match(regex, version)
    hdbg.dassert(m, "Invalid version: '%s'", version)


_IMAGE_VERSION_FROM_CHANGELOG = "FROM_CHANGELOG"


def _resolve_version_value(
    version: str,
    *,
    container_dir_name: str = ".",
) -> str:
    """
    Pass a version (e.g., 1.0.0) or a symbolic value (e.g., FROM_CHANGELOG) and
    return the resolved value of the version.
    """
    hdbg.dassert_isinstance(version, str)
    if version == _IMAGE_VERSION_FROM_CHANGELOG:
        version = hversio.get_changelog_version(container_dir_name)
    _dassert_is_version_valid(version)
    return version


def _dassert_is_subsequent_version(
    version: str,
    *,
    container_dir_name: str = ".",
) -> None:
    """
    Check that version is strictly bigger than the current one as specified in
    the changelog.
    """
    if version != _IMAGE_VERSION_FROM_CHANGELOG:
        current_version = hversio.get_changelog_version(container_dir_name)
        hdbg.dassert_lt(current_version, version)


# ////////////////////////////////////////////////////////////////////////////////
# Image.
# ////////////////////////////////////////////////////////////////////////////////


_INTERNET_ADDRESS_RE = r"([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}"
_IMAGE_BASE_NAME_RE = r"[a-z0-9_-]+"
_IMAGE_USER_RE = r"[a-z0-9_-]+"
# For candidate prod images which have added hash for easy identification.
_IMAGE_HASH_RE = r"[a-z0-9]{9}"
_IMAGE_STAGE_RE = (
    rf"(local(?:-{_IMAGE_USER_RE})?|dev|prod|prod(?:-{_IMAGE_HASH_RE})?)"
)


def _dassert_is_image_name_valid(image: str) -> None:
    """
    Check whether an image name is valid.

    Invariants:
    - Local images contain a user name and a version
      - E.g., `*****.dkr.ecr.us-east-1.amazonaws.com/amp:local-saggese-1.0.0`
    - `dev` and `prod` images have an instance with the a version and one without
      to indicate the latest
      - E.g., `*****.dkr.ecr.us-east-1.amazonaws.com/amp:dev-1.0.0`
        and `*****.dkr.ecr.us-east-1.amazonaws.com/amp:dev`
    - `prod` candidate image has a 9 character hash identifier from the
        corresponding Git commit
        - E.g., `*****.dkr.ecr.us-east-1.amazonaws.com/amp:prod-1.0.0-4rf74b83a`

    An image should look like:

    *****.dkr.ecr.us-east-1.amazonaws.com/amp:dev
    *****.dkr.ecr.us-east-1.amazonaws.com/amp:local-saggese-1.0.0
    *****.dkr.ecr.us-east-1.amazonaws.com/amp:dev-1.0.0
    """
    regex = "".join(
        [
            # E.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
            rf"^{_INTERNET_ADDRESS_RE}\/{_IMAGE_BASE_NAME_RE}",
            # :local-saggese
            rf":{_IMAGE_STAGE_RE}",
            # -1.0.0
            rf"(-{_IMAGE_VERSION_RE})?$",
        ]
    )
    _LOG.debug("Testing with regex='%s'", regex)
    m = re.match(regex, image)
    hdbg.dassert(m, "Invalid image: '%s'", image)


def _dassert_is_base_image_name_valid(base_image: str) -> None:
    """
    Check that the base image is valid, i.e. looks like below.

    *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    regex = rf"^{_INTERNET_ADDRESS_RE}\/{_IMAGE_BASE_NAME_RE}$"
    _LOG.debug("regex=%s", regex)
    m = re.match(regex, base_image)
    hdbg.dassert(m, "Invalid base_image: '%s'", base_image)


def _get_base_image(base_image: str) -> str:
    """
    :return: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    if base_image == "":
        # TODO(gp): Use os.path.join.
        base_image = (
            get_default_param("AM_ECR_BASE_PATH")
            + "/"
            + get_default_param("BASE_IMAGE")
        )
    _dassert_is_base_image_name_valid(base_image)
    return base_image


# This code path through Git tag was discontinued with CmTask746.
# def get_git_tag(
#      version: str,
#  ) -> str:
#      """
#      Return the tag to be used in Git that consists of an image name and
#      version.
#      :param version: e.g., `1.0.0`. If None, the latest version is used
#      :return: e.g., `amp-1.0.0`
#      """
#      hdbg.dassert_is_not(version, None)
#      _dassert_is_version_valid(version)
#      base_image = get_default_param("BASE_IMAGE")
#      tag_name = f"{base_image}-{version}"
#      return tag_name


# TODO(gp): Consider using a token "latest" in version, so that it's always a
#  string and we avoid a special behavior encoded in None.
def get_image(
    base_image: str,
    stage: str,
    version: Optional[str],
) -> str:
    """
    Return the fully qualified image name.

    For local stage, it also appends the user name to the image name.

    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    :param stage: e.g., `local`, `dev`, `prod`
    :param version: e.g., `1.0.0`, if None empty, the latest version is used
    :return: e.g., `*****.dkr.ecr.us-east-1.amazonaws.com/amp:local` or
        `*****.dkr.ecr.us-east-1.amazonaws.com/amp:local-1.0.0`
    """
    # Docker refers the default image as "latest", although in our stage
    # nomenclature we call it "dev".
    hdbg.dassert_in(stage, "local dev prod".split())
    # Get the base image.
    base_image = _get_base_image(base_image)
    _dassert_is_base_image_name_valid(base_image)
    # Get the full image name.
    image = [base_image]
    # Handle the stage.
    image.append(f":{stage}")
    # User the user name.
    if stage == "local":
        user = hsystem.get_user_name()
        image.append(f"-{user}")
    # Handle the version.
    if version is not None and version != "":
        _dassert_is_version_valid(version)
        image.append(f"-{version}")
    #
    image = "".join(image)
    _dassert_is_image_name_valid(image)
    return image


# ////////////////////////////////////////////////////////////////////////////////
# Misc.
# ////////////////////////////////////////////////////////////////////////////////


def _run_docker_as_user(as_user_from_cmd_line: bool) -> bool:
    as_root = hgit.execute_repo_config_code("run_docker_as_root()")
    as_user = as_user_from_cmd_line
    if as_root:
        as_user = False
    _LOG.debug(
        "as_user_from_cmd_line=%s as_root=%s -> as_user=%s",
        as_user_from_cmd_line,
        as_root,
        as_user,
    )
    return as_user


def _get_container_name(service_name: str) -> str:
    """
    Create a container name based on various information (e.g.,
    `grisha.cmamp.app.cmamp1.20220317_232120`).

    The information used to build a container is:
       - Linux user name
       - Base Docker image name
       - Service name
       - Project directory that was used to start a container
       - Container start timestamp

    :param service_name: `docker-compose` service name, e.g., `app`
    :return: container name
    """
    hdbg.dassert_ne(service_name, "", "You need to specify a service name")
    # Get linux user name.
    linux_user = hsystem.get_user_name()
    # Get dir name.
    project_dir = hgit.get_project_dirname()
    # Get Docker image base name.
    image_name = get_default_param("BASE_IMAGE")
    # Get current timestamp.
    current_timestamp = _get_ET_timestamp()
    # Build container name.
    container_name = f"{linux_user}.{image_name}.{service_name}.{project_dir}.{current_timestamp}"
    _LOG.debug(
        "get_container_name: container_name=%s",
        container_name,
    )
    return container_name


def _get_docker_base_cmd(
    base_image: str,
    stage: str,
    version: str,
    extra_env_vars: Optional[List[str]],
    extra_docker_compose_files: Optional[List[str]],
) -> List[str]:
    r"""
    Get base `docker-compose` command encoded as a list of strings.

    It can be used as a base to build more complicated commands, e.g., `run`, `up`, `down`.

    E.g.,
    ```
        ['IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp:dev',
            '\n        docker-compose',
            '\n        --file amp/devops/compose/docker-compose.yml',
            '\n        --file amp/devops/compose/docker-compose_as_submodule.yml',
            '\n        --env-file devops/env/default.env']
    ```
    :param extra_env_vars: represent vars to add, e.g., `["PORT=9999", "DRY_RUN=1"]`
    :param extra_docker_compose_files: `docker-compose` override files
    """
    hprint.log(
        _LOG,
        logging.DEBUG,
        "base_image stage version extra_env_vars extra_docker_compose_files",
    )
    docker_cmd_: List[str] = []
    # - Handle the image.
    image = get_image(base_image, stage, version)
    _LOG.debug("base_image=%s stage=%s -> image=%s", base_image, stage, image)
    _dassert_is_image_name_valid(image)
    docker_cmd_.append(f"IMAGE={image}")
    # - Handle extra env vars.
    if extra_env_vars:
        hdbg.dassert_isinstance(extra_env_vars, list)
        for env_var in extra_env_vars:
            docker_cmd_.append(f"{env_var}")
    #
    docker_cmd_.append(
        r"""
        docker-compose"""
    )
    docker_compose_files = _get_docker_compose_paths(extra_docker_compose_files)
    file_opts = " ".join([f"--file {dcf}" for dcf in docker_compose_files])
    _LOG.debug(hprint.to_str("file_opts"))
    # TODO(gp): Use something like `.append(rf"{space}{...}")`
    docker_cmd_.append(
        rf"""
        {file_opts}"""
    )
    # - Handle the env file.
    env_file = "devops/env/default.env"
    docker_cmd_.append(
        rf"""
        --env-file {env_file}"""
    )
    return docker_cmd_


# TODO(Grisha): -> `_get_docker_run_cmd` CmTask #1486.
def _get_docker_cmd(
    base_image: str,
    stage: str,
    version: str,
    cmd: str,
    *,
    extra_env_vars: Optional[List[str]] = None,
    extra_docker_compose_files: Optional[List[str]] = None,
    extra_docker_run_opts: Optional[List[str]] = None,
    service_name: str = "app",
    entrypoint: bool = True,
    as_user: bool = True,
    print_docker_config: bool = False,
    use_bash: bool = False,
) -> str:
    """
    Get `docker-compose` run command.

    E.g.,
    ```
    IMAGE=*****..dkr.ecr.us-east-1.amazonaws.com/amp:dev \
        docker-compose \
        --file /amp/devops/compose/docker-compose.yml \
        --env-file devops/env/default.env \
        run \
        --rm \
        --name grisha.cmamp.app.cmamp1.20220317_232120 \
        --user $(id -u):$(id -g) \
        app \
        bash
    ```
    :param cmd: command to run inside Docker container
    :param extra_docker_run_opts: additional `docker-compose` run options
    :param service_name: service to use to run a command
    :param entrypoint: use whether to use `entrypoint` or not
    :param as_user: pass the user / group id or not
    :param print_docker_config: print the docker config for debugging purposes
    :param use_bash: run command through a shell
    """
    hprint.log(
        _LOG,
        logging.DEBUG,
        "cmd extra_docker_run_opts service_name "
        "entrypoint as_user print_docker_config use_bash",
    )
    # - Get the base Docker command.
    docker_cmd_ = _get_docker_base_cmd(
        base_image,
        stage,
        version,
        extra_env_vars,
        extra_docker_compose_files,
    )
    # - Add the `config` command for debugging purposes.
    docker_config_cmd: List[str] = docker_cmd_[:]
    docker_config_cmd.append(
        r"""
        config"""
    )
    # - Add the `run` command.
    docker_cmd_.append(
        r"""
        run \
        --rm"""
    )
    # - Add a name to the container.
    container_name = _get_container_name(service_name)
    docker_cmd_.append(
        rf"""
        --name {container_name}"""
    )
    # - Handle the user.
    as_user = _run_docker_as_user(as_user)
    if as_user:
        docker_cmd_.append(
            r"""
        --user $(id -u):$(id -g)"""
        )
    # - Handle the extra docker options.
    if extra_docker_run_opts:
        hdbg.dassert_isinstance(extra_docker_run_opts, list)
        extra_opts = " ".join(extra_docker_run_opts)
        docker_cmd_.append(
            rf"""
        {extra_opts}"""
        )
    # - Handle entrypoint.
    if entrypoint:
        docker_cmd_.append(
            rf"""
        {service_name}"""
        )
        if cmd:
            if use_bash:
                cmd = f"bash -c '{cmd}'"
            docker_cmd_.append(
                rf"""
        {cmd}"""
            )
    else:
        docker_cmd_.append(
            rf"""
        --entrypoint bash \
        {service_name}"""
        )
    # Print the config for debugging purpose.
    if print_docker_config:
        docker_config_cmd_as_str = _to_multi_line_cmd(docker_config_cmd)
        _LOG.debug("docker_config_cmd=\n%s", docker_config_cmd_as_str)
        _LOG.debug(
            "docker_config=\n%s",
            hsystem.system_to_string(docker_config_cmd_as_str)[1],
        )
    # Print the config for debugging purpose.
    docker_cmd_ = _to_multi_line_cmd(docker_cmd_)
    return docker_cmd_


# ////////////////////////////////////////////////////////////////////////////////
# bash and cmd.
# ////////////////////////////////////////////////////////////////////////////////


def _docker_cmd(
    ctx: Any,
    docker_cmd_: str,
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    """
    Execute a docker command printing the command.

    :param kwargs: kwargs for `ctx.run`
    """
    _LOG.info("Pulling the latest version of Docker")
    docker_pull(ctx)
    _LOG.debug("cmd=%s", docker_cmd_)
    rc: Optional[int] = _run(ctx, docker_cmd_, pty=True, **ctx_run_kwargs)
    return rc


@task
def docker_bash(  # type: ignore
    ctx,
    base_image="",
    stage="dev",
    version="",
    entrypoint=True,
    as_user=True,
    container_dir_name=".",
):
    """
    Start a bash shell inside the container corresponding to a stage.

    TODO(gp): Add description of non-obvious interface params.
    """
    _report_task(container_dir_name=container_dir_name)
    cmd = "bash"
    docker_cmd_ = _get_docker_cmd(
        base_image, stage, version, cmd, entrypoint=entrypoint, as_user=as_user
    )
    _docker_cmd(ctx, docker_cmd_)


@task
def docker_cmd(  # type: ignore
    ctx,
    base_image="",
    stage="dev",
    version="",
    cmd="",
    as_user=True,
    use_bash=False,
    container_dir_name=".",
):
    """
    Execute the command `cmd` inside a container corresponding to a stage.

    TODO(gp): Add description of non-obvious interface params.
    """
    _report_task(container_dir_name=container_dir_name)
    hdbg.dassert_ne(cmd, "")
    # TODO(gp): Do we need to overwrite the entrypoint?
    docker_cmd_ = _get_docker_cmd(
        base_image,
        stage,
        version,
        cmd,
        as_user=as_user,
        use_bash=use_bash,
    )
    _docker_cmd(ctx, docker_cmd_)


# ////////////////////////////////////////////////////////////////////////////////
# Jupyter.
# ////////////////////////////////////////////////////////////////////////////////


def _get_docker_jupyter_cmd(
    base_image: str,
    stage: str,
    version: str,
    port: int,
    self_test: bool,
    *,
    print_docker_config: bool = False,
) -> str:
    cmd = ""
    extra_env_vars = [f"PORT={port}"]
    extra_docker_run_opts = ["--service-ports"]
    service_name = "jupyter_server_test" if self_test else "jupyter_server"
    #
    docker_cmd_ = _get_docker_cmd(
        base_image,
        stage,
        version,
        cmd,
        extra_env_vars=extra_env_vars,
        extra_docker_run_opts=extra_docker_run_opts,
        service_name=service_name,
        print_docker_config=print_docker_config,
    )
    return docker_cmd_


@task
def docker_jupyter(  # type: ignore
    ctx,
    stage="dev",
    version="",
    base_image="",
    auto_assign_port=True,
    port=9999,
    self_test=False,
    container_dir_name=".",
):
    """
    Run jupyter notebook server.

    :param auto_assign_port: use the UID of the user and the inferred number of the
        repo (e.g., 4 for `~/src/amp4`) to get a unique port
    """
    _report_task(container_dir_name=container_dir_name)
    if auto_assign_port:
        uid = os.getuid()
        _LOG.debug("uid=%s", uid)
        git_repo_idx = hgit.get_project_dirname(only_index=True)
        git_repo_idx = int(git_repo_idx)
        _LOG.debug("git_repo_idx=%s", git_repo_idx)
        # We assume that there are no more than `max_idx_per_users` clients.
        max_idx_per_user = 10
        hdbg.dassert_lte(git_repo_idx, max_idx_per_user)
        port = (uid * max_idx_per_user) + git_repo_idx
        _LOG.info("Assigned port is %s", port)
    #
    print_docker_config = False
    docker_cmd_ = _get_docker_jupyter_cmd(
        base_image,
        stage,
        version,
        port,
        self_test,
        print_docker_config=print_docker_config,
    )
    _docker_cmd(ctx, docker_cmd_)


# #############################################################################
# Docker image workflows.
# #############################################################################


def _to_abs_path(filename: str) -> str:
    filename = os.path.abspath(filename)
    hdbg.dassert_path_exists(filename)
    return filename


def _prepare_docker_ignore(ctx: Any, docker_ignore: str) -> None:
    """
    Copy the target docker_ignore in the proper position for `docker build`.
    """
    # Currently there is no built-in way to control which .dockerignore to use.
    # https://stackoverflow.com/questions/40904409
    hdbg.dassert_path_exists(docker_ignore)
    cmd = f"cp -f {docker_ignore} .dockerignore"
    _run(ctx, cmd)


# =============================================================================
# DEV image flow
# =============================================================================
# - A "local" image (which is a release candidate for the DEV image) is built with:
#   ```
#   > docker_build_local_image
#   ```
#   This creates the local image `dev_tools:local.saggese-1.0.0`
# - A qualification process (e.g., running all unit tests and the QA tests) is
#   performed on the "local" image (e.g., locally or through GitHub actions)
# - If the qualification process is passed, the image is released as `dev` on ECR


# Use Docker buildkit or not.
# DOCKER_BUILDKIT = 1
DOCKER_BUILDKIT = 0


# For base_image, we use "" as default instead None since pyinvoke can only infer
# a single type.
@task
def docker_build_local_image(  # type: ignore
    ctx,
    version,
    cache=True,
    base_image="",
    update_poetry=False,
    container_dir_name=".",
    just_do_it=False,
):
    """
    Build a local image (i.e., a release candidate "dev" image).

    :param version: version to tag the image and code with
    :param cache: use the cache
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    :param update_poetry: run poetry lock to update the packages
    :param just_do_it: execute the action ignoring the checks
    """
    _report_task(container_dir_name=container_dir_name)
    if just_do_it:
        _LOG.warning("Skipping subsequent version check")
    else:
        _dassert_is_subsequent_version(
            version, container_dir_name=container_dir_name
        )
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    # Update poetry, if needed.
    if update_poetry:
        cmd = "cd devops/docker_build; poetry lock -v"
        _run(ctx, cmd)
    # Prepare `.dockerignore`.
    docker_ignore = ".dockerignore.dev"
    _prepare_docker_ignore(ctx, docker_ignore)
    # Build the local image.
    image_local = get_image(base_image, "local", version)
    _dassert_is_image_name_valid(image_local)
    # This code path through Git tag was discontinued with CmTask746.
    # git_tag_prefix = get_default_param("BASE_IMAGE")
    # container_version = get_git_tag(version)
    #
    dockerfile = "devops/docker_build/dev.Dockerfile"
    dockerfile = _to_abs_path(dockerfile)
    #
    opts = "--no-cache" if not cache else ""
    # TODO(gp): Use _to_multi_line_cmd()
    cmd = rf"""
    DOCKER_BUILDKIT={DOCKER_BUILDKIT} \
    time \
    docker build \
        --progress=plain \
        {opts} \
        --build-arg AM_CONTAINER_VERSION={version} \
        --tag {image_local} \
        --file {dockerfile} \
        .
    """
    _run(ctx, cmd)
    # Check image and report stats.
    cmd = f"docker image ls {image_local}"
    _run(ctx, cmd)


@task
def docker_tag_local_image_as_dev(  # type: ignore
    ctx,
    version,
    base_image="",
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Mark the "local" image as "dev".

    :param version: version to tag the image and code with
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    _report_task(container_dir_name=container_dir_name)
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    # Tag local image as versioned dev image (e.g., `dev-1.0.0`).
    image_versioned_local = get_image(base_image, "local", version)
    image_versioned_dev = get_image(base_image, "dev", version)
    cmd = f"docker tag {image_versioned_local} {image_versioned_dev}"
    _run(ctx, cmd)
    # Tag local image as dev image.
    latest_version = None
    image_dev = get_image(base_image, "dev", latest_version)
    cmd = f"docker tag {image_versioned_local} {image_dev}"
    _run(ctx, cmd)


@task
def docker_push_dev_image(  # type: ignore
    ctx,
    version,
    base_image="",
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Push the "dev" image to ECR.

    :param version: version to tag the image and code with
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    _report_task(container_dir_name=container_dir_name)
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    #
    docker_login(ctx)
    # Push Docker versioned tag.
    image_versioned_dev = get_image(base_image, "dev", version)
    cmd = f"docker push {image_versioned_dev}"
    _run(ctx, cmd, pty=True)
    # Push Docker tag.
    latest_version = None
    image_dev = get_image(base_image, "dev", latest_version)
    cmd = f"docker push {image_dev}"
    _run(ctx, cmd, pty=True)


@task
def docker_release_dev_image(  # type: ignore
    ctx,
    version,
    cache=True,
    skip_tests=False,
    fast_tests=True,
    slow_tests=True,
    superslow_tests=False,
    qa_tests=True,
    push_to_repo=True,
    update_poetry=False,
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Build, test, and release to ECR the latest "dev" image.

    This can be used to test the entire flow from scratch by building an image,
    running the tests, but not necessarily pushing.

    Phases:
    1) Build local image
    2) Run the unit tests (e.g., fast, slow, superslow) on the local image
    3) Mark local as dev image
    4) Run the QA tests on the dev image
    5) Push dev image to the repo

    :param version: version to tag the image and code with
    :param cache: use the cache
    :param skip_tests: skip all the tests and release the dev image
    :param fast_tests: run fast tests, unless all tests skipped
    :param slow_tests: run slow tests, unless all tests skipped
    :param superslow_tests: run superslow tests, unless all tests skipped
    :param qa_tests: run end-to-end linter tests, unless all tests skipped
    :param push_to_repo: push the image to the repo_short_name
    :param update_poetry: update package dependencies using poetry
    """
    _report_task(container_dir_name=container_dir_name)
    # 1) Build "local" image.
    docker_build_local_image(
        ctx,
        cache=cache,
        update_poetry=update_poetry,
        version=version,
        container_dir_name=container_dir_name,
    )
    # Run resolve after `docker_build_local_image` so that a proper check
    # for subsequent version can be made in case `FROM_CHANGELOG` token
    # is used.
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    # 2) Run tests for the "local" image.
    if skip_tests:
        _LOG.warning("Skipping all tests and releasing")
        fast_tests = False
        slow_tests = False
        superslow_tests = False
        qa_tests = False
    stage = "local"
    if fast_tests:
        run_fast_tests(ctx, stage=stage, version=version)
    if slow_tests:
        run_slow_tests(ctx, stage=stage, version=version)
    if superslow_tests:
        run_superslow_tests(ctx, stage=stage, version=version)
    # 3) Promote the "local" image to "dev".
    docker_tag_local_image_as_dev(
        ctx, version, container_dir_name=container_dir_name
    )
    # 4) Run QA tests for the (local version) of the dev image.
    if qa_tests:
        run_qa_tests(ctx, stage="dev", version=version)
    # 5) Push the "dev" image to ECR.
    if push_to_repo:
        docker_push_dev_image(ctx, version, container_dir_name=container_dir_name)
    else:
        _LOG.warning(
            "Skipping pushing dev image to repo_short_name, as requested"
        )
    _LOG.info("==> SUCCESS <==")


# #############################################################################
# PROD image flow:
# #############################################################################
# - PROD image has no release candidate
# - Start from a DEV image already built and qualified
# - The PROD image is created from the DEV image by copying the code inside the
#   image
# - The PROD image is tagged as "prod"


# TODO(gp): Remove redundancy with docker_build_local_image(), if possible.
@task
def docker_build_prod_image(  # type: ignore
    ctx,
    version,
    cache=True,
    base_image="",
    candidate=False,
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Build a prod image.

    Phases:
    - Build the prod image on top of the dev image

    :param version: version to tag the image and code with
    :param cache: note that often the prod image is just a copy of the dev
        image so caching makes no difference
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    :param candidate: build a prod image with a tag format: prod-{hash}
        where hash is the output of hgit.get_head_hash
    """
    _report_task(container_dir_name=container_dir_name)
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    # Prepare `.dockerignore`.
    docker_ignore = ".dockerignore.prod"
    _prepare_docker_ignore(ctx, docker_ignore)
    # TODO(gp): We should do a `i git_clean` to remove artifacts and check that
    #  the client is clean so that we don't release from a dirty client.
    # Build prod image.
    if candidate:
        # For candidate prod images which need to be tested on
        # the AWS infra add a hash identifier.
        latest_version = None
        image_versioned_prod = get_image(base_image, "prod", latest_version)
        head_hash = hgit.get_head_hash(short_hash=True)
        image_versioned_prod += f"-{head_hash}"
    else:
        image_versioned_prod = get_image(base_image, "prod", version)
    _dassert_is_image_name_valid(image_versioned_prod)
    #
    dockerfile = "devops/docker_build/prod.Dockerfile"
    dockerfile = _to_abs_path(dockerfile)
    #
    # TODO(gp): Use _to_multi_line_cmd()
    opts = "--no-cache" if not cache else ""
    cmd = rf"""
    DOCKER_BUILDKIT={DOCKER_BUILDKIT} \
    time \
    docker build \
        --progress=plain \
        {opts} \
        --tag {image_versioned_prod} \
        --file {dockerfile} \
        --build-arg VERSION={version} \
        .
    """
    _run(ctx, cmd)
    if candidate:
        _LOG.info("Head hash: %s", head_hash)
        cmd = f"docker image ls {image_versioned_prod}"
    else:
        # Tag versioned image as latest prod image.
        latest_version = None
        image_prod = get_image(base_image, "prod", latest_version)
        cmd = f"docker tag {image_versioned_prod} {image_prod}"
        _run(ctx, cmd)
        #
        cmd = f"docker image ls {image_prod}"

    _run(ctx, cmd)


@task
def docker_push_prod_image(  # type: ignore
    ctx,
    version,
    base_image="",
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Push the "prod" image to ECR.

    :param version: version to tag the image and code with
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    _report_task(container_dir_name=container_dir_name)
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    #
    docker_login(ctx)
    # Push versioned tag.
    image_versioned_prod = get_image(base_image, "prod", version)
    cmd = f"docker push {image_versioned_prod}"
    _run(ctx, cmd, pty=True)
    #
    latest_version = None
    image_prod = get_image(base_image, "prod", latest_version)
    cmd = f"docker push {image_prod}"
    _run(ctx, cmd, pty=True)


@task
def docker_push_prod_candidate_image(  # type: ignore
    ctx,
    candidate,
    base_image="",
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Push the "prod" candidate image to ECR.

    :param candidate: hash tag of the candidate prod image to push
    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    """
    _report_task(container_dir_name=container_dir_name)
    #
    docker_login(ctx)
    # Push image with tagged with a hash ID.
    image_versioned_prod = get_image(base_image, "prod", None)
    cmd = f"docker push {image_versioned_prod}-{candidate}"
    _run(ctx, cmd, pty=True)


@task
def docker_release_prod_image(  # type: ignore
    ctx,
    version,
    cache=True,
    skip_tests=False,
    fast_tests=True,
    slow_tests=True,
    superslow_tests=False,
    push_to_repo=True,
    container_dir_name=".",
):
    """
    (ONLY CI/CD) Build, test, and release to ECR the prod image.

    - Build prod image
    - Run the tests
    - Push the prod image repo

    :param version: version to tag the image and code with
    :param cache: use the cache
    :param skip_tests: skip all the tests and release the dev image
    :param fast_tests: run fast tests, unless all tests skipped
    :param slow_tests: run slow tests, unless all tests skipped
    :param superslow_tests: run superslow tests, unless all tests skipped
    :param push_to_repo: push the image to the repo_short_name
    """
    _report_task(container_dir_name=container_dir_name)
    version = _resolve_version_value(
        version, container_dir_name=container_dir_name
    )
    # 1) Build prod image.
    docker_build_prod_image(
        ctx, cache=cache, version=version, container_dir_name=container_dir_name
    )
    # 2) Run tests.
    if skip_tests:
        _LOG.warning("Skipping all tests and releasing")
        fast_tests = slow_tests = superslow_tests = False
    stage = "prod"
    if fast_tests:
        run_fast_tests(ctx, stage=stage, version=version)
    if slow_tests:
        run_slow_tests(ctx, stage=stage, version=version)
    if superslow_tests:
        run_superslow_tests(ctx, stage=stage, version=version)
    # 3) Push prod image.
    if push_to_repo:
        docker_push_prod_image(
            ctx, version=version, container_dir_name=container_dir_name
        )
    else:
        _LOG.warning("Skipping pushing image to repo_short_name as requested")
    _LOG.info("==> SUCCESS <==")


@task
def docker_release_all(ctx, version, container_dir_name="."):  # type: ignore
    """
    (ONLY CI/CD) Release both dev and prod image to ECR.

    This includes:
    - docker_release_dev_image
    - docker_release_prod_image

    :param version: version to tag the image and code with
    """
    _report_task()
    docker_release_dev_image(ctx, version, container_dir_name=container_dir_name)
    docker_release_prod_image(ctx, version, container_dir_name=container_dir_name)
    _LOG.info("==> SUCCESS <==")


def _docker_rollback_image(
    ctx: Any, base_image: str, stage: str, version: str
) -> None:
    """
    Rollback the versioned image for a particular stage.

    :param base_image: e.g., *****.dkr.ecr.us-east-1.amazonaws.com/amp
    :param stage: select a specific stage for the Docker image
    :param version: version to tag the image and code with
    """
    image_versioned_dev = get_image(base_image, stage, version)
    latest_version = None
    image_dev = get_image(base_image, stage, latest_version)
    cmd = f"docker tag {image_versioned_dev} {image_dev}"
    _run(ctx, cmd)


@task
def docker_rollback_dev_image(  # type: ignore
    ctx,
    version,
    push_to_repo=True,
):
    """
    Rollback the version of the dev image.

    Phases:
    1) Ensure that version of the image exists locally
    2) Promote versioned image as dev image
    3) Push dev image to the repo

    :param version: version to tag the image and code with
    :param push_to_repo: push the image to the ECR repo
    """
    _report_task()
    # 1) Ensure that version of the image exists locally.
    _docker_pull(ctx, base_image="", stage="dev", version=version)
    # 2) Promote requested image as dev image.
    _docker_rollback_image(ctx, base_image="", stage="dev", version=version)
    # 3) Push the "dev" image to ECR.
    if push_to_repo:
        docker_push_dev_image(ctx, version=version)
    else:
        _LOG.warning("Skipping pushing dev image to ECR, as requested")
    _LOG.info("==> SUCCESS <==")


@task
def docker_rollback_prod_image(  # type: ignore
    ctx,
    version,
    push_to_repo=True,
):
    """
    Rollback the version of the prod image.

    Same as parameters and meaning as `docker_rollback_dev_image`.
    """
    _report_task()
    # 1) Ensure that version of the image exists locally.
    _docker_pull(ctx, base_image="", stage="prod", version=version)
    # 2) Promote requested image as prod image.
    _docker_rollback_image(ctx, base_image="", stage="prod", version=version)
    # 3) Push the "prod" image to ECR.
    if push_to_repo:
        docker_push_prod_image(ctx, version=version)
    else:
        _LOG.warning("Skipping pushing prod image to ECR, as requested")
    _LOG.info("==> SUCCESS <==")


# #############################################################################
# Find test.
# #############################################################################


def _find_test_files(
    dir_name: Optional[str] = None, use_absolute_path: bool = False
) -> List[str]:
    """
    Find all the files containing test code in `abs_dir`.
    """
    dir_name = dir_name or "."
    hdbg.dassert_dir_exists(dir_name)
    _LOG.debug("abs_dir=%s", dir_name)
    # Find all the file names containing test code.
    _LOG.info("Searching from '%s'", dir_name)
    path = os.path.join(dir_name, "**", "test_*.py")
    _LOG.debug("path=%s", path)
    file_names = glob.glob(path, recursive=True)
    _LOG.debug("Found %d files: %s", len(file_names), str(file_names))
    hdbg.dassert_no_duplicates(file_names)
    # Test files should always under a dir called `test`.
    for file_name in file_names:
        if "/old/" in file_name:
            continue
        hdbg.dassert_eq(
            os.path.basename(os.path.dirname(file_name)),
            "test",
            "Test file '%s' needs to be under a `test` dir ",
            file_name,
        )
        hdbg.dassert_not_in(
            "notebook/",
            file_name,
            "Test file '%s' should not be under a `notebook` dir",
            file_name,
        )
    # Make path relatives, if needed.
    if use_absolute_path:
        file_names = [os.path.abspath(file_name) for file_name in file_names]
    #
    file_names = sorted(file_names)
    _LOG.debug("file_names=%s", file_names)
    hdbg.dassert_no_duplicates(file_names)
    return file_names


# TODO(gp): -> find_class since it works also for any class.
def _find_test_class(
    class_name: str, file_names: List[str], exact_match: bool = False
) -> List[str]:
    """
    Find test file containing `class_name` and report it in pytest format.

    E.g., for "TestLibTasksRunTests1" return
    "test/test_lib_tasks.py::TestLibTasksRunTests1"

    :param exact_match: find an exact match or an approximate where `class_name`
        is included in the class name
    """
    # > jackpy TestLibTasksRunTests1
    # test/test_lib_tasks.py:60:class TestLibTasksRunTests1(hut.TestCase):
    regex = r"^\s*class\s+(\S+)\s*\("
    _LOG.debug("regex='%s'", regex)
    res: List[str] = []
    # Scan all the files.
    for file_name in file_names:
        _LOG.debug("file_name=%s", file_name)
        txt = hio.from_file(file_name)
        # Search for the class in each file.
        for i, line in enumerate(txt.split("\n")):
            # _LOG.debug("file_name=%s i=%s: %s", file_name, i, line)
            # TODO(gp): We should skip ```, """, '''
            m = re.match(regex, line)
            if m:
                found_class_name = m.group(1)
                _LOG.debug("  %s:%d -> %s", line, i, found_class_name)
                if exact_match:
                    found = found_class_name == class_name
                else:
                    found = class_name in found_class_name
                if found:
                    res_tmp = f"{file_name}::{found_class_name}"
                    _LOG.debug("-> res_tmp=%s", res_tmp)
                    res.append(res_tmp)
    res = sorted(list(set(res)))
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


# TODO(gp): Extend this to accept only the test method.
# TODO(gp): Have a single `find` command with multiple options to search for different
#  things, e.g., class names, test names, pytest_mark, ...
@task
def find_test_class(ctx, class_name, dir_name=".", pbcopy=True, exact_match=False):  # type: ignore
    """
    Report test files containing `class_name` in a format compatible with
    pytest.

    :param class_name: the class to search
    :param dir_name: the dir from which to search (default: .)
    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    _report_task(txt="class_name abs_dir pbcopy")
    hdbg.dassert(class_name != "", "You need to specify a class name")
    _ = ctx
    file_names = _find_test_files(dir_name)
    res = _find_test_class(class_name, file_names, exact_match)
    res = " ".join(res)
    # Print or copy to clipboard.
    _to_pbcopy(res, pbcopy)


# //////////////////////////////////////////////////////////////////////////////////


@functools.lru_cache()
def _get_python_files(subdir: str) -> List[str]:
    pattern = "*.py"
    only_files = False
    use_relative_paths = False
    python_files = hio.listdir(subdir, pattern, only_files, use_relative_paths)
    # Remove tmp files.
    python_files = [f for f in python_files if not f.startswith("tmp")]
    return python_files


# File, line number, line, info1, info2
_FindResult = Tuple[str, int, str, str, str]
_FindResults = List[_FindResult]


def _scan_files(python_files: List[str]) -> Iterator:
    for file_ in python_files:
        _LOG.debug("file=%s", file_)
        txt = hio.from_file(file_)
        for line_num, line in enumerate(txt.split("\n")):
            # TODO(gp): Skip commented lines.
            # _LOG.debug("%s:%s line='%s'", file_, line_num, line)
            yield file_, line_num, line


def _find_short_import(iterator: Iterator, short_import: str) -> _FindResults:
    """
    Find imports in the Python files with the given short import.

    E.g., for dtfcodarun dataflow/core/test/test_builders.py:9:import
    dataflow.core.dag_runner as dtfcodarun returns
    """
    # E.g.,
    # `import dataflow.core.dag_runner as dtfcodarun`
    regex = rf"import\s+(\S+)\s+as\s+({short_import})"
    regex = re.compile(regex)
    #
    results: _FindResults = []
    for file_, line_num, line in iterator:
        m = regex.search(line)
        if m:
            # E.g.,
            # dataflow/core/test/test_builders.py:9:import dataflow.core.dag_runner as dtfcodarun
            _LOG.debug("  --> line:%s=%s", line_num, line)
            long_import_txt = m.group(1)
            short_import_txt = m.group(2)
            full_import_txt = f"import {long_import_txt} as {short_import_txt}"
            res = (file_, line_num, line, short_import_txt, full_import_txt)
            # E.g.,
            _LOG.debug("  => %s", str(res))
            results.append(res)
    return results


def _find_func_class_uses(iterator: Iterator, regex: str) -> _FindResults:
    regexs = []
    # E.g.,
    # `dag_runner = dtfsys.RealTimeDagRunner(**dag_runner_kwargs)`
    regexs.append(rf"\s+(\w+)\.(\w*{regex})\(")
    # `dag_builder: dtfcodabui.DagBuilder`
    regexs.append(rf":\s*(\w+)\.(\w*{regex})")
    #
    _LOG.debug("regexs=%s", str(regexs))
    regexs = [re.compile(regex_) for regex_ in regexs]
    #
    results: _FindResults = []
    for file_, line_num, line in iterator:
        _LOG.debug("line='%s'", line)
        m = None
        for regex_ in regexs:
            m = regex_.search(line)
            if m:
                # _LOG.debug("--> regex matched")
                break
        if m:
            _LOG.debug("  --> line:%s=%s", line_num, line)
            short_import_txt = m.group(1)
            obj_txt = m.group(2)
            res = (file_, line_num, line, short_import_txt, obj_txt)
            # E.g.,
            # ('./helpers/lib_tasks.py', 10226, 'dtfsys', 'RealTimeDagRunner')
            # ('./dataflow/core/test/test_builders.py', 70, 'dtfcodarun', 'FitPredictDagRunner')
            # ('./dataflow/core/test/test_builders.py', 157, 'dtfcodarun', 'FitPredictDagRunner')
            _LOG.debug("  => %s", str(res))
            results.append(res)
    return results


def _process_find_results(results: _FindResults, how: str) -> List:
    filtered_results: List = []
    if how == "remove_dups":
        # Remove duplicates.
        for result in results:
            (_, _, _, info1, info2) = result
            filtered_results.append((info1, info2))
        filtered_results = hlist.remove_duplicates(filtered_results)
        filtered_results = sorted(filtered_results)
    elif how == "all":
        filtered_results = sorted(results)
    else:
        raise ValueError(f"Invalid how='{how}'")
    return filtered_results


@task
def find(ctx, regex, mode="all", how="remove_dups", subdir="."):  # type: ignore
    """
    Find symbols, imports, test classes and so on.

    Example:
    ```
    > i find DagBuilder
    ('dtfcodabui', 'DagBuilder')
    ('dtfcore', 'DagBuilder')
    ('dtfcodabui', 'import dataflow.core.dag_builder as dtfcodabui')
    ('dtfcore', 'import dataflow.core as dtfcore')
    ```

    :param regex: function or class use to search for
    :param mode: what to look for
        - `symbol_import`: look for uses of function or classes
          E.g., `DagRunner`
          returns
          ```
          ('cdataf', 'PredictionDagRunner')
          ('cdataf', 'RollingFitPredictDagRunner')
          ```
        - `short_import`: look for the short import
          E.g., `'dtfcodabui'
          returns
          ```
          ('dtfcodabui', 'import dataflow.core.dag_builder as dtfcodabui')
          ```
    :param how: how to report the results
        - `remove_dups`: report only imports and calls that are the same
    """
    _report_task(txt=hprint.to_str("regex mode how subdir"))
    _ = ctx
    # Process the `where`.
    python_files = _get_python_files(subdir)
    iter_ = _scan_files(python_files)
    # Process the `what`.
    if mode == "all":
        for mode_tmp in ("symbol_import", "short_import"):
            find(ctx, regex, mode=mode_tmp, how=how, subdir=subdir)
        return
    if mode == "symbol_import":
        results = _find_func_class_uses(iter_, regex)
        filtered_results = _process_find_results(results, "remove_dups")
        print("\n".join(map(str, filtered_results)))
        # E.g.,
        # ('cdataf', 'PredictionDagRunner')
        # ('cdataf', 'RollingFitPredictDagRunner')
        # Look for each short import.
        results = []
        for short_import, _ in filtered_results:
            iter_ = _scan_files(python_files)
            results.extend(_find_short_import(iter_, short_import))
    elif mode == "short_import":
        results = _find_short_import(iter_, regex)
    else:
        raise ValueError(f"Invalid mode='{mode}'")
    # Process the `how`.
    filtered_results = _process_find_results(results, how)
    print("\n".join(map(str, filtered_results)))


# #############################################################################
# Find test decorator.
# #############################################################################


# TODO(gp): decorator_name -> pytest_mark
def _find_test_decorator(decorator_name: str, file_names: List[str]) -> List[str]:
    """
    Find test files containing tests with a certain decorator
    `@pytest.mark.XYZ`.
    """
    hdbg.dassert_isinstance(file_names, list)
    # E.g.,
    #   @pytest.mark.slow(...)
    #   @pytest.mark.qa
    string = f"@pytest.mark.{decorator_name}"
    regex = rf"^\s*{re.escape(string)}\s*[\(]?"
    _LOG.debug("regex='%s'", regex)
    res: List[str] = []
    # Scan all the files.
    for file_name in file_names:
        _LOG.debug("file_name=%s", file_name)
        txt = hio.from_file(file_name)
        # Search for the class in each file.
        for i, line in enumerate(txt.split("\n")):
            # _LOG.debug("file_name=%s i=%s: %s", file_name, i, line)
            # TODO(gp): We should skip ```, """, '''. We can add a function to
            # remove all the comments, although we need to keep track of the
            # line original numbers.
            m = re.match(regex, line)
            if m:
                _LOG.debug("  -> found: %d:%s", i, line)
                res.append(file_name)
    #
    res = sorted(list(set(res)))
    return res


@task
def find_test_decorator(ctx, decorator_name="", dir_name="."):  # type: ignore
    """
    Report test files containing `class_name` in pytest format.

    :param decorator_name: the decorator to search
    :param dir_name: the dir from which to search
    """
    _report_task()
    _ = ctx
    hdbg.dassert_ne(decorator_name, "", "You need to specify a decorator name")
    file_names = _find_test_files(dir_name)
    res = _find_test_decorator(decorator_name, file_names)
    res = " ".join(res)
    print(res)


# #############################################################################
# Find / replace `check_string`.
# #############################################################################


@task
def find_check_string_output(  # type: ignore
    ctx, class_name, method_name, as_python=True, fuzzy_match=False, pbcopy=True
):
    """
    Find output of `check_string()` in the test running
    class_name::method_name.

    E.g., for `TestResultBundle::test_from_config1` return the content of the file
        `./core/dataflow/test/TestResultBundle.test_from_config1/output/test.txt`

    :param as_python: if True return the snippet of Python code that replaces the
        `check_string()` with a `assert_equal`
    :param fuzzy_match: if True return Python code with `fuzzy_match=True`
    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    _report_task()
    _ = ctx
    hdbg.dassert_ne(class_name, "", "You need to specify a class name")
    hdbg.dassert_ne(method_name, "", "You need to specify a method name")
    # Look for the directory named `class_name.method_name`.
    cmd = f"find . -name '{class_name}.{method_name}' -type d"
    # > find . -name "TestResultBundle.test_from_config1" -type d
    # ./core/dataflow/test/TestResultBundle.test_from_config1
    _, txt = hsystem.system_to_string(cmd, abort_on_error=False)
    file_names = txt.split("\n")
    if not txt:
        hdbg.dfatal(f"Can't find the requested dir with '{cmd}'")
    if len(file_names) > 1:
        hdbg.dfatal(f"Found more than one dir with '{cmd}':\n{txt}")
    dir_name = file_names[0]
    # Find the only file underneath that dir.
    hdbg.dassert_dir_exists(dir_name)
    cmd = f"find {dir_name} -name 'test.txt' -type f"
    _, file_name = hsystem.system_to_one_line(cmd)
    hdbg.dassert_file_exists(file_name)
    # Read the content of the file.
    _LOG.info("Found file '%s' for %s::%s", file_name, class_name, method_name)
    txt = hio.from_file(file_name)
    if as_python:
        # Package the code snippet.
        if not fuzzy_match:
            # Align the output at the same level as 'exp = r...'.
            num_spaces = 8
            txt = hprint.indent(txt, num_spaces=num_spaces)
        output = f"""
        act =
        exp = r\"\"\"
{txt}
        \"\"\".lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match={fuzzy_match})
        """
    else:
        output = txt
    # Print or copy to clipboard.
    _to_pbcopy(output, pbcopy)
    return output


# #############################################################################
# Run tests.
# #############################################################################

_COV_PYTEST_OPTS = [
    # Only compute coverage for current project and not venv libraries.
    "--cov=.",
    "--cov-branch",
    # Report the missing lines.
    # Name                 Stmts   Miss  Cover   Missing
    # -------------------------------------------------------------------------
    # myproj/__init__          2      0   100%
    # myproj/myproj          257     13    94%   24-26, 99, 149, 233-236, 297-298
    "--cov-report term-missing",
    # Report data in the directory `htmlcov`.
    "--cov-report html",
    # "--cov-report annotate",
]


_TEST_TIMEOUTS_IN_SECS = {
    "fast_tests": 5,
    "slow_tests": 30,
    "superslow_tests": 60 * 60,
}


_NUM_TIMEOUT_TEST_RERUNS = {
    "fast_tests": 2,
    "slow_tests": 1,
    "superslow_tests": 1,
}


@task
def run_blank_tests(ctx, stage="dev", version=""):  # type: ignore
    """
    (ONLY CI/CD) Test that pytest in the container works.
    """
    _report_task()
    _ = ctx
    base_image = ""
    cmd = '"pytest -h >/dev/null"'
    docker_cmd_ = _get_docker_cmd(base_image, stage, version, cmd)
    hsystem.system(docker_cmd_, abort_on_error=False, suppress_output=False)


def _select_tests_to_skip(test_list_name: str) -> str:
    """
    Generate text for pytest specifying which tests to deselect.
    """
    if test_list_name == "fast_tests":
        skipped_tests = "not slow and not superslow"
    elif test_list_name == "slow_tests":
        skipped_tests = "slow and not superslow"
    elif test_list_name == "superslow_tests":
        skipped_tests = "not slow and superslow"
    else:
        raise ValueError(f"Invalid `test_list_name`={test_list_name}")
    return skipped_tests


def _build_run_command_line(
    test_list_name: str,
    custom_marker: str,
    pytest_opts: str,
    skip_submodules: bool,
    coverage: bool,
    collect_only: bool,
    tee_to_file: bool,
    n_threads: str,
) -> str:
    """
    Build the pytest run command.

    E.g.,

    ```
    pytest -m "optimizer and not slow and not superslow" \
                . \
                -o timeout_func_only=true \
                --timeout 5 \
                --reruns 2 \
                --only-rerun "Failed: Timeout"
    ```

    The rest of params are the same as in `run_fast_tests()`.

    The invariant is that we don't want to duplicate pytest options that can be
    passed by the user through `-p` (unless really necessary).

    :param test_list_name: "fast_tests", "slow_tests" or
        "superslow_tests"
    :param custom_marker: specify a space separated list of
        `pytest` markers to skip (e.g., `optimizer` for the optimizer
        tests, see `pytest.ini`). Empty means no marker to skip
    """
    hdbg.dassert_in(
        test_list_name, _TEST_TIMEOUTS_IN_SECS, "Invalid test_list_name"
    )
    pytest_opts = pytest_opts or "."
    pytest_opts_tmp = []

    # Select tests to skip based on the `test_list_name` (e.g., fast tests)
    # and on the custom marker, if present.
    skipped_tests = _select_tests_to_skip(test_list_name)
    if custom_marker != "":
        pytest_opts_tmp.append(f'-m "{custom_marker} and {skipped_tests}"')
    else:
        pytest_opts_tmp.append(f'-m "{skipped_tests}"')
    if pytest_opts:
        pytest_opts_tmp.append(pytest_opts)
    timeout_in_sec = _TEST_TIMEOUTS_IN_SECS[test_list_name]
    # Adding `timeout_func_only` is a workaround for
    # https://github.com/pytest-dev/pytest-rerunfailures/issues/99. Because of
    # it, we limit only run time, without setup and teardown time.
    pytest_opts_tmp.append("-o timeout_func_only=true")
    pytest_opts_tmp.append(f"--timeout {timeout_in_sec}")
    num_reruns = _NUM_TIMEOUT_TEST_RERUNS[test_list_name]
    pytest_opts_tmp.append(
        f'--reruns {num_reruns} --only-rerun "Failed: Timeout"'
    )
    if hgit.execute_repo_config_code("skip_submodules_test()"):
        # For some repos (e.g. `dev_tools`) submodules should be skipped
        # regardless of the passed value.
        skip_submodules = True
    if skip_submodules:
        submodule_paths = hgit.get_submodule_paths()
        _LOG.warning(
            "Skipping %d submodules: %s", len(submodule_paths), submodule_paths
        )
        pytest_opts_tmp.append(
            " ".join([f"--ignore {path}" for path in submodule_paths])
        )
    if coverage:
        pytest_opts_tmp.append(" ".join(_COV_PYTEST_OPTS))
    if collect_only:
        _LOG.warning("Only collecting tests as per user request")
        pytest_opts_tmp.append("--collect-only")
    # Indicate the number of threads for parallelization.
    pytest_opts_tmp.append(f"-n {str(n_threads)}")
    # Concatenate the options.
    _LOG.debug("pytest_opts_tmp=\n%s", str(pytest_opts_tmp))
    pytest_opts_tmp = [po for po in pytest_opts_tmp if po != ""]
    # TODO(gp): Use _to_multi_line_cmd()
    pytest_opts = " ".join([po.rstrip().lstrip() for po in pytest_opts_tmp])
    cmd = f"pytest {pytest_opts}"
    if tee_to_file:
        cmd += f" 2>&1 | tee tmp.pytest.{test_list_name}.log"
    return cmd


def _run_test_cmd(
    ctx: Any,
    stage: str,
    version: str,
    cmd: str,
    coverage: bool,
    collect_only: bool,
    start_coverage_script: bool,
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    """
    See params in `run_fast_tests()`.
    """
    if collect_only:
        # Clean files.
        _run(ctx, "rm -rf ./.coverage*")
    # Run.
    base_image = ""
    # We need to add some " to pass the string as it is to the container.
    cmd = f"'{cmd}'"
    # We use "host" for the app container to allow access to the database
    # exposing port 5432 on localhost (of the server), when running dind we
    # need to switch back to bridge. See CmTask988.
    extra_env_vars = ["NETWORK_MODE=bridge"]
    docker_cmd_ = _get_docker_cmd(
        base_image, stage, version, cmd, extra_env_vars=extra_env_vars
    )
    _LOG.info("cmd=%s", docker_cmd_)
    # We can't use `hsystem.system()` because of buffering of the output,
    # losing formatting and so on, so we stick to executing through `ctx`.
    rc = _docker_cmd(ctx, docker_cmd_, **ctx_run_kwargs)
    # Print message about coverage.
    if coverage:
        msg = """
- The coverage results in textual form are above

- To browse the files annotate with coverage, start a server (not from the
  container):
  > (cd ./htmlcov; python -m http.server 33333)
- Then go with your browser to `localhost:33333` to see which code is
  covered
"""
        print(msg)
        if start_coverage_script:
            # Create and run a script to show the coverage in the browser.
            script_txt = """(sleep 2; open http://localhost:33333) &
(cd ./htmlcov; python -m http.server 33333)"""
            script_name = "./tmp.coverage.sh"
            hio.create_executable_script(script_name, script_txt)
            coverage_rc = hsystem.system(script_name)
            if coverage_rc != 0:
                _LOG.warning(
                    "Setting `rc` to `0` even though the coverage script fails."
                )
                rc = 0
    return rc


def _run_tests(
    ctx: Any,
    test_list_name: str,
    stage: str,
    version: str,
    custom_marker: str,
    pytest_opts: str,
    skip_submodules: bool,
    coverage: bool,
    collect_only: bool,
    tee_to_file: bool,
    n_threads: str,
    git_clean_: bool,
    *,
    start_coverage_script: bool = False,
    **ctx_run_kwargs: Any,
) -> Optional[int]:
    """
    See params in `run_fast_tests()`.
    """
    if git_clean_:
        cmd = "invoke git_clean --fix-perms"
        _run(ctx, cmd)
    # Build the command line.
    cmd = _build_run_command_line(
        test_list_name,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
    )
    # Execute the command line.
    rc = _run_test_cmd(
        ctx,
        stage,
        version,
        cmd,
        coverage,
        collect_only,
        start_coverage_script,
        **ctx_run_kwargs,
    )
    return rc


@task
# TODO(Grisha): "Unit tests run_*_tests invokes" CmTask #1652.
def run_tests(  # type: ignore
    ctx,
    test_lists,
    abort_on_first_error=False,
    stage="dev",
    version="",
    custom_marker="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
    **kwargs,
):
    """
    :param test_lists: comma separated list with test lists to run (e.g., `fast_test,slow_tests`)
    :param abort_on_first_error: stop after the first test list failing
    """
    results = []
    for test_list_name in test_lists.split(","):
        rc = _run_tests(
            ctx,
            test_list_name,
            stage,
            version,
            custom_marker,
            pytest_opts,
            skip_submodules,
            coverage,
            collect_only,
            tee_to_file,
            n_threads,
            git_clean_,
            warn=True,
            **kwargs,
        )
        if rc != 0:
            _LOG.error("'%s' tests failed", test_list_name)
            if abort_on_first_error:
                sys.exit(-1)
        results.append((test_list_name, rc))
    #
    rc = any(result[1] for result in results)
    # Summarize the results.
    _LOG.info("# Tests run summary:")
    for test_list_name, rc in results:
        if rc != 0:
            _LOG.error("'%s' tests failed", test_list_name)
        else:
            _LOG.info("'%s' tests succeeded", test_list_name)
    return rc


# TODO(gp): Pass a test_list in fast, slow, ... instead of duplicating all the code CmTask #1571.
@task
def run_fast_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
    **kwargs,
):
    """
    Run fast tests.

    :param stage: select a specific stage for the Docker image
    :param pytest_opts: additional options for `pytest` invocation. It can be empty
    :param skip_submodules: ignore all the dir inside a submodule
    :param coverage: enable coverage computation
    :param collect_only: do not run tests but show what will be executed
    :param tee_to_file: save output of pytest in `tmp.pytest.log`
    :param n_threads: the number of threads to run the tests with
        - "auto": distribute the tests across all the available CPUs
    :param git_clean_: run `invoke git_clean --fix-perms` before running the tests
    :param kwargs: kwargs for `ctx.run`
    """
    _report_task()
    test_list_name = "fast_tests"
    custom_marker = ""
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        **kwargs,
    )
    return rc


@task
def run_slow_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
    **kwargs,
):
    """
    Run slow tests.

    Same params as `invoke run_fast_tests`.
    """
    _report_task()
    test_list_name = "slow_tests"
    custom_marker = ""
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        **kwargs,
    )
    return rc


@task
def run_superslow_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
    **kwargs,
):
    """
    Run superslow tests.

    Same params as `invoke run_fast_tests`.
    """
    _report_task()
    test_list_name = "superslow_tests"
    custom_marker = ""
    rc = _run_tests(
        ctx,
        test_list_name,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
        **kwargs,
    )
    return rc


@task
def run_fast_slow_tests(  # type: ignore
    ctx,
    abort_on_first_error=False,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
):
    """
    Run fast and slow tests back-to-back.

    Same params as `invoke run_fast_tests`.
    """
    _report_task()
    # Run fast tests but do not fail on error.
    test_lists = "fast_tests,slow_tests"
    custom_marker = ""
    rc = run_tests(
        ctx,
        test_lists,
        abort_on_first_error,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
    )
    return rc


@task
def run_fast_slow_superslow_tests(  # type: ignore
    ctx,
    abort_on_first_error=False,
    stage="dev",
    version="",
    pytest_opts="",
    skip_submodules=False,
    coverage=False,
    collect_only=False,
    tee_to_file=False,
    n_threads="1",
    git_clean_=False,
):
    """
    Run fast, slow, superslow tests back-to-back.

    Same params as `invoke run_fast_tests`.
    """
    _report_task()
    # Run fast tests but do not fail on error.
    test_lists = "fast_tests,slow_tests,superslow_tests"
    custom_marker = ""
    rc = run_tests(
        ctx,
        test_lists,
        abort_on_first_error,
        stage,
        version,
        custom_marker,
        pytest_opts,
        skip_submodules,
        coverage,
        collect_only,
        tee_to_file,
        n_threads,
        git_clean_,
    )
    return rc


@task
def run_qa_tests(  # type: ignore
    ctx,
    stage="dev",
    version="",
):
    """
    Run QA tests independently.

    :param version: version to tag the image and code with
    :param stage: select a specific stage for the Docker image
    """
    _report_task()
    #
    qa_test_fn = get_default_param("QA_TEST_FUNCTION")
    # Run the call back function.
    rc = qa_test_fn(ctx, stage, version)
    if not rc:
        msg = "QA tests failed"
        _LOG.error(msg)
        raise RuntimeError(msg)


def _publish_html_coverage_report_on_s3(aws_profile: str) -> None:
    """
    Publish HTML coverage report on S3 so that it can be accessed via browser.

    Target S3 dir is constructed from linux user and Git branch name, e.g.
    `s3://...-html/html_coverage/grisha_CmTask1047_fix_tests`.
    """
    # Build the dir name from user and branch name.
    user = hsystem.get_user_name()
    branch_name = hgit.get_branch_name()
    _LOG.debug("User='%s', branch_name='%s'", user, branch_name)
    s3_html_coverage_dir = f"{user}_{branch_name}"
    # Get the full path to the dir.
    s3_html_base_dir = "html_coverage"
    s3_html_bucket_path = hgit.execute_repo_config_code("get_html_bucket_path()")
    s3_html_coverage_path = os.path.join(
        s3_html_bucket_path, s3_html_base_dir, s3_html_coverage_dir
    )
    # Copy HTML coverage data from the local dir to S3.
    local_coverage_path = "./htmlcov"
    cp_cmd = (
        f"aws s3 cp {local_coverage_path} {s3_html_coverage_path} "
        f"--recursive --profile {aws_profile}"
    )
    _LOG.info(
        "HTML coverage report is published on S3: path=`%s`",
        s3_html_coverage_path,
    )
    hsystem.system(cp_cmd)


@task
def run_coverage_report(  # type: ignore
    ctx,
    target_dir,
    generate_html_report=True,
    publish_html_on_s3=True,
    aws_profile="ck",
):
    """
    Compute test coverage stats.

    The flow is:
       - Run tests and compute coverage stats for each test type
       - Combine coverage stats in a single file
       - Generate a text report
       - Generate a HTML report (optional)
          - Post it on S3 (optional)

    :param target_dir: directory to compute coverage stats for
    :param generate_html_report: whether to generate HTML coverage report or not
    :param publish_html_on_s3: whether to publish HTML coverage report or not
    :param aws_profile: the AWS profile to use for publishing HTML report
    """
    # TODO(Grisha): allow user to specify which tests to run.
    # Run tests for the target dir and collect coverage stats.
    fast_tests_cmd = (
        f"invoke run_fast_tests --coverage -p {target_dir}; "
        "cp .coverage .coverage_fast_tests"
    )
    _run(ctx, fast_tests_cmd)
    slow_tests_cmd = (
        f"invoke run_slow_tests --coverage -p {target_dir}; "
        "cp .coverage .coverage_slow_tests"
    )
    _run(ctx, slow_tests_cmd)
    #
    report_cmd: List[str] = []
    # Clean the previous coverage results. For some docker-specific reasons
    # command which combines stats does not work when being run first in
    # the chain `bash -c "cmd1 && cmd2 && cmd3"`. So `erase` command which
    # does not affect the coverage results was added as a workaround.
    report_cmd.append("coverage erase")
    # Merge stats for fast and slow tests into single dir.
    report_cmd.append(
        "coverage combine --keep .coverage_fast_tests .coverage_slow_tests"
    )
    # Only target dir is included in the reports.
    include_in_report = f"*/{target_dir}/*"
    # Generate text report with the coverage stats.
    report_cmd.append(
        f"coverage report --include={include_in_report} --sort=Cover"
    )
    if generate_html_report:
        # Generate HTML report with the coverage stats.
        report_cmd.append(f"coverage html --include={include_in_report}")
    # Execute commands above one-by-one inside docker. Coverage tool is not
    # installed outside docker.
    full_report_cmd = " && ".join(report_cmd)
    docker_cmd_ = f"invoke docker_cmd --use-bash --cmd '{full_report_cmd}'"
    _run(ctx, docker_cmd_)
    if publish_html_on_s3:
        # Publish HTML report on S3.
        _publish_html_coverage_report_on_s3(aws_profile)


# #############################################################################
# Pytest helpers.
# #############################################################################


# TODO(gp): Consolidate the code from dev_scripts/testing here.


@task
def traceback(ctx, log_name="tmp.pytest_script.log", purify=True):  # type: ignore
    """
    Parse the traceback from Pytest and navigate it with vim.

    ```
    # Run a unit test.
    > pytest helpers/test/test_traceback.py 2>&1 | tee tmp.pytest.log
    > pytest.sh helpers/test/test_traceback.py
    # Parse the traceback
    > invoke traceback -i tmp.pytest.log
    ```

    :param log_name: the file with the traceback
    :param purify: purify the filenames from client (e.g., from running inside Docker)
    """
    _report_task()
    #
    dst_cfile = "cfile"
    hio.delete_file(dst_cfile)
    # Convert the traceback into a cfile.
    cmd = []
    cmd.append("traceback_to_cfile.py")
    if log_name:
        cmd.append(f"-i {log_name}")
    cmd.append(f"-o {dst_cfile}")
    # Purify the file names.
    if purify:
        cmd.append("--purify_from_client")
    else:
        cmd.append("--no_purify_from_client")
    cmd = " ".join(cmd)
    _run(ctx, cmd)
    # Read and navigate the cfile with vim.
    if os.path.exists(dst_cfile):
        cmd = 'vim -c "cfile cfile"'
        _run(ctx, cmd, pty=True)
    else:
        _LOG.warning("Can't find %s", dst_cfile)


@task
def pytest_clean(ctx):  # type: ignore
    """
    Clean pytest artifacts.
    """
    _report_task()
    _ = ctx
    import helpers.hpytest as hpytest

    hpytest.pytest_clean(".")


def _get_failed_tests_from_file(file_name: str) -> List[str]:
    hdbg.dassert_file_exists(file_name)
    txt = hio.from_file(file_name)
    if file_name.endswith("/cache/lastfailed"):
        # Decode the json-style string.
        # {
        # "vendors/test/test_vendors.py::Test_gp::test1": true,
        # "vendors/test/test_vendors.py::Test_kibot_utils1::...": true,
        # }
        vals = json.loads(txt)
        hdbg.dassert_isinstance(vals, dict)
        tests = [k for k, v in vals.items() if v]
    else:
        # Extract failed tests from the regular text output.
        tests = re.findall(r"FAILED (\S+\.py::\S+::\S+)\b", txt)
    return tests


@task
def pytest_repro(  # type: ignore
    ctx,
    mode="tests",
    file_name="./.pytest_cache/v/cache/lastfailed",
    show_stacktrace=False,
    create_script=True,
):
    """
    Generate commands to reproduce the failed tests after a `pytest` run.

    The workflow is:
    ```
    # Run a lot of tests, e.g., the entire regression suite.
    server> i run_fast_slow_tests 2>&1 | log pytest.txt
    docker> pytest ... 2>&1 | log pytest.txt

    # Run the `pytest_repro` to summarize test failures and to generate
    # commands to reproduce them.
    server> i pytest_repro
    ```

    :param mode: the granularity level for generating the commands
        - "tests" (default): failed test methods, e.g.,
            ```
            pytest helpers/test/test_cache.py::TestCachingOnS3::test_with_caching1
            pytest helpers/test/test_cache.py::TestCachingOnS3::test_with_caching2
            ```
        - "classes": classes of the failed tests, e.g.,
            ```
            pytest helpers/test/test_cache.py::TestCachingOnS3
            pytest helpers/test/test_cache.py::TestCachingOnS3_2
            ```
        - "files": files with the failed tests, e.g.,
            ```
            pytest helpers/test/test_cache.py
            pytest helpers/test/test_lib_tasks.py
            ```
    :param file_name: the name of the file containing the pytest output file to parse
    :param show_stacktrace: whether to show the stacktrace of the failed tests
      - only if it is available in the pytest output file
    :param create_script: create a script to run the tests
    :return: commands to reproduce pytest failures at the requested granularity level
    """
    _report_task()
    _ = ctx
    # Read file.
    _LOG.info("Reading file_name='%s'", file_name)
    hdbg.dassert_file_exists(file_name)
    _LOG.info("Reading failed tests from file '%s'", file_name)
    # E.g., vendors/test/test_vendors.py::Test_gp::test1
    tests = _get_failed_tests_from_file(file_name)
    if len(tests) == 0:
        _LOG.info("Found 0 failed tests")
        return ""
    _LOG.debug("tests=%s", str(tests))
    # Process the tests.
    targets = []
    for test in tests:
        data = test.split("::")
        hdbg.dassert_lte(len(data), 3, "Can't parse '%s'", test)
        # E.g., dev_scripts/testing/test/test_run_tests.py
        # E.g., helpers/test/helpers/test/test_list.py::Test_list_1
        # E.g., core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5
        test_file_name = test_class = test_method = ""
        if len(data) >= 1:
            test_file_name = data[0]
        if len(data) >= 2:
            test_class = data[1]
        if len(data) >= 3:
            test_method = data[2]
        _LOG.debug(
            "test=%s -> (%s, %s, %s)",
            test,
            test_file_name,
            test_class,
            test_method,
        )
        if mode == "tests":
            targets.append(test)
        elif mode == "files":
            if test_file_name != "":
                targets.append(test_file_name)
            else:
                _LOG.warning(
                    "Skipping test='%s' since test_file_name='%s'",
                    test,
                    test_file_name,
                )
        elif mode == "classes":
            if test_file_name != "" and test_class != "":
                targets.append(f"{test_file_name}::{test_class}")
            else:
                _LOG.warning(
                    "Skipping test='%s' since test_file_name='%s', test_class='%s'",
                    test,
                    test_file_name,
                    test_class,
                )
        else:
            hdbg.dfatal(f"Invalid mode='{mode}'")
    # Package the output.
    # targets is a list of tests in the format
    # `helpers/test/test_env.py::Test_env1::test_get_system_signature1`.
    hdbg.dassert_isinstance(targets, list)
    targets = hlist.remove_duplicates(targets)
    failed_test_output_str = (
        f"Found {len(targets)} failed pytest '{mode}' target(s); "
        "to reproduce run:\n"
    )
    res = [f"pytest {t}" for t in targets]
    res = "\n".join(res)
    failed_test_output_str += res
    #
    if show_stacktrace:
        # Get the stacktrace block from the pytest output.
        txt = hio.from_file(file_name)
        if (
            "====== FAILURES ======" in txt
            and "====== slowest 3 durations ======" in txt
        ):
            failures_blocks = txt.split("====== FAILURES ======")[1:]
            failures_blocks = [
                x.split("====== slowest 3 durations ======")[0]
                for x in failures_blocks
            ]
            txt = "\n".join([x.rstrip("=").lstrip("=") for x in failures_blocks])
            # Get the classes and names of the failed tests, e.g.
            # "core/dataflow/nodes/test/test_volatility_models.py::TestSmaModel::test5" ->
            # -> "TestSmaModel.test5".
            failed_test_names = [
                test.split("::")[1] + "." + test.split("::")[2] for test in tests
            ]
            tracebacks = []
            for name in failed_test_names:
                # Get the stacktrace for the individual test failure.
                # Its start is marked with the name of the test, e.g.
                # "___________________ TestSmaModel.test5 ___________________".
                start_block = "________ " + name + " ________"
                traceback_block = txt.rsplit(start_block, maxsplit=1)[-1]
                end_block_options = [
                    "________ " + n + " ________"
                    for n in failed_test_names
                    if n != name
                ]
                for end_block in end_block_options:
                    # The end of the traceback for the current failed test is the
                    # start of the traceback for the next failed test.
                    if end_block in traceback_block:
                        traceback_block = traceback_block.split(end_block)[0]
                _, traceback_ = htraceb.parse_traceback(
                    traceback_block, purify_from_client=False
                )
                tracebacks.append(
                    "\n".join(["# " + name, traceback_.strip(), ""])
                )
            # Combine the stacktraces for all the failures.
            full_traceback = "\n\n" + "\n".join(tracebacks)
            failed_test_output_str += full_traceback
            res += full_traceback
    _LOG.info("%s", failed_test_output_str)
    if create_script:
        script_name = "./tmp.pytest_repro.sh"
        cmd = "pytest " + " ".join(targets)
        msg = "To run the tests"
        hio.create_executable_script(script_name, cmd, msg=msg)
    return res


# #############################################################################


def _purify_test_output(src_file_name: str, dst_file_name: str) -> None:
    """
    Clean up the output of `pytest -s --dbg` to make easier to compare two
    runs.

    E.g., remove the timestamps, reference to Git repo.
    """
    _LOG.info("Converted '%s' -> '%s", src_file_name, dst_file_name)
    txt = hio.from_file(src_file_name)
    out_txt = []
    for line in txt.split("\n"):
        # 10:05:18       portfolio        : _get_holdings       : 431 :
        m = re.match(r"^\d\d:\d\d:\d\d\s+(.*:.*)$", line)
        if m:
            new_line = m.group(1)
        else:
            new_line = line
        out_txt.append(new_line)
    #
    out_txt = "\n".join(out_txt)
    hio.to_file(dst_file_name, out_txt)


@task
def pytest_compare(ctx, file_name1, file_name2):  # type: ignore
    """
    Compare the output of two runs of `pytest -s --dbg` removing irrelevant
    details.
    """
    _report_task()
    _ = ctx
    # TODO(gp): Change the name of the file before the extension.
    dst_file_name1 = file_name1 + ".purified"
    _purify_test_output(file_name1, dst_file_name1)
    dst_file_name2 = file_name2 + ".purified"
    _purify_test_output(file_name2, dst_file_name2)
    # TODO(gp): Call vimdiff automatically.
    cmd = f"vimdiff {dst_file_name1} {dst_file_name2}"
    print(f"> {cmd}")


# #############################################################################


@task
def pytest_rename_test(ctx, old_test_class_name, new_test_class_name):  # type: ignore
    """
    Rename the test and move its golden outcome.

    E.g., to rename a test class and all the test methods:
    > i pytest_rename_test TestCacheUpdateFunction1 TestCacheUpdateFunction_new

    :param old_test_class_name: old class name
    :param new_test_class_name: new class name
    """
    _report_task()
    _ = ctx
    root_dir = os.getcwd()
    renamer = hunteuti.UnitTestRenamer(
        old_test_class_name, new_test_class_name, root_dir
    )
    renamer.run()


# #############################################################################


@task
def pytest_find_unused_goldens(  # type: ignore
    ctx,
    dir_name=".",
    run_bash=False,
    stage="prod",
    as_user=True,
    out_file_name="pytest_find_unused_goldens.output.txt",
):
    """
    Detect mismatches between tests and their golden outcome files.

    - When goldens are required by the tests but the corresponding files
      do not exist
    - When the existing golden files are not actually required by the
      corresponding tests

    :param dir_name: the head dir to start the check from
    """
    _report_task()
    # Remove the log file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        _run(ctx, cmd)
    as_user = _run_docker_as_user(as_user)
    # Prepare the command line.
    amp_abs_path = hgit.get_amp_abs_path()
    amp_path = amp_abs_path.replace(
        os.path.commonpath([os.getcwd(), amp_abs_path]), ""
    )
    script_path = os.path.join(
        amp_path, "dev_scripts/find_unused_golden_files.py"
    ).lstrip("/")
    docker_cmd_opts = [f"--dir_name {dir_name}"]
    docker_cmd_ = f"{script_path} " + _to_single_line_cmd(docker_cmd_opts)
    # Execute command line.
    cmd = _get_lint_docker_cmd(docker_cmd_, run_bash, stage, as_user)
    cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
    # Run.
    _run(ctx, cmd)


# #############################################################################
# Linter.
# #############################################################################


@task
def lint_check_python_files_in_docker(  # type: ignore
    ctx,
    python_compile=True,
    python_execute=True,
    modified=False,
    branch=False,
    last_commit=False,
    all_=False,
    files="",
):
    """
    Compile and execute Python files checking for errors.

    This is supposed to be run inside Docker.

    The params have the same meaning as in `_get_files_to_process()`.
    """
    _report_task()
    _ = ctx
    # We allow to filter through the user specified `files`.
    mutually_exclusive = False
    remove_dirs = True
    file_list = _get_files_to_process(
        modified,
        branch,
        last_commit,
        all_,
        files,
        mutually_exclusive,
        remove_dirs,
    )
    _LOG.debug("Found %d files:\n%s", len(file_list), "\n".join(file_list))
    # Filter keeping only Python files.
    _LOG.debug("Filtering for Python files")
    exclude_paired_jupytext = True
    file_list = hio.keep_python_files(file_list, exclude_paired_jupytext)
    _LOG.debug("file_list=%s", "\n".join(file_list))
    _LOG.info("Need to process %d files", len(file_list))
    if not file_list:
        _LOG.warning("No files were selected")
    # Scan all the files.
    failed_filenames = []
    for file_name in file_list:
        _LOG.info("Processing '%s'", file_name)
        if python_compile:
            import compileall

            success = compileall.compile_file(file_name, force=True, quiet=1)
            _LOG.debug("file_name='%s' -> python_compile=%s", file_name, success)
            if not success:
                msg = f"'{file_name}' doesn't compile correctly"
                _LOG.error(msg)
                failed_filenames.append(file_name)
        # TODO(gp): Add also `python -c "import ..."`, if not equivalent to `compileall`.
        if python_execute:
            cmd = f"python {file_name}"
            rc = hsystem.system(cmd, abort_on_error=False, suppress_output=False)
            _LOG.debug("file_name='%s' -> python_compile=%s", file_name, rc)
            if rc != 0:
                msg = f"'{file_name}' doesn't execute correctly"
                _LOG.error(msg)
                failed_filenames.append(file_name)
    hprint.log_frame(
        _LOG,
        f"failed_filenames={len(failed_filenames)}",
        verbosity=logging.INFO,
    )
    _LOG.info("\n".join(failed_filenames))
    error = len(failed_filenames) > 0
    return error


@task
def lint_check_python_files(  # type: ignore
    ctx,
    python_compile=True,
    python_execute=True,
    modified=False,
    branch=False,
    last_commit=False,
    all_=False,
    files="",
):
    """
    Compile and execute Python files checking for errors.

    The params have the same meaning as in `_get_files_to_process()`.
    """
    _ = python_compile, python_execute, modified, branch, last_commit, all_, files
    # Execute the same command line but inside the container. E.g.,
    # /Users/saggese/src/venv/amp.client_venv/bin/invoke lint_docker_check_python_files --branch
    cmd_line = hdbg.get_command_line()
    # Replace the full path of invoke with just `invoke`.
    cmd_line = cmd_line.split()
    cmd_line = ["/venv/bin/invoke lint_check_python_files_in_docker"] + cmd_line[
        2:
    ]
    docker_cmd_ = " ".join(cmd_line)
    cmd = f'invoke docker_cmd --cmd="{docker_cmd_}"'
    _run(ctx, cmd)


def _get_lint_docker_cmd(
    docker_cmd_: str,
    run_bash: bool,
    stage: str,
    as_user: bool,
) -> str:
    """
    Create a command to run in Docker.

    For parameter descriptions, see `lint()`.

    :param docker_cmd_: command to run inside the container
    :return: the full command to run in Docker
    """
    superproject_path, submodule_path = hgit.get_path_from_supermodule()
    if superproject_path:
        # We are running in a Git submodule.
        work_dir = f"/src/{submodule_path}"
        repo_root = superproject_path
    else:
        work_dir = "/src"
        repo_root = os.getcwd()
    _LOG.debug("work_dir=%s repo_root=%s", work_dir, repo_root)
    # TODO(gp): Do not hardwire the repo_short_name.
    # image = get_default_param("DEV_TOOLS_IMAGE_PROD")
    # image="*****.dkr.ecr.us-east-1.amazonaws.com/dev_tools:local"
    ecr_base_path = os.environ["AM_ECR_BASE_PATH"]
    image = f"{ecr_base_path}/dev_tools:{stage}"
    docker_wrapper_cmd = ["docker run", "--rm"]
    if stage in ("local", "dev"):
        # Map repository root to /app in the container, so that we can
        # reuse the current code being developed inside Docker before
        # releasing the prod image.
        docker_wrapper_cmd.append(f"-v '{repo_root}':/app")
    if run_bash:
        docker_wrapper_cmd.append("-it")
    else:
        docker_wrapper_cmd.append("-t")
    if as_user:
        docker_wrapper_cmd.append(r"--user $(id -u):$(id -g)")
    docker_wrapper_cmd.extend(
        [
            # Pass MYPYPATH for `mypy` to find the packages from PYTHONPATH.
            "-e MYPYPATH",
            f"-v '{repo_root}':/src",
            f"--workdir={work_dir}",
            f"{image}",
        ]
    )
    # Build the command inside Docker.
    cmd = f"'{docker_cmd_}'"
    if run_bash:
        _LOG.warning("Run bash instead of:\n  > %s", cmd)
        cmd = "bash"
    docker_wrapper_cmd.append(cmd)
    docker_wrapper_cmd = _to_single_line_cmd(docker_wrapper_cmd)
    if run_bash:
        # We don't execute this command since pty=True corrupts the terminal
        # session.
        print("# To get a bash session inside Docker run:")
        print(docker_wrapper_cmd)
        sys.exit(0)
    return docker_wrapper_cmd


def _parse_linter_output(txt: str) -> str:
    """
    Parse the output of the linter and return a file suitable for vim quickfix.
    """
    stage: Optional[str] = None
    output: List[str] = []
    for i, line in enumerate(txt.split("\n")):
        _LOG.debug("%d:line='%s'", i + 1, line)
        # Tabs remover...............................................Passed
        # isort......................................................Failed
        # Don't commit to branch...............................^[[42mPassed^[[m
        m = re.search(r"^(\S.*?)\.{10,}\S+?(Passed|Failed)\S*?$", line)
        if m:
            stage = m.group(1)
            result = m.group(2)
            _LOG.debug("  -> stage='%s' (%s)", stage, result)
            continue
        # core/dataflow/nodes.py:601:9: F821 undefined name '_check_col_names'
        m = re.search(r"^(\S+):(\d+)[:\d+:]\s+(.*)$", line)
        if m:
            _LOG.debug("  -> Found a lint to parse: '%s'", line)
            hdbg.dassert_is_not(stage, None)
            file_name = m.group(1)
            line_num = int(m.group(2))
            msg = m.group(3)
            _LOG.debug(
                "  -> file_name='%s' line_num=%d msg='%s'",
                file_name,
                line_num,
                msg,
            )
            output.append(f"{file_name}:{line_num}:[{stage}] {msg}")
    # Sort to keep the lints in order of files.
    output = sorted(output)
    output_as_str = "\n".join(output)
    return output_as_str


@task
def lint_detect_cycles(  # type: ignore
    ctx,
    dir_name=".",
    run_bash=False,
    # TODO(gp): This is the backdoor.
    stage="prod",
    as_user=True,
    out_file_name="lint_detect_cycles.output.txt",
):
    """
    Detect cyclic imports in the directory files.

    For param descriptions, see `lint()`.

    :param dir_name: the name of the dir to detect cyclic imports in
        - By default, the check will be carried out in the dir from where
          the task is run
    """
    _report_task()
    # Remove the log file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        _run(ctx, cmd)
    as_user = _run_docker_as_user(as_user)
    # Prepare the command line.
    docker_cmd_opts = [dir_name]
    docker_cmd_ = (
        "/app/import_check/detect_import_cycles.py "
        + _to_single_line_cmd(docker_cmd_opts)
    )
    # Execute command line.
    cmd = _get_lint_docker_cmd(docker_cmd_, run_bash, stage, as_user)
    cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
    # Run.
    _run(ctx, cmd)


# pylint: disable=line-too-long
@task
def lint(  # type: ignore
    ctx,
    modified=False,
    branch=False,
    last_commit=False,
    files="",
    dir_name="",
    phases="",
    only_format=False,
    only_check=False,
    fast=False,
    # stage="prod",
    run_bash=False,
    run_linter_step=True,
    parse_linter_output=True,
    stage="prod",
    as_user=True,
    out_file_name="linter_output.txt",
):
    """
    Lint files.

    ```
    # To lint all the files:
    > i lint --dir-name . --only-format

    # To lint only a repo (e.g., lime, lemonade) including `amp` but not `amp` itself:
    > i lint --files="$(find . -name '*.py' -not -path './compute/*' -not -path './amp/*')"

    # To lint dev_tools:
    > i lint --files="$(find . -name '*.py' -not -path './amp/*' -not -path './import_check/example/*' -not -path './import_check/test/outcomes/*')"
    ```

    :param modified: select the files modified in the client
    :param branch: select the files modified in the current branch
    :param last_commit: select the files modified in the previous commit
    :param files: specify a space-separated list of files
    :param dir_name: process all the files in a dir
    :param phases: specify the lint phases to execute
    :param only_format: run only the formatting phases (e.g., black)
    :param only_check: run only the checking phases (e.g., pylint, mypy) that
        don't change the code
    :param fast: run everything but skip `pylint`, since it is often very picky
        and slow
    :param run_bash: instead of running pre-commit, run bash to debug
    :param run_linter_step: run linter step
    :param parse_linter_output: parse linter output and generate vim cfile
    :param stage: the image stage to use
    :param as_user: pass the user / group id or not
    :param out_file_name: name of the file to save the log output in
    """
    _report_task()
    # Remove the file.
    if os.path.exists(out_file_name):
        cmd = f"rm {out_file_name}"
        _run(ctx, cmd)
    # The available phases are:
    # ```
    # > i lint -f "foobar.py"
    # Don't commit to branch...............................................Passed
    # Check for merge conflicts........................(no files to check)Skipped
    # Trim Trailing Whitespace.........................(no files to check)Skipped
    # Fix End of Files.................................(no files to check)Skipped
    # Check for added large files......................(no files to check)Skipped
    # CRLF end-lines remover...........................(no files to check)Skipped
    # Tabs remover.....................................(no files to check)Skipped
    # autoflake........................................(no files to check)Skipped
    # add_python_init_files............................(no files to check)Skipped
    # amp_lint_md......................................(no files to check)Skipped
    # amp_doc_formatter................................(no files to check)Skipped
    # amp_isort........................................(no files to check)Skipped
    # amp_class_method_order...........................(no files to check)Skipped
    # amp_normalize_import.............................(no files to check)Skipped
    # amp_format_separating_line.......................(no files to check)Skipped
    # amp_black........................................(no files to check)Skipped
    # amp_processjupytext..............................(no files to check)Skipped
    # amp_check_filename...............................(no files to check)Skipped
    # amp_warn_incorrectly_formatted_todo..............(no files to check)Skipped
    # amp_flake8.......................................(no files to check)Skipped
    # amp_pylint.......................................(no files to check)Skipped
    # amp_mypy.........................................(no files to check)Skipped
    # ```
    if only_format:
        hdbg.dassert_eq(phases, "")
        phases = " ".join(
            [
                "add_python_init_files",
                "amp_isort",
                "amp_class_method_order",
                "amp_normalize_import",
                "amp_format_separating_line",
                "amp_black",
                "amp_processjupytext",
                "amp_remove_eof_newlines",
            ]
        )
    if only_check:
        hdbg.dassert_eq(phases, "")
        phases = " ".join(
            [
                "amp_pylint",
                "amp_mypy",
            ]
        )
    if run_linter_step:
        # We don't want to run this all the times.
        # docker_pull(ctx, stage=stage, images="dev_tools")
        # Get the files to lint.
        # TODO(gp): For now we don't support linting the entire tree.
        all_ = False
        if dir_name != "":
            hdbg.dassert_eq(files, "")
            pattern = "*.py"
            only_files = True
            use_relative_paths = False
            files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
            files = " ".join(files)
        # For linting we can use only files modified in the client, in the branch, or
        # specified.
        mutually_exclusive = True
        # pre-commit doesn't handle directories, but only files.
        remove_dirs = True
        files_as_list = _get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files,
            mutually_exclusive,
            remove_dirs,
        )
        _LOG.info("Files to lint:\n%s", "\n".join(files_as_list))
        if not files_as_list:
            _LOG.warning("Nothing to lint: exiting")
            return
        files_as_str = " ".join(files_as_list)
        phases = phases.split(" ")
        as_user = _run_docker_as_user(as_user)
        for phase in phases:
            # Prepare the command line.
            precommit_opts = []
            precommit_opts.extend(
                [
                    f"run {phase}",
                    "-c /app/.pre-commit-config.yaml",
                    f"--files {files_as_str}",
                ]
            )
            docker_cmd_ = "pre-commit " + _to_single_line_cmd(precommit_opts)
            if fast:
                docker_cmd_ = "SKIP=amp_pylint " + docker_cmd_
            # Execute command line.
            cmd = _get_lint_docker_cmd(docker_cmd_, run_bash, stage, as_user)
            cmd = f"({cmd}) 2>&1 | tee -a {out_file_name}"
            # Run.
            _run(ctx, cmd)
    else:
        _LOG.warning("Skipping linter step, as per user request")
    #
    if parse_linter_output:
        # Parse the linter output into a cfile.
        _LOG.info("Parsing '%s'", out_file_name)
        txt = hio.from_file(out_file_name)
        cfile = _parse_linter_output(txt)
        cfile_name = "./linter_warnings.txt"
        hio.to_file(cfile_name, cfile)
        _LOG.info("Saved cfile in '%s'", cfile_name)
        print(cfile)
    else:
        _LOG.warning("Skipping lint parsing, as per user request")


@task
def lint_create_branch(ctx, dry_run=False):  # type: ignore
    """
    Create the branch for linting in the current dir.

    The dir needs to be specified to ensure the set-up is correct.
    """
    _report_task()
    #
    date = datetime.datetime.now().date()
    date_as_str = date.strftime("%Y%m%d")
    branch_name = f"AmpTask1955_Lint_{date_as_str}"
    # query_yes_no("Are you sure you want to create the branch '{branch_name}'")
    _LOG.info("Creating branch '%s'", branch_name)
    cmd = f"invoke git_create_branch -b '{branch_name}'"
    _run(ctx, cmd, dry_run=dry_run)


# #############################################################################
# GitHub CLI.
# #############################################################################


@task
def gh_login(  # type: ignore
    ctx,
    account="",
    print_status=False,
):
    _report_task()
    #
    if not account:
        # Retrieve the name of the repo, e.g., "alphamatic/amp".
        full_repo_name = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=False
        )
        _LOG.debug(hprint.to_str("full_repo_name"))
        account = full_repo_name.split("/")[0]
    _LOG.info(hprint.to_str("account"))
    #
    ssh_filename = os.path.expanduser(f"~/.ssh/id_rsa.{account}.github")
    _LOG.debug(hprint.to_str("ssh_filename"))
    if os.path.exists(ssh_filename):
        cmd = f"export GIT_SSH_COMMAND='ssh -i {ssh_filename}'"
        print(cmd)
    else:
        _LOG.warning("Can't find file '%s'", ssh_filename)
    #
    if print_status:
        cmd = "gh auth status"
        _run(ctx, cmd)
    #
    github_pat_filename = os.path.expanduser(f"~/.ssh/github_pat.{account}.txt")
    if os.path.exists(github_pat_filename):
        cmd = f"gh auth login --with-token <{github_pat_filename}"
        _run(ctx, cmd)
    else:
        _LOG.warning("Can't find file '%s'", github_pat_filename)
    #
    if print_status:
        cmd = "gh auth status"
        _run(ctx, cmd)


def _get_branch_name(branch_mode: str) -> Optional[str]:
    if branch_mode == "current_branch":
        branch_name: Optional[str] = hgit.get_branch_name()
    elif branch_mode == "master":
        branch_name = "master"
    elif branch_mode == "all":
        branch_name = None
    else:
        raise ValueError(f"Invalid branch='{branch_mode}'")
    return branch_name


def _get_workflow_table() -> htable.TableType:
    """
    Get a table with the status of the GH workflow for the current repo.
    """
    # Get the workflow status from GH.
    cmd = "export NO_COLOR=1; gh run list"
    _, txt = hsystem.system_to_string(cmd)
    _LOG.debug(hprint.to_str("txt"))
    # pylint: disable=line-too-long
    # > gh run list
    # STATUS  NAME                                                        WORKFLOW    BRANCH                                                EVENT              ID          ELAPSED  AGE
    # X       Amp task1786 integrate 2021118 (#1857)                    Fast tests  master                                                push               1477484584  5m40s    23m
    # X       Merge branch 'master' into AmpTask1786_Integrate_2021118  Fast tests  AmpTask1786_Integrate_2021118                         pull_request       1477445218  5m52s    34m
    # pylint: enable=line-too-long
    # The output is tab separated, so convert it into CSV.
    first_line = txt.split("\n")[0]
    _LOG.debug("first_line=%s", first_line.replace("\t", ","))
    num_cols = len(first_line.split("\t"))
    _LOG.debug(hprint.to_str("first_line num_cols"))
    cols = [
        "completed",
        "status",
        "name",
        "workflow",
        "branch",
        "event",
        "id",
        "elapsed",
        "age",
    ]
    hdbg.dassert_eq(num_cols, len(cols))
    # Build the table.
    table = htable.Table.from_text(cols, txt, delimiter="\t")
    _LOG.debug(hprint.to_str("table"))
    return table


@task
def gh_workflow_list(  # type: ignore
    ctx,
    filter_by_branch="current_branch",
    filter_by_status="all",
    report_only_status=True,
):
    """
    Report the status of the GH workflows.

    :param filter_by_branch: name of the branch to check
        - `current_branch` for the current Git branch
        - `master` for master branch
        - `all` for all branches
    :param filter_by_status: filter table by the status of the workflow
        - E.g., "failure", "success"
    """
    _report_task(txt=hprint.to_str("filter_by_branch filter_by_status"))
    # Login.
    gh_login(ctx)
    # Get the table.
    table = _get_workflow_table()
    # Filter table based on the branch.
    if filter_by_branch != "all":
        field = "branch"
        value = _get_branch_name(filter_by_branch)
        print(f"Filtering table by {field}={value}")
        table = table.filter_rows(field, value)
    # Filter table by the workflow status.
    if filter_by_status != "all":
        field = "status"
        value = filter_by_status
        print(f"Filtering table by {field}={value}")
        table = table.filter_rows(field, value)
    if (
        filter_by_branch not in ("current_branch", "master")
        or not report_only_status
    ):
        print(str(table))
        return
    # For each workflow find the last success.
    branch_name = hgit.get_branch_name()
    workflows = table.unique("workflow")
    print(f"workflows={workflows}")
    for workflow in workflows:
        print(hprint.frame(workflow))
        table_tmp = table.filter_rows("workflow", workflow)
        # Report the full status.
        print(table_tmp)
        # Find the first success.
        num_rows = table.size()[0]
        for i in range(num_rows):
            status_column = table_tmp.get_column("status")
            _LOG.debug("status_column=%s", str(status_column))
            hdbg.dassert_lt(i, len(status_column))
            status = status_column[i]
            if status == "success":
                print(f"Workflow '{workflow}' for '{branch_name}' is ok")
                break
            if status in ("failure", "startup_failure", "cancelled"):
                _LOG.error(
                    "Workflow '%s' for '%s' is broken", workflow, branch_name
                )
                # Get the output of the broken run.
                # > gh run view 1477484584 --log-failed
                workload_id = table_tmp.get_column("id")[i]
                log_file_name = f"tmp.failure.{workflow}.{branch_name}.txt"
                log_file_name = log_file_name.replace(" ", "_").lower()
                cmd = f"gh run view {workload_id} --log-failed >{log_file_name}"
                hsystem.system(cmd)
                print(f"# Log is in '{log_file_name}'")
                # Run_fast_tests  Run fast tests  2021-12-19T00:19:38.3394316Z FAILED data
                cmd = rf"grep 'Z FAILED ' {log_file_name}"
                hsystem.system(cmd, suppress_output=False, abort_on_error=False)
                break
            if status == "":
                # It's in progress.
                pass
            else:
                raise ValueError(f"Invalid status='{status}'")


@task
def gh_workflow_run(ctx, branch="current_branch", workflows="all"):  # type: ignore
    """
    Run GH workflows in a branch.
    """
    _report_task(txt=hprint.to_str("branch workflows"))
    # Login.
    gh_login(ctx)
    # Get the branch name.
    if branch == "current_branch":
        branch_name = hgit.get_branch_name()
    elif branch == "master":
        branch_name = "master"
    else:
        raise ValueError(f"Invalid branch='{branch}'")
    _LOG.debug(hprint.to_str("branch_name"))
    # Get the workflows.
    if workflows == "all":
        gh_tests = ["fast_tests", "slow_tests"]
    else:
        gh_tests = [workflows]
    _LOG.debug(hprint.to_str("workflows"))
    # Run.
    for gh_test in gh_tests:
        gh_test += ".yml"
        # gh workflow run fast_tests.yml --ref AmpTask1251_Update_GH_actions_for_amp
        cmd = f"gh workflow run {gh_test} --ref {branch_name}"
        _run(ctx, cmd)


def _get_repo_full_name_from_cmd(repo_short_name: str) -> Tuple[str, str]:
    """
    Convert the `repo_short_name` from command line (e.g., "current", "amp",
    "lm") to the repo_short_name full name without host name.
    """
    repo_full_name_with_host: str
    if repo_short_name == "current":
        # Get the repo name from the current repo.
        repo_full_name_with_host = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=True
        )
        # Compute the short repo name corresponding to "current".
        repo_full_name = hgit.get_repo_full_name_from_dirname(
            ".", include_host_name=False
        )
        ret_repo_short_name = hgit.get_repo_name(
            repo_full_name, in_mode="full_name", include_host_name=False
        )

    else:
        # Get the repo name using the short -> full name mapping.
        repo_full_name_with_host = hgit.get_repo_name(
            repo_short_name, in_mode="short_name", include_host_name=True
        )
        ret_repo_short_name = repo_short_name
    _LOG.debug(
        "repo_short_name=%s -> repo_full_name_with_host=%s ret_repo_short_name=%s",
        repo_short_name,
        repo_full_name_with_host,
        ret_repo_short_name,
    )
    return repo_full_name_with_host, ret_repo_short_name


# #############################################################################


def _get_gh_issue_title(issue_id: int, repo_short_name: str) -> Tuple[str, str]:
    """
    Get the title of a GitHub issue.

    :param repo_short_name: `current` refer to the repo_short_name where we are,
        otherwise a repo_short_name short name (e.g., "amp")
    """
    repo_full_name_with_host, repo_short_name = _get_repo_full_name_from_cmd(
        repo_short_name
    )
    # > (export NO_COLOR=1; gh issue view 1251 --json title)
    # {"title":"Update GH actions for amp"}
    hdbg.dassert_lte(1, issue_id)
    cmd = f"gh issue view {issue_id} --repo {repo_full_name_with_host} --json title,url"
    _, txt = hsystem.system_to_string(cmd)
    _LOG.debug("txt=\n%s", txt)
    # Parse json.
    dict_ = json.loads(txt)
    _LOG.debug("dict_=\n%s", dict_)
    title = dict_["title"]
    _LOG.debug("title=%s", title)
    url = dict_["url"]
    _LOG.debug("url=%s", url)
    # Remove some annoying chars.
    for char in ": + ( ) / ` *".split():
        title = title.replace(char, "")
    # Replace multiple spaces with one.
    title = re.sub(r"\s+", " ", title)
    #
    title = title.replace(" ", "_")
    title = title.replace("-", "_")
    title = title.replace("'", "_")
    title = title.replace("`", "_")
    title = title.replace('"', "_")
    # Add the prefix `AmpTaskXYZ_...`
    task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)
    _LOG.debug("task_prefix=%s", task_prefix)
    title = f"{task_prefix}{issue_id}_{title}"
    return title, url


@task
def gh_issue_title(ctx, issue_id, repo_short_name="current", pbcopy=True):  # type: ignore
    """
    Print the title that corresponds to the given issue and repo_short_name.
    E.g., AmpTask1251_Update_GH_actions_for_amp.

    :param pbcopy: save the result into the system clipboard (only on macOS)
    """
    _report_task(txt=hprint.to_str("issue_id repo_short_name"))
    # Login.
    gh_login(ctx)
    #
    issue_id = int(issue_id)
    hdbg.dassert_lte(1, issue_id)
    title, url = _get_gh_issue_title(issue_id, repo_short_name)
    # Print or copy to clipboard.
    msg = f"{title}: {url}"
    _to_pbcopy(msg, pbcopy)


def _check_if_pr_exists(title: str) -> bool:
    """
    Return whether a PR exists or not.
    """
    # > gh pr diff AmpTask1955_Lint_20211219
    # no pull requests found for branch "AmpTask1955_Lint_20211219"
    cmd = f"gh pr diff {title}"
    rc = hsystem.system(cmd, abort_on_error=False)
    pr_exists: bool = rc == 0
    return pr_exists


@task
def gh_create_pr(  # type: ignore
    ctx,
    body="",
    draft=True,
    auto_merge=False,
    repo_short_name="current",
    title="",
):
    """
    Create a draft PR for the current branch in the corresponding
    repo_short_name.

    ```
    # To open a PR in the web browser
    > gh pr view --web

    # To see the status of the checks
    > gh pr checks
    ```

    :param body: the body of the PR
    :param draft: draft or ready-to-review PR
    :param auto_merge: enable auto merging PR
    :param title: title of the PR or the branch name, if title is empty
    """
    _report_task()
    # Login.
    gh_login(ctx)
    #
    branch_name = hgit.get_branch_name()
    if not title:
        # Use the branch name as title.
        title = branch_name
    repo_full_name_with_host, repo_short_name = _get_repo_full_name_from_cmd(
        repo_short_name
    )
    _LOG.info(
        "Creating PR with title '%s' for '%s' in %s",
        title,
        branch_name,
        repo_full_name_with_host,
    )
    if auto_merge:
        hdbg.dassert(
            not draft, "The PR can't be a draft in order to auto merge it"
        )
    pr_exists = _check_if_pr_exists(title)
    _LOG.debug(hprint.to_str("pr_exists"))
    if pr_exists:
        _LOG.warning("PR '%s' already exists: skipping creation", title)
    else:
        cmd = (
            "gh pr create"
            + f" --repo {repo_full_name_with_host}"
            + (" --draft" if draft else "")
            + f' --title "{title}"'
            + f' --body "{body}"'
        )
        # TODO(gp): Use _to_single_line_cmd
        _run(ctx, cmd)
    if auto_merge:
        cmd = f"gh pr ready {title}"
        _run(ctx, cmd)
        cmd = f"gh pr merge {title} --auto --delete-branch --squash"
        _run(ctx, cmd)


# #############################################################################
# Fix permission
# #############################################################################


# The desired invariants are that all files
# 1) are owned by our user or by Docker user
# 2) have the shared group as group
# 3) have the same user and group permissions

# E.g.,
# -rw-rw-r-- 1 spm-sasm spm-sasm-fileshare 21877 Nov  3 18:11 pytest_logger.log

# The possible problems are:
# -r--r--r-- 1 spm-sasm spm-sasm-fileshare ./.git/objects/02/4df16f66c87bdfb
# -rw-r--r-- 1 265533 spm-sasm-fileshare  ./core_lime/dataflow/nodes/test/te
# -rw-rw-r-- 1 265533 spm-sasm-fileshare  ./research/real_time/notebooks/Lim

# drwxr-sr-x 2 gsaggese spm-sasm-fileshare    35 Oct 12 21:51 test
# chmod g=u amp/dev_scripts/git/git_hooks/test


def _save_dir_status(dir_name: str, filename: str) -> None:
    cmd = f'find {dir_name} -name "*" | sort | xargs ls -ld >{filename}'
    hsystem.system(cmd)
    _LOG.info("Saved dir status in %s", filename)


# From https://stackoverflow.com/questions/1830618
def _get_user_group(filename: str) -> Tuple[str, str]:
    """
    Return the symbolic name of user and group of a file.
    """
    uid = os.stat(filename).st_uid
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError as e:
        # _LOG.warning("Error: ", str(e))
        _ = e
        user = str(uid)
    #
    gid = os.stat(filename).st_gid
    try:
        group = grp.getgrgid(gid).gr_name
    except KeyError as e:
        _ = e
        group = str(gid)
    return user, group


def _find_files_for_user(dir_name: str, user: str, is_equal: bool) -> List[str]:
    """
    Find all the files under `abs_dir` that are owned or not by `user`.
    """
    _LOG.debug("")
    mode = "\\!" if not is_equal else ""
    cmd = f'find {dir_name} -name "*" {mode} -user "{user}"'
    _, txt = hsystem.system_to_string(cmd)
    files: List[str] = txt.split("\n")
    return files


def _find_files_for_group(dir_name: str, group: str, is_equal: bool) -> List[str]:
    """
    Find all the files under `abs_dir` that are owned by a group `group`.
    """
    _LOG.debug("")
    mode = "\\!" if not is_equal else ""
    cmd = f'find {dir_name} -name "*" {mode} -group "{group}"'
    _, txt = hsystem.system_to_string(cmd)
    files: List[str] = txt.split("\n")
    return files


def _compute_stats_by_user_and_group(dir_name: str) -> Tuple[Dict, Dict, Dict]:
    """
    Scan all the files reporting statistics in terms of users and groups.

    It also compute a mapping from file to user and group.
    """
    _LOG.debug("")
    # Find all files.
    cmd = f'find {dir_name} -name "*"'
    _, txt = hsystem.system_to_string(cmd)
    files = txt.split("\n")
    # Get the user of each file.
    user_to_files: Dict[str, List[str]] = {}
    group_to_files: Dict[str, List[str]] = {}
    file_to_user_group: Dict[str, Tuple[str, str]] = {}
    for file in files:
        user, group = _get_user_group(file)
        # Update mapping from user to files.
        if user not in user_to_files:
            user_to_files[user] = []
        user_to_files[user].append(file)
        # Update mapping from group to files.
        if group not in group_to_files:
            group_to_files[group] = []
        group_to_files[group].append(file)
        # Update the mapping from file to (user, group).
        hdbg.dassert_not_in(file, file_to_user_group)
        file_to_user_group[file] = (user, group)
    # Print stats.
    txt1 = ""
    for user, files in user_to_files.items():
        txt1 += f"{user}({len(files)}), "
    _LOG.info("user=%s", txt1)
    #
    txt2 = ""
    for group, files in group_to_files.items():
        txt2 += f"{group}({len(files)}), "
    _LOG.info("group=%s", txt2)
    return user_to_files, group_to_files, file_to_user_group


def _ls_l(files: List[str], size: int = 100) -> str:
    """
    Run `ls -l` on the files using chunks of size `size`.
    """
    txt = []
    for pos in range(0, len(files), size):
        files_tmp = files[pos : pos + size]
        files_tmp = [f"'{f}'" for f in files_tmp]
        cmd = f"ls -ld {' '.join(files_tmp)}"
        _, txt_tmp = hsystem.system_to_string(cmd)
        txt.append(txt_tmp)
    return "\n".join(txt)


def _exec_cmd_by_chunks(
    cmd: str, files: List[str], abort_on_error: bool, size: int = 100
) -> None:
    """
    Execute `cmd` on files using chunks of size `size`.
    """
    for pos in range(0, len(files), size):
        files_tmp = files[pos : pos + size]
        files_tmp = [f"'{f}'" for f in files_tmp]
        cmd = f"{cmd} {' '.join(files_tmp)}"
        hsystem.system(cmd, abort_on_error=abort_on_error)


def _print_problems(dir_name: str = ".") -> None:
    """
    Do `ls -l` on files that are not owned by the current user and its group.

    This function is used for debugging.
    """
    _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)
    user = hsystem.get_user_name()
    docker_user = hgit.execute_repo_config_code("get_docker_user()")
    # user_group = f"{user}_g"
    # shared_group = hgit.execute_repo_config_code("get_docker_shared_group()")
    files_with_problems = []
    for file, (curr_user, curr_group) in file_to_user_group.items():
        _ = curr_user, curr_group
        # Files owned by our user and
        # if curr_user == user and curr_group == user_group:
        #    continue
        if curr_user in (user, docker_user):
            continue
        # if curr_group == shared_group:
        #    continue
        files_with_problems.append(file)
    #
    txt = _ls_l(files_with_problems)
    print(txt)


def _change_file_ownership(file: str, abort_on_error: bool) -> None:
    """
    Change ownership of files with an invalid user (e.g., 265533) by copying
    and deleting.
    """
    # pylint: disable=line-too-long
    # > ls -l ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py
    # -rw-r--r-- 1 265533 spm-sasm-fileshare 14327 Nov  3 14:01 ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py
    #
    # > mv ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py{,.OLD}
    #
    # > cp ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py{.OLD,}
    #
    # > ls -l ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py
    # -rw-r--r-- 1 gsaggese spm-sasm-fileshare 14327 Nov  5 17:58 ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py
    #
    # > rm -rf ./core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py.OLD
    # pylint: enable=line-too-long
    hdbg.dassert_file_exists(file)
    tmp_file = file + ".OLD"
    #
    cmd = f"mv {file} {tmp_file}"
    hsystem.system(cmd, abort_on_error=abort_on_error)
    #
    cmd = f"cp {tmp_file} {file}"
    hsystem.system(cmd, abort_on_error=abort_on_error)
    #
    cmd = f"rm -rf {tmp_file}"
    hsystem.system(cmd, abort_on_error=abort_on_error)


def _fix_invalid_owner(dir_name: str, fix: bool, abort_on_error: bool) -> None:
    """
    Fix files that are owned by a user that is not the current user or the
    Docker one.
    """
    _LOG.info("\n%s", hprint.frame(hintros.get_function_name()))
    #
    _LOG.info("Before fix")
    _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)
    #
    user = hsystem.get_user_name()
    docker_user = hgit.execute_repo_config_code("get_docker_user()")
    for file, (curr_user, _) in tqdm.tqdm(file_to_user_group.items()):
        if curr_user not in (user, docker_user):
            _LOG.info("Fixing file '%s'", file)
            hdbg.dassert_file_exists(file)
            cmd = f"ls -l {file}"
            hsystem.system(
                cmd, abort_on_error=abort_on_error, suppress_output=False
            )
            if fix:
                _change_file_ownership(file, abort_on_error)
    #
    _LOG.info("After fix")
    _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)


def _fix_group(dir_name: str, fix: bool, abort_on_error: bool) -> None:
    """
    Ensure that all files are owned by the shared group.
    """
    _LOG.info("\n%s", hprint.frame(hintros.get_function_name()))
    _LOG.info("Before fix")
    _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)
    if fix:
        # Get the user and the group.
        user = hsystem.get_user_name()
        user_group = f"{user}_g"
        shared_group = hgit.execute_repo_config_code("get_docker_shared_group()")
        #
        for file, (curr_user, curr_group) in file_to_user_group.items():
            # If the group is the shared group there is nothing to do.
            if curr_group == shared_group:
                continue
            cmd = f"chgrp {shared_group} {file}"
            if curr_user == user:
                # This is a paranoia check.
                hdbg.dassert_eq(curr_group, user_group)
            else:
                # For files not owned by the current user, we need to `sudo`.
                cmd = f"sudo -u {curr_user} {cmd}"
            hsystem.system(cmd, abort_on_error=abort_on_error)
        _LOG.info("After fix")
        _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)
    else:
        _LOG.warning("Skipping fix")


def _fix_group_permissions(dir_name: str, abort_on_error: bool) -> None:
    """
    Ensure that all files are owned by the shared group.
    """
    _LOG.info("\n%s", hprint.frame(hintros.get_function_name()))
    _, _, file_to_user_group = _compute_stats_by_user_and_group(dir_name)
    user = hsystem.get_user_name()
    # docker_user = get_default_param("DOCKER_USER")
    for file, (curr_user, curr_group) in tqdm.tqdm(file_to_user_group.items()):
        _ = curr_group
        st_mode = os.stat(file).st_mode
        perms = oct(st_mode & 0o777)
        # perms=0o775
        if perms[2] != perms[3]:
            _LOG.debug("%s -> %s, %s", file, oct(st_mode), perms)
            cmd = f"chmod g=u {file}"
            if curr_user != user:
                # For files not owned by the current user, we need to `sudo`.
                cmd = f"sudo -u {curr_user} {cmd}"
            hsystem.system(cmd, abort_on_error=abort_on_error)
        is_dir = os.path.isdir(file)
        if is_dir:
            # pylint: disable=line-too-long
            # From https://www.gnu.org/software/coreutils/manual/html_node/Directory-Setuid-and-Setgid.html
            # If a directory
            # inherit the same group as the directory,
            # pylint: enable=line-too-long
            has_set_group_id = st_mode & stat.S_ISGID
            if not has_set_group_id:
                cmd = f"chmod g+s {file}"
                if curr_user != user:
                    # For files not owned by the current user, we need to `sudo`.
                    cmd = f"sudo -u {curr_user} {cmd}"
                hsystem.system(cmd, abort_on_error=abort_on_error)


@task
def fix_perms(  # type: ignore
    ctx, dir_name=".", action="all", fix=True, abort_on_error=True
):
    """
    :param action:
        - `all`: run all the fixes
        - `print_stats`: print stats about file users and groups
        - `print_problems`:
        - `fix_invalid_owner`: fix the files with an invalid owner (e.g., mysterious
            265533)
        - `fix_group`: ensure that shared group owns all the files
        - `fix_group_permissions`: ensure that the group permissions are the same
            as the owner ones
    """
    _ = ctx
    _report_task()
    #
    if hgit.execute_repo_config_code("is_dev4()"):
        if action == "all":
            action = ["fix_invalid_owner", "fix_group", "fix_group_permissions"]
        else:
            action = [action]
        #
        file_name1 = "./tmp.fix_perms.before.txt"
        _save_dir_status(dir_name, file_name1)
        #
        if "print_stats" in action:
            _compute_stats_by_user_and_group(dir_name)
        if "print_problems" in action:
            _print_problems(dir_name)
        if "fix_invalid_owner" in action:
            _fix_invalid_owner(dir_name, fix, abort_on_error)
        if "fix_group" in action:
            _fix_group(dir_name, fix, abort_on_error)
        if "fix_group_permissions" in action:
            _fix_group_permissions(dir_name, abort_on_error)
        #
        file_name2 = "./tmp.fix_perms.after.txt"
        _save_dir_status(dir_name, file_name2)
        #
        cmd = f"To compare run:\n> vimdiff {file_name1} {file_name2}"
        print(cmd)
    elif hgit.execute_repo_config_code("is_dev_ck()"):
        user = hsystem.get_user_name()
        group = user
        cmd = f"sudo chown -R {user}:{group} *"
        hsystem.system(cmd)
        cmd = f"sudo chown -R {user}:{group} .pytest_cache"
        hsystem.system(cmd, abort_on_error=False)
    else:
        raise ValueError(f"Invalid machine {os.uname()[1]}")


# TODO(gp): Add gh_open_pr to jump to the PR from this branch.

# TODO(gp): Add ./dev_scripts/testing/pytest_count_files.sh

# pylint: disable=line-too-long
# From https://stackoverflow.com/questions/34878808/finding-docker-container-processes-from-host-point-of-view
# Convert Docker container to processes id
# for i in $(docker container ls --format "{{.ID}}"); do docker inspect -f '{{.State.Pid}} {{.Name}}' $i; done
# 7444 /compose_app_run_d386dc360071
# 8857 /compose_jupyter_server_run_7575f1652032
# 1767 /compose_app_run_6782c2bd6999
# 25163 /compose_app_run_ab27e17f2c47
# 18721 /compose_app_run_de23819a6bc2
# pylint: enable=line-too-long
