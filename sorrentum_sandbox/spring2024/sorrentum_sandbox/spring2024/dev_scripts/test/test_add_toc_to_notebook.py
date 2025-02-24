import json
import logging
import shutil

import dev_scripts.notebooks.add_toc_to_notebook as dsnattono
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_add_toc(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test adding a TOC to an ipynb file.
        """
        input_file_path = f"{self.get_input_dir()}/test_ipynb_contents.json"
        # Run.
        output = self._add_toc_to_input_file(input_file_path)
        # Check.
        first_cell_str = json.dumps(output["cells"][0], indent=4)
        self.check_string(first_cell_str)

    def test2(self) -> None:
        """
        Test that nothing changes if there is an up-to-date TOC in the file.
        """
        input_file_path = f"{self.get_input_dir()}/test_ipynb_contents.json"
        # Run.
        output = self._add_toc_to_input_file(input_file_path)
        # Check.
        actual = json.dumps(output, indent=4)
        with open(input_file_path, mode="r", encoding="utf-8") as f:
            file_contents = json.load(f)
        expected = json.dumps(file_contents, indent=4)
        self.assertEqual(actual, expected)

    def test3(self) -> None:
        """
        Test updating a TOC in the file that has an outdated TOC.
        """
        input_file_path = f"{self.get_input_dir()}/test_ipynb_contents.json"
        # Run.
        output = self._add_toc_to_input_file(input_file_path)
        # Check.
        first_cell_str = json.dumps(output["cells"][0], indent=4)
        self.check_string(first_cell_str)

    def _add_toc_to_input_file(self, input_file_path: str) -> dict:
        """
        Load an ipynb file and add a TOC to it.

        :param input_file_path: the name of the file with the original
            ipynb's contents
        :return: the contents of the updated ipynb file
        """
        # Get an ipynb file.
        output_file_path = f"{self.get_output_dir()}/test.ipynb"
        shutil.copy(input_file_path, output_file_path)
        # Add a TOC to the file.
        output: dict = dsnattono.add_toc(output_file_path)
        return output
