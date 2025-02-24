#!/usr/bin/env python

"""
Add a table of contents to an IPython Notebook file.

See full description and instructions at
`docs/work_tools/all.add_toc_to_notebook.how_to_guide.md`.
"""

import argparse
import json
import logging
import os
import re

import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def add_toc(file_name: str) -> dict:
    """
    Add a table of contents to the first cell in an IPython Notebook file.

    :param file_name: the name of the file
    :return: the updated contents of the file
    """
    with open(file_name, mode="r", encoding="utf-8") as f:
        file_contents: dict = json.load(f)
    _LOG.debug("Opened %s", file_name)
    # Collect headings from the file.
    # A heading starts at the beginning of a line and consists of one or
    # more hash signs, followed by at least one whitespace and then the
    # heading text, e.g. "# First heading", "## Second-level heading".
    _LOG.debug("Collecting headings from the notebook...")
    heading_structure_regex = r"^(#+)\s(.+)"
    headings = []
    for i, cell in enumerate(file_contents["cells"]):
        if cell["cell_type"] != "markdown":
            # Only check Markdown-type cells.
            continue
        anchors = []
        for line in cell["source"]:
            # Extract the level and text of the heading, if present.
            heading_structure = re.findall(heading_structure_regex, line.strip())
            if not heading_structure:
                continue
            _LOG.debug("Extracted %s", heading_structure)
            level, heading_text = heading_structure[0]
            # Store an anchor to add to the cell for navigation.
            heading_link = heading_text.lower().replace(" ", "-")
            anchor = f"<a name='{heading_link}'></a>\n"
            anchors.append(anchor)
            # Store the heading information.
            headings.append((level, heading_text, heading_link))
        upd_cell_content = cell["source"]
        for anchor in anchors:
            if anchor not in upd_cell_content:
                # Add the anchor to the cell.
                upd_cell_content = [anchor] + upd_cell_content
                _LOG.debug("Added an anchor to the cell: %s", anchor)
        file_contents["cells"][i]["source"] = upd_cell_content
    # Create a table of contents.
    _LOG.debug("Creating a table of contents...")
    first_toc_line = "CONTENTS:\n"
    toc = [first_toc_line]
    for i, heading in enumerate(headings):
        level, heading_text, heading_link = heading
        # Compose a line to add to the TOC; e.g.,
        # "# First heading" becomes "- [First heading](#first-heading)\n".
        indent = (level.count("#") - 1) * (2 * " ")
        toc_line = f"{indent}- [{heading_text}](#{heading_link})"
        if i != len(headings) - 1:
            toc_line += "\n"
        toc.append(toc_line)
        _LOG.debug("Added a TOC line: %s", toc_line)
    # Create a cell with the table of contents.
    toc_cell = {
        "cell_type": "markdown",
        "metadata": {},
        "source": toc,
    }
    #
    cur_first_cell = file_contents["cells"][0]
    if (
        cur_first_cell["cell_type"] == "markdown"
        and cur_first_cell["source"][0] == first_toc_line
    ):
        # Replace the table of contents from the first cell.
        file_contents["cells"][0] = toc_cell
        _LOG.debug(
            "Replaced the TOC in the first cell with the new one: %s", toc_cell
        )
    else:
        # Add the cell with the table of contents to the beginning of the file.
        file_contents["cells"] = [toc_cell] + file_contents["cells"]
        _LOG.debug("Added a cell with the TOC to the beginning: %s", toc_cell)
    with open(file_name, mode="w", encoding="utf-8") as f:
        # Re-write the original file.
        json.dump(file_contents, f, indent=4)
    _LOG.debug("File %s is updated with the new TOC", file_name)
    return file_contents


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input_files",
        action="append",
        help="Ipynb files to add a TOC to",
    )
    group.add_argument(
        "--input_dir",
        action="store",
        help="Directory where all ipynb files should get a TOC",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    # Get the ipynb files to add a TOC to.
    if args.input_files:
        files_to_process = []
        for input_file in args.input_files:
            hdbg.dassert_path_exists(input_file)
            hdbg.dassert_file_extension(input_file, ".ipynb")
            files_to_process.append(input_file)
    elif args.input_dir:
        hdbg.dassert_dir_exists(args.input_dir)
        files_to_process = [
            os.path.join(dp, f)
            for dp, dn, fn in os.walk(args.input_dir)
            for f in fn
            if f.endswith(".ipynb")
        ]
    else:
        hdbg.dfatal("You need to choose files or a dir to process")
    # Run.
    for file_name in files_to_process:
        _ = add_toc(file_name)


if __name__ == "__main__":
    _main(_parse())
