#!/usr/bin/env python
"""
jackdoc: Locate input from Markdown files in the docs directory
    and generate corresponding file links.
Example usage:
jackdoc "search_term" [--skip-toc] [--line-only] [--subdir <subdirectory>]
"""
import argparse
import logging
import os
import re
import subprocess
from typing import List, Optional, Tuple

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

# Define the relative path to the docs directory.
DOCS_DIR = "docs"


def _get_github_info() -> Tuple[str, str]:
    """
    Get GitHub repository information.

    :return: list of tuples containing the file path and the found item
        reference
    """
    try:
        # Get the remote URL of the git repository.
        remote_url = (
            subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"]
            )
            .decode()
            .strip()
        )
        # Extract username and repository name from the remote URL.
        match = re.match(r"^https://github.com/(.*)/(.*)\.git$", remote_url)
        if match:
            username = match.group(1)
            repo = match.group(2)
            return username, repo
    except (subprocess.CalledProcessError, IndexError) as exc:
        raise RuntimeError(
            "Unable to get remote URL from git configuration"
        ) from exc
    raise ValueError("Not a GitHub repository")


def _remove_toc(content: str) -> str:
    """
    Remove table of contents (TOC) from Markdown content.

    :param content: the markdown content from which TOC needs to be
        removed
    :return: the markdown content with TOC removed
    """
    toc_pattern = r"<!--\s*toc\s*-->(.*?)<!--\s*tocstop\s*-->"
    toc_match = re.search(toc_pattern, content, flags=re.DOTALL)
    if toc_match:
        toc_content = toc_match.group(1)
        toc_lines = toc_content.split("\n")
        # Find the line numbers of TOC content.
        excluded_lines = {
            content.count(toc_line, 0, toc_match.start(1)) + 1
            for toc_line in toc_lines
        }
        content_lines = content.split("\n")
        # Filter out TOC content from the original content.
        filtered_content = [
            line
            for i, line in enumerate(content_lines, start=1)
            if i not in excluded_lines
        ]
        return "\n".join(filtered_content)
    return content


def _search_in_markdown_files(
    git_root: str,
    search_term: str,
    skip_toc: bool = False,
    line_only: bool = False,
    subdir: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """
    Search for a term in Markdown files.

    :param git_root: the root directory of the git repository
    :param search_term: the term to search in Markdown files
    :param skip_toc: flag indicating whether to skip the table of
        contents (TOC)
    :param line_only: flag indicating whether to search through lines
        only and generate links with line numbers
    :param subdir: subdirectory to search within
    :return: list of tuples containing the file path and the found item
        reference
    """
    found_in_files = []
    # Construct the path to the docs directory.
    docs_path = (
        os.path.join(git_root, DOCS_DIR, subdir)
        if subdir is not None
        else os.path.join(git_root, DOCS_DIR)
    )
    # Check if the `docs_path` exists.
    hdbg.dassert_dir_exists(docs_path)

    def search_content(content: str) -> List[Tuple[str, str]]:
        """
        Search for the term in content.

        :param content: the content to search for the term
        :return: list of tuples containing the file path and the found
            item reference
        """
        if skip_toc:
            # Remove Table of Contents from the content if specified.
            content = _remove_toc(content)
        if line_only:
            # Search for the term in each line of the content.
            return [
                (md_file, str(line_num))
                for line_num, line in enumerate(content.split("\n"), start=1)
                if re.search(search_term, line)
            ]
        # Search for the term in section headers.
        sections = re.findall(r"^#+\s+(.*)$", content, flags=re.MULTILINE)
        return [
            (md_file, section)
            for section in sections
            if re.search(search_term, section)
        ]

    # Recursively walk through the docs directory.
    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith(".md"):
                md_file = os.path.join(root, file)
                content = hio.from_file(md_file)
                # Search for the term in each markdown file.
                found_in_files.extend(search_content(content))
    return found_in_files


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(args.log_level)
    # Get the root directory of the git repository.
    git_root = hgit.get_client_root(super_module=True)
    # Get GitHub repository information.
    username, repo = _get_github_info()
    # Search for the term in markdown files.
    found_items = _search_in_markdown_files(
        git_root, args.search_term, args.skip_toc, args.line_only, args.subdir
    )
    if found_items:
        _LOG.info("Input found in the following items:")
        for item in found_items:
            file_path, item_ref = item
            relative_path = os.path.relpath(file_path, git_root)
            if args.line_only:
                # Generate GitHub URL with line number.
                url = f"https://github.com/{username}/{repo}/blob/master/{relative_path}?plain=1#L{item_ref}"
            else:
                # Generate GitHub URL with section anchor.
                section_name = re.sub(r"[^\w\s-]", "", item_ref)
                section_name = section_name.replace(" ", "-").replace("--", "-")
                section_name = re.sub(r"-+", "-", section_name)
                url = f"https://github.com/{username}/{repo}/blob/master/{relative_path}#{section_name}"
            _LOG.info(url)
    else:
        _LOG.info("Input not found in any Markdown files.")


def _parse() -> argparse.ArgumentParser:
    """
    Parse command-line arguments.

    :return: the argument parser object
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("search_term", help="Term to search in Markdown files")
    parser.add_argument(
        "--skip-toc",
        action="store_true",
        help="Skip search results from the table of contents (TOC)",
    )
    parser.add_argument(
        "--line-only",
        action="store_true",
        help="Search terms through the document and generate links with line numbers",
    )
    parser.add_argument("--subdir", help="Subdirectory to search within")
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
