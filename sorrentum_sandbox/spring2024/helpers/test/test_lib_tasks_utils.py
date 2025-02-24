import logging
import os

import pytest

import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hunit_test as hunitest
import helpers.lib_tasks_utils as hlitauti

_LOG = logging.getLogger(__name__)


# pylint: disable=protected-access


class Test_get_files_to_process1(hunitest.TestCase):
    """
    We can't check the outcome so we just execute the code.
    """

    def test_modified1(self) -> None:
        """
        Retrieve files modified in this client.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    @pytest.mark.skipif(
        hgit.get_branch_name() != "master",
        reason="This test makes sense for a branch",
    )
    def test_branch1(self) -> None:
        """
        Retrieved files modified in this client.
        """
        # This test needs a reference to Git master branch.
        hgit.fetch_origin_master_if_needed()
        #
        modified = False
        branch = True
        last_commit = False
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    def test_last_commit1(self) -> None:
        """
        Retrieved files modified in the last commit.
        """
        modified = False
        branch = False
        last_commit = True
        all_ = False
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        _ = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )

    def test_files1(self) -> None:
        """
        Pass through files from user.
        """
        modified = False
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = True
        remove_dirs = True
        files = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        self.assertEqual(files, [__file__])

    def test_files2(self) -> None:
        """
        Pass through files from user.

        Use two types of paths we don't want to process:
          - non-existent python file
          - pattern "/*" that matches no files
        """
        modified = False
        branch = False
        last_commit = False
        all_ = False
        files_from_user = "testfile1.py testfiles1/*"
        mutually_exclusive = True
        remove_dirs = True
        files = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        self.assertEqual(files, [])

    def test_files3(self) -> None:
        """
        Pass through files from user.

        Use the sequence of paths separated by newlines.
        """
        modified = False
        branch = False
        last_commit = False
        all_ = False
        # Specify the number of toy files.
        n_toy_files = 4
        files_from_user = []
        # Get root directory.
        root_dir = hgit.get_client_root(super_module=False)
        # Generate toy files and store their paths.
        for file_num in range(n_toy_files):
            # Build the name of the test file.
            file_name = f"test_toy{str(file_num)}.tmp.py"
            # Build the path to the test file.
            test_path = os.path.join(root_dir, file_name)
            # Create the empty toy file.
            hio.to_file(test_path, "")
            files_from_user.append(test_path)
        mutually_exclusive = True
        remove_dirs = True
        # Join the names with `\n` separator.
        joined_files_from_user = "\n".join(files_from_user)
        files = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            joined_files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        # Remove the toy files.
        for path in files_from_user:
            hio.delete_file(path)
        self.assertEqual(files, files_from_user)

    def test_assert1(self) -> None:
        """
        Test that --modified and --branch together cause an assertion.
        """
        modified = True
        branch = True
        last_commit = False
        all_ = True
        files_from_user = ""
        mutually_exclusive = True
        remove_dirs = True
        with self.assertRaises(AssertionError) as cm:
            hlitauti._get_files_to_process(
                modified,
                branch,
                last_commit,
                all_,
                files_from_user,
                mutually_exclusive,
                remove_dirs,
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '3'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit, --all_files, and --files
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert2(self) -> None:
        """
        Test that --modified and --files together cause an assertion if
        `mutually_exclusive=True`.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = True
        remove_dirs = True
        with self.assertRaises(AssertionError) as cm:
            hlitauti._get_files_to_process(
                modified,
                branch,
                last_commit,
                all_,
                files_from_user,
                mutually_exclusive,
                remove_dirs,
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        '2'
        ==
        '1'
        Specify only one among --modified, --branch, --last-commit, --all_files, and --files
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert3(self) -> None:
        """
        Test that --modified and --files together don't cause an assertion if
        `mutually_exclusive=False`.
        """
        modified = True
        branch = False
        last_commit = False
        all_ = False
        files_from_user = __file__
        mutually_exclusive = False
        remove_dirs = True
        files = hlitauti._get_files_to_process(
            modified,
            branch,
            last_commit,
            all_,
            files_from_user,
            mutually_exclusive,
            remove_dirs,
        )
        self.assertEqual(files, [__file__])


# #############################################################################


class TestLibTasksRemoveSpaces1(hunitest.TestCase):
    def test1(self) -> None:
        txt = r"""
            IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp_test:dev \
                docker-compose \
                --file $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml \
                run \
                --rm \
                -l user=$USER_NAME \
                --entrypoint bash \
                user_space
            """
        act = hlitauti._to_single_line_cmd(txt)
        exp = (
            "IMAGE=*****.dkr.ecr.us-east-1.amazonaws.com/amp_test:dev"
            " docker-compose --file"
            " $GIT_ROOT/devops/compose/docker-compose_as_submodule.yml"
            " run --rm -l user=$USER_NAME --entrypoint bash user_space"
        )
        self.assert_equal(act, exp, fuzzy_match=False)
