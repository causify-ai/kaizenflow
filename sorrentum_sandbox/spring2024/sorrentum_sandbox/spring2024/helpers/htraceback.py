"""
Import as:

import helpers.htraceback as htraceb
"""

import logging
import os
import re
from typing import Any, List, Match, Optional, Tuple

import helpers.hdbg as hdbg
import helpers.hgit as hgit

_LOG = logging.getLogger(__name__)


# Store elements parsed from a line of a traceback:
#   (file_name, line_num, text)
# E.g.,
#   ("test/test_lib_tasks.py",
#    27,
#    "test_get_gh_issue_title2:act = ltasks._get_gh_issue_title(issue_id, repo)"
#    )
CfileRow = Tuple[str, int, str]


def cfile_row_to_str(cfile_row: CfileRow) -> str:
    # helpers/git.py:295:def get_repo_long_name_from_client(super_module
    hdbg.dassert_isinstance(cfile_row, tuple)
    return ":".join(list(map(str, cfile_row)))


def cfile_to_str(cfile: List[CfileRow]) -> str:
    hdbg.dassert_isinstance(cfile, list)
    return "\n".join(map(cfile_row_to_str, cfile))


def parse_traceback(
    txt: str, *, purify_from_client: bool = True
) -> Tuple[List[CfileRow], Optional[str]]:
    """
    Parse a string containing text including a Python traceback.

    :param purify_from_client: express the files with respect to the Git root
    :return:
    - a list of `CFILE_ROW`, e.g.,
      ```
      ("test/test_lib_tasks.py",
       27,
       "test_get_gh_issue_title2:act = ltasks._get_gh_issue_title(issue_id, repo)")
    - a string storing the traceback, like:
      ```
      Traceback (most recent call last):
        File "/app/amp/test/test_lib_tasks.py", line 27, in test_get_gh_issue_title2
          act = ltasks._get_gh_issue_title(issue_id, repo)
        File "/app/amp/lib_tasks.py", line 1265, in _get_gh_issue_title
          task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)
        File "/app/amp/helpers/git.py", line 397, in get_task_prefix_from_repo_short_name
          if repo_short_name == "amp":
      NameError: name 'repo_short_name' is not defined
      ```
      - A `None` value means that no traceback was found.
    """
    lines = txt.split("\n")
    # pylint: disable=line-too-long
    # Remove the artifacts of a GH run. E.g.,
    # "Run_fast_tests  Run fast tests  2022-02-19T16:53:07.0945561Z NameError: name 'cofinanc' is not defined" ->
    # -> "NameError: name 'cofinanc' is not defined".
    lines = [
        re.split(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]+Z ",
            line,
        )[-1]
        for line in lines
    ]
    state = "look_for"
    cfile: List[CfileRow] = []
    i = 0
    start_idx = end_idx = 0
    while i < len(lines):
        line = lines[i]
        _LOG.debug("state=%-10s i=%d: line='%s'", state, i, line)
        if state == "look_for":
            if line.startswith("Traceback (most recent call last):"):
                start_idx = i
                # Update the state.
                state = "parse"
                i += 1
                continue
        elif state == "parse":
            # The file looks like:
            #   File "/app/amp/test/test_lib_tasks.py", line 27, in test_get_gh
            #     act = ltasks._get_gh_issue_title(issue_id, repo)
            regex = r"^\s*File \"(.+)\", line (\d+), in (\S+)$"
            m = re.match(regex, line)
            hdbg.dassert(m, "Can't parse '%s'", line)
            m: Match[Any]
            file_name = m.group(1)
            line_num = int(m.group(2))
            func_name = m.group(3)
            _LOG.debug("  -> %s %d %s", file_name, line_num, func_name)
            #
            # Parse the next line until the next `File...`.
            _LOG.debug("Search end of snippet")
            j = i + 1
            hdbg.dassert_lte(j, len(lines))
            while j < len(lines):
                _LOG.debug("  j=%d: line='%s'", j, lines[j])
                if lines[j].startswith('  File "') or not lines[j].startswith(
                    "  "
                ):
                    _LOG.debug("  Found end of snippet")
                    break
                j += 1
            # Concatenate the lines into a single line.
            code = lines[i + 1 : j]
            _LOG.debug("  -> code: [%d, %d]\n%s", i, j, "\n".join(code))
            code = map(lambda x: x.rstrip().lstrip(), code)
            code_as_single_line = "/".join(code)
            _LOG.debug("  -> code_as_single_line=\n%s", code_as_single_line)
            # Assemble the result.
            file_name = os.path.normpath(file_name)
            cfile_row = (
                file_name,
                line_num,
                func_name + ":" + code_as_single_line,
            )
            _LOG.debug("  => cfile_row='%s'", cfile_row_to_str(cfile_row))
            cfile.append(cfile_row)
            # Update the state.
            if not lines[j].startswith("  "):
                _LOG.debug("  Found end of traceback")
                end_idx = j
                state = "end"
                break
            state = "parse"
            i = j
            continue
        #
        i += 1
    #
    if state == "look_for":
        # We didn't find a traceback.
        cfile = []
        traceback = None
    elif state == "end":
        if (
            end_idx < len(lines) - 1
            and "Error:" not in lines[end_idx - 1]
            and "Error:" in lines[end_idx]
        ):
            # Extend the traceback to the lines with the error description.
            # E.g., for the snippet below:
            # '''
            #    if repo_short_name == "amp":
            # NameError: name 'repo_short_name' is not defined
            # '''
            # If the parsed traceback stops at 'if repo_short_name == "amp":', and thus,
            # its last line does not include the error description ("NameError:..."),
            # and the following line does include the error description,
            # then the traceback will be extended to include the following line,
            # making the parsed traceback end with the following two lines:
            # '''
            #    if repo_short_name == "amp":
            # NameError: name 'repo_short_name' is not defined
            # '''
            to_break = False
            while end_idx < len(lines) - 1 and not to_break:
                end_idx += 1
                if (
                    "________ Test" in lines[end_idx]
                    or "====== slowest 3 durations" in lines[end_idx]
                ):
                    # Stop if we have reached the next traceback or the end of the
                    # pytest report.
                    to_break = True
        hdbg.dassert_lte(0, start_idx)
        hdbg.dassert_lte(start_idx, end_idx)
        hdbg.dassert_lt(end_idx, len(lines))
        traceback = "\n".join(lines[start_idx:end_idx])
    else:
        raise ValueError(f"Invalid state='{state}'")
    _LOG.debug("traceback=\n%s", traceback)
    _LOG.debug("cfile=\n%s", cfile_to_str(cfile))
    # Purify filenames from client so that refer to files in this client.
    if cfile and purify_from_client:
        _LOG.debug("# Purifying from client")
        cfile_tmp = []
        for cfile_row in cfile:
            file_name, line_num, text = cfile_row
            # Leave the files relative to the current dir.
            root_dir = hgit.get_client_root(super_module=False)
            mode = "return_all_results"
            file_names = hgit.find_docker_file(
                file_name, root_dir=root_dir, mode=mode
            )
            if len(file_names) == 0:
                _LOG.warning("Can't find file corresponding to '%s'", file_name)
            elif len(file_names) > 1:
                _LOG.warning(
                    "Found multiple potential files corresponding to '%s'",
                    file_name,
                )
            else:
                file_name = file_names[0]
                cfile_tmp.append((file_name, line_num, text))
        cfile = cfile_tmp
        _LOG.debug("# After purifying from client")
        _LOG.debug("cfile=\n%s", cfile_to_str(cfile))
    return cfile, traceback
