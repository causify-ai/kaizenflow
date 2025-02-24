"""
Support opening a file.

Import as:

import helpers.hopen as hopen
"""

# TODO(gp): -> open_file or move it to system_interaction.py

import logging
import os
from typing import Optional

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _cmd_open_html(file_name: str, os_name: str) -> Optional[str]:
    """
    Get OS-specific command to open an HTML file.
    """
    # Retrieve the executable.
    os_cmds = {
        "Darwin": "open",
        "Windows": "start",
        "Linux": "xdg-open",
    }
    hdbg.dassert_in(os_name, os_cmds)
    exec_name = os_cmds[os_name]
    if not hsystem.check_exec(exec_name):
        _LOG.warning("Can't execute the command '%s' on this platform", exec_name)
        return None
    # Build the command.
    full_cmd = f"{exec_name} {file_name}"
    if os_name == "Linux":
        _LOG.warning(
            "To open files faster launch in background '%s &'", exec_name
        )
    return full_cmd


def _cmd_open_pdf(file_name: str, os_name: str) -> str:
    """
    Get OS-specific command to open a PDF file.
    """
    os_cmds = {
        "Darwin": (
            "/usr/bin/osascript << EOF\n"
            f'set theFile to POSIX file "{file_name}" as alias\n'
            'tell application "Skim"\n'
            "activate\n"
            "set theDocs to get documents whose path is "
            "(get POSIX path of theFile)\n"
            "if (count of theDocs) > 0 then revert theDocs\n"
            "open theFile\n"
            "end tell\n"
            "EOF\n"
        )
    }
    hdbg.dassert_in(os_name, os_cmds)
    return os_cmds[os_name]


def open_file(file_name: str) -> None:
    """
    Open file locally if its extension is supported.
    """
    # Detect file format by the (last) extension.
    # E.g., 'hello.html.txt' is considered a txt file.
    extension = os.path.split(file_name)[-1].split(".")[-1]
    extension = extension.lower()
    # Make sure file exists.
    _LOG.info(
        "\n%s",
        hprint.frame(
            f"Opening {extension} file '{file_name}'", char1="<", char2=">"
        ),
    )
    hdbg.dassert_path_exists(file_name)
    # Get opening command.
    os_name = hsystem.get_os_name()
    cmd: Optional[str]
    if extension == "pdf":
        cmd = _cmd_open_pdf(file_name, os_name)
    elif extension == "html":
        cmd = _cmd_open_html(file_name, os_name)
    else:
        hdbg.dfatal(f"Opening '{extension}' files is not supported yet")
    # Run command.
    if cmd is not None:
        _LOG.info("%s", cmd)
        hsystem.system(cmd, suppress_output=False)
