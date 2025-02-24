import logging
import unittest.mock as umock

import helpers.hdocker as hdocker
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# Test_dassert_is_datetime1
# #############################################################################


class Test_replace_shared_root_path(hunitest.TestCase):
    def test_replace_shared_root_path1(self) -> None:
        """
        Test replacing shared root path with the dummy mapping.
        """
        # Mock `henv.execute_repo_config_code()` to return a dummy mapping.
        mock_mapping = {
            "/shared_folder1": "/data/shared1",
            "/shared_folder2": "/data/shared2",
        }
        with umock.patch.object(
            hdocker.henv, "execute_repo_config_code", return_value=mock_mapping
        ):
            # Test replacing shared root path.
            path1 = "/shared_folder1/asset1"
            act1 = hdocker.replace_shared_root_path(path1)
            exp1 = "/data/shared1/asset1"
            self.assertEqual(act1, exp1)
            #
            path2 = "/shared_folder2/asset2"
            act2 = hdocker.replace_shared_root_path(path2)
            exp2 = "/data/shared2/asset2"
            self.assertEqual(act2, exp2)
            #
            path3 = 'object("/shared_folder2/asset2/item")'
            act3 = hdocker.replace_shared_root_path(path3)
            exp3 = 'object("/data/shared2/asset2/item")'
            self.assertEqual(act3, exp3)
