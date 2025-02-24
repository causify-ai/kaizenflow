"""
Import as:

import helpers.hlist as hlist
"""

from typing import Any, List, Optional, Set

import helpers.hdbg as hdbg

# TODO(gp): -> return_single_element, return_single_element_or_assert?
def assert_single_element_and_return(list_: List[Any]) -> Any:
    """
    Assert that the passed list has a single element and return that single
    element.

    :return: return the unique element in the list
    """
    hdbg.dassert_isinstance(list_, list)
    hdbg.dassert_eq(len(list_), 1, "List has %d elements!", len(list_))
    return list_[0]


def find_duplicates(list_: List[Any]) -> List[Any]:
    """
    Find the elements duplicated in a list.
    """
    hdbg.dassert_isinstance(list_, list)
    # Count the occurrences of each element of the seq.
    set_l = set(list_)
    v_to_num = [(v, list_.count(v)) for v in set_l]
    # Build list of elems with duplicates.
    res = [v for v, n in v_to_num if n > 1]
    return res


def remove_duplicates(list_: List[Any]) -> List[Any]:
    """
    Remove the elements duplicated in a list, without changing the order.
    """
    hdbg.dassert_isinstance(list_, list)
    list_out = []
    set_l: Set[Any] = set()
    for v in list_:
        if v not in set_l:
            set_l.add(v)
            list_out.append(v)
    return list_out


def extract(
    list_: List[Any], start_idx: Optional[int], end_idx: Optional[int]
) -> List[Any]:
    """
    Filter the list using [start_idx, end_idx).
    """
    if start_idx is not None:
        hdbg.dassert_lte(0, start_idx)
    else:
        start_idx = 0
    if end_idx is not None:
        hdbg.dassert_lte(end_idx, len(list_))
    else:
        end_idx = len(list_)
    if list_:
        hdbg.dassert_lt(start_idx, end_idx)
        list_ = list_[start_idx:end_idx]
    return list_


def chunk(list_: List[Any], n: int) -> List[Any]:
    hdbg.dassert_lte(1, n)
    hdbg.dassert_lte(n, len(list_))
    k, m = divmod(len(list_), n)
    return list(
        list_[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)
    )
