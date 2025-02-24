#!/usr/bin/env python
"""
Reformat and lint python and ipynb files.

This script uses the version of the files present on the disk and not what is
staged for commit by git, thus you need to stage again after running it.

E.g.,
# Lint all modified files in git client.
> linter.py

# Lint current files.
> linter.py -c --collect_only
> linter.py -c --all

# Lint previous commit files.
> linter.py -p --collect_only

# Lint a certain number of previous commits
> linter.py -p 3 --collect_only
> linter.py --files event_study/*.py linter_v2.py --yapf --isort -v DEBUG

# Lint the changes in the branch:
> linter.py -b
> linter.py -f $(git diff --name-only master...)

# Lint all python files, but not the notebooks.
> linter.py -d . --only_py --collect

# To jump to all the warnings to fix:
> vim -c "cfile linter.log"

# Check all jupytext files.
> linter.py -d . --action sync_jupytext

Import as:

import dev_scripts.old.linter.linter as dsollili
"""

import argparse
import itertools
import logging
import os
import py_compile
import re
import sys
from typing import Any, List, Tuple, Type

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hlist as hlist
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# Use the current dir and not the dir of the executable.
_TMP_DIR = os.path.abspath(os.getcwd() + "/tmp.linter")


# #############################################################################
# Utils.
# #############################################################################


NO_PRINT = False


def _print(*args: Any, **kwargs: Any) -> None:
    if not NO_PRINT:
        print(*args, **kwargs)


# TODO(gp): This could become the default behavior of system().
def _system(cmd: str, abort_on_error: bool = True) -> int:
    suppress_output = _LOG.getEffectiveLevel() > logging.DEBUG
    rc = hsystem.system(
        cmd,
        abort_on_error=abort_on_error,
        suppress_output=suppress_output,
        log_level=logging.DEBUG,
    )
    return rc  # type: ignore


# TODO(gp): Move to helpers/printing.py
def _dassert_list_of_strings(output: List[str], *args: Any) -> None:
    hdbg.dassert_isinstance(output, list, *args)
    for line in output:
        hdbg.dassert_isinstance(line, str, *args)


def _annotate_output(output: List, executable: str) -> List:
    """
    Annotate a list containing the output of a cmd line with the name of the
    executable used.

    :return: list of strings
    """
    _dassert_list_of_strings(output)
    output = [t + " [%s]" % executable for t in output]
    _dassert_list_of_strings(output)
    return output


def _tee(
    cmd: str, executable: str, abort_on_error: bool
) -> Tuple[int, List[str]]:
    """
    Execute command "cmd", capturing its output and removing empty lines.

    :return: list of strings
    """
    _LOG.debug("cmd=%s executable=%s", cmd, executable)
    rc, output = hsystem.system_to_string(cmd, abort_on_error=abort_on_error)
    hdbg.dassert_isinstance(output, str)
    output1 = output.split("\n")
    _LOG.debug("output1= (%d)\n'%s'", len(output1), "\n".join(output1))
    #
    output2 = hprint.remove_empty_lines_from_string_list(output1)
    _LOG.debug("output2= (%d)\n'%s'", len(output2), "\n".join(output2))
    _dassert_list_of_strings(output2)
    return rc, output2


# TODO(gp): Move to system_interactions.
def _check_exec(tool: str) -> bool:
    """
    :return: True if the executables "tool" can be executed.
    """
    rc = _system("which %s" % tool, abort_on_error=False)
    return rc == 0


# #############################################################################
# Handle files.
# #############################################################################


def _filter_target_files(file_names: List[str]) -> List[str]:
    """
    Keep only the files that:

    - have extension .py, .ipynb, .txt or .md.
    - are not Jupyter checkpoints
    - are not in tmp dirs
    """
    file_names_out: List[str] = []
    for file_name in file_names:
        _, file_ext = os.path.splitext(file_name)
        # We skip .ipynb since jupytext is part of the main flow.
        is_valid = file_ext in (".py", ".txt", ".md", ".ipynb")
        is_valid &= ".ipynb_checkpoints/" not in file_name
        is_valid &= "dev_scripts/install/conda_envs" not in file_name
        # Skip requirements.txt.
        is_valid &= os.path.basename(file_name) != "requirements.txt"
        # Skip tmp names since we need to run on unit tests.
        if False:
            # Skip files in directory starting with "tmp.".
            is_valid &= "/tmp." not in file_name
            # Skip files starting with "tmp.".
            is_valid &= not file_name.startswith("tmp.")
        if is_valid:
            file_names_out.append(file_name)
    return file_names_out


def _get_files(args: argparse.Namespace) -> List[str]:
    """
    Return the list of files to process given the command line arguments.
    """
    file_names: List[str] = []
    if args.files:
        _LOG.debug("Specified files")
        # User has specified files.
        file_names = args.files
    else:
        if args.current_git_files:
            # Get all the git modified files.
            file_names = hgit.get_modified_files()
        elif args.previous_git_committed_files is not None:
            _LOG.debug("Looking for files committed in previous Git commit")
            # Get all the git in user previous commit.
            n_commits = args.previous_git_committed_files
            _LOG.info("Using %s previous commits", n_commits)
            file_names = hgit.get_previous_committed_files(n_commits)
        elif args.modified_files_in_branch:
            dir_name = "."
            dst_branch = "master"
            file_names = hgit.get_modified_files_in_branch(dir_name, dst_branch)
        elif args.target_branch:
            dir_name = "."
            dst_branch = args.target_branch
            file_names = hgit.get_modified_files_in_branch(dir_name, dst_branch)
        elif args.dir_name:
            if args.dir_name == "$GIT_ROOT":
                dir_name = hgit.get_client_root(super_module=True)
            else:
                dir_name = args.dir_name
            dir_name = os.path.abspath(dir_name)
            _LOG.info("Looking for all files in '%s'", dir_name)
            hdbg.dassert_path_exists(dir_name)
            cmd = "find %s -name '*' -type f" % dir_name
            _, output = hsystem.system_to_string(cmd)
            file_names = output.split("\n")
    # Remove text files used in unit tests.
    file_names = [f for f in file_names if not is_test_input_output_file(f)]
    # Make all paths absolute.
    # file_names = [os.path.abspath(f) for f in file_names]
    # Check files exist.
    file_names_out = []
    for f in file_names:
        if not os.path.exists(f):
            _LOG.warning("File '%s' doesn't exist: skipping", f)
        else:
            file_names_out.append(f)
    return file_names_out


def _list_to_str(list_: List[str]) -> str:
    return "%d (%s)" % (len(list_), " ".join(list_))


def _get_files_to_lint(
    args: argparse.Namespace, file_names: List[str]
) -> List[str]:
    """
    Get all the files that need to be linted.

    Typically files to lint are python and notebooks.
    """
    _LOG.debug("file_names=%s", _list_to_str(file_names))
    # Keep only actual .py and .ipynb files.
    file_names = _filter_target_files(file_names)
    _LOG.debug("file_names=%s", _list_to_str(file_names))
    # Remove files.
    if args.skip_py:
        file_names = [f for f in file_names if not is_py_file(f)]
    if args.skip_ipynb:
        file_names = [f for f in file_names if not is_ipynb_file(f)]
    if args.skip_files:
        hdbg.dassert_isinstance(args.skip_files, list)
        # TODO(gp): Factor out this code and reuse it in this function.
        _LOG.warning(
            "Skipping %s files, as per user request",
            _list_to_str(args.skip_files),
        )
        skip_files = args.skip_files
        skip_files = [os.path.abspath(f) for f in skip_files]
        skip_files = set(skip_files)
        file_names_out = [f for f in file_names if f not in skip_files]
        removed_file_names = list(set(file_names) - set(file_names_out))
        _LOG.warning("Removing %s files", _list_to_str(removed_file_names))
        file_names = file_names_out
    # Keep files.
    if args.only_py:
        file_names = [
            f
            for f in file_names
            if is_py_file(f) and not is_paired_jupytext_file(f)
        ]
    if args.only_ipynb:
        file_names = [f for f in file_names if is_ipynb_file(f)]
    if args.only_paired_jupytext:
        file_names = [f for f in file_names if is_paired_jupytext_file(f)]
    #
    _LOG.debug("file_names=(%s) %s", len(file_names), " ".join(file_names))
    if len(file_names) < 1:
        _LOG.warning("No files that can be linted are specified")
    return file_names


# #############################################################################


def _write_file_back(file_name: str, txt: List[str], txt_new: List[str]) -> None:
    _dassert_list_of_strings(txt)
    txt_as_str = "\n".join(txt)
    #
    _dassert_list_of_strings(txt_new)
    txt_new_as_str = "\n".join(txt_new)
    #
    if txt_as_str != txt_new_as_str:
        hio.to_file(file_name, txt_new_as_str)


# There are some lints that
#   a) we disagree with (e.g., too many functions in a class)
#       - they are ignored all the times
#   b) are too hard to respect (e.g., each function has a docstring)
#       - they are ignored unless we want to see them
#
# pedantic=2 -> all lints, including a) and b)
# pedantic=1 -> discard lints from a), include b)
# pedantic=0 -> discard lints from a) and b)

# - The default is to run with (-> pedantic=0)
# - Sometimes we want to take a look at the lints that we would like to enforce
#   (-> pedantic=1)
# - In rare occasions we want to see all the lints (-> pedantic=2)


# TODO(gp): joblib asserts when using abstract classes:
#   AttributeError: '_BasicHygiene' object has no attribute '_executable'
# class _Action(abc.ABC):
class _Action:
    """
    Implemented as a Strategy pattern.
    """

    def __init__(self, executable: str = "") -> None:
        self._executable = executable

    # @abc.abstractmethod
    def check_if_possible(self) -> bool:
        """
        Check if the action can be executed.
        """
        raise NotImplementedError

    def execute(self, file_name: str, pedantic: int) -> List[str]:
        """
        Execute the action.

        :param file_name: name of the file to process
        :param pendantic: True if it needs to be run in angry mode
        :return: list of strings representing the output
        """
        hdbg.dassert(file_name)
        hdbg.dassert_path_exists(file_name)
        output = self._execute(file_name, pedantic)
        _dassert_list_of_strings(output)
        return output

    # @abc.abstractmethod
    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        raise NotImplementedError


# #############################################################################


class _CheckFileProperty(_Action):
    """
    Perform various checks based on property of a file:

    - check that file size doesn't exceed a certain threshould
    - check that notebook files are under a `notebooks` dir
    - check that test files are under `test` dir
    """

    def check_if_possible(self) -> bool:
        # We don't need any special executable, so we can always run this action.
        return True

    @staticmethod
    def _check_size(file_name: str) -> str:
        """
        Check size of a file.
        """
        msg = ""
        max_size_in_bytes = 512 * 1024
        size_in_bytes = os.path.getsize(file_name)
        if size_in_bytes > max_size_in_bytes:
            msg = "%s:1: file size is too large %s > %s" % (
                file_name,
                size_in_bytes,
                max_size_in_bytes,
            )
        return msg

    @staticmethod
    def _check_notebook_dir(file_name: str) -> str:
        """
        # Check if that notebooks are under `notebooks` dir.
        """
        msg = ""
        if is_ipynb_file(file_name):
            subdir_names = file_name.split("/")
            if "notebooks" not in subdir_names:
                msg = (
                    "%s:1: each notebook should be under a 'notebooks' "
                    "directory to not confuse pytest" % file_name
                )
        return msg

    @staticmethod
    def _check_test_file_dir(file_name: str) -> str:
        """
        Check if test files are under `test` dir.
        """
        msg = ""
        # TODO(gp): A little annoying that we use "notebooks" and "test".
        if is_py_file(file_name) and os.path.basename(file_name).startswith(
            "test_"
        ):
            if not is_under_test_dir(file_name):
                msg = (
                    "%s:1: test files should be under 'test' directory to "
                    "be discovered by pytest" % file_name
                )
        return msg

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        output: List[str] = []
        for func in [
            self._check_size,
            self._check_notebook_dir,
            self._check_test_file_dir,
        ]:
            msg = func(file_name)
            if msg:
                _LOG.warning(msg)
                output.append(msg)
        return output


# #############################################################################


class _BasicHygiene(_Action):
    def check_if_possible(self) -> bool:
        # We don't need any special executable, so we can always run this action.
        return True

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        output: List[str] = []
        # Read file.
        txt = hio.from_file(file_name).split("\n")
        # Process file.
        txt_new: List[str] = []
        for line in txt:
            if "\t" in line:
                msg = (
                    "Found tabs in %s: please use 4 spaces as per PEP8"
                    % file_name
                )
                _LOG.warning(msg)
                output.append(msg)
            # Convert tabs.
            line = line.replace("\t", " " * 4)
            # Remove trailing spaces.
            line = line.rstrip()
            # dos2unix.
            line = line.replace("\r\n", "\n")
            # TODO(gp): Remove empty lines in functions.
            txt_new.append(line.rstrip("\n"))
        # Remove whitespaces at the end of file.
        while txt_new and (txt_new[-1] == "\n"):
            # While the last item in the list is blank, removes last element.
            txt_new.pop(-1)
        # Write.
        _write_file_back(file_name, txt, txt_new)
        return output


# #############################################################################


class _CompilePython(_Action):
    """
    Check that the code is valid python.
    """

    def check_if_possible(self) -> bool:
        # We don't need any special executable, so we can always run this action.
        return True

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        output: List[str] = []
        # Applicable only to python files.
        if not is_py_file(file_name):
            _LOG.debug("Skipping self._file_name='%s'", file_name)
            return output
        #
        try:
            py_compile.compile(file_name, doraise=True)
            # pylint: disable=broad-except
        except Exception as e:
            output.append(str(e))
        return output


# #############################################################################


class _Autoflake(_Action):
    """
    Remove unused imports and variables.
    """

    def __init__(self) -> None:
        executable = "autoflake"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        #
        opts = "-i --remove-all-unused-imports --remove-unused-variables"
        cmd = self._executable + " %s %s" % (opts, file_name)
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        return output


# #############################################################################


class _Yapf(_Action):
    """
    Apply yapf code formatter.
    """

    def __init__(self) -> None:
        executable = "yapf"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        #
        opts = "-i --style='google'"
        cmd = self._executable + " %s %s" % (opts, file_name)
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        return output


# #############################################################################


class _Black(_Action):
    """
    Apply black code formatter.
    """

    def __init__(self) -> None:
        executable = "black"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        #
        opts = "--line-length 82"
        cmd = self._executable + " %s %s" % (opts, file_name)
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        # Remove the lines:
        # - reformatted core/test/test_core.py
        # - 1 file reformatted.
        # - All done!
        # - 1 file left unchanged.
        to_remove = ["All done!", "file left unchanged", "reformatted"]
        output = [l for l in output if all(w not in l for w in to_remove)]
        return output


# #############################################################################


class _Isort(_Action):
    """
    Sort imports using isort.
    """

    def __init__(self) -> None:
        executable = "isort"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        #
        cmd = self._executable + " %s" % file_name
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        return output


# #############################################################################


class _Flake8(_Action):
    """
    Look for formatting and semantic issues in code and docstrings. It relies
    on:

    - mccabe
    - pycodestyle
    - pyflakes
    """

    def __init__(self) -> None:
        executable = "flake8"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        # TODO(gp): Does -j 4 help?
        opts = "--exit-zero --doctests --max-line-length=82 -j 4"
        ignore = [
            # - "W503 line break before binary operator"
            #     - Disabled because in contrast with black formatting.
            "W503",
            # - W504 line break after binary operator
            #     - Disabled because in contrast with black formatting.
            "W504",
            # - E203 whitespace before ':'
            #     - Disabled because in contrast with black formatting
            "E203",
            # - E266 too many leading '#' for block comment
            #     - We have disabled this since it is a false positive for
            #       jupytext files.
            "E266,"
            # - E501 line too long (> 82 characters)
            #     - We have disabled this since it triggers also for docstrings
            #       at the beginning of the line. We let pylint pick the lines
            #       too long, since it seems to be smarter.
            "E501",
            # - E731 do not assign a lambda expression, use a def
            "E731",
            # - E265 block comment should start with '# '
            "E265",
        ]
        is_jupytext_code = is_paired_jupytext_file(file_name)
        _LOG.debug("is_jupytext_code=%s", is_jupytext_code)
        if is_jupytext_code:
            ignore.extend(
                [
                    # E501 line too long.
                    "E501"
                ]
            )
        opts += " --ignore=" + ",".join(ignore)
        cmd = self._executable + " %s %s" % (opts, file_name)
        #
        _, output = _tee(cmd, self._executable, abort_on_error=True)
        # Remove some errors.
        is_jupytext_code = is_paired_jupytext_file(file_name)
        _LOG.debug("is_jupytext_code=%s", is_jupytext_code)
        if is_jupytext_code:
            output_tmp: List[str] = []
            for line in output:
                # F821 undefined name 'display' [flake8]
                if "F821" in line and "undefined name 'display'" in line:
                    continue
                output_tmp.append(line)
            output = output_tmp
        return output


# #############################################################################


class _Pydocstyle(_Action):
    def __init__(self) -> None:
        executable = "pydocstyle"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        ignore = []
        # http://www.pydocstyle.org/en/2.1.1/error_codes.html
        if pedantic < 2:
            # TODO(gp): Review all of these.
            ignore.extend(
                [
                    # D105: Missing docstring in magic method
                    "D105",
                    # D200: One-line docstring should fit on one line with quotes
                    "D200",
                    # D202: No blank lines allowed after function docstring
                    "D202",
                    # D212: Multi-line docstring summary should start at the first line
                    "D212",
                    # D203: 1 blank line required before class docstring (found 0)
                    "D203",
                    # D205: 1 blank line required between summary line and description
                    "D205",
                    # D400: First line should end with a period (not ':')
                    "D400",
                    # D402: First line should not be the function's "signature"
                    "D402",
                    # D407: Missing dashed underline after section
                    "D407",
                    # D413: Missing dashed underline after section
                    "D413",
                    # D415: First line should end with a period, question mark, or
                    # exclamation point
                    "D415",
                ]
            )
        if pedantic < 1:
            # Disable some lints that are hard to respect.
            ignore.extend(
                [
                    # D100: Missing docstring in public module
                    "D100",
                    # D101: Missing docstring in public class
                    "D101",
                    # D102: Missing docstring in public method
                    "D102",
                    # D103: Missing docstring in public function
                    "D103",
                    # D104: Missing docstring in public package
                    "D104",
                    # D107: Missing docstring in __init__
                    "D107",
                ]
            )
        cmd_opts = ""
        if ignore:
            cmd_opts += "--ignore " + ",".join(ignore)
        #
        cmd = []
        cmd.append(self._executable)
        cmd.append(cmd_opts)
        cmd.append(file_name)
        cmd_as_str = " ".join(cmd)
        # We don't abort on error on pydocstyle, since it returns error if there
        # is any violation.
        _, file_lines_as_str = hsystem.system_to_string(
            cmd_as_str, abort_on_error=False
        )
        # Process lint_log transforming:
        #   linter_v2.py:1 at module level:
        #       D400: First line should end with a period (not ':')
        # into:
        #   linter_v2.py:1: at module level: D400: First line should end with a
        #   period (not ':')
        #
        output: List[str] = []
        #
        file_lines = file_lines_as_str.split("\n")
        lines = ["", ""]
        for cnt, line in enumerate(file_lines):
            line = line.rstrip("\n")
            # _log.debug("line=%s", line)
            if cnt % 2 == 0:
                regex = r"(\s(at|in)\s)"
                subst = r":\1"
                line = re.sub(regex, subst, line)
            else:
                line = line.lstrip()
            # _log.debug("-> line=%s", line)
            lines[cnt % 2] = line
            if cnt % 2 == 1:
                line = "".join(lines)
                output.append(line)
        return output


# #############################################################################


class _Pyment(_Action):
    def __init__(self) -> None:
        executable = "pyment"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        opts = "-w --first-line False -o reST"
        cmd = self._executable + " %s %s" % (opts, file_name)
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        return output


# #############################################################################


class _Pylint(_Action):
    def __init__(self) -> None:
        executable = "pylint"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        # Applicable to only python file.
        if not is_py_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        #
        is_test_code_tmp = is_under_test_dir(file_name)
        _LOG.debug("is_test_code_tmp=%s", is_test_code_tmp)
        #
        is_jupytext_code = is_paired_jupytext_file(file_name)
        _LOG.debug("is_jupytext_code=%s", is_jupytext_code)
        #
        opts = []
        ignore = []
        if pedantic < 2:
            # We ignore these errors as too picky.
            ignore.extend(
                [
                    # [C0302(too-many-lines), ] Too many lines in module (/1000)
                    "C0302",
                    # TODO(gp): Re-enable?
                    # [C0304(missing-final-newline), ] Final newline missing
                    "C0304",
                    # [C0330(bad-continuation), ] Wrong hanging indentation before
                    #   block (add 4 spaces).
                    # - Black and pylint don't agree on the formatting.
                    "C0330",
                    # [C0412(ungrouped-imports), ] Imports from package ... are not
                    #   grouped
                    # TODO(gp): Re-enable?
                    "C0412",
                    # [C0415(import-outside-toplevel), ] Import outside toplevel
                    # - Sometimes we import inside a function.
                    "C0415",
                    # [R0902(too-many-instance-attributes)] Too many instance attributes (/7)
                    "R0902",
                    # [R0903(too-few-public-methods), ] Too few public methods (/2)
                    "R0903",
                    # [R0904(too-many-public-methods), ] Too many public methods (/20)
                    "R0904",
                    # [R0912(too-many-branches), ] Too many branches (/12)
                    "R0912",
                    # R0913(too-many-arguments), ] Too many arguments (/5)
                    "R0913",
                    # [R0914(too-many-locals), ] Too many local variables (/15)
                    "R0914",
                    # [R0915(too-many-statements), ] Too many statements (/50)
                    "R0915",
                    # [W0123(eval-used), ] Use of eval
                    # - We assume that we are mature enough to use `eval` properly.
                    "W0123",
                    # [W0125(using-constant-test), ] Using a conditional statement
                    #   with a constant value:
                    # - E.g., we use sometimes `if True:` or `if False:`.
                    "W0125",
                    # [W0201(attribute-defined-outside-init)]
                    # - If the constructor calls a method (e.g., `reset()`) to
                    #   initialize the state, we have all these errors.
                    "W0201",
                    # [W0511(fixme), ]
                    "W0511",
                    # [W0603(global-statement), ] Using the global statement
                    # - We assume that we are mature enough to use `global` properly.
                    "W0603",
                    # [W1113(keyword-arg-before-vararg), ] Keyword argument before variable
                    #   positional arguments list in the definition of
                    # - TODO(gp): Not clear what is the problem.
                    "W1113",
                ]
            )
            # Unit test.
            if is_test_code_tmp:
                ignore.extend(
                    [
                        # [C0103(invalid-name), ] Class name "Test_dassert_eq1"
                        #   doesn't conform to PascalCase naming style
                        "C0103",
                        # [R0201(no-self-use), ] Method could be a function
                        "R0201",
                        # [W0212(protected-access), ] Access to a protected member
                        #   _get_default_tempdir of a client class
                        "W0212",
                    ]
                )
            # Jupytext.
            if is_jupytext_code:
                ignore.extend(
                    [
                        # [W0104(pointless-statement), ] Statement seems to
                        # have noeffect
                        # - This is disabled since we use just variable names
                        #   to print.
                        "W0104",
                        # [W0106(expression-not-assigned), ] Expression ... is
                        # assigned to nothing
                        "W0106",
                        # [W0621(redefined-outer-name), ] Redefining name ...
                        # from outer scope
                        "W0621",
                    ]
                )
        if pedantic < 1:
            ignore.extend(
                [
                    # [C0103(invalid-name), ] Constant name "..." doesn't
                    #   conform to UPPER_CASE naming style
                    "C0103",
                    # [C0111(missing - docstring), ] Missing module docstring
                    "C0111",
                    # [C0301(line-too-long), ] Line too long (/100)
                    # "C0301",
                ]
            )
        if ignore:
            opts.append("--disable " + ",".join(ignore))
        # Allow short variables, as long as they are camel-case.
        opts.append('--variable-rgx="[a-z0-9_]{1,30}$"')
        opts.append('--argument-rgx="[a-z0-9_]{1,30}$"')
        # TODO(gp): Not sure this is needed anymore.
        opts.append("--ignored-modules=pandas")
        opts.append("--output-format=parseable")
        # TODO(gp): Does -j 4 help?
        opts.append("-j 4")
        # pylint crashed due to lack of memory.
        # A fix according to https://github.com/PyCQA/pylint/issues/2388 is:
        opts.append('--init-hook="import sys; sys.setrecursionlimit(2000)"')
        _dassert_list_of_strings(opts)
        opts_as_str = " ".join(opts)
        cmd = " ".join([self._executable, opts_as_str, file_name])
        _, output = _tee(cmd, self._executable, abort_on_error=False)
        # Remove some errors.
        output_tmp: List[str] = []
        for line in output:
            if is_jupytext_code:
                # [E0602(undefined-variable), ] Undefined variable 'display'
                if "E0602" in line and "Undefined variable 'display'" in line:
                    continue
            if line.startswith("Your code has been rated"):
                # Your code has been rated at 10.00/10 (previous run: ...
                line = file_name + ": " + line
            output_tmp.append(line)
        output = output_tmp
        # Remove lines.
        output = [l for l in output if ("-" * 20) not in l]
        # Remove:
        #    ************* Module dev_scripts.generate_script_catalog
        output_as_str = hunitest.filter_text(
            re.escape("^************* Module "), "\n".join(output)
        )
        # Remove empty lines.
        output = [l for l in output if l.rstrip().lstrip() != ""]
        #
        output = output_as_str.split("\n")
        return output


# #############################################################################


class _Mypy(_Action):
    def __init__(self) -> None:
        executable = "mypy"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        # Applicable to only python files, that are not paired with notebooks.
        if not is_py_file(file_name) or is_paired_jupytext_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return []
        # TODO(gp): Convert all these idioms into arrays and joins.
        cmd = self._executable + " %s" % file_name
        _, output = _tee(
            cmd,
            self._executable,
            # mypy returns -1 if there are errors.
            abort_on_error=False,
        )
        # Remove some errors.
        output_tmp: List[str] = []
        for line in output:
            if (
                line.startswith("Success:")
                or
                # Found 2 errors in 1 file (checked 1 source file)
                line.startswith("Found ")
                or
                # note: See https://mypy.readthedocs.io
                "note: See https" in line
            ):
                continue
            output_tmp.append(line)
        output = output_tmp
        return output


# #############################################################################


class _IpynbFormat(_Action):
    def __init__(self) -> None:
        curr_path = os.path.dirname(os.path.realpath(sys.argv[0]))
        executable = "%s/ipynb_format.py" % curr_path
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        output: List[str] = []
        # Applicable to only ipynb file.
        if not is_ipynb_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return output
        #
        cmd = self._executable + " %s" % file_name
        _system(cmd)
        return output


# TODO(gp): Move in a more general file: probably system_interaction.
def _is_under_dir(file_name: str, dir_name: str) -> bool:
    """
    Return whether a file is under the given directory.
    """
    subdir_names = file_name.split("/")
    return dir_name in subdir_names


def is_under_test_dir(file_name: str) -> bool:
    """
    Return whether a file is under a test directory (which is called "test").
    """
    return _is_under_dir(file_name, "test")


def is_test_input_output_file(file_name: str) -> bool:
    """
    Return whether a file is used as input or output in a unit test.
    """
    ret = is_under_test_dir(file_name)
    ret &= file_name.endswith(".txt")
    return ret


def is_test_code(file_name: str) -> bool:
    """
    Return whether a file contains unit test code.
    """
    ret = is_under_test_dir(file_name)
    ret &= os.path.basename(file_name).startswith("test_")
    ret &= file_name.endswith(".py")
    return ret


def is_py_file(file_name: str) -> bool:
    """
    Return whether a file is a python file.
    """
    return file_name.endswith(".py")


def is_ipynb_file(file_name: str) -> bool:
    """
    Return whether a file is a jupyter notebook file.
    """
    return file_name.endswith(".ipynb")


def from_python_to_ipynb_file(file_name: str) -> str:
    hdbg.dassert(is_py_file(file_name))
    ret = file_name.replace(".py", ".ipynb")
    return ret


def from_ipynb_to_python_file(file_name: str) -> str:
    hdbg.dassert(is_ipynb_file(file_name))
    ret = file_name.replace(".ipynb", ".py")
    return ret


def is_paired_jupytext_file(file_name: str) -> bool:
    """
    Return whether a file is a paired jupytext file.
    """
    is_paired = (
        is_py_file(file_name)
        and os.path.exists(from_python_to_ipynb_file(file_name))
        or (
            is_ipynb_file(file_name)
            and os.path.exists(from_ipynb_to_python_file(file_name))
        )
    )
    return is_paired


def is_init_py(file_name: str) -> bool:
    return os.path.basename(file_name) == "__init__.py"


# #############################################################################


class _ProcessJupytext(_Action):
    def __init__(self, jupytext_action: str) -> None:
        executable = "process_jupytext.py"
        super().__init__(executable)
        self._jupytext_action = jupytext_action

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        output: List[str] = []
        # TODO(gp): Use the usual idiom of these functions.
        if is_py_file(file_name) and is_paired_jupytext_file(file_name):
            cmd_opts = "-f %s --action %s" % (file_name, self._jupytext_action)
            cmd = self._executable + " " + cmd_opts
            rc, output = _tee(cmd, self._executable, abort_on_error=False)
            if rc != 0:
                error = "process_jupytext failed with command `%s`\n" % cmd
                output.append(error)
                _LOG.error(output)
        else:
            _LOG.debug("Skipping file_name='%s'", file_name)
        return output


class _SyncJupytext(_ProcessJupytext):
    def __init__(self) -> None:
        super().__init__("sync")


class _TestJupytext(_ProcessJupytext):
    def __init__(self) -> None:
        super().__init__("test")


# #############################################################################


class _CustomPythonChecks(_Action):
    # The maximum length of an 'import as'.
    MAX_LEN_IMPORT = 8
    DEBUG = False

    def check_if_possible(self) -> bool:
        # We don't need any special executable, so we can always run this action.
        return True

    @staticmethod
    def _check_shebang(
        file_name: str, txt: List[str], is_executable: bool
    ) -> str:
        msg = ""
        shebang = "#!/usr/bin/env python"
        has_shebang = txt[0] == shebang
        if (is_executable and not has_shebang) or (
            not is_executable and has_shebang
        ):
            msg = "%s:1: any executable needs to start with a shebang '%s'" % (
                file_name,
                shebang,
            )
        return msg

    @staticmethod
    def _check_import(file_name: str, line_num: int, line: str) -> str:
        msg = ""
        if _CustomPythonChecks.DEBUG:
            _LOG.debug("* Check 'from * imports'")
        if is_init_py(file_name):
            # In __init__.py we can import in weird ways (e.g., the
            # evil `from ... import *`).
            return msg
        m = re.match(r"\s*from\s+(\S+)\s+import\s+.*", line)
        if m:
            if m.group(1) != "typing":
                msg = "%s:%s: do not use '%s' use 'import foo.bar " "as fba'" % (
                    file_name,
                    line_num,
                    line.rstrip().lstrip(),
                )
        else:
            m = re.match(r"\s*import\s+\S+\s+as\s+(\S+)", line)
            if m:
                shortcut = m.group(1)
                if len(shortcut) > _CustomPythonChecks.MAX_LEN_IMPORT:
                    msg = (
                        "%s:%s: the import shortcut '%s' in '%s' is longer than "
                        "%s characters"
                        % (
                            file_name,
                            line_num,
                            shortcut,
                            line.rstrip().lstrip(),
                            _CustomPythonChecks.MAX_LEN_IMPORT,
                        )
                    )
        return msg

    @staticmethod
    def _was_baptized(file_name: str, txt: List[str]) -> str:
        """
        Check if code contains a declaration of how it needs to be imported.

        Import as:

        import _setenv_lib as selib
        ...
        """
        msg: List[str] = []
        _dassert_list_of_strings(txt)
        if len(txt) > 3:
            match = True
            match &= txt[0] == '"""'
            match &= txt[1] == "Import as:"
            match &= txt[2] == ""
            match &= txt[3].startswith("import ")
        else:
            match = False
        if not match:
            msg.append(
                "%s:1: every library needs to describe how to be imported:"
                % file_name
            )
            msg.append('"""')
            msg.append("Import as:")
            msg.append("\nimport foo.bar as fba")
            msg.append('"""')
        else:
            # Check that the import is in the right format, like:
            #   import _setenv_lib as selib
            import_line = 3
            line = txt[import_line]
            _LOG.debug("import line=%s", line)
            msg_tmp = _CustomPythonChecks._check_import(
                file_name, import_line, line
            )
            if msg_tmp:
                msg.append(msg_tmp)
        msg_as_str = "\n".join(msg)
        return msg_as_str

    @staticmethod
    def _check_line_by_line(
        file_name: str, txt: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Apply various checks line by line.

        - Check imports
        - Look for conflict markers
        - Format separating lines
        """
        _dassert_list_of_strings(txt)
        output: List[str] = []
        txt_new: List[str] = []
        for i, line in enumerate(txt):
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("%s: line='%s'", i, line)
            # Check imports.
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("* Check imports")
            msg = _CustomPythonChecks._check_import(file_name, i + 1, line)
            if msg:
                output.append(msg)
            # Look for conflicts markers.
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("* Look for conflict markers")
            if any(line.startswith(c) for c in ["<<<<<<<", "=======", ">>>>>>>"]):
                msg = "%s:%s: there are conflict markers" % (file_name, i + 1)
                output.append(msg)
            # Format separating lines.
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("* Format separating lines")
            min_num_chars = 6
            regex = r"(\s*\#)\s*([\#\=\-\<\>]){%d,}\s*$" % min_num_chars
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("regex=%s", regex)
            m = re.match(regex, line)
            if m:
                char = m.group(2)
                line = m.group(1) + " " + char * (78 - len(m.group(1)))
            #
            if _CustomPythonChecks.DEBUG:
                _LOG.debug("    -> %s", line)
            txt_new.append(line)
            _dassert_list_of_strings(txt_new)
            #
            _dassert_list_of_strings(output)
        return output, txt_new

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        _ = pedantic
        output: List[str] = []
        # Applicable only to python files that are not paired with Jupytext.
        if not is_py_file(file_name) or is_paired_jupytext_file(file_name):
            _LOG.debug("Skipping file_name='%s'", file_name)
            return output
        # Read file.
        txt = hio.from_file(file_name).split("\n")
        # Only library code should be baptized.
        should_baptize = True
        should_baptize &= not os.path.basename("__init__.py")
        should_baptize &= not is_test_code(file_name)
        if should_baptize:
            # Check shebang.
            is_executable = os.access(file_name, os.X_OK)
            msg = self._check_shebang(file_name, txt, is_executable)
            if msg:
                output.append(msg)
            # Check that the module was baptized.
            if not is_executable:
                msg = self._was_baptized(file_name, txt)
                if msg:
                    output.append(msg)
        # Process file.
        output_tmp, txt_new = self._check_line_by_line(file_name, txt)
        output.extend(output_tmp)
        # Write file back.
        _write_file_back(file_name, txt, txt_new)
        return output


# #############################################################################


class _LintMarkdown(_Action):
    def __init__(self) -> None:
        executable = "prettier"
        super().__init__(executable)

    def check_if_possible(self) -> bool:
        return _check_exec(self._executable)

    def _execute(self, file_name: str, pedantic: int) -> List[str]:
        # Applicable only to txt and md files.
        ext = os.path.splitext(file_name)[1]
        output: List[str] = []
        if ext not in (".txt", ".md"):
            _LOG.debug("Skipping file_name='%s' because ext='%s'", file_name, ext)
            return output
        # Run lint_txt.py.
        executable = "lint_txt.py"
        exec_path = hgit.find_file_in_git_tree(executable)
        hdbg.dassert_path_exists(exec_path)
        #
        cmd = []
        cmd.append(exec_path)
        cmd.append("-i %s" % file_name)
        cmd.append("--in_place")
        cmd_as_str = " ".join(cmd)
        _, output = _tee(cmd_as_str, executable, abort_on_error=True)
        # Remove cruft.
        output = [l for l in output if "Saving log to file" not in l]
        return output


# #############################################################################


def _check_file_property(
    actions: List[str], all_file_names: List[str], pedantic: int
) -> Tuple[List[str], List[str]]:
    output: List[str] = []
    action = "check_file_property"
    if action in actions:
        for file_name in all_file_names:
            class_ = _get_action_class(action)
            output_tmp = class_.execute(file_name, pedantic)
            _dassert_list_of_strings(output_tmp)
            output.extend(output_tmp)
    actions = [a for a in actions if a != action]
    _LOG.debug("actions=%s", actions)
    return output, actions


def _are_git_files_changed() -> bool:
    """
    Check changes in the local repo.

    If any file in the local repo changed, returns False.
    """
    result = True
    changed_files = hgit.get_modified_files()
    if changed_files:
        _LOG.warning("Modified files: %s.", changed_files)
        result = False
    return result


# #############################################################################
# Actions.
# #############################################################################

# We use the command line instead of API because:
# - some tools don't have a public API
# - this make easier to reproduce / test commands using the command lines and
#   then incorporate in the code
# - it allows to have clear control over options


# Actions and if they read / write files.
# The order of this list implies the order in which they are executed.

# TODO(GP,Sergey): I think this info should be encapsulated in classes.
#  There are mapping that we have to maintain. DRY.
_VALID_ACTIONS_META: List[Tuple[str, str, str, Type[_Action]]] = [
    (
        "check_file_property",
        "r",
        "Check that generic files are valid",
        _CheckFileProperty,
    ),
    (
        "basic_hygiene",
        "w",
        "Clean up (e.g., tabs, trailing spaces)",
        _BasicHygiene,
    ),
    ("compile_python", "r", "Check that python code is valid", _CompilePython),
    ("autoflake", "w", "Removes unused imports and variables", _Autoflake),
    ("isort", "w", "Sort Python import definitions alphabetically", _Isort),
    # Superseded by black.
    # ("yapf", "w", "Formatter for Python code", _Yapf),
    ("black", "w", "The uncompromising code formatter", _Black),
    ("flake8", "r", "Tool For Style Guide Enforcement", _Flake8),
    ("pydocstyle", "r", "Docstring style checker", _Pydocstyle),
    # TODO(gp): Fix this.
    # Not installable through conda.
    # ("pyment", "w", "Create, update or convert docstring", _Pyment),
    ("pylint", "w", "Check that module(s) satisfy a coding standard", _Pylint),
    ("mypy", "r", "Static code analyzer using the hint types", _Mypy),
    ("sync_jupytext", "w", "Create / sync jupytext files", _SyncJupytext),
    ("test_jupytext", "r", "Test jupytext files", _TestJupytext),
    # Superseded by "sync_jupytext".
    # ("ipynb_format", "w", "Format jupyter code using yapf", _IpynbFormat),
    (
        "custom_python_checks",
        "w",
        "Apply some custom python checks",
        _CustomPythonChecks,
    ),
    ("lint_markdown", "w", "Lint txt/md markdown files", _LintMarkdown),
]


# joblib and caching with lru_cache don't get along, so we cache explicitly.
_VALID_ACTIONS = None


def _get_valid_actions() -> List[str]:
    global _VALID_ACTIONS
    if _VALID_ACTIONS is None:
        _VALID_ACTIONS = list(zip(*_VALID_ACTIONS_META))[0]
    return _VALID_ACTIONS  # type: ignore


def _get_default_actions() -> List[str]:
    return _get_valid_actions()


def _get_action_class(action: str) -> _Action:
    """
    Return the function corresponding to the passed string.
    """
    res = None
    for action_meta in _VALID_ACTIONS_META:
        name, rw, comment, class_ = action_meta
        _ = rw, comment
        if name == action:
            hdbg.dassert_is(res, None)
            res = class_
    hdbg.dassert_is_not(res, None)
    # mypy gets confused since we are returning a class.
    obj = res()  # type: ignore
    return obj


def _remove_not_possible_actions(actions: List[str]) -> List[str]:
    """
    Check whether each action in "actions" can be executed and return a list of
    the actions that can be executed.

    :return: list of strings representing actions
    """
    actions_tmp: List[str] = []
    for action in actions:
        class_ = _get_action_class(action)
        is_possible = class_.check_if_possible()
        if not is_possible:
            _LOG.warning("Can't execute action '%s': skipping", action)
        else:
            actions_tmp.append(action)
    return actions_tmp


def _select_actions(args: argparse.Namespace) -> List[str]:
    valid_actions = _get_valid_actions()
    default_actions = _get_default_actions()
    actions = hparser.select_actions(args, valid_actions, default_actions)
    # Find the tools that are available.
    actions = _remove_not_possible_actions(actions)
    #
    add_frame = True
    actions_as_str = hparser.actions_to_string(
        actions, _get_valid_actions(), add_frame
    )
    _LOG.info("\n%s", actions_as_str)
    return actions


def _test_actions() -> None:
    _LOG.info("Testing actions")
    # Check all the actions.
    num_not_poss = 0
    possible_actions: List[str] = []
    for action in _get_valid_actions():
        class_ = _get_action_class(action)
        is_possible = class_.check_if_possible()
        _LOG.debug("%s -> %s", action, is_possible)
        if is_possible:
            possible_actions.append(action)
        else:
            num_not_poss += 1
    # Report results.
    add_frame = True
    actions_as_str = hparser.actions_to_string(
        possible_actions, _get_valid_actions(), add_frame
    )
    _LOG.info("\n%s", actions_as_str)
    if num_not_poss > 0:
        _LOG.warning("There are %s actions that are not possible", num_not_poss)
    else:
        _LOG.info("All actions are possible")


# #############################################################################


def _lint(
    file_name: str, actions: List[str], pedantic: int, debug: bool
) -> List[str]:
    """
    Execute all the actions on a filename.

    Note that this is the unit of parallelization, i.e., we run all the
    actions on a single file to ensure that the actions are executed in
    the proper order.
    """
    output: List[str] = []
    _LOG.info("\n%s", hprint.frame(file_name, char1="="))
    for action in actions:
        _LOG.debug("\n%s", hprint.frame(action, char1="-"))
        _print("## %-20s (%s)" % (action, file_name))
        if debug:
            # Make a copy after each action.
            dst_file_name = file_name + "." + action
            cmd = "cp -a %s %s" % (file_name, dst_file_name)
            os.system(cmd)
        else:
            dst_file_name = file_name
        class_ = _get_action_class(action)
        # We want to run the stages, and not check.
        output_tmp = class_.execute(dst_file_name, pedantic)
        # Annotate with executable [tag].
        output_tmp = _annotate_output(output_tmp, action)
        _dassert_list_of_strings(
            output_tmp, "action=%s file_name=%s", action, file_name
        )
        output.extend(output_tmp)
        if output_tmp:
            _LOG.info("\n%s", "\n".join(output_tmp))
    return output


def _run_linter(
    actions: List[str], args: argparse.Namespace, file_names: List[str]
) -> List[str]:
    num_steps = len(file_names) * len(actions)
    _LOG.info(
        "Num of files=%d, num of actions=%d -> num of steps=%d",
        len(file_names),
        len(actions),
        num_steps,
    )
    pedantic = args.pedantic
    num_threads = args.num_threads
    # Use serial mode if there is a single file, unless the user specified
    # explicitly the numer of threads to use.
    if len(file_names) == 1 and num_threads != -1:
        num_threads = "serial"
        _LOG.warning(
            "Using num_threads='%s' since there is a single file", num_threads
        )
    output: List[str] = []
    if num_threads == "serial":
        for file_name in file_names:
            output_tmp = _lint(file_name, actions, pedantic, args.debug)
    else:
        num_threads = int(num_threads)
        # -1 is interpreted by joblib like for all cores.
        _LOG.info(
            "Using %s threads", num_threads if num_threads > 0 else "all CPUs"
        )
        import joblib

        output_tmp = joblib.Parallel(n_jobs=num_threads, verbose=50)(
            joblib.delayed(_lint)(file_name, actions, pedantic, args.debug)
            for file_name in file_names
        )
        output_tmp = list(itertools.chain.from_iterable(output_tmp))
    output.extend(output_tmp)
    output = hprint.remove_empty_lines_from_string_list(output)
    return output  # type: ignore


def _count_lints(lints: List[str]) -> int:
    num_lints = 0
    for line in lints:
        # dev_scripts/linter.py:493: ... [pydocstyle]
        if re.match(r"\S+:\d+.*\[\S+\]", line):
            num_lints += 1
    _LOG.info("num_lints=%d", num_lints)
    return num_lints


# #############################################################################
# Main.
# #############################################################################


def _main(args: argparse.Namespace) -> int:
    hdbg.init_logger(args.log_level)
    #
    if args.test_actions:
        _LOG.warning("Testing actions...")
        _test_actions()
        _LOG.warning("Exiting as requested")
        sys.exit(0)
    if args.no_print:
        global NO_PRINT
        NO_PRINT = True
    # Get all the files to process.
    all_file_names = _get_files(args)
    _LOG.info("# Found %d files to process", len(all_file_names))
    # Select files.
    file_names = _get_files_to_lint(args, all_file_names)
    _LOG.info(
        "\n%s\n%s",
        hprint.frame("# Found %d files to lint:" % len(file_names)),
        hprint.indent("\n".join(file_names)),
    )
    if args.collect_only:
        _LOG.warning("Exiting as requested")
        sys.exit(0)
    # Select actions.
    actions = _select_actions(args)
    all_actions = actions[:]
    _LOG.debug("actions=%s", actions)
    # Create tmp dir.
    hio.create_dir(_TMP_DIR, incremental=False)
    _LOG.info("tmp_dir='%s'", _TMP_DIR)
    # Check the files.
    lints: List[str] = []
    lints_tmp, actions = _check_file_property(
        actions, all_file_names, args.pedantic
    )
    lints.extend(lints_tmp)
    # Run linter.
    lints_tmp = _run_linter(actions, args, file_names)
    _dassert_list_of_strings(lints_tmp)
    lints.extend(lints_tmp)
    # Sort the errors.
    lints = sorted(lints)
    lints = hlist.remove_duplicates(lints)
    # Count number of lints.
    num_lints = _count_lints(lints)
    #
    output: List[str] = []
    output.append("cmd line='%s'" % hdbg.get_command_line())
    # TODO(gp): datetime_.get_timestamp().
    # output.insert(1, "datetime='%s'" % datetime.datetime.now())
    output.append("actions=%d %s" % (len(all_actions), all_actions))
    output.append("file_names=%d %s" % (len(file_names), file_names))
    output.extend(lints)
    output.append("num_lints=%d" % num_lints)
    # Write the file.
    output_as_str = "\n".join(output)
    hio.to_file(args.linter_log, output_as_str)
    # Print linter output.
    txt = hio.from_file(args.linter_log)
    _print(hprint.frame(args.linter_log, char1="/").rstrip("\n"))
    _print(txt + "\n")
    _print(hprint.line(char="/").rstrip("\n"))
    #
    if num_lints != 0:
        _LOG.warning(
            "You can quickfix the issues with\n> vim -c 'cfile %s'",
            args.linter_log,
        )
    #
    if not args.no_cleanup:
        hio.delete_dir(_TMP_DIR)
    else:
        _LOG.warning("Leaving tmp files in '%s'", _TMP_DIR)
    if args.jenkins:
        _LOG.warning("Skipping returning an error because of --jenkins")
        num_lints = 0
    return num_lints


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Select files.
    parser.add_argument(
        "-f", "--files", nargs="+", type=str, help="Files to process"
    )
    parser.add_argument(
        "-c",
        "--current_git_files",
        action="store_true",
        help="Select files modified in the current git client",
    )
    parser.add_argument(
        "-p",
        "--previous_git_committed_files",
        nargs="?",
        type=int,
        const=1,
        default=None,
        help="Select files modified in previous 'n' user git commit",
    )
    parser.add_argument(
        "-b",
        "--modified_files_in_branch",
        action="store_true",
        help="Select files modified in current branch with respect to master",
    )
    parser.add_argument(
        "-t",
        "--target_branch",
        action="store",
        type=str,
        help="Select files modified in current branch with respect to `target_branch`.",
    )
    parser.add_argument(
        "-d",
        "--dir_name",
        action="store",
        help="Select all files in a dir. 'GIT_ROOT' to select git root",
    )
    parser.add_argument(
        "--skip_files",
        action="append",
        help="Force skipping certain files, e.g., together with -d",
    )
    # Select files based on type.
    parser.add_argument(
        "--skip_py", action="store_true", help="Do not process python scripts"
    )
    parser.add_argument(
        "--skip_ipynb",
        action="store_true",
        help="Do not process jupyter notebooks",
    )
    parser.add_argument(
        "--skip_paired_jupytext",
        action="store_true",
        help="Do not process paired notebooks",
    )
    parser.add_argument(
        "--only_py",
        action="store_true",
        help="Process only python scripts excluding paired notebooks",
    )
    parser.add_argument(
        "--only_ipynb", action="store_true", help="Process only jupyter notebooks"
    )
    parser.add_argument(
        "--only_paired_jupytext",
        action="store_true",
        help="Process only paired notebooks",
    )
    # Debug.
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Generate one file per transformation",
    )
    parser.add_argument(
        "--no_cleanup", action="store_true", help="Do not clean up tmp files"
    )
    parser.add_argument("--jenkins", action="store_true", help="Run as jenkins")
    # Test.
    parser.add_argument(
        "--collect_only",
        action="store_true",
        help="Print only the files to process and stop",
    )
    parser.add_argument(
        "--test_actions", action="store_true", help="Print the possible actions"
    )
    # Select actions.
    hparser.add_action_arg(parser, _get_valid_actions(), _get_default_actions())
    #
    parser.add_argument(
        "--pedantic",
        action="store",
        type=int,
        default=0,
        help="Pedantic level. 0 = min, 2 = max (all the lints)",
    )
    parser.add_argument(
        "--num_threads",
        action="store",
        default="-1",
        help="Number of threads to use ('serial' to run serially, -1 to use "
        "all CPUs)",
    )
    #
    parser.add_argument(
        "--linter_log",
        default="./linter_warnings.txt",
        help="File storing the warnings",
    )
    parser.add_argument("--no_print", action="store_true")
    parser.add_argument(
        "--post_check",
        action="store_true",
        help="Add post check. Return -1 if any file changed by the linter.",
    )
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    parser_ = _parse()
    args_ = parser_.parse_args()
    rc_ = _main(args_)
    if args_.post_check:
        if not _are_git_files_changed():
            rc_ = 1
            _LOG.warning(
                "Detected that some files were changed so returning -1 as per "
                "the option `--post_check`"
            )
        else:
            rc_ = 0
    sys.exit(rc_)
