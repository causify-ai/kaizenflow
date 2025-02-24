"""
Import as:

import dev_scripts.git.git_hooks.utils as dsgghout
"""

# NOTE: This file should depend only on Python standard libraries.
import compileall
import inspect
import logging
import os
import re
import string
import subprocess
import sys
from typing import Any, List, Optional, Tuple

_LOG = logging.getLogger(__name__)

# TODO(gp): Check these hooks
# https://github.com/pre-commit/pre-commit-hooks/tree/master/pre_commit_hooks
# https://github.com/pre-commit/pre-commit-hooks/blob/master/pre_commit_hooks/check_ast.py
# https://github.com/pre-commit/pre-commit-hooks/blob/master/pre_commit_hooks/check_added_large_files.py
# https://github.com/pre-commit/pre-commit-hooks/blob/master/pre_commit_hooks/check_merge_conflict.py
# https://code-maven.com/enforcing-commit-message-format-in-git

# TODO(gp): Add a check for "Do not commit" or "Do not merge".


# The path to the git-binary:
_GIT_BINARY_PATH = "git"


# Stat copy-paste from helpers/printing.py
_COLOR_MAP = {
    "blue": 94,
    "green": 92,
    "white": 0,
    "purple": 95,
    "red": 91,
    "yellow": 33,
    # Blu.
    "DEBUG": 34,
    # Cyan.
    "INFO": 36,
    # Yellow.
    "WARNING": 33,
    # Red.
    "ERROR": 31,
    # White on red background.
    "CRITICAL": 41,
}


def color_highlight(text: str, color: str) -> str:
    """
    Return a colored string.
    """
    prefix = "\033["
    suffix = "\033[0m"
    assert color in _COLOR_MAP
    color_code = _COLOR_MAP[color]
    txt = f"{prefix}{color_code}m{text}{suffix}"
    return txt


# End copy-paste.


# Start copy-paste from helpers/introspection.py
def get_function_name(count: int = 0) -> str:
    """
    Return the name of the function calling this function, i.e., the name of
    the function calling `get_function_name()`.
    """
    ptr = inspect.currentframe()
    # count=0 corresponds to the calling function, so we need to add an extra
    # step walking the call stack.
    count += 1
    for _ in range(count):
        assert ptr is not None
        ptr = ptr.f_back
    func_name = ptr.f_code.co_name  # type: ignore
    return func_name


# End copy-paste.


# Start copy-paste from helpers/system_interaction.py
def _system_to_string(
    cmd: str, abort_on_error: bool = True, verbose: bool = False
) -> Tuple[int, str]:
    assert isinstance(cmd, str), "Type of '%s' is %s" % (str(cmd), type(cmd))
    if verbose:
        print(f"> {cmd}")
    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    with subprocess.Popen(
        cmd, shell=True, executable="/bin/bash", stdout=stdout, stderr=stderr
    ) as p:
        output = ""
        while True:
            line = p.stdout.readline().decode("utf-8")  # type: ignore
            if not line:
                break
            # print((line.rstrip("\n")))
            output += line
        p.stdout.close()  # type: ignore
        rc = p.wait()
    if abort_on_error and rc != 0:
        msg = (
            "cmd='%s' failed with rc='%s'" % (cmd, rc)
        ) + "\nOutput of the failing command is:\n%s" % output
        _LOG.error(msg)
        sys.exit(-1)
    return rc, output


# End copy-paste.

# #############################################################################
# Utils.
# #############################################################################


def _get_files() -> List[str]:
    """
    Get all the files to process.
    """
    # Check all files staged and modified, i.e., skipping only un-tracked files.
    # TODO(gp): In reality we should check only staged files.
    # > git status --porcelain -uno
    #  M dev_scripts/git/git_hooks/pre-commit.py
    cmd = f"{_GIT_BINARY_PATH} status --porcelain --untracked-files=no"
    rc, txt = _system_to_string(cmd)
    _ = rc
    file_list: List[str] = txt.splitlines()
    # Remove the Git codes (in the first 3 characters) leaving only the file name.
    file_list = [file_name[3:] for file_name in file_list]
    return file_list


def _report() -> str:
    func_name = get_function_name(count=1)
    print("\n" + color_highlight(f"##### {func_name} ######", "purple"))
    return func_name


def _handle_error(func_name: str, error: bool, abort_on_error: bool) -> None:
    """
    Abort depending on the error code `error` and on the desired behavior
    `abort_on_error`.
    """
    if error:
        print("\n" + color_highlight(f"'{func_name}' failed", "red"))
        if abort_on_error:
            sys.exit(-1)
    else:
        print(color_highlight(f"'{func_name}' passed", "green"))


# #############################################################################
# check_master
# #############################################################################


def check_master(abort_on_error: bool = True) -> None:
    """
    Check if we are committing directly to master, instead of a branch.
    """
    func_name = _report()
    # Print some information.
    verbose = True
    cmd = "git rev-parse --abbrev-ref HEAD"
    rc, branch_name = _system_to_string(cmd, verbose=verbose)
    _ = rc
    branch_name = branch_name.lstrip().rstrip()
    print(f"Branch is '{branch_name}'")
    if branch_name == "master":
        msg = (
            "You shouldn't merge into `master`: please do a PR and then merge it"
        )
        _LOG.error(msg)
        error = True
    else:
        error = False
    # Handle error.
    _handle_error(func_name, error, abort_on_error)


# #############################################################################
# check_author
# #############################################################################


def check_author(abort_on_error: bool = True) -> None:
    """
    Ensure that the committer use a gmail and not a corporate account.

    Extremely custom but effective invariant.
    """
    func_name = _report()
    # Print some information.
    verbose = True
    var = "user.name"
    cmd = f"{_GIT_BINARY_PATH} config {var}"
    _system_to_string(cmd, verbose=verbose)
    cmd = f"{_GIT_BINARY_PATH} config --show-origin {var}"
    _system_to_string(cmd, verbose=verbose)
    #
    var = "user.email"
    cmd = f"{_GIT_BINARY_PATH} config {var}"
    rc, user_email = _system_to_string(cmd, verbose=verbose)
    _ = rc
    user_email = user_email.lstrip().rstrip()
    cmd = f"{_GIT_BINARY_PATH} config --show-origin {var}"
    _system_to_string(cmd, verbose=verbose)
    print(f"user_email='{user_email}")
    # Check.
    error = False
    if not user_email.endswith("@gmail.com"):
        _LOG.error("user_email='%s' is incorrect", user_email)
        error = True
    # Handle error.
    _handle_error(func_name, error, abort_on_error)


# #############################################################################
# check_file_size
# #############################################################################


# Start copy-paste From helpers/introspection.py
def _sizeof_fmt(num: float) -> str:
    """
    Return a human-readable string for a filesize (e.g., "3.5 MB").
    """
    # From http://stackoverflow.com/questions/1094841
    for x in ["bytes", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    assert 0, "Invalid num='%s'" % num


# End copy-paste.


# The maximum file-size in KB for a file (not notebook) to be committed.
_MAX_FILE_SIZE_IN_KB = 512


def check_file_size(
    abort_on_error: bool = True, file_list: Optional[List[str]] = None
) -> None:
    """
    Ensure that (not notebook) files are not larger than a certain size.

    The goal is to avoid to check in a 100MB file.
    """
    func_name = _report()
    print(f"max file size={_MAX_FILE_SIZE_IN_KB} KB")
    if file_list is None:
        file_list = _get_files()
    _LOG.info("Files:\n%s", "\n".join(file_list))
    # Check all files:
    error = False
    for file_name in file_list:
        if not os.path.exists(file_name):
            _LOG.warning("'%s' doesn't exist", file_name)
            continue
        _LOG.info(file_name)
        stat = os.stat(file_name)
        size = stat.st_size
        size_as_str = _sizeof_fmt(stat.st_size)
        _LOG.debug("%s: %s", file_name, size_as_str)
        if not file_name.endswith(".ipynb"):
            if size > _MAX_FILE_SIZE_IN_KB * 1024:
                # File is to big, abort the commit.
                msg = (
                    f"Filename '{file_name}' is too big to be committed"
                    + f": {size_as_str} > {_MAX_FILE_SIZE_IN_KB} KB"
                )
                _LOG.error(msg)
                error = True
    # Handle error.
    _handle_error(func_name, error, abort_on_error)


# #############################################################################
# check_words
# #############################################################################


_CAESAR_STEP = 7


def caesar(text: str, step: int) -> str:
    def shift(alphabet: str) -> str:
        return alphabet[step:] + alphabet[:step]

    alphabets = (string.ascii_lowercase, string.ascii_uppercase, string.digits)
    shifted_alphabets = tuple(map(shift, alphabets))
    joined_alphabets = "".join(alphabets)
    joined_shifted_alphabets = "".join(shifted_alphabets)
    table = str.maketrans(joined_alphabets, joined_shifted_alphabets)
    return text.translate(table)


def _get_regex(decaesarify: bool) -> Any:
    # Prepare the regex.
    words = "ln lnpk sptl sltvuhkl slt jyfwav"
    if decaesarify:
        words = caesar(words, -_CAESAR_STEP)
    words_as_regex = "(" + "|".join(words.split()) + ")"
    regex = rf"""
            (?<![^\W_])     # The preceding char should not be a letter or digit char.
            {words_as_regex}
            (?![^\W_])      # The next char cannot be a letter or digit.
            """
    # regex  = re.compile(r"\b(%s)\b" % "|".join(words.split()))
    # _LOG.debug("regex=%s", regex)
    regex = re.compile(regex, re.IGNORECASE | re.VERBOSE)
    # _LOG.debug("regex=%s", regex)
    return regex


def _check_words_in_text(
    file_name: str, lines: List[str], decaesarify: bool = True
) -> List[str]:
    """
    Look for words in the content `lines` of `file_name`.

    :return: violations in cfile format
    """
    regex = _get_regex(decaesarify)
    # Search for violations.
    violations = []
    for i, line in enumerate(lines):
        _LOG.debug("%s: %s", i + 1, line)
        m = regex.search(line)
        if m:
            # Remove some false positive.
            if file_name.endswith(".ipynb") and "image/png" in line:
                continue
            if file_name.endswith(".html") and '<td class="ms' in line:
                continue
            if file_name.endswith("git.py") and "return _is_repo" in line:
                continue
            if file_name.endswith("ack") and "compressed" in line:
                continue
            if file_name.endswith("helpers/git.py") and "def is_" in line:
                continue
            # Found a violation.
            val = m.group(1)
            _LOG.debug("  -> found '%s'", val)
            val = caesar(val, _CAESAR_STEP)
            violation = f"{file_name}:{i+1}: Found '{val}'"
            violations.append(violation)
    return violations


def _check_words_files(file_list: List[str]) -> bool:
    """
    Look for words in the passed files.

    :return: error
    """
    _LOG.debug("Processing %d files", len(file_list))
    # Scan all the files.
    violations = []
    for file_name in file_list:
        if any(file_name.endswith(ext) for ext in "jpg png zip pkl gz".split()):
            _LOG.warning("Skipping '%s'", file_name)
            continue
        if not os.path.exists(file_name):
            _LOG.warning("Skipping '%s' since it doesn't exist", file_name)
            continue
        if os.path.isdir(file_name):
            _LOG.warning("Skipping '%s' since it is a dir", file_name)
            continue
        _LOG.info(file_name)
        with open(file_name) as f:
            lines = f.readlines()
        violations.extend(_check_words_in_text(file_name, lines))
    #
    error = False
    if violations:
        file_content = "\n".join(map(str, violations))
        _LOG.error("There are %d violations:\n%s", len(violations), file_content)
        # Write file.
        file_name = "cfile"
        with open(file_name, "w") as f:
            f.write(file_content)
        _LOG.warning("Saved cfile in '%s'", file_name)
        error = True
    return error


def check_words(
    abort_on_error: bool = True, file_list: Optional[List[str]] = None
) -> None:
    """
    Check that certain words are not used in the staged files.
    """
    func_name = _report()
    # Get the files.
    if file_list is None:
        file_list = _get_files()
    _LOG.info("Files:\n%s", "\n".join(file_list))
    #
    error = _check_words_files(file_list)
    # Handle error.
    _handle_error(func_name, error, abort_on_error)


# #############################################################################
# Python compile
# #############################################################################


def _check_python_compile(file_list: List[str]) -> bool:
    """
    Run `compileall.compile_file()` on the files.

    :return: error
    """
    _LOG.debug("Processing %d files", len(file_list))
    # Scan all the files.
    violations = []
    for file_name in file_list:
        success = compileall.compile_file(file_name, force=True, quiet=0)
        _LOG.debug("%s -> success=%s", file_name, success)
        if not success:
            _LOG.error("file_name='%s' doesn't compile correctly", file_name)
            violations.append(file_name)
    _LOG.debug("violations=%s", len(violations))
    error = len(violations) > 0
    return error


def check_python_compile(
    abort_on_error: bool = True, file_list: Optional[List[str]] = None
) -> None:
    """
    Check that code can be compiled.

    This is not as thorough as executing it.
    """
    func_name = _report()
    # Get the files.
    if file_list is None:
        file_list = _get_files()
    _LOG.info("Files:\n%s", "\n".join(file_list))
    # Keep only the python files.
    file_list = [f for f in file_list if f.endswith(".py")]
    _LOG.info("Python files:\n%s", "\n".join(file_list))
    #
    error = _check_python_compile(file_list)
    # Handle error.
    _handle_error(func_name, error, abort_on_error)
