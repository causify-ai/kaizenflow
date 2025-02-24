import os
from typing import Dict

import pytest

import helpers.hgit as hgit
import helpers.hunit_test as hunitest
import helpers.lib_tasks_utils as hlitauti
import optimizer.opt_lib_tasks as ooplitas

# TODO(Grisha): unify with `helpers/test/test_lib_tasks.py` CmTask #1485.


def _get_default_params() -> Dict[str, str]:
    """
    Get fake params pointing to a different image so we can test the code
    without affecting the official images.
    """
    ecr_base_path = os.environ["CK_ECR_BASE_PATH"]
    default_params = {
        "CK_ECR_BASE_PATH": ecr_base_path,
        "BASE_IMAGE": "opt_test",
        "DEV_TOOLS_IMAGE_PROD": f"{ecr_base_path}/dev_tools:prod",
    }
    return default_params


class _OptLibTasksTestCase(hunitest.TestCase):
    """
    Test class injecting default parameters in the `opt_lib_tasks` singleton in
    `set_up_test()` and cleaning up the singleton in `tear_down_test()`.
    """

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        params = _get_default_params()
        hlitauti.set_default_params(params)

    def tear_down_test(self) -> None:
        hlitauti.reset_default_params()


@pytest.mark.skipif(hgit.is_amp(), reason="Doesn't run in amp")
class TestGetOptDockerUpDownCmd(_OptLibTasksTestCase):
    """
    Test optimizer `docker-compose up/down`.
    """

    def test1(self) -> None:
        """
        Command `docker-compose up`, detached mode.
        """
        detach = True
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        actual = ooplitas._get_opt_docker_up_cmd(
            detach, base_image, stage, version
        )
        expected = r"""
        IMAGE=$CK_ECR_BASE_PATH/opt_test:dev-1.0.0 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml \
            --env-file devops/env/default.env \
            up \
            -d \
            app
        """
        self._check(actual, expected)

    def test2(self) -> None:
        """
        Command `docker-compose up`.
        """
        detach = False
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        actual = ooplitas._get_opt_docker_up_cmd(
            detach, base_image, stage, version
        )
        expected = r"""
        IMAGE=$CK_ECR_BASE_PATH/opt_test:dev-1.0.0 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml \
            --env-file devops/env/default.env \
            up \
            app
        """
        self._check(actual, expected)

    def test3(self) -> None:
        """
        Command `docker-compose down`.
        """
        base_image = ""
        stage = "dev"
        version = "1.0.0"
        actual = ooplitas._get_opt_docker_down_cmd(base_image, stage, version)
        expected = r"""
        IMAGE=$CK_ECR_BASE_PATH/opt_test:dev-1.0.0 \
            docker-compose \
            --file $GIT_ROOT/devops/compose/docker-compose.yml \
            --env-file devops/env/default.env \
            down
        """
        self._check(actual, expected)

    def _check(self, actual: str, expected: str) -> None:
        """
        Compare actual test outcomes to the expected ones.
        """
        actual = hunitest.purify_txt_from_client(actual)
        self.assert_equal(actual, expected, fuzzy_match=True)
