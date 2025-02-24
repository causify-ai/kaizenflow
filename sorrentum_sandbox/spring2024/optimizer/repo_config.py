"""
This file contains info specific of this repo.
"""

# TODO(gp): Is this file needed? optimizer is not a separate Git repo.

import logging

_LOG = logging.getLogger(__name__)
# We can't use `__file__` since this file is imported with an exec.
_LOG.debug("Importing //amp/optimizer/repo_config.py")

from typing import Dict


def get_repo_map() -> Dict[str, str]:
    """
    Return a mapping of short repo name -> long repo name.
    """
    repo_map: Dict[str, str] = {}
    return repo_map


def get_host_name() -> str:
    return "github.com"
