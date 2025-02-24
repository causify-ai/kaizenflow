import logging

import helpers.henv as henv
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_env1(hunitest.TestCase):
    def test_get_system_signature1(self) -> None:
        txt = henv.get_system_signature()
        _LOG.debug(txt)

    def test_has_module1(self) -> None:
        """
        Check that the function returns true for the existing package.
        """
        self.assertTrue(henv.has_module("numpy"))

    def test_has_not_module1(self) -> None:
        """
        Check that the function returns false for the non-existing package.
        """
        self.assertFalse(henv.has_module("no_such_module"))


# #############################################################################


class Test_execute_repo_config_code1(hunitest.TestCase):
    """
    Make sure we can execute the code from `repo_config.py`.
    """

    def test_get_repo_map1(self) -> None:
        self._exec("get_repo_map()")

    def test_get_host_name1(self) -> None:
        self._exec("get_host_name()")

    def test_get_docker_base_image_name1(self) -> None:
        self._exec("get_docker_base_image_name()")

    def test_has_didn_support1(self) -> None:
        self._exec("has_dind_support()")

    def _exec(self, code_to_execute: str) -> None:
        val = henv.execute_repo_config_code(code_to_execute)
        _LOG.debug("%s=%s", code_to_execute, val)
