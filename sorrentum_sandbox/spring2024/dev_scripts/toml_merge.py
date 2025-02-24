#!/usr/bin/env python

"""
Merge two or more pyproject.toml files in a single one. This can be used to
merge multiple poetry files.

> toml_merge.py \
    --in_file devops/docker_build/pyproject.toml \
    --in_file amp/devops/docker_build/pyproject.toml \
    --out_file pyproject.toml

Import as:

import dev_scripts.toml_merge as dsctomer
"""

import argparse
import copy
import logging
import os
import pprint
from typing import Any, List, MutableMapping

import toml

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)

_DepDict = MutableMapping[str, Any]


def _update(dict_merged: _DepDict, dict_new: _DepDict) -> _DepDict:
    """
    Merge a dictionary `dict_new` into `dict_merged` asserting if there are
    conflicting (key, value) pair.
    """
    for k, v in dict_new.items():
        v = dict_new[k]
        if k in dict_merged:
            if v != dict_merged[k]:
                raise ValueError(
                    "Key '%s' is assigned to different values '%s' and '%s'"
                    % (k, v, dict_merged[k])
                )
        else:
            dict_merged[k] = v
    return dict_merged


def _merge_deps(dicts: List[_DepDict]) -> _DepDict:
    """
    Merge a list of dictionary in place.
    """
    dict_merged: _DepDict = {}
    for dict_new in dicts:
        dict_merged = _update(dict_merged, dict_new)
    return dict_merged


def _merge_toml(pyprojs: List[_DepDict]) -> _DepDict:
    """
    Merge "dependencies", "dev-dependencies" keys in two toml dictionaries.
    """
    hdbg.dassert_lte(1, len(pyprojs))
    pyproj = copy.deepcopy(pyprojs[0])
    for key in ["dependencies", "dev-dependencies"]:
        pyproj_list = [
            curr_pyproj["tool"]["poetry"].get(key, {}) for curr_pyproj in pyprojs
        ]
        pyproj["tool"]["poetry"][key] = _merge_deps(pyproj_list)
    return pyproj


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--in_file", action="append", help="Files to read", required=True
    )
    parser.add_argument(
        "--out_file", action="store", help="File to write", required=True
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Load all the toml files requested as dictionaries.
    pyprojs: List[_DepDict] = []
    for file_name in args.in_file:
        file_name = os.path.abspath(file_name)
        _LOG.info("Reading file '%s'", file_name)
        pyproj = toml.load(file_name)
        _LOG.debug("file_name=%s:\n%s", file_name, pprint.pformat(pyproj))
        pyprojs.append(pyproj)
    # Merge all the toml files.
    merged_pyproj = _merge_toml(pyprojs)
    _LOG.debug("merged_pyproj=%s", pprint.pformat(merged_pyproj))
    # Save.
    merged_pyproj = hprint.sort_dictionary(merged_pyproj)
    merged_toml = toml.dumps(merged_pyproj)
    _LOG.debug("merged_toml=%s", merged_toml)
    file_name = os.path.abspath(args.out_file)
    hio.to_file(file_name, merged_toml)
    _LOG.info("Result saved into '%s'", file_name)


if __name__ == "__main__":
    _main(_parse())
