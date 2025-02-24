#!/usr/bin/env python
"""
Import as:

import dev_scripts.old.linter.process_jupytext as dsolprju
"""

# pylint: disable=line-too-long
r"""
Automate some common workflows with jupytext.

> find . -name "*.ipynb" | grep -v ipynb_checkpoints | head -3 | xargs -t -L 1 process_jupytext.py --action sync --file

# Pair
> process_jupytext.py -f im.kibot/data_exploratory_analysis.ipynb --action pair

# Test
> process_jupytext.py -f im.kibot/data_exploratory_analysis.ipynb --action test
> process_jupytext.py -f im.kibot/data_exploratory_analysis.ipynb --action test_strict

# Sync
> process_jupytext.py -f im.kibot/data_exploratory_analysis.ipynb --action sync
"""
# pylint: enable=line-too-long

import argparse
import logging
import re

import dev_scripts.linter as lin
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################

_EXECUTABLE = "jupytext"


def _pair(file_name: str) -> None:
    hdbg.dassert(
        lin.is_ipynb_file(file_name), "'%s' has no .ipynb extension", file_name
    )
    if lin.is_paired_jupytext_file(file_name):
        _LOG.warning("The file '%s' seems already paired", file_name)
    # It is a ipynb and it is unpaired: create the python file.
    msg = (
        "There was no paired notebook for '%s': created and added to git"
        % file_name
    )
    _LOG.warning(msg)
    # Convert a notebook into jupytext.
    cmd = []
    cmd.append(_EXECUTABLE)
    cmd.append("--update-metadata")
    cmd.append("""'{"jupytext":{"formats":"ipynb,py:percent"}}'""")
    cmd.append(file_name)
    cmd = " ".join(cmd)
    hsystem.system(cmd)
    # Test the ipynb -> py:percent -> ipynb round trip conversion.
    cmd = _EXECUTABLE + " --test --stop --to py:percent %s" % file_name
    hsystem.system(cmd)
    # Add the .py file.
    cmd = _EXECUTABLE + " --to py:percent %s" % file_name
    hsystem.system(cmd)
    # Add to git.
    py_file_name = lin.from_ipynb_to_python_file(file_name)
    cmd = "git add %s" % py_file_name
    hsystem.system(cmd)


def _sync(file_name: str) -> None:
    if lin.is_paired_jupytext_file(file_name):
        # cmd = _EXECUTABLE + " --sync --update --to py:percent %s" % file_name
        cmd = _EXECUTABLE + " --sync --to py:percent %s" % file_name
        hsystem.system(cmd)
    else:
        _LOG.warning("The file '%s' is not paired: run --pair", file_name)


def _is_jupytext_version_different(output_txt: str) -> bool:
    """
    Return True if was a difference in jupytext_version.

    Workaround for https://github.com/mwouts/jupytext/issues/414 to avoid
    report an error due to jupytext version mismatch.

    [jupytext] Reading nlp/notebooks/PTask1081_RP_small_test.py
    nlp/notebooks/PTask1081_RP_small_test.py:
    --- expected
    +++ actual
    @@ -5,7 +5,7 @@
     #       extension: .py
     #       format_name: percent
     #       format_version: '1.3'
    -#       jupytext_version: 1.3.3
    +#       jupytext_version: 1.3.0
     #   kernelspec:
     #     display_name: Python [conda env:.conda-develop] *
     #     language: python
    """
    ret = False
    regex = r"jupytext_version: \d.*"
    m = re.findall(regex, output_txt, re.MULTILINE)
    _LOG.debug("Regex search result: %s", m)
    if m:
        if len(m) == 2:
            ret = True
            _LOG.warning(
                "There is a mismatch of jupytext version: '%s' vs '%s': skipping",
                m[0],
                m[1],
            )
    return ret


def _test(file_name: str, action: str) -> None:
    if action == "test":
        opts = "--test"
    elif action == "test_strict":
        opts = "--test-strict"
    else:
        raise ValueError("Invalid action='%s'" % action)
    cmd = [_EXECUTABLE, opts, "--stop --to py:percent %s" % file_name]
    cmd = " ".join(cmd)
    rc, txt = hsystem.system_to_string(cmd, abort_on_error=False)
    if rc != 0:
        # Here we handle special cases that must be escaped.
        _LOG.debug("rc=%s, txt=\n'%s'", rc, txt)
        if _is_jupytext_version_different(txt):
            pass
        else:
            raise RuntimeError(txt)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        type=str,
        required=True,
        help="File to process",
    )
    parser.add_argument(
        "--action",
        action="store",
        choices=["pair", "test", "test_strict", "sync"],
        required=True,
        help="Action to perform",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    #
    file_name = args.file
    hdbg.dassert_path_exists(file_name)
    if args.action == "pair":
        _pair(file_name)
    elif args.action == "sync":
        _sync(file_name)
    elif args.action in ("test", "test_strict"):
        _test(file_name, args.action)
    else:
        raise ValueError("Invalid action '%s'" % args.action)


if __name__ == "__main__":
    _main(_parse())
