#!/usr/bin/env python

"""
Convert a txt file into markdown suitable for pandoc.py.

E.g.,
- convert the text in pandoc / latex format
- handle banners around chapters
- handle comments

Import as:

import dev_scripts.documentation.convert_txt_to_pandoc as dsdcttpa
"""

# TODO(gp):
#  - Add spaces between lines
#  - Add index counting the indices
#  - Convert // comments in code into #
#  - Fix /* and */

import argparse
import logging
import re
from typing import List, Tuple

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

_NUM_SPACES = 2


def _process_comment_block(line: str, in_skip_block: bool) -> Tuple[bool, bool]:
    # TODO: improve the comment handling, handle also \* *\ and %.
    do_continue = False
    if line.startswith(r"<!--") or re.search(r"^\s*\/\*", line):
        hdbg.dassert(not in_skip_block)
        # Start skipping comments.
        in_skip_block = True
    if in_skip_block:
        if line.endswith(r"-->") or re.search(r"^\s*\*\/", line):
            # End skipping comments.
            in_skip_block = False
        # Skip comment.
        _LOG.debug("  -> skip")
        do_continue = True
    return do_continue, in_skip_block


def _process_code_block(
    line: str, in_code_block: bool, i: int, lines: List[str]
) -> Tuple[bool, bool, List[str]]:
    out: List[str] = []
    do_continue = False
    if re.match(r"^(\s*)```", line):
        _LOG.debug("  -> code block")
        in_code_block = not in_code_block
        # Add empty line.
        if (
            in_code_block
            and (i + 1 < len(lines))
            and re.match(r"\s*", lines[i + 1])
        ):
            out.append("\n")
        out.append("    " + line)
        if (
            not in_code_block
            and (i + 1 < len(lines))
            and re.match(r"\s*", lines[i + 1])
        ):
            out.append("\n")
        do_continue = True
        return do_continue, in_code_block, out
    if in_code_block:
        line = line.replace("// ", "# ")
        out.append("    " + line)
        # We don't do any of the other post-processing.
        do_continue = True
        return do_continue, in_code_block, out
    return do_continue, in_code_block, out


def _process_single_line_comment(line: str) -> bool:
    """
    Handle single line comment.

    We need to do it after the // in code blocks have been handled.
    """
    do_continue = False
    if line.startswith(r"%%") or line.startswith(r"//"):
        do_continue = True
        _LOG.debug("  -> do_continue=True")
        return do_continue
    # Skip frame.
    if (
        re.match(r"\#+ -----", line)
        or re.match(r"\#+ \#\#\#\#\#", line)
        or re.match(r"\#+ =====", line)
        or re.match(r"\#+ \/\/\/\/\/", line)
    ):
        do_continue = True
        _LOG.debug("  -> do_continue=True")
        return do_continue
    # Nothing to do.
    return do_continue


def _process_abbreviations(in_line: str) -> str:
    r"""
    Transform
        - `->` into `$\rightarrow`
    """
    line = in_line
    for x, y in [
        (r"=>", r"\implies"),
        (r"->", r"\rightarrow"),
        (r"-^", r"\uparrow"),
        (r"-v", r"\downarrow"),
    ]:
        line = re.sub(
            r"(\s)%s(\s)" % re.escape(x), r"\1$%s$\2" % re.escape(y), line
        )
    if line != in_line:
        _LOG.debug("    -> line=%s", line)
    return line


def _process_question(line: str) -> Tuple[bool, str]:
    """
    Transform `* foo bar` into `- **foo bar**`.
    """
    # Bold.
    meta = "**"
    # Bold + italic: meta = "_**"
    # Underline (not working): meta = "__"
    # Italic: meta = "_"
    do_continue = False
    regex = r"^(\*|\*\*|\*:)(\s+)(\S.*)\s*$"
    m = re.search(regex, line)
    if m:
        line = "-%s%s%s%s" % (m.group(2), meta, m.group(3), meta)
        do_continue = True
    return do_continue, line


def _transform(lines: List[str]) -> List[str]:
    out: List[str] = []
    # True inside a block to skip.
    in_skip_block = False
    # True inside a code block.
    in_code_block = False
    for i, line in enumerate(lines):
        _LOG.debug("%s:line=%s", i, line)
        # Process comment block.
        do_continue, in_skip_block = _process_comment_block(line, in_skip_block)
        # _LOG.debug("  -> do_continue=%s in_skip_block=%s", do_continue, in_skip_block)
        if do_continue:
            continue
        # Process code block.
        do_continue, in_code_block, out_tmp = _process_code_block(
            line, in_code_block, i, lines
        )
        out.extend(out_tmp)
        if do_continue:
            continue
        # Process single line comment.
        do_continue = _process_single_line_comment(line)
        if do_continue:
            continue
        # Process abbreviations.
        line = _process_abbreviations(line)
        # Process question.
        do_continue, line = _process_question(line)
        if do_continue:
            out.append(line)
            continue
        # Process empty lines in the questions and answers.
        is_empty = line.rstrip(" ").lstrip(" ") == ""
        if not is_empty:
            if line.startswith("#"):
                # It's a chapter.
                out.append(line)
            else:
                # It's a line in an answer.
                out.append(" " * _NUM_SPACES + line)
        else:
            # Empty line.
            prev_line_is_verbatim = ((i - 1) > 0) and lines[i - 1].startswith(
                "```"
            )
            next_line_is_verbatim = ((i + 1) < len(lines)) and (
                lines[i + 1].startswith("```")
            )
            # The next line has a chapter or the start of a new note.
            next_line_is_chapter = ((i + 1) < len(lines)) and (
                lines[i + 1].startswith("#") or lines[i + 1].startswith("* ")
            )
            _LOG.debug(
                "  is_empty=%s prev_line_is_verbatim=%s next_line_is_chapter=%s",
                is_empty,
                prev_line_is_verbatim,
                next_line_is_chapter,
            )
            if (
                next_line_is_chapter
                or prev_line_is_verbatim
                or next_line_is_verbatim
            ):
                out.append(" " * _NUM_SPACES + line)
    # - Clean up.
    # Remove all the lines with only spaces.
    out_tmp = []
    for line in out:
        if re.search(r"^\s+$", line):
            line = ""
        out_tmp.append(line)
    out = out_tmp
    return out


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", action="store", type=str, required=True)
    parser.add_argument("--output", action="store", type=str, default=None)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _LOG.info("cmd line=%s", hdbg.get_command_line())
    # Slurp file.
    lines = hio.from_file(args.input).split("\n")
    lines = [l.rstrip("\n") for l in lines]
    out: List[str] = []
    # Add some directive for pandoc.
    out.append(r"""\let\emph\textit""")
    out.append(r"""\let\uline\underline""")
    out.append(r"""\let\ul\underline""")
    #
    out_tmp = _transform(lines)
    out.extend(out_tmp)
    # Print result.
    txt = "\n".join(out)
    hio.to_file(args.output, txt)


if __name__ == "__main__":
    _main(_parse())
