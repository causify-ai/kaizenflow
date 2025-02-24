import os

import helpers.hio as hio
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import helpers.hunit_test_utils as hunteuti


class TestUnitTestRenamer(hunitest.TestCase):
    """
    Test class renaming functionality.
    """

    @staticmethod
    def helper() -> str:
        """
        Create file content.
        """
        content = """
class TestCases(hunitest.TestCase):
    def test_assert_equal1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test_check_string1(self) -> None:
        actual = "hello world"
        self.check_string(actual)
        """
        return content

    def test_rename_class1(self) -> None:
        """
        Test renaming of existing class.
        """
        content = self.helper()
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer("TestCases", "TestNewCase", root_dir)
        actual, _ = renamer._rename_class(content)
        expected = """
class TestNewCase(hunitest.TestCase):
    def test_assert_equal1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test_check_string1(self) -> None:
        actual = "hello world"
        self.check_string(actual)
        """
        self.assert_equal(actual, expected)

    def test_rename_class2(self) -> None:
        """
        Test renaming of non existing class.
        """
        content = self.helper()
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer("TestCase", "TestNewCase", root_dir)
        actual, _ = renamer._rename_class(content)
        # Check if the content of the file was not changed.
        self.assert_equal(actual, content)


class TestPytestRenameMethod(hunitest.TestCase):
    """
    Test method renaming functionality.
    """

    @staticmethod
    def helper() -> str:
        """
        Create file content.
        """
        content = """
class TestCases(hunitest.TestCase):
    def test1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test10(self) -> None:
        actual = "hello world"
        self.check_string(actual)


class TestOtherCases(hunitest.TestCase):
    def test1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test10(self) -> None:
        actual = "hello world"
        self.check_string(actual)
        """
        return content

    def test_rename_method1(self) -> None:
        """
        Test renaming of existing method.
        """
        content = self.helper()
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer(
            "TestCases.test1", "TestCases.test_new", root_dir
        )
        actual, _ = renamer._rename_method(content)
        expected = """
class TestCases(hunitest.TestCase):
    def test_new(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test10(self) -> None:
        actual = "hello world"
        self.check_string(actual)


class TestOtherCases(hunitest.TestCase):
    def test1(self) -> None:
        actual = "hello world"
        expected = actual
        self.assert_equal(actual, expected)

    def test10(self) -> None:
        actual = "hello world"
        self.check_string(actual)
        """
        self.assert_equal(actual, expected)

    def test_rename_method2(self) -> None:
        """
        Test renaming of non existing method.
        """
        content = self.helper()
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer(
            "TestOtherCases.test5", "TestOtherCases.test6", root_dir
        )
        actual, _ = renamer._rename_method(content)
        # Check if the content of the file was not changed.
        self.assert_equal(actual, content)

    def test_rename_method3(self) -> None:
        """
        Test renaming of invalid method names.
        """
        self.helper()
        root_dir = os.getcwd()
        with self.assertRaises(AssertionError):
            hunteuti.UnitTestRenamer(
                "TestCases.test10", "TestOtherCases.test6", root_dir
            )


class TestPytestRenameOutcomes(hunitest.TestCase):
    """
    Test golden outcomes directory renaming.
    """

    @staticmethod
    def helper(toy_test: str) -> None:
        """
        Create the temporary outcome to rename.

        :param toy_test: the name of the toy directory
        """
        outcomes_paths = [
            "TestCase.test_check_string1",
            "TestCase.test_rename",
            "TestCase.test_rename3",
            "TestCases.test_rename2",
            "TestRename.test_rename1",
        ]
        for path in outcomes_paths:
            outcomes_dir = os.path.join(toy_test, "test/outcomes", path)
            hio.create_dir(outcomes_dir, incremental=False)
            hio.to_file(f"{outcomes_dir}/test.txt", "Test files.")
        cmd = f"git add {toy_test}/"
        hsystem.system(cmd, abort_on_error=False, suppress_output=False)

    def test_rename_class_outcomes(self) -> None:
        """
        Rename outcome directory.
        """
        toy_test = "toyCmTask1279." + self._testMethodName
        # Create outcomes directory.
        test_path = os.path.join(toy_test, "test")
        # Create the toy outcomes.
        self.helper(toy_test)
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer(
            "TestCase", "TestRenamedCase", root_dir
        )
        renamer.rename_outcomes(
            test_path,
        )
        # Check if the dirs were renamed.
        outcomes_path = os.path.join(test_path, "outcomes")
        outcomes_dirs = os.listdir(outcomes_path)
        actual = sorted(
            [
                ent
                for ent in outcomes_dirs
                if os.path.isdir(os.path.join(outcomes_path, ent))
            ]
        )
        expected = [
            "TestCases.test_rename2",
            "TestRename.test_rename1",
            "TestRenamedCase.test_check_string1",
            "TestRenamedCase.test_rename",
            "TestRenamedCase.test_rename3",
        ]
        self.assertEqual(actual, expected)
        self._clean_up(toy_test)

    def test_rename_method_outcomes(self) -> None:
        """
        Rename outcome directory.
        """
        toy_test = "toyCmTask1279." + self._testMethodName
        # Create outcomes directory.
        test_path = os.path.join(toy_test, "test")
        # Create the toy outcomes.
        self.helper(toy_test)
        root_dir = os.getcwd()
        renamer = hunteuti.UnitTestRenamer(
            "TestCase.test_rename",
            "TestCase.test_method_renamed",
            root_dir,
        )
        renamer.rename_outcomes(
            test_path,
        )
        # Check if the dirs were renamed.
        outcomes_path = os.path.join(test_path, "outcomes")
        outcomes_dirs = os.listdir(outcomes_path)
        actual = sorted(
            [
                ent
                for ent in outcomes_dirs
                if os.path.isdir(os.path.join(outcomes_path, ent))
            ]
        )
        expected = [
            "TestCase.test_check_string1",
            "TestCase.test_method_renamed",
            "TestCase.test_rename3",
            "TestCases.test_rename2",
            "TestRename.test_rename1",
        ]
        self.assertEqual(actual, expected)
        self._clean_up(toy_test)

    def _clean_up(self, toy_test: str) -> None:
        """
        Remove temporary test directory.

        :param toy_test: the name of the toy directory
        """
        cmd = f"git reset {toy_test}/ && rm -rf {toy_test}/"
        hsystem.system(cmd, abort_on_error=False, suppress_output=False)
