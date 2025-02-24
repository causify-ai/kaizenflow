"""
Import as:

import helpers.hunit_test_utils as hunteuti
"""

import abc
import glob
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pytest

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hserver as hserver
import helpers.hstring as hstring
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class UnitTestRenamer:
    """
    Rename a unit test in Python code and the corresponding directories
    containing the inputs and the expected outputs.
    """

    def __init__(
        self, old_test_name: str, new_test_name: str, root_dir: str
    ) -> None:
        """
        Construct the UnitTestRenamer.

        :param old_test_name: the old name of the test
        :param new_test_name: the new name of the test
        :param root_dir: the directory to start the search from
        """
        # Check if the names of the test are valid.
        self._check_names(old_test_name, new_test_name)
        # Get the directories containing tests.
        self.test_dirs = get_test_directories(root_dir)
        # Construct the renaming config.
        self.cfg = self._process_parameters(old_test_name, new_test_name)

    def run(self) -> None:
        """
        Run the renamer tool on the files under `root_dir`.
        """
        # Iterate over test directories.
        for path in self.test_dirs:
            # Get all Python test files from this directory.
            _LOG.debug("Scanning `%s` directory.", path)
            search_pattern = os.path.join(path, "test_*.py")
            files = glob.glob(search_pattern)
            for test_file in files:
                self._rename_in_file(
                    path,
                    test_file,
                )

    def rename_outcomes(
        self,
        path: str,
    ) -> None:
        """
        Rename the directory that contains test outcomes.

        :param path: the path to the test directory, e.g.
            `cmamp1/helpers/test/`
        """
        outcomes_path = os.path.join(path, "outcomes")
        dir_items = os.listdir(outcomes_path)
        # Get the list of outcomes directories.
        outcomes = [
            dir_name
            for dir_name in dir_items
            if os.path.isdir(os.path.join(outcomes_path, dir_name))
        ]
        renamed = False
        for outcome_dir in outcomes:
            renamed = self._process_outcomes_dir(outcome_dir, outcomes_path)
        if not renamed:
            _LOG.info(
                "No outcomes for `%s` were found in `%s`.",
                self.cfg["old_class"],
                outcomes_path,
            )

    @staticmethod
    def _check_names(old_test_name: str, new_test_name: str) -> None:
        """
        Check if the test names are valid.

        :param old_test_name: the old name of the test
        :param new_test_name: the new name of the test
        """
        # Assert if the classname does not start with `Test`.
        for name in [old_test_name, new_test_name]:
            hdbg.dassert(
                name.startswith("Test"),
                "Invalid test_class_name='%s'. A test class should start with `Test`",
                name,
            )
        # Assert if the names are the same.
        hdbg.dassert_ne(old_test_name, new_test_name)

    @staticmethod
    def _process_parameters(
        old_test_name: str,
        new_test_name: str,
    ) -> Dict[str, str]:
        """
        Build the processing config with the renaming parameters.

        :param old_test_name: the old name of the test
        :param new_test_name: the new name of the test
        :return: config for renaming process, i.e. a dictionary which includes the fields:
          - `old_class`: old name of the class
          - `new_class`: new name of the class
          - `old_method`: new name of the method. If empty, only class should be renamed
          - `new_method`: new name of the method
        """
        # Build the processing config.
        config: Dict[str, str] = {}
        # Split by "." to separate class name and method name.
        split_old_name = old_test_name.split(".")
        split_new_name = new_test_name.split(".")
        # Check the consistency of the names - they should have the same length.
        hdbg.dassert_eq(
            len(split_old_name),
            len(split_new_name),
            "The test names are not consistent; one has a method and the other does not.",
        )
        # Check the format of the test name.
        hdbg.dassert_in(
            len(split_old_name),
            [1, 2],
            msg="Wrong test name format: it must contain no more than 1 dot",
        )
        if len(split_old_name) == 1:
            # Class name split by `.` is one element array, e.g. `["TestClassName"]`.
            old_class_name, old_method_name = split_old_name[0], ""
            new_class_name, new_method_name = split_new_name[0], ""
            _LOG.debug(
                "Trying to change the name of `{old_test_name}` unit test class to `%s`.",
                new_test_name,
            )
        else:
            # Method name split by `.` is 2 element array, e.g.
            # TestClassName.test2` - >`["TestClassName", "test2"]`.
            old_class_name, old_method_name = split_old_name
            new_class_name, new_method_name = split_new_name
            hdbg.dassert_eq(
                old_class_name,
                new_class_name,
                "To change the name of the method, specify the methods of the \
                same class. E.g.  `--old TestCache.test1 --new TestCache.new_test1`",
            )
            _LOG.debug(
                "Trying to change the name of `%s` method of `%s` class to `%s`.",
                old_method_name,
                old_class_name,
                new_method_name,
            )
        # Fill the processing parameters.
        config["old_class"] = old_class_name
        config["old_method"] = old_method_name
        config["new_class"] = new_class_name
        config["new_method"] = new_method_name
        return config

    @staticmethod
    def _rename_directory(outcome_path_old: str, outcome_path_new: str) -> None:
        """
        Rename the outcomes directory and add it to git.

        :param outcome_path_old: the old name of outcome directory, e.g.
          `/src/cmamp1/helpers/test/outcomes/TestRename.test_old`
        :param outcome_path_new: the new name of outcome directory, e.g.
          `/src/cmamp1/helpers/test/outcomes/TestRename.test_new`
        """
        cmd = f"mv {outcome_path_old} {outcome_path_new}"
        # Rename the directory.
        rc = hsystem.system(cmd, abort_on_error=True, suppress_output=False)
        _LOG.info(
            "Renaming `%s` directory to `%s`. Output log: %s",
            outcome_path_old,
            outcome_path_new,
            rc,
        )
        # Add to git new outcome directory and remove the old one.
        # The sequence of commands is used because `git mv` does not work
        # properly while unit testing.
        cmd = f"git add {outcome_path_new} && git rm -r {outcome_path_old}"
        hsystem.system(cmd, abort_on_error=True, suppress_output=False)

    def _rename_in_file(
        self,
        test_dir: str,
        file_path: str,
    ) -> None:
        """
        Process the file:

        - check if the content of the file contains target class
        - change the class name, e.g. `TestClassName` -> `TestClassNameNew`
          / change the method name `TestClassName.test2` -> `TestClassName.test_new`
        - rename the outcomes if they exist

        :param test_dir: the path to the test directory containing the file, e.g.
          `/src/cmamp1/helpers/test`
        :param file_path: the path to the file, `/src/cmamp1/helpers/test/test_lib_tasks.py`
        """
        content = hio.from_file(file_path)
        if not re.search(rf"class {self.cfg['old_class']}\(", content):
            # Return if target test class does not appear in file content.
            return
        if self.cfg["old_method"] == "":
            # Rename the class.
            content, n_replaced = self._rename_class(content)
            if n_replaced != 0:
                _LOG.info(
                    "%s: class `%s` was renamed to `%s`.",
                    file_path,
                    self.cfg["old_class"],
                    self.cfg["new_class"],
                )
        else:
            # Rename the method of the class.
            content, n_replaced = self._rename_method(content)
            if n_replaced != 0:
                _LOG.info(
                    "%s: method `%s` of `%s` class was renamed to `%s`.",
                    file_path,
                    self.cfg["old_method"],
                    self.cfg["old_class"],
                    self.cfg["new_method"],
                )
        # Rename the directories that contain target test outcomes.
        self.rename_outcomes(
            test_dir,
        )
        # Write processed content back to file.
        hio.to_file(file_path, content)

    def _rename_class(
        self,
        content: str,
    ) -> Tuple[str, int]:
        """
        Rename a class in a Python file.

        :param content: the content of the file
        :return: the content of the file with the class name replaced,
            the number of substitutions replaced
        """
        lines = content.split("\n")
        docstring_line_indices = hstring.get_docstring_line_indices(lines)
        for ind, line in enumerate(lines):
            # Skip if the line is inside a docstring.
            if ind not in docstring_line_indices:
                # Rename the class.
                new_line, num_replaced = re.subn(
                    rf"class {self.cfg['old_class']}\(",
                    rf"class {self.cfg['new_class']}(",
                    line,
                )
                if num_replaced != 0:
                    lines[ind] = new_line
                    break
        content = "\n".join(lines)
        return content, num_replaced

    def _rename_method(
        self,
        content: str,
    ) -> Tuple[str, int]:
        """
        Rename the method of the class.

        :param content: the content of the file
        :return: content of the file with the method renamed, the number
            of substitutions made
        """
        lines = content.split("\n")
        # Flag that informs if the class border was found.
        class_found = False
        # The number of substitutions made in the content of the file.
        num_replaced = 0
        class_pattern = rf"class {self.cfg['old_class']}\("
        method_pattern = rf"def {self.cfg['old_method']}\("
        docstring_line_indices = hstring.get_docstring_line_indices(lines)
        for ind, line in enumerate(lines):
            # Iterate over the lines of the file to find the specific method of the
            # class that should be renamed.
            # Skip if the line is inside a docstring.
            if class_found and ind not in docstring_line_indices:
                if line.startswith("class"):
                    # Break if the next class started and the method was not found.
                    break
                # Rename the method.
                new_line, num_replaced = re.subn(
                    method_pattern, f"def {self.cfg['new_method']}(", line
                )
                if num_replaced != 0:
                    # Replace the line with method definition.
                    lines[ind] = new_line
                    break
            else:
                if re.search(class_pattern, line):
                    class_found = True
        new_content = "\n".join(lines)
        return new_content, num_replaced

    def _process_outcomes_dir(self, outcome_dir: str, outcomes_path: str) -> bool:
        """
        Process the directory containing target test outcomes.

        The stages of processing are:
         - generate the new name of the directory
         - rename and add it to git

        :param outcome_dir: the name of the directory containing the outcomes
        :param outcomes_path: the path to the outcomes directory
        :return: if the outcomes were renamed
        """
        # Contruct the path to outcomes directory.
        outcome_path_old = os.path.join(outcomes_path, outcome_dir)
        # Construct old and new target dir names, e.g.
        # `TestOldName.` and `TestNewName.` if class should be renamed or
        # `TestOldName.test_old` and `TestOldName.test_new` if method should be renamed.
        old_target = ".".join([self.cfg["old_class"], self.cfg["old_method"]])
        new_target = ".".join([self.cfg["new_class"], self.cfg["new_method"]])
        if self.cfg["old_method"] == "" and outcome_dir.startswith(old_target):
            # Check if the class should be renamed, e.g.
            # if `outcome_dir` is `TestOld.test1` and `old_target` is `TestOld.`.
            # Split old directory name - the part before "." is the class name.
            class_method = outcome_dir.split(".")
            # Replace old class name with the new one, `["TestOld", "test1"]`
            # -> `["TestNew", "test1"]`.
            class_method[0] = self.cfg["new_class"]
            # Construct the new outcome directory name -> `TestNew.test1`.
            outcome_name_new = ".".join(class_method)
            outcome_path_new = os.path.join(outcomes_path, outcome_name_new)
        elif self.cfg["old_method"] != "" and outcome_dir == old_target:
            # Check if the dir should be renamed. E.g. given that `old_target`
            # is `TestOld.test1_new`, then if `outcome_dir` is `TestOld.test1`,
            # it should not be renamed, and if `outcome_dir` is `TestOld.test1_new`,
            # it should be renamed.
            outcome_path_new = os.path.join(outcomes_path, new_target)
        else:
            return False
        # Rename the directory and add it to git.
        self._rename_directory(outcome_path_old, outcome_path_new)
        return True


def get_test_directories(root_dir: str) -> List[str]:
    """
    Get paths of all the directories that contain unit tests.

    :param root_dir: the dir to start the search from, e.g.
        `/src/cmamp1/helpers`
    :return: paths of test directories
    """
    paths = []
    for path, _, _ in os.walk(root_dir):
        # Iterate over the paths to find the test directories.
        if path.endswith("/test"):
            paths.append(path)
    hdbg.dassert_lte(1, len(paths))
    return paths


# #############################################################################


class Obj_to_str_TestCase(abc.ABC):
    """
    Test case for testing `obj_to_str()` and `obj_to_repr()`.
    """

    def run_test_repr(self, obj: Any, expected_str: str) -> None:
        """
        Check that `__repr__` is printed correctly.
        """
        method_name = "__repr__"
        self._test_method(obj, method_name, expected_str)

    def run_test_str(self, obj: Any, expected_str: str) -> None:
        """
        Check that `__str__` is printed correctly.
        """
        method_name = "__str__"
        self._test_method(obj, method_name, expected_str)

    def run_test_to_config_str(self, obj: Any, expected_str: str) -> None:
        """
        Check that `to_config_str()` is printed correctly.
        """
        method_name = "to_config_str"
        self._test_method(obj, method_name, expected_str)

    def _test_method(self, obj: Any, method_name: str, expected_str: str) -> None:
        """
        Common method for testing `__repr__` and `__str__`.
        """
        hdbg.dassert_is_not(obj, None)
        actual_str = getattr(obj, method_name)()
        self.assert_equal(
            actual_str, expected_str, purify_text=True, fuzzy_match=True
        )


# #############################################################################


def _get_repo_short_name() -> str:
    dir_name = "."
    include_host_name = False
    repo_name = hgit.get_repo_full_name_from_dirname(dir_name, include_host_name)
    _LOG.debug("repo_name=%s", repo_name)
    # ck/cmamp
    short_repo_name = repo_name.split("/")[1]
    _LOG.debug("short_repo_name=%s", short_repo_name)
    return short_repo_name


def execute_only_in_target_repo(target_name: str) -> None:
    repo_short_name = _get_repo_short_name()
    if repo_short_name != target_name:
        pytest.skip(f"Only run on {target_name} and not {repo_short_name}")


def execute_only_on_ci() -> None:
    is_inside_ci_ = hserver.is_inside_ci()
    if not is_inside_ci_:
        pytest.skip("Only run in CI")


def execute_only_on_dev4() -> None:
    is_dev4_ = hserver.is_dev4()
    if not is_dev4_:
        pytest.skip("Only run on dev4")


def execute_only_on_dev_ck() -> None:
    is_dev_ck_ = hserver.is_dev_ck()
    if not is_dev_ck_:
        pytest.skip("Only run on dev CK")


def execute_only_on_mac(*, version: Optional[str] = None) -> None:
    is_mac_ = hserver.is_mac(version=version)
    if not is_mac_:
        pytest.skip(f"Only run on Mac with version={version}")


def check_env_to_str(
    self_: Any, exp: str, *, skip_secrets_vars: bool = False
) -> None:
    act = henv.env_to_str(add_system_signature=False)
    act = hunitest.filter_text("get_name", act)
    act = hunitest.filter_text("get_repo_map", act)
    act = hunitest.filter_text("AM_HOST_", act)
    if skip_secrets_vars:
        # TODO(gp): Difference between amp and cmamp.
        act = hunitest.filter_text(
            "AM_AWS_|CK_AWS_|AM_TELEGRAM_TOKEN|GH_ACTION_ACCESS_TOKEN", act
        )
    self_.assert_equal(act, exp, fuzzy_match=True, purify_text=True)
