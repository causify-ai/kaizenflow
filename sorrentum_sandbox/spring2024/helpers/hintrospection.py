"""
Import as:

import helpers.hintrospection as hintros
"""

import collections.abc as cabc
import importlib
import inspect
import logging
import pickle
import re
import sys
import types
from typing import Any, Callable, List, Optional, cast

import helpers.hdbg as hdbg

# This module can depend only on:
# - Python standard modules
# - a few helpers as described in `helpers/dependencies.txt`

_LOG = logging.getLogger(__name__)


# Copied from `hstring` to avoid import cycles.


def remove_prefix(string: str, prefix: str, assert_on_error: bool = True) -> str:
    if string.startswith(prefix):
        res = string[len(prefix) :]
    else:
        if assert_on_error:
            raise RuntimeError(
                f"string='{string}' doesn't start with prefix ='{prefix}'"
            )
    return res


# End copy.

# TODO(gp): object -> Any?


# #############################################################################
# Function introspection
# #############################################################################


def get_function_name(count: int = 0) -> str:
    """
    Return the name of the function calling this function.
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


def get_name_from_function(func: callable) -> str:
    """
    Return the name of the passed function.

    E.g., amp.helpers.test.test_hintrospection.test_function
    """
    func_name = func.__name__
    #
    module = inspect.getmodule(func)
    module_name = module.__name__
    # Remove `app.` if needed from the module name, e.g.,
    # `app.amp.helpers.test.test_hintrospection`.
    prefix = "app."
    if module_name.startswith(prefix):
        module_name = remove_prefix(module_name, prefix)
    return f"{module_name}.{func_name}"


def get_function_from_string(func_as_str: str) -> Callable:
    """
    Return the function from its name including the import.

    E.g., `import im.scripts.AmpTask317_transform_pq_by_date_to_by_asset`
    """
    # Split txt in an import and function name.
    m = re.match(r"^(\S+)\.(\S+)$", func_as_str)
    hdbg.dassert(m, "txt='%s'", func_as_str)
    m = cast(re.Match, m)
    import_, function = m.groups()
    _LOG.debug("import=%s", import_)
    _LOG.debug("function=%s", function)
    # Import the needed module.
    imp = importlib.import_module(import_)
    # Force the linter not to remove this import which is needed in the following
    # eval.
    _ = imp
    python_code = f"imp.{function}"
    func: Callable = eval(python_code)
    _LOG.debug("{txt} -> func=%s", func)
    return func


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
        raise ValueError(f"Invalid access='{access}'")
    return methods


# #############################################################################


def is_iterable(obj: object) -> bool:
    """
    Return whether obj can be iterated upon or not.

    Note that a string is iterable in Python, but typically we refer to
    iterables as lists, tuples, so we exclude strings.
    """
    # From https://stackoverflow.com/questions/1952464
    return not isinstance(obj, str) and isinstance(obj, cabc.Iterable)


# From https://stackoverflow.com/questions/53225
def is_bound_to_object(method: object) -> bool:
    """
    Return whether a method is bound to an object.
    """
    _LOG.debug("method=%s", method)
    if not hasattr(method, "__self__"):
        _LOG.debug("hasattr(im_self)=False")
        val = False
    else:
        # val = method.im_self is not None
        val = True
    return val


# From https://stackoverflow.com/questions/23852423
def is_lambda_function(method: object) -> bool:
    _LOG.debug("type(method)=%s", str(type(method)))
    return isinstance(method, types.LambdaType) and method.__name__ == "<lambda>"


def is_pickleable(obj: object, *, mode: str = "try_and_catch") -> bool:
    """
    Return if an object is a bound method.

    :param obj: object to process
    :param mode: approach to detect non-pikleable objects
        - "type_search": detect non-pickleable objects by type, e.g., lambda
            functions are not Pickleable
        - "try_and_catch": try to pickle an object directly, if it fails,
            an object is non-pickleable then
    """
    _LOG.debug("obj=%s", obj)
    if mode == "type_search":
        _LOG.debug("callable=%s", callable(obj))
        if not callable(obj):
            return True
        #
        is_bound = is_bound_to_object(obj)
        _LOG.debug("is_bound=%s", is_bound)
        if is_bound:
            return False
        #
        is_lambda = is_lambda_function(obj)
        _LOG.debug("is_lambda=%s", is_lambda)
        if is_lambda:
            return False
        return True
    elif mode == "try_and_catch":
        try:
            _ = pickle.dumps(obj)
            return True
        # `AttributeError` is raised when obj is a class with lambda param
        # values, and `TypeError`is raised when the class has DB connection
        # object as value.
        except (AttributeError, TypeError) as e:
            _LOG.debug("Cannot pickle object=%s, the error is %s", obj, str(e))
            return False
    else:
        raise ValueError(f"Invalid mode='{mode}'")


# #############################################################################
# Object size
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
    for x in ["b", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"%3.1f {x}" % num
        num /= 1024.0
    assert 0, f"Invalid num='{num}'"


# #############################################################################
# Stacktrace
# #############################################################################


def stacktrace_to_str() -> str:
    """
    Print the stack trace.
    """
    import traceback

    txt = traceback.format_stack()
    txt = "".join(txt)
    return txt
