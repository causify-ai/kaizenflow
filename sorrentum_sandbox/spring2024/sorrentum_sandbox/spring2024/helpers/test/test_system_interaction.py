import logging
import os
import re
import tempfile
from typing import List

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# #############################################################################


class Test_system1(hunitest.TestCase):
    def test1(self) -> None:
        hsystem.system("ls")

    def test2(self) -> None:
        hsystem.system("ls /dev/null", suppress_output=False)

    def test3(self) -> None:
        """
        Output to a file.
        """
        with tempfile.NamedTemporaryFile() as fp:
            temp_file_name = fp.name
            _LOG.debug("temp_file_name=%s", temp_file_name)
            hsystem.system("ls", output_file=temp_file_name)
            hdbg.dassert_path_exists(temp_file_name)

    def test4(self) -> None:
        """
        Tee to a file.
        """
        with tempfile.NamedTemporaryFile() as fp:
            temp_file_name = fp.name
            _LOG.debug("temp_file_name=%s", temp_file_name)
            hsystem.system("ls", output_file=temp_file_name, tee=True)
            hdbg.dassert_path_exists(temp_file_name)

    def test5(self) -> None:
        """
        Test dry_run.
        """
        temp_file_name = tempfile._get_default_tempdir()  # type: ignore
        candidate_name = tempfile._get_candidate_names()  # type: ignore
        temp_file_name += "/" + next(candidate_name)
        _LOG.debug("temp_file_name=%s", temp_file_name)
        hsystem.system("ls", output_file=temp_file_name, dry_run=True)
        hdbg.dassert_path_not_exists(temp_file_name)

    def test6(self) -> None:
        """
        Test abort_on_error=True.
        """
        hsystem.system("ls this_file_doesnt_exist", abort_on_error=False)

    def test7(self) -> None:
        """
        Test abort_on_error=False.
        """
        with self.assertRaises(RuntimeError) as cm:
            hsystem.system("ls this_file_doesnt_exist")
        act = str(cm.exception)
        # Different systems return different rc.
        # cmd='(ls this_file_doesnt_exist) 2>&1' failed with rc='2'
        act = re.sub(r"rc='(\d+)'", "rc=''", act)
        self.check_string(act)

    def test8(self) -> None:
        """
        Check that an assert error is raised when `tee` is passed without a log
        file.
        """
        with self.assertRaises(AssertionError) as cm:
            _ = hsystem.system("ls this_should_fail", tee=True)
        actual = str(cm.exception)
        expected = r"""
        ################################################################################
        * Failed assertion *
        'True' implies 'False'
        ################################################################################
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test9(self) -> None:
        """
        Check that the failing command fails and logs are stored in the log
        file.

        - `allow_errors = False`
        - `tee = True`
        - Log file path is passed
        """
        log_dir = self.get_scratch_space()
        log_file_path = os.path.join(log_dir, "tee_log")
        with self.assertRaises(RuntimeError) as cm:
            _ = hsystem.system(
                "ls this_should_fail", tee=True, output_file=log_file_path
            )
        actual = str(cm.exception)
        actual = hunitest.purify_txt_from_client(actual)
        expected = r"""
        cmd='(ls this_should_fail) 2>&1 | tee -a $GIT_ROOT/helpers/test/outcomes/Test_system1.test9/tmp.scratch/tee_log; exit ${PIPESTATUS[0]}' failed with rc='2'
        truncated output=
        ls: cannot access 'this_should_fail': No such file or directory
        """
        self.assert_equal(actual, expected, fuzzy_match=True)
        # Check log output.
        actual = hio.from_file(log_file_path)
        expected = (
            r"ls: cannot access 'this_should_fail': No such file or directory\n"
        )
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test10(self) -> None:
        """
        Check that the failing command passes and logs are stored in the log
        file.

        - `allow_errors = True`
        - `tee = True`
        - Log file path is passed
        """
        log_dir = self.get_scratch_space()
        log_file_path = os.path.join(log_dir, "tee_log")
        rc = hsystem.system(
            "ls this_should_fail",
            tee=True,
            abort_on_error=False,
            output_file=log_file_path,
        )
        self.assertNotEqual(rc, 0)
        # Check log output.
        actual = hio.from_file(log_file_path)
        expected = (
            r"ls: cannot access 'this_should_fail': No such file or directory\n"
        )
        self.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################


class Test_system2(hunitest.TestCase):
    def test_get_user_name(self) -> None:
        act = hsystem.get_user_name()
        _LOG.debug("act=%s", act)
        #
        exp = hsystem.system_to_string("whoami")[1]
        _LOG.debug("exp=%s", exp)
        self.assertEqual(act, exp)
        #
        exp = hsystem.system_to_one_line("whoami")[1]
        _LOG.debug("exp=%s", exp)
        self.assertEqual(act, exp)

    def test_get_server_name(self) -> None:
        act = hsystem.get_server_name()
        _LOG.debug("act=%s", act)
        #
        exp = hsystem.system_to_string("uname -n")[1]
        _LOG.debug("exp=%s", exp)
        self.assertEqual(act, exp)

    def test_get_os_name(self) -> None:
        act = hsystem.get_os_name()
        _LOG.debug("act=%s", act)
        #
        exp = hsystem.system_to_string("uname -s")[1]
        _LOG.debug("exp=%s", exp)
        self.assertEqual(act, exp)


# #############################################################################


class Test_compute_file_signature1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Compute the signature of a file using 1 enclosing dir.
        """
        file_name = (
            "/app/amp/core/test/TestCheckSameConfigs."
            + "test_check_same_configs_error/output/test.txt"
        )
        dir_depth = 1
        act = hsystem._compute_file_signature(file_name, dir_depth=dir_depth)
        exp = ["output", "test.txt"]
        self.assert_equal(str(act), str(exp))

    def test2(self) -> None:
        """
        Compute the signature of a file using 2 enclosing dirs.
        """
        file_name = (
            "/app/amp/core/test/TestCheckSameConfigs."
            + "test_check_same_configs_error/output/test.txt"
        )
        dir_depth = 2
        act = hsystem._compute_file_signature(file_name, dir_depth=dir_depth)
        exp = [
            "TestCheckSameConfigs.test_check_same_configs_error",
            "output",
            "test.txt",
        ]
        self.assert_equal(str(act), str(exp))

    def test3(self) -> None:
        """
        Compute the signature of a file using 4 enclosing dirs.
        """
        file_name = "/app/amp/core/test/TestApplyAdfTest.test1/output/test.txt"
        dir_depth = 4
        act = hsystem._compute_file_signature(file_name, dir_depth=dir_depth)
        exp = [
            "core",
            "test",
            "TestApplyAdfTest.test1",
            "output",
            "test.txt",
        ]
        self.assert_equal(str(act), str(exp))


# #############################################################################


class Test_find_file_with_dir1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Check whether we can find this file using one enclosing dir.
        """
        # Use this file.
        file_name = "helpers/test/test_system_interaction.py"
        dir_depth = 1
        act = hsystem.find_file_with_dir(file_name, dir_depth=dir_depth)
        exp = r"""['helpers/test/test_system_interaction.py']"""
        self.assert_equal(str(act), str(exp), purify_text=True)

    def test2(self) -> None:
        """
        Check whether we can find a test golden output using different number
        of enclosing dirs.

        With only 1 enclosing dir, we can't find it.
        """
        # Use only one dir which is not enough to identify the file.
        # E.g., .../test/TestSqlWriterBackend1.test_insert_tick_data1/output/test.txt
        dir_depth = 1
        mode = "return_all_results"
        act = self._helper(dir_depth, mode)
        # For sure there are more than 100 tests.
        self.assertGreater(len(act), 100)

    def test3(self) -> None:
        """
        Like `test2`, but using 2 levels for sure we are going to identify the
        file.
        """
        dir_depth = 2
        mode = "return_all_results"
        act = self._helper(dir_depth, mode)
        _LOG.debug("Found %d matching files", len(act))
        # There should be a single match.
        exp = r"""['helpers/test/outcomes/Test_find_file_with_dir1.test3/output/test.txt']"""
        self.assert_equal(str(act), str(exp), purify_text=True)
        self.assertEqual(len(act), 1)

    def test4(self) -> None:
        """
        Like `test2`, but using 2 levels for sure we are going to identify the
        file and asserting in case we don't find a single result.
        """
        dir_depth = 2
        mode = "assert_unless_one_result"
        act = self._helper(dir_depth, mode)
        _LOG.debug("Found %d matching files", len(act))
        # There should be a single match.
        exp = r"""['helpers/test/outcomes/Test_find_file_with_dir1.test4/output/test.txt']"""
        self.assert_equal(str(act), str(exp), purify_text=True)
        self.assertEqual(len(act), 1)

    def test5(self) -> None:
        """
        Like `test2`, using more level than 2, again, we should have a single
        result.
        """
        dir_depth = 3
        mode = "assert_unless_one_result"
        act = self._helper(dir_depth, mode)
        _LOG.debug("Found %d matching files", len(act))
        exp = r"""['helpers/test/outcomes/Test_find_file_with_dir1.test5/output/test.txt']"""
        self.assert_equal(str(act), str(exp), purify_text=True)
        self.assertEqual(len(act), 1)

    def _helper(self, dir_depth: int, mode: str) -> List[str]:
        # Create a fake golden outcome to be used in this test.
        act = "hello world"
        self.check_string(act)
        # E.g., helpers/test/test_system_interaction.py::Test_find_file_with_dir1::test2/test.txt
        file_name = os.path.join(self.get_output_dir(), "test.txt")
        _LOG.debug("file_name=%s", file_name)
        act: List[str] = hsystem.find_file_with_dir(
            file_name, dir_depth=dir_depth, mode=mode
        )
        _LOG.debug("Found %d matching files", len(act))
        return act


# #############################################################################


class Test_Linux_commands1(hunitest.TestCase):
    def test_du1(self) -> None:
        hsystem.du(".")


# #############################################################################


class Test_has_timestamp1(hunitest.TestCase):
    def test_has_not_timestamp1(self) -> None:
        """
        No timestamp.
        """
        file_name = "patch.amp.8c5a2da9.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = False
        self.assertEqual(act, exp)

    def test_has_timestamp1(self) -> None:
        """
        Valid timestamp.
        """
        file_name = "patch.amp.8c5a2da9.20210725_225857.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = True
        self.assertEqual(act, exp)

    def test_has_timestamp2(self) -> None:
        """
        Valid timestamp.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725-22_58_57.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = True
        self.assertEqual(act, exp)

    def test_has_timestamp3(self) -> None:
        """
        Valid timestamp.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725225857.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = True
        self.assertEqual(act, exp)

    def test_has_timestamp4(self) -> None:
        """
        Valid timestamp.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725_22_58_57.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = True
        self.assertEqual(act, exp)

    def test_has_timestamp5(self) -> None:
        """
        Valid timestamp.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725225857.tgz"
        act = hsystem.has_timestamp(file_name)
        exp = True
        self.assertEqual(act, exp)


class Test_append_timestamp_tag1(hunitest.TestCase):
    def test_no_timestamp1(self) -> None:
        """
        Invalid timestamp, with no tag.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.tgz"
        tag = ""
        act = hsystem.append_timestamp_tag(file_name, tag)
        # /foo/bar/patch.amp.8c5a2da9.20210726-15_11_25.tgz
        exp = r"/foo/bar/patch.amp.8c5a2da9.\S+.tgz"
        self.assertRegex(act, exp)

    def test_no_timestamp2(self) -> None:
        """
        Invalid timestamp, with no tag.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.tgz"
        tag = "hello"
        act = hsystem.append_timestamp_tag(file_name, tag)
        # /foo/bar/patch.amp.8c5a2da9.20210726-15_11_25.hello.tgz
        exp = r"/foo/bar/patch.amp.8c5a2da9.\S+.hello.tgz"
        self.assertRegex(act, exp)

    def test1(self) -> None:
        """
        Valid timestamp, with no tag.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725_225857.tgz"
        tag = ""
        act = hsystem.append_timestamp_tag(file_name, tag)
        # /foo/bar/patch.amp.8c5a2da9.20210725_225857.20210726-15_11_25.tgz
        exp = "/foo/bar/patch.amp.8c5a2da9.20210725_225857.tgz"
        self.assertEqual(act, exp)

    def test2(self) -> None:
        """
        Valid timestamp, with a tag.
        """
        file_name = "/foo/bar/patch.amp.8c5a2da9.20210725_225857.tgz"
        tag = "hello"
        act = hsystem.append_timestamp_tag(file_name, tag)
        exp = "/foo/bar/patch.amp.8c5a2da9.20210725_225857.hello.tgz"
        self.assertEqual(act, exp)
