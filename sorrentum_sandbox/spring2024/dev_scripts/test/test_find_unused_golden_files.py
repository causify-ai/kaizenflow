import logging
from typing import Dict, List

import dev_scripts.find_unused_golden_files as dsfugofi
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_parse_test_code(hunitest.TestCase):
    def test1(self) -> None:
        code = """
        class TestClass(hunitest.TestCase):
            def test1(self) -> None:
                actual = lib.run()
                self.check_string(actual)

            def test2(self) -> None:
                actual = lib.run()
                expected = "abc"
                self.assertEqual(actual, expected)
        """
        test_py_file = "dir/test/test_lib.py"
        actual_test_methods, actual_class_to_test_file = dsfugofi.parse_test_code(
            code, test_py_file
        )
        expected_test_methods = ["dir/test/outcomes/TestClass.test1"]
        expected_class_to_test_file = {
            "dir/test/outcomes/TestClass": "dir/test/test_lib.py"
        }
        self.assertEqual(actual_test_methods, expected_test_methods)
        self.assertEqual(actual_class_to_test_file, expected_class_to_test_file)

    def test2(self) -> None:
        code = """
        class TestClass(hunitest.TestCase):
            def helper(self, actual) -> None:
                self.check_string(actual)

            def test1(self) -> None:
                actual = lib.run()
                self.helper(actual)
        """
        test_py_file = "dir/test/test_lib.py"
        actual_test_methods, actual_class_to_test_file = dsfugofi.parse_test_code(
            code, test_py_file
        )
        expected_test_methods = ["dir/test/outcomes/TestClass.test1"]
        expected_class_to_test_file = {
            "dir/test/outcomes/TestClass": "dir/test/test_lib.py"
        }
        self.assertEqual(actual_test_methods, expected_test_methods)
        self.assertEqual(actual_class_to_test_file, expected_class_to_test_file)

    def test3(self) -> None:
        code = """
        class HelperClass(hunitest.TestCase):
            def helper(self, actual) -> None:
                self.check_string(actual)

        class TestClass(HelperClass):
            def test1(self) -> None:
                actual = lib.run()
                self.helper(actual)
        """
        test_py_file = "dir/test/test_lib.py"
        actual_test_methods, actual_class_to_test_file = dsfugofi.parse_test_code(
            code, test_py_file
        )
        expected_test_methods: List[str] = []
        expected_class_to_test_file: Dict[str, str] = {
            "dir/test/outcomes/TestClass": "dir/test/test_lib.py"
        }
        self.assertEqual(actual_test_methods, expected_test_methods)
        self.assertEqual(actual_class_to_test_file, expected_class_to_test_file)
