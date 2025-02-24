import logging
import os
from typing import List, Optional

import pytest

import helpers.hgit as hgit
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# Unfortunately we can't check the outcome of some of these functions since we
# don't know in which dir we are running. Thus we just test that the function
# completes and visually inspect the outcome, if possible.


def _execute_func_call(func_call: str) -> None:
    """
    Execute a function call, e.g., `func_call = "hgit.get_modified_files()"`.
    """
    act = eval(func_call)
    _LOG.debug("\n-> %s=\n  '%s'", func_call, act)


class Test_git_submodule1(hunitest.TestCase):
    def test_get_client_root1(self) -> None:
        func_call = "hgit.get_client_root(super_module=True)"
        _execute_func_call(func_call)

    def test_get_client_root2(self) -> None:
        func_call = "hgit.get_client_root(super_module=False)"
        _execute_func_call(func_call)

    def test_get_project_dirname1(self) -> None:
        func_call = "hgit.get_project_dirname()"
        _execute_func_call(func_call)

    def test_get_branch_name1(self) -> None:
        _ = hgit.get_branch_name()

    def test_is_inside_submodule1(self) -> None:
        func_call = "hgit.is_inside_submodule()"
        _execute_func_call(func_call)

    # Outside CK infra, the following call hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    def test_is_amp(self) -> None:
        func_call = "hgit.is_amp()"
        _execute_func_call(func_call)

    def test_get_path_from_supermodule1(self) -> None:
        func_call = "hgit.get_path_from_supermodule()"
        _execute_func_call(func_call)

    def test_get_submodule_paths1(self) -> None:
        func_call = "hgit.get_submodule_paths()"
        _execute_func_call(func_call)


class Test_git_submodule2(hunitest.TestCase):
    # def test_get_submodule_hash1(self) -> None:
    #     dir_name = "amp"
    #     _ = hgit._get_submodule_hash(dir_name)

    def test_get_remote_head_hash1(self) -> None:
        dir_name = "."
        _ = hgit.get_head_hash(dir_name)

    # def test_report_submodule_status1(self) -> None:
    #     dir_names = ["."]
    #     short_hash = True
    #     _ = hgit.report_submodule_status(dir_names, short_hash)

    def test_get_head_hash1(self) -> None:
        dir_name = "."
        _ = hgit.get_head_hash(dir_name)

    def test_group_hashes1(self) -> None:
        head_hash = "a2bfc704"
        remh_hash = "a2bfc704"
        subm_hash = None
        exp = "head_hash = remh_hash = a2bfc704"
        #
        self._helper_group_hashes(head_hash, remh_hash, subm_hash, exp)

    def test_group_hashes2(self) -> None:
        head_hash = "22996772"
        remh_hash = "92167662"
        subm_hash = "92167662"
        exp = """
        head_hash = 22996772
        remh_hash = subm_hash = 92167662
        """
        #
        self._helper_group_hashes(head_hash, remh_hash, subm_hash, exp)

    def test_group_hashes3(self) -> None:
        head_hash = "7ea03eb6"
        remh_hash = "7ea03eb6"
        subm_hash = "7ea03eb6"
        exp = "head_hash = remh_hash = subm_hash = 7ea03eb6"
        #
        self._helper_group_hashes(head_hash, remh_hash, subm_hash, exp)

    def _helper_group_hashes(
        self, head_hash: str, remh_hash: str, subm_hash: Optional[str], exp: str
    ) -> None:
        act = hgit._group_hashes(head_hash, remh_hash, subm_hash)
        self.assert_equal(act, exp, fuzzy_match=True)


class Test_git_repo_name1(hunitest.TestCase):
    def test_parse_github_repo_name1(self) -> None:
        repo_name = "git@github.com:alphamatic/amp"
        host_name, repo_name = hgit._parse_github_repo_name(repo_name)
        self.assert_equal(host_name, "github.com")
        self.assert_equal(repo_name, "alphamatic/amp")

    def test_parse_github_repo_name2(self) -> None:
        repo_name = "https://github.com/alphamatic/amp"
        hgit._parse_github_repo_name(repo_name)
        host_name, repo_name = hgit._parse_github_repo_name(repo_name)
        self.assert_equal(host_name, "github.com")
        self.assert_equal(repo_name, "alphamatic/amp")

    def test_parse_github_repo_name3(self) -> None:
        repo_name = "git@github.fake.com:alphamatic/amp"
        host_name, repo_name = hgit._parse_github_repo_name(repo_name)
        self.assert_equal(host_name, "github.fake.com")
        self.assert_equal(repo_name, "alphamatic/amp")

    def test_parse_github_repo_name4(self) -> None:
        repo_name = "https://github.fake.com/alphamatic/amp"
        host_name, repo_name = hgit._parse_github_repo_name(repo_name)
        self.assert_equal(host_name, "github.fake.com")
        self.assert_equal(repo_name, "alphamatic/amp")

    def test_get_repo_full_name_from_dirname1(self) -> None:
        func_call = "hgit.get_repo_full_name_from_dirname(dir_name='.', include_host_name=False)"
        _execute_func_call(func_call)

    def test_get_repo_full_name_from_dirname2(self) -> None:
        func_call = "hgit.get_repo_full_name_from_dirname(dir_name='.', include_host_name=True)"
        _execute_func_call(func_call)

    def test_get_repo_full_name_from_client1(self) -> None:
        func_call = "hgit.get_repo_full_name_from_client(super_module=True)"
        _execute_func_call(func_call)

    def test_get_repo_full_name_from_client2(self) -> None:
        func_call = "hgit.get_repo_full_name_from_client(super_module=False)"
        _execute_func_call(func_call)

    def test_get_repo_name1(self) -> None:
        short_name = "amp"
        mode = "short_name"
        act = hgit.get_repo_name(short_name, mode)
        exp = "alphamatic/amp"
        self.assert_equal(act, exp)

    def test_get_repo_name2(self) -> None:
        full_name = "alphamatic/amp"
        mode = "full_name"
        act = hgit.get_repo_name(full_name, mode)
        exp = "amp"
        self.assert_equal(act, exp)

    def test_get_repo_name4(self) -> None:
        full_name = "kaizen-ai/dev_tools"
        mode = "full_name"
        act = hgit.get_repo_name(full_name, mode)
        exp = "dev_tools"
        self.assert_equal(act, exp)

    # Outside CK infra, the following call hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    def test_get_all_repo_names1(self) -> None:
        if not hgit.is_in_amp_as_supermodule():
            _LOG.warning(
                "Skipping this test, since it can run only in amp as super-module"
            )
            return
        mode = "short_name"
        act = hgit.get_all_repo_names(mode)
        # Difference between `cmamp` and `kaizenflow`.
        exp = ["amp", "dev_tools", "kaizen"]
        self.assert_equal(str(act), str(exp))

    # Outside CK infra, the following call hangs, so we skip it.
    @pytest.mark.requires_ck_infra
    def test_get_all_repo_names2(self) -> None:
        if not hgit.is_in_amp_as_supermodule():
            _LOG.warning(
                "Skipping this test, since it can run only in amp as super-module"
            )
            return
        mode = "full_name"
        act = hgit.get_all_repo_names(mode)
        # Difference between `cmamp` and `kaizenflow`.
        exp = ["alphamatic/amp", "kaizen-ai/dev_tools", "kaizen-ai/kaizenflow"]
        self.assert_equal(str(act), str(exp))

    def test_get_repo_name_rountrip1(self) -> None:
        """
        Test round-trip transformation for get_repo_name().
        """
        # Get the short name for all the repos.
        mode = "short_name"
        all_repo_short_names = hgit.get_all_repo_names(mode)
        # Round trip.
        for repo_short_name in all_repo_short_names:
            repo_full_name = hgit.get_repo_name(repo_short_name, "short_name")
            repo_short_name_tmp = hgit.get_repo_name(repo_full_name, "full_name")
            self.assert_equal(repo_short_name, repo_short_name_tmp)

    def test_get_task_prefix_from_repo_short_name1(self) -> None:
        short_name = "dev_tools"
        act = hgit.get_task_prefix_from_repo_short_name(short_name)
        exp = "DevToolsTask"
        self.assert_equal(act, exp)


# Outside CK infra, the following class hangs, so we skip it.
@pytest.mark.requires_ck_infra
class Test_git_path1(hunitest.TestCase):
    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Run only in amp as super-module",
    )
    def test_get_path_from_git_root1(self) -> None:
        file_name = "/app/helpers/test/test_git.py"
        act = hgit.get_path_from_git_root(file_name, super_module=True)
        _LOG.debug("get_path_from_git_root()=%s", act)
        # Check.
        exp = "helpers/test/test_git.py"
        self.assert_equal(act, exp)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Run only in amp as sub-module"
    )
    def test_get_path_from_git_root2(self) -> None:
        file_name = "/app/amp/helpers/test/test_git.py"
        act = hgit.get_path_from_git_root(file_name, super_module=True)
        _LOG.debug("get_path_from_git_root()=%s", act)
        # Check.
        exp = "amp/helpers/test/test_git.py"
        self.assert_equal(act, exp)

    def test_get_path_from_git_root3(self) -> None:
        file_name = "/app/amp/helpers/test/test_git.py"
        git_root = "/app"
        act = hgit.get_path_from_git_root(
            file_name, super_module=False, git_root=git_root
        )
        # Check.
        exp = "amp/helpers/test/test_git.py"
        self.assert_equal(act, exp)

    def test_get_path_from_git_root4(self) -> None:
        file_name = "/app/amp/helpers/test/test_git.py"
        git_root = "/app/amp"
        act = hgit.get_path_from_git_root(
            file_name, super_module=False, git_root=git_root
        )
        # Check.
        exp = "helpers/test/test_git.py"
        self.assert_equal(act, exp)

    def test_get_path_from_git_root5(self) -> None:
        file_name = "helpers/test/test_git.py"
        git_root = "/app/amp"
        with self.assertRaises(ValueError):
            hgit.get_path_from_git_root(
                file_name, super_module=False, git_root=git_root
            )


# Outside CK infra, the following class hangs, so we skip it.
@pytest.mark.requires_ck_infra
@pytest.mark.slow(reason="Around 7s")
@pytest.mark.skipif(
    not hgit.is_in_amp_as_supermodule(),
    reason="Run only in amp as super-module",
)
class Test_git_modified_files1(hunitest.TestCase):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield

    def set_up_test(self) -> None:
        """
        All these tests need a reference to Git master branch.
        """
        hgit.fetch_origin_master_if_needed()

    def test_get_modified_files1(self) -> None:
        func_call = "hgit.get_modified_files()"
        _execute_func_call(func_call)

    def test_get_previous_committed_files1(self) -> None:
        func_call = "hgit.get_previous_committed_files()"
        _execute_func_call(func_call)

    def test_get_modified_files_in_branch1(self) -> None:
        func_call = "hgit.get_modified_files_in_branch('master')"
        _execute_func_call(func_call)

    def test_get_summary_files_in_branch1(self) -> None:
        func_call = "hgit.get_summary_files_in_branch('master')"
        _execute_func_call(func_call)

    def test_git_log1(self) -> None:
        func_call = "hgit.git_log()"
        _execute_func_call(func_call)


# #############################################################################


# Outside CK infra, the following class hangs, so we skip it.
@pytest.mark.requires_ck_infra
class Test_find_docker_file1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test for a file `amp/helpers/test/test_git.py` that is not from Docker
        (i.e., it doesn't start with `/app`) and exists in the repo.
        """
        amp_dir = hgit.get_amp_abs_path()
        # Use this file since `find_docker_file()` needs to do a `find` in the repo
        # so we need to have a fixed file structure.
        file_name = "/app/amp/helpers/test/test_git.py"
        actual = hgit.find_docker_file(
            file_name,
            root_dir=amp_dir,
        )
        expected = ["helpers/test/test_git.py"]
        self.assertEqual(actual, expected)

    def test2(self) -> None:
        """
        Test for a file `/app/amp/helpers/test/test_git.py` that is from Docker
        (i.e., it starts with `/app`) and exists in the repo.
        """
        amp_dir = hgit.get_amp_abs_path()
        # Use this file since `find_docker_file()` needs to do a `find` in the repo
        # so we need to have a fixed file structure.
        file_name = "/app/amp/helpers/test/test_git.py"
        expected = ["helpers/test/test_git.py"]
        actual = hgit.find_docker_file(
            file_name,
            root_dir=amp_dir,
        )
        self.assertEqual(actual, expected)

    def test3(self) -> None:
        """
        Test for a file `/venv/lib/python3.8/site-packages/invoke/tasks.py`
        that is from Docker (e.g., it starts with `/app`), but doesn't exist in
        the repo.
        """
        file_name = "/venv/lib/python3.8/site-packages/invoke/tasks.py"
        actual = hgit.find_docker_file(file_name)
        expected: List[str] = []
        self.assertEqual(actual, expected)

    def test4(self) -> None:
        """
        Test for a file `./core/dataflow/utils.py` that is from Docker (i.e.,
        it starts with `/app`), but has multiple copies in the repo.
        """
        amp_dir = hgit.get_amp_abs_path()
        file_name = "/app/amp/core/dataflow/utils.py"
        dir_depth = 1
        candidate_files = [
            "core/dataflow/utils.py",
            "core/foo/utils.py",
            "core/bar/utils.py",
        ]
        candidate_files = [os.path.join(amp_dir, f) for f in candidate_files]
        actual = hgit.find_docker_file(
            file_name,
            root_dir=amp_dir,
            dir_depth=dir_depth,
            candidate_files=candidate_files,
        )
        # Only one candidate file matches basename and one dirname.
        expected = ["core/dataflow/utils.py"]
        self.assertEqual(actual, expected)

    def test5(self) -> None:
        amp_dir = hgit.get_amp_abs_path()
        file_name = "/app/amp/core/dataflow/utils.py"
        dir_depth = -1
        candidate_files = [
            "core/dataflow/utils.py",
            "bar/dataflow/utils.py",
            "core/foo/utils.py",
        ]
        candidate_files = [os.path.join(amp_dir, f) for f in candidate_files]
        actual = hgit.find_docker_file(
            file_name,
            root_dir=amp_dir,
            dir_depth=dir_depth,
            candidate_files=candidate_files,
        )
        # Only one file matches `utils.py` using all the 3 dir levels.
        expected = ["core/dataflow/utils.py"]
        self.assertEqual(actual, expected)
