import logging
import os

import pytest

import helpers.hgit as hgit
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import helpers.lib_tasks_find as hlitafin
import helpers.test.test_lib_tasks as httestlib

_LOG = logging.getLogger(__name__)


class Test_find_short_import1(hunitest.TestCase):
    def test1(self) -> None:
        iterator = [
            ("file1.py", 10, "import dataflow.core.dag_runner as dtfcodarun"),
            ("file1.py", 11, "import helpers.hpandas as hpandas"),
        ]
        results = hlitafin._find_short_import(iterator, "dtfcodarun")
        act = "\n".join(map(str, results))
        # pylint: disable=line-too-long
        exp = r"""('file1.py', 10, 'import dataflow.core.dag_runner as dtfcodarun', 'dtfcodarun', 'import dataflow.core.dag_runner as dtfcodarun')"""
        self.assert_equal(act, exp, fuzzy_match=True)


class Test_find_func_class_uses1(hunitest.TestCase):
    def test1(self) -> None:
        iterator = [
            (
                "file1.py",
                10,
                "dag_runner = dtfsys.RealTimeDagRunner(**dag_runner_kwargs)",
            ),
            (
                "file1.py",
                11,
                "This test is similar to `TestRealTimeDagRunner1`. It uses:",
            ),
            ("file1.py", 12, "dag_builder: dtfcodabui.DagRunner,"),
            ("file1.py", 13, ":param dag_builder: `DagRunner` instance"),
        ]
        results = hlitafin._find_func_class_uses(iterator, "DagRunner")
        act = "\n".join(map(str, results))
        exp = r"""
        ('file1.py', 10, 'dag_runner = dtfsys.RealTimeDagRunner(**dag_runner_kwargs)', 'dtfsys', 'RealTimeDagRunner')
        ('file1.py', 12, 'dag_builder: dtfcodabui.DagRunner,', 'dtfcodabui', 'DagRunner')"""
        self.assert_equal(act, exp, fuzzy_match=True)


class TestLibTasksRunTests1(hunitest.TestCase):
    """
    Test `_find_test_files()`, `_find_test_decorator()`.
    """

    def test_find_test_files1(self) -> None:
        """
        Find all the test files in the current dir.
        """
        files = hlitafin._find_test_files()
        # For sure there are more than 1 test files: at least this one.
        self.assertGreater(len(files), 1)

    def test_find_test_files2(self) -> None:
        """
        Find all the test files from the top of the super module root.
        """
        git_root = hgit.get_client_root(super_module=True)
        files = hlitafin._find_test_files(git_root)
        # For sure there are more than 1 test files: at least this one.
        self.assertGreater(len(files), 1)

    def test_find_test_class1(self) -> None:
        """
        Find the current test class.
        """
        git_root = hgit.get_client_root(super_module=True)
        file_names = hlitafin._find_test_files(git_root)
        #
        file_names = hlitafin._find_test_class(
            "TestLibTasksRunTests1", file_names
        )
        act = hunitest.purify_file_names(file_names)
        exp = ["helpers/test/test_lib_tasks_find.py::TestLibTasksRunTests1"]
        self.assert_equal(str(act), str(exp))

    def test_find_test_class2(self) -> None:
        """
        Find the current test class.
        """
        file_names = [__file__]
        #
        file_names = hlitafin._find_test_class(
            "TestLibTasksRunTests1", file_names
        )
        act = hunitest.purify_file_names(file_names)
        exp = ["helpers/test/test_lib_tasks_find.py::TestLibTasksRunTests1"]
        self.assert_equal(str(act), str(exp))

    def test_find_test_class3(self) -> None:
        """
        Create synthetic code and look for a class.
        """
        scratch_space = self.get_scratch_space()
        dir_name = os.path.join(scratch_space, "test")
        file_dict = {
            "test_this.py": hprint.dedent(
                """
                    foo

                    class TestHelloWorld(hunitest.TestCase):
                        bar
                    """
            ),
            "test_that.py": hprint.dedent(
                """
                    foo
                    baz

                    class TestHello_World(hunitest.):
                        bar
                    """
            ),
        }
        incremental = True
        hunitest.create_test_dir(dir_name, incremental, file_dict)
        #
        file_names = hlitafin._find_test_files(dir_name)
        act_file_names = [os.path.relpath(d, scratch_space) for d in file_names]
        exp_file_names = ["test/test_that.py", "test/test_this.py"]
        self.assert_equal(str(act_file_names), str(exp_file_names))
        #
        act = hlitafin._find_test_class("TestHelloWorld", file_names)
        act = hunitest.purify_file_names(act)
        exp = [
            "helpers/test/outcomes/TestLibTasksRunTests1.test_find_test_class3/tmp.scratch/"
            "test/test_this.py::TestHelloWorld"
        ]
        self.assert_equal(str(act), str(exp))

    def test_find_test_decorator1(self) -> None:
        """
        Find test functions in the "no_container" in synthetic code.
        """
        scratch_space = self.get_scratch_space()
        dir_name = os.path.join(scratch_space, "test")
        file_dict = {
            "test_this.py": hprint.dedent(
                """
                    foo

                    class TestHelloWorld(hunitest.TestCase):
                        bar
                    """
            ),
            "test_that.py": hprint.dedent(
                """
                    foo
                    baz

                    @pytest.mark.no_container
                    class TestHello_World(hunitest.):
                        bar
                    """
            ),
        }
        incremental = True
        hunitest.create_test_dir(dir_name, incremental, file_dict)
        #
        file_names = hlitafin._find_test_files(dir_name)
        act = hlitafin._find_test_decorator("no_container", file_names)
        act = hunitest.purify_file_names(act)
        exp = [
            "helpers/test/outcomes/TestLibTasksRunTests1.test_find_test_decorator1/"
            "tmp.scratch/test/test_that.py"
        ]
        self.assert_equal(str(act), str(exp))

    @pytest.mark.skipif(not hgit.is_amp(), reason="Only run in amp")
    def test_find_test_decorator2(self) -> None:
        """
        Find test functions in the "no_container" test list.
        """
        file_names = ["helpers/hunit_test.py"]
        act = hlitafin._find_test_decorator("qa", file_names)
        act = hunitest.purify_file_names(act)
        exp = file_names
        self.assert_equal(str(act), str(exp))


class Test_find_check_string_output1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test `find_check_string_output()` by searching the `check_string` of
        this test.
        """
        # Force to generate a `check_string` file so we can search for it.
        act = "A fake check_string output to use for test1"
        self.check_string(act)
        # Check.
        exp = '''
        act =
        exp = r"""
        A fake check_string output to use for test1

        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=False)
        '''
        self._helper(exp, fuzzy_match=False)

    def test2(self) -> None:
        """
        Like test1 but using `fuzzy_match=True`.
        """
        # Force to generate a `check_string` file so we can search for it.
        act = "A fake check_string output to use for test2"
        self.check_string(act)
        # Check.
        exp = '''
        act =
        exp = r"""
A fake check_string output to use for test2

        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)
        '''
        self._helper(exp, fuzzy_match=True)

    def _helper(self, exp: str, fuzzy_match: bool) -> None:
        # Look for the `check_string()` corresponding to this test.
        ctx = httestlib._build_mock_context_returning_ok()
        class_name = self.__class__.__name__
        method_name = self._testMethodName
        as_python = True
        # We don't want to copy but just print.
        pbcopy = False
        act = hlitafin.find_check_string_output(
            ctx, class_name, method_name, as_python, fuzzy_match, pbcopy
        )
        # Check that it matches exactly.
        self.assert_equal(act, exp, fuzzy_match=False)
