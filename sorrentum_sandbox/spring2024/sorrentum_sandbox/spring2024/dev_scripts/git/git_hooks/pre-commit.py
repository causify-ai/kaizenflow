#!/usr/bin/env python3
"""
This is a git commit-hook used to check that a commit follows certain
invariants.

In case of violations the script will exit non-zero and abort the
commit. User can ignore the checks with `git commit --no-verify '...'`.

One can run this hook to preview what `git commit` will do:
> pre-commit.py

Import as:

import dev_scripts.git.git_hooks.pre-commit as dsgghpr
"""

# NOTE: This file should depend only on Python standard libraries.
import logging
import sys

import dev_scripts.git.git_hooks.utils as dsgghout

_LOG = logging.getLogger(__name__)


# #############################################################################


if __name__ == "__main__":
    print("# Running git pre-commit hook ...")
    dsgghout.check_master()
    dsgghout.check_author()
    dsgghout.check_file_size()
    dsgghout.check_words()
    dsgghout.check_python_compile()
    print(
        "\n"
        + dsgghout.color_highlight(
            "##### All pre-commit hooks passed: committing ######", "purple"
        )
    )
    sys.exit(0)
