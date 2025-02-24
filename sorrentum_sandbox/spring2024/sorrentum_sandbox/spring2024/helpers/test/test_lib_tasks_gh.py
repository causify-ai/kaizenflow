import logging

import pytest

import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hserver as hserver
import helpers.hunit_test as hunitest
import helpers.lib_tasks_gh as hlitagh

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


class TestLibTasks1(hunitest.TestCase):
    """
    Test some auxiliary functions, e.g., `_get_gh_issue_title()`.
    """

    @pytest.mark.skip("CmTask #2362.")
    def test_get_gh_issue_title1(self) -> None:
        issue_id = 1
        repo = "amp"
        act = hlitagh._get_gh_issue_title(issue_id, repo)
        exp = (
            "AmpTask1_Bridge_Python_and_R",
            "https://github.com/alphamatic/amp/issues/1",
        )
        self.assert_equal(str(act), str(exp))

    @pytest.mark.skipif(
        not hgit.is_cmamp(),
        reason="CmampTask #683.",
    )
    @pytest.mark.skip(reason="Waiting on CmTask#1996")
    def test_get_gh_issue_title3(self) -> None:
        issue_id = 1
        repo = "dev_tools"
        act = hlitagh._get_gh_issue_title(issue_id, repo)
        exp = (
            "DevToolsTask1_Migration_from_amp",
            "https://github.com/alphamatic/dev_tools/issues/1",
        )
        self.assert_equal(str(act), str(exp))

    # TODO(ShaopengZ): fails when running kaizenflow on CK server. `gh auth
    # login` issue.
    @pytest.mark.skipif(
        henv.execute_repo_config_code("get_name()") == "//kaizen"
        and hserver.is_inside_ci(),
        reason="Do not pass from kaizenflow GH actions. See CmTask5211",
    )
    def test_get_gh_issue_title4(self) -> None:
        issue_id = 1
        repo = "current"
        _ = hlitagh._get_gh_issue_title(issue_id, repo)
