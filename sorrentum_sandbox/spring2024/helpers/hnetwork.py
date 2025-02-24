"""
Import as:

import helpers.hnetwork as hnetwor
"""

import logging
import os
import re
from typing import Optional, Tuple

import requests

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def check_url(url: str) -> None:
    """
    Check that an URL responds.
    """
    try:
        request = requests.get(url)
        exists = request.status_code == 200
        # pylint: disable=broad-except
    except Exception:
        # TODO(gp): RuntimeError doesn't seem to catch. Find a narrower
        #  exception to catch.
        exists = False
    if not exists:
        _LOG.warning("url '%s' doesn't exist", url)


def get_prefixes(jupyter_port: Optional[int] = None) -> Tuple[str, str]:
    """
    Return the prefixes that a file should have under a GitHub repo and a
    Jupyter notebook.
    """
    hsystem.get_user_name()
    if jupyter_port is None:
        jupyter_port = 10001
        _LOG.warning(
            "jupyter_port not available: using the default one %s", jupyter_port
        )
    repo_name = hgit.get_repo_full_name_from_client(super_module=False)
    _LOG.debug("repo_name=%s", repo_name)
    github_prefix = f"https://github.com/{repo_name}/blob/master"
    jupyter_prefix = f"http://localhost:{jupyter_port}/tree"
    return github_prefix, jupyter_prefix


# TODO(gp): -> get_canonical_file_name_from_url
def get_file_name(url: str) -> str:
    """
    Given an URL from GitHub or from Jupyter server extract the path
    corresponding to the file.

    E.g.,
    - http://localhost:10001/notebooks/research/...
        oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb
      ->
        oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb

    - https://github.com/.../.../blob/master/...
        oil/ST/Task229_Exploratory_analysis_of_ST_data.ipynb
      ->
        oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb
    """
    # "http://localhost:10001/notebooks/...
    #   oil/ST/Task229_Exploratory_analysis_of_ST_data_part1.ipynb"
    ret = None
    if ret is None:
        m = re.search(r"http.*://localhost:\d+/(.*)", url)
        if m:
            ret = m.group(1)
            to_remove = "notebooks/"
            idx = ret.index(to_remove)
            if idx >= 0:
                end_idx = idx + len(to_remove)
                ret = ret[end_idx:]
    if ret is None:
        # https://github.com/.../.../blob/master/...
        #   oil/ST/Task229_Exploratory_analysis_of_ST_data.ipynb
        m = re.search(r"http.*://.*github.com/(.*)", url)
        if m:
            ret = m.group(1)
            # Remove ".../.../blob/master"
            ret = "/".join(ret.split("/")[4:])
    if ret is None:
        if os.path.exists(url):
            ret = url
    if ret is None:
        hdbg.dassert_is_not(ret, None, "url=%s", url)
    return ret  # type: ignore
