import logging
from typing import List, Tuple

import dev_scripts.replace_text as dscretex
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_files_to_rename(hunitest.TestCase):
    def helper(
        self,
        file_names: List[str],
        old_regex: str,
        new_regex: str,
        replace_in: str,
        filter_by: str,
        filter_on: str,
        expected_file_names: List[str],
        expected_file_map: List[Tuple[str, str]],
    ) -> None:
        """
        Run `_get_files_to_rename()` on the file names and check the outcome.

        See param descriptions in `dscretex._get_files_to_rename()`.

        :param expected_file_names: file names expected to remain after filtering
        :param expected_file_map: the expected mapping for renaming the filtered files
        """
        # Run.
        actual_file_names, actual_file_map = dscretex._get_files_to_rename(
            file_names, old_regex, new_regex, replace_in, filter_by, filter_on
        )
        actual_file_names = sorted(actual_file_names)
        actual_file_map = sorted(actual_file_map.items())
        # Check the outcome.
        self.assertEqual(actual_file_names, expected_file_names)
        self.assertEqual(actual_file_map, expected_file_map)

    def test1(self) -> None:
        file_names = [
            "dir/subdir/test1.py",
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        old_regex = r"test\d"
        new_regex = r"testNUM"
        replace_in = "basename"
        filter_by = r"/Test\..+"
        filter_on = "dirname"
        expected_file_names = [
            "dir/Test.subdir/test2.py",
        ]
        expected_file_map = [
            ("dir/Test.subdir/test2.py", "dir/Test.subdir/testNUM.py"),
        ]
        self.helper(
            file_names,
            old_regex,
            new_regex,
            replace_in,
            filter_by,
            filter_on,
            expected_file_names,
            expected_file_map,
        )

    def test2(self) -> None:
        file_names = [
            "dir/subdir/test1.py",
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        old_regex = r"test\d"
        new_regex = r"testNUM"
        replace_in = "basename"
        filter_by = r"/Test\..+"
        filter_on = "basename"
        expected_file_names: List[str] = []
        expected_file_map: List[Tuple[str, str]] = []
        self.helper(
            file_names,
            old_regex,
            new_regex,
            replace_in,
            filter_by,
            filter_on,
            expected_file_names,
            expected_file_map,
        )

    def test3(self) -> None:
        file_names = [
            "dir/subdir/test1.py",
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        old_regex = r"dir/"
        new_regex = r"dir/outcomes/"
        replace_in = "dirname"
        filter_by = r"/Test\..+"
        filter_on = "dirname"
        expected_file_names = [
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        expected_file_map = [
            ("dir/Test.subdir/test.py", "dir/outcomes/Test.subdir/test.py"),
            ("dir/Test.subdir/test2.py", "dir/outcomes/Test.subdir/test2.py"),
        ]
        self.helper(
            file_names,
            old_regex,
            new_regex,
            replace_in,
            filter_by,
            filter_on,
            expected_file_names,
            expected_file_map,
        )

    def test4(self) -> None:
        file_names = [
            "dir/subdir/test1.py",
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        old_regex = r"test\d"
        new_regex = r"testNUM"
        replace_in = "basename"
        filter_by = r"test\d"
        filter_on = "basename"
        expected_file_names = ["dir/Test.subdir/test2.py", "dir/subdir/test1.py"]
        expected_file_map = [
            ("dir/Test.subdir/test2.py", "dir/Test.subdir/testNUM.py"),
            ("dir/subdir/test1.py", "dir/subdir/testNUM.py"),
        ]
        self.helper(
            file_names,
            old_regex,
            new_regex,
            replace_in,
            filter_by,
            filter_on,
            expected_file_names,
            expected_file_map,
        )

    def test5(self) -> None:
        file_names = [
            "dir/subdir/test1.py",
            "dir/Test.subdir/test.py",
            "dir/Test.subdir/test2.py",
        ]
        old_regex = r"dir/"
        new_regex = r"dir/outcomes/"
        replace_in = "dirname"
        filter_by = r"test\d"
        filter_on = "basename"
        expected_file_names = ["dir/Test.subdir/test2.py", "dir/subdir/test1.py"]
        expected_file_map = [
            ("dir/Test.subdir/test2.py", "dir/outcomes/Test.subdir/test2.py"),
            ("dir/subdir/test1.py", "dir/outcomes/subdir/test1.py"),
        ]
        self.helper(
            file_names,
            old_regex,
            new_regex,
            replace_in,
            filter_by,
            filter_on,
            expected_file_names,
            expected_file_map,
        )


class Test_get_files_to_replace(hunitest.TestCase):
    def helper(
        self,
        file_names: List[str],
        filter_by: str,
        expected_file_names: List[str],
        expected_cfile: str,
    ) -> None:
        """
        Run the filter on the files and check the outcome.

        See param descriptions in `dscretex._get_files_to_replace`.

        :param expected_file_names: file names expected to remain after filtering
        :param expected_cfile: the lines from the files where the filtering regex
            should be detected
        """
        # Run.
        actual_file_names, actual_cfile = dscretex._get_files_to_replace(
            file_names, filter_by
        )
        actual_file_names = sorted(actual_file_names)
        actual_cfile = "\n".join(
            [":".join(x.split(":")[1:]) for x in actual_cfile.split("\n")]
        )
        # Check the outcome.
        self.assertEqual(actual_file_names, expected_file_names)
        self.assertEqual(actual_cfile, expected_cfile)

    def test1(self) -> None:
        in_dir = self.get_input_dir()
        file_names = [
            f"{in_dir}/file1.txt",
            f"{in_dir}/file2.txt",
            f"{in_dir}/file3.txt",
        ]
        filter_by = r"Test\..+\d"
        expected_file_names = [f"{in_dir}/file1.txt", f"{in_dir}/file2.txt"]
        expected_cfile = "\n".join(
            ["1:testing for Test.file1", "2:testing for Test.file2"]
        )
        self.helper(file_names, filter_by, expected_file_names, expected_cfile)
