"""
Import as:

import helpers.introspection as hintros
"""

import collections.abc as cabc
import inspect
import sys
from typing import Any, List, Optional

import helpers.dbg as hdbg


def is_iterable(obj: object) -> bool:
    """
    Return whether obj can be iterated upon or not.

    Note that a string is iterable in python, but typically we refer to
    iterables as lists, tuples, so we exclude it.
    """
    # From https://stackoverflow.com/questions/1952464
    return not isinstance(obj, str) and isinstance(obj, cabc.Iterable)


def get_function_name(count: int = 0) -> str:
    """
    Return the name of the function calling this function, i.e., the name of
    the function calling `get_function_name()`.
    """
    ptr = inspect.currentframe()
    # count=0 corresponds to the calling function, so we need to add an extra
    # step walking the call stack.
    count += 1
    for _ in range(count):
        hdbg.dassert_is_not(ptr, None)
        ptr = ptr.f_back  # type: ignore
    func_name = ptr.f_code.co_name  # type: ignore
    return func_name


# #############################################################################


# https://code.activestate.com/recipes/577504/
# https://stackoverflow.com/questions/449560/how-do-i-determine-the-size-of-an-object-in-python


def get_size_in_bytes(obj: object, seen: Optional[set] = None) -> int:
    """
    Recursively find size of an object `obj` in bytes.
    """
    # From https://github.com/bosswissam/pysize
    # getsizeof() returns the size in bytes.
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Mark as seen *before* entering recursion to gracefully handle
    # self-referential objects.
    seen.add(obj_id)
    if hasattr(obj, "__dict__"):
        for cls in obj.__class__.__mro__:
            if "__dict__" in cls.__dict__:
                d = cls.__dict__["__dict__"]
                if inspect.isgetsetdescriptor(d) or inspect.ismemberdescriptor(d):
                    size += get_size_in_bytes(obj.__dict__, seen)
                break
    if isinstance(obj, dict):
        size += sum((get_size_in_bytes(v, seen) for v in obj.values()))
        size += sum((get_size_in_bytes(k, seen) for k in obj.keys()))
    elif isinstance(obj, cabc.Iterable) and not isinstance(
        obj, (str, bytes, bytearray)
    ):
        size += sum((get_size_in_bytes(i, seen) for i in obj))
    if hasattr(obj, "__slots__"):  # can have __slots__ with __dict__
        size += sum(
            get_size_in_bytes(getattr(obj, s), seen)
            for s in obj.__slots__
            if hasattr(obj, s)
        )
    return size


# TODO(gp): -> move to helpers/hprint.py
def format_size(num: float) -> str:
    """
    Return a human-readable string for a filesize (e.g., "3.5 MB").
    """
    # From http://stackoverflow.com/questions/1094841
    for x in ["bytes", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    assert 0, "Invalid num='%s'" % num


# #############################################################################


def get_methods(obj: Any, access: str = "all") -> List[str]:
    """
    Return list of names corresponding to class methods of an object `obj`.

    :param obj: class or class object
    :param access: allows to select private, public or all methods of
        the object.
    """
    methods = [method for method in dir(obj) if callable(getattr(obj, method))]
    if access == "all":
        pass
    elif access == "private":
        methods = [method for method in methods if method.startswith("_")]
    elif access == "public":
        methods = [method for method in methods if not method.startswith("_")]
    else:
        raise ValueError("Invalid access='%s'" % access)
    return methods
