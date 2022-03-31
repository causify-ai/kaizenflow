#!/usr/bin/env python

"""
Lint md files.

> lint_txt.py -i foo.md -o bar.md

It can be used in vim to prettify a part of the text using stdin / stdout.
:%!lint_txt.py
"""

# TODO(gp): -> lint_md.py

import argparse
import logging
import os
import re
import sys
import tempfile
from typing import List, Optional

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################

# TODO(gp): Implement these replacements for `.txt`.
#  us -> you
#  ours -> yours
#  ourselves -> yourself


def _preprocess(txt: str) -> str:
    _LOG.debug("txt=%s", txt)
    # Remove some artifacts when copying from gdoc.
    txt = re.sub(r"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", "'", txt)
    txt = re.sub(r"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", '"', txt)
    txt = re.sub(r"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", '"', txt)
    txt = re.sub(r"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¦", "...", txt)
    txt_new: List[str] = []
    for line in txt.split("\n"):
        # Skip frames.
        if re.match(r"#+ [#\/\-\=]{6,}$", line):
            continue
        line = re.sub(r"^\s*\*\s+", "- STAR", line)
        line = re.sub(r"^\s*\*\*\s+", "- SSTAR", line)
        # Transform:
        # $$E_{in} = \frac{1}{N} \sum_i e(h(\vx_i), y_i)$$
        #
        # $$E_{in}(\vw) = \frac{1}{N} \sum_i \big(
        # -y_i \log(\Pr(h(\vx) = 1|\vx)) - (1 - y_i) \log(1 - \Pr(h(\vx)=1|\vx))
        # \big)$$
        #
        # $$
        if re.search(r"^\s*\$\$\s*$", line):
            txt_new.append(line)
            continue
        # $$ ... $$
        m = re.search(r"^(\s*)(\$\$)(.+)(\$\$)\s*$", line)
        if m:
            for i in range(3):
                txt_new.append(m.group(1) + m.group(2 + i))
            continue
        # ... $$
        m = re.search(r"^(\s*)(\$\$)(.+)$", line)
        if m:
            for i in range(2):
                txt_new.append(m.group(1) + m.group(2 + i))
            continue
        # $$ ...
        m = re.search(r"^(\s*)(.*)(\$\$)$", line)
        if m:
            for i in range(2):
                txt_new.append(m.group(1) + m.group(2 + i))
            continue
        txt_new.append(line)
    txt_new_as_str = "\n".join(txt_new)
    # Replace multiple empty lines with one, to avoid prettier to start using
    # `*` instead of `-`.
    txt_new_as_str = re.sub(r"\n\s*\n", "\n\n", txt_new_as_str)
    #
    _LOG.debug("txt_new_as_str=%s", txt_new_as_str)
    return txt_new_as_str


def _prettier(txt: str, print_width: Optional[int] = None) -> str:
    _LOG.debug("txt=\n%s", txt)
    #
    debug = False
    if not debug:
        tmp_file_name = tempfile.NamedTemporaryFile().name
    else:
        tmp_file_name = "/tmp/tmp_prettier.txt"
    hio.to_file(tmp_file_name, txt)
    #
    executable = "prettier"
    cmd: List[str] = []
    cmd.append(executable)
    cmd.append("--parser markdown")
    cmd.append("--prose-wrap always")
    cmd.append("--write")
    tab_width = 2
    cmd.append("--tab-width %s" % tab_width)
    if print_width is not None:
        hdbg.dassert_lte(1, print_width)
        cmd.append("--print-width %s" % print_width)
    if True:
        # Workaround for PTask2155.
        cmd.insert(0, "cd %s &&" % os.path.dirname(tmp_file_name))
        cmd.append(os.path.basename(tmp_file_name))
    else:
        cmd.append(tmp_file_name)
    # cmd.append("2>&1 >/dev/null")
    cmd_as_str = " ".join(cmd)
    _, output_tmp = hsystem.system_to_string(cmd_as_str, abort_on_error=True)
    _LOG.debug("output_tmp=%s", output_tmp)
    #
    txt = hio.from_file(tmp_file_name)
    _LOG.debug("After prettier txt=\n%s", txt)
    return txt  # type: ignore


def _postprocess(txt: str, in_file_name: str) -> str:
    _LOG.debug("txt=%s", txt)
    # Remove empty lines before ```.
    txt = re.sub(r"^\s*\n(\s*```)$", r"\1", txt, 0, flags=re.MULTILINE)
    # Remove empty lines before higher level bullets, but not chapters.
    txt = re.sub(r"^\s*\n(\s+-\s+.*)$", r"\1", txt, 0, flags=re.MULTILINE)
    # True if one is in inside a ``` .... ``` block.
    in_triple_tick_block: bool = False
    txt_new: List[str] = []
    for i, line in enumerate(txt.split("\n")):
        # Undo the transformation `* -> STAR`.
        line = re.sub(r"^\-(\s*)STAR", r"*\1", line, 0)
        line = re.sub(r"^\-(\s*)SSTAR", r"**\1", line, 0)
        # Remove empty lines.
        line = re.sub(r"^\s*\n(\s*\$\$)", r"\1", line, 0, flags=re.MULTILINE)
        # Handle ``` block.
        m = re.match(r"^\s*```(.*)\s*$", line)
        if m:
            in_triple_tick_block = not in_triple_tick_block
            if in_triple_tick_block:
                tag = m.group(1)
                if not tag:
                    print(
                        "%s:%s: Missing syntax tag in ```" % (in_file_name, i + 1)
                    )
        if not in_triple_tick_block:
            # Upper case for `- hello`.
            m = re.match(r"(\s*-\s+)(\S)(.*)", line)
            if m:
                line = m.group(1) + m.group(2).upper() + m.group(3)
            # Upper case for `\d) hello`.
            m = re.match(r"(\s*\d+[\)\.]\s+)(\S)(.*)", line)
            if m:
                line = m.group(1) + m.group(2).upper() + m.group(3)
        #
        txt_new.append(line)
    if in_triple_tick_block:
        print("%s:%s: A ``` block was not ending" % (in_file_name, 1))
    txt_new_as_str = "\n".join(txt_new)
    return txt_new_as_str


def _frame_chapters(txt: str, max_lev: int = 4) -> str:
    """
    Add the frame around each chapter.
    """
    txt_new: List[str] = []
    # _LOG.debug("txt=%s", txt)
    for i, line in enumerate(txt.split("\n")):
        _LOG.debug("line=%d:%s", i, line)
        m = re.match(r"^(\#+) ", line)
        txt_processed = False
        if m:
            comment = m.group(1)
            lev = len(comment)
            _LOG.debug("  -> lev=%s", lev)
            if lev < max_lev:
                sep = comment + " " + "#" * (80 - 1 - len(comment))
                txt_new.append(sep)
                txt_new.append(line)
                txt_new.append(sep)
                txt_processed = True
            else:
                _LOG.debug(
                    "  -> Skip formatting the chapter frame: lev=%d, "
                    "max_lev=%d",
                    lev,
                    max_lev,
                )
        if not txt_processed:
            txt_new.append(line)
    txt_new_as_str = "\n".join(txt_new).rstrip("\n")
    return txt_new_as_str


def _refresh_toc(txt: str) -> str:
    _LOG.debug("txt=%s", txt)
    # Check whether there is a TOC otherwise add it.
    txt_as_arr = txt.split("\n")
    if txt_as_arr[0] != "<!--ts-->":
        _LOG.warning("No tags for table of content in md file: adding it")
        txt = "<!--ts-->\n<!--te-->\n" + txt
    # Write file.
    tmp_file_name = tempfile.NamedTemporaryFile().name
    hio.to_file(tmp_file_name, txt)
    # Process TOC.
    cmd: List[str] = []
    # Find the script `gh-md-toc`, assuming that it's in the same directory of
    # this script.
    gh_md_toc = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "gh-md-toc"
    )
    hdbg.dassert_path_exists(gh_md_toc)
    cmd.append(gh_md_toc)
    cmd.append("--insert %s" % tmp_file_name)
    cmd_as_str = " ".join(cmd)
    hsystem.system(cmd_as_str, abort_on_error=False, suppress_output=True)
    # Read file.
    txt = hio.from_file(tmp_file_name)
    return txt  # type: ignore


# #############################################################################


def _to_execute_action(action: str, actions: Optional[List[str]] = None) -> bool:
    to_execute = actions is None or action in actions
    if not to_execute:
        _LOG.debug("Skipping %s", action)
    return to_execute


def _process(
    txt: str,
    in_file_name: str,
    actions: Optional[List[str]] = None,
    print_width: Optional[int] = None,
) -> str:
    is_md_file = in_file_name.endswith(".md")
    # Pre-process text.
    action = "preprocess"
    if _to_execute_action(action, actions):
        txt = _preprocess(txt)
    # Prettify.
    action = "prettier"
    if _to_execute_action(action, actions):
        txt = _prettier(txt, print_width=print_width)
    # Post-process text.
    action = "postprocess"
    if _to_execute_action(action, actions):
        txt = _postprocess(txt, in_file_name)
    # Frame chapters.
    action = "frame_chapters"
    if _to_execute_action(action, actions):
        if not is_md_file:
            txt = _frame_chapters(txt)
    # Refresh table of content.
    action = "refresh_toc"
    if _to_execute_action(action, actions):
        if is_md_file:
            txt = _refresh_toc(txt)
    return txt


# #############################################################################

_VALID_ACTIONS = [
    "preprocess",
    "prettier",
    "postprocess",
    "frame_chapters",
    "refresh_toc",
]


_DEFAULT_ACTIONS = _VALID_ACTIONS[:]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-i",
        "--infile",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
    )
    parser.add_argument(
        "-o",
        "--outfile",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
    )
    parser.add_argument(
        "--in_place",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--print-width",
        action="store",
        type=int,
        default=None,
    )
    hparser.add_action_arg(parser, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(args: argparse.Namespace) -> None:
    in_file_name = args.infile.name
    from_stdin = in_file_name == "<stdin>"
    hdbg.init_logger(
        verbosity=args.log_level, use_exec_path=False, force_white=from_stdin
    )
    # Read input.
    _LOG.debug("in_file_name=%s", in_file_name)
    if not from_stdin:
        hdbg.dassert(
            in_file_name.endswith(".txt") or in_file_name.endswith(".md"),
            "Invalid extension for file name '%s'",
            in_file_name,
        )
    txt = args.infile.read()
    # Process.
    txt = _process(
        txt, in_file_name, actions=args.action, print_width=args.print_width
    )
    # Write output.
    if args.in_place:
        hdbg.dassert_ne(in_file_name, "<stdin>")
        hio.to_file(in_file_name, txt)
    else:
        args.outfile.write(txt)


if __name__ == "__main__":
    parser_ = _parser()
    args_ = parser_.parse_args()
    _main(args_)
