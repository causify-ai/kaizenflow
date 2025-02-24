#!/usr/bin/env python

"""
Import as:

import dev_scripts.compile_all as dsccoall
"""

import compileall
import re

# find . -type f -name '*.py' | xargs -t -n1 python3 -m py_compile
compileall.compile_dir(
    ".",
    force=True,
    quiet=0,
    # Skip .git, tmp dirs, venv dirs.
    rx=re.compile(r"(\.git/|tmp\.|/venv/)"),
)
