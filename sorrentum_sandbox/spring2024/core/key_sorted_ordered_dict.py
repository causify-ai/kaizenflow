"""
Import as:

import core.key_sorted_ordered_dict as cksoordi
"""

import collections
import logging
from typing import Any, Optional, Tuple, Type

import helpers.hdbg as hdbg
import helpers.hobject as hobject

_LOG = logging.getLogger(__name__)

# TODO(gp): It could be in helpers since it's a basic data structure.


class KeySortedOrderedDict(hobject.PrintableMixin):
    """
    Key-value pairs where insertion order respects key order.
    """

    def __init__(
        self,
        key_type: Type,
        max_keys: Optional[int] = None,
    ):
        self._key_type = key_type
        self._max_keys = max_keys
        self._odict = collections.OrderedDict()

    def __len__(self):
        return len(self._odict)

    def __contains__(self, key: Any) -> bool:
        hdbg.dassert_isinstance(key, self._key_type)
        return key in self._odict

    def __getitem__(self, key: Any) -> Any:
        hdbg.dassert_isinstance(key, self._key_type)
        return self._odict[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        hdbg.dassert_isinstance(key, self._key_type)
        if self._odict:
            last_key = next(reversed(self._odict))
            hdbg.dassert_lt(last_key, key)
        self._odict[key] = value
        if self._max_keys is not None and len(self._odict) > self._max_keys:
            self._odict.popitem(last=False)

    def peek(self) -> Tuple[Any, Any]:
        """
        Get but do not remove last key, value pair.
        """
        # TODO(Paul): Alternatively we may do
        # key = next(reversed(self._odict)
        # value = self._odict[key]
        key, value = self._odict.popitem()
        self._odict[key] = value
        return key, value

    def get_ordered_dict(
        self, num_keys: Optional[int] = None
    ) -> collections.OrderedDict:
        """
        Get `num_keys` most recent elements as an `OrderedDict`.
        """
        if num_keys is None:
            return self._odict
        num_keys = min(num_keys, len(self._odict))
        counter = 0
        tmp_odict = collections.OrderedDict()
        for key in reversed(self._odict):
            tmp_odict[key] = self._odict[key]
            counter += 1
            if counter >= num_keys:
                break
        odict = collections.OrderedDict()
        for key in reversed(tmp_odict):
            odict[key] = tmp_odict[key]
        #
        hdbg.dassert_isinstance(odict, collections.OrderedDict)
        return odict
