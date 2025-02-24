#!/usr/bin/env python

r"""
Generate and print a bash script that is used to configure the environment for
//amp client.

This script:
- is used to configure the environment
- should have no dependency other than basic python library

Import as:

import dev_scripts.old.create_conda._setenv_amp as dsoccseam
"""

import argparse
import logging
import os
import sys
from typing import List

# Dir of the current executable.
_CURR_DIR = os.path.dirname(sys.argv[0])

# This script is `//amp/dev_scripts/_setenv_amp.py`, so we need to go up one
# levels to reach `//amp`.
_AMP_REL_PATH = ".."
_AMP_PATH = os.path.abspath(os.path.join(_CURR_DIR, _AMP_REL_PATH))
assert os.path.exists(_AMP_PATH), f"Can't find '{_AMP_PATH}'"
sys.path.insert(0, _AMP_PATH)

# This import is relative to the top of the repo.
# pylint: disable=wrong-import-position
import dev_scripts.old.create_conda._bootstrap as dsoccobo  # isort:skip # noqa: E402

# This script is `//amp/dev_scripts/_setenv_amp.py`, so we need ".." to go from
# the position of this executable to `//amp/helpers`.
# pylint: disable=no-member
dsoccobo.bootstrap(_AMP_REL_PATH)

# pylint: disable=wrong-import-position
import helpers.hdbg as hdbg  # isort:skip # noqa: E402
import helpers.old.user_credentials as holuscre  # isort:skip # noqa: E402
import dev_scripts.old.create_conda._setenv_lib as dsoccseli  # isort:skip # noqa: E402


# #############################################################################


_LOG = logging.getLogger(__name__)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # TODO(gp): We might want to force to print also the name of script to
    #  help debugging in_get_logging_format(force_print_format,
    #  force_verbose_format):
    hdbg.init_logger(verbosity=args.log_level)
    txt: List[str] = []
    #
    # - Report system info.
    #
    client_root_dir, user_name = dsoccseli.report_info(txt)
    # Get the path to amp dir.
    amp_path = client_root_dir
    amp_path = os.path.abspath(amp_path)
    hdbg.dassert_path_exists(amp_path)
    #
    # - Config Git.
    #
    user_credentials = holuscre.get_credentials()
    dsoccseli.config_git(user_name, user_credentials, txt)
    #
    # - Config Python (e.g., PYTHONPATH).
    #
    dsoccseli.config_python([client_root_dir], txt)
    #
    # - Config conda.
    #
    conda_env = "amp_develop"
    if args.conda_env and conda_env != args.conda_env:
        _LOG.warning(
            "Overriding the default conda env '%s' with '%s'",
            conda_env,
            args.conda_env,
        )
        conda_env = args.conda_env
    dsoccseli.config_conda(conda_env, user_credentials, txt)
    #
    # - Config PATH.
    #
    dirs = [
        f"{amp_path}/dev_scripts/{d}" for d in dsoccseli.get_dev_scripts_subdirs()
    ]
    dirs.append(os.path.join(amp_path, "documentation", "scripts"))
    dsoccseli.config_path(dirs, txt)
    #
    # - Test packages.
    #
    dsoccseli.test_packages(amp_path, txt)
    #
    # - Save.
    #
    dsoccseli.save_script(args, txt)


if __name__ == "__main__":
    _main(dsoccseli.parse())
