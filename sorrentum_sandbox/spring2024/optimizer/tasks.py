import logging
import os

import helpers.lib_tasks_utils as hlitauti

# Expose the pytest targets.
# Extract with:
# > i print_tasks --as-code
from optimizer.opt_lib_tasks import (  # noqa: F401  # pylint: disable=unused-import
    opt_docker_bash,
    opt_docker_build_local_image,
    opt_docker_cmd,
    opt_docker_down,
    opt_docker_jupyter,
    opt_docker_pull,
    opt_docker_push_dev_image,
    opt_docker_release_dev_image,
    opt_docker_tag_local_image_as_dev,
    opt_docker_up,
    opt_run_fast_tests,
    opt_run_slow_tests,
)

_LOG = logging.getLogger(__name__)


# #############################################################################
# Setup.
# #############################################################################


CK_ECR_BASE_PATH = os.environ["CK_ECR_BASE_PATH"]


default_params = {
    "CK_ECR_BASE_PATH": CK_ECR_BASE_PATH,
    # When testing a change to the build system in a branch you can use a
    # different image, e.g., `XYZ_tmp` to not interfere with the prod system.
    # "BASE_IMAGE": "opt_tmp",
    "BASE_IMAGE": "opt",
    "DEV_TOOLS_IMAGE_PROD": f"{CK_ECR_BASE_PATH}/dev_tools:prod",
}


hlitauti.set_default_params(default_params)
