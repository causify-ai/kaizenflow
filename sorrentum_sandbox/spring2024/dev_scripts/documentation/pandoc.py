#!/usr/bin/env python

"""
Convert a txt file into a PDF / HTML using pandoc.

# From scratch with TOC:
> pandoc.py -a pdf --input ...

# For interactive mode:
> pandoc.py -a pdf --no_cleanup_before --no_cleanup --input ...

# Check that can be compiled:
> pandoc.py -a pdf --no_toc --no_open_pdf --input ...

> pandoc.py --input notes/IN_PROGRESS/math.The_hundred_page_ML_book.Burkov.2019.txt \
        -a pdf --no_cleanup --no_cleanup_before --no_run_latex_again --no_open
"""

# TODO(gp):
#  - clean up the file_ file_out logic and make it a pipeline
#  - factor out the logic from linter.py about actions and use it everywhere


import argparse
import logging
import os
import sys
from typing import Any, List, Tuple

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hopen as hopen
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

_EXEC_DIR_NAME = os.path.abspath(os.path.dirname(sys.argv[0]))

# #############################################################################

_SCRIPT = None


def _system(cmd: str, log_level: int = logging.INFO, **kwargs: Any) -> int:
    if _SCRIPT is not None:
        _SCRIPT.append(cmd)
    rc = hsystem.system(cmd, log_level=log_level, **kwargs)
    return rc  # type: ignore


def _system_to_string(
    cmd: str, log_level: int = logging.INFO, **kwargs: Any
) -> Tuple[int, str]:
    if _SCRIPT is not None:
        _SCRIPT.append(cmd)
    rc, txt = hsystem.system_to_string(cmd, log_level=log_level, **kwargs)
    return rc, txt


# #############################################################################


def _cleanup_before(prefix: str) -> None:
    _LOG.warning("\n%s", hprint.frame("Clean up before", char1="<", char2=">"))
    cmd = "rm -rf %s*" % prefix
    _ = _system(cmd)


def _convert_txt_to_pandoc(curr_path: str, file_: str, prefix: str) -> str:
    _LOG.info("\n%s", hprint.frame("Pre-process markdown", char1="<", char2=">"))
    file1 = file_
    file2 = "%s.no_spaces.txt" % prefix
    cmd = "%s/convert_txt_to_pandoc.py --input %s --output %s" % (
        curr_path,
        file1,
        file2,
    )
    _ = _system(cmd)
    file_ = file2
    return file_


_COMMON_PANDOC_OPTS = [
    "-V geometry:margin=1in",
    "-f markdown",
    "--number-sections",
    # - To change the highlight style
    # https://github.com/jgm/skylighting
    "--highlight-style=tango",
    "-s",
]
# --filter /Users/$USER/src/github/pandocfilters/examples/tikz.py \
# -F /Users/$USER/src/github/pandocfilters/examples/lilypond.py \
# --filter pandoc-imagine


def _run_latex(cmd: str, file_: str) -> None:
    data: Tuple[int, str] = _system_to_string(cmd, abort_on_error=False)
    rc, txt = data
    log_file = file_ + ".latex1.log"
    hio.to_file(log_file, txt)
    if rc != 0:
        txt_as_arr: List[str] = txt.split("\n")
        for i, line in enumerate(txt_as_arr):
            if line.startswith("!"):
                break
        # pylint: disable=undefined-loop-variable
        txt_as_arr = [
            line for i in range(max(i - 10, 0), min(i + 10, len(txt_as_arr)))
        ]
        txt = "\n".join(txt_as_arr)
        _LOG.error(txt)
        _LOG.error("Log is in %s", log_file)
        _LOG.error("\n%s", hprint.frame("cmd is:\n> %s" % cmd))
        raise RuntimeError("Latex failed")


def _run_pandoc_to_pdf(
    args: argparse.Namespace, curr_path: str, file_: str, prefix: str
) -> str:
    _LOG.info("\n%s", hprint.frame("Pandoc to pdf", char1="<", char2=">"))
    #
    file1 = file_
    cmd = []
    cmd.append("pandoc %s" % file1)
    cmd.extend(_COMMON_PANDOC_OPTS[:])
    #
    cmd.append("-t latex")
    template = "%s/pandoc.latex" % curr_path
    hdbg.dassert_path_exists(template)
    cmd.append("--template %s" % template)
    cmd.append("--filter pandoc-plantuml")
    #
    file2 = "%s.tex" % prefix
    cmd.append("-o %s" % file2)
    if not args.no_toc:
        cmd.append("--toc")
        cmd.append("--toc-depth 2")
    else:
        args.no_run_latex_again = True
    # Doesn't work
    # -f markdown+raw_tex
    cmd = " ".join(cmd)
    _ = _system(cmd, suppress_output=False)
    file_ = file2
    #
    # Run latex.
    #
    _LOG.info("\n%s", hprint.frame("Latex", char1="<", char2=">"))
    # pdflatex needs to run in the same dir of latex_abbrevs.sty so we
    # cd to that dir and save the output in the same dir of the input.
    hdbg.dassert_path_exists(_EXEC_DIR_NAME + "/latex_abbrevs.sty")
    cmd = "cd %s; " % _EXEC_DIR_NAME
    cmd += (
        "pdflatex"
        + " -interaction=nonstopmode"
        + " -halt-on-error"
        + " -shell-escape"
        + " -output-directory %s" % os.path.dirname(file_)
        + " %s" % file_
    )

    _run_latex(cmd, file_)
    # Run latex again.
    _LOG.info("\n%s", hprint.frame("Latex again", char1="<", char2=">"))
    if not args.no_run_latex_again:
        _run_latex(cmd, file_)
    else:
        _LOG.warning("Skipping: run latex again")
    #
    file_out = file_.replace(".tex", ".pdf")
    _LOG.debug("file_out=%s", file_out)
    hdbg.dassert_path_exists(file_out)
    return file_out


def _run_pandoc_to_html(
    args: argparse.Namespace, file_in: str, prefix: str
) -> str:
    _LOG.info("\n%s", hprint.frame("Pandoc to html", char1="<", char2=">"))
    #
    cmd = []
    cmd.append("pandoc %s" % file_in)
    cmd.extend(_COMMON_PANDOC_OPTS[:])
    cmd.append("-t html")
    cmd.append("--metadata pagetitle='%s'" % os.path.basename(file_in))
    #
    file2 = "%s.html" % prefix
    cmd.append("-o %s" % file2)
    if not args.no_toc:
        cmd.append("--toc")
        cmd.append("--toc-depth 2")
    cmd = " ".join(cmd)
    _ = _system(cmd, suppress_output=False)
    #
    file_out = os.path.abspath(file2.replace(".tex", ".html"))
    _LOG.debug("file_out=%s", file_out)
    hdbg.dassert_path_exists(file_out)
    return file_out


def _copy_to_output(args: argparse.Namespace, file_in: str, prefix: str) -> str:
    if args.output is not None:
        _LOG.debug("Using file_out from command line")
        file_out = args.output
    else:
        _LOG.debug("Leaving file_out in the tmp dir")
        file_out = "%s.%s.%s" % (
            prefix,
            os.path.basename(args.input),
            args.type,
        )
    _LOG.debug("file_out=%s", file_out)
    cmd = r"\cp -af %s %s" % (file_in, file_out)
    _ = _system(cmd)
    return file_out  # type: ignore


def _copy_to_gdrive(args: argparse.Namespace, file_name: str, ext: str) -> None:
    _LOG.info("\n%s", hprint.frame("Copy to gdrive", char1="<", char2=">"))
    hdbg.dassert(not ext.startswith("."), "Invalid file_name='%s'", file_name)
    if args.gdrive_dir is not None:
        gdrive_dir = args.gdrive_dir
    else:
        gdrive_dir = "/Users/saggese/GoogleDrive/pdf_notes"
    # Copy.
    hdbg.dassert_dir_exists(gdrive_dir)
    _LOG.debug("gdrive_dir=%s", gdrive_dir)
    basename = os.path.basename(args.input).replace(".txt", "." + ext)
    _LOG.debug("basename=%s", basename)
    dst_file = os.path.join(gdrive_dir, basename)
    cmd = r"\cp -af %s %s" % (file_name, dst_file)
    _ = _system(cmd)
    _LOG.debug("Saved file='%s' to gdrive", dst_file)


def _cleanup_after(prefix: str) -> None:
    _LOG.info("\n%s", hprint.frame("Clean up after", char1="<", char2=">"))
    cmd = "rm -rf %s*" % prefix
    _ = _system(cmd)


# #############################################################################


def _pandoc(args: argparse.Namespace) -> None:
    #
    _LOG.info("type=%s", args.type)
    # Print actions.
    actions = hparser.select_actions(args, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    add_frame = True
    actions_as_str = hparser.actions_to_string(actions, _VALID_ACTIONS, add_frame)
    _LOG.info("\n%s", actions_as_str)
    #
    curr_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    _LOG.debug("curr_path=%s", curr_path)
    #
    if args.script:
        _LOG.info("Logging the actions into a script")
        global _SCRIPT
        _SCRIPT = ["#/bin/bash -xe"]
    #
    file_ = args.input
    hdbg.dassert_path_exists(file_)
    prefix = args.tmp_dir + "/tmp.pandoc"
    prefix = os.path.abspath(prefix)
    #
    action = "cleanup_before"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        _cleanup_before(prefix)
    #
    action = "convert_txt_to_pandoc"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        file_ = _convert_txt_to_pandoc(curr_path, file_, prefix)
    #
    action = "run_pandoc"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        if args.type == "pdf":
            file_out = _run_pandoc_to_pdf(args, curr_path, file_, prefix)
        elif args.type == "html":
            file_out = _run_pandoc_to_html(args, file_, prefix)
        else:
            raise ValueError("Invalid type='%s'" % args.type)
    file_in = file_out
    file_final = _copy_to_output(args, file_in, prefix)
    #
    action = "copy_to_gdrive"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        ext = args.type
        _copy_to_gdrive(args, file_final, ext)
    #
    action = "open"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        hopen.open_file(file_final)
    #
    action = "cleanup_after"
    to_execute, actions = hparser.mark_action(action, actions)
    if to_execute:
        _cleanup_after(prefix)
    # Save script, if needed.
    if args.script:
        txt = "\n".join(_SCRIPT)
        hio.to_file(args.script, txt)
        _LOG.info("Saved script into '%s'", args.script)
    # Check that everything was executed.
    if actions:
        _LOG.error("actions=%s were not processed", str(actions))
    _LOG.info("\n%s", hprint.frame("SUCCESS"))


# #############################################################################

_VALID_ACTIONS = [
    "cleanup_before",
    "convert_txt_to_pandoc",
    "run_pandoc",
    "copy_to_gdrive",
    "open",
    "cleanup_after",
]


_DEFAULT_ACTIONS = _VALID_ACTIONS[:]


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-i", "--input", action="store", type=str, required=True)
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        type=str,
        default=None,
        help="Output file",
    )
    parser.add_argument(
        "--tmp_dir",
        action="store",
        type=str,
        default=".",
        help="Directory where to save artifacts",
    )
    parser.add_argument(
        "-t", "--type", required=True, choices=["pdf", "html"], action="store"
    )
    parser.add_argument(
        "--script", action="store", help="Bash script to generate"
    )
    parser.add_argument("--no_toc", action="store_true", default=False)
    parser.add_argument(
        "--no_run_latex_again", action="store_true", default=False
    )
    parser.add_argument(
        "--gdrive_dir",
        action="store",
        default=None,
        help="Directory where to save the output",
    )
    hparser.add_action_arg(parser, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    cmd_line = " ".join(map(str, sys.argv))
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _LOG.info("cmd line=%s", cmd_line)
    _pandoc(args)


if __name__ == "__main__":
    _main(_parse())
