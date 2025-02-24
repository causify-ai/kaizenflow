import logging

import helpers.hunit_test as hunitest
import helpers.repo_config_utils as hrecouti

_LOG = logging.getLogger(__name__)


class Test_repo_config_utils1(hunitest.TestCase):
    def test_consistency1(self) -> None:
        hrecouti._dassert_setup_consistency()
