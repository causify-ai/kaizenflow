#!/usr/bin/env python

"""
# Replace only:

> scripts/replace_latex.py -a replace --file notes/IN_PROGRESS/finance.portfolio_theory.txt

# Replace and check:
> scripts/replace_latex.py -a pandoc_before -a replace -a pandoc_after --file notes/IN_PROGRESS/finance.portfolio_theory.txt
"""

import argparse
import logging
import re

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


# #############################################################################


def _standard_cleanup(in_file, aggressive):
    # - Always use "you" instead of "one"
    # - Try to make the wording as terse as possible
    # - Always use $\cdot$
    hdbg.dassert_path_exists(in_file)
    txt = hio.from_file(in_file).split("\n")
    out = []
    for line in txt:
        for s, d in [
            ("gaussian", "Gaussian"),
            ("iid", "IID"),
            ("doesn't", "does not"),
            ("can't", "cannot"),
            ("it's", "it is"),
            ("'s", " is"),
            ("they're", "they are"),
            ("isn't", "is not"),
            ("aren't", "are not"),
            ("wrt", "with respect to"),
            ("we", "you"),
            ("one", "you"),
            # \bbR -> \R ?
            # see https://oeis.org/wiki/List_of_LaTeX_mathematical_symbols
        ]:
            # l = l.replace(s, d)
            line = re.sub("\\b" + s + "\\b", d, line)
            line = re.sub("\\b" + s.capitalize() + "\\b", d.capitalize(), line)
        for re1, re2 in [
            # Replace "iff" with "$\iff$" unless it's in a word or it's
            # alread $\iff$.
            (r"\b(?<!\\)iff\b", r"$\\iff$"),
            # (nasdaq -> NASDAQ)
            # \textit{Answer}
            (r"^\\textit{(.*?)}", r"- ___\1___"),
            # (\textit{} -> _ _)
            (r"\\textit{(.*?)}", r"_\1_"),
        ]:
            line = re.sub(re1, re2, line)
        # This can't be automatic, but needs to be verified by hand.
        if aggressive:
            for s, d in [(r"\\d=", r"\\dd=")]:
                line = re.sub("\\b" + s + "\\b", d, line)
                line = re.sub(
                    "\\b" + s.capitalize() + "\\b", d.capitalize(), line
                )

            def _repl_func(m):
                return m.group(1) + m.group(2).upper() + m.group(3)

            line = re.sub(r"^(\s*- )(\S)(.*)", _repl_func, line)
        # Remove spaces at the end of the line.
        line = re.sub(r"\s+$", "", line)
        out.append(line)
    out = "\n".join(out)
    hio.to_file(in_file, out)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-a",
        "--action",
        required=True,
        choices=["checkout", "pandoc_before", "pandoc_after", "replace"],
        action="append",
    )
    parser.add_argument("--file", action="store", type=str, required=True)
    parser.add_argument("--aggressive", action="store_true")
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    hdbg.dassert_path_exists(args.file)
    actions = args.action
    if not isinstance(actions, list):
        actions = list(actions)
    if "checkout" in actions:
        cmd = "git checkout -- %s" % args.file
        _ = hsystem.system(cmd)
    if "pandoc_before" in actions:
        cmd = "pandoc.py -a pdf --no_toc --no_open_pdf --input %s" % args.file
        _ = hsystem.system(cmd)
    if "replace" in actions:
        _standard_cleanup(args.file, args.aggressive)
    if "pandoc_after" in actions:
        cmd = "pandoc.py -a pdf --no_toc --no_open_pdf --input %s" % args.file
        _ = hsystem.system(cmd)


if __name__ == "__main__":
    _main(_parse())
