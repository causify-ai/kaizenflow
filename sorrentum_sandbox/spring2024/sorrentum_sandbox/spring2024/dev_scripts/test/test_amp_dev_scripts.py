import logging
import os

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hnetwork as hnetwor
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# url.py
# #############################################################################


class Test_url_py1(hunitest.TestCase):
    def test_get_file_name1(self) -> None:
        url_tmp = (
            "http://localhost:10001/notebooks/oil/ST/"
            + "Task229_Exploratory_analysis_of_ST_data_part1.ipynb"
        )
        act = hnetwor.get_file_name(url_tmp)
        exp = "oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb"
        self.assertEqual(act, exp)

    def test_get_file_name2(self) -> None:
        url_tmp = (
            "https://github.com/.../.../blob/"
            + "master/oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb"
        )
        act = hnetwor.get_file_name(url_tmp)
        exp = "oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb"
        self.assertEqual(act, exp)

    def test_run1(self) -> None:
        exec_name = os.path.join(hgit.get_amp_abs_path(), "dev_scripts/url.py")
        hdbg.dassert_path_exists(exec_name)
        _LOG.debug(hprint.to_str("exec_name"))
        cmd = (
            f"{exec_name} http://localhost:9999/notebooks/research/"
            "Task51_experiment_with_sklearn_pipeline/"
            "Task51_experiment_with_sklearn_pipeline.ipynb"
        )
        hsystem.system(cmd)


# #############################################################################


# TODO(gp): Move this to test to the proper dir `helpers/test/test.py`


class Test_env1(hunitest.TestCase):
    def test_get_system_signature1(self) -> None:
        _ = henv.get_system_signature()
