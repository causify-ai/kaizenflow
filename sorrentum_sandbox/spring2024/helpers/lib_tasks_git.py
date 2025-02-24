"""
Import as:

import helpers.lib_tasks_git as hlitagit
"""

import logging
import os
import re
from typing import Any

from invoke import task

# We want to minimize the dependencies from non-standard Python packages since
# this code needs to run with minimal dependencies and without Docker.
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.lib_tasks_gh as hlitagh
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


def run_git_recursively(ctx: Any, cmd_: str) -> None:
    cmd = cmd_
    hlitauti.run(ctx, cmd)
    #
    cmd = f"git submodule foreach '{cmd_}'"
    hlitauti.run(ctx, cmd)


@task
def git_pull(ctx):  # type: ignore
    """
    Pull all the repos.
    """
    hlitauti.report_task()
    #
    cmd = "git pull --autostash"
    run_git_recursively(ctx, cmd)


@task
def git_fetch_master(ctx):  # type: ignore
    """
    Pull master without changing branch.
    """
    hlitauti.report_task()
    #
    cmd = "git fetch origin master:master"
    run_git_recursively(ctx, cmd)


@task
def git_merge_master(ctx, ff_only=False, abort_if_not_clean=True):  # type: ignore
    """
    Merge `origin/master` into the current branch.

    :param ff_only: abort if fast-forward is not possible
    """
    hlitauti.report_task()
    # Check that the Git client is clean.
    hgit.is_client_clean(dir_name=".", abort_if_not_clean=abort_if_not_clean)
    # Pull master.
    git_fetch_master(ctx)
    # Merge master.
    cmd = "git merge master"
    if ff_only:
        cmd += " --ff-only"
    hlitauti.run(ctx, cmd)


@task
def git_clean(ctx, fix_perms_=False, dry_run=False):  # type: ignore
    """
    Clean the repo_short_name and its submodules from artifacts.

    Run `git status --ignored` to see what it's skipped.
    """
    hlitauti.report_task(txt=hprint.to_str("dry_run"))

    def _run_all_repos(cmd: str) -> None:
        # Use `run(ctx, cmd)` instead of `hsystem.system()` so that it is possible
        # to easily use a mock context while unit testing.
        hlitauti.run(ctx, cmd)
        # Clean submodules.
        cmd = f"git submodule foreach '{cmd}'"
        hlitauti.run(ctx, cmd)

    # Clean recursively.
    git_clean_cmd = "git clean -fd"
    if dry_run:
        git_clean_cmd += " --dry-run"
    # This cmd is supposed to give errors so we mute them.
    git_clean_cmd += " >/dev/null 2>&1"
    _run_all_repos(git_clean_cmd)
    # TODO(*): Add "are you sure?" or a `--force switch` to avoid to cancel by
    #  mistake.
    # Fix permissions, if needed.
    if fix_perms_:
        cmd = "invoke fix_perms"
        hlitauti.run(ctx, cmd)
        # Clean temporary files created by permission fix.
        _run_all_repos(git_clean_cmd)
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
    hlitauti.run(ctx, cmd)


@task
def git_add_all_untracked(ctx):  # type: ignore
    """
    Add all untracked files to Git.
    """
    hlitauti.report_task()
    cmd = "git add $(git ls-files -o --exclude-standard)"
    hlitauti.run(ctx, cmd)


@task
def git_patch_create(  # type: ignore
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
    hlitauti.report_task(
        txt=hprint.to_str("mode modified branch last_commit files")
    )
    _ = ctx
    # TODO(gp): Check that the current branch is up to date with master to avoid
    #  failures when we try to merge the patch.
    hdbg.dassert_in(mode, ("tar", "diff"))
    # For now we just create a patch for the current submodule.
    # TODO(gp): Extend this to handle also nested repos.
    super_module = False
    git_client_root = hgit.get_client_root(super_module)
    hash_ = hgit.get_head_hash(git_client_root, short_hash=True)

    timestamp = hlitauti.get_ET_timestamp()
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
    files_as_list = hlitauti._get_files_to_process(
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
    hlitauti.report_task()
    _ = ctx
    all_ = False
    files = ""
    mutually_exclusive = True
    # pre-commit doesn't handle directories, but only files.
    remove_dirs = True
    files_as_list = hlitauti._get_files_to_process(
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
        hlitauti._to_pbcopy(res, pbcopy)


@task
def git_last_commit_files(ctx, pbcopy=True):  # type: ignore
    """
    Print the status of the files in the previous commit.

    :param pbcopy: save the result into the system clipboard (only on
        macOS)
    """
    cmd = 'git log -1 --name-status --pretty=""'
    hlitauti.run(ctx, cmd)
    # Get the list of existing files.
    files = hgit.get_previous_committed_files(".")
    txt = "\n".join(files)
    print(f"\n# The files modified are:\n{txt}")
    # Save to clipboard.
    res = " ".join(files)
    hlitauti._to_pbcopy(res, pbcopy)


@task
def git_roll_amp_forward(ctx):  # type: ignore
    """
    Roll amp forward.
    """
    hlitauti.report_task()
    AMP_DIR = "amp"
    if os.path.exists(AMP_DIR):
        cmds = [
            f"cd {AMP_DIR} && git checkout master",
            f"cd {AMP_DIR} && git pull",
            f"git add {AMP_DIR}",
            f"git commit -m 'Roll {AMP_DIR} pointer forward'",
            "git push",
        ]
        for cmd in cmds:
            hlitauti.run(ctx, cmd)
    else:
        _LOG.warning("%s does not exist, aborting", AMP_DIR)


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
    hlitauti.report_task()
    _ = ctx
    print(
        "Difference between HEAD and master:\n"
        + hgit.get_summary_files_in_branch("master", dir_name=".")
    )


@task
def git_branch_create(  # type: ignore
    ctx,
    branch_name="",
    issue_id=0,
    repo_short_name="current",
    suffix="",
    only_branch_from_master=True,
    check_branch_name=True,
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
    :param check_branch_name: make sure the name of the branch is valid like
        `{Amp,...}TaskXYZ_...`
    """
    hlitauti.report_task()
    if issue_id > 0:
        # User specified an issue id on GitHub.
        hdbg.dassert_eq(
            branch_name, "", "You can't specify both --issue and --branch_name"
        )
        title, _ = hlitagh._get_gh_issue_title(issue_id, repo_short_name)
        branch_name = title
        _LOG.info(
            "Issue %d in %s repo_short_name corresponds to '%s'",
            issue_id,
            repo_short_name,
            branch_name,
        )
        if suffix != "":
            # Add the suffix.
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
    if check_branch_name:
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
    cmd = "git pull --autostash --rebase"
    hlitauti.run(ctx, cmd)
    # git checkout -b LmTask169_Get_GH_actions_working_on_lm
    cmd = f"git checkout -b {branch_name}"
    hlitauti.run(ctx, cmd)
    cmd = f"git push --set-upstream origin {branch_name}"
    hlitauti.run(ctx, cmd)


# TODO(gp): @all Move to hgit.
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
        hlitauti.run(ctx, cmd_tmp)


@task
def git_branch_delete_merged(ctx, confirm_delete=True):  # type: ignore
    """
    Remove (both local and remote) branches that have been merged into master.
    """
    hlitauti.report_task()
    hdbg.dassert(
        hgit.get_branch_name(),
        "master",
        "You need to be on master to delete dead branches",
    )
    #
    cmd = "git fetch --all --prune"
    hlitauti.run(ctx, cmd)
    # Delete local and remote branches that are already merged into master.
    _delete_branches(ctx, "local", confirm_delete)
    _delete_branches(ctx, "remote", confirm_delete)
    #
    cmd = "git fetch --all --prune"
    hlitauti.run(ctx, cmd)


@task
def git_branch_rename(ctx, new_branch_name):  # type: ignore
    """
    Rename current branch both locally and remotely.
    """
    hlitauti.report_task()
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
    hlitauti.run(ctx, cmd)
    # Delete the old branch on remote.
    # > git push <remote> --delete <old_name>
    cmd = f"git push origin --delete {old_branch_name}"
    hlitauti.run(ctx, cmd)
    # Prevent Git from using the old name when pushing in the next step.
    # Otherwise, Git will use the old upstream name instead of <new_name>.
    # > git branch --unset-upstream <new_name>
    cmd = f"git branch --unset-upstream {new_branch_name}"
    hlitauti.run(ctx, cmd)
    # Push the new branch to remote.
    # > git push <remote> <new_name>
    cmd = f"git push origin {new_branch_name}"
    hlitauti.run(ctx, cmd)
    # Reset the upstream branch for the new_name local branch.
    # > git push <remote> -u <new_name>
    cmd = f"git push origin u {new_branch_name}"
    hlitauti.run(ctx, cmd)
    print("Done")


@task
def git_branch_next_name(ctx, branch_name=None):  # type: ignore
    """
    Return a name derived from the current branch so that the branch doesn't
    exist.

    :param branch_name: if `None` use the current branch name, otherwise specify it

    E.g., `AmpTask1903_Implemented_system_Portfolio` ->
        `AmpTask1903_Implemented_system_Portfolio_3`
    """
    hlitauti.report_task()
    _ = ctx
    branch_next_name = hgit.get_branch_next_name(
        curr_branch_name=branch_name, log_verb=logging.INFO
    )
    print(f"branch_next_name='{branch_next_name}'")


# TODO(gp): @all Improve docstring
@task
def git_branch_copy(  # type: ignore
    ctx,
    new_branch_name="",
    skip_git_merge_master=False,
    use_patch=False,
    check_branch_name=True,
):
    """
    Create a new branch with the same content of the current branch.

    :param skip_git_merge_master
    :param check_branch_name: make sure the name of the branch is valid like
        `{Amp,...}TaskXYZ_...`
    """
    hdbg.dassert(not use_patch, "Patch flow not implemented yet")
    #
    cmd = "git clean -fd"
    hlitauti.run(ctx, cmd)
    #
    curr_branch_name = hgit.get_branch_name()
    hdbg.dassert_ne(curr_branch_name, "master")
    if not skip_git_merge_master:
        # Make sure `old_branch_name` doesn't need to have `master` merged.
        cmd = "invoke git_merge_master --ff-only"
        hlitauti.run(ctx, cmd)
    else:
        _LOG.warning("Skipping git_merge_master as requested")
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
        cmd = f"git checkout master && invoke git_branch_create -b '{new_branch_name}'"
        if not check_branch_name:
            cmd += " --no-check-branch-name"
    hlitauti.run(ctx, cmd)
    if use_patch:
        # TODO(gp): Apply the patch.
        pass
    #
    cmd = f"git merge --squash --ff {curr_branch_name} && git reset HEAD"
    hlitauti.run(ctx, cmd)


# ///////////////////////////////////////////////////////////////////////////////


def _git_diff_with_branch(
    ctx: Any,
    hash_: str,
    tag: str,
    #
    dir_name: str,
    subdir: str,
    #
    diff_type: str,
    keep_extensions: str,
    skip_extensions: str,
    file_name: str,
    #
    only_print_files: bool,
    dry_run: bool,
) -> None:
    """
    Diff files from this client against files in a branch using vimdiff.

    Same parameters as `git_branch_diff_with`.
    """
    _LOG.debug(
        hprint.to_str(
            "hash_ tag dir_name diff_type subdir keep_extensions skip_extensions"
            " file_name only_print_files dry_run"
        )
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
    _LOG.debug("%s", "\n".join(files))
    # Filter by `file_name`, if needed.
    if file_name:
        _LOG.debug("Filter by file_name")
        _LOG.info("Before filtering files=%s", len(files))
        files_tmp = []
        for f in files:
            if f == file_name:
                files_tmp.append(f)
        hdbg.dassert_eq(
            1,
            len(files_tmp),
            "Can't find file_name='%s' in\n%s",
            file_name,
            "\n".join(files),
        )
        files = files_tmp
        _LOG.info("After filtering by file_name: files=%s", len(files))
        _LOG.debug("%s", "\n".join(files))
    # Filter by keep_extension.
    if keep_extensions:
        _LOG.debug("# Filter by keep_extensions")
        _LOG.debug("Before filtering files=%s", len(files))
        extensions_lst = keep_extensions.split(",")
        _LOG.warning(
            "Keeping files with %d extensions: %s",
            len(extensions_lst),
            extensions_lst,
        )
        files_tmp = []
        for f in files:
            if any(f.endswith(ext) for ext in extensions_lst):
                files_tmp.append(f)
        files = files_tmp
        _LOG.info("After filtering by keep_extensions: files=%s", len(files))
        _LOG.debug("%s", "\n".join(files))
    # Filter by skip_extension.
    if skip_extensions:
        _LOG.debug("# Filter by skip_extensions")
        _LOG.debug("Before filtering files=%s", len(files))
        extensions_lst = skip_extensions.split(",")
        _LOG.warning(
            "Skipping files with %d extensions: %s",
            len(extensions_lst),
            extensions_lst,
        )
        files_tmp = []
        for f in files:
            if not any(f.endswith(ext) for ext in extensions_lst):
                files_tmp.append(f)
        files = files_tmp
        _LOG.info("After filtering by skip_extensions: files=%s", len(files))
        _LOG.debug("%s", "\n".join(files))
    # Filter by subdir.
    if subdir != "":
        _LOG.debug("# Filter by subdir")
        _LOG.debug("Before filtering files=%s", len(files))
        files_tmp = []
        for f in files:
            if f.startswith(subdir):
                files_tmp.append(f)
        files = files_tmp
        _LOG.info("After filtering by subdir: files=%s", len(files))
        _LOG.debug("%s", "\n".join(files))
    # Done filtering.
    _LOG.info("\n" + hprint.frame("# files=%s" % len(files)))
    _LOG.info("\n" + "\n".join(files))
    if len(files) == 0:
        _LOG.warning("Nothing to diff: exiting")
        return
    if only_print_files:
        _LOG.warning("Exiting as per user request with --only-print-files")
        return
    # Create the dir storing all the files to compare.
    root_dir = hgit.get_repo_full_name_from_client(super_module=True)
    # TODO(gp): We should get a temp dir.
    dst_dir = f"/tmp/{root_dir}/tmp.{tag}"
    hio.create_dir(dst_dir, incremental=False)
    # Retrieve the original file and create the diff command.
    script_txt = []
    for branch_file in files:
        _LOG.debug("\n%s", hprint.frame(f"branch_file={branch_file}"))
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
    _LOG.info("\n" + hprint.frame("Diffing script"))
    _LOG.info(script_txt)
    # Save the script to compare.
    script_file_name = f"./tmp.vimdiff_branch_with_{tag}.sh"
    msg = f"To diff against {tag} run"
    hio.create_executable_script(script_file_name, script_txt, msg=msg)
    hlitauti.run(ctx, script_file_name, dry_run=dry_run, pty=True)
    # Clean up file.
    cmd = f"rm -rf {dst_dir}"
    hlitauti.run(ctx, cmd, dry_run=dry_run)


def _git_diff_with_branch_wrapper(
    ctx: Any,
    hash_: str,
    tag: str,
    #
    dir_name: str,
    subdir: str,
    include_submodules: bool,
    #
    diff_type: str,
    keep_extensions: str,
    skip_extensions: str,
    python: bool,
    file_name: str,
    #
    only_print_files: bool,
    dry_run: bool,
) -> None:
    hdbg.dassert_eq(dir_name, ".")
    if python:
        hdbg.dassert_eq(diff_type, "")
        hdbg.dassert_eq(keep_extensions, "")
        hdbg.dassert_eq(skip_extensions, "")
        hdbg.dassert_eq(file_name, "")
        keep_extensions = "py"
    # Run for current dir.
    _git_diff_with_branch(
        ctx,
        hash_,
        tag,
        dir_name,
        diff_type,
        subdir,
        keep_extensions,
        skip_extensions,
        file_name,
        only_print_files,
        dry_run,
    )
    # Run for `amp` dir, if needed.
    if include_submodules:
        if hgit.is_amp_present():
            with hsystem.cd("amp"):
                _git_diff_with_branch(
                    ctx,
                    hash_,
                    tag,
                    dir_name,
                    diff_type,
                    subdir,
                    keep_extensions,
                    skip_extensions,
                    file_name,
                    only_print_files,
                    dry_run,
                )


@task
def git_branch_diff_with(  # type: ignore
    ctx,
    target="base",
    hash_value="",
    # Where to diff.
    subdir="",
    include_submodules=False,
    # What files to diff.
    diff_type="",
    keep_extensions="",
    skip_extensions="",
    python=False,
    file_name="",
    # What actions.
    only_print_files=False,
    dry_run=False,
):
    """
    Diff files of the current branch with master at the branching point.

    :param subdir: subdir to consider for diffing, instead of `.`
    :param target:
        - `base`: diff with respect to the branching point
        - `master`: diff with respect to `origin/master`
        - `head`: diff modified files
        - `hash`: diff with respect to hash specified in `hash`
    :param hash_value: the hash to use with target="hash"
    :param include_submodules: run recursively on all submodules
    :param diff_type: files to diff using git `--diff-filter` options
    :param keep_extensions: a comma-separated list of extensions to check, e.g.,
        'csv,py'. An empty string means keep all the extensions
    :param skip_extensions: a comma-separated list of extensions to skip, e.g.,
        'txt'. An empty string means do not skip any extension
    :param only_print_files: print files to diff and exit
    :param dry_run: execute diffing script or not
    """
    # Get the branching point.
    dir_name = "."
    hdbg.dassert_in(target, ("base", "master", "head", "hash"))
    if target == "base":
        hdbg.dassert_eq(hash_value, "")
        hash_value = hgit.get_branch_hash(dir_name=dir_name)
        tag = "base"
    elif target == "master":
        hdbg.dassert_eq(hash_value, "")
        hash_value = "origin/master"
        tag = "origin_master"
    elif target == "head":
        hdbg.dassert_eq(hash_value, "")
        # This will execute `git diff --name-only HEAD` to find the files, which
        # corresponds to finding all the files modified in the client.
        hash_value = ""
        tag = "head"
    elif target == "hash":
        hdbg.dassert_ne(hash_value, "")
        tag = f"hash@{hash_value}"
    else:
        raise ValueError(f"Invalid target='{target}")
    _git_diff_with_branch_wrapper(
        ctx,
        hash_value,
        tag,
        #
        dir_name,
        subdir,
        include_submodules,
        #
        diff_type,
        keep_extensions,
        skip_extensions,
        python,
        file_name,
        #
        only_print_files,
        dry_run,
    )


# pylint: disable=line-too-long

# TODO(gp): Add the following scripts:
# dev_scripts/git/git_backup.sh
# dev_scripts/git/gcl
# dev_scripts/git/git_branch.sh
# dev_scripts/git/git_branch_point.sh
# dev_scripts/create_class_diagram.sh

# How to find out if the current branch was merged
# ```
# > git branch --merged master | grep "$(git rev-parse --abbrev-ref HEAD)"
# ```
# If the output is empty it was merged, otherwise it was not merged.
