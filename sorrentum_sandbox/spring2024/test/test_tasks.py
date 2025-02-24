import logging
import os
from typing import Any, Dict

import pytest

import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _get_default_params_mock() -> Dict[str, str]:
    """
    Get fake params pointing to a different image so we can test the code
    without affecting the official images.
    """
    ecr_base_path = os.environ["AM_ECR_BASE_PATH"]
    default_params = {
        "AM_ECR_BASE_PATH": ecr_base_path,
        "BASE_IMAGE": "amp_test",
        "DEV_TOOLS_IMAGE_PROD": f"{ecr_base_path}/dev_tools:prod",
    }
    return default_params


def _get_invoke_cmd_params(self_: Any) -> str:
    """
    Return the parameters passed to pytest controlling the stage / version to
    use for commands using a specific stage / version (e.g., `invoke bash`).

    E.g., `--image_stage`, `--image_version`
    """
    image_stage = self_._config.getoption("--image_stage")
    image_version = self_._config.getoption("--image_version")
    _LOG.debug(hprint.to_str("image_stage image_version"))
    cmd_params = []
    cmd_params.append(f"--stage {image_stage}")
    if image_version:
        cmd_params.append(f"--version {image_version}")
    cmd_params = " ".join(cmd_params)
    return cmd_params


class TestExecuteTasks1(hunitest.QaTestCase):
    """
    Execute tasks that don't change state of the system (e.g., commit images).
    """

    @pytest.fixture(autouse=True)
    def inject_config(self, request: Any) -> None:
        self._config = request.config

    def test_list(self) -> None:
        cmd = "invoke --list"
        hsystem.system(cmd)

    def test_print_setup1(self) -> None:
        cmd = "invoke print_setup"
        hsystem.system(cmd)

    def test_docker_images_ls_repo1(self) -> None:
        cmd = "invoke docker_images_ls_repo"
        hsystem.system(cmd)

    def test_docker_ps(self) -> None:
        cmd = "invoke docker_ps"
        hsystem.system(cmd)

    def test_docker_stats(self) -> None:
        cmd = "invoke docker_stats --all"
        hsystem.system(cmd)

    def test_docker_login1(self) -> None:
        cmd = "invoke docker_login"
        hsystem.system(cmd)

    # invoke cmd-like commands.

    def test_docker_cmd1(self) -> None:
        invoke_target = "docker_cmd"
        invoke_params = _get_invoke_cmd_params(self)
        invoke_params += ' --cmd="ls"'
        cmd = f"invoke {invoke_target} {invoke_params}"
        hsystem.system(cmd)

    def test_docker_jupyter1(self) -> None:
        invoke_target = "docker_jupyter"
        invoke_params = _get_invoke_cmd_params(self)
        invoke_params += " --self-test --no-auto-assign-port"
        cmd = f"invoke {invoke_target} {invoke_params}"
        hsystem.system(cmd)


class TestExecuteTasks2(hunitest.QaTestCase):
    """
    Execute tasks that change the state of the system but use a temporary
    image.
    """

    def test_docker_jupyter1(self) -> None:
        cmd = "invoke docker_jupyter --self-test --no-auto-assign-port"
        hsystem.system(cmd)

    def test_docker_pull1(self) -> None:
        cmd = "invoke docker_pull"
        hsystem.system(cmd)

    # Images workflows.

    @pytest.mark.superslow("Around 5 mins")
    def test_docker_build_local_image(self) -> None:
        params = _get_default_params_mock()
        base_image = params["AM_ECR_BASE_PATH"] + "/" + params["BASE_IMAGE"]
        # Version must be bigger than any version in `changelog.txt`.
        cmd = f"invoke docker_build_local_image --version 999.0.0 --cache --base-image={base_image}"
        hsystem.system(cmd)

    @pytest.mark.skip("No prod image for amp yet")
    @pytest.mark.slow("Around 5 mins")
    def test_docker_build_prod_image(self) -> None:
        params = _get_default_params_mock()
        base_image = params["AM_ECR_BASE_PATH"] + "/" + params["BASE_IMAGE"]
        # Version must be bigger than any version in `changelog.txt`.
        cmd = f"invoke docker_build_prod_image --version 999.0.0 --cache --base-image={base_image}"
        hsystem.system(cmd)

    # Run tests.

    def test_run_blank_tests1(self) -> None:
        cmd = "invoke run_blank_tests"
        hsystem.system(cmd)

    @pytest.mark.skip
    @pytest.mark.slow("Around 30 secs")
    def test_collect_only1(self) -> None:
        cmd = "invoke docker_cmd --cmd='pytest --collect-only'"
        hsystem.system(cmd)

    def test_collect_only2(self) -> None:
        # We need to specify the dir independently of the git root since this will
        # run inside a container.
        dir_name = '$(dirname $(find . -name "test_dbg.py" -type f))'
        cmd = f"invoke docker_cmd --cmd='pytest {dir_name} --collect-only'"
        hsystem.system(cmd)

    def test_run_fast_tests(self) -> None:
        file_name = '$(find . -name "test_dbg.py" -type f)'
        cmd = f"invoke run_fast_tests --pytest-opts='{file_name}'"
        hsystem.system(cmd)

    def test_run_fast_tests_failed(self) -> None:
        file_name = "helpers/test/test_lib_tasks.py::TestFailing"
        cmd = f"export AM_FORCE_TEST_FAIL=1; invoke run_fast_tests --pytest-opts='{file_name}'"
        with self.assertRaises(RuntimeError):
            hsystem.system(cmd)

    # Linter.

    def test_lint1(self) -> None:
        file_name = '$(find . -name "dbg.py" -type f)'
        cmd = f"invoke lint --files='{file_name}' --phases='black'"
        hsystem.system(cmd)
