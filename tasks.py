import logging
import os
from typing import Any

import repo_config as rconf

# Expose the pytest targets.
# Extract with:
# > i print_tasks --as-code
from helpers.lib_tasks import set_default_params  # This is not an invoke target.
from helpers.lib_tasks import (  # noqa: F401  # pylint: disable=unused-import
    check_python_files,
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
    docker_push_prod_image,
    docker_release_all,
    docker_release_dev_image,
    docker_release_prod_image,
    docker_rollback_dev_image,
    docker_rollback_prod_image,
    docker_stats,
    docker_tag_local_image_as_dev,
    find_check_string_output,
    find_test_class,
    find_test_decorator,
    fix_perms,
    gh_create_pr,
    gh_issue_title,
    gh_workflow_list,
    gh_workflow_run,
    git_add_all_untracked,
    git_branch_copy,
    git_branch_diff_with_base,
    git_branch_files,
    git_branch_next_name,
    git_clean,
    git_create_branch,
    git_create_patch,
    git_delete_merged_branches,
    git_files,
    git_last_commit_files,
    git_merge_master,
    git_pull,
    git_pull_master,
    git_rename_branch,
    integrate_compare_branch_with_base,
    integrate_copy_dirs,
    integrate_create_branch,
    integrate_diff_dirs,
    lint,
    lint_create_branches,
    print_setup,
    print_tasks,
    pytest_clean,
    pytest_compare,
    pytest_failed,
    pytest_failed_freeze_test_list,
    run_blank_tests,
    run_fast_slow_tests,
    run_fast_tests,
    run_qa_tests,
    run_slow_tests,
    run_superslow_tests,
    traceback,
)

_LOG = logging.getLogger(__name__)


# #############################################################################
# Setup.
# #############################################################################


# TODO(gp): Move it to lib_tasks.
ECR_BASE_PATH = os.environ["AM_ECR_BASE_PATH"]
DOCKER_BASE_IMAGE_NAME = rconf.get_docker_base_image_name()


# pylint: disable=unused-argument
def _run_qa_tests(ctx: Any, stage: str, version: str) -> bool:
    """
    Run QA tests to verify that the invoke tasks are working properly.

    This is used when qualifying a docker image before releasing.
    """
    cmd = f"pytest -m qa test --image_stage {stage}"
    if version:
        cmd = f"{cmd} --image_version {version}"
    ctx.run(cmd)
    return True


default_params = {
    "ECR_BASE_PATH": ECR_BASE_PATH,
    # When testing a change to the build system in a branch you can use a different
    # image, e.g., `XYZ_tmp` to not interfere with the prod system.
    # "BASE_IMAGE": "amp_tmp",
    "BASE_IMAGE": DOCKER_BASE_IMAGE_NAME,
    "QA_TEST_FUNCTION": _run_qa_tests,
}


set_default_params(default_params)
