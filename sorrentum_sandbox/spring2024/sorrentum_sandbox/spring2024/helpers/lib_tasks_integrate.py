"""
Import as:

import helpers.lib_tasks_integrate as hlitaint
"""

import datetime
import logging
import os
from typing import List, Optional, Set, Tuple

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


DEFAULT_SRC_DIR_BASENAME = "cmamp1"
DEFAULT_DST_DIR_BASENAME = "kaizenflow1"

# DEFAULT_SRC_DIR_BASENAME="amp1"
# DEFAULT_DST_DIR_BASENAME="cmamp1"


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
    hlitauti.report_task()
    # Check that the current dir has the name `dir_basename`.
    _dassert_current_dir_matches(dir_basename)
    # Login in GitHub.
    hlitagh.gh_login(ctx)
    # Create the integration branch with the current date, e.g.,
    # `AmpTask1786_Integrate_20211231`.
    date = datetime.datetime.now().date()
    date_as_str = date.strftime("%Y%m%d")
    branch_name = f"AmpTask1786_Integrate_{date_as_str}"
    # query_yes_no("Are you sure you want to create the branch ")
    _LOG.info("Creating branch '%s'", branch_name)
    cmd = f"invoke git_branch_create -b '{branch_name}'"
    hlitauti.run(ctx, cmd, dry_run=dry_run)


# #############################################################################


def _resolve_src_dst_names(
    src_dir_basename: str,
    dst_dir_basename: str,
    subdir: str,
    *,
    check_exists: bool = True,
) -> Tuple[str, str]:
    """
    Return the full path of `src_dir_basename` and `dst_dir_basename`.

    :param src_dir_basename: the current dir (e.g., `amp1`)
    :param dst_dir_basename: a dir parallel to the current one (`cmamp1`)
    :param check_exists: check that the dst dir exists

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
    if check_exists:
        hdbg.dassert_dir_exists(abs_dst_dir)
    return abs_src_dir, abs_dst_dir


@task
def integrate_diff_dirs(  # type: ignore
    ctx,
    src_dir_basename=DEFAULT_SRC_DIR_BASENAME,
    dst_dir_basename=DEFAULT_DST_DIR_BASENAME,
    reverse=False,
    subdir="",
    copy=False,
    use_linux_diff=False,
    check_branches=True,
    clean_branches=True,
    remove_usual=False,
    run_diff_script=True,
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
    :param run_diff_script: run the diff script
    :param dry_run: do not execute the commands
    """
    _ = ctx
    hlitauti.report_task()
    if reverse:
        src_dir_basename, dst_dir_basename = dst_dir_basename, src_dir_basename
        _LOG.warning(
            "Reversing dirs: %s",
            hprint.to_str2(src_dir_basename, dst_dir_basename),
        )
    # Check that the integration branches are in the expected state.
    # _dassert_current_dir_matches(src_dir_basename)
    # When we integrate a dir that doesn't exist in the dst branch, we need to
    # skip the check for existence.
    check_exists = False
    abs_src_dir, abs_dst_dir = _resolve_src_dst_names(
        src_dir_basename, dst_dir_basename, subdir, check_exists=check_exists
    )
    hio.create_dir(abs_dst_dir, incremental=True)
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
            cmd = "dev_scripts/diff_to_vimdiff.py"
            if run_diff_script:
                cmd += " --run_diff_script"
            else:
                cmd += " --no_run_diff_script"
                _LOG.warning("Skipping running diff script")
            cmd += f" --dir1 {abs_src_dir} --dir2 {abs_dst_dir}"
            if remove_usual:
                vals = [
                    r"\/\.github\/",
                ]
                regex = "|".join(vals)
                cmd += f" --ignore_files='{regex}'"
    # We need to use `system` to get vimdiff to connect to stdin and stdout.
    if not dry_run:
        # hlitauti.run(ctx, cmd, dry_run=dry_run, print_cmd=True)
        os.system(cmd)


# #############################################################################


# TODO(gp): Allow to pass the hash of the last integration to consider.
#  Factor out the logic to find the hash

# Sometimes we want to see the changes in one dir since an integration point

# E.g., find all the changes in `im_v2` since the last integration
#
# > git log --oneline im_v2
# 77f612f75 SorrIssue244 CCXT timestamp representation unit test (#317)
# 6b981b1f6 Sorrtask298 rename get docker cmd to get docker run cmd (#331)
# bd33a5fb9 SorrTask267_Parquet_to_CSV (#267)
# 9819fd117 AmpTask1786_Integrate_20230518_im (#273)       <====
# d530ed561 Update (#272)
# b75eab7ad AmpTask1786_Integrate_20230518_3 (#271)
#
# > git difftool 9819fd117.. im_v2
# ...
#
# > git diff --name-only 9819fd117.. im_v2
# im_v2/ccxt/data/extract/test/test_ccxt_extractor.py
# im_v2/common/data/transform/convert_pq_to_csv.py
# im_v2/im_lib_tasks.py
# im_v2/test/test_im_lib_tasks.py
#
# for file in im_v2/ccxt/data/extract/test/test_ccxt_extractor.py im_v2/common/data/transform/convert_pq_to_csv.py im_v2/im_lib_tasks.py im_v2/test/test_im_lib_tasks.py; do
#   vimdiff ~/src/cmamp1/$file ~/src/kaizenflow1/$file
# done


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
    # Change the dir to the desired one.
    old_dir = os.getcwd()
    try:
        os.chdir(abs_dir)
        # Find the hash of all integration commits.
        cmd = "git log --date=local --oneline --date-order | grep AmpTask1786_Integrate"
        # Remove integrations like "'... Merge branch 'master' into
        # AmpTask1786_Integrate_20220113'"
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
    hlitauti.report_task()
    abs_dir = os.getcwd()
    _ = ctx
    files = _find_files_touched_since_last_integration(abs_dir, subdir)
    # Print the result.
    tag = "Files modified since the integration"
    print(hprint.frame(tag))
    print("\n".join(files))


# #############################################################################


def _integrate_files(
    files: Set[str],
    abs_left_dir: str,
    abs_right_dir: str,
    only_different_files: bool,
) -> List[Tuple[str, str, str]]:
    """
    Build a list of files to compare based on the pattern.

    :param files: relative path of the files to compare :param
        abs_left_dir, abs_right_dir: path of the left / right dir
    :param only_different_files: include in the script only the files
        that are different
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
                try:
                    equal = hio.from_file(left_file) == hio.from_file(right_file)
                except RuntimeError as e:
                    # RuntimeError: error='utf-8' codec can't decode byte 0xd0 in
                    # position 10: invalid continuation byte
                    _LOG.error("Caught error:\n%s", e)
                    equal = True
                skip = equal
            else:
                # They both exist, and we want to process even if they are the
                # same.
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
    src_dir_basename=DEFAULT_SRC_DIR_BASENAME,
    dst_dir_basename=DEFAULT_DST_DIR_BASENAME,
    reverse=False,
    subdir="",
    mode="vimdiff",
    file_direction="",
    only_different_files=True,
    check_branches=True,
):
    """
    Find and copy the files that are touched only in one branch or in both.

    :param ctx: invoke ctx
    :param src_dir_basename: dir with the source branch (e.g., amp1)
    :param dst_dir_basename: dir with the destination branch (e.g., cmamp1)
    :param reverse: switch the roles of the default source and destination branches
    :param subdir: directory to select
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
    :param check_branches: ensure that the current branches are for integration
        and not `master`
    """
    hlitauti.report_task()
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
            dir_name = os.path.dirname(file)
            # Skip empty dir, e.g., for `pytest.ini`.
            if dir_name != "":
                files_lst.append(dir_name)
        files_lst = sorted(list(set(files_lst)))
        print(hprint.frame("Dirs changed"))
        print("\n".join(files_lst))
    else:
        # Build the script with the operations to perform.
        if mode == "copy" and file_direction == "only_files_in_dst":
            raise ValueError("Can't copy files from destination")
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
            for cmd in script_txt.split("\n"):
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
    hlitauti.report_task()
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
    hlitauti.report_task()
    _ = ctx
    # Check that the integration branches are in the expected state.
    _dassert_current_dir_matches(src_dir_basename)
    # When we integrate a dir that doesn't exist in the dst branch, we need to
    # skip the check for existence.
    check_exists = False
    src_dir_basename, dst_dir_basename = _resolve_src_dst_names(
        src_dir_basename, dst_dir_basename, subdir, check_exists=check_exists
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


def _infer_dst_file_path(
    src_file_path: str,
    *,
    default_src_dir_basename: str = DEFAULT_SRC_DIR_BASENAME,
    default_dst_dir_basename: str = DEFAULT_DST_DIR_BASENAME,
    check_exists: bool = True,
) -> Tuple[str, str]:
    """
    Convert a file path across two dirs with the same data structure.

    E.g.,
    `.../src/cmamp1/.../test_data_snapshots/alpha_numeric_data_snapshots`
    is converted into
    `.../src/amp1/.../test_data_snapshots/alpha_numeric_data_snapshots`
    """
    _LOG.debug(hprint.to_str("src_file_path"))
    src_file_path = os.path.normpath(src_file_path)
    if check_exists:
        hdbg.dassert_path_exists(src_file_path)
    # Extract the repo dir name, by looking for one of the default basenames.
    target_dir = f"/{default_dst_dir_basename}/"
    idx = src_file_path.find(target_dir)
    if idx >= 0:
        src_dir_basename = default_dst_dir_basename
        dst_dir_basename = default_src_dir_basename
        subdir = src_file_path[idx + len(target_dir) :]
    else:
        target_dir = f"/{default_src_dir_basename}/"
        idx = src_file_path.find(target_dir)
        if idx >= 0:
            src_dir_basename = default_src_dir_basename
            dst_dir_basename = default_dst_dir_basename
            subdir = src_file_path[idx + len(target_dir) :]
        else:
            raise ValueError(
                f"Can't find either '{default_src_dir_basename}' or "
                f"'{default_dst_dir_basename}' in file_path="
                f"'{src_file_path}'"
            )
    # Replace src dir (e.g., `cmamp1`) with dst dir (e.g., `amp1`).
    dst_file_path = src_file_path.replace(
        f"/{src_dir_basename}/", f"/{dst_dir_basename}/"
    )
    _LOG.debug(hprint.to_str("dst_file_path subdir"))
    if check_exists:
        hdbg.dassert_path_exists(dst_file_path)
    return dst_file_path, subdir


@task
def integrate_rsync(  # type: ignore
    ctx,
    src_dir,
    src_dir_basename=DEFAULT_SRC_DIR_BASENAME,
    dst_dir_basename=DEFAULT_DST_DIR_BASENAME,
    dst_dir="",
    check_dir=True,
    dry_run=False,
):
    """
    Use `rsync` to bring two dirs to sync.

    E.g.,
    ```
    > invoke integrate_diff_dirs
    ...
      ... Only in .../cmamp1/.../alpha_numeric_data_snapshots: alpha
      ... Only in .../amp1/.../alpha_numeric_data_snapshots: latest

    # Accept the `cmamp1` side vs the `amp1` side with:
    > invoke integrate_rsync .../cmamp1/.../alpha_numeric_data_snapshots/
    ```

    :param src_dir: dir to be used. If empty, it is inferred from file_name
    :param dst_dir: dir to be used. If empty, it is inferred from file_name
    :param check_dir: force checking that src_dir and dst_dir are valid
        integration dirs
    :param dry_run: print the system command instead of executing them
    """
    hlitauti.report_task()
    _ = ctx
    src_dir = os.path.normpath(src_dir)
    hdbg.dassert_path_exists(src_dir)
    _LOG.info(hprint.to_str("src_dir"))
    if check_dir:
        _dassert_is_integration_branch(src_dir)
    # Resolve the dst dir.
    if dst_dir == "":
        dst_dir, _ = _infer_dst_file_path(
            src_dir,
            default_src_dir_basename=src_dir_basename,
            default_dst_dir_basename=dst_dir_basename,
        )
    if check_dir:
        _dassert_is_integration_branch(dst_dir)
    dst_dir = os.path.normpath(dst_dir)
    hdbg.dassert_path_exists(dst_dir)
    _LOG.info(hprint.to_str("dst_dir"))
    #
    _LOG.info("Syncing:\n'%s'\nto\n'%s'", src_dir, dst_dir)
    cmd = f"rsync --delete -a -r {src_dir}/ {dst_dir}/"
    hsystem.system(cmd, log_level=logging.INFO, dry_run=dry_run)


@task
def integrate_file(  # type: ignore
    ctx,
    file_name,
    src_dir_basename=DEFAULT_SRC_DIR_BASENAME,
    dst_dir_basename=DEFAULT_DST_DIR_BASENAME,
    dry_run=False,
):
    """
    Diff corresponding files in two different repos.

    ```
    # The path is assumed referred to current dir.
    > i integrate_file --file-name helpers/lib_tasks_integrate.py

    > i integrate_file --file-name /Users/saggese/src/kaizenflow1/helpers/lib_tasks_integrate.py

    > i integrate_file \
        --file-name helpers/lib_tasks_integrate.py \
        --src-dir-name cmamp1
        --dst-dir-name kaizenflow1
    ```

    :param file_name: it can be a full path (e.g.,
        `/Users/saggese/src/kaizenflow1/helpers/lib_tasks_integrate.py`)
        or a relative path to the root of the Git repo (e.g.,
        `helpers/lib_tasks_integrate.py)
    :param dst_dir: dir to be used. If empty, it is inferred from file_name
    :param check_dir: force checking that src_dir and dst_dir are valid
        integration dirs
    :param dry_run: print the system command instead of executing them
    """
    hlitauti.report_task()
    _ = ctx
    file_name = os.path.normpath(file_name)
    hdbg.dassert_file_exists(file_name)
    # If the file is in the current dir, we need to prepend the dir name.
    if not file_name.startswith("/"):
        file_name = os.path.join(os.getcwd(), file_name)
        _LOG.info(hprint.to_str("file_name"))
    # Resolve the src / dst dir, if needed.
    dst_file_name, _ = _infer_dst_file_path(
        file_name,
        default_src_dir_basename=src_dir_basename,
        default_dst_dir_basename=dst_dir_basename,
    )
    _LOG.info(hprint.to_str("file_name dst_file_name"))
    #
    _LOG.info("Syncing:\n'%s'\nto\n'%s'", file_name, dst_file_name)
    cmd = f"vimdiff {file_name} {dst_file_name}"
    # We need to use `system` to get vimdiff to connect to stdin and stdout.
    if not dry_run:
        # hlitauti.run(ctx, cmd, dry_run=dry_run, print_cmd=True)
        os.system(cmd)


# Compare the timestamp of last modification of a file.
# FILE=helpers/lib_tasks_git.py; (cd ~/src/cmamp1; git log -1 $FILE); (cd ~/src/kaizenflow1; git log -1 $FILE)

# > git log --pretty=format:"%h - %an, %ad : %s" --date=short | grep _Integrate_ | head -5
# fffa1c8b2 - GP Saggese, 2023-06-30 : AmpTask1786_Integrate_20230627_7 (#367)
# 5a05a0c94 - GP Saggese, 2023-06-29 : AmpTask1786_Integrate_20230627_6 (#365)
# 6c3ad7d87 - GP Saggese, 2023-06-29 : AmpTask1786_Integrate_20230627_5 (#364)
# 36abfd8b3 - GP Saggese, 2023-06-28 : AmpTask1786_Integrate_20230627_3 (#361)
# 65fe42d38 - GP Saggese, 2023-06-28 : AmpTask1786_Integrate_20230627_2 (#360)

# In Sorr
# GIT_INTEGR_HASH=fffa1c8b2
# fffa1c8b2 - GP Saggese, 2023-06-30 : AmpTask1786_Integrate_20230627_7 (#367)

# In cmamp
# 20526ed09 - GP Saggese, 2023-08-10 : AmpTask1786_Integrate_20230810_2 (#5011)

# Show files changed since an integration point
# > git diff --name-only $GIT_INTEGR_HASH dataflow_amp
# dataflow_amp/system/mock1/test/test_mock1_forecast_system.py

# Show the difference since an integration point
# git difftool $GIT_INTEGR_HASH.. dataflow_amp
