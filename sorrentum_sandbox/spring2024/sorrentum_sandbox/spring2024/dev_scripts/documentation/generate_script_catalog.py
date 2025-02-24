#!/usr/bin/env python

"""
Generate a markdown file with the docstring for any script in the repo.

> generate_script_catalog.py
"""

import argparse
import logging
import os

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _get_docstring(file_name):
    _LOG.debug("file_name=%s", file_name)
    txt = hio.from_file(file_name).split("\n")
    docstring = []
    found = False
    for line in txt:
        # _LOG.debug("%s: line='%s'", found, line)
        if any(line.startswith(c) for c in ['"""', '# """', 'r"""']):
            # _LOG.debug("-> Found")
            if not found:
                found = True
                continue
            # Done.
            break
        if found:
            if line.startswith("# "):
                line = line.replace("# ", "")
            docstring.append(line)
    docstring_as_str = "\n".join(docstring)
    _LOG.debug("docstring=%s", docstring_as_str)
    return docstring_as_str


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src_dir", action="store", default=".")
    parser.add_argument("--src_file", action="store", default=None)
    parser.add_argument(
        "--dst_file",
        action="store",
        default="docs/kaizenflow/ck.script_catalog.reference.md",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    # Get the files.
    cmd = "find %s -perm +111 -type f" % args.src_dir
    _, output = hsystem.system_to_string(cmd)
    file_names = output.split("\n")
    file_names = sorted(file_names)
    file_names = [
        f for f in file_names if not os.path.basename(f).startswith("tmp")
    ]
    if args.src_file is not None:
        file_names = [args.src_file]
    # file_names = ["dev_scripts/git/gb"]
    # file_names = ["./dev_scripts/_setenv_amp.py"]
    _LOG.info("Files selected: %d", len(file_names))
    num_docstring = 0
    res = {}
    for file_name in file_names:
        docstring = _get_docstring(file_name)
        res[file_name] = docstring
        if docstring:
            num_docstring += 1
    # Compose the catalog.
    last_dir = curr_dir = None
    md_text = []
    # Order by level of directory.
    ordered_file_names = sorted(res.keys(), key=lambda x: len(x.split("/")))
    for file_name in ordered_file_names:
        _LOG.debug(
            "file_name=%s curr_dir=%s last_dir=%s", file_name, curr_dir, last_dir
        )
        docstring = res[file_name]
        file_name = file_name.replace("./", "")
        curr_dir = os.path.dirname(file_name)
        if last_dir is None or last_dir != curr_dir:
            md_text.append("\n# `%s`\n" % curr_dir)
            last_dir = curr_dir
        md_text.append("\n***%s***\n" % file_name)
        if docstring:
            md_text.append("```\n%s\n```" % docstring)
    # Save in a file.
    md_text_as_str = "\n".join(md_text)
    hio.to_file(args.dst_file, md_text_as_str)
    _LOG.info("File '%s' saved", args.dst_file)
    _LOG.info(
        "Number of scripts with docstring: %s",
        hprint.perc(num_docstring, len(res)),
    )
    # Format the md.
    _LOG.info("Formatting")
    cmd = "linter.py -f %s" % args.dst_file
    hsystem.system(cmd)


if __name__ == "__main__":
    _main(_parse())
