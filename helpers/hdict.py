"""
Import as:

import helpers.hdict as hdict
"""

import collections
import logging
from typing import Any, Dict, Generator, Iterable, Mapping, Optional, Tuple

_LOG = logging.getLogger(__name__)


def get_nested_dict_iterator(
    nested: Mapping[Any, Any],
    path: Optional[Iterable[Any]] = None,
) -> Generator[Tuple[Tuple, Any], None, None]:
    """
    Return nested mapping iterator that iterates in a depth-first fashion.

    :param nested: nested dictionary
    :param path: path to node to start the visit from or `None` to start from
        the root
    :return: path to leaf node, value
    """
    if path is None:
        path = []
    if not isinstance(path, tuple):
        path = tuple(path)
    if not nested.items():
        yield path, nested
    for key, value in nested.items():
        local_path = path + (key,)
        if isinstance(value, collections.abc.Mapping):
            yield from get_nested_dict_iterator(value, local_path)
        else:
            yield local_path, value


def extract_leaf_values(nested: Dict[Any, Any], key: Any) -> Dict[Any, Any]:
    """
    Extract leaf values with key matching `key`.

    :param nested: nested dictionary
    :param key: leaf key value to match
    :return: dict with key = path as tuple, value = leaf value
    """
    d = {}
    for k, v in get_nested_dict_iterator(nested):
        if k[-1] == key:
            d[k] = v
    return d