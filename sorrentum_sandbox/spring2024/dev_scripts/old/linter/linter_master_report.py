#!/usr/bin/env python
"""
Compute the change of lints of a branch with respect to master.

Import as:

import dev_scripts.old.linter.linter_master_report as dsollmare
"""

import argparse
import logging
import os
import sys
from typing import List, Optional, Tuple

import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def _perform_linter_for_test_branch(base_commit_sha: str) -> Tuple[int, int, str]:
    cmd = "git reset --hard"
    # Clean up the client from all linter artifacts.
    hsystem.system(cmd)
    cmd = f"linter.py -t {base_commit_sha} --post_check"
    # We run the same comment twice since we need to get 2 different information
    # from the linter.
    # With `--post_check` we get information about whether any file needed to be
    # linted. Without we receive the number of lints.
    # TODO(Sergey): Pass both values with one execution of the linter and stop
    #  this insanity.
    branch_dirty = hsystem.system(cmd, abort_on_error=False)
    _LOG.info("Branch dirty: %s", branch_dirty)
    #
    cmd = "git reset --hard"
    # Clean up the client from all linter artifacts.
    hsystem.system(cmd)
    #
    cmd = f"linter.py -t {base_commit_sha}"
    branch_lints = hsystem.system(cmd, abort_on_error=False)
    _LOG.info("Branch lints: %s", branch_lints)
    # Read the lints reported from the linter.
    linter_output_filename = "./linter_warnings.txt"
    linter_message = hio.from_file(linter_output_filename)
    linter_message = "```\n" + linter_message + "\n```\n"
    cmd = "git reset --hard"
    # Clean up the client from all linter artifacts.
    hsystem.system(cmd)
    return branch_lints, branch_dirty, linter_message


def _perform_linter_for_reference_branch(
    base_commit_sha: str, mod_files: List[str]
) -> Tuple[int, int]:
    # # Calculate "Before*" stats
    cmd = "git reset --hard"
    hsystem.system(cmd)
    cmd = f"git checkout {base_commit_sha} --recurse-submodules"
    # Check out master at the requested hash.
    hsystem.system(cmd)
    mod_files_as_str = " ".join(mod_files)
    cmd = f"linter.py --files {mod_files_as_str} --post_check"
    # We run the same comment twice since we need to get 2 different information
    # from the linter.
    # With `--post_check` we get information about whether any file needed to be
    # linted. Without we receive the number of lints.
    # TODO(Sergey): Pass both values with one execution of the linter and stop
    #  this insanity.
    # Lint the files that are modified.
    master_dirty = hsystem.system(cmd, abort_on_error=False)
    _LOG.info("Master dirty: %s", master_dirty)
    # Clean up the client.
    cmd = "git reset --hard"
    hsystem.system(cmd)
    cmd = f"linter.py --files {mod_files_as_str}"
    master_lints = hsystem.system(cmd, abort_on_error=False)
    _LOG.info("Master lints: %s", master_lints)
    # Clean up the client.
    cmd = "git reset --hard"
    hsystem.system(cmd)
    return master_lints, master_dirty


def _calculate_exit_status(
    branch_dirty_status: bool,
    master_lints: int,
    branch_lints: int,
) -> Tuple[int, str]:
    """
    Calculate status and error message.
    """
    exit_status = 0
    errors = []
    if branch_dirty_status:
        errors.append("**ERROR**: Run `linter.py. -b` locally before merging.")
        exit_status = 1
    if master_lints > 0:
        errors.append("**WARNING**: Your branch has lints. Please fix them.")
    if branch_lints > master_lints:
        exit_status = 1
        errors.append("**ERROR**: You introduced more lints. Please fix them.")
    return exit_status, "\n".join(errors)


def _compute_stats(
    master_dirty: int,
    branch_dirty: int,
    master_lints: int,
    branch_lints: int,
) -> Tuple[bool, bool, int, str]:
    # Prepares a message and exit status
    master_dirty_status = master_dirty > 0
    branch_dirty_status = branch_dirty > 0
    exit_status, errors = _calculate_exit_status(
        branch_dirty_status, master_lints, branch_lints
    )
    return master_dirty_status, branch_dirty_status, exit_status, errors


def _calculate_stats(
    base_commit_sha: str,
    head_commit_sha: str,
    head_branch_name: str,
    build_url: Optional[str] = None,
) -> Tuple[int, str]:
    """
    Compute the statistics from the linter when run on a branch vs master.

    :param base_commit_sha: hash of the branch to compare
    :param head_branch_name: name of the branch to be compared
    :param branch_name: branch name for the report
    :param build_url: jenkins build url
    :return: an integer representing the exit status and an error message.
    """
    dir_name = "."
    # TODO(Sergey): Not sure what to do with files that are not present in the
    #  branch.
    remove_files_non_present = False
    # Find the files that are modified in the branch.
    mod_files = hgit.get_modified_files_in_branch(
        dir_name,
        base_commit_sha,
        remove_files_non_present=remove_files_non_present,
    )
    branch_lints, branch_dirty, linter_message = _perform_linter_for_test_branch(
        base_commit_sha
    )
    master_lints, master_dirty = _perform_linter_for_reference_branch(
        base_commit_sha, mod_files
    )
    (
        master_dirty_status,
        branch_dirty_status,
        exit_status,
        errors,
    ) = _compute_stats(master_dirty, branch_dirty, master_lints, branch_lints)
    # Message
    message = list()
    # Report title
    message.append("# Results of the linter build")
    # Console url for Jenkins
    console_url = os.path.join(str(build_url), "consoleFull")
    if build_url is not None:
        console_message = f"Console output: {console_url}"
    else:
        console_message = "Console output: No console output"
    message.append(console_message)
    # Statuses and additional info
    message.append(f"- Master (sha: {base_commit_sha})")
    message.append(f"\t- Number of lints: {master_lints}")
    message.append(f"\t- Dirty (i.e., linter was not run): {master_dirty_status}")
    message.append(f"- Branch ({head_branch_name}: {head_commit_sha})")
    message.append(f"\t- Number of lints: {branch_lints}")
    message.append(f"\t- Dirty (i.e., linter was not run): {branch_dirty_status}")
    diff_lints = branch_lints - master_lints
    message.append(
        f"\nThe number of lints introduced with this change: {diff_lints}"
    )
    # Format report in order. Message \n Errors \n Linter output.
    message = "\n".join(message)
    message += "\n\n" + errors
    message += "\n" + linter_message
    return exit_status, message


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Select files.
    parser.add_argument(
        "--jenkins",
        action="store_true",
        help="",
    )
    parser.add_argument("--base_commit_sha", type=str, required=False, help="")
    parser.add_argument("--head_branch_name", type=str, required=False, help="")
    parser.add_argument("--head_commit_sha", type=str, required=False, help="")

    hparser.add_verbosity_arg(parser)
    return parser


def _main(args: argparse.Namespace) -> int:
    build_url = None
    if args.jenkins:
        # Fetch the environment variable as passed by Jenkins from Git web-hook
        base_commit_sha = os.environ["data_pull_request_base_sha"]
        head_branch_name = os.environ["data_pull_request_head_ref"]
        head_commit_sha = os.environ["data_pull_request_head_sha"]
        build_url = os.environ["BUILD_URL"]
    else:
        # Use passed parameters from command line or infer some defaults from
        # the current git client.
        base_commit_sha = args.base_commit_sha or "master"
        head_branch_name = args.head_branch_name or hgit.get_branch_name()
        head_commit_sha = args.head_commit_sha or hgit.get_current_commit_hash()
    rc, message = _calculate_stats(
        base_commit_sha, head_commit_sha, head_branch_name, build_url
    )
    # Save the result or print it to the screen.
    if args.jenkins:
        hio.to_file("./tmp_message.txt", message)
        hio.to_file("./tmp_exit_status.txt", str(rc))
    else:
        print(message)
    cmd = "git reset --hard"
    hsystem.system(cmd)
    cmd = f"git checkout {head_branch_name} --recurse-submodules"
    # Clean up the branch bringing to the original status.
    hsystem.system(cmd)
    return rc


if __name__ == "__main__":
    parser_ = _parse()
    args_ = parser_.parse_args()
    rc_ = _main(args_)
    sys.exit(rc_)
