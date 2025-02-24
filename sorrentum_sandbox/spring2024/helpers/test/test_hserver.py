import logging

import helpers.hserver as hserver
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_hserver1(hunitest.TestCase):
    def test_is_inside_ci1(self) -> None:
        is_inside_ci_ = hserver.is_inside_ci()
        if is_inside_ci_:
            # Inside CI we expect to run inside Docker.
            self.assertTrue(hserver.is_inside_docker())

    def test_is_inside_docker1(self) -> None:
        # We always run tests inside Docker.
        self.assertTrue(hserver.is_inside_docker())

    def test_is_dev_ck1(self) -> None:
        _ = hserver.is_dev_ck()

    def test_is_cmamp_prod1(self) -> None:
        is_cmamp_prod = hserver.is_cmamp_prod()
        if is_cmamp_prod:
            # Prod runs inside Docker.
            self.assertTrue(hserver.is_inside_docker())

    def test_gp1(self) -> None:
        user = hserver.get_host_user_name()
        _LOG.debug("user=%s", user)
        _LOG.debug("is_mac=%s", hserver.is_mac())
        if user == "saggese" and hserver.is_mac():
            version = "Catalina"
            _LOG.debug("Checking version=%s", version)
            self.assertTrue(hserver.is_mac(version=version))

    def test_consistency1(self) -> None:
        """
        One and only one set up config should be true.
        """
        hserver._dassert_setup_consistency()
