"""
Import as:

import helpers.hdict as hdict
"""

import collections
import logging
from typing import Any, Dict, Generator, Iterable, Mapping, Optional, Tuple, Union

import helpers.hdbg as hdbg

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


_NO_VALUE_SPECIFIED = "__NO_VALUE_SPECIFIED__"


def typed_get(
    dict_: Union[Dict, "Config"],
    key: Any,
    default_value: Optional[Any] = _NO_VALUE_SPECIFIED,
    *,
    expected_type: Optional[Any] = None,
) -> Any:
    """
    Equivalent to `dict.get(key, default_val)` and check the type of the
    output.

    :param default_value: default value to return if key is not in `config`
    :param expected_type: expected type of `value`
    :return: config[key] if available, else `default_value`
    """
    hdbg.dassert_isinstance(dict_, dict)
    if default_value == _NO_VALUE_SPECIFIED:
        # No value is specified so check that the key is present with dassert_in
        # to report a decent error.
        hdbg.dassert_in(key, dict_)
    try:
        ret = dict_.__getitem__(key)
    except KeyError as e:
        # No key: use the default val if it was passed or asserts.
        _LOG.debug("e=%s", e)
        # We can't use None since None can be a valid default value, so we use
        # another value.
        if default_value != _NO_VALUE_SPECIFIED:
            ret = default_value
        else:
            # No default value found, then raise.
            raise e
    if expected_type is not None:
        hdbg.dassert_isinstance(ret, expected_type)
    return ret


def checked_get(
    dict_: Dict,
    key: Any,
) -> Any:
    """
    Ensure that the key exists and print a decent error message in case of
    error, instead of a generic `TypeError`.
    """
    hdbg.dassert_in(key, dict_)
    return dict_[key]
