#!/usr/bin/env python

"""
Import as:

import dev_scripts.old.create_conda.install.check_develop_packages as dsoccicdp
"""

import os
import sys

import helpers.henv as henv

# Dir of the current executable.
_CURR_DIR = os.path.dirname(sys.argv[0])

# This script is `//amp/dev_scripts/install/check_develop_packages.py`, so we
# need to go up two levels to reach `//amp`.
_AMP_REL_PATH = "../.."
_AMP_PATH = os.path.abspath(os.path.join(_CURR_DIR, _AMP_REL_PATH))
assert os.path.exists(_AMP_PATH), f"Can't find '{_AMP_PATH}'"
sys.path.insert(0, _AMP_PATH)

# pylint: disable=wrong-import-position
import dev_scripts.old.create_conda._bootstrap as dsoccobo  # isort:skip # noqa: E402

dsoccobo.bootstrap(_AMP_REL_PATH)


if __name__ == "__main__":
    txt, failed = henv.get_system_signature()
    print(txt)
    if failed:
        raise RuntimeError("Can't import some libraries")
