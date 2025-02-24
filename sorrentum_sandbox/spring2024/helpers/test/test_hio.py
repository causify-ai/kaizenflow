import os

import helpers.hio as hio
import helpers.hunit_test as hunitest


class Test_rename_file_if_exists(hunitest.TestCase):
    """
    Test that the function renames existing files correctly.
    """

    def check_file(
        self, file_to_rename: str, before_extension: bool, expected_file_name: str
    ) -> None:
        """
        Check that file is renamed correctly.
        """
        # Create a target file to rename.
        scratch_dir = self.get_scratch_space()
        file_name = "test_file.txt"
        file_path = os.path.join(scratch_dir, file_name)
        lines = ""
        hio.to_file(file_path, lines)
        # Rename the file.
        file_to_rename = os.path.join(scratch_dir, file_to_rename)
        suffix = "suffix"
        hio.rename_file_if_exists(
            file_to_rename, suffix, before_extension=before_extension
        )
        # Check that file is renamed.
        expected_file_path = os.path.join(scratch_dir, expected_file_name)
        self.assertTrue(os.path.exists(expected_file_path))

    def test1(self) -> None:
        """
        Test that suffix is added before an extension.
        """
        file_to_rename = "test_file.txt"
        before_extension = True
        expected_file_name = "test_file.suffix.txt"
        self.check_file(file_to_rename, before_extension, expected_file_name)

    def test2(self) -> None:
        """
        Test that suffix is added after an extension.
        """
        file_to_rename = "test_file.txt"
        before_extension = False
        expected_file_name = "test_file.txt.suffix"
        self.check_file(file_to_rename, before_extension, expected_file_name)

    def test3(self) -> None:
        """
        Test that non-existing file is not renamed.
        """
        file_to_rename = "not_exist.txt"
        before_extension = False
        expected_file_name = "not_exist.txt"
        with self.assertRaises(AssertionError) as e:
            self.check_file(file_to_rename, before_extension, expected_file_name)
