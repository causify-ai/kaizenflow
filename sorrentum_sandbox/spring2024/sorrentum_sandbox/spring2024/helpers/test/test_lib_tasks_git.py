import logging

import pytest

import helpers.hgit as hgit
import helpers.hunit_test as hunitest
import helpers.lib_tasks_git as hlitagit
import helpers.test.test_lib_tasks as httestlib

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


@pytest.mark.slow(reason="Around 7s")
@pytest.mark.skipif(
    not hgit.is_in_amp_as_supermodule(),
    reason="Run only in amp as super-module",
)
class TestLibTasksGitCreatePatch1(hunitest.TestCase):
    """
    Test `git_patch_create()`.
    """

    @staticmethod
    def helper(
        modified: bool, branch: bool, last_commit: bool, files: str
    ) -> None:
        ctx = httestlib._build_mock_context_returning_ok()
        #
        mode = "tar"
        hlitagit.git_patch_create(ctx, mode, modified, branch, last_commit, files)
        #
        mode = "diff"
        hlitagit.git_patch_create(ctx, mode, modified, branch, last_commit, files)

    def test_tar_modified1(self) -> None:
        """
        Exercise the code for:

        > invoke git_patch_create ... --branch
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = True
        branch = False
        last_commit = False
        files = ""
        self.helper(modified, branch, last_commit, files)

    def test_tar_branch1(self) -> None:
        """
        Exercise the code for:

        > invoke git_patch_create ... --modified
        """
        modified = False
        branch = True
        last_commit = False
        files = ""
        self.helper(modified, branch, last_commit, files)

    def test_tar_last_commit1(self) -> None:
        """
        Exercise the code for:

        > invoke git_patch_create ... --last-commit
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = False
        branch = False
        last_commit = True
        files = ""
        self.helper(modified, branch, last_commit, files)

    def test_tar_files1(self) -> None:
        """
        Exercise the code for:

        > invoke git_patch_create \
                --mode="tar" \
                --files "this file" \
                --modified
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        ctx = httestlib._build_mock_context_returning_ok()
        mode = "tar"
        modified = True
        branch = False
        last_commit = False
        files = __file__
        hlitagit.git_patch_create(ctx, mode, modified, branch, last_commit, files)

    def test_diff_files_abort1(self) -> None:
        """
        Exercise the code for:

        > invoke git_patch_create --mode="diff" --files "this file"

        In this case one needs to specify at least one --branch, --modified,
        --last-commit option.
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        ctx = httestlib._build_mock_context_returning_ok()
        mode = "diff"
        modified = False
        branch = False
        last_commit = False
        files = __file__
        with self.assertRaises(AssertionError) as cm:
            hlitagit.git_patch_create(
                ctx, mode, modified, branch, last_commit, files
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '0'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit
        """
        self.assert_equal(act, exp, fuzzy_match=True)
