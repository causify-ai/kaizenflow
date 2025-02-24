"""
Import as:

import helpers.hstring as hstring
"""
import logging
import os
import re
import tempfile
from typing import List, Optional, Tuple, cast

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def remove_prefix(string: str, prefix: str, assert_on_error: bool = True) -> str:
    if string.startswith(prefix):
        res = string[len(prefix) :]
    else:
        res = string
        if assert_on_error:
            raise RuntimeError(
                f"string='{string}' doesn't start with prefix ='{prefix}'"
            )
    return res


def remove_suffix(string: str, suffix: str, assert_on_error: bool = True) -> str:
    if string.endswith(suffix):
        res = string[: -len(suffix)]
    else:
        res = string
        if assert_on_error:
            raise RuntimeError(
                f"string='{string}' doesn't end with suffix='{suffix}'"
            )
    return res


def diff_strings(
    txt1: str,
    txt2: str,
    txt1_descr: Optional[str] = None,
    txt2_descr: Optional[str] = None,
    width: int = 130,
) -> str:
    # Write file.
    def _to_file(txt: str, txt_descr: Optional[str]) -> str:
        file_name = tempfile.NamedTemporaryFile().name
        if txt_descr is not None:
            txt = "# " + txt_descr + "\n" + txt
        hio.to_file(file_name, txt)
        return file_name

    file_name1 = _to_file(txt1, txt1_descr)
    file_name2 = _to_file(txt2, txt2_descr)
    # Get the difference between the files.
    cmd = f"sdiff --width={width} {file_name1} {file_name2}"
    _, txt = hsystem.system_to_string(
        cmd,
        # We don't care if they are different.
        abort_on_error=False,
    )
    # For some reason, mypy doesn't understand that system_to_string returns a
    # string.
    txt = cast(str, txt)
    return txt


def get_docstring_line_indices(lines: List[str]) -> List[int]:
    """
    Get indices of lines of code that are inside (doc)strings.

    :param lines: the code lines to check
    :return: the indices of docstrings
    """
    docstring_line_indices = []
    quotes = {'"""': False, "'''": False, "```": False}
    for i, line in enumerate(lines):
        # Determine if the current line is inside a (doc)string.
        for quote in quotes:
            quotes_matched = re.findall(quote, line)
            for q in quotes_matched:
                # Switch the docstring flag.
                # pylint: disable=modified-iterating-dict
                quotes[q] = not quotes[q]
        if any(quotes.values()):
            # Store the index if the quotes have been opened but not closed yet.
            docstring_line_indices.append(i)
    return docstring_line_indices


def extract_version_from_file_name(file_name: str) -> Tuple[int, int]:
    """
    Extract version number from filename_vXX.json file. e.g.
    'universe_v3.1.json' -> (3, 1) 'universe_v1.json' -> (1, 0)
    'dataset_schema_v3.json' -> (3, 0)

    Currently only JSON file extension is supported.

    :param file_name: file to extract version part from
    :return: file version tuple in format (major, minor)
    """
    basename = os.path.basename(file_name).rstrip(".json")
    m = re.search(r"v(\d+(\.\d+)?)$", basename)
    hdbg.dassert(
        m,
        "Can't parse file '%s', correct format is e.g. 'universe_v03.json'.",
        basename,
    )
    # Groups return tuple.
    version = m.groups(1)[0].split(".")  # type: ignore[arg-type, union-attr]
    major, minor = int(version[0]), 0 if len(version) == 1 else int(version[1])

    return major, minor
