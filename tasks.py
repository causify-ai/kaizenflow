import logging
import os
from typing import Any

import repo_config as rconf

# Expose the pytest targets.
# Extract with:
# > i print_tasks --as-code
from helpers.lib_tasks import (  # This is not an invoke target.
    parse_command_line,
    set_default_params,
)

from helpers.lib_tasks import (  # isort: skip # noqa: F401  # pylint: disable=unused-import
    docker_bash,
    docker_build_local_image,
    docker_build_prod_image,
    docker_cmd,
    docker_images_ls_repo,
    docker_jupyter,
    docker_kill,
    docker_login,
    docker_ps,
    docker_pull,
    docker_pull_dev_tools,
    docker_push_dev_image,
    docker_push_prod_candidate_image,
    docker_push_prod_image,
    docker_release_all,
    docker_release_dev_image,
    docker_release_prod_image,
    # TODO(gp): -> docker_release_rollback_dev_image
    docker_rollback_dev_image,
    docker_rollback_prod_image,
    docker_stats,
    # TODO(gp): -> docker_release_...
    docker_tag_local_image_as_dev,
    find,
    find_check_string_output,
    find_test_class,
    find_test_decorator,
    fix_perms,
    gh_create_pr,
    gh_issue_title,
    gh_login,
    gh_workflow_list,
    gh_workflow_run,
    git_add_all_untracked,
    git_branch_copy,
    git_branch_diff_with_base,
    git_branch_diff_with_master,
    git_branch_files,
    git_branch_next_name,
    git_clean,
    # TODO(gp): -> git_branch_create
    git_create_branch,
    # TODO(gp): -> git_patch_create
    git_create_patch,
    git_delete_merged_branches,
    # TODO(gp): -> git_master_fetch
    git_fetch_master,
    # TODO(gp): -> git_files_list
    git_files,
    # TODO(gp): -> git_files_last_commit_
    git_last_commit_files,
    # TODO(gp): -> git_master_merge
    git_merge_master,
    git_pull,
    # TODO(gp): -> git_branch_rename
    git_rename_branch,
    git_roll_amp_forward,
    integrate_create_branch,
    integrate_diff_dirs,
    integrate_diff_overlapping_files,
    integrate_files,
    integrate_find_files,
    integrate_find_files_touched_since_last_integration,
    lint,
    lint_check_python_files,
    lint_check_python_files_in_docker,
    lint_create_branch,
    lint_detect_cycles,
    print_env,
    print_setup,
    print_tasks,
    pytest_clean,
    pytest_compare_logs,
    pytest_find_unused_goldens,
    pytest_rename_test,
    pytest_repro,
    run_blank_tests,
    run_coverage_report,
    run_fast_slow_superslow_tests,
    run_fast_slow_tests,
    run_fast_tests,
    run_qa_tests,
    run_slow_tests,
    run_superslow_tests,
    run_tests,
    traceback,
)


_LOG = logging.getLogger(__name__)


# #############################################################################
# Setup.
# #############################################################################


# TODO(gp): Move it to lib_tasks.
AM_ECR_BASE_PATH = os.environ["AM_ECR_BASE_PATH"]
DOCKER_BASE_IMAGE_NAME = rconf.get_docker_base_image_name()


def _run_qa_tests(ctx: Any, stage: str, version: str) -> bool:
    """
    Run QA tests to verify that the invoke tasks are working properly.

    This is used when qualifying a docker image before releasing.
    """
    _ = ctx
    # The QA tests are in `qa_test_dir` and are marked with `qa_test_tag`.
    qa_test_dir = "test"
    # qa_test_dir = "test/test_tasks.py::TestExecuteTasks1::test_docker_bash"
    qa_test_tag = "qa and not superslow"
    cmd = f'pytest -m "{qa_test_tag}" {qa_test_dir} --image_stage {stage}'
    if version:
        cmd = f"{cmd} --image_version {version}"
    ctx.run(cmd)
    return True


default_params = {
    "AM_ECR_BASE_PATH": AM_ECR_BASE_PATH,
    # When testing a change to the build system in a branch you can use a different
    # image, e.g., `XYZ_tmp` to not interfere with the prod system.
    # "BASE_IMAGE": "amp_tmp",
    "BASE_IMAGE": DOCKER_BASE_IMAGE_NAME,
    "QA_TEST_FUNCTION": _run_qa_tests,
}


set_default_params(default_params)
parse_command_line()
